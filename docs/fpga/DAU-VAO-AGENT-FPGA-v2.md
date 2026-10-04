# Giao việc: lõi RISC-V trên FPGA Sipeed Tang Nano 20K

**Bản 2.0 · 03/10/2026**

| | |
|---|---|
| Người giao việc | Sinh viên làm đồ án, ngành điện tử — chưa từng dựng CPU trên FPGA |
| Người thực hiện | Tác tử EIDE |
| Thay cho | [`yeu-cau-agent-riscv-tang-nano-20k.md`](yeu-cau-agent-riscv-tang-nano-20k.md) bản 1.1 |

Bản 1.1 để 10 trong 12 dòng thông số phần cứng ở trạng thái *cần tra*. Mình đã đi tra hết rồi,
nên bản này không còn ô nào phải tự tìm. Phần còn lại — thiết kế, viết mã, đo — thì vẫn là việc
của bạn.

---

## 1 · Mình muốn gì

Mình đang làm đồ án về đưa phép nhân ma trận xuống phần cứng. Trước khi nói chuyện phần cứng
chuyên dụng, mình cần một **đường cơ sở**: nhân ma trận chạy trên một CPU thường thì tốn bao
nhiêu chu kỳ máy.

Nên hai bài, làm theo thứ tự:

| Bài | Việc |
|---|---|
| **1** | Dựng một SoC nhỏ nhất chạy được: CPU RISC-V + bộ nhớ + cổng nối tiếp. Chương trình C in một chuỗi ra máy tính mình |
| **2** | Chạy nhân ma trận bằng C trên CPU đó, **đo số chu kỳ** cho nhiều kích thước ma trận và nhiều cấu hình CPU |

Kết quả mình cần cuối cùng: một **bảng số liệu** nói cấu hình CPU nào đổi được gì, và đổi bao
nhiêu. Cộng với một kho mã mà mình chạy lại được từ đầu bằng vài lệnh `make`.

Mình **có kit thật** và sẽ cắm giúp bạn khi cần.

---

## 2 · Phần cứng — mình đã tra, bạn dùng luôn

Kit **Sipeed Tang Nano 20K**, chip Gowin **GW2AR-LV18QN88C8/I7** (family GW2A-18C, vỏ QFN88).

| # | Thông số | Giá trị | Mình lấy ở đâu |
|---|---|---|---|
| 1 | Chuỗi device cho `nextpnr` / `gowin_pack` | `GW2AR-LV18QN88C8/I7` | Sipeed wiki |
| 2 | LUT4 · Flip-Flop | **20 736** · **15 552** | Gowin DS226 |
| 3 | BSRAM | **46 khối × 18 Kbit** = 828 Kbit (~103,5 KB) | Gowin DS226 |
| 4 | Bộ nhân cứng | **48 bộ 18×18 bit** (hoặc 96 bộ 9×9) | Gowin DS226 |
| 5 | Thạch anh · chân clock | **27 MHz** · **PIN 4** (`IOT13A`) | Sơ đồ nguyên lý Sipeed |
| 6 | 6 chân LED | **PIN 15–20** (LED0–LED5), **tích cực thấp** (ghi 0 thì đèn sáng) | Sipeed wiki |
| 7 | Nút S1 · S2 | **PIN 88** (`IOB3B`) · **PIN 87** (`IOB3A`), tích cực thấp | Sipeed wiki |
| 8 | UART tới chip cầu BL616 | FPGA phát **PIN 69** (`IOB20A`) · FPGA nhận **PIN 70** (`IOB20B`), 3,3 V LVCMOS | Sipeed wiki |
| 9 | Cổng nối tiếp trên macOS | Chip cầu BL616 cấp **hai** giao diện USB. Mình chưa rõ cổng nào làm gì — bạn tự xác định rồi ghi lại | Sipeed wiki |
| 10 | Chân đa chức năng | MSPI (PIN 48, 49, 79, 80) và JTAG — cần bật cờ dual-purpose nếu muốn dùng làm I/O thường | Gowin UG290 |
| 11 | PLL từ 27 MHz | VCO 400–1000 MHz; sinh được 27, 54, 81 MHz | Gowin UG286 |
| 12 | Kho ví dụ chính thức | `github.com/sipeed/TangNano-20K-example` | Sipeed |

