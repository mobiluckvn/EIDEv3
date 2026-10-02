`timescale 1ns / 1ps

`include "bai3/rtl/pcpi_vmini.v"
`include "rtl/bram.v"

module tb_pcpi_vmini;

    reg clk;
    reg resetn;

    // Giao diện PCPI
    reg         pcpi_valid;
    reg  [31:0] pcpi_insn;
    reg  [31:0] pcpi_rs1;
    reg  [31:0] pcpi_rs2;
    wire        pcpi_wr;
    wire [31:0] pcpi_rd;
    wire        pcpi_wait;
    wire        pcpi_ready;

    // Giao diện BRAM Port B
    wire        vmem_en;
    wire [31:0] vmem_addr;
    wire [31:0] vmem_wdata;
    wire [3:0]  vmem_wstrb;
    wire [31:0] vmem_rdata;

    // DUT: pcpi_vmini
    pcpi_vmini dut (
        .clk        (clk),
        .resetn     (resetn),
        .pcpi_valid (pcpi_valid),
        .pcpi_insn  (pcpi_insn),
        .pcpi_rs1   (pcpi_rs1),
        .pcpi_rs2   (pcpi_rs2),
        .pcpi_wr    (pcpi_wr),
        .pcpi_rd    (pcpi_rd),
        .pcpi_wait  (pcpi_wait),
        .pcpi_ready (pcpi_ready),
        .vmem_en    (vmem_en),
        .vmem_addr  (vmem_addr),
        .vmem_wdata (vmem_wdata),
        .vmem_wstrb (vmem_wstrb),
        .vmem_rdata (vmem_rdata)
    );

    // BRAM kết nối làm cổng B
    bram #(
        .WORDS(8192)
    ) ram (
        .clk        (clk),
        .resetn     (resetn),
        .mem_valid  (1'b0),
        .mem_addr   (32'd0),
        .mem_wdata  (32'd0),
        .mem_wstrb  (4'b0000),
        .mem_ready  (),
        .mem_rdata  (),
        .b_en       (vmem_en),
        .b_addr     (vmem_addr),
        .b_wdata    (vmem_wdata),
        .b_wstrb    (vmem_wstrb),
        .b_rdata    (vmem_rdata)
    );

    // Xung clock 27 MHz (~37.037 ns chu kỳ, nửa chu kỳ ~18.519 ns)
    always #18 clk = ~clk;

    localparam [6:0] OPCODE_CUSTOM0 = 7'b0001011;
    localparam [6:0] FUNCT7_CUSTOM0 = 7'b0000000;

    function [31:0] make_insn;
        input [2:0] funct3;
        input [4:0] rd;
        input [4:0] rs1;
        input [4:0] rs2;
        begin
            make_insn = {FUNCT7_CUSTOM0, rs2, rs1, funct3, rd, OPCODE_CUSTOM0};
        end
    endfunction

    integer err_count;

    // Thực thi một lệnh PCPI với đồng hồ canh (watchdog 64 chu kỳ)
    task exec_insn;
        input [31:0] insn;
        input [31:0] rs1_val;
        input [31:0] rs2_val;
        output [31:0] rd_val;
        integer watchdog;
        begin
            @(posedge clk);
            #1;
            pcpi_valid = 1'b1;
            pcpi_insn  = insn;
            pcpi_rs1   = rs1_val;
            pcpi_rs2   = rs2_val;
            watchdog   = 0;

            while (!pcpi_ready) begin
                @(posedge clk);
                #1;
                watchdog = watchdog + 1;
                if (watchdog > 64) begin
                    $display("FAIL treo: state=%0d step=%0d", dut.state, dut.step);
                    $finish;
                end
            end

            rd_val = pcpi_rd;
            @(posedge clk);
            #1;
            pcpi_valid = 1'b0;
            pcpi_insn  = 32'd0;
            pcpi_rs1   = 32'd0;
            pcpi_rs2   = 32'd0;
        end
    endtask

    // Kiểm tra ca âm: khối bắt buộc PHẢI IM LẶNG (ready=0, wait=0, wr=0, vmem_en=0)
    task check_negative_case;
        input [31:0] insn;
        input [31:0] rs1_val;
        input [31:0] rs2_val;
        input [8*48:1] desc;
        begin
            while (dut.state != 2'd0) begin
                @(posedge clk);
                #1;
            end
            @(posedge clk);
            #1;
            pcpi_valid = 1'b1;
            pcpi_insn  = insn;
            pcpi_rs1   = rs1_val;
            pcpi_rs2   = rs2_val;

            @(posedge clk);
            #1;
            if (pcpi_ready !== 1'b0 || pcpi_wait !== 1'b0 || pcpi_wr !== 1'b0 || vmem_en !== 1'b0) begin
                $display("FAIL [CA AM]: %0s - Khoi DA NHAN lenh! (ready=%b, wait=%b, wr=%b, vmem_en=%b)",
                         desc, pcpi_ready, pcpi_wait, pcpi_wr, vmem_en);
                err_count = err_count + 1;
            end else begin
                $display("PASS [CA AM]: %0s (khoi khong nhan lenh: ready=0, wait=0, wr=0, vmem_en=0)", desc);
            end

            @(posedge clk);
            #1;
            pcpi_valid = 1'b0;
            pcpi_insn  = 32'd0;
            pcpi_rs1   = 32'd0;
            pcpi_rs2   = 32'd0;
            @(posedge clk);
            #1;
        end
    endtask

    reg [31:0] res_rd;
    reg signed [31:0] expected_sum;
    integer k;
    integer iter;
    integer test_vl;
    integer vl_idx;
    reg signed [7:0] a_vals [0:15];
    reg signed [7:0] b_vals [0:15];

    initial begin
        clk        = 1'b0;
        resetn     = 1'b0;
        pcpi_valid = 1'b0;
        pcpi_insn  = 32'd0;
        pcpi_rs1   = 32'd0;
        pcpi_rs2   = 32'd0;

        // Khởi tạo dữ liệu mẫu cho vector A (16 phần tử int8) và B (16 phần tử int8)
        expected_sum = 0;
        for (k = 0; k < 16; k = k + 1) begin
            a_vals[k] = k + 1;       // 1, 2, ..., 16
            b_vals[k] = 8'sd2;       // 2, 2, ..., 2
            expected_sum = expected_sum + ($signed(a_vals[k]) * $signed(b_vals[k]));
        end

        // Nạp vector A vào BRAM tại byte address 32'h0000_0100 (từ 64..67)
        ram.mem[64] = {a_vals[3],  a_vals[2],  a_vals[1],  a_vals[0]};
        ram.mem[65] = {a_vals[7],  a_vals[6],  a_vals[5],  a_vals[4]};
        ram.mem[66] = {a_vals[11], a_vals[10], a_vals[9],  a_vals[8]};
        ram.mem[67] = {a_vals[15], a_vals[14], a_vals[13], a_vals[12]};

        // Nạp vector B vào BRAM tại byte address 32'h0000_0200 (từ 128..131)
        ram.mem[128] = {b_vals[3],  b_vals[2],  b_vals[1],  b_vals[0]};
        ram.mem[129] = {b_vals[7],  b_vals[6],  b_vals[5],  b_vals[4]};
        ram.mem[130] = {b_vals[11], b_vals[10], b_vals[9],  b_vals[8]};
        ram.mem[131] = {b_vals[15], b_vals[14], b_vals[13], b_vals[12]};

        // Nhả reset
        #100;
        @(posedge clk);
        #1;
        resetn = 1'b1;
        @(posedge clk);

        // 1. vsetvl 16 (funct3=100, rd=x11, rs1=x10, val=16)
        exec_insn(make_insn(3'b100, 5'd11, 5'd10, 5'd0), 32'd16, 32'd0, res_rd);

        // 2. vload v0, 32'h0000_0100 (funct3=101, vd=0 -> rd=0, rs1=x10)
        exec_insn(make_insn(3'b101, 5'd0, 5'd10, 5'd0), 32'h0000_0100, 32'd0, res_rd);

        // 3. vload v1, 32'h0000_0200 (funct3=101, vd=1 -> rd=1, rs1=x10)
        exec_insn(make_insn(3'b101, 5'd1, 5'd10, 5'd0), 32'h0000_0200, 32'd0, res_rd);

        // 4. vdot v0, v1 (funct3=110, vs1=v0 -> rs1=0, vs2=v1 -> rs2=1)
        exec_insn(make_insn(3'b110, 5'd0, 5'd0, 5'd1), 32'd0, 32'd0, res_rd);

        // 5. acc.rd rd (funct3=010, rd=x12)
        exec_insn(make_insn(3'b010, 5'd12, 5'd0, 5'd0), 32'd0, 32'd0, res_rd);

        // Kiểm tra kết quả so với expected_sum
        if ($signed(res_rd) == expected_sum) begin
            $display("TB_PCPI_VMINI (sanity test): PASS");
        end else begin
            $display("TB_PCPI_VMINI (sanity test): FAIL (got %0d, expected %0d)", $signed(res_rd), expected_sum);
        end

        // -------------------------------------------------------------
        // Kiểm tra mặt nạ vector length: vl in {4, 8, 12, 16}
        // Nhồi giá trị KHÁC 0 vào các byte ngoài vl (k >= vl) để kiểm tra mask
        // -------------------------------------------------------------
        $display("--- Bat dau kiem tra masking voi vl in {4, 8, 12, 16} ---");
        for (vl_idx = 0; vl_idx < 4; vl_idx = vl_idx + 1) begin
            case (vl_idx)
                0: test_vl = 4;
                1: test_vl = 8;
                2: test_vl = 12;
                default: test_vl = 16;
            endcase

            // Xóa bộ tích lũy acc
            exec_insn(make_insn(3'b000, 5'd0, 5'd0, 5'd0), 32'd0, 32'd0, res_rd);

            // Đặt vl bằng lệnh vsetvl
            exec_insn(make_insn(3'b100, 5'd11, 5'd10, 5'd0), test_vl, 32'd0, res_rd);

            // Nạp vector A và B:
            // - Các byte trong phạm vi vl (k < test_vl): mang dữ liệu tính toán
            // - Các byte ngoài phạm vi vl (k >= test_vl): NHỒI GIÁ TRỊ KHÁC 0
            expected_sum = 0;
            for (k = 0; k < 16; k = k + 1) begin
                if (k < test_vl) begin
                    a_vals[k] = k + 1;
                    b_vals[k] = 8'sd2;
                    expected_sum = expected_sum + ($signed(a_vals[k]) * $signed(b_vals[k]));
                end else begin
                    // Nhồi giá trị khác 0: nếu mask hỏng, kết quả sẽ sai ngay
                    a_vals[k] = 8'sd127;
                    b_vals[k] = -8'sd128;
                end
            end

            // Ghi vào BRAM vector A tại 0x0000_0100 (từ 64..67)
            ram.mem[64] = {a_vals[3],  a_vals[2],  a_vals[1],  a_vals[0]};
            ram.mem[65] = {a_vals[7],  a_vals[6],  a_vals[5],  a_vals[4]};
            ram.mem[66] = {a_vals[11], a_vals[10], a_vals[9],  a_vals[8]};
            ram.mem[67] = {a_vals[15], a_vals[14], a_vals[13], a_vals[12]};

            // Ghi vào BRAM vector B tại 0x0000_0200 (từ 128..131)
            ram.mem[128] = {b_vals[3],  b_vals[2],  b_vals[1],  b_vals[0]};
            ram.mem[129] = {b_vals[7],  b_vals[6],  b_vals[5],  b_vals[4]};
            ram.mem[130] = {b_vals[11], b_vals[10], b_vals[9],  b_vals[8]};
            ram.mem[131] = {b_vals[15], b_vals[14], b_vals[13], b_vals[12]};

            // Nạp vector v0 và v1 qua vload
            exec_insn(make_insn(3'b101, 5'd0, 5'd10, 5'd0), 32'h0000_0100, 32'd0, res_rd);
            exec_insn(make_insn(3'b101, 5'd1, 5'd10, 5'd0), 32'h0000_0200, 32'd0, res_rd);

            // Thực hiện tính tích vô hướng vdot
            exec_insn(make_insn(3'b110, 5'd0, 5'd0, 5'd1), 32'd0, 32'd0, res_rd);

            // Đọc kết quả acc
            exec_insn(make_insn(3'b010, 5'd12, 5'd0, 5'd0), 32'd0, 32'd0, res_rd);

            if ($signed(res_rd) == expected_sum) begin
                $display("PASS [MASK TEST vl=%0d]: got %0d, expected %0d", test_vl, $signed(res_rd), expected_sum);
            end else begin
                $display("FAIL [MASK TEST vl=%0d]: got %0d, expected %0d (mask khong hoat dong!)", test_vl, $signed(res_rd), expected_sum);
                err_count = err_count + 1;
            end
        end

        // -------------------------------------------------------------
        // Bốn ca âm: mỗi ca sai đúng MỘT thứ, khối bắt buộc KHÔNG nhận lệnh
        // -------------------------------------------------------------
        $display("--- Bat dau kiem tra 4 ca am (single-fault decode / alignment) ---");

        // Ca 1: funct7 sai (0000001 != 0000000), opcode custom-0 đúng, funct3=110 (vdot) đúng, địa chỉ đúng
        check_negative_case({7'b0000001, 5'd1, 5'd0, 3'b110, 5'd0, 7'b0001011}, 32'h0000_0100, 32'h0000_0200, "Ca am 1: funct7 sai (0000001)");

        // Ca 2: opcode sai (0110011 != 0001011), funct7=0000000 đúng, funct3=110 (vdot) đúng, địa chỉ đúng
        check_negative_case({7'b0000000, 5'd1, 5'd0, 3'b110, 5'd0, 7'b0110011}, 32'h0000_0100, 32'h0000_0200, "Ca am 2: opcode sai (0110011)");

        // Ca 3: Voi tung lenh 3c, dua funct7 = 1 (sai funct7 thi khoi khong nhan)
        check_negative_case({7'b0000001, 5'd0, 5'd10, 3'b100, 5'd0, 7'b0001011}, 32'd16,         32'd0,         "Ca am 3a: vsetvl funct7=1");
        check_negative_case({7'b0000001, 5'd0, 5'd10, 3'b101, 5'd0, 7'b0001011}, 32'h0000_0100, 32'd0,         "Ca am 3b: vload funct7=1");
        check_negative_case({7'b0000001, 5'd1, 5'd0,  3'b110, 5'd0, 7'b0001011}, 32'd0,         32'd0,         "Ca am 3c: vdot funct7=1");
        check_negative_case({7'b0000001, 5'd0, 5'd10, 3'b111, 5'd0, 7'b0001011}, 32'h0000_0100, 32'd0,         "Ca am 3d: vstore funct7=1");

        // Ca 4: dia chi lech (rs1=0x0000_0101 khong chia het cho 4), opcode đúng, funct7 đúng, funct3=101 (vload) đúng
        check_negative_case({7'b0000000, 5'd0, 5'd10, 3'b101, 5'd0, 7'b0001011}, 32'h0000_0101, 32'd0, "Ca am 4: dia chi lech (rs1=0x101)");

        // -------------------------------------------------------------
        // Ca rieng cho dong ho canh (Watchdog test):
        // Giu pcpi_valid len voi mot lenh co funct7 sai roi cho du.
        // Ca nay PASS khi dong ho canh no, khong phai FAIL.
        // -------------------------------------------------------------
        $display("--- Bat dau kiem tra ca dong ho canh (funct7 sai) ---");
        begin : test_watchdog
            integer wd_cycles;
            reg wd_fired;
            reg unexpected_resp;

            @(posedge clk);
            #1;
            pcpi_valid = 1'b1;
            // funct7 = 7'b0000001 (sai), opcode custom-0, funct3 = 3'b110 (vdot)
            pcpi_insn  = {7'b0000001, 5'd1, 5'd0, 3'b110, 5'd0, 7'b0001011};
            pcpi_rs1   = 32'h0000_0100;
            pcpi_rs2   = 32'h0000_0200;
            wd_cycles  = 0;
            wd_fired   = 1'b0;
            unexpected_resp = 1'b0;

            // Giu pcpi_valid = 1 va cho du 64 chu ky
            while (wd_cycles < 64 && !unexpected_resp) begin
                @(posedge clk);
                #1;
                wd_cycles = wd_cycles + 1;
                if (pcpi_ready || pcpi_wait) begin
                    unexpected_resp = 1'b1;
                end
            end

            if (unexpected_resp) begin
                $display("FAIL [DONG HO CANH]: Khoi phan hoi bat thuong khi funct7 sai! (ready=%b, wait=%b)", pcpi_ready, pcpi_wait);
                err_count = err_count + 1;
            end else begin
                wd_fired = 1'b1;
                $display("PASS [DONG HO CANH]: Giu pcpi_valid voi funct7 sai qua %0d chu ky -> Dong ho canh da no dung ky vong!", wd_cycles);
            end

            @(posedge clk);
            #1;
            pcpi_valid = 1'b0;
            pcpi_insn  = 32'd0;
            pcpi_rs1   = 32'd0;
            pcpi_rs2   = 32'd0;
            @(posedge clk);
            #1;
        end

        // 6. Kiểm tra 1000 bộ ngẫu nhiên gồm các giá trị biên -128 và 127
        err_count = 0;
        $display("--- Bat dau kiem tra 1000 bo ngau nhien (co corner cases -128 va 127) ---");
        for (iter = 0; iter < 1000; iter = iter + 1) begin
            // Xóa thanh ghi tích lũy acc bằng lệnh acc.clr (funct3=3'b000)
            exec_insn(make_insn(3'b000, 5'd0, 5'd0, 5'd0), 32'd0, 32'd0, res_rd);

            expected_sum = 0;
            for (k = 0; k < 16; k = k + 1) begin
                case (k % 4)
                    0: a_vals[k] = (iter % 3 == 0) ? -8'sd128 : (iter % 3 == 1) ? 8'sd127 : $random;
                    1: a_vals[k] = (iter % 3 == 2) ? -8'sd128 : $random;
                    default: a_vals[k] = $random;
                endcase

                case ((k + 1) % 4)
                    0: b_vals[k] = (iter % 3 == 0) ? 8'sd127 : (iter % 3 == 1) ? -8'sd128 : $random;
                    1: b_vals[k] = (iter % 3 == 2) ? 8'sd127 : $random;
                    default: b_vals[k] = $random;
                endcase

                expected_sum = expected_sum + ($signed(a_vals[k]) * $signed(b_vals[k]));
            end

            // Nạp vector A vào BRAM tại byte address 32'h0000_0100 (từ 64..67)
            ram.mem[64] = {a_vals[3],  a_vals[2],  a_vals[1],  a_vals[0]};
            ram.mem[65] = {a_vals[7],  a_vals[6],  a_vals[5],  a_vals[4]};
            ram.mem[66] = {a_vals[11], a_vals[10], a_vals[9],  a_vals[8]};
            ram.mem[67] = {a_vals[15], a_vals[14], a_vals[13], a_vals[12]};

            // Nạp vector B vào BRAM tại byte address 32'h0000_0200 (từ 128..131)
            ram.mem[128] = {b_vals[3],  b_vals[2],  b_vals[1],  b_vals[0]};
            ram.mem[129] = {b_vals[7],  b_vals[6],  b_vals[5],  b_vals[4]};
            ram.mem[130] = {b_vals[11], b_vals[10], b_vals[9],  b_vals[8]};
            ram.mem[131] = {b_vals[15], b_vals[14], b_vals[13], b_vals[12]};

            // Thực hiện chuỗi lệnh vsetvl 16, vload v0, vload v1, vdot v0 v1, acc.rd rd
            exec_insn(make_insn(3'b100, 5'd11, 5'd10, 5'd0), 32'd16, 32'd0, res_rd);
            exec_insn(make_insn(3'b101, 5'd0, 5'd10, 5'd0), 32'h0000_0100, 32'd0, res_rd);
            exec_insn(make_insn(3'b101, 5'd1, 5'd10, 5'd0), 32'h0000_0200, 32'd0, res_rd);
            exec_insn(make_insn(3'b110, 5'd0, 5'd0, 5'd1), 32'd0, 32'd0, res_rd);
            exec_insn(make_insn(3'b010, 5'd12, 5'd0, 5'd0), 32'd0, 32'd0, res_rd);

            if ($signed(res_rd) != expected_sum) begin
                $display("FAIL tai iter %0d: got %0d, expected %0d", iter, $signed(res_rd), expected_sum);
                err_count = err_count + 1;
            end
        end

        if (err_count == 0) begin
            $display("TB_PCPI_VMINI: 1000 RANDOM CHECKS PASS");
        end else begin
            $display("TB_PCPI_VMINI: 1000 RANDOM CHECKS FAIL (%0d errors)", err_count);
        end

        $finish;
    end

endmodule
