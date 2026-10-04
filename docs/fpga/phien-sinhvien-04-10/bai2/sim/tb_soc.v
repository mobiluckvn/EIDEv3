// bai2/sim/tb_soc.v
// Testbench mo phong toan bo SoC cho Bai 2
// Bat va in tung byte UART, tu dong ket thuc khi nhan DONE_BENCHMARK_BAI2
`timescale 1ns / 1ps

`include "bai1/rtl/reset_gen.v"
`include "bai1/rtl/bus_interconnect.v"
`include "bai1/rtl/bram_mem.v"
`include "bai1/rtl/uart_tx.v"
`include "bai1/rtl/gpio_led.v"
`define SOC_RTL_COMMON_DONE
`include "bai2/rtl/soc_top.v"
`include "bai1/sim/uart_rx_model.v"

module tb_soc #(
`ifdef CFG_H2
    parameter HEX_FILE        = "bai2/build/firmware_h2.hex",
    parameter ENABLE_MUL      = 1,
    parameter ENABLE_FAST_MUL = 1
`elsif CFG_H1
    parameter HEX_FILE        = "bai2/build/firmware_h1.hex",
    parameter ENABLE_MUL      = 1,
    parameter ENABLE_FAST_MUL = 0
`else
    parameter HEX_FILE        = "bai2/build/firmware_h0.hex",
    parameter ENABLE_MUL      = 0,
    parameter ENABLE_FAST_MUL = 0
`endif
);

    reg clk;
    reg btn_s1;
    wire uart_tx_line;
    wire [5:0] leds;

    // Chu ky 27 MHz
    initial begin
        clk = 1'b0;
        forever #18.518 clk = ~clk;
    end

    initial begin
        btn_s1 = 1'b1;
    end

    // DUT SoC
    soc_top #(
        .CLK_FREQ        (27000000),
        .BAUD            (115200),
        .HEX_FILE        (HEX_FILE),
        .ENABLE_MUL      (ENABLE_MUL),
        .ENABLE_FAST_MUL (ENABLE_FAST_MUL)
    ) u_dut (
        .clk     (clk),
        .btn_s1  (btn_s1),
        .uart_tx (uart_tx_line),
        .led     (leds)
    );

    // Bo thu UART mo hinh
    wire       rx_valid;
    wire [7:0] rx_byte;

    uart_rx_model #(
        .CLK_FREQ (27000000),
        .BAUD     (115200)
    ) u_rx (
        .clk       (clk),
        .rst_n     (1'b1),
        .rx_serial (uart_tx_line),
        .rx_valid  (rx_valid),
        .rx_byte   (rx_byte)
    );

    // In tung byte UART va bat chuoi ket thuc / kiem tra loi
    reg [8*20-1:0] shift_reg = 0;
    reg [8*5-1:0]  ok_shift = 0;
    integer pass_count = 0;
    integer fail_count = 0;

    always @(posedge clk) begin
        if (u_dut.cpu_trap) begin
            $display("\n==========================================");
            $display("  KET QUA: FAIL (CPU TRAP)");
            $display("  CPU TRAP xay ra tai thoi diem %0t ps! PC = 0x%08x, Opcode = 0x%08x, ENABLE_MUL = %0d", 
                     $time, u_dut.u_cpu.reg_pc, u_dut.u_cpu.dbg_insn_opcode, ENABLE_MUL);
            $display("==========================================\n");
            $finish(1);
        end
    end

    always @(posedge clk) begin
        if (rx_valid) begin
            shift_reg <= {shift_reg[8*19-1:0], rx_byte};
            ok_shift  <= {ok_shift[8*4-1:0], rx_byte};

            if ({ok_shift[8*4-1:0], rx_byte} == ",ok=1") begin
                pass_count = pass_count + 1;
            end
            if ({ok_shift[8*4-1:0], rx_byte} == ",ok=0") begin
                fail_count = fail_count + 1;
            end

            if ({shift_reg[8*18-1:0], rx_byte} == "DONE_BENCHMARK_BAI2") begin
                $display("\n==========================================");
                $display("  TONG KET MO PHONG BAI 2:");
                $display("  So o do dat chuan (ok=1): %0d", pass_count);
                $display("  So o do bi loi: %0d", fail_count);
                if (fail_count > 0 || pass_count == 0) begin
                    $display("  KET QUA: FAIL");
                    $display("  Phat hien loi ket qua (ok=0) hoac chua co o do!");
                    $display("==========================================\n");
                    $finish(1);
                end else begin
                    $display("  KET QUA: PASS");
                    $display("  Tat ca %0d o do deu dung voi mo hinh chuan!", pass_count);
                    $display("==========================================\n");
                    $finish(0);
                end
            end
        end
    end

    // Gioi han thoi gian mo phong (30 giay xung nhip thuc te)
    initial begin
        #30_000_000_000; // 30 giay mo phong
        $display("\n==========================================");
        $display("  KET QUA MO PHONG BAI 2: FAIL (Timeout)");
        $display("==========================================\n");
        $finish;
    end

endmodule