**Một chỗ mình muốn bạn để ý ở dòng 12:** kho đó có sẵn **một ví dụ PicoRV32 cho chính con bo
này**. Mình nghĩ nên đối chiếu bảng chân của bạn với tệp ràng buộc trong ví dụ ấy trước khi
dựng — nó là thiết kế tham chiếu gần nhất có thể có.

**Và dòng 9 mình để trống có chủ ý.** Mình không biết trong hai cổng ấy cổng nào dùng để nạp,
cổng nào để đọc chữ. Bạn xác định bằng cách đo, rồi ghi vào `docs/hardware-facts.md` kèm cách
bạn xác định.

---

## 3 · Bài 1 — SoC in chuỗi qua cổng nối tiếp

### Phần cứng cần dựng

**CPU:** mình đọc thì thấy nên dùng **PicoRV32** (Verilog) — nó nhỏ, và nó có bộ đếm chu kỳ
`rdcycle`, thứ mà Bài 2 bắt buộc phải có. Tham số:

```
ENABLE_COUNTERS=1    ENABLE_COUNTERS64=1
ENABLE_MUL=0         ENABLE_DIV=0        ENABLE_PCPI=0
COMPRESSED_ISA=0     PROGADDR_RESET=0    STACKADDR = đỉnh BRAM
```

**Bộ nhớ:** một khối BRAM dùng chung lệnh và dữ liệu. Nhắm **32 KB**, giảm xuống 16 KB nếu
BSRAM không đủ. Phải ghi được từng byte theo `mem_wstrb`.

**Chương trình nạp vào bộ nhớ lúc tổng hợp** bằng `$readmemh`. SoC này không có cổng nhận, cũng
không có bootloader — nên không có cách nào đưa chương trình vào lúc đang chạy. Bạn cân nhắc
điều này khi lập kế hoạch cho Bài 2.

**Bản đồ địa chỉ:**

| Địa chỉ | Thiết bị | Truy cập |
|---|---|---|
| `0x0000_0000` – đỉnh BRAM | BRAM | đọc/ghi |
| `0x1000_0000` | UART_TX: ghi 1 byte để gửi | ghi |
| `0x1000_0004` | UART_STATUS: bit 0 = 1 nghĩa là đang bận gửi | đọc |
| `0x2000_0000` | LED: 6 bit thấp | ghi |

Địa chỉ không hợp lệ thì **phải trả `mem_ready`** để CPU không treo, và đọc ra 0.

**UART TX:** 115 200 baud, 8N1, mức nghỉ = 1. Tham số hoá bộ chia theo tần số clock, để đổi PLL
thì không phải sửa tay.

**Clock và reset:** chạy thẳng 27 MHz, chưa dùng PLL. Reset gồm **giữ reset vài chục chu kỳ sau
cấp nguồn** và **nút S1**.

**LED:** do phần mềm điều khiển, để nhìn biết CPU đang chạy.

### Phần mềm cần viết

- `start.S` — đặt `sp`, xoá `.bss`, gọi `main`
- `linker.ld` — đặt `.text` / `.data` / `.bss` trong BRAM, bắt đầu từ địa chỉ 0
- `main.c` — vòng lặp vô hạn, mỗi khoảng 1 giây (đo bằng `rdcycle`, 27 000 000 chu kỳ) làm hai
  việc: in `Hello from PicoRV32 on Tang Nano 20K, cycle=<số>\r\n`, và đảo một LED
- Script chuyển `.elf` → `.hex` đúng định dạng `$readmemh`: một từ 32 bit mỗi dòng,
  little-endian

Cho phép dịch với hằng "1 giây" nhỏ hơn qua `-DSIM` để mô phỏng nhanh. **Nhớ là bản nạp lên bo
phải dùng hằng thật.**

### Mô phỏng

Testbench chạy toàn SoC, có **bộ thu UART mô hình** giải mã từng bit theo đúng baud. In `PASS`
khi nhận đúng chuỗi ít nhất 2 lần, `FAIL` sau giới hạn thời gian. Đừng bắt mình ngồi xem dạng
sóng.

### Nghiệm thu Bài 1

| # | Việc | Điều kiện qua | |
|---|---|---|---|
| 1 | Mô phỏng | `PASS` | |
| 2 | Định thời | Fmax ≥ 27 MHz, không cảnh báo latch hoặc multi-driven | |
| 3 | Nạp kit, xem cổng nối tiếp | terminal hiện chuỗi lặp lại, **và LED nháy** | **cần mình** |
| 4 | Nạp flash rồi **cấp lại nguồn** | vẫn chạy | **cần mình** |

