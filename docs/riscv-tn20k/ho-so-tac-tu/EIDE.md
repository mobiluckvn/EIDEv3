# Dự án: lõi RISC-V trên Sipeed Tang Nano 20K

Đề bài đầy đủ: `tai-lieu/yeu-cau-agent-riscv-tang-nano-20k.md` (v1.1, 01/10/2026).
Đọc kỹ **Phần A3 — Quy tắc bắt buộc** trước khi làm bất cứ việc gì.

## Luật thường trực của dự án này

1. **Mọi con số phần cứng phải có link nguồn.** Chỗ nào tài liệu đánh `[XÁC MINH]` là giá trị
   ban đầu, chưa được tin. Phải đối chiếu Sipeed wiki, sơ đồ nguyên lý, hoặc tài liệu Gowin,
   rồi ghi link vào `docs/hardware-facts.md`. Không đoán chân, không đoán tần số.
2. **Mô phỏng trước, nạp sau.** Bài nào chưa qua mức đo mô phỏng thì không nạp lên kit.
3. **Mỗi kết quả phải có bộ kiểm tự chạy**, tự in `PASS`/`FAIL`. Không dựa vào việc người ngồi
   xem dạng sóng.
4. **Không tự cài phần mềm cần quyền quản trị, không tự đặt mua hàng** khi chưa được anh Công
   đồng ý.
5. Gặp **điểm dừng bắt buộc** (Phần F của đề bài) thì dừng, báo cáo, chờ trả lời. Sáu điểm
   dừng đó không phải gợi ý.

## Chuỗi công cụ: XONG, không kiểm lại nữa

Giai đoạn dựng công cụ **đã kết thúc ngày 01/10/2026**. Sáu công cụ đều chạy được, phiên bản đọc
từ chính lệnh:

| Công cụ | Phiên bản | Ở đâu |
|---|---|---|
| `yosys` | 0.69+post | `/opt/homebrew/bin` |
| `nextpnr-himbaechel` | nextpnr-0.11.1-40 | `~/.eide/cong-cu/oss-cad-suite/bin` |
| `gowin_pack` | Apicula trong gói | `~/.eide/cong-cu/oss-cad-suite/bin` |
| `openFPGALoader` | v1.1.1 | `~/.eide/cong-cu/oss-cad-suite/bin` |
| `verilator` | 5.052 | `/opt/homebrew/bin` |
| `riscv64-unknown-elf-gcc` | 14.2.0 | `/opt/homebrew/bin` |

**Đừng gọi `env.check` hay `tool.install` cho nhóm `fpga-gowin` nữa** trừ khi một lệnh thật sự
báo lỗi "không tìm thấy". Việc kiểm lại chuỗi công cụ đã làm xong và ghi xong.

## Khi EIDE thiếu năng lực

Dự án này cố ý vượt ra ngoài những gì EIDE từng làm. Phần HDL — tổng hợp Verilog, mô phỏng
Verilog, đóng gói bitstream, nạp FPGA — EIDE **chưa có công cụ nào**, dù sáu chương trình ở bảng
trên đã nằm trên máy.

Khi gặp chỗ EIDE không làm được thì **nói ra trong câu trả lời**, nói rõ thiếu cái gì, rồi làm
tiếp phần không phụ thuộc chỗ thiếu ấy. Đừng đi đường tắt bằng lệnh hệ thống.

Chuyện ghi nhật ký nâng cấp: `tai-lieu/NANG-CAP-AGENT.md` **anh Công tự ghi**. Đừng tự mở tệp ấy
ra viết — nó đã đủ, và mỗi lượt viết lại nó là một lượt không làm việc chính.

## Một lượt, một việc

Phiên này đã mất bốn lượt vì lời giao việc dài: Agent bám vào phần đầu của câu, hoặc làm lại việc
của lượt trước. Nên quy ước: **mỗi lượt làm đúng việc được nêu ở lượt đó**, và nếu câu giao việc
có nhiều phần thì làm phần được viết là "lượt này".
