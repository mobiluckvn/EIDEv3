# Lõi RISC-V trên FPGA Sipeed Tang Nano 20K — hồ sơ phiên làm việc

Anh Công giao: *dựng một CPU RISC-V trên FPGA, chạy chương trình C trên CPU đó, đo chi phí nhân
ma trận, rồi thêm phần cứng chuyên dụng để giảm chi phí ấy.* Đề bài đầy đủ ở
[`docs/fpga/`](../fpga/). Ba bài, hai cổng chuẩn bị, **sáu điểm dừng bắt buộc**.

**Đang làm.** Thư mục này giữ dấu vết, không giữ bản kể lại.

## Vì sao phiên này khác hai phiên trước

Phiên viết hệ điều hành và phiên robot đều nằm trong vùng EIDE đã làm được: biên dịch C cho ARM
hoặc AVR, nạp qua ST-Link hoặc avrdude. Phiên này nằm **ngoài hẳn** — EIDE chưa có một dòng nào
về HDL.

Nên nó đo hai thứ cùng lúc: **Agent làm được bài FPGA tới đâu**, và **một môi trường dựng cho vi
điều khiển còn thiếu gì khi gặp FPGA**. Phần thứ hai ghi ở
[`tai-lieu/NANG-CAP-AGENT.md`](tai-lieu/NANG-CAP-AGENT.md), và nó là kết quả nghiên cứu chính của
phiên này cho tới giờ.

## Đã xong

| | |
|---|---|
| Chuỗi công cụ | **sáu chương trình chạy được**, phiên bản đọc từ chính lệnh |
| EIDE: biên dịch RISC-V | `rv32i` · `rv32im` · `rv32imac` — đúng ba cấu hình H0/H1/H2 đề bài cần |
| EIDE: tệp hex `$readmemh` | sinh được, little-endian, có bộ kiểm so từng từ với ảnh nhị phân |
| EIDE: đọc lỗi linker script | trước đó im lặng hoàn toàn |
| G0 — bảng thông số | 12 dòng, 12 link — **chưa coi là xong**, năm dòng trỏ vào trang tra cứu |
| Gowin EDA Education macOS | đã tải (655 MB), **chưa cài** |

## Chưa xong

Nhóm công cụ `hdl.*` — tổng hợp Verilog, mô phỏng Verilog, đóng gói bitstream, nạp FPGA. Sáu
chương trình đã nằm trên máy, nhưng **EIDE chưa có công cụ nào gọi chúng**. Đây là phần lớn hơn
hẳn phần đã làm.

## Mở ra xem được

| Thư mục | Nội dung |
|---|---|
| [`tai-lieu/NANG-CAP-AGENT.md`](tai-lieu/NANG-CAP-AGENT.md) | từng chỗ EIDE không làm được, và chuyện gì xảy ra sau đó |
| [`docs/`](docs/) | bảng 12 thông số phần cứng · môi trường |
| [`ho-so-tac-tu/`](ho-so-tac-tu/) | sổ ghi việc · lần sửa · luật thường trực của dự án |
| [`nhat-ky-llm/`](nhat-ky-llm/) | **295 lời gọi mô hình**, giữ nguyên văn phần trả về và lượt gửi mới |
| [`nhat-ky-phien/`](nhat-ky-phien/) | nhật ký từng bước · ảnh chụp cửa sổ EIDE |

Dựng lại phiên: `.venv/bin/python tools/phien_fpga.py`
