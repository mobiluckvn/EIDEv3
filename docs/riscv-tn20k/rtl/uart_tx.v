`timescale 1ns / 1ps

module uart_tx #(
    parameter CLK_FREQ  = 27000000,
    parameter BAUD_RATE = 115200
) (
    input  wire       clk,
    input  wire       resetn,
    input  wire       tx_start,
    input  wire [7:0] tx_data,
    output reg        tx,
    output wire       busy
);

    localparam [15:0] CLK_DIV = 16'(CLK_FREQ / BAUD_RATE); // 27000000 / 115200 ≈ 234

    localparam [1:0]
        STATE_IDLE  = 2'd0,
        STATE_START = 2'd1,
        STATE_DATA  = 2'd2,
        STATE_STOP  = 2'd3;

    reg [1:0]  state;
    reg [15:0] baud_cnt;
    reg [2:0]  bit_cnt;
    reg [7:0]  shift_reg;

    assign busy = (state != STATE_IDLE);

    always @(posedge clk) begin
        if (!resetn) begin
            state     <= STATE_IDLE;
            baud_cnt  <= 16'd0;
            bit_cnt   <= 3'd0;
            shift_reg <= 8'd0;
            tx        <= 1'b1;
        end else begin
            case (state)
                STATE_IDLE: begin
                    tx       <= 1'b1;
                    baud_cnt <= 16'd0;
                    bit_cnt  <= 3'd0;
                    if (tx_start) begin
                        shift_reg <= tx_data;
                        state     <= STATE_START;
                    end
                end

                STATE_START: begin
                    tx <= 1'b0; // start bit
                    if (baud_cnt == CLK_DIV - 1) begin
                        baud_cnt <= 16'd0;
                        state    <= STATE_DATA;
                    end else begin
                        baud_cnt <= baud_cnt + 1'b1;
                    end
                end

                STATE_DATA: begin
                    tx <= shift_reg[0];
                    if (baud_cnt == CLK_DIV - 1) begin
                        baud_cnt  <= 16'd0;
                        shift_reg <= {1'b0, shift_reg[7:1]};
                        if (bit_cnt == 3'd7) begin
                            state <= STATE_STOP;
                        end else begin
                            bit_cnt <= bit_cnt + 1'b1;
                        end
                    end else begin
                        baud_cnt <= baud_cnt + 1'b1;
                    end
                end

                STATE_STOP: begin
                    tx <= 1'b1; // stop bit
                    if (baud_cnt == CLK_DIV - 1) begin
                        baud_cnt <= 16'd0;
                        state    <= STATE_IDLE;
                    end else begin
                        baud_cnt <= baud_cnt + 1'b1;
                    end
                end

                default: begin
                    state <= STATE_IDLE;
                end
            endcase
        end
    end

endmodule
