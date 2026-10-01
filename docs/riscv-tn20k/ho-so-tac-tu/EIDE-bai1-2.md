# Lõi RISC-V trên Sipeed Tang Nano 20K — BÀI 1

Đề bài đầy đủ: `tai-lieu-de-bai.md`. Giai đoạn này làm **Bài 1**.

## Đã xong, đừng làm lại

- **Chuỗi công cụ**: `yosys` 0.69 · `nextpnr-himbaechel` 0.11.1 · `gowin_pack` ·
  `openFPGALoader` 1.1.1 · `verilator` 5.052 · `riscv64-unknown-elf-gcc` 14.2.0. Đừng kiểm
  lại, đừng cài lại.
- **Bảng thông số phần cứng**: `docs/hardware-facts.md`. Chân lấy từ đó, không đoán lại.
- **Luồng bốn chặng đã chạy thông**: blinky ra `.fs` 4 618 782 byte, Fmax 301 MHz.

## Bài 1 — SoC tối thiểu in "Hello" qua UART

Một hệ trên chip gồm: CPU **PicoRV32** · **BRAM** dùng chung lệnh và dữ liệu · **UART TX**.
Chương trình C chạy trên CPU in chuỗi ra máy tính.

Bản đồ địa chỉ (đề bài mục Bài 1, điểm 3):

| Địa chỉ | Thiết bị | Truy cập |
|---|---|---|
| `0x0000_0000` – đỉnh BRAM | BRAM | đọc/ghi |
| `0x1000_0000` | UART_TX: ghi 1 byte để gửi | ghi |
| `0x1000_0004` | UART_STATUS: bit 0 = 1 là đang bận | đọc |
| `0x2000_0000` | LED: 6 bit thấp | ghi |

Địa chỉ không hợp lệ: vẫn trả `mem_ready` để CPU không treo, đọc ra 0.

Tham số CPU: `ENABLE_COUNTERS=1`, `ENABLE_COUNTERS64=1`, `ENABLE_MUL=0`, `ENABLE_DIV=0`,
`ENABLE_PCPI=0`, `COMPRESSED_ISA=0`, `PROGADDR_RESET=0`, `STACKADDR` = đỉnh BRAM.

UART: 115200 baud, 8N1, mức nghỉ 1. Bộ chia từ 27 MHz: 27 000 000 / 115 200 ≈ 234,375 → dùng
**234**, sai số ≈ +0,16 %. Tham số hoá theo tần số clock.

## Công cụ

Nhóm `hdl.*` không nằm trong bộ thấy sẵn. Mở bằng `tool.search{query: "hdl"}` một lần ở đầu
phiên. Phần mềm RISC-V dịch bằng `build.compile` với `isa="rv32i"` — nó tự sinh tệp hex cho
`$readmemh`.

## Luật

1. **Mô phỏng trước, nạp sau.** Chưa qua `hdl.sim` thì không tổng hợp để nạp.
2. **Testbench phải tự in `PASS`/`FAIL`.** Không dựa vào người xem dạng sóng.
3. **Mỗi chặng ăn đầu ra của chặng trước.** Chặng nào đỏ thì sửa rồi chạy lại đúng chặng đó.
4. **Chân và hằng số phần cứng lấy từ `docs/hardware-facts.md`**, không đoán.

## Bài 2 — nhân ma trận, đo số chu kỳ

Mục tiêu: có **đường cơ sở** để Bài 3 so vào. Tính C = A × B cho ma trận N×N trên chính CPU của
Bài 1, đo chính xác số chu kỳ cho từng cách viết và từng cấu hình CPU.

| | |
|---|---|
| Kích thước | N ∈ {4, 8, 16, 32} |
| Kiểu dữ liệu | **I8** (A, B là `int8_t`, C là `int32_t`) · **I32** (cả ba đều `int32_t`) |
| Cách viết | V0 ba vòng i-j-k · V1 thứ tự i-k-j · V2 = V1 + mở vòng trong ×4 · V3 chia khối (chỉ N ≥ 16) |
| Cấu hình CPU | H0 `rv32i` · H1 `ENABLE_MUL=1` · H2 `ENABLE_FAST_MUL=1` |

