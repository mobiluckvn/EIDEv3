`timescale 1ns / 1ps

`include "bai3/rtl/pcpi_dot4.v"

module tb_pcpi_dot4;

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
    pcpi_dot4 dut (
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

    // Xung clock 27 MHz
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

    // Mô hình tham chiếu
    reg signed [31:0] ref_acc;

    integer err_count;
    integer test_count;
    integer i;

    task check_negative_insn;
        input [31:0] bad_insn;
        input [31:0] rs1_val;
        input [31:0] rs2_val;
        input [80*8:1] msg;
        begin
            @(posedge clk);
            #1;
            pcpi_valid = 1'b1;
            pcpi_insn  = bad_insn;
            pcpi_rs1   = rs1_val;
            pcpi_rs2   = rs2_val;

            #1;
            test_count = test_count + 1;
            if (pcpi_ready !== 1'b0) begin
                $display("ERROR [%0s]: pcpi_ready must be 0 for invalid insn %h, got %b", msg, bad_insn, pcpi_ready);
                err_count = err_count + 1;
            end
            if (pcpi_wait !== 1'b0) begin
                $display("ERROR [%0s]: pcpi_wait must be 0 for invalid insn %h, got %b", msg, bad_insn, pcpi_wait);
                err_count = err_count + 1;
            end
            if (pcpi_wr !== 1'b0) begin
                $display("ERROR [%0s]: pcpi_wr must be 0 for invalid insn %h, got %b", msg, bad_insn, pcpi_wr);
                err_count = err_count + 1;
            end

            @(posedge clk);
            #1;
            pcpi_valid = 1'b0;
            pcpi_insn  = 32'd0;
            pcpi_rs1   = 32'd0;
            pcpi_rs2   = 32'd0;
        end
    endtask

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

            #1;
            if (!pcpi_ready) begin
                $display("ERROR: pcpi_ready not asserted for insn %h", insn);
                err_count = err_count + 1;
            end
            if (pcpi_wait !== 1'b0) begin
                $display("ERROR: pcpi_wait must be 0, got %b", pcpi_wait);
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

    task insn_acc_clr;
        reg [31:0] dummy_rd;
        reg        dummy_wr;
        begin
            execute_pcpi(make_insn(3'b000, 5'd0, 5'd0, 5'd0), 32'd0, 32'd0, dummy_rd, dummy_wr);
            ref_acc = 32'sd0;
        end
    endtask

    task insn_dot4;
        input [31:0] w_rs1;
        input [31:0] w_rs2;
        reg signed [7:0] a0, a1, a2, a3;
        reg signed [7:0] b0, b1, b2, b3;
        reg signed [31:0] term;
        reg [31:0] dummy_rd;
        reg        dummy_wr;
        begin
            a0 = w_rs1[7:0];
            a1 = w_rs1[15:8];
            a2 = w_rs1[23:16];
            a3 = w_rs1[31:24];

            b0 = w_rs2[7:0];
            b1 = w_rs2[15:8];
            b2 = w_rs2[23:16];
            b3 = w_rs2[31:24];

            term = ($signed(a0) * $signed(b0)) +
                   ($signed(a1) * $signed(b1)) +
                   ($signed(a2) * $signed(b2)) +
                   ($signed(a3) * $signed(b3));

            execute_pcpi(make_insn(3'b011, 5'd0, 5'd1, 5'd2), w_rs1, w_rs2, dummy_rd, dummy_wr);
            ref_acc = ref_acc + term;
        end
    endtask

    task insn_acc_rd_check;
        input [80*8:1] context_msg;
        reg [31:0] actual_rd;
        reg        actual_wr;
        begin
            execute_pcpi(make_insn(3'b010, 5'd3, 5'd0, 5'd0), 32'd0, 32'd0, actual_rd, actual_wr);
            test_count = test_count + 1;
            if (!actual_wr) begin
                $display("ERROR [%0s]: pcpi_wr was not asserted on acc.rd", context_msg);
                err_count = err_count + 1;
            end
            if ($signed(actual_rd) !== ref_acc) begin
                $display("ERROR [%0s]: mismatch! DUT=%d (0x%h), REF=%d (0x%h)",
                         context_msg, $signed(actual_rd), actual_rd, ref_acc, ref_acc);
                err_count = err_count + 1;
            end
        end
    endtask

    reg [31:0] rand_a;
    reg [31:0] rand_b;

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

        #100;
        @(posedge clk);
        #1;
        resetn = 1;
        #50;

        $display("=== START TB_PCPI_DOT4 UNIT TEST ===");

        // 1. Kiểm tra xóa tích luỹ và nạp giá trị mốc
        insn_acc_clr();
        insn_acc_rd_check("After reset and clr");

        insn_dot4(32'h01010101, 32'h01010101); // 1*1 + 1*1 + 1*1 + 1*1 = 4
        insn_acc_rd_check("Nap acc=4 truoc kiem tra am tinh");

        // -------------------------------------------------------------
        // Ca kiểm tra âm tính tách riêng từng chốt (single-fault check)
        // Khối phải IM HOÀN TOÀN (ready=0, wait=0, wr=0) và acc không đổi.
        // -------------------------------------------------------------
        $display("--- Negative tests: single-fault decode checks ---");

        // Chốt 1: Chỉ sai Opcode (opcode=7'b0110011 != 7'b0001011, funct7=0, funct3=011 dot4)
        check_negative_insn({7'b0000000, 5'd2, 5'd1, 3'b011, 5'd3, 7'b0110011}, 32'h10101010, 32'h20202020, "Single-fault: Opcode mismatch");

        // Chốt 2: Chỉ sai Funct7 (funct7=7'b0000001 != 7'b0000000, opcode=7'b0001011, funct3=011 dot4)
        check_negative_insn({7'b0000001, 5'd2, 5'd1, 3'b011, 5'd3, 7'b0001011}, 32'h10101010, 32'h20202020, "Single-fault: Funct7 mismatch (0000001)");
        check_negative_insn({7'b0100000, 5'd2, 5'd1, 3'b011, 5'd3, 7'b0001011}, 32'h10101010, 32'h20202020, "Single-fault: Funct7 mismatch (0100000)");

        // Chốt 3: Chỉ sai Funct3 lạ (opcode=7'b0001011, funct7=7'b0000000, funct3=3'b100, 101, 110, 111)
        check_negative_insn({7'b0000000, 5'd2, 5'd1, 3'b100, 5'd3, 7'b0001011}, 32'h10101010, 32'h20202020, "Single-fault: Funct3 unsupported (100)");
        check_negative_insn({7'b0000000, 5'd2, 5'd1, 3'b101, 5'd3, 7'b0001011}, 32'h10101010, 32'h20202020, "Single-fault: Funct3 unsupported (101)");
        check_negative_insn({7'b0000000, 5'd2, 5'd1, 3'b110, 5'd3, 7'b0001011}, 32'h10101010, 32'h20202020, "Single-fault: Funct3 unsupported (110)");
        check_negative_insn({7'b0000000, 5'd2, 5'd1, 3'b111, 5'd3, 7'b0001011}, 32'h10101010, 32'h20202020, "Single-fault: Funct3 unsupported (111)");

        // Đảm bảo acc vẫn giữ nguyên giá trị 4, không bị ghi đè hay tích luỹ bởi lệnh rác
        insn_acc_rd_check("Check acc unchanged after negative tests");

        // 2. Ca kiểm riêng biệt cho DẤU (Signedness tests)
        $display("--- 1. Specific Sign Tests ---");

        // 2a. (-128) * (-128) trên cả 4 byte lane
        // Byte = -128 (0x80)
        // 0x80808080 = [-128, -128, -128, -128]
        // Mỗi lane: (-128)*(-128) = 16384. 4 lane = 65536
        insn_acc_clr();
        insn_dot4(32'h80808080, 32'h80808080);
        insn_acc_rd_check("Sign test: 4x (-128)*(-128)");

        // 2b. (-1) * 127 trên cả 4 byte lane
        // Byte: -1 (0xFF), 127 (0x7F)
        // (-1)*127 = -127. 4 lane = -508
        insn_acc_clr();
        insn_dot4(32'hFFFFFFFF, 32'h7F7F7F7F);
        insn_acc_rd_check("Sign test: 4x (-1)*127");

        // 2c. Biên hỗn hợp: lane 0: 127*127, lane 1: (-128)*127, lane 2: 127*(-128), lane 3: (-128)*(-128)
        // rs1 = { -128, 127, -128, 127 } = 0x807F807F
        // rs2 = { -128, -128, 127, 127 } = 0x80807F7F
        insn_acc_clr();
        insn_dot4(32'h807F807F, 32'h80807F7F);
        insn_acc_rd_check("Sign test: Mixed corner cases");

        // 2d. Kiểm tra tích luỹ nhiều lần (dương và âm bù trừ)
        insn_acc_clr();
        insn_dot4(32'h01020304, 32'h05060708); // 1*5 + 2*6 + 3*7 + 4*8 = 5 + 12 + 21 + 32 = 70
        insn_dot4(32'hFFFFFFFF, 32'h01020304); // 4x (-1)*k = -1 - 2 - 3 - 4 = -10 -> tổng = 60
        insn_acc_rd_check("Accumulation test 2 steps");

        // 3. Kiểm tra ngẫu nhiên 1000+ bộ giá trị (gồm cả corner cases)
        $display("--- 2. Random 1200 Vectors with Corner Cases ---");
        insn_acc_clr();

        for (i = 0; i < 1200; i = i + 1) begin
            if (i % 50 == 0) begin
                // Thỉnh thoảng clr và kiểm tra
                insn_acc_rd_check("Periodic checkpoint");
                insn_acc_clr();
            end

            // Trộn các giá trị biên đặc biệt vào dữ liệu ngẫu nhiên
            case (i % 6)
                0: rand_a = {$random} | 32'h80000000; // Có byte chứa -128
                1: rand_a = {$random} | 32'h007F0000; // Có byte chứa 127
                2: rand_a = 32'h80808080;             // Toàn -128
                3: rand_a = 32'h7F7F7F7F;             // Toàn 127
                default: rand_a = $random;
            endcase

            case ((i + 1) % 6)
                0: rand_b = {$random} | 32'h80000000;
                1: rand_b = {$random} | 32'h007F0000;
                2: rand_b = 32'h80808080;
                3: rand_b = 32'h7F7F7F7F;
                default: rand_b = $random;
            endcase

            insn_dot4(rand_a, rand_b);
        end
        insn_acc_rd_check("Final random stream");

        // 4. Báo cáo kết quả
        $display("--------------------------------------------");
        $display("Total checks: %0d", test_count);
        $display("Total errors: %0d", err_count);
        if (err_count == 0) begin
            $display("TB_PCPI_DOT4: PASS");
        end else begin
            $display("TB_PCPI_DOT4: FAIL");
        end
        $display("--------------------------------------------");

        #100;
        $finish;
    end

endmodule
