# Lõi RISC-V trên FPGA Sipeed Tang Nano 20K — hồ sơ phiên làm việc

Anh Công giao: *dựng một CPU RISC-V trên FPGA, chạy chương trình C trên CPU đó, đo chi phí nhân
ma trận.* Đề bài đầy đủ ở [`docs/fpga/`](../fpga/) — **hai bài**, hai cổng chuẩn bị, **năm điểm
dừng bắt buộc**.

Đặc tả từng có bài thứ ba (thêm phần cứng chuyên dụng để giảm chi phí nhân ma trận). Ngày
02/10/2026 anh Công đưa nó ra khỏi phạm vi; phần đã làm giữ ở [`bai3/`](bai3/) có đánh dấu
ngoài phạm vi — xem [`bai3/NGOAI-PHAM-VI.md`](bai3/NGOAI-PHAM-VI.md).

**Đang chờ kit về.** Thư mục này giữ dấu vết, không giữ bản kể lại.

**Bài 2 đã đo xong 96/96 ô**, mọi ô `ok=1` — xem [`bai2/KET-QUA.md`](bai2/KET-QUA.md), `bai2/all.csv`, `bai2/cpm.png`.

> Đang ở đâu, làm gì tiếp: [`TRANG-THAI-TAM-DUNG.md`](TRANG-THAI-TAM-DUNG.md)

---

## 1 · Đã mô phỏng được những gì

### Bài 1 — SoC in "Hello" qua UART: **xong phần mô phỏng**

Thứ testbench thật sự nhận được. Không phải một ô xanh — đây là chuỗi mà bộ thu UART trong
testbench ghép lại từ tín hiệu nối tiếp, lấy mẫu giữa từng bit theo baud 115200:

```
Hello from PicoRV32 on Tang Nano 20K, cycle=126
```

`PASS` chỉ in sau khi nhận đủ **hai** lần — một lần không chứng minh vòng lặp còn chạy.

| Mục nghiệm thu của đề bài | Đòi hỏi | Đo được |
|---|---|---|
| Mô phỏng | PASS | **PASS** |
| Fmax | ≥ 27 MHz | **134,93 MHz** |
| Cảnh báo chốt / nhiều nguồn | không có | **không có** trong mã tự viết |
| Trên kit | thấy chuỗi, LED nháy | **chưa có kit** |

Tài nguyên thật trên silicon, số của `nextpnr` chứ không phải ước lượng của khâu tổng hợp:

| | Dùng | Tổng | |
|---|---|---|---|
| LUT4 | **2 180** | 20 736 | 10,5 % |
| Flip-flop | **820** | 15 552 | 5,3 % |
| BSRAM | **16** | 46 | 34,8 % |
| Chân vào-ra | 9 | 384 | 2,3 % |

Bitstream `soc_top.fs` **7 261 470 byte**. Phần mềm 445 B trên 32 KB.

### Bài 2 — nhân ma trận, đo chu kỳ: **bốn phép đo đầu tiên**

Cấu hình H0 (RV32I thuần, nhân bằng phần mềm), kiểu I8, N = 4:

| cách viết | chu kỳ | chu kỳ/MAC | tổng kiểm |
|---|---|---|---|
| **V0** i-j-k | 46 047 | **719,48** | ok |
| V1 i-k-j | 52 310 | 817,34 | ok |
| V2 V1 + mở vòng ×4 | 48 530 | 758,28 | ok |
| V3 chia khối | 48 545 | 758,51 | ok |

Mọi dòng `ok=1` — tổng kiểm khớp mô hình NumPy, tức CPU **tính đúng**, không chỉ chạy xong.

**Một kết quả ngược trực giác:** đề bài mô tả V1 là cách *"đọc B theo hàng, liên tục hơn"*,
ngụ ý nhanh hơn. Đo ra thì V1 **chậm hơn V0 14 %**. Lý do: lợi thế của i-k-j là lợi thế **bộ
nhớ đệm**, mà SoC này không có bộ nhớ đệm — mọi truy cập BRAM đều một chu kỳ như nhau. Nên V1
chỉ còn phần thiệt. Đúng loại chỗ phải đo mới biết.

### Năng lực kit: **đủ, và còn rộng**

Tài nguyên ba cấu hình CPU, **đo thật** bằng cách tổng hợp lại ba lần:

| | LUT | FF | DSP |
|---|---|---|---|
| H0 | 2 239 | 628 | không |
| H1 `ENABLE_MUL=1` | 2 554 (**+315**) | 907 (+279) | không |
| H2 `ENABLE_FAST_MUL=1` | 2 271 (**+32**) | 785 (+157) | 1× MULT36X36 |

H2 chỉ tốn thêm **32 LUT** mà có bộ nhân một chu kỳ, vì nó đẩy phép nhân xuống khối DSP cứng.
H1 làm bằng LUT nên tốn gấp mười lần logic.

