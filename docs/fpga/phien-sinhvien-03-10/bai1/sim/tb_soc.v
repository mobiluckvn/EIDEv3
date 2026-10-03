// tb_soc.v
// Testbench tự kiểm tra toàn SoC Bài 1
// Tự động in PASS khi nhận đúng chuỗi ít nhất 2 lần, FAIL sau thời gian giới hạn
`timescale 1ns / 1ps

module tb_soc;

    reg clk;
    reg btn_s1;
    wire uart_tx_line;
    wire [5:0] leds;

    // Chu kỳ 27 MHz: T ~ 37.037 ns -> nửa chu kỳ 18.518 ns
    initial begin
        clk = 1'b0;
        forever #18.518 clk = ~clk;
    end

    // Nút S1 tích cực mức thấp (mặc định không nhấn = 1)
    initial begin
        btn_s1 = 1'b1;
    end

    // Khởi tạo SoC
    soc_top #(
        .CLK_FREQ (27_000_000),
        .BAUD     (115_200),
        .HEX_FILE ("firmware.hex")
    ) u_dut (
        .clk     (clk),
        .btn_s1  (btn_s1),
        .uart_tx (uart_tx_line),
        .led     (leds)
    );

    // Bộ thu UART mô hình
    wire       rx_valid;
    wire [7:0] rx_byte;

    uart_rx_model #(
        .CLK_FREQ (27_000_000),
        .BAUD     (115_200)
    ) u_rx (
        .clk       (clk),
        .rst_n     (1'b1),
        .rx_serial (uart_tx_line),
        .rx_valid  (rx_valid),
        .rx_byte   (rx_byte)
    );

    // Giám sát chuỗi nhận được
    reg [8*40-1:0] shift_window = 0;
    integer match_count = 0;

    always @(posedge clk) begin
        if (rx_valid) begin
            shift_window <= {shift_window[8*39-1:0], rx_byte};
            // Kiểm tra khớp chuỗi tiền tố cốt lõi "Hello from PicoRV32 on Tang Nano 20K"
            if ({shift_window[8*34-1:0], rx_byte} == "Hello from PicoRV32 on Tang Nano 20K") begin
                match_count <= match_count + 1;
                $display("\n[TB] Phat hien chuoi lan thu %0d tai thoi diem %0t ns", match_count + 1, $time);
                if (match_count + 1 >= 2) begin
                    $display("\n==========================================");
                    $display("  KET QUA MO PHONG: PASS");
                    $display("  Da nhan dung chuoi it nhat 2 lan!");
                    $display("==========================================\n");
                    $finish;
                end
            end
        end
    end

    // Giới hạn thời gian (Timeout guard)
    initial begin
        // Trong chế độ SIM (hằng số delay 1000 chu kỳ), chuỗi in ra rất nhanh (~100-200 us mỗi chuỗi)
        // Thiết lập timeout 20 ms (20,000,000 ns) đủ dồi dào
        #20000000;
        $display("\n==========================================");
        $display("  KET QUA MO PHONG: FAIL");
        $display("  Het thoi gian cho (Timeout)! So lan nhan: %0d", match_count);
        $display("==========================================\n");
        $finish;
    end

endmodule
