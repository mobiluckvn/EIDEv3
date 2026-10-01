`timescale 1ns / 1ps

module pcpi_mac (
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

    wire is_our_insn = is_acc_clr || is_mac || is_acc_rd;

    // -------------------------------------------------------------
    // Thanh ghi tích luỹ acc (32-bit)
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
