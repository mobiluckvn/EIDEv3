// bai2/rtl/soc_top.v
// Khoi dinh SoC cho Bai 2 tren bo Sipeed Tang Nano 20K
// Tham so hoa ENABLE_MUL va ENABLE_FAST_MUL cho 3 cau hinh H0, H1, H2
`timescale 1ns / 1ps
`include "tai-lieu/picorv32.v"

`ifndef SOC_RTL_COMMON_DONE
`define SOC_RTL_COMMON_DONE
`include "bai1/rtl/reset_gen.v"
`include "bai1/rtl/bus_interconnect.v"
`include "bai1/rtl/bram_mem.v"
`include "bai1/rtl/uart_tx.v"
`include "bai1/rtl/gpio_led.v"
`endif

module soc_top #(
    parameter CLK_FREQ        = 27000000,
    parameter BAUD            = 115200,
    parameter HEX_FILE        = "bai2/build/firmware_h1.hex",
    parameter ENABLE_MUL      = 1,
    parameter ENABLE_FAST_MUL = 0
)(
    input  wire       clk,
    input  wire       btn_s1,
    output wire       uart_tx,
    output wire [5:0] led
);

    // Khoi tao reset he thong
    wire rst_n;
    wire [7:0] por_cnt_val;
    wire       por_done_val;
    reset_gen #(
        .POR_CYCLES(64)
    ) u_reset_gen (
        .clk(clk),
        .rst_n(rst_n),
        .por_cnt_out(por_cnt_val),
        .por_done_out(por_done_val)
    );

    // Tin hieu bus PicoRV32
    wire        cpu_trap;
    wire        cpu_mem_valid;
    wire        cpu_mem_instr;
    wire        cpu_mem_ready;
    wire [31:0] cpu_mem_addr;
    wire [31:0] cpu_mem_wdata;
    wire [3:0]  cpu_mem_wstrb;
    wire [31:0] cpu_mem_rdata;

    // Loi PicoRV32 voi tham so cau hinh bo nhan tuy bien (H0, H1, H2)
    picorv32 #(
        .ENABLE_COUNTERS   (1),
        .ENABLE_COUNTERS64 (1),
        .ENABLE_MUL        (ENABLE_MUL),
        .ENABLE_DIV        (0),
        .ENABLE_FAST_MUL   (ENABLE_FAST_MUL),
        .ENABLE_PCPI       (0),
        .COMPRESSED_ISA    (0),
        .PROGADDR_RESET    (32'h0000_0000),
        .STACKADDR         (32'h0000_8000)
    ) u_cpu (
        .clk         (clk),
        .resetn      (rst_n),
        .trap        (cpu_trap),
        .mem_valid   (cpu_mem_valid),
        .mem_instr   (cpu_mem_instr),
        .mem_ready   (cpu_mem_ready),
        .mem_addr    (cpu_mem_addr),
        .mem_wdata   (cpu_mem_wdata),
        .mem_wstrb   (cpu_mem_wstrb),
        .mem_rdata   (cpu_mem_rdata)
    );

    // Tin hieu ket noi ngoai vi
    wire        bram_valid;
    wire        bram_ready;
    wire [31:0] bram_rdata;

    wire        uart_tx_start;
    wire [7:0]  uart_tx_data;
    wire        uart_busy;

    wire        led_we;
    wire [5:0]  led_wdata;

    // Bo giai ma bus MMIO
    bus_interconnect u_bus (
        .clk           (clk),
        .rst_n         (rst_n),
        .cpu_mem_valid (cpu_mem_valid),
        .cpu_mem_addr  (cpu_mem_addr),
        .cpu_mem_wdata (cpu_mem_wdata),
        .cpu_mem_wstrb (cpu_mem_wstrb),
        .cpu_mem_ready (cpu_mem_ready),
        .cpu_mem_rdata (cpu_mem_rdata),

        .bram_valid    (bram_valid),
        .bram_ready    (bram_ready),
        .bram_rdata    (bram_rdata),

        .uart_tx_start (uart_tx_start),
        .uart_tx_data  (uart_tx_data),
        .uart_busy     (uart_busy),

        .led_we        (led_we),
        .led_wdata     (led_wdata)
    );

    // Bo nho BRAM 32 KB
    bram_mem #(
        .WORDS    (8192),
        .HEX_FILE (HEX_FILE)
    ) u_bram (
        .clk       (clk),
        .rst_n     (rst_n),
        .mem_valid (bram_valid),
        .mem_addr  (cpu_mem_addr),
        .mem_wdata (cpu_mem_wdata),
        .mem_wstrb (cpu_mem_wstrb),
        .mem_ready (bram_ready),
        .mem_rdata (bram_rdata)
    );

    // Bo phat UART TX
    uart_tx #(
        .CLK_FREQ (CLK_FREQ),
        .BAUD     (BAUD)
    ) u_uart_tx (
        .clk       (clk),
        .rst_n     (rst_n),
        .tx_start  (uart_tx_start),
        .tx_data   (uart_tx_data),
        .tx_busy   (uart_busy),
        .tx_serial (uart_tx)
    );

    // Dieu khien 6 LED ngoai
    gpio_led u_gpio_led (
        .clk       (clk),
        .rst_n     (rst_n),
        .led_we    (led_we),
        .led_wdata (led_wdata),
        .led_n     (led)
    );

endmodule
