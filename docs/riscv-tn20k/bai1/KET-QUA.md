# Bài 1 — SoC tối thiểu in "Hello" qua UART

*01/10/2026. Mô phỏng PASS, tổng hợp ra bitstream. Chưa thử trên kit — chưa có kit.*

## Nghiệm thu của đề bài

| Mục | Đòi hỏi | Đo được |
|---|---|---|
| Mô phỏng | PASS | **PASS** — testbench nhận đúng chuỗi hai lần |
| Fmax | ≥ 27 MHz | **134,93 MHz** |
| Cảnh báo chốt / nhiều nguồn | không có | **không có** trong mã tự viết |
| Trên kit | thấy chuỗi lặp, LED nháy | **chưa có kit** |

## Thứ testbench thật sự nhận được

Không phải một ô xanh — đây là chuỗi mà bộ thu UART trong testbench giải mã ra, từng bit một,
lấy mẫu ở giữa mỗi bit theo đúng baud 115200:

```
Hello from PicoRV32 on Tang Nano 20K, cycle=126
```

Tức CPU RISC-V thi hành mã C đã dịch, ghi byte vào `0x1000_0000`, khối UART đẩy ra nối tiếp, và
testbench ghép lại thành chữ. `PASS` chỉ in sau khi nhận đủ **hai** lần — một lần không chứng
minh vòng lặp chạy tiếp.

## Tài nguyên thật trên silicon

Số của `nextpnr`, không phải số ước lượng của khâu tổng hợp:

| | Dùng | Tổng | |
|---|---|---|---|
| LUT4 | **2 180** | 20 736 | 10,5 % |
| Flip-flop | **820** | 15 552 | 5,3 % |
| **BSRAM** | **16** | 46 | **34,8 %** |
| ALU | 404 | 15 552 | 2,6 % |
| Chân vào-ra | 9 | 384 | 2,3 % |

**BRAM 32 KB vừa chip**, không phải hạ xuống 16 KB như đề bài dự phòng.

## Phần mềm

| | |
|---|---|
| Mã + dữ liệu | **445 B** / 32 768 B (1,4 %) |
| Tệp hex cho `$readmemh` | **102 từ** 32 bit, little-endian |
| Dịch bằng | `build.compile` với `isa="rv32i"` → `-march=rv32i_zicsr -mabi=ilp32` |

## Hai chỗ suýt thành lỗi im lặng

**Chân UART trong tệp ràng buộc.** Bản đầu của `.cst` chỉ có clock và LED. Thiếu chân UART thì
nextpnr **tự chọn** một chân nào đó, bitstream vẫn dựng xong, nạp lên bo vẫn chạy — và không
một chữ nào ra cổng nối tiếp. Mọi ô đều xanh. Nay `.cst` có TX chân 69, RX chân 70, nút chân
88, lấy từ bảng thông số đã xác minh.

**Ghi từng byte theo `mem_wstrb`.** Thiếu nó thì lệnh `sb` ghi hỏng ba byte bên cạnh, và lỗi
chỉ hiện khi chương trình dùng chuỗi ký tự — tức đúng lúc in "Hello".

## Tệp

| | |
|---|---|
| `rtl/` | `bram.v` · `uart_tx.v` · `soc_top.v` |
| `sw/` | `start.S` · `linker.ld` · `main.c` · `mach.hex` |
| `sim/` | `tb_soc.v` — có bộ thu UART tự giải mã |
| Bitstream | `soc_top.fs`, **7 261 470 byte** |