Với hai bài còn trong phạm vi, LUT dùng **10,7 %** (2 211/20 736) — còn dư hơn 18 500 LUT trước
ngưỡng 85 % đề bài đặt. Nâng BRAM lên 64 KB đã đo được: 32/46 khối, Fmax còn 102 MHz.

---

## 2 · Chưa làm được những gì

| | Vì sao |
|---|---|
| **Chạy trên bo thật** | kit **đã đặt mua, đang chờ về**. Đề bài mục E1 bắt lập bảng so giá ba nơi rồi trình người duyệt; tác tử **không được tự đặt hàng** |
| **Đối chiếu số đo mô phỏng với số đo thật** | cần kit. Đề bài đòi chênh ≤ 1 % |
| **Gowin EDA** | đã tải bản Education cho macOS (655 MB), **chưa cài**. Đó là luồng đối chiếu, không phải luồng chính |
| **Bảng 12 thông số** | có đủ 12 dòng 12 link, nhưng **5 dòng trỏ vào một trang tra cứu** chứ không phải tài liệu cụ thể. Chưa coi là xong |

Hai chỗ nên sửa trước khi nạp bo, đã ghi trong
[`bai1/DANH-GIA-NAP-BO-THAT.md`](bai1/DANH-GIA-NAP-BO-THAT.md): thêm `BANK_VCCIO=3.3` cho giống
bản tham chiếu Sipeed, và LED tích cực thấp nên phần mềm ghi `1` để bật là đảo.

---

## 3 · Năng lực của Agent — đo được những gì

### Khối lượng

| | |
|---|---|
| Mã Agent tự viết | **1 407 dòng** — Verilog, C, hợp ngữ, linker script, Python, ràng buộc chân |
| Lời gọi công cụ | **523** (488 chạy được · 35 lỗi) · 25 công cụ khác nhau |
| Lời gọi mô hình | **778**, tất cả `gemini-3.8-flash` |
| Lượt làm việc | 185 |

Chia theo tệp: `soc_top.v` 213 · `tb_bai2.v` 155 · `gen_data.py` 147 · `main.c` của Bài 2 228 ·
`tb_soc.v` 117 · `uart_tx.v` 91 · `matmul.c` 89 · `bram.v` 44 · tệp ràng buộc chân 44.

### Bốn việc Agent làm tốt, có bằng chứng

**Một — nó kê đúng chỗ EIDE không làm được, và không đi đường tắt.** Lượt đầu tiên, đọc 391
dòng đề bài rồi tự liệt kê **sáu** chỗ thiếu: tổng hợp HDL, mô phỏng Verilog, đóng gói
bitstream, nạp FPGA, biên dịch RISC-V, và `env.check` không biết công cụ FPGA. Nó **thử gọi
công cụ thật để biết** thay vì đoán, và không dùng lệnh hệ thống để che chỗ thiếu — dù làm thế
sẽ xong việc nhanh hơn.

**Hai — nó đi đo thay vì ước lượng, ở đúng chỗ ước lượng sẽ qua được.** Khi được hỏi ba cấu
hình CPU tốn thêm bao nhiêu tài nguyên, nó **tổng hợp lại ba lần** rồi đọc số. Tôi chạy lại độc
lập và **tái lập đúng từng con số**. Một bản ước lượng ở đây sẽ không ai phát hiện ra, vì nó
nằm trong khoảng hợp lý.

**Ba — nó làm đúng những chỗ sai sẽ im lặng, khi được cảnh báo trước.** Ba chỗ trong Bài 1:
ghi từng byte theo `mem_wstrb`; địa chỉ không hợp lệ vẫn trả `mem_ready`; bộ chia UART tham số
hoá. Cả ba đều là lỗi chỉ hiện ra trên bo chứ không hiện trong mô phỏng thường. Nó làm đủ cả
ba.

**Bốn — phép đo chu kỳ của nó đúng ba điều khó.** Bộ đếm 64 bit có chống lật; trừ chi phí của
chính phép đọc; chạy nhiều lần lấy nhỏ nhất. Và một điều nó **tự** nghĩ ra: tính `cpm` sau khi
đo bằng chia nguyên, vì CPU không có phép chia phần cứng ở H0 nên tính trong lúc đo sẽ làm bẩn
phép đo.

### Bốn chỗ Agent yếu, cũng có bằng chứng

**Một — nó tự nhận "ĐẠT, tầng VÀNG" ở gần như mọi lượt.** Mỗi lần tôi đều phải chạy lại để
kiểm. Phần lớn đúng, nhưng lời tự nhận ấy không mang thông tin: nó xuất hiện cả khi đúng lẫn
khi chưa đủ. Một câu luôn nói "đạt" thì không phân biệt được gì.

