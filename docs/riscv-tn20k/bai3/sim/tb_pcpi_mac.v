`timescale 1ns / 1ps

`include "bai3/rtl/pcpi_mac.v"

module tb_pcpi_mac;

    reg clk;
    reg resetn;
    reg pcpi_valid;
    reg [31:0] pcpi_insn;
    reg [31:0] pcpi_rs1;
    reg [31:0] pcpi_rs2;

    wire        pcpi_wr;
    wire [31:0] pcpi_rd;
    wire        pcpi_wait;
    wire        pcpi_ready;

    // DUT
    pcpi_mac dut (
        .clk        (clk),
        .resetn     (resetn),
        .pcpi_valid (pcpi_valid),
        .pcpi_insn  (pcpi_insn),
        .pcpi_rs1   (pcpi_rs1),
        .pcpi_rs2   (pcpi_rs2),
        .pcpi_wr    (pcpi_wr),
        .pcpi_rd    (pcpi_rd),
        .pcpi_wait  (pcpi_wait),
        .pcpi_ready (pcpi_ready)
    );

    // Tạo xung clock 27 MHz (chu kỳ ~37 ns)
    always #18 clk = ~clk;

    // Mã lệnh custom-0 (opcode = 7'b0001011, funct7 = 7'b0000000)
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

    // Mô hình tham chiếu độc lập trong testbench
    reg signed [31:0] ref_acc;

    // Bộ đếm kiểm thử
    integer err_count;
    integer test_count;
    integer i;

    // Task thực thi 1 lệnh PCPI
    task execute_pcpi;
        input  [31:0] insn;
        input  [31:0] rs1;
        input  [31:0] rs2;
        output [31:0] rd_val;
        output        rd_wr;
        begin
            @(posedge clk);
            #1;
            pcpi_valid = 1'b1;
            pcpi_insn  = insn;
            pcpi_rs1   = rs1;
            pcpi_rs2   = rs2;

            #1; // Cho phép mạng tổ hợp lan truyền tín hiệu wire
            if (!pcpi_ready) begin
                $display("ERROR: pcpi_ready not asserted for valid instruction %h", insn);
                err_count = err_count + 1;
            end
            if (pcpi_wait !== 1'b0) begin
                $display("ERROR: pcpi_wait must be 0 for 1-cycle MAC, got %b", pcpi_wait);
                err_count = err_count + 1;
            end

            rd_val = pcpi_rd;
            rd_wr  = pcpi_wr;

            @(posedge clk);
            #1;
            pcpi_valid = 1'b0;
            pcpi_insn  = 32'd0;
            pcpi_rs1   = 32'd0;
            pcpi_rs2   = 32'd0;
        end
    endtask

    // Task xóa bộ tích luỹ
    task insn_acc_clr;
        reg [31:0] dummy_rd;
        reg        dummy_wr;
        begin
            execute_pcpi(make_insn(3'b000, 5'd0, 5'd0, 5'd0), 32'd0, 32'd0, dummy_rd, dummy_wr);
            ref_acc = 32'sd0;
        end
    endtask

    // Task nhân cộng
    task insn_mac;
        input signed [31:0] s_rs1;
        input signed [31:0] s_rs2;
        reg [31:0] dummy_rd;
        reg        dummy_wr;
        begin
            execute_pcpi(make_insn(3'b001, 5'd0, 5'd1, 5'd2), s_rs1, s_rs2, dummy_rd, dummy_wr);
            ref_acc = ref_acc + (s_rs1 * s_rs2);
        end
    endtask

    // Task đọc bộ tích luỹ và so sánh với mô hình tham chiếu
    task insn_acc_rd_check;
        input [80*8:1] context_msg;
        reg [31:0] actual_rd;
        reg        actual_wr;
        begin
            execute_pcpi(make_insn(3'b010, 5'd3, 5'd0, 5'd0), 32'd0, 32'd0, actual_rd, actual_wr);
            if (!actual_wr) begin
                $display("FAIL: acc.rd did not assert pcpi_wr! Context: %s", context_msg);
                err_count = err_count + 1;
            end
            if ($signed(actual_rd) !== ref_acc) begin
                $display("FAIL: Mismatch in acc.rd! Actual=0x%08x (%0d), Expected=0x%08x (%0d). Context: %s",
                         actual_rd, $signed(actual_rd), ref_acc, ref_acc, context_msg);
                err_count = err_count + 1;
            end
            test_count = test_count + 1;
        end
    endtask

    // Task kiểm tra lệnh âm tính: khối phải im hoàn toàn (ready=0, wait=0, wr=0, acc không đổi)
    task check_negative_insn;
        input [31:0] bad_insn;
        input signed [31:0] test_rs1;
        input signed [31:0] test_rs2;
        input [80*8:1] test_name;
        reg signed [31:0] saved_acc;
        begin
            saved_acc = ref_acc;
            @(posedge clk);
            #1;
            pcpi_valid = 1'b1;
            pcpi_insn  = bad_insn;
            pcpi_rs1   = test_rs1;
            pcpi_rs2   = test_rs2;

            #1;
            if (pcpi_ready !== 1'b0) begin
                $display("FAIL: %0s - pcpi_ready phai bang 0 (got %b, insn=%08x)", test_name, pcpi_ready, bad_insn);
                err_count = err_count + 1;
            end
            if (pcpi_wait !== 1'b0) begin
                $display("FAIL: %0s - pcpi_wait phai bang 0 (got %b)", test_name, pcpi_wait);
                err_count = err_count + 1;
            end
            if (pcpi_wr !== 1'b0) begin
                $display("FAIL: %0s - pcpi_wr phai bang 0 (got %b)", test_name, pcpi_wr);
                err_count = err_count + 1;
            end

            @(posedge clk);
            #1;
            pcpi_valid = 1'b0;
            pcpi_insn  = 32'd0;
            pcpi_rs1   = 32'd0;
            pcpi_rs2   = 32'd0;

            // Kiểm tra biến nội bộ acc không bị thay đổi lén
            if (dut.acc !== saved_acc) begin
                $display("FAIL: %0s - acc bi thay doi len! Truoc=%0d, Sau=%0d", test_name, saved_acc, dut.acc);
                err_count = err_count + 1;
            end

            // Kiểm tra qua lệnh acc.rd hợp lệ xem giá trị acc có đúng không
            insn_acc_rd_check(test_name);
        end
    endtask

    reg signed [31:0] rand_a, rand_b;

    initial begin
        clk = 0;
        resetn = 0;
        pcpi_valid = 0;
        pcpi_insn = 0;
        pcpi_rs1 = 0;
        pcpi_rs2 = 0;
        ref_acc = 0;
        err_count = 0;
        test_count = 0;

        // Reset
        #100;
        @(posedge clk);
        #1;
        resetn = 1;
        #50;

        $display("=================================================");
        $display("Bat dau kiem tra don vi: pcpi_mac (nac 3a)");
        $display("=================================================");

        // 1. Kiểm tra acc.clr ban đầu và nạp giá trị khác 0 để chuẩn bị thử nghiệm âm tính
        insn_acc_clr();
        insn_acc_rd_check("acc.clr ban dau");

        insn_mac(32'sd10, 32'sd10); // ref_acc = 100
        insn_acc_rd_check("Nap acc=100 truoc kiem tra am tinh");

        // 2. Kiểm tra các ca âm tính: khối phải IM HOÀN TOÀN (ready=0, wait=0, wr=0, acc không đổi)
        $display("Kiem tra cac ca am tinh (khoi phai im hoan toan)...");
        // Ca 0: Lệnh chuẩn RV32M MUL (sai cả opcode lẫn funct7)
        check_negative_insn(32'h02208133, 32'sd10, 32'sd20, "Ca am tinh 0: RV32M MUL");

        // Ca 1: funct7 = 7'b0000000 đúng nhưng opcode khác custom-0 (dùng opcode OP=7'b0110011)
        // insn: funct7=0000000, rs2=2, rs1=1, funct3=001 (mac), rd=3, opcode=0110011 (OP)
        check_negative_insn({7'b0000000, 5'd2, 5'd1, 3'b001, 5'd3, 7'b0110011}, 32'sd20, 32'sd30, "Ca am tinh 1: funct7=0 dung, opcode khac custom-0");

        // Ca 2: opcode = 7'b0001011 (custom-0) đúng nhưng funct7 != 7'b0000000 (dùng funct7=7'b0000001)
        // insn: funct7=0000001, rs2=2, rs1=1, funct3=001 (mac), rd=3, opcode=7'b0001011 (custom-0)
        check_negative_insn({7'b0000001, 5'd2, 5'd1, 3'b001, 5'd3, 7'b0001011}, 32'sd50, 32'sd60, "Ca am tinh 2: opcode custom-0 dung, funct7 khac 0");
        $display("OK: Tat ca cac ca am tinh deu pass (khoi im hoan toan, acc khong doi).");

        // 3. Kiểm tra các trường hợp biên đặc biệt theo đề bài (-128, 127)
        $display("Kiem tra cac ca bien: -128 va 127...");

        // Ca 3.1: (-128) * (-128) = 16384
        insn_acc_clr();
        insn_mac(-32'sd128, -32'sd128);
        insn_acc_rd_check("(-128) * (-128)");

        // Ca 3.2: (-128) * 127 = -16256
        insn_acc_clr();
        insn_mac(-32'sd128, 32'sd127);
        insn_acc_rd_check("(-128) * 127");

        // Ca 3.3: 127 * 127 = 16129
        insn_acc_clr();
        insn_mac(32'sd127, 32'sd127);
        insn_acc_rd_check("127 * 127");

        // Ca 3.4: Tích luỹ chuỗi biên: acc = 0 + (-128)*127 + 127*(-128) + (-128)*(-128) + 127*127
        insn_acc_clr();
        insn_mac(-32'sd128, 32'sd127);
        insn_mac(32'sd127, -32'sd128);
        insn_mac(-32'sd128, -32'sd128);
        insn_mac(32'sd127, 32'sd127);
        insn_acc_rd_check("Chuoi bien tich luy");

        // Ca 3.5: Các giá trị biên 32-bit: -1, 1, 0, số lớn
        insn_acc_clr();
        insn_mac(-32'sd1, 32'sd100);
        insn_mac(32'sd1, -32'sd50);
        insn_mac(32'sd0, 32'sd12345);
        insn_mac(-32'sd3000, 32'sd2000);
        insn_acc_rd_check("Gia tri bien 32-bit");

        // 4. Chạy ít nhất 1 000 bộ ngẫu nhiên (chạy 1 200 bộ)
        $display("Chay 1200 bo thu ngau nhien (bao gom -128 va 127)...");
        insn_acc_clr();

        for (i = 0; i < 1200; i = i + 1) begin
            // 10% cơ hội đưa giá trị biên -128 hoặc 127
            if ((i % 10) == 0) rand_a = -32'sd128;
            else if ((i % 10) == 1) rand_a = 32'sd127;
            else if ((i % 10) == 2) rand_a = -32'sd1;
            else rand_a = $random % 256; // dải 8-bit mở rộng

            if ((i % 10) == 3) rand_b = -32'sd128;
            else if ((i % 10) == 4) rand_b = 32'sd127;
            else if ((i % 10) == 5) rand_b = 32'sd0;
            else rand_b = $random % 256;

            // Đôi khi thử cả số 32-bit lớn
            if ((i % 50) == 0) begin
                rand_a = $random;
                rand_b = $random;
            end

            // Cứ mỗi 100 phép tính thì xóa acc để kiểm tra acc.clr giữa chừng
            if ((i > 0) && (i % 100 == 0)) begin
                insn_acc_clr();
            end

            insn_mac(rand_a, rand_b);

            // Kiểm tra kết quả acc.rd mỗi 5 phép tính hoặc ở cuối
            if ((i % 5 == 0) || (i == 1199)) begin
                insn_acc_rd_check("Vong lap ngau nhien");
            end
        end

        $display("-------------------------------------------------");
        $display("Tong so phep kiem tra rd doc lap: %0d", test_count);
        $display("Tong so loi phat hien: %0d", err_count);
        $display("-------------------------------------------------");

        if (err_count == 0) begin
            $display("PASS: Tat ca cac ca kiem thu pcpi_mac deu thanh cong!");
        end else begin
            $display("FAIL: Co %0d loi trong qua trinh kiem thu!", err_count);
        end

        $finish;
    end

endmodule