---

## 4 · Bài 2 — nhân ma trận, đo số chu kỳ

### Bài toán

Tính `C = A × B` cho ma trận vuông `N × N` trên CPU của Bài 1. Đo **chính xác số chu kỳ máy**
cho từng cách cài đặt và từng cấu hình CPU.

### Tham số thử nghiệm

**Kích thước:** `N ∈ {4, 8, 16, 32}`. Bạn tự tính dung lượng: ba ma trận × N² × kích thước phần
tử phải vừa BRAM **cùng với chương trình**. N nào không vừa thì ghi rõ và bỏ.

**Hai kiểu dữ liệu:**

| | A, B | C |
|---|---|---|
| `I32` | `int32_t` | `int32_t` |
| `I8` | `int8_t` | `int32_t` (cộng dồn) | ← kiểu của mô hình AI lượng tử hoá |

**Ba cấu hình CPU**, và **tập lệnh biên dịch phải khớp cấu hình**:

| Cấu hình | Tham số PicoRV32 | Dịch bằng |
|---|---|---|
| **H0** | `ENABLE_MUL=0`, `ENABLE_FAST_MUL=0` | `-march=rv32i_zicsr -mabi=ilp32` |
| **H1** | `ENABLE_MUL=1`, `ENABLE_FAST_MUL=0` | `-march=rv32im_zicsr -mabi=ilp32` |
| **H2** | `ENABLE_MUL=1`, `ENABLE_FAST_MUL=1` | `-march=rv32im_zicsr -mabi=ilp32` |

`_zicsr` cần cho cả ba, vì `rdcycle` là lệnh CSR.

Mình đọc thì hiểu ghép lệch tập lệnh sai theo **hai chiều**, và mình muốn bạn kiểm cả hai chiều
chứ đừng chỉ kiểm một: dịch `rv32im` cho CPU không có bộ nhân, và dịch `rv32i` cho CPU có bộ
nhân. Nghĩ xem mỗi chiều cho triệu chứng gì, rồi tìm cách tự kiểm trên mã máy.

**Bốn cách cài đặt** thuật toán, đặt tên `V0` đến `V3`. Bạn tự chọn bốn cách, nhưng nói trước
cho mình mỗi cách khác nhau ở đâu. Cách nào chỉ hợp với N lớn thì ghi rõ, và với N nhỏ thì xử
lý cho tường minh chứ đừng để nó âm thầm chạy sai.

### Cách đo — mục mình quan tâm nhất

Mình cần số chu kỳ **đo được**, không phải số ước lượng. Bốn điều mình nghĩ là bắt buộc, bạn
xem có đúng không và bổ sung nếu thiếu:

1. **Đo hiệu số, đừng đo số tuyệt đối.** Số tuyệt đối phụ thuộc lúc nào CPU khởi động.
2. **Bộ đếm chu kỳ rộng hơn 32 bit**, và xử lý trường hợp nó lật giữa hai lần đọc.
3. **Lặp nhiều lần rồi lấy một giá trị đại diện.** Bạn chọn lấy nhỏ nhất hay trung bình, nhưng
   nói lý do.
4. **Trừ chi phí của chính phép đọc bộ đếm.** Đo riêng rồi trừ ra.

### Sản phẩm

- Một dòng kết quả cho mỗi ô, khuôn cố định để công cụ đọc được:

```
RESULT,n=<N>,dtype=<I32|I8>,ver=<V0..V3>,hw=<H0|H1|H2>,cycles=<số>,macs=<số>,cpm=<số>,chk=<0x…>,ok=<0|1>
```

- `chk` là tổng kiểm của ma trận kết quả, so với **mô hình chuẩn** tính bằng Python. `ok=1` chỉ
  khi tổng kiểm khớp.
- Một tệp CSV gom hết các ô, một biểu đồ `cycles/MAC` theo N cho ba cấu hình, và một trang
  `KET-QUA.md` đọc được bằng mắt.

**Lưu ý về chương trình Bài 2:** nó tính xong rồi in kết quả **một lần rồi dừng**, không in lặp
như Bài 1. Bạn cân nhắc điều này khi lập cách bắt bản ghi cổng nối tiếp.

