`timescale 1ns / 1ps

`include "rtl/bram.v"
`include "rtl/uart_tx.v"
`include "rtl/soc_top.v"

module tb_bai2;

    reg clk;
    reg btn_s1;
    wire uart_tx_pin;
    wire [5:0] led;

    // Clock 27 MHz: chu kỳ ~ 37.037 ns (18.5185 ns mỗi nửa chu kỳ)
    initial begin
        clk = 0;
        forever #18.5185 clk = ~clk;
    end

    // Khởi tạo SoC
    soc_top #(
        .INIT_FILE(".eide/build/mach.hex")
    ) uut (
        .clk_27m(clk),
        .btn_s1(btn_s1),
        .uart_tx_pin(uart_tx_pin),
        .led(led)
    );

    // Reset ban đầu và nạp mã BRAM
    initial begin
        btn_s1 = 0;
        $readmemh(".eide/build/mach.hex", uut.ram.mem);
        #200;
        btn_s1 = 1;
    end

    // Đếm chu kỳ clock và đặt hạn thời gian (Timeout theo chu kỳ)
    reg [63:0] cycle_count = 0;
    localparam [63:0] MAX_CYCLES = 64'd800_000_000; // 800 triệu chu kỳ (~30 giây CPU giả lập)

    integer result_count = 0;
    integer result_ok_count = 0;
    integer has_error = 0;

    always @(posedge clk) begin
        cycle_count <= cycle_count + 1;
        if (cycle_count >= MAX_CYCLES) begin
            $display("\n==========================================");
            $display("FAIL: Timeout vuot qua %0d chu ky! Thu duoc %0d dong RESULT (ok=%0d).",
                     cycle_count, result_count, result_ok_count);
            $display("==========================================");
            $finish;
        end
    end

    // Bộ thu UART: 115200 baud, 8N1
    localparam real BIT_PERIOD_NS = 1000000000.0 / 115200.0; // ~8680.555 ns

    reg [7:0] rx_byte;
    reg [7:0] line_buf [0:255];
    integer line_len = 0;

    // Hàm kiểm tra chuỗi con trong line_buf
    function automatic integer has_substring;
        input integer len;
        input [8*32-1:0] sub;
        input integer sub_len;
        integer i, j, match;
        reg [7:0] expected_char;
        begin
            has_substring = 0;
            if (len >= sub_len) begin
                for (i = 0; i <= len - sub_len; i = i + 1) begin
                    match = 1;
                    for (j = 0; j < sub_len; j = j + 1) begin
                        expected_char = sub[(sub_len - 1 - j)*8 +: 8];
                        if (line_buf[i + j] != expected_char) begin
                            match = 0;
                        end
                    end
                    if (match == 1) begin
                        has_substring = 1;
                    end
                end
            end
        end
    endfunction

    // Giám sát cổng UART TX
    initial begin
        $display("[TB_BAI2] Bat dau giam sat UART TX tai 115200 baud...");
        forever begin
            // 1. Chờ start bit (cạnh xuống)
            @(negedge uart_tx_pin);

            // 2. Lấy mẫu tại giữa start bit
            #(BIT_PERIOD_NS / 2.0);
            if (uart_tx_pin == 1'b0) begin
                // Đọc 8 bit dữ liệu
                #(BIT_PERIOD_NS); rx_byte[0] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[1] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[2] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[3] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[4] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[5] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[6] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[7] = uart_tx_pin;

                // Chờ giữa stop bit
                #(BIT_PERIOD_NS);

                // In ngay lập tức ra màn hình
                $write("%c", rx_byte);
                $fflush();

                // Lưu ký tự vào bộ đệm dòng
                if (rx_byte == 8'h0A) begin
                    // Kết thúc một dòng (ký tự newline '\n')
                    // 1. Kiểm tra nếu là dòng RESULT
                    if (has_substring(line_len, "RESULT,", 7)) begin
                        result_count = result_count + 1;
                        if (has_substring(line_len, "ok=1", 4)) begin
                            result_ok_count = result_ok_count + 1;
                        end else begin
                            has_error = 1;
                            $display("\n[TB_BAI2] PHAT HIEN KET QUA SAI (ok!=1) tai dong %0d!", result_count);
                        end
                    end

                    // 2. Kiểm tra nếu là dòng hoàn thành (DONE hoặc BENCHMARK COMPLETED)
                    if (has_substring(line_len, "DONE", 4) || has_substring(line_len, "BENCHMARK COMPLETED", 19)) begin
                        $display("\n==========================================");
                        if (result_count > 0 && !has_error && (result_ok_count == result_count)) begin
                            $display("PASS: Hoan tat %0d phep do, tat ca deu ok=1 tai chu ky %0d!", result_count, cycle_count);
                        end else begin
                            $display("FAIL: Hoan thanh nhung ket qua loi! result_count=%0d, ok_count=%0d, has_error=%0d",
                                     result_count, result_ok_count, has_error);
                        end
                        $display("==========================================");
                        $finish;
                    end

                    line_len = 0;
                end else if (rx_byte != 8'h0D) begin
                    if (line_len < 255) begin
                        line_buf[line_len] = rx_byte;
                        line_len = line_len + 1;
                    end
                end
            end
        end
    end

endmodule
