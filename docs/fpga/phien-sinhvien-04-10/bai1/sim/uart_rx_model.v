// uart_rx_model.v
// Bộ thu giải mã UART mô hình phục vụ testbench tự động
`timescale 1ns / 1ps

module uart_rx_model #(
    parameter CLK_FREQ = 27_000_000,
    parameter BAUD     = 115_200
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       rx_serial,
    output reg        rx_valid,
    output reg  [7:0] rx_byte
);

    localparam CLKS_PER_BIT = CLK_FREQ / BAUD;

    localparam STATE_IDLE  = 2'd0;
    localparam STATE_START = 2'd1;
    localparam STATE_DATA  = 2'd2;
    localparam STATE_STOP  = 2'd3;

    reg [1:0]  state = STATE_IDLE;
    reg [15:0] clk_cnt = 16'd0;
    reg [2:0]  bit_idx = 3'd0;
    reg [7:0]  rx_shifter = 8'd0;

    // Lọc khử metastability (mặc định mức nghỉ UART là 1)
    reg rx_sync1 = 1'b1;
    reg rx_sync2 = 1'b1;
    always @(posedge clk) begin
        rx_sync1 <= rx_serial;
        rx_sync2 <= rx_sync1;
    end

    always @(posedge clk) begin
        if (!rst_n) begin
            state      <= STATE_IDLE;
            clk_cnt    <= 16'd0;
            bit_idx    <= 3'd0;
            rx_shifter <= 8'd0;
            rx_valid   <= 1'b0;
            rx_byte    <= 8'd0;
        end else begin
            rx_valid <= 1'b0;

            case (state)
                STATE_IDLE: begin
                    clk_cnt <= 16'd0;
                    bit_idx <= 3'd0;
                    if (!rx_sync2) begin // Cạnh xuống start bit
                        state <= STATE_START;
                    end
                end

                STATE_START: begin
                    // Lấy mẫu ở giữa bit start
                    if (clk_cnt == (CLKS_PER_BIT / 2)) begin
                        if (!rx_sync2) begin
                            clk_cnt <= 16'd0;
                            state   <= STATE_DATA;
                        end else begin
                            state   <= STATE_IDLE; // Nhiễu giả
                        end
                    end else begin
                        clk_cnt <= clk_cnt + 16'd1;
                    end
                end

                STATE_DATA: begin
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt <= 16'd0;
                        rx_shifter[bit_idx] <= rx_sync2;
                        if (bit_idx == 3'd7) begin
                            state <= STATE_STOP;
                        end else begin
                            bit_idx <= bit_idx + 3'd1;
                        end
                    end else begin
                        clk_cnt <= clk_cnt + 16'd1;
                    end
                end

                STATE_STOP: begin
                    // Lấy mẫu giữa stop bit để sẵn sàng bắt cạnh xuống của byte tiếp theo
                    if (clk_cnt == (CLKS_PER_BIT / 2)) begin
                        clk_cnt  <= 16'd0;
                        state    <= STATE_IDLE;
                        rx_byte  <= rx_shifter;
                        rx_valid <= 1'b1;
                        // In ký tự trực tiếp ra màn hình console mô phỏng (chỉ in ASCII hợp lệ)
                        if ((rx_shifter >= 8'd32 && rx_shifter < 8'd127) || rx_shifter == 8'd10 || rx_shifter == 8'd13)
                            $write("%c", rx_shifter);
                        else
                            $write("?");
                        $fflush();
                    end else begin
                        clk_cnt <= clk_cnt + 16'd1;
                    end
                end
                default: begin
                    state   <= STATE_IDLE;
                    clk_cnt <= 16'd0;
                end
            endcase
        end
    end

endmodule
