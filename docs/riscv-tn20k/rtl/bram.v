`timescale 1ns / 1ps

// Bộ nhớ chương trình và dữ liệu của SoC: 32 KB, MỘT CỔNG, nạp sẵn bằng $readmemh.
//
// Một cổng, không phải hai — và đó là một quyết định có số đo đứng sau.
//
// Ngày 02/10/2026, bản hai cổng (thêm b_en/b_addr/b_wdata/b_wstrb/b_rdata cho đơn vị vector
// của Bài 3 nấc 3c) làm **suy luận BSRAM đứt hoàn toàn**. Tổng hợp riêng mô-đun này cho:
//
//     Module bram: replaced 819152 cells with 5635760 new cells
//       262144  DFFE          ◀── cả 32 KB thành flip-flop
//       786384  $_MUX_
//     Extracted 2474345 AND gates ... 262516 inputs
//
// Chip GW2AR-18 có 15 552 flip-flop. Cần 262 144 là vượt 17 lần — thiết kế không bao giờ
// vừa, và `yosys-abc` cày 30 phút để tối ưu một mạng 2,47 triệu cổng cho một mạch không thể
// nạp được. "Tổng hợp chậm" ở đó không phải chuyện hiệu năng công cụ.
//
// Nguyên nhân nằm ở cấu trúc, không ở số cổng: bản hai cổng đặt CẢ HAI cổng trong cùng một
// khối `always @(posedge clk)`, mỗi cổng vừa đọc vừa ghi với cho phép ghi theo từng byte,
// trên cùng một mảng `mem`. Gowin BSRAM không có nguyên thuỷ nào như thế, nên yosys bỏ cuộc
// và dựng bằng thanh ghi. Bản một cổng dưới đây suy luận ra 32 × RAM16SDP4 + 16 × SP = 16
// khối BSRAM, và tổng hợp cả SoC xong trong 5 giây.
//
// Nếu sau này lại cần cổng thứ hai: phép kiểm BRAM hai cổng phải chạy TRƯỚC khi viết RTL
// dùng nó, và phải kiểm bằng cách đọc bảng đếm ô — không phải bằng việc mô phỏng chạy đúng.
// Mô phỏng của bản hai cổng chạy đúng hoàn toàn; chỉ có silicon là không nhận.

module bram #(
    parameter WORDS = 8192,             // 32 KB = 8192 từ 32-bit (32768 byte)
    parameter INIT_FILE = ""
) (
    input  wire        clk,
    input  wire        resetn,

    // Bus CPU PicoRV32
    input  wire        mem_valid,
    input  wire [31:0] mem_addr,
    input  wire [31:0] mem_wdata,
    input  wire [3:0]  mem_wstrb,
    output reg         mem_ready,
    output reg  [31:0] mem_rdata
);

    // Mảng bộ nhớ 32 KB (8192 từ 32-bit)
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
