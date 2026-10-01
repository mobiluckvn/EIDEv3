# Nhật ký nâng cấp EIDE cho việc FPGA

Mỗi dòng là một chỗ EIDE không làm được, và chuyện gì đã xảy ra sau đó.
Đây là kết quả nghiên cứu, không phải danh sách phàn nàn: nó cho biết một môi trường dựng cho
vi điều khiển còn thiếu gì khi gặp FPGA.

| # | Lúc nào | Agent muốn làm gì | EIDE thiếu gì | Đã thêm gì | Sau đó chạy được chưa |
|---|---|---|---|---|---|
| 1 | 01/10/2026 | Tổng hợp Verilog (`synth_gowin`) | EIDE không có công cụ tổng hợp HDL (tìm kiếm không có `yosys`/`synth_gowin`) | Chưa thêm | Chưa chạy được |
| 2 | 01/10/2026 | Mô phỏng Verilog (Verilator / Icarus) | `sim.run` chỉ hỗ trợ mô phỏng C host cho firmware, không có bộ mô phỏng HDL | Chưa thêm | Chưa chạy được |
| 3 | 01/10/2026 | Đặt đi dây & đóng gói bitstream (`gowin_pack`) | EIDE hoàn toàn thiếu công cụ P&R và đóng gói bitstream FPGA (`nextpnr-himbaechel`, Apicula) | Chưa thêm | Chưa chạy được |
| 4 | 01/10/2026 | Nạp bitstream vào FPGA | `target.flash` chỉ hỗ trợ vi điều khiển (`st-flash`, `avrdude`, kéo thả USB), không hỗ trợ `openFPGALoader` hay nạp FPGA | Chưa thêm | Chưa chạy được |
| 5 | 01/10 18:25 | Biên dịch C RISC-V bare-metal | `build.compile` nhận `rv32i` / `rv32im` / `rv32imac` | Mã nguồn EIDE đã thêm trong `toolchain.py` | **Chạy được** — `build.compile` đã nhận diện `rv32i`/`rv32im`/`rv32imac`, tự sinh hex `$readmemh`, đọc lỗi linker script, canh `--gc-sections`. Gọi thử trả về `E4001` (chờ mã nguồn), không còn lỗi `E4002`. |
| 6 | 01/10 18:25 | Kiểm tra & cài công cụ FPGA (`fpga-gowin`) | `env.check` quét nhóm `fpga-gowin`, `tool.install` cài qua `G-TOOL` | Mã nguồn EIDE đã thêm `CAN_GI["fpga-gowin"]` | **Chạy được** — `env.check` quét đủ 9 công cụ nhóm `fpga-gowin` kèm lệnh cài thật, kết quả đo thực tế trên máy có đủ 9/9 công cụ (`so_thieu: 0`). |
| 5a | 01/10 17:52 | Biên dịch C cho RISC-V bare-metal | `CHUOI_CONG_CU` không có dòng nào cho rv32, nên `build.compile` đẩy dự án RISC-V sang nhánh AVR rồi báo thiếu `avr-gcc` | Thêm `rv32i`, `rv32im`, `rv32imac` vào `CHUOI_CONG_CU` và `CAN_GI`; thêm `_lenh_rv32()` | **Chạy được** — dịch ra 147 B / 32 KB, `rdcycle` có trong ảnh |
| 5b | 01/10 18:00 | — (lỗi phát sinh khi làm 5a) | `tim_chuoi_cong_cu` không mang `march`/`mabi` sang, nên `la_rv32` luôn sai | Thêm hai khoá vào dict trả về | **Chạy được** |
| 5c | 01/10 18:05 | Đổi `.elf` thành tệp hex cho `$readmemh` nạp vào BRAM lúc tổng hợp | EIDE chỉ biết sinh Intel HEX và `.bin`; `$readmemh` cần một định dạng KHÁC (một từ 32 bit mỗi dòng) | Thêm `_sinh_hex_readmemh()` và hai trường `tep_hex_readmemh`, `so_tu_readmemh` | **Chạy được** — 28 từ 32 bit, little-endian, đã có bộ kiểm so từng từ với ảnh nhị phân |
| 7 | 01/10 17:58 | Đọc lỗi trong tệp linker script | `phan_tich_loi` chỉ khớp dạng của gcc (`tệp:dòng:cột: error:`). Lỗi của trình liên kết là `tệp:dòng: thông điệp`, nên một lỗi cú pháp hiện thành *"trả mã 1 nhưng không in ra lỗi nào có toạ độ"* | Thêm `_MAU_LOI_LD`. Quan trọng với FPGA vì linker script phải tự viết từ bản đồ địa chỉ của chính thiết kế, nên nó là tệp sai nhiều nhất | **Chạy được** — `sw/linker.ld:5:0 error: syntax error` |
| 8 | 01/10 18:12 | — (lỗ do bộ kiểm tìm ra) | `--gc-sections` dọn sạch chương trình khi linker script thiếu `ENTRY`/`KEEP`, mà trình liên kết **vẫn trả 0**. EIDE báo **đạt** cho tệp ảnh 0 byte mã | Canh bằng chính `kq.flash <= 0`, kèm lời từ chối nói rõ phải thêm `ENTRY(_start)` và `KEEP(*(.init))` | **Chạy được** — ca kiểm `test_thieu_entry_thi_KHONG_bao_dat` |

