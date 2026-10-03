`timescale 1ns / 1ps

`include "third_party/picorv32/picorv32.v"

module soc_top #(
    parameter INIT_FILE       = ".eide/build/mach.hex",
    parameter ENABLE_MUL      = 0,
    parameter ENABLE_FAST_MUL = 0,
    parameter ENABLE_PCPI     = 0,
    parameter DIAG_LEDS       = 0  // 0 = Bản giao: tắt LED chẩn đoán, hoàn trả nguyên trạng 6 LED cho CPU; 1 = Chẩn đoán
) (
    input  wire       clk_27m,      // Thạch anh 27 MHz (PIN 4)
    input  wire       btn_s1,       // Nút S1 (PIN 88, không dùng trong reset theo ADR-05)
    output wire       uart_tx_pin,  // UART TX nối BL616 (PIN 69)
    output wire [5:0] led           // 6 LED trên bo (PIN 15..20, Active-Low)
);

    // -------------------------------------------------------------
    // 1. Mạch tạo tín hiệu Reset (Theo quyết định kiến trúc ADR-05)
    //    Giữ reset 16 chu kỳ clk_27m sau cấp nguồn / nạp bitstream (POR).
    //    Cô lập nút S1 (PIN 88) vì chân này bị kẹp 0 trên bo vật lý.
    // -------------------------------------------------------------
    reg [4:0] por_cnt = 5'd0;
    reg       sys_resetn = 1'b0;

    always @(posedge clk_27m) begin
        if (por_cnt < 5'd16) begin
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
    // 3. PicoRV32 CPU Core và PCPI Co-processor
    // -------------------------------------------------------------
    wire        pcpi_valid;
    wire [31:0] pcpi_insn;
    wire [31:0] pcpi_rs1;
    wire [31:0] pcpi_rs2;
    wire        pcpi_wr;
    wire [31:0] pcpi_rd;
    wire        pcpi_wait;
    wire        pcpi_ready;

    picorv32 #(
        .ENABLE_COUNTERS   (1),
        .ENABLE_COUNTERS64 (1),
        .ENABLE_MUL        (ENABLE_MUL),
        .ENABLE_DIV        (0),
        .ENABLE_FAST_MUL   (ENABLE_FAST_MUL),
        .ENABLE_PCPI       (ENABLE_PCPI),
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
        .pcpi_valid  (pcpi_valid),
        .pcpi_insn   (pcpi_insn),
        .pcpi_rs1    (pcpi_rs1),
        .pcpi_rs2    (pcpi_rs2),
        .pcpi_wr     (pcpi_wr),
        .pcpi_rd     (pcpi_rd),
        .pcpi_wait   (pcpi_wait),
        .pcpi_ready  (pcpi_ready),
        .irq         (32'd0),
        .eoi         (),
        .trace_valid (),
        .trace_data  ()
    );

    // Không có khối đồng xử lý ngoài. Vẫn giữ các dây PCPI và buộc chúng về mức không
    // tích cực, chứ không bỏ hẳn: `picorv32` nhận chúng là cổng vào, và `pcpi_wait` thả nổi
    // thì CPU có thể treo vĩnh viễn ở một lệnh nó không hiểu — một kiểu hỏng không hiện ra
    // lúc mô phỏng nếu chương trình không dùng lệnh lạ nào.
    assign pcpi_wr    = 1'b0;
    assign pcpi_rd    = 32'd0;
    assign pcpi_wait  = 1'b0;
    assign pcpi_ready = 1'b0;

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

    // Bộ đếm tạo xung nháy LED5 từ clk_27m (độc lập với reset và CPU)
    // 27 MHz / 2^24 ≈ 1.61 Hz (nháy ~0.62 s, mắt thường nhìn rõ)
    reg [23:0] diag_clk_cnt = 24'd0;
    always @(posedge clk_27m) begin
        diag_clk_cnt <= diag_clk_cnt + 1'b1;
    end

    // LED trên Tang Nano 20K tích cực thấp (Active-Low: 0 sáng, 1 tắt)
    // Khi DIAG_LEDS = 1:
    //   - led[5]: nháy theo clock (độc lập với reset và CPU)
    //   - led[4]: sáng khi sys_resetn = 1 (CPU đã thoát reset)
    //   - led[3:0]: 4 bit thấp do CPU ghi (0x2000_0000)
    // Khi DIAG_LEDS = 0: hoàn trả trọn vẹn 6 bit led cho CPU ghi (~led_reg)
    wire [5:0] led_diag = {
        diag_clk_cnt[23],
        ~sys_resetn,
        ~led_reg[3:0]
    };

    assign led = (DIAG_LEDS) ? led_diag : ~led_reg;

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