### Nghiệm thu Bài 2

| # | Việc | Điều kiện qua | |
|---|---|---|---|
| 1 | Mô phỏng đủ các ô | mọi ô `ok=1` | |
| 2 | Chạy trên kit thật | mọi ô `ok=1` | **cần mình** |
| 3 | Đối chiếu kit với mô phỏng | **lệch không quá 1 %** | |

---

## 5 · Cách mình muốn làm việc với bạn

### 5.1 · Mọi thông số phần cứng phải có nguồn

Không đoán chân, tần số, tên thiết bị. Bảng ở mục 2 đã đủ cho hai bài này. Cần thêm thì tra
Sipeed wiki hoặc Gowin datasheet rồi **ghi link**.

Mình nói thẳng vì sao mình nhấn mạnh: mình từng đọc một bài học là **tự nhớ hằng số phần cứng
thì sẽ tự chế ra bằng chứng sai**. Nên con số nào bạn không tra được nguồn thì nói là **chưa
biết**, đừng điền một giá trị trông hợp lý.

### 5.2 · Mô phỏng trước, nạp sau

Bài nào chưa qua tiêu chí mô phỏng thì không nạp lên kit. Gỡ lỗi trên bo đắt hơn nhiều, vì trên
bo mình chỉ thấy được những gì có đèn hoặc có cổng nối tiếp.

### 5.3 · Mỗi kết quả phải có phép đo, và phép đo phải biết báo sai

Testbench tự kiểm và in `PASS` / `FAIL`.

Và một việc nữa mình muốn bạn làm mà mình nghĩ nhiều người bỏ: **sau khi bài kiểm báo xanh, phá
mã sản phẩm rồi chạy lại.** Phép phá nào cũng phải làm bài kiểm **đỏ**. Phép nào vẫn xanh thì
bài kiểm đó không đo gì ở chỗ ấy.

Mình đọc được một câu và thấy đúng:

> Một phép đo báo đạt bất kể sản phẩm đúng hay sai thì nó không đo gì cả.

Hai chỗ mình nghe nói hay sập, bạn tự tránh:

- **Tệp kiểm chép lại logic** của mã sản phẩm thay vì dịch thẳng mã sản phẩm vào
- **Bộ sinh dữ liệu dùng lại chính hằng số** mà mã sản phẩm dùng, nên phá hằng số thì hai bên
  tự khử nhau

### 5.3b · Luật sinh dữ liệu vào — số này là của mình

Thêm 03/10 tối. Bản đầu của tài liệu này **không nêu** luật sinh dữ liệu, nên bạn phải tự
chọn — và bạn đã chọn hợp lý. Nhưng rồi `golden_checksums.h` ghi là luật ấy *theo tài liệu
đầu vào*, mà tài liệu không có dòng nào về nó. Mốc chuẩn mất chỗ đứng: nó truy về lựa chọn
của chính bạn ở một lượt trước, chứ không về một dữ kiện của mình.

Nên mình chốt vào đây, thành số của mình:

    A[i][k] = ((i + k) mod 7) + 1          giá trị trong [1, 7]
    B[k][j] = ((k * 3 + j) mod 11) - 5     giá trị trong [-5, 5]
    C[i][j] = tổng theo k của A[i][k] * B[k][j]
    chk     = với từng phần tử của C theo thứ tự hàng:  chk = (chk * 31 + C) mod 2^32

Dùng đúng luật này cho cả `I32` và `I8`: mọi giá trị của A và B đều nằm trong khoảng của
`int8_t`, nên hai kiểu cho **cùng một ma trận C và cùng một `chk`**. Một bảng tổng kiểm theo
`N` là đủ cho cả hai kiểu — nếu bạn thấy hai kiểu ra số khác nhau thì có chỗ sai, đừng sinh
hai bảng để che nó.

Mình đã tự tính bốn số này một lần nữa bằng tay, độc lập với mã của bạn:

| N | `chk` |
|---|---|
| 4 | `0xfeaabd40` |
| 8 | `0x2110c56a` |
| 16 | `0xc7ce1f03` |
| 32 | `0x36395f4b` |

Bốn số trên là tầng NGƯỜI. Mã của bạn lệch với chúng thì mã sai, không phải bảng sai.

### 5.4 · Không đổi tiêu chí sau khi đã thấy kết quả

