`timescale 1ns / 1ps

`include "rtl/bram.v"
`include "rtl/uart_tx.v"
`include "rtl/soc_top.v"

module tb_soc;

    reg clk;
    reg btn_s1;
    wire uart_tx_pin;
    wire [5:0] led;

    // Clock 27 MHz: T ~ 37.037 ns (18.5185 ns đảo mức)
    initial begin
        clk = 0;
        forever #18.5185 clk = ~clk;
    end

    // Dựng SoC
    soc_top #(
        .INIT_FILE(".eide/build/mach.hex")
    ) uut (
        .clk_27m(clk),
        .btn_s1(btn_s1),
        .uart_tx_pin(uart_tx_pin),
        .led(led)
    );

    // Reset: S1 nhấn (active-low = 0) trong 200 ns rồi nhả
    initial begin
        btn_s1 = 0;
        $readmemh(".eide/build/mach.hex", uut.ram.mem);
        #200;
        btn_s1 = 1;
    end

    // Bộ thu UART trong testbench: 115200 baud, 8N1
    localparam real BIT_PERIOD_NS = 1000000000.0 / 115200.0; // ~8680.555 ns

    reg [7:0] rx_byte;
    reg [7:0] rx_buf [0:1023];
    integer rx_count = 0;
    integer match_count = 0;

    // Bộ nhớ đệm 19 ký tự gần nhất để nhận dạng "Hello from PicoRV32"
    reg [8*19-1:0] shift_window = 0;
    localparam [8*19-1:0] TARGET_STR = "Hello from PicoRV32";

    // Tiến trình thu UART và kiểm tra chuỗi
    initial begin
        $display("[TB] Bat dau giam sat UART TX tai 115200 baud...");
        forever begin
            // 1. Chờ start bit (mép xuống)
            @(negedge uart_tx_pin);

            // 2. Lấy mẫu ở GIỮA start bit
            #(BIT_PERIOD_NS / 2.0);
            if (uart_tx_pin == 1'b0) begin
                // Start bit đúng, lần lượt đọc 8 bit dữ liệu tại giữa mỗi bit
                #(BIT_PERIOD_NS); rx_byte[0] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[1] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[2] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[3] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[4] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[5] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[6] = uart_tx_pin;
                #(BIT_PERIOD_NS); rx_byte[7] = uart_tx_pin;

                // Chờ tới giữa stop bit
                #(BIT_PERIOD_NS);

                // In ký tự ra console
                $write("%c", rx_byte);
                $fflush();

                // Lưu vào bộ đệm
                if (rx_count < 1024) begin
                    rx_buf[rx_count] = rx_byte;
                    rx_count = rx_count + 1;
                end

                // Cập nhật cửa sổ dịch 19 byte
                shift_window = {shift_window[8*18-1:0], rx_byte};

                if (shift_window == TARGET_STR) begin
                    match_count = match_count + 1;
                    $display("\n[TB] Khop chuoi 'Hello from PicoRV32' lan %0d tai thoi diem %0t ns", match_count, $time);
                    if (match_count >= 2) begin
                        $display("\n==========================================");
                        $display("PASS: Nhan dung 'Hello from PicoRV32' 2 lan!");
                        $display("==========================================");
                        $finish;
                    end
                end
            end
        end
    end

    // Giới hạn thời gian (Timeout): 25 ms
    initial begin
        #25_000_000;
        $display("\n==========================================");
        $display("FAIL: Timeout 25 ms! Chi nhan duoc chuoi %0d lan.", match_count);
        $write("Cac ky tu da nhan duoc (%0d byte): \"", rx_count);
        begin : dump_buf
            integer i;
            for (i = 0; i < rx_count; i = i + 1) begin
                $write("%c", rx_buf[i]);
            end
        end
        $display("\"");
        $display("==========================================");
        $finish;
    end

endmodule