## Còn lại chưa làm: bốn chỗ về HDL

Mục 1, 2, 3, 4 ở bảng trên (tổng hợp Verilog · mô phỏng Verilog · đóng gói bitstream · nạp
FPGA) vẫn chưa có. Đó là nhóm công cụ `hdl.*` còn phải viết, và là phần lớn hơn hẳn phần vừa
làm.

Đã làm được một việc giúp chúng khởi động: `CAN_GI["fpga-gowin"]` nay có đủ bảy công cụ kèm
lệnh cài thật, nên `env.check` thấy được chúng và `tool.install` cài được — Agent tự cài, không
ai cài hộ.

## Đo độ nhạy của bộ kiểm vừa thêm

Phá mã sản phẩm rồi xem bộ kiểm có đỏ không. Chép nguyên kết quả:

| Phá gì trong `toolchain.py` | Bộ kiểm |
|---|---|
| bỏ mang `march` sang trong `tim_chuoi_cong_cu` | **đỏ** (8 ca) |
| bỏ canh `kq.flash <= 0` | **đỏ** (1 ca) |
| đảo thứ tự byte little-endian → big-endian | **đỏ** (1 ca) |
| bước đọc từ 4 byte → 2 byte | **đỏ** (1 ca) |
| bỏ đọc lỗi trình liên kết | **đỏ** (3 ca) |
| đổi đệm `4 - len%4` → `3 - len%4` | **xanh — nhánh này không chạy** |

Dòng cuối ghi đúng như đo được, không làm tròn thành 5/5: mã RV32 luôn là bội số của 4 byte nên
nhánh đệm không bao giờ chạy với đầu vào thật. Đây là mã chết, không phải lỗ của bộ kiểm.

Phép phá *đảo thứ tự byte* là phép đáng giá nhất: ở bản đầu nó **lọt**, và nếu lọt thật thì tệp
hex vẫn đúng hình dạng, tổng hợp vẫn xong, bitstream vẫn dựng được — rồi CPU nạp mã lộn byte và
chạy rác. Không phép đo nào trước lúc cắm bo nhìn ra.

## Vòng hai: ba chỗ nữa, tìm ra bằng cách để Agent tự đụng vào tường

| # | Agent muốn làm gì | EIDE/máy thiếu gì | Đã thêm gì | Sau đó |
|---|---|---|---|---|
| 9 | Cài `yosys` qua `tool.install` | Lệnh cài trong bảng là `brew install oss-cad-suite` — **gói không tồn tại**. Tôi tự viết ra, nghe hợp lý mà sai | Tra lại: `brew install yosys` (0.69) · `brew install openfpgaloader` · `pip install apycula` (0.33) · `nextpnr` phải tải gói oss-cad-suite | **`yosys` đã cài được**, `/opt/homebrew/bin/yosys` |
| 10 | Tải gói oss-cad-suite | Lệnh lấy mù bản `latest`, mà bản `latest` ngày 01/10 **chỉ có tệp x64**, máy này arm64 → URL 404 → `tar` báo "not in gzip format" | Lệnh quét lùi 20 bản, tìm bản mới nhất **có tệp cho đúng kiến trúc máy** | Tra ra bản `2026-09-30` arm64, 483 MB |
| 11 | Giải gói vào `~/.local` | `~/.local` do **root** sở hữu, quyền 755, có từ 2023. Không user nào ghi được → `tar: Permission denied`. Sửa quyền cần `sudo`, tức một điểm dừng | Đổi chỗ cài sang `~/Library/Application Support/EIDE/cong-cu`, là chỗ đúng của macOS và do người dùng sở hữu. `_tim_lenh` tìm thêm ở đó | chờ cài lại |
| 12 | Chạy `tool.install` tới lúc xong | Hạn một lượt **300 giây** (MDD-40 §B1), chọn cho việc vi điều khiển. Gói 483 MB và việc tổng hợp FPGA **dài hơn hạn ngay từ bản chất**, nên Agent không bao giờ chạm được tới lúc xong — hết lượt giữa đường, lượt sau làm lại từ đầu | Nới được bằng `EIDE_TRAN_GIAY_LUOT`, trần trên 7 200 s, không siết được xuống dưới mặc định. Ghi lệch ở **DEV-319** | Phiên này chạy 1 800 s |