Đo bằng `rdcycle`/`rdcycleh` ngay trước và sau lời gọi hàm, **trừ đi chi phí của chính phép
đọc** (đo riêng bằng hai lần đọc liền nhau), mỗi phép đo chạy 3 lần lấy giá trị nhỏ nhất.

Một dòng kết quả mỗi phép đo, để máy đọc được:

```
RESULT,n=16,dtype=I8,ver=V1,hw=H2,cycles=123456,macs=4096,cpm=30.14,chk=0x1A2B3C4D,ok=1
```

`cpm` = chu kỳ trên mỗi phép nhân-cộng, số MAC = N³. `ok=1` khi tổng kiểm khớp đáp án.

**Dùng Verilator**, không dùng Icarus — đề bài nói rõ Icarus quá chậm với H0 ở N=32. Đã đo:
Verilator chạy testbench SoC của Bài 1 trong 4 giây.

Số đo tài nguyên ba cấu hình, **đã đo**, đừng đo lại:

| | LUT | FF | DSP |
|---|---|---|---|
| H0 | 2 239 | 628 | không |
| H1 | 2 554 (+315) | 907 (+279) | không |
| H2 | 2 271 (+32) | 785 (+157) | 1× MULT36X36 |

## Bài 3 — lệnh tuỳ biến và đơn vị vector mini

Mục tiêu: giảm số chu kỳ trên mỗi phép nhân-cộng của bài nhân ma trận **I8**, bằng phần cứng
gắn vào CPU qua giao diện đồng xử lý **PCPI**. Ba nấc, mỗi nấc gần hơn với mô hình vector RVV.

Bật `ENABLE_PCPI=1`. Tín hiệu vào khối: `pcpi_valid`, `pcpi_insn`, `pcpi_rs1`, `pcpi_rs2`.
Trả về: `pcpi_wr`, `pcpi_rd`, `pcpi_wait`, `pcpi_ready`.

**Phải đọc README của PicoRV32 để xác minh giao thức**, nhất là ba điểm đề bài nêu:
(a) phối hợp thế nào khi đồng thời bật bộ nhân nội bộ — `ENABLE_MUL`/`ENABLE_FAST_MUL` cũng
dùng PCPI bên trong; (b) thời hạn trả lời trước khi CPU báo lệnh không hợp lệ; (c) cách giữ CPU
chờ bằng `pcpi_wait`. Đừng đoán ba điểm này.

Mã lệnh: vùng **custom-0** = `0001011`, định dạng R, `funct7 = 0000000`.

| `funct3` | Lệnh | Nghĩa | Nấc |
|---|---|---|---|
| 000 | `acc.clr` | acc ← 0 | 3a |
| 001 | `mac rs1, rs2` | acc ← acc + rs1 × rs2 (có dấu, 32 bit) | 3a |
| 010 | `acc.rd rd` | rd ← acc | 3a |
| 011 | `dot4 rs1, rs2` | acc ← acc + Σ int8(rs1[8i+7:8i]) × int8(rs2[8i+7:8i]) | 3b |

Trong C gọi bằng `.insn r 0x0B, funct3, 0, rd, rs1, rs2`, gói trong macro ở
`bai3/sw/custom_insn.h`. **Không sửa trình biên dịch.**

### Kiểm chứng cho mọi nấc

- **Testbench đơn vị** cho khối tăng tốc, so với mô hình tham chiếu viết ngay trong testbench,
  **ít nhất 1 000 bộ giá trị ngẫu nhiên**, gồm các giá trị biên **−128** và **127**.
- **Testbench hệ thống** chạy nhân ma trận đầy đủ, dùng lại `gen_data.py` và tổng kiểm của Bài 2.
- Kết quả ghi thêm vào bảng với `hw` = `P3a`, `P3b`, `P3c`.

### Mục tiêu số

Nấc 3b phải đạt **cpm ≤ ½ cpm của H2 tốt nhất** (I8, N=16). Không đạt thì phải phân tích nút
thắt bằng cách đếm chu kỳ nạp/ghi so với chu kỳ tính — **không được im lặng bỏ qua**.

### Điểm dừng bắt buộc

Nấc **3c** (đơn vị vector mini): `docs/bai3-arch.md` phải được anh Công **duyệt trước khi viết
một dòng RTL nào**. Đó là điểm dừng số 4 của đề bài.
