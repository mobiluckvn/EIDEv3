`timescale 1ns / 1ps

module bram #(
    parameter WORDS = 8192,             // 32 KB = 8192 từ 32-bit (32768 byte)
    parameter INIT_FILE = ""
) (
    input  wire        clk,
    input  wire        resetn,
    input  wire        mem_valid,
    input  wire [31:0] mem_addr,
    input  wire [31:0] mem_wdata,
    input  wire [3:0]  mem_wstrb,
    output reg         mem_ready,
    output reg  [31:0] mem_rdata
);

    // Mảng bộ nhớ 32 KB
    reg [31:0] mem [0:WORDS-1];
    wire [12:0] word_addr = mem_addr[14:2];

    initial begin
        if (INIT_FILE != "") begin
            $readmemh(INIT_FILE, mem);
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            mem_ready <= 1'b0;
            mem_rdata <= 32'd0;
        end else begin
            mem_ready <= 1'b0;
            if (mem_valid && !mem_ready) begin
                mem_ready <= 1'b1;
                mem_rdata <= mem[word_addr];
                if (mem_wstrb[0]) mem[word_addr][ 7: 0] <= mem_wdata[ 7: 0];
                if (mem_wstrb[1]) mem[word_addr][15: 8] <= mem_wdata[15: 8];
                if (mem_wstrb[2]) mem[word_addr][23:16] <= mem_wdata[23:16];
                if (mem_wstrb[3]) mem[word_addr][31:24] <= mem_wdata[31:24];
            end
        end
    end

endmodule
