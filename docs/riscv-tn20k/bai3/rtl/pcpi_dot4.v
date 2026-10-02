`timescale 1ns / 1ps

module pcpi_dot4 (
    input  wire        clk,
    input  wire        resetn,

    // Giao diện Pico Co-Processor Interface (PCPI)
    input  wire        pcpi_valid,
    input  wire [31:0] pcpi_insn,
    input  wire [31:0] pcpi_rs1,
    input  wire [31:0] pcpi_rs2,
    output wire        pcpi_wr,
    output wire [31:0] pcpi_rd,
    output wire        pcpi_wait,
    output wire        pcpi_ready
);

    // -------------------------------------------------------------
    // Giải mã lệnh custom-0 (opcode = 7'b0001011, funct7 = 7'b0000000)
    // -------------------------------------------------------------
    wire [6:0] opcode = pcpi_insn[6:0];
    wire [2:0] funct3 = pcpi_insn[14:12];
    wire [6:0] funct7 = pcpi_insn[31:25];

    wire is_custom0 = pcpi_valid && (opcode == 7'b0001011) && (funct7 == 7'b0000000);

    wire is_acc_clr = is_custom0 && (funct3 == 3'b000);
    wire is_mac     = is_custom0 && (funct3 == 3'b001);
    wire is_acc_rd  = is_custom0 && (funct3 == 3'b010);
    wire is_dot4    = is_custom0 && (funct3 == 3'b011);

    wire is_our_insn = is_acc_clr || is_mac || is_acc_rd || is_dot4;

    // -------------------------------------------------------------
    // Bốn bộ nhân 8x8 có dấu cho lệnh dot4
    // rs1 và rs2 chứa 4 phần tử int8_t liên tiếp
    // -------------------------------------------------------------
    wire signed [7:0] a0 = pcpi_rs1[7:0];
    wire signed [7:0] a1 = pcpi_rs1[15:8];
    wire signed [7:0] a2 = pcpi_rs1[23:16];
    wire signed [7:0] a3 = pcpi_rs1[31:24];

    wire signed [7:0] b0 = pcpi_rs2[7:0];
    wire signed [7:0] b1 = pcpi_rs2[15:8];
    wire signed [7:0] b2 = pcpi_rs2[23:16];
    wire signed [7:0] b3 = pcpi_rs2[31:24];

    wire signed [15:0] prod0 = a0 * b0;
    wire signed [15:0] prod1 = a1 * b1;
    wire signed [15:0] prod2 = a2 * b2;
    wire signed [15:0] prod3 = a3 * b3;

    wire signed [31:0] dot4_sum = {{16{prod0[15]}}, prod0} +
                                  {{16{prod1[15]}}, prod1} +
                                  {{16{prod2[15]}}, prod2} +
                                  {{16{prod3[15]}}, prod3};

    // -------------------------------------------------------------
    // Thanh ghi tích luỹ acc (32-bit có dấu)
    // -------------------------------------------------------------
    reg signed [31:0] acc;

    always @(posedge clk) begin
        if (!resetn) begin
            acc <= 32'sd0;
        end else if (pcpi_valid) begin
            if (is_acc_clr) begin
                acc <= 32'sd0;
            end else if (is_mac) begin
                acc <= acc + ($signed(pcpi_rs1) * $signed(pcpi_rs2));
            end else if (is_dot4) begin
                acc <= acc + dot4_sum;
            end
        end
    end

    // -------------------------------------------------------------
    // Tín hiệu bắt tay PCPI:
    // Khối thực thi trong 1 chu kỳ, trả ready ngay khi pcpi_valid tích cực
    // -------------------------------------------------------------
    assign pcpi_ready = is_our_insn;
    assign pcpi_wait  = 1'b0;
    assign pcpi_wr    = is_acc_rd;
    assign pcpi_rd    = is_acc_rd ? acc : 32'd0;

endmodule
