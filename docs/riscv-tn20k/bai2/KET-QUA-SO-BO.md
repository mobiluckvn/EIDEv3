# Bài 2 — số đo đầu tiên

*01/10/2026. Bốn phép đo thật, chưa đủ ma trận cấu hình.*

## Đường cơ sở đầu tiên của cả đề án

Cấu hình H0 (RV32I thuần, nhân bằng phần mềm), kiểu I8, N = 4:

| N | kiểu | cách viết | chu kỳ | chu kỳ / MAC | tổng kiểm |
|---|---|---|---|---|---|
| 4 | I8 | **V0** i-j-k | 46 047 | **719,48** | ok |
| 4 | I8 | V1 i-k-j | 52 310 | 817,34 | ok |
| 4 | I8 | V2 V1 + mở vòng ×4 | 48 530 | 758,28 | ok |
| 4 | I8 | V3 chia khối | 48 545 | 758,51 | ok |

**Mọi dòng `ok=1`** — tổng kiểm khớp mô hình NumPy, tức CPU tính đúng tích ma trận.

## Một kết quả ngược với trực giác, và nó có lý

Đề bài mô tả V1 (thứ tự i-k-j) là cách *"đọc B theo hàng, liên tục hơn"*, ngụ ý nhanh hơn V0.
Đo được thì **V1 chậm hơn V0 14 %** ở N = 4.

Lý do: lợi thế của i-k-j là lợi thế **bộ nhớ đệm**, mà SoC này **không có bộ nhớ đệm** — mọi
truy cập đều vào BRAM một chu kỳ như nhau. Nên V1 chỉ còn phần thiệt: thêm một vòng ghi C.

Đây đúng loại chỗ phải đo mới biết, và là lý do đề bài bắt đo cả bốn cách thay vì chọn sẵn
một cách.

## Ba điều phép đo này đã làm đúng

1. **Bộ đếm 64 bit** (`rdcycle` + `rdcycleh`, có chống lật). Chỉ đọc 32 bit thấp thì ở N = 32
   cấu hình H0 nó tràn, và số đo thành vô nghĩa mà trông vẫn hợp lý.
2. **Trừ chi phí của chính phép đọc**, đo riêng bằng hai lần đọc liền nhau.
3. **Chạy nhiều lần lấy nhỏ nhất**, không lấy trung bình.

Và `cpm` tính **sau** khi đo, bằng phép chia nguyên — vì CPU này không có phép chia phần cứng
ở H0, tính trong lúc đo sẽ làm bẩn chính phép đo.

## Tổng kiểm: vì sao có trọng số

Đề bài chọn `Σ C[i][j]·(i·N+j+1) mod 2³²` chứ không phải tổng đơn thuần. Đã kiểm:

| Lỗi | Tổng có trọng số | Tổng đơn thuần |
|---|---|---|
| chuyển vị ma trận | **bắt được** | bỏ lọt |
| đổi chỗ hai phần tử | **bắt được** | bỏ lọt |

Nhầm chỉ số hàng với cột là lỗi hay gặp nhất ở nhân ma trận, và tổng đơn thuần không thấy nó.

## Còn lại

Ma trận đủ là **4 N × 2 kiểu × 4 cách × 3 cấu hình = 96 phép đo**. Mỗi N cần sinh lại tệp dữ
liệu và dịch lại firmware; mỗi cấu hình CPU cần dựng lại mô phỏng. Cần một bộ điều khiển chạy
hết rồi gom thành bảng.
