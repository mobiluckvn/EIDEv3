// soc_top.v
// Khối đỉnh toàn SoC Bài 1 cho bo Sipeed Tang Nano 20K (Gowin GW2AR-LV18QN88C8)
`timescale 1ns / 1ps
`include "../../tai-lieu/picorv32.v"

// Cờ dựng bản chẩn đoán (Diagnostic Build):
// Mặc định thiết kế của Bài 1 & Bài 2 là TẮT (DIAG_ENABLE = 0).
// Khi cần chẩn đoán phần cứng bo mạch, bật `define DIAG_BUILD 1 để truyền 1 vào parameter DIAG_ENABLE.
// `define DIAG_BUILD 1

module soc_top #(
    parameter CLK_FREQ    = 27_000_000,
    parameter BAUD        = 115_200,
    parameter HEX_FILE    = "/Users/congvt/Documents/EIDE_v3/du-lieu/fpga-sinhvien/firmware.hex",
`ifdef DIAG_BUILD
    parameter DIAG_ENABLE = 1
`else
    parameter DIAG_ENABLE = 0
`endif
)(
    input  wire       clk,
    input  wire       btn_s1,
    output wire       uart_tx,
    output wire [5:0] led
);

    // Khối Reset đồng bộ kết hợp Power-on Reset và nút S1
    wire rst_n;
    wire [7:0] por_cnt_val;
    wire       por_done_val;
    reset_gen #(
        .POR_CYCLES(64)
    ) u_reset_gen (
        .clk(clk),
        .btn_s1(btn_s1),
        .rst_n(rst_n),
        .por_cnt_out(por_cnt_val),
        .por_done_out(por_done_val)
    );

    // Tín hiệu bus PicoRV32
    wire        cpu_trap;
    wire        cpu_mem_valid;
    wire        cpu_mem_instr;
    wire        cpu_mem_ready;
    wire [31:0] cpu_mem_addr;
    wire [31:0] cpu_mem_wdata;
    wire [3:0]  cpu_mem_wstrb;
    wire [31:0] cpu_mem_rdata;

    // Lõi PicoRV32 (RV32I_Zicsr)
    picorv32 #(
        .ENABLE_COUNTERS   (1),
        .ENABLE_COUNTERS64 (1),
        .ENABLE_MUL        (0),
        .ENABLE_DIV        (0),
        .ENABLE_FAST_MUL   (0),
        .ENABLE_PCPI       (0),
        .COMPRESSED_ISA    (0),
        .PROGADDR_RESET    (32'h0000_0000),
        .STACKADDR         (32'h0000_8000)   // Đỉnh 32 KB BRAM
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

    // Tín hiệu kết nối ngoại vi
    wire        bram_valid;
    wire        bram_ready;
    wire [31:0] bram_rdata;

    wire        uart_tx_start;
    wire [7:0]  uart_tx_data;
    wire        uart_busy;

    wire        led_we;
    wire [5:0]  led_wdata;

    // Bộ giải mã bus MMIO
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

    // Bộ nhớ BRAM 32 KB
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

    // Bộ phát UART TX hoạt động bình thường của SoC
    wire normal_uart_tx;
    uart_tx #(
        .CLK_FREQ (CLK_FREQ),
        .BAUD     (BAUD)
    ) u_uart_tx (
        .clk       (clk),
        .rst_n     (rst_n),
        .tx_start  (uart_tx_start),
        .tx_data   (uart_tx_data),
        .tx_busy   (uart_busy),
        .tx_serial (normal_uart_tx)
    );

    // Điều khiển 6 LED ngoài (chế độ bình thường)
    wire [5:0] normal_led;
    gpio_led u_gpio_led (
        .clk       (clk),
        .rst_n     (rst_n),
        .led_we    (led_we),
        .led_wdata (led_wdata),
        .led_n     (normal_led)
    );

    // -------------------------------------------------------------
    // Chế độ chẩn đoán phần cứng (Diagnostic Mode)
    // DIAG_ENABLE = 0: Mặc định TẮT cho Bài 2 (zero overhead, dead-code eliminated)
    // DIAG_ENABLE = 1: BẬT để phân lập nguyên nhân bo tối bằng LED & UART
    // -------------------------------------------------------------
    generate
        if (DIAG_ENABLE) begin : gen_diag
            // POR độc lập cho mạch chẩn đoán: đảm bảo mạch chạy ngay cả khi rst_n bị kẹt
            reg [7:0] diag_por_cnt = 8'd0;
            reg       diag_por_done = 1'b0;
            always @(posedge clk) begin
                if (!diag_por_done) begin
                    if (diag_por_cnt < 8'd64) diag_por_cnt <= diag_por_cnt + 8'd1;
                    else                      diag_por_done <= 1'b1;
                end
            end
            wire diag_rst_n = diag_por_done;

            // LED0: Heartbeat nhấp nháy ~0.8s (bit 24 của bộ đếm 27 MHz)
            reg [24:0] hb_cnt;
            always @(posedge clk or negedge diag_rst_n) begin
                if (!diag_rst_n) hb_cnt <= 25'd0;
                else             hb_cnt <= hb_cnt + 1'b1;
            end
            wire diag_led0 = hb_cnt[24];

            // LED1: rst_n (1 = bình thường -> sáng; nhấn nút S1 thì rst_n = 0 -> tắt)
            wire diag_led1 = rst_n;

            // LED2: Chốt bẫy lỗi CPU (cpu_trap)
            reg trap_latched;
            always @(posedge clk or negedge diag_rst_n) begin
                if (!diag_rst_n)     trap_latched <= 1'b0;
                else if (cpu_trap)   trap_latched <= 1'b1;
            end
            wire diag_led2 = trap_latched;

            // LED3: Bộ dò bus hang - đếm mem_valid giữ > 64 chu kỳ mà không có mem_ready
            reg [6:0] hang_cnt;
            reg       hang_latched;
            always @(posedge clk or negedge diag_rst_n) begin
                if (!diag_rst_n) begin
                    hang_cnt     <= 7'd0;
                    hang_latched <= 1'b0;
                end else if (cpu_mem_valid && !cpu_mem_ready) begin
                    if (hang_cnt < 7'd64) begin
                        hang_cnt <= hang_cnt + 1'b1;
                    end else begin
                        hang_latched <= 1'b1; // Chốt lỗi treo bus
                    end
                end else begin
                    hang_cnt <= 7'd0;
                end
            end
            wire diag_led3 = hang_latched;

            // LED4: mem_valid (CPU đang truy cập bus)
            wire diag_led4 = cpu_mem_valid;

            // LED5: bram_ready chốt (CPU truy cập BRAM thành công ít nhất một lần)
            reg bram_ready_latched;
            always @(posedge clk or negedge diag_rst_n) begin
                if (!diag_rst_n)      bram_ready_latched <= 1'b0;
                else if (bram_ready)  bram_ready_latched <= 1'b1;
            end
            wire diag_led5 = bram_ready_latched;

            // LED trên bo Tang Nano 20K tích cực mức thấp (0 = SÁNG, 1 = TẮT)
            assign led = ~{diag_led5, diag_led4, diag_led3, diag_led2, diag_led1, diag_led0};

            // ---------------------------------------------------------
            // Bộ phát UART chẩn đoán tự động độc lập (đọc được bằng máy)
            // Định kỳ mỗi 0.5s phát chuỗi: "[DIAG] R:x S:x C:xx T:x H:x B:x\r\n"
            // R: rst_n, S: btn_s1 thô (chân 88), C: por_cnt (hex)
            // T: trap_latched, H: hang_latched, B: bram_ready_latched
            // ---------------------------------------------------------
            function [7:0] hex_char;
                input [3:0] nibble;
                begin
                    if (nibble < 4'd10)
                        hex_char = 8'h30 + {4'd0, nibble};
                    else
                        hex_char = 8'h41 + {4'd0, (nibble - 4'd10)};
                end
            endfunction

            wire       diag_tx_busy;
            reg        diag_tx_start;
            reg [7:0]  diag_tx_data;
            wire       diag_tx_serial;

            uart_tx #(
                .CLK_FREQ (CLK_FREQ),
                .BAUD     (BAUD)
            ) u_diag_uart_tx (
                .clk       (clk),
                .rst_n     (diag_rst_n),
                .tx_start  (diag_tx_start),
                .tx_data   (diag_tx_data),
                .tx_busy   (diag_tx_busy),
                .tx_serial (diag_tx_serial)
            );

            reg [23:0] timer_cnt;
            reg [5:0]  char_idx;
            reg        diag_transmitting;

            always @(posedge clk or negedge diag_rst_n) begin
                if (!diag_rst_n) begin
                    timer_cnt         <= 24'd0;
                    char_idx          <= 6'd0;
                    diag_transmitting <= 1'b0;
                    diag_tx_start     <= 1'b0;
                    diag_tx_data      <= 8'd0;
                end else begin
                    diag_tx_start <= 1'b0;

                    if (!diag_transmitting) begin
                        if (timer_cnt >= 24'd13_500_000) begin // 0.5 giây ở 27 MHz
                            timer_cnt         <= 24'd0;
                            char_idx          <= 6'd0;
                            diag_transmitting <= 1'b1;
                        end else begin
                            timer_cnt <= timer_cnt + 24'd1;
                        end
                    end else begin
                        if (!diag_tx_busy && !diag_tx_start) begin
                            diag_tx_start <= 1'b1;
                            case (char_idx)
                                6'd0:  diag_tx_data <= 8'h5B; // '['
                                6'd1:  diag_tx_data <= 8'h44; // 'D'
                                6'd2:  diag_tx_data <= 8'h49; // 'I'
                                6'd3:  diag_tx_data <= 8'h41; // 'A'
                                6'd4:  diag_tx_data <= 8'h47; // 'G'
                                6'd5:  diag_tx_data <= 8'h5D; // ']'
                                6'd6:  diag_tx_data <= 8'h20; // ' '
                                6'd7:  diag_tx_data <= 8'h52; // 'R'
                                6'd8:  diag_tx_data <= 8'h3A; // ':'
                                6'd9:  diag_tx_data <= rst_n ? 8'h31 : 8'h30;
                                6'd10: diag_tx_data <= 8'h20; // ' '
                                6'd11: diag_tx_data <= 8'h53; // 'S'
                                6'd12: diag_tx_data <= 8'h3A; // ':'
                                6'd13: diag_tx_data <= btn_s1 ? 8'h31 : 8'h30;
                                6'd14: diag_tx_data <= 8'h20; // ' '
                                6'd15: diag_tx_data <= 8'h43; // 'C'
                                6'd16: diag_tx_data <= 8'h3A; // ':'
                                6'd17: diag_tx_data <= hex_char(por_cnt_val[7:4]);
                                6'd18: diag_tx_data <= hex_char(por_cnt_val[3:0]);
                                6'd19: diag_tx_data <= 8'h20; // ' '
                                6'd20: diag_tx_data <= 8'h54; // 'T'
                                6'd21: diag_tx_data <= 8'h3A; // ':'
                                6'd22: diag_tx_data <= trap_latched ? 8'h31 : 8'h30;
                                6'd23: diag_tx_data <= 8'h20; // ' '
                                6'd24: diag_tx_data <= 8'h48; // 'H'
                                6'd25: diag_tx_data <= 8'h3A; // ':'
                                6'd26: diag_tx_data <= hang_latched ? 8'h31 : 8'h30;
                                6'd27: diag_tx_data <= 8'h20; // ' '
                                6'd28: diag_tx_data <= 8'h42; // 'B'
                                6'd29: diag_tx_data <= 8'h3A; // ':'
                                6'd30: diag_tx_data <= bram_ready_latched ? 8'h31 : 8'h30;
                                6'd31: diag_tx_data <= 8'h0D; // '\r'
                                6'd32: diag_tx_data <= 8'h0A; // '\n'
                                default: diag_tx_data <= 8'h0A;
                            endcase

                            if (char_idx == 6'd32) begin
                                diag_transmitting <= 1'b0;
                                char_idx          <= 6'd0;
                            end else begin
                                char_idx <= char_idx + 6'd1;
                            end
                        end
                    end
                end
            end

            assign uart_tx = diag_tx_serial;

        end else begin : gen_normal
            // Hoạt động thông thường của Bài 1 & Bài 2: nối thẳng từ gpio_led và uart_tx
            assign led     = normal_led;
            assign uart_tx = normal_uart_tx;
        end
    endgenerate

endmodule
