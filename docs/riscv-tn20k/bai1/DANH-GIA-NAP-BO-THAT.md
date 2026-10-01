# Bài 1 nạp lên bo thật có chạy không?

*Đánh giá ngày 01/10/2026, trước khi có kit. Mọi kết luận dưới đây là **phép đo**, không phải
phỏng đoán — trừ chỗ nào ghi rõ là chưa đo được.*

## Trả lời ngắn

**Nhiều khả năng chạy.** Năm rủi ro lớn nhất đều đã kiểm và đều qua. Rủi ro còn lại không nằm ở
thiết kế mà nằm ở những thứ chỉ bo thật mới trả lời được.

## Năm phép kiểm đã làm

### 1 · Chương trình có thật sự nằm trong bitstream không — ĐO ĐƯỢC

Đây là rủi ro lớn nhất và cũng là loại im lặng nhất: nếu `$readmemh` không đi được vào bitstream
thì FPGA cấu hình xong, CPU chạy, và nó chạy toàn lệnh 0. Mọi chặng vẫn báo đạt.

Phép đo: thay toàn bộ 101 từ chương trình thành `00000000`, dựng lại cả ba chặng, rồi so mã băm
tệp `.fs`.

| Chương trình | Mã băm `.fs` |
|---|---|
| thật | `d5767a6be3a29f80…` |
| toàn số 0 | `5e1a6699357eb4e5…` |

**Bitstream đổi theo chương trình** — nên chương trình nằm trong đó.

### 2 · Số chân có đúng không — ĐỐI CHIẾU VỚI KHO CHÍNH THỨC CỦA SIPEED

Không tin bảng tự lập. Đối chiếu với tệp ràng buộc trong kho ví dụ chính thức
`sipeed/TangNano-20K-example`:

| Chân | Ta dùng | Kho chính thức | Nguồn |
|---|---|---|---|
| Clock 27 MHz | 4 | **4** | `led/blink_leds/src/blink_leds.cst` |
| LED 0–5 | 15–20 | **15–20** | cùng tệp trên |
| UART TX | 69 | **69** | `uart/src/top.cst` **và** `picorv32/src/fpga_project.cst` |
| UART RX | 70 | **70** | `uart/src/top.cst` |
| Nút S1 / reset | 88 | **88** | `picorv32/src/fpga_project.cst` |

Đáng chú ý: Sipeed có sẵn **một ví dụ PicoRV32 cho chính bo này**, và nó dùng đúng ba chân
`ser_tx` 69 · `resetn` 88 · `clk` 4. Đó là thiết kế tham chiếu gần nhất có thể có.

### 3 · Chân reset có bị thả nổi không — KIỂM MÃ

`soc_top.v` coi nút là tích cực thấp (`if (!btn_s1)`), khớp tài liệu. Và tệp ràng buộc có
`PULL_MODE=UP` cho chân 88.

Thiếu phần kéo lên này thì chân thả nổi có thể đọc ra 0, và bo **nằm trong reset vĩnh viễn** —
một lỗi trông giống hệt "nạp xong mà không chạy".

### 4 · Định thời — ĐO BẰNG nextpnr

Fmax **134,93 MHz**, cần 27 MHz. Dư gần 5 lần.

### 5 · Phần mềm có thật sự chạy không — ĐO BẰNG MÔ PHỎNG

Testbench giải mã UART từng bit, lấy mẫu giữa mỗi bit theo baud 115200, và nhận đúng:

```
Hello from PicoRV32 on Tang Nano 20K, cycle=126
```

PASS chỉ in sau khi nhận đủ **hai** lần.

## Ba chỗ mô phỏng KHÔNG chứng minh được

Nói ra để không ai đọc quá tay bản đánh giá này.

1. **Thạch anh có đúng 27,000 MHz không.** Bộ chia baud 234 giả định như vậy. Lệch tần số thì
   ký tự ra rác, và đó là triệu chứng dễ bị đổ nhầm cho phần mềm.
2. **Chip cầu USB BL616 có nối đúng chiều không.** Chân 69 là TX của FPGA; nếu trên bo nó lại
   vào TX của BL616 thay vì RX thì không có chữ nào ra, dù mọi thứ khác đúng.
3. **Tệp `.fs` chưa bao giờ được nạp bằng `openFPGALoader`.** Luồng nạp chạy được hay không là
   một câu hỏi riêng, chưa ai trả lời.

## Hai chỗ nên sửa trước khi nạp

Không chặn, nhưng rẻ và nên làm:

- **Thêm `BANK_VCCIO=3.3`** vào từng dòng `IO_PORT`. Thiết kế tham chiếu của Sipeed có; của ta
  không. Bộ công cụ mở có thể bỏ qua thuộc tính này, nhưng giống bản tham chiếu thì bớt một
  biến khi đi tìm lỗi.
- **LED tích cực thấp.** Tài liệu ghi vậy, mà phần mềm ghi `1` để bật. Trên bo thì đèn sẽ sáng
  khi chương trình ghi `0` — đảo so với ý định. Không hỏng gì, chỉ gây hiểu nhầm lúc nhìn.

## Thử thế nào khi có kit

| Bước | Lệnh | Điều kiện qua |
|---|---|---|
| 1 | `target.flash` với `cach="openfpgaloader"` | nạp xong không lỗi |
| 2 | mở cổng nối tiếp 115200 baud | thấy chuỗi lặp mỗi giây |
| 3 | nhìn LED | một đèn đảo trạng thái mỗi giây |
| 4 | bấm nút S1 | chuỗi bắt đầu lại từ `cycle=` nhỏ |

Nếu bước 2 im lặng mà bước 3 chạy: sai chân UART hoặc sai chiều TX/RX — **không phải** lỗi CPU.
Nếu cả hai im lặng: xem lại reset và xem bitstream có vào SRAM không.
Nếu ra ký tự rác: sai bộ chia baud, tức tần số thạch anh thật khác 27 MHz.
