# Bài 2 — đường cơ sở đầy đủ, N = 16, kiểu I8

*02/10/2026. Mười hai phép đo trên mô phỏng Verilator, **tất cả `ok=1`** — tổng kiểm khớp mô
hình NumPy, nên CPU tính đúng chứ không chỉ chạy xong.*

## Bảng

Số chu kỳ trên mỗi phép nhân-cộng. Thấp hơn là tốt hơn.

| | V0 i-j-k | V1 i-k-j | **V2** mở vòng ×4 | V3 chia khối |
|---|---|---|---|---|
| **H0** `rv32i`, nhân bằng phần mềm | 618,04 | 656,04 | **601,19** | 632,85 |
| **H1** `ENABLE_MUL`, nhân bằng LUT | 83,40 | 92,79 | **72,51** | 75,61 |
| **H2** `ENABLE_FAST_MUL`, nhân bằng DSP | 49,40 | 58,79 | **38,51** | 41,60 |

| Cấu hình | cpm tốt nhất | Nhanh hơn H0 |
|---|---|---|
| H0 | 601,19 | — |
| H1 | 72,51 | 8,29 lần |
| **H2** | **38,51** | **15,61 lần** |

### Mục tiêu nấc 3b

Đề bài: *"cpm ≤ ½ cpm của H2 tốt nhất"*.

> **cpm ≤ 19,25**

## Ba điều bảng này cho biết

**Một — V2 thắng ở cả ba cấu hình.** Mở vòng lặp ×4 luôn là cách tốt nhất, và khoảng cách giữ
nguyên khi đổi phần cứng. Đó là lợi thế của việc bớt chi phí điều khiển vòng lặp, không phụ
thuộc bộ nhân.

**Hai — V1 thua ở cả ba cấu hình.** Đề bài mô tả V1 là cách *"đọc B theo hàng, liên tục hơn"*,
ngụ ý nhanh hơn. Đo ở N=4 thấy chậm hơn, và ở N=16 vẫn chậm hơn, ở **cả ba** cấu hình. Lợi thế
của thứ tự i-k-j là lợi thế **bộ nhớ đệm**, mà SoC này không có bộ nhớ đệm — mọi truy cập BRAM
đều một chu kỳ như nhau. Nên V1 chỉ còn phần thiệt.

**Ba — bộ nhân DSP đáng giá hơn bộ nhân LUT gần gấp đôi**, mà tốn ít tài nguyên hơn mười lần:

| | cpm tốt nhất | LUT thêm | FF thêm | DSP |
|---|---|---|---|---|
| H1 | 72,51 | +315 | +279 | không |
| **H2** | **38,51** | **+32** | +157 | 1× MULT36X36 |

Đây là chỗ đáng ghi nhất của Bài 2: **H2 vừa nhanh gấp đôi H1 vừa rẻ gấp mười lần về LUT.**
Nếu chỉ nhìn một trong hai cột thì không thấy.

## Ba lần phép đo của người giao việc sai, và vì sao

Chép lại để lần sau khỏi đi lại đường ấy.

| Lần | Tôi làm gì | Vì sao sai |
|---|---|---|
| 1 | Sửa `.ENABLE_MUL (0)` ở chỗ gọi mô-đun | Agent đã chuyển sang **tham số mô-đun**, chuỗi ấy không còn |
| 2 | Sửa `parameter ENABLE_MUL = 0` | testbench **đè** bằng macro `CFG_MUL`, nên mặc định không có tác dụng |
| 3 | — | cách đúng: truyền `dinh_nghia={"CFG_MUL":"1",…}` cho `hdl.sim` |

Hai lần đầu đều cho ra cùng một triệu chứng: H1 và H2 **không in dòng nào** rồi hết hạn sau
180 giây. Triệu chứng ấy rất dễ đọc nhầm thành *"bật bộ nhân cứng làm CPU treo"* — một kết luận
sai về sản phẩm, rút ra từ một phép đo hỏng.

Thứ cứu được là một câu tự dặn trước khi đo: **nếu H1/H2 gần bằng H0 thì đừng báo kết quả, đi
tìm nguyên nhân trước.** Nhưng lần này chúng không gần bằng — chúng **không có gì cả**, và im
lặng cũng là một dạng số liệu phải nghi.

Thiết kế của Agent thì đúng: nhận cấu hình qua macro ở testbench là cách để một tệp RTL phục vụ
được cả ba cấu hình mà không phải sửa tệp. Người đo sai, không phải người viết sai.
