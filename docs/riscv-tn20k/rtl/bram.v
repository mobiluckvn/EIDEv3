`timescale 1ns / 1ps

module bram #(
    parameter WORDS = 8192,             // 32 KB = 8192 từ 32-bit (32768 byte)
    parameter INIT_FILE = ""
) (
    input  wire        clk,
    input  wire        resetn,

    // Port A: Bus CPU PicoRV32
    input  wire        mem_valid,
    input  wire [31:0] mem_addr,
    input  wire [31:0] mem_wdata,
    input  wire [3:0]  mem_wstrb,
    output reg         mem_ready,
    output reg  [31:0] mem_rdata,

    // Port B: Đơn vị Vector Nấc 3c (hoặc master phụ)
    input  wire        b_en,
    input  wire [31:0] b_addr,
    input  wire [31:0] b_wdata,
    input  wire [3:0]  b_wstrb,
    output reg  [31:0] b_rdata
);

    // Mảng bộ nhớ 32 KB (8192 từ 32-bit)
    reg [31:0] mem [0:WORDS-1];
    wire [12:0] word_addr_a = mem_addr[14:2];
    wire [12:0] word_addr_b = b_addr[14:2];

    initial begin
        if (INIT_FILE != "") begin
            $readmemh(INIT_FILE, mem);
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            mem_ready <= 1'b0;
            mem_rdata <= 32'd0;
            b_rdata   <= 32'd0;
        end else begin
            // Port A
            mem_ready <= 1'b0;
            if (mem_valid && !mem_ready) begin
                mem_ready <= 1'b1;
                mem_rdata <= mem[word_addr_a];
                if (mem_wstrb[0]) mem[word_addr_a][ 7: 0] <= mem_wdata[ 7: 0];
                if (mem_wstrb[1]) mem[word_addr_a][15: 8] <= mem_wdata[15: 8];
                if (mem_wstrb[2]) mem[word_addr_a][23:16] <= mem_wdata[23:16];
                if (mem_wstrb[3]) mem[word_addr_a][31:24] <= mem_wdata[31:24];
            end

            // Port B
            if (b_en) begin
                b_rdata <= mem[word_addr_b];
                if (b_wstrb[0]) mem[word_addr_b][ 7: 0] <= b_wdata[ 7: 0];
                if (b_wstrb[1]) mem[word_addr_b][15: 8] <= b_wdata[15: 8];
                if (b_wstrb[2]) mem[word_addr_b][23:16] <= b_wdata[23:16];
                if (b_wstrb[3]) mem[word_addr_b][31:24] <= b_wdata[31:24];
            end
        end
    end

endmodule
