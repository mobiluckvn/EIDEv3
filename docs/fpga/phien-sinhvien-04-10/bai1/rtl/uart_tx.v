// uart_tx.v
// Bộ phát UART TX: 8N1, mức nghỉ = 1, tham số hoá bộ chia baud theo clock
`timescale 1ns / 1ps

module uart_tx #(
    parameter CLK_FREQ = 27_000_000,
    parameter BAUD     = 115_200
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       tx_start,
    input  wire [7:0] tx_data,
    output wire       tx_busy,
    output reg        tx_serial
);

    localparam CLKS_PER_BIT = CLK_FREQ / BAUD;

    localparam STATE_IDLE = 1'b0;
    localparam STATE_TX   = 1'b1;

    reg state;
    reg [15:0] clk_cnt;
    reg [3:0]  bit_idx;
    reg [9:0]  tx_shifter; // {stop_bit(1), data[7:0], start_bit(0)}

    assign tx_busy = (state == STATE_TX);

    always @(posedge clk) begin
        if (!rst_n) begin
            state      <= STATE_IDLE;
            clk_cnt    <= 16'd0;
            bit_idx    <= 4'd0;
            tx_shifter <= 10'h3FF;
            tx_serial  <= 1'b1;
        end else begin
            case (state)
                STATE_IDLE: begin
                    tx_serial <= 1'b1;
                    clk_cnt   <= 16'd0;
                    bit_idx   <= 4'd0;
                    if (tx_start) begin
                        // Khung UART: 1 start bit (0), 8 bit dữ liệu LSB first, 1 stop bit (1)
                        tx_shifter <= {1'b1, tx_data, 1'b0};
                        state      <= STATE_TX;
                    end
                end

                STATE_TX: begin
                    tx_serial <= tx_shifter[0];
                    if (clk_cnt < CLKS_PER_BIT - 1) begin
                        clk_cnt <= clk_cnt + 16'd1;
                    end else begin
                        clk_cnt <= 16'd0;
                        tx_shifter <= {1'b1, tx_shifter[9:1]};
                        if (bit_idx < 4'd9) begin
                            bit_idx <= bit_idx + 4'd1;
                        end else begin
                            state <= STATE_IDLE;
                        end
                    end
                end
            endcase
        end
    end

endmodule