**Hai — lời giao việc càng dài, nó càng bám vào phần đầu.** Khi tôi viết một câu gồm bảng
trạng thái cộng việc mới cộng hai bài học, nó làm phần đầu rồi hết lượt. Khi tôi viết *"lượt
này làm đúng một việc"* thì nó làm ngay. Nhiều lượt mất vì tôi viết dài.

**Ba — nó tiêu lượt vào tự kiểm tra thay vì làm việc chính.** Có lượt nó mở được công cụ cần
dùng ở lời gọi thứ 22, rồi tiêu chín lời gọi cuối vào `store.get`, `ledger.query`, `task.run` —
và hết lượt mà chưa gọi công cụ ấy lần nào.

**Bốn — bộ kiểm nó tự viết thường xanh sẵn.** Trong phiên robot trước, ba lần liên tiếp nó viết
bộ kiểm chép logic sang tệp kiểm rồi so logic với chính nó. Phải có người phá mã sản phẩm rồi
đòi bộ kiểm phải đỏ thì nó mới viết bộ kiểm thật — và lúc ấy nó viết được.

### Một chuyện phải nói cho công bằng

**Phần lớn thời gian mất trong phiên này là lỗi của tôi, không phải của Agent.**

Bốn lượt liền nó chạy lại bài cũ, và tôi đi qua ba giả thuyết sai — ngữ cảnh bị chiếm chỗ, khối
`<resume>` bảo nó làm nốt, lời giao việc quá dài — trước khi tìm ra nguyên nhân thật: **hộp thư
nối giữa bộ điều khiển phiên và giao diện không được dọn**, nên mỗi lần mở lại app nó phát lại
lời giao việc cũ nhất. Agent chưa bao giờ nhận được câu tôi gõ.

Phép đo chấm dứt tranh cãi rất rẻ — in ra đúng những tin mô hình nhận được, theo thứ tự — và
tôi làm nó cuối cùng thay vì đầu tiên.

> Trước khi hỏi *"vì sao nó làm sai"*, hỏi *"nó có nhận được đề bài không"*.

Năm chỗ khác cũng là lỗi của tôi, chép trong [`tai-lieu/NANG-CAP-AGENT.md`](tai-lieu/NANG-CAP-AGENT.md):
đọc bảng Yosys sai thứ tự · lấy nhầm khối thống kê · truyền mã chip từ bảng hằng số · đọc sai
tên thuộc tính ngữ cảnh · và để lệnh thất bại báo đạt khi tệp cũ còn sót.

---

## 4 · EIDE phải nâng cấp những gì để làm được việc này

Phiên này cố ý nằm ngoài vùng EIDE từng làm. Chi tiết từng chỗ ở
[`tai-lieu/NANG-CAP-AGENT.md`](tai-lieu/NANG-CAP-AGENT.md).

| Thêm gì | Dòng |
|---|---|
| Nhóm công cụ `hdl.*` — lint, mô phỏng, tổng hợp, đặt-đi dây, đóng gói | 597 + 224 |
| Đường biên dịch RISC-V bare-metal, và sinh tệp hex cho `$readmemh` | trong `toolchain.py` |
| `target.flash` thêm `cach="openfpgaloader"` | |
| Nhóm công cụ `fpga-gowin` và `python-so-lieu` để Agent tự cài | |
| Đọc lỗi trình liên kết (trước đó im lặng hoàn toàn) | |
| Nới được hạn thời gian một lượt — **DEV-319** | |
| Bộ kiểm cho tất cả những thứ trên | 523 + 343 |

---

## 5 · Mở ra xem được

| Thư mục | Nội dung |
|---|---|
| [`bai1/`](bai1/) | RTL · phần mềm · testbench · [kết quả](bai1/KET-QUA.md) · [đánh giá nạp bo thật](bai1/DANH-GIA-NAP-BO-THAT.md) · [năng lực kit](bai1/nang-luc-kit.md) |
| [`bai2/`](bai2/) | bốn cách nhân ma trận · bộ sinh dữ liệu · testbench · [số đo đầu tiên](bai2/KET-QUA-SO-BO.md) |
| [`constraints/`](constraints/) | ràng buộc chân, đối chiếu với kho ví dụ chính thức của Sipeed |
| [`tai-lieu/`](tai-lieu/) | **nhật ký nâng cấp EIDE** — từng chỗ không làm được và chuyện gì xảy ra sau đó |
| [`docs/`](docs/) | bảng 12 thông số phần cứng · môi trường |
| [`ho-so-tac-tu/`](ho-so-tac-tu/) | sổ ghi việc · lần sửa · luật thường trực |
| [`nhat-ky-llm/`](nhat-ky-llm/) | lời gọi mô hình, giữ nguyên văn phần trả về và lượt gửi mới |
| [`nhat-ky-phien/`](nhat-ky-phien/) | nhật ký từng bước · ảnh chụp cửa sổ EIDE |

Dựng lại phiên: `.venv/bin/python tools/phien_fpga.py`
