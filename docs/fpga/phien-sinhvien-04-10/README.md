# Phiên sinh viên — lõi RISC-V trên FPGA, 03–04/10/2026

Sở cứ của việc thứ ba trong luận văn: dựng CPU RISC-V trên kit Sipeed Tang Nano 20K, chạy
chương trình C trên CPU đó, đo chi phí nhân ma trận ở ba cấu hình phần cứng.

Khác phiên [`../phien-sinhvien-03-10/`](../phien-sinhvien-03-10/): phiên này làm lại **từ bước 1
trong một dự án trống**, với đầu vào viết lại cho tường minh
([`../DAU-VAO-AGENT-FPGA-v2.md`](../DAU-VAO-AGENT-FPGA-v2.md)), và **chạy trên bo thật**. Mọi
con số dưới đây là số đo từ silicon.

## Kết quả, và phép kiểm của người

| phép kiểm — người tự làm, đọc bản ghi gốc và mã máy | kết quả |
|---|---|
| ô bắt được từ cổng nối tiếp của bo | **96 / 96** |
| ô có `ok=1` | **96 / 96** |
| ô có tổng kiểm lệch bảng tính tay ở tầng NGƯỜI | **0** |
| ô lệch số chu kỳ giữa bo thật và mô phỏng Verilator | **0** |
| dòng trong bảng 96 ô khớp bản ghi gốc | **96 / 96** |

Tăng tốc khi đưa phép nhân xuống phần cứng: bộ nhân tuần tự **1,57×–6,8×**, bộ nhân DSP
**2,45×–12,5×** so với nhân bằng phần mềm.

## Tệp nào là gì

| | |
|---|---|
| `bai2/ket-qua/bo-that-h0.log` · `-h1.log` · `-h2.log` | **bản ghi thô từ cổng nối tiếp của bo**, mỗi tệp 32 dòng `RESULT` kèm `DONE_BENCHMARK_BAI2` |
| `bai2/ket-qua/bo-that-h0-lan2.log` | lần bắt lại H0 để kiểm lặp — giữ lại vì nó chứng minh số không đổi giữa hai lần chạy |
| `bai2/ket-qua/bang-doi-chieu-96-o.md` | bảng 96 ô, cột mô phỏng và cột bo thật |
| `KET-QUA.md` | tài liệu tổng kết Agent tự xuất; có **một chỗ người sửa**, ghi rõ tại chỗ |
| `bai1/` · `bai2/` | mã Agent tự viết: Verilog, C, hợp ngữ, linker script, Python, Makefile |
| `constraints/` | ràng buộc chân cho kit |
| `nhat-ky-phien/NHAT-KY.md` | nhật ký từng bước — **54 bước**, mỗi bước một ảnh cửa sổ EIDE |
| `nhat-ky-phien/anh/` | 54 ảnh cửa sổ EIDE, do chính app vẽ ra |
| `nhat-ky-phien/buoc.jsonl` | cùng nội dung ở dạng máy đọc |
| `nhat-ky-phien/quan-sat-nguoi.jsonl` | những gì người quan sát trên bo và báo lại |
| `ho-so-tac-tu/changesets.jsonl` | 161 changeset — mọi lần sửa đều gỡ lại được |
| `ho-so-tac-tu/so-cai-loi-goi-cong-cu.jsonl` | sổ cái rút gọn: mọi lời gọi công cụ kèm **mốc thời gian** và kết quả |

Sổ cái đầy đủ 11,2 MB không mang vào đây. Bản rút gọn giữ đúng phần dùng để kiểm: lời gọi,
mốc, kết quả, cửa duyệt. Mốc thời gian là thứ đã bắt được hai lỗi nặng nhất của phiên.

## Hai lỗi chỉ mốc thời gian mới bắt được

**Bản ghi chụp trước khi nạp 92 giây.** Một lượt báo *"bắt 32 dòng từ bo, lệch 0 %"*. Mốc trong
sổ cái rút gọn nói khác:

```
01:59:44  target.log     ok   ← đọc cổng Ở ĐÂY
02:00:37  hdl.synth      ok   ← tổng hợp mới bắt đầu
02:01:16  hdl.bitstream  ok   ← bitstream ra đời Ở ĐÂY
02:02:14  target.flash   ok   ← nạp lên bo
```

Tức đọc bo đang chạy bài trước, rồi so bản ghi mô phỏng với chính nó. Tra được lại bằng
`grep target.log ho-so-tac-tu/so-cai-loi-goi-cong-cu.jsonl`.

**Gói giao diện cũ hơn mã nguồn ba ngày.** Nó cắt lời Agent ở 3 000 ký tự không để lại dấu, nên
16 trong 30 câu mất đuôi, và người đọc nhật ký kết luận sai rằng Agent không trả lời một câu
hỏi. Chi tiết: [`../DEV-333-GOI-APP-CU-HON-MA-NGUON.md`](../DEV-333-GOI-APP-CU-HON-MA-NGUON.md).

## Lỗi của người, ghi ở đây vì chúng đo được điều lỗi của Agent không đo

1. **Tiêu chí nghiệm thu tự nó vô hiệu.** Tài liệu đầu vào do người viết đòi *mọi ô `ok=1`* — mà
   một bo tính sai toàn bộ vẫn đạt, vì cờ ấy chỉ so bốn cách viết với nhau. Vá bằng mục 5.3b:
   chốt luật sinh dữ liệu và bốn tổng kiểm ở tầng NGƯỜI, người tự tính tay.
2. **Đặt tên tệp theo cấu hình mình *tưởng* đang đo** — đè mất 22 ô dữ liệu. Nay tên tệp lấy từ
   nhãn `hw=` trong chính bản ghi.
3. **Vòng đọc cổng thoát khi đếm được 32 chuỗi `RESULT`**, nên cắt giữa dòng thứ 32. Đếm một
   chuỗi xuất hiện không giống đọc xong một dòng.

## Hai chỗ chưa dựng lại được bằng lệnh tay

- `make bitstream-h1` **đổ**: `soc_top.v` ghi đường dẫn `include` tính từ gốc dự án, nên đứng
  trong `bai2/` thì không thấy tệp. 96 ô đo được là thật, nhưng đường dựng mà Makefile mô tả
  thì người khác gõ lại chưa ra.
- Dựng tay bằng `yosys` + `nextpnr` cũng **đổ** ở `no BELs remaining for cell type '$buf'` tại
  `pcpi_mul`. Đường chạy được hiện nay là `hdl.synth` của EIDE.
