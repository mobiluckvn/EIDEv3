`timescale 1ns / 1ps

`include "third_party/picorv32/picorv32.v"

module soc_top #(
    parameter INIT_FILE = ".eide/build/mach.hex"
) (
    input  wire       clk_27m,      // Thạch anh 27 MHz (PIN 4)
    input  wire       btn_s1,       // Nút S1 (PIN 88, Active-Low)
    output wire       uart_tx_pin,  // UART TX nối BL616 (PIN 69)
    output wire [5:0] led           // 6 LED trên bo (PIN 15..20, Active-Low)
);

    // -------------------------------------------------------------
    // 1. Mạch tạo tín hiệu Reset
    //    Giữ reset 16 chu kỳ sau cấp nguồn hoặc khi nhấn S1
    // -------------------------------------------------------------
    reg [4:0] por_cnt = 5'd0;
    reg       sys_resetn = 1'b0;

    always @(posedge clk_27m) begin
        if (!btn_s1) begin
            por_cnt    <= 5'd0;
            sys_resetn <= 1'b0;
        end else if (por_cnt < 5'd16) begin
            por_cnt    <= por_cnt + 1'b1;
            sys_resetn <= 1'b0;
        end else begin
            sys_resetn <= 1'b1;
        end
    end

    // -------------------------------------------------------------
    // 2. Tín hiệu bus bộ nhớ của PicoRV32
    // -------------------------------------------------------------
    wire        mem_valid;
    wire        mem_instr;
    wire        mem_ready;
    wire [31:0] mem_addr;
    wire [31:0] mem_wdata;
    wire [3:0]  mem_wstrb;
    wire [31:0] mem_rdata;

    // -------------------------------------------------------------
    // 3. PicoRV32 CPU Core
    // -------------------------------------------------------------
    picorv32 #(
        .ENABLE_COUNTERS   (1),
        .ENABLE_COUNTERS64 (1),
        .ENABLE_MUL        (0),
        .ENABLE_DIV        (0),
        .ENABLE_FAST_MUL   (0),
        .ENABLE_PCPI       (0),
        .COMPRESSED_ISA    (0),
        .PROGADDR_RESET    (32'h0000_0000),
        .STACKADDR         (32'h0000_8000) // Đỉnh BRAM 32 KB
    ) cpu (
        .clk         (clk_27m),
        .resetn      (sys_resetn),
        .trap        (),
        .mem_valid   (mem_valid),
        .mem_instr   (mem_instr),
        .mem_ready   (mem_ready),
        .mem_addr    (mem_addr),
        .mem_wdata   (mem_wdata),
        .mem_wstrb   (mem_wstrb),
        .mem_rdata   (mem_rdata),
        .mem_la_read (),
        .mem_la_write(),
        .mem_la_addr (),
        .mem_la_wdata(),
        .mem_la_wstrb(),
        .pcpi_valid  (),
        .pcpi_insn   (),
        .pcpi_rs1    (),
        .pcpi_rs2    (),
        .pcpi_wr     (1'b0),
        .pcpi_rd     (32'd0),
        .pcpi_wait   (1'b0),
        .pcpi_ready  (1'b0),
        .irq         (32'd0),
        .eoi         (),
        .trace_valid (),
        .trace_data  ()
    );

    // -------------------------------------------------------------
    // 4. Giải mã địa chỉ (Memory-mapped IO)
    //    0x0000_0000 - 0x0000_7FFF: BRAM 32 KB
    //    0x1000_0000: UART TX (ghi byte)
    //    0x1000_0004: UART STATUS (bit 0 = bận)
    //    0x2000_0000: LED (6 bit thấp)
    // -------------------------------------------------------------
    wire sel_bram        = (mem_addr[31:15] == 17'd0);
    wire sel_uart        = (mem_addr[31:28] == 4'h1);
    wire sel_uart_tx     = sel_uart && (mem_addr[7:0] == 8'h00);
    wire sel_uart_status = sel_uart && (mem_addr[7:0] == 8'h04);
    wire sel_led         = (mem_addr[31:28] == 4'h2);
    wire sel_invalid     = !(sel_bram || sel_uart || sel_led);

    // -------------------------------------------------------------
    // 5. Khối BRAM (32 KB)
    // -------------------------------------------------------------
    wire        bram_ready;
    wire [31:0] bram_rdata;
    wire        bram_valid = mem_valid && sel_bram;

    bram #(
        .WORDS     (8192),
        .INIT_FILE (INIT_FILE)
    ) ram (
        .clk       (clk_27m),
        .resetn    (sys_resetn),
        .mem_valid (bram_valid),
        .mem_addr  (mem_addr),
        .mem_wdata (mem_wdata),
        .mem_wstrb (mem_wstrb),
        .mem_ready (bram_ready),
        .mem_rdata (bram_rdata)
    );

    // -------------------------------------------------------------
    // 6. Khối UART TX
    // -------------------------------------------------------------
    reg        uart_ready;
    reg        uart_tx_start;
    reg [7:0]  uart_tx_data;
    wire       uart_busy;

    uart_tx #(
        .CLK_FREQ  (27000000),
        .BAUD_RATE (115200)
    ) u_uart_tx (
        .clk      (clk_27m),
        .resetn   (sys_resetn),
        .tx_start (uart_tx_start),
        .tx_data  (uart_tx_data),
        .tx       (uart_tx_pin),
        .busy     (uart_busy)
    );

    always @(posedge clk_27m) begin
        if (!sys_resetn) begin
            uart_ready    <= 1'b0;
            uart_tx_start <= 1'b0;
            uart_tx_data  <= 8'd0;
        end else begin
            uart_tx_start <= 1'b0;
            uart_ready    <= 1'b0;
            if (mem_valid && sel_uart && !uart_ready) begin
                uart_ready <= 1'b1;
                if (sel_uart_tx && |mem_wstrb) begin
                    uart_tx_data  <= mem_wdata[7:0];
                    uart_tx_start <= 1'b1;
                end
            end
        end
    end

    // -------------------------------------------------------------
    // 7. Khối điều khiển LED
    // -------------------------------------------------------------
    reg [5:0] led_reg;
    reg       led_ready;

    always @(posedge clk_27m) begin
        if (!sys_resetn) begin
            led_reg   <= 6'd0;
            led_ready <= 1'b0;
        end else begin
            led_ready <= 1'b0;
            if (mem_valid && sel_led && !led_ready) begin
                led_ready <= 1'b1;
                if (|mem_wstrb) begin
                    led_reg <= mem_wdata[5:0];
                end
            end
        end
    end

    // LED trên Tang Nano 20K tích cực thấp (Active-Low: 0 sáng, 1 tắt)
    assign led = ~led_reg;

    // -------------------------------------------------------------
    // 8. Xử lý địa chỉ không hợp lệ (không treo CPU)
    // -------------------------------------------------------------
    reg invalid_ready;

    always @(posedge clk_27m) begin
        if (!sys_resetn) begin
            invalid_ready <= 1'b0;
        end else begin
            invalid_ready <= 1'b0;
            if (mem_valid && sel_invalid && !invalid_ready) begin
                invalid_ready <= 1'b1;
            end
        end
    end

    // -------------------------------------------------------------
    // 9. Ghép nối tín hiệu bus phản hồi về CPU
    // -------------------------------------------------------------
    assign mem_ready = (sel_bram)    ? bram_ready :
                       (sel_uart)    ? uart_ready :
                       (sel_led)     ? led_ready :
                                       invalid_ready;

    assign mem_rdata = (sel_bram)        ? bram_rdata :
                       (sel_uart_status) ? {31'd0, uart_busy} :
                       (sel_led)         ? {26'd0, led_reg} :
                                           32'd0;

endmodule
