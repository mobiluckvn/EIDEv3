// reset_gen.v
// Bộ tạo tín hiệu reset đồng bộ: trễ khởi động (Power-on Reset) và nút nhấn S1
// Tang Nano 20K: btn_s1 tích cực mức thấp (nhấn nút = 0)
`timescale 1ns / 1ps

module reset_gen #(
    parameter POR_CYCLES = 64
)(
    input  wire clk,
    input  wire btn_s1,
    output wire rst_n,
    output wire [7:0] por_cnt_out,
    output wire por_done_out
);

    // Đồng bộ hoá nút nhấn btn_s1 qua 2 tầng flip-flop
    reg btn_s1_sync1 = 1'b0;
    reg btn_s1_sync2 = 1'b0;

    always @(posedge clk) begin
        btn_s1_sync1 <= btn_s1;
        btn_s1_sync2 <= btn_s1_sync1;
    end

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

    // Theo ADR-01: Bỏ nút S1 khỏi điều kiện giải phóng rst_n, chỉ giữ bộ đếm POR
    assign rst_n = por_done;
    assign por_cnt_out = por_cnt;
    assign por_done_out = por_done;

endmodule
