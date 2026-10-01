`timescale 1ns / 1ps

// Blinky test cho Sipeed Tang Nano 20K (Gowin GW2AR-18C)
// Clock 27 MHz, nhay LED0 (PIN 15, active-low) voi chu ky ~1s (0.5s sang, 0.5s toi)
module blinky (
    input  wire sys_clk,   // 27 MHz
    output wire [5:0] led  // Active-low: 0 = sang, 1 = toi
);

    reg [23:0] counter = 24'd0;
    reg        led_state = 1'b0;

    // 27.000.000 / 2 = 13.500.000 chu ky cho 0.5 giay
    always @(posedge sys_clk) begin
        if (counter >= 24'd13_499_999) begin
            counter <= 24'd0;
            led_state <= ~led_state;
        end else begin
            counter <= counter + 1'b1;
        end
    end

    // LED0 nhay, cac LED con lai tat (muc 1)
    assign led = {5'b11111, led_state};

endmodule