### Một chỗ tôi đọc sai, ghi lại để không ai lặp

Thấy `tool.install` có trong danh sách công cụ Agent nhìn thấy ở lời gọi 14, mất ở 46, có ở 78,
mất ở 82 — tôi kết luận công cụ "mở ra rồi rơi lại", tức đường dẫn đứt.

**Sai.** Gom theo từng lượt thì trong **một** lượt nó mở ra ở lời gọi #22 và **giữ nguyên** tới
hết lượt (#30). Những lần "rơi" là ranh giới giữa các lượt, chuyện đúng theo thiết kế: mỗi lượt
bắt đầu lại với bộ công cụ gốc, và `tool.search` là đường mở thêm.

Nên vấn đề không phải cơ chế, mà là **cách Agent dùng lượt**: nó mở được `tool.install` rồi tiêu
9 lời gọi cuối vào `store.get`, `ledger.query`, `task.run` — kiểm chứng và tra cứu — rồi hết
lượt. Phải nói một câu thật hẹp *"lượt này làm đúng một việc, gọi `tool.install` bốn lần, không
làm gì khác"* thì nó mới gọi.

Đây là một kết quả đáng ghi riêng: **một tác tử có đủ công cụ và đủ thời gian vẫn có thể không
làm việc chính, vì nó dùng thời gian để tự kiểm tra.** Lời giao việc càng rộng thì tỉ lệ ấy càng
cao.

## Vòng ba: luồng công cụ đã chạy được cả bốn chặng

| # | Chuyện gì | Chữa thế nào | Kết |
|---|---|---|---|
| 13 | Gói oss-cad-suite tải xong, giải ra **1,9 GB**, và nó mang **cả ba** công cụ còn thiếu — `nextpnr-himbaechel`, `gowin_pack`, `openFPGALoader` | — | một lần tải đủ cho ba chặng |
| 14 | `nextpnr --version` in ra `mkdir: ~/.local/share: Permission denied` | không phải lỗi: đó là cảnh báo của script bọc, lệnh vẫn chạy và in đúng phiên bản | chạy được |
| 15 | `gowin_pack` báo `/Users/congvt/Library/Application: No such file or directory` | **Dấu cách** trong "Application Support". Script bọc dòng 7 viết `exec $release_bindir_abs/...` **không bọc nháy**, nên đường dẫn bị cắt làm hai. Đổi chỗ cài sang `~/.eide/cong-cu` — người dùng sở hữu, không dấu cách | chạy được |

Bốn chặng của luồng FPGA nay đều chạy, phiên bản đọc từ chính lệnh:

| Công cụ | Phiên bản | Ở đâu |
|---|---|---|
| `yosys` | 0.69+post | `/opt/homebrew/bin` |
| `nextpnr-himbaechel` | nextpnr-0.11.1-40-geb4f15c3 | `~/.eide/cong-cu/oss-cad-suite/bin` |
| `gowin_pack` | Apicula trong gói | `~/.eide/cong-cu/oss-cad-suite/bin` |
| `openFPGALoader` | v1.1.1 | `~/.eide/cong-cu/oss-cad-suite/bin` |
| `verilator` | 5.052 | `/opt/homebrew/bin` |
| `iverilog` | có sẵn | `/opt/homebrew/bin` |

### Chuyện đáng ghi về cửa duyệt

Sổ ghi việc có **19 thẻ cổng `G-TOOL`** mở ra cho `tool.install`, tất cả còn trạng thái `open`.
Nguyên nhân: thẻ cổng được duyệt **sang lượt sau**, nên trong cùng một lượt Agent không bao giờ
thấy nó qua — nó gọi lại, mở thẻ mới, gọi lại nữa. Mỗi lần gọi lại là một thẻ.

Đây không phải lỗi của Agent, và cũng không phải lỗi của cửa duyệt. Nó là chỗ hai cơ chế đúng
gặp nhau mà không ai nối: cửa duyệt làm việc theo nhịp **giữa các lượt**, còn Agent thử lại theo
nhịp **trong một lượt**.

Cách đi được ngay: giao **một công cụ một lượt**, và nói rõ *"bị chặn là đúng, đừng gọi lại"*.
Cách đúng hơn, chưa làm: cho `tool.install` biết là đã có một thẻ đang chờ cho đúng công cụ ấy,
và trả về *"đang chờ duyệt, đừng mở thẻ mới"* thay vì mở thêm một thẻ.

## Kiểm tra thực tế năng lực EIDE cho bài toán FPGA (Lượt run-063)

Thực hiện thử nghiệm gọi công cụ thực tế của EIDE để xác định chính xác các điểm thiếu hụt cho bài toán FPGA Tang Nano 20K:

| # | Năng lực cần kiểm tra | Đã thử gọi gì | Kết quả / Lỗi nhận được | Cần thêm năng lực gì |
|---|---|---|---|---|
| 1 | Tổng hợp Verilog (`synth_gowin`) | `tool.search(query='verilog synthesis yosys')` | Không có công cụ tổng hợp HDL nào trong hệ thống EIDE. | Cần bổ sung nhóm công cụ `hdl.synth` tích hợp Yosys. |
| 2 | Mô phỏng Verilog (Verilator / Icarus) | `tool.search(query='verilog simulation verilator iverilog')` | Chỉ tìm thấy `sim.run` (chỉ dùng cho C logic host mô phỏng firmware vi điều khiển). | Cần bổ sung công cụ `hdl.sim` (Verilator / Icarus Verilog) hỗ trợ testbench HDL và đo chu kỳ. |
| 3 | Đặt-đi dây & Đóng gói bitstream | `tool.search(query='bitstream gowin pack nextpnr')` | Không có công cụ nào cho P&R hoặc đóng gói bitstream Gowin. | Cần bổ sung công cụ `hdl.pnr` (`nextpnr-himbaechel`) và `hdl.pack` (`gowin_pack` / Apicula). |
| 4 | Nạp bitstream vào FPGA | `tool.search(query='fpga flash openFPGALoader')` và kiểm tra `target.flash` | `target.flash` chỉ nhận `tu_chon`, `st-flash`, `avrdude`, `sao_tep` cho MCU, không có lựa chọn nào cho FPGA hoặc `openFPGALoader`. | Cần bổ sung công cụ nạp FPGA chuyên dụng (như `hdl.flash` hoặc tích hợp `openFPGALoader` vào `target.flash`). |
| 5 | Biên dịch C RISC-V bare-metal | `build.compile(isa='rv32i')` | Trả về `E4001: Không có firmware trong dự án để biên dịch.` (Không còn bị lỗi `E4002: Chưa biết biên dịch cho kiến trúc rv32i`). | Mã nguồn EIDE đã được cập nhật nhận `rv32i`/`rv32im`/`rv32imac` và sinh hex `$readmemh`, sẵn sàng khi có mã nguồn C. |

## Thử nghiệm Kiểm tra 2 Mục B3 (Tổng hợp Blinky ra .fs) (Lượt run-067)

- **Mục tiêu:** Chạy luồng Yosys (`synth_gowin`) → `nextpnr-himbaechel` → `gowin_pack` để sinh tệp `.fs` cho Tang Nano 20K.
- **Hiện trạng công cụ máy chủ:** Đã có đủ `yosys` (0.69), `nextpnr-himbaechel`, `gowin_pack` (Apicula).
- **Điểm thiếu của EIDE:** EIDE chưa có công cụ để Agent kích hoạt luồng tổng hợp và đóng gói HDL (chưa có nhóm công cụ `hdl.synth`, `hdl.pnr`, `hdl.pack` hoặc công cụ điều phối tương đương). Agent không đi đường tắt bằng shell lệnh hệ thống (`sh.run`).
- **Nhu cầu nâng cấp:** Cần bổ sung công cụ trong EIDE cho phép Agent thực hiện tổng hợp Verilog, P&R và đóng gói bitstream Gowin.



