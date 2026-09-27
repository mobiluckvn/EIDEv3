# Sở cứ — dự án robot hai bánh tự cân bằng làm bằng EIDE

Thư mục này giữ bằng chứng của một phiên làm việc **có thật** trên máy: EIDE đọc tài liệu bàn
giao phần cứng của MOBILUCK rồi đi hết đường ống, từ tạo dự án tới mô phỏng vòng cân bằng.

| Tệp | Là gì |
|---|---|
| `NHAT-KY.md` | Nhật ký từng bước: câu người gõ, lời tác tử, công cụ nó gọi, kết luận đo được |
| `buoc.jsonl` | Cùng nội dung ở dạng máy đọc, để so hai lần chạy bằng mã |
| `doi-chieu.md` | Đối chiếu netlist sinh ra với bảng 12/30/33 của tài liệu — **14/14 net khớp** |
| `mach.net` | Netlist KiCad do `sch.netlist` sinh |
| `anh/` | Ảnh cửa sổ EIDE ở từng mốc, do **chính app vẽ ra** (không chụp màn hình) |
| `ma-nguon/` | Firmware và chương trình mô phỏng mà tác tử viết |

## Kết quả đo được

| Mốc | Số đo | Đối chiếu tài liệu |
|---|---|---|
| Bản đồ chân | 22 chân vào kho, mỗi chân có trích dẫn tới dòng bảng | 14/14 chân bảng 12 |
| Bản đồ mạch | 10 khối · 21 nút · 19 net | 14/14 net đúng chân; 19/19 net đủ hai đầu |
| Sơ đồ nguyên lý | 11 sheet phân cấp + SVG + `.net` | 14/14 net khớp (`doi-chieu.md`) |
| Giá trị thanh ghi | 19 Fact có trích dẫn | 18/19 khớp bảng 91 |
| Firmware | `control.c` (logic thuần) + `firmware.ino` (thanh ghi) | 0 cấu trúc bị cấm (bảng 83) |
| Biên dịch | `arduino-cli` → `.hex` | Flash 2.500/30.720 B · SRAM 72/2.048 B |
| Mô phỏng | vòng kín, chạy chính `control.c` | **ĐẠT**: góc max 3,0° · góc cuối 0,155° · 5 s |

## Đọc kết quả mô phỏng cho đúng

Mô phỏng chạy **đúng mã sẽ nạp vào chip** (`firmware/control.c`) trong một mô hình con lắc
ngược. Nó nói: bộ điều khiển tự nhất quán và ổn định được **với mô hình đó**. Nó **không** nói
robot thật sẽ đứng — tham số cơ khí thật (chiều dài, quán tính, ma sát) phải đo trên bo, và
tài liệu bàn giao gọi chúng là *hạng L*: xác định bằng bài đo, không suy từ datasheet.

## Cách chạy lại

```bash
EIDE_FEATURE_SCHEMATIC=1 .venv/bin/python tools/phien_robot.py   # cả 13 bước
.venv/bin/python tools/doi_chieu_robot.py                        # đối chiếu với tài liệu
```
