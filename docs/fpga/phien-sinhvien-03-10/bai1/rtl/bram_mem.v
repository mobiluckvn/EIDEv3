// bram_mem.v
// Khối BRAM 32 KB (8192 từ 32-bit) dùng chung cho Lệnh và Dữ liệu
// Hỗ trợ ghi từng byte theo mem_wstrb và nạp trước qua $readmemh
`timescale 1ns / 1ps

module bram_mem #(
    parameter WORDS = 8192,           // 8192 * 4 bytes = 32 KB
    parameter HEX_FILE = ""
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire        mem_valid,
    input  wire [31:0] mem_addr,
    input  wire [31:0] mem_wdata,
    input  wire [3:0]  mem_wstrb,
    output reg         mem_ready,
    output reg  [31:0] mem_rdata
);

    // Mảng bộ nhớ 32-bit
    reg [31:0] mem [0:WORDS-1];

    wire [12:0] word_addr = mem_addr[14:2];

    integer i;
    initial begin
        for (i = 0; i < WORDS; i = i + 1) begin
            mem[i] = 32'd0;
        end
        if (HEX_FILE != "") begin
            $readmemh(HEX_FILE, mem);
        end
    end

    // Giao thức bắt tay: mem_ready trễ 1 chu kỳ clock theo chuẩn synchronous BRAM
    always @(posedge clk) begin
        if (!rst_n) begin
            mem_ready <= 1'b0;
            mem_rdata <= 32'd0;
        end else begin
            mem_ready <= mem_valid && !mem_ready;
            if (mem_valid) begin
                // Đọc đồng bộ
                mem_rdata <= mem[word_addr];

                // Ghi theo byte mask
                if (mem_wstrb[0]) mem[word_addr][ 7: 0] <= mem_wdata[ 7: 0];
                if (mem_wstrb[1]) mem[word_addr][15: 8] <= mem_wdata[15: 8];
                if (mem_wstrb[2]) mem[word_addr][23:16] <= mem_wdata[23:16];
                if (mem_wstrb[3]) mem[word_addr][31:24] <= mem_wdata[31:24];
            end
        end
    end

endmodule
