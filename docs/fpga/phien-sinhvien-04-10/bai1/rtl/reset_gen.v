// reset_gen.v
// Bộ tạo tín hiệu Power-on Reset (POR) đồng bộ theo xung nhịp clk
// Giải phóng reset (rst_n = 1) sau khi đếm đủ POR_CYCLES chu kỳ
`timescale 1ns / 1ps

module reset_gen #(
    parameter POR_CYCLES = 64
)(
    input  wire clk,
    output wire rst_n,
    output wire [7:0] por_cnt_out,
    output wire por_done_out
);

    // Bộ đếm power-on reset
    reg [7:0] por_cnt = 8'd0;
    reg por_done = 1'b0;

    always @(posedge clk) begin
        if (!por_done) begin
            if (por_cnt < POR_CYCLES) begin
                por_cnt <= por_cnt + 8'd1;
                por_done <= 1'b0;
            end else begin
                por_done <= 1'b1;
            end
        end
    end

    // Theo ADR-01: rst_n tích cực thấp, điều khiển hoàn toàn bởi POR
    assign rst_n = por_done;
    assign por_cnt_out = por_cnt;
    assign por_done_out = por_done;

endmodule
