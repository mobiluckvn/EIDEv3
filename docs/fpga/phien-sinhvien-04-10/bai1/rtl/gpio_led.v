// gpio_led.v
// Thanh ghi điều khiển 6 LED ngoài bo Tang Nano 20K (chân 15-20, tích cực thấp)
`timescale 1ns / 1ps

module gpio_led (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       led_we,
    input  wire [5:0] led_wdata,
    output wire [5:0] led_n
);

    reg [5:0] led_reg;

    always @(posedge clk) begin
        if (!rst_n) begin
            led_reg <= 6'b000000; // Mặc định tắt LED
        end else if (led_we) begin
            led_reg <= led_wdata;
        end
    end

    // LED trên bo Tang Nano 20K tích cực mức thấp (ghi 0 sáng đèn, ghi 1 tắt)
    // Tín hiệu nội bộ led_reg: 1 = BẬT, 0 = TẮT -> xuất ra chân đảo bit: led_n = ~led_reg
    assign led_n = ~led_reg;

endmodule
