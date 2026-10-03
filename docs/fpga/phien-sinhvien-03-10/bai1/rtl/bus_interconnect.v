// bus_interconnect.v
// Bộ giải mã bus và phân nhánh địa chỉ theo kiến trúc PicoRV32 Memory Bus
`timescale 1ns / 1ps

module bus_interconnect (
    input  wire        clk,
    input  wire        rst_n,

    // Giao diện PicoRV32 Bus
    input  wire        cpu_mem_valid,
    input  wire [31:0] cpu_mem_addr,
    input  wire [31:0] cpu_mem_wdata,
    input  wire [3:0]  cpu_mem_wstrb,
    output wire        cpu_mem_ready,
    output reg  [31:0] cpu_mem_rdata,

    // Giao diện BRAM (0x0000_0000 - 0x0000_7FFF)
    output wire        bram_valid,
    input  wire        bram_ready,
    input  wire [31:0] bram_rdata,

    // Giao diện UART (0x1000_0000 & 0x1000_0004)
    output reg         uart_tx_start,
    output wire [7:0]  uart_tx_data,
    input  wire        uart_busy,

    // Giao diện LED (0x2000_0000)
    output reg         led_we,
    output wire [5:0]  led_wdata
);

    // Phân vùng địa chỉ
    wire sel_bram    = (cpu_mem_addr[31:15] == 17'h00000);             // 0x0000_0000 - 0x0000_7FFF (32 KB)
    wire sel_uart_tx = (cpu_mem_addr == 32'h1000_0000);                // Ghi byte UART TX
    wire sel_uart_st = (cpu_mem_addr == 32'h1000_0004);                // Đọc trạng thái UART (bit 0 = busy)
    wire sel_led     = (cpu_mem_addr == 32'h2000_0000);                // Ghi 6 bit LED

    assign bram_valid = cpu_mem_valid && sel_bram;

    assign uart_tx_data = cpu_mem_wdata[7:0];
    assign led_wdata    = cpu_mem_wdata[5:0];

    // Tạo ready 1 chu kỳ cho toàn bộ các thiết bị ngoại vi MMIO và vùng địa chỉ không hợp lệ
    reg mmio_ready;
    always @(posedge clk) begin
        if (!rst_n) begin
            mmio_ready    <= 1'b0;
            uart_tx_start <= 1'b0;
            led_we        <= 1'b0;
        end else begin
            uart_tx_start <= 1'b0;
            led_we        <= 1'b0;
            mmio_ready    <= cpu_mem_valid && !sel_bram && !mmio_ready;

            if (cpu_mem_valid && !mmio_ready) begin
                if (sel_uart_tx && |cpu_mem_wstrb) begin
                    uart_tx_start <= 1'b1;
                end
                if (sel_led && |cpu_mem_wstrb) begin
                    led_we <= 1'b1;
                end
            end
        end
    end

    // Ghép tín hiệu cpu_mem_ready
    assign cpu_mem_ready = sel_bram ? bram_ready : mmio_ready;

    // Ghép dữ liệu cpu_mem_rdata
    always @(*) begin
        if (sel_bram) begin
            cpu_mem_rdata = bram_rdata;
        end else if (sel_uart_st) begin
            cpu_mem_rdata = {31'd0, uart_busy};
        end else begin
            // Địa chỉ không hợp lệ hoặc thanh ghi chỉ ghi -> đọc ra 0 chống treo
            cpu_mem_rdata = 32'd0;
        end
    end

endmodule
