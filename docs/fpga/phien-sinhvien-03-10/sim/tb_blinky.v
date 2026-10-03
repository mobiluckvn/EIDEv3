`timescale 1ns / 1ps
`include "rtl/blinky.v"
module tb_blinky;
    reg clk = 0;
    reg btn_s1 = 0;
    wire [5:0] led;

    blinky uut (
        .clk(clk),
        .btn_s1(btn_s1),
        .led(led)
    );

    always #18.5 clk = ~clk; // ~27 MHz (37.037 ns)

    initial begin
        #100;
        btn_s1 = 1;
        #200;
        $display("PASS: tb_blinky initialized");
        $finish;
    end
endmodule