Nêu tiêu chí nghiệm thu **trước** khi chạy. Nếu sau khi có số đo bạn thấy tiêu chí cần sửa thì
**đề xuất cho mình duyệt**, đừng tự sửa — không thì bảng nghiệm thu chỉ còn đo lại chính nó.

### 5.5 · Phân biệt "đã đo" với "suy ra"

Cái này mình quan tâm nhất, vì mình không đủ trình để kiểm từng dòng mã của bạn.

Khi bạn báo một con số, nói rõ nó **đo bằng công cụ gì**. Nếu chưa đo được thì **nói là chưa đo
được** — mình thà không có số còn hơn có một con số trông như đã đo.

Và nhớ cho mình: một công cụ báo *"xong"* nghĩa là **lời gọi đã chạy**, không nghĩa **việc đã
tới đích**. Hai thứ ấy khác nhau, và chỗ khác nhau là chỗ mình dễ bị lừa nhất.

### 5.6 · Giao một việc mỗi lượt

Mình sẽ giao từng việc một. Bạn cứ làm xong việc được giao rồi báo, đừng chạy trước sang việc
sau.

### 5.7 · Báo cáo sau mỗi bước

Năm dòng, ngắn thôi:

1. Đã làm gì
2. Bỏ gì và vì sao
3. Giả định đang dùng
4. Hoàn tác được tới đâu
5. Hết bao nhiêu lời gọi công cụ

---

## 6 · Điểm dừng bắt buộc — dừng lại và hỏi mình

1. Cần **cài phần mềm cần quyền quản trị**, hoặc cần mua gì
2. Cần **ghi vào flash trên kit** — việc này không hoàn tác được, và nó ghi đè bitstream nhà máy
3. Cần mình **cắm cáp, rút nguồn, hoặc nhìn đèn**
4. Muốn **đổi tiêu chí nghiệm thu** sau khi đã thấy kết quả
5. Một thông số phần cứng **không tra được nguồn**
6. Bạn phát hiện mình đã báo xong một việc mà thực ra chưa xong

Điểm 6 mình thêm vào, và mình mong bạn dùng nó. Nói ra thì mình không coi là lỗi.

---

## 7 · Môi trường

macOS. Ghi phiên bản macOS và kiến trúc chip vào `docs/env.md`.

| Vai trò | Công cụ |
|---|---|
| Tổng hợp, đặt-đi dây, đóng gói bitstream | Yosys (`synth_gowin`) · nextpnr-himbaechel · Apicula (`gowin_pack`) — bộ **oss-cad-suite** bản darwin |
| Nạp bitstream | **openFPGALoader**, board `tangnano20k` |
| Mô phỏng nhanh, đo chu kỳ | **Verilator** — bắt buộc cho Bài 2 |
| Mô phỏng testbench nhỏ | Icarus Verilog |
| Biên dịch RISC-V | `riscv64-unknown-elf-gcc` bare-metal |
| Mô hình chuẩn, biểu đồ | Python 3 + NumPy + matplotlib |

**Kiểm môi trường sớm**, trước khi viết dòng HDL đầu tiên:

1. In phiên bản mọi công cụ
2. Tổng hợp một ví dụ nháy LED cho bo này **tới tận tệp `.fs`** — chưa cần kit
3. Tổng hợp thử PicoRV32 trần để biết lõi chiếm bao nhiêu tài nguyên

---

## 8 · Cấu trúc kho mình muốn

```
├── README.md              # cách chạy lại toàn bộ
├── Makefile
├── docs/
│   ├── hardware-facts.md  # bảng mục 2, cộng những gì bạn tra thêm
│   ├── env.md
│   ├── decisions.md       # quyết định thiết kế + lý do
│   ├── third_party.md     # lõi ngoài + license + commit
│   └── troubleshooting.md # mỗi sự cố: triệu chứng · nguyên nhân · cách sửa
├── constraints/
├── third_party/picorv32/
├── rtl/
├── bai1/  bai2/           # mỗi bài: rtl/ sw/ sim/ results/
└── tools/
```

Lệnh `make` chuẩn cho mỗi bài: `sw` · `sim` · `bitstream` · `load` · `flash` · `term`.

`docs/troubleshooting.md` mình muốn bạn ghi **trong lúc làm**, không phải viết lại ở cuối. Mỗi
sự cố ba dòng: thấy gì, vì sao, sửa thế nào.
