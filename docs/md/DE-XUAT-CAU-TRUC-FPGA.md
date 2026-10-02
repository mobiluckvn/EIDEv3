# Đề xuất: tổ chức một đề án FPGA nhiều bài, và hiện nó lên màn hình

*02/10/2026. Anh Công nêu: màn hình Thiết kế trắng xoá, và cấu trúc hiện tại không cho thấy
đây là **một solution gồm ba dự án dùng chung một số thứ**, mỗi dự án lại có **hai tầng thiết
kế** — thiết kế chip trên FPGA, rồi thiết kế phần mềm chạy trên chip ấy.*

Nhận xét ấy đúng, và nó chỉ ra hai vấn đề khác nhau. Tôi tách riêng.

---

## Phần 1 — Vì sao màn hình Thiết kế trắng

**Không phải vì thiếu dữ liệu.** Kho của dự án có sẵn:

| Mục trong kho | Bản | Nội dung |
|---|---|---|
| `build:hdl:synth` | v7 | số ô sau tổng hợp, bảng chi tiết từng loại |
| `build:hdl:pnr` | v5 | **tài nguyên thật trên silicon + Fmax đo được** |
| `build:hdl:bitstream` | v5 | tệp `.fs`, kích thước, mã chip |
| `build:hdl:sim` | v3 | kết quả testbench, PASS/FAIL |

28 mục tất cả. Màn hình trắng vì **tab A5 Thiết kế dựng cho một loại dự án khác**: nó có khối
danh sách linh kiện, khối bản đồ mạch, khối sơ đồ nguyên lý — ba thứ của một bo mạch in. Không
khối nào đọc `build:hdl:*`.

Đây đúng cái mẫu dự án này gặp đi gặp lại: **cơ chế có sẵn, đường dẫn tới nó đứt.**

---

## Phần 2 — Một đề án FPGA có hai tầng thiết kế, và thứ tự giữa chúng là thật

Anh Công nói đúng chỗ cốt lõi: với FPGA, **chip chưa tồn tại cho tới khi ta thiết kế nó**. Nên
quan hệ là:

```
Thiết kế chip (HDL)  ──tổng hợp──▶  chip có thật  ──▶  Thiết kế phần mềm CHẠY TRÊN chip ấy
     │                                                          │
     └── bản đồ địa chỉ, chân, tần số ◀──────── phần mềm dựa vào đúng những thứ này
```

Với vi điều khiển thì tầng trên là **cho sẵn** (datasheet), nên EIDE chưa bao giờ phải mô hình
hoá nó. Với FPGA thì tầng trên là **sản phẩm của chính ta**, và nó thay đổi — nâng BRAM từ 32
lên 64 KB là đổi chip, và linker script của phần mềm phải đổi theo.

Hệ quả: **bản đồ địa chỉ là hiện vật dùng chung của hai tầng.** Hiện nó chỉ nằm trong chú thích
của `soc_top.v` và trong `EIDE.md`, hai chỗ không ai đối chiếu được.

---

## Phần 3 — Đề xuất cấu trúc thư mục

### Hiện tại

```
riscv-tn20k-b/
├── rtl/              bram.v  uart_tx.v  soc_top.v  blinky.v
├── third_party/picorv32/
├── constraints/      tangnano20k.cst
├── docs/             hardware-facts.md  env.md  nang-luc-kit.md  third_party.md
├── bai1/  sw/  sim/
├── bai2/  sw/  sim/  tools/
└── bai3/  rtl/  sim/        (nay ngoài phạm vi)
```

Ba chỗ không nói lên cấu trúc thật:

1. **`rtl/` ở gốc trộn hai thứ**: `soc_top.v`, `bram.v`, `uart_tx.v` là xương sống dùng chung;
   `blinky.v` là bài thử riêng. Nhìn vào không biết cái nào chung cái nào riêng.
2. **Bài 1 không có thư mục của mình cho phần chip** — RTL của nó nằm ở `rtl/` gốc, nên trông
   như thể nó thuộc về cả đề án.
3. **Trong mỗi bài, `sw/` và `sim/` đứng ngang hàng**, nên không thấy `sim/` đang kiểm *chip*
   hay kiểm *phần mềm* — mà hai thứ ấy là hai tầng khác nhau.

### Đề xuất

```
riscv-tn20k/                        ◀── SOLUTION: cả đề án
│
├── chung/                          ◀── dùng chung cho ba bài, đổi ở đây là đổi cho cả ba
│   ├── chip/
│   │   ├── rtl/                    bram.v · uart_tx.v · soc_top.v
│   │   ├── third_party/picorv32/
│   │   └── constraints/            tangnano20k.cst
│   ├── BAN-DO-DIA-CHI.md           ◀── hiện vật của CẢ HAI tầng
│   └── docs/                       hardware-facts.md · env.md · nang-luc-kit.md
│
├── bai1-soc-hello/                 ◀── DỰ ÁN 1
│   ├── chip/                       ── tầng 1: thiết kế chip
│   │   ├── rtl/                    phần RTL riêng của bài này
│   │   ├── sim/                    testbench cho chip
│   │   └── THIET-KE.md             yêu cầu · sơ đồ khối · quyết định
│   ├── phan-mem/                   ── tầng 2: phần mềm CHẠY TRÊN chip ấy
│   │   ├── src/                    start.S · linker.ld · main.c
│   │   ├── sim/                    testbench hệ thống (chip + phần mềm)
│   │   └── THIET-KE.md
│   └── KET-QUA.md                  số đo của cả hai tầng
│
├── bai2-nhan-ma-tran/              ◀── DỰ ÁN 2 — cùng khuôn
└── ket-qua-chung/                  bảng so ba bài · biểu đồ cpm
```

Bốn điều cấu trúc này nói ra mà cấu trúc cũ không nói:

- **`chung/` tách hẳn** — nhìn là biết đổi gì thì ảnh hưởng cả ba bài.
- **`chip/` và `phan-mem/` song song trong mỗi bài** — hai tầng thiết kế hiện rõ, và thứ tự
  phụ thuộc nằm ngay trong tên.
- **Mỗi tầng có `sim/` riêng** — testbench kiểm chip tách khỏi testbench kiểm hệ thống. Hai
  loại ấy trả lời hai câu khác nhau: *mạch có đúng không* và *chương trình chạy trên mạch ấy có
  đúng không*.
- **`BAN-DO-DIA-CHI.md` nằm ở `chung/`**, không nằm trong chú thích mã — vì nó là giao kèo giữa
  hai tầng, và cả hai bên phải đối chiếu được.

---

## Phần 4 — Đề xuất cho màn hình

Dữ liệu đã có trong kho. Thiếu bốn khối, và tôi xếp theo thứ tự đáng làm:

### A5.10 — Chip trên FPGA: cây mô-đun — **ĐÃ LÀM 02/10/2026, xem DEV-327**

Dựng từ quan hệ **gọi mô-đun** trong Verilog, đúng cách A5.6 đang dựng cây phần mềm từ
`#include`. Mỗi nút ghi rõ **chung** hay **riêng của bài nào** — đó là thứ anh Công muốn thấy.

```
soc_top  (chung)
├── picorv32       (bên thứ ba, ISC)
├── bram           (chung)       32 KB, nạp sẵn bằng $readmemh
├── uart_tx        (chung)       115200 baud
└── pcpi_mac       (bài 3)       ◀── chỉ bài 3 có
```

Và quy tắc như A5.6: **không có quan hệ thật thì không vẽ** — một sơ đồ trang trí còn tệ hơn
không có sơ đồ.

### A5.11 — Tài nguyên và định thời

Đọc thẳng `build:hdl:pnr`. Đây là con số quyết định thiết kế có vừa chip không, và hiện **không
hiện ở đâu cả**:

| | Dùng | Tổng | | |
|---|---|---|---|---|
| LUT4 | 2 180 | 20 736 | 10,5 % | |
| Flip-flop | 820 | 15 552 | 5,3 % | |
| BSRAM | 16 | 46 | 34,8 % | |
| **Fmax** | **134,93 MHz** | cần 27 | | **đạt** |

Kèm **ngưỡng của đề bài** (LUT ≤ 85 %) để người nhìn biết còn bao nhiêu chỗ, và kèm **số của
lần trước** để thấy một thay đổi tốn thêm bao nhiêu.

### A5.12 — Bản đồ địa chỉ

Giao kèo giữa chip và phần mềm. Hiện chỉ nằm trong chú thích `soc_top.v`.

| Địa chỉ | Thiết bị | Truy cập | Phần mềm dùng ở đâu |
|---|---|---|---|
| `0x0000_0000`– | BRAM 32 KB | đọc/ghi | `linker.ld` |
| `0x1000_0000` | UART TX | ghi | `main.c` |
| `0x1000_0004` | UART bận | đọc | `main.c` |
| `0x2000_0000` | LED | ghi | `main.c` |

Cột cuối là chỗ đáng giá: nó cho thấy **đổi bản đồ thì phải sửa những tệp nào**.

### A8 Mô phỏng — thêm kết quả testbench HDL

Hiện A8 dựng cho `sim.run` của vi điều khiển. Thêm khối đọc `build:hdl:sim`: mô-đun nào,
PASS/FAIL, bao nhiêu ca, **và kết quả đo độ nhạy nếu có**.

Dòng cuối ấy quan trọng hơn cả PASS: một bộ kiểm PASS mà chưa ai phá mã thì chưa biết nó đo gì.
Nấc 3a vừa rồi PASS với hai lỗ, và chỉ phép đo độ nhạy mới thấy.

### A9 Mạch thật — thêm bitstream

Đọc `build:hdl:bitstream`: tệp `.fs`, kích thước, mã chip đọc từ tệp bố trí, đã nạp chưa.

---

## Phần 5 — Thứ tự làm

| | Việc | Vì sao trước |
|---|---|---|
| 1 | **A5.11 tài nguyên và định thời** | dữ liệu đã có, giá trị cao nhất, làm xong là màn hình hết trắng |
| 2 | **A5.12 bản đồ địa chỉ** | là giao kèo hai tầng, và nó đang nằm trong chú thích mã |
| 3 | **A5.10 cây mô-đun** | cần viết bộ đọc quan hệ gọi mô-đun Verilog |
| 4 | **A8 + A9** | mở rộng khối có sẵn |
| 5 | **Dọn lại cấu trúc thư mục** | nay làm được: rào cản đã hết, xem dưới |

Việc 5 từng có một rào cản: đổi cấu trúc thư mục lúc Bài 3 đang dở sẽ làm hỏng mọi đường dẫn
trong các lời gọi công cụ đã ghi vào sổ, và làm bản ghi cũ khó đọc lại.

**Rào cản ấy đã hết.** Ngày 02/10/2026 Bài 3 ra khỏi phạm vi, nên đề án còn hai dự án và không
còn việc nào đang dở giữa chặng. Vẫn nên làm bằng một changeset riêng không kèm việc gì khác —
không phải vì rủi ro trùng việc, mà vì một changeset chỉ đổi đường dẫn thì đọc lại được, còn
một changeset vừa đổi đường dẫn vừa đổi mã thì không ai tách ra được nữa.

Và cấu trúc đề xuất nay chỉ còn **hai dự án**: `bai1-soc-hello/` và `bai2-nhan-ma-tran/`. Mã
của Bài 3 chuyển vào `ngoai-pham-vi/bai3-tang-toc/`, giữ nguyên hai tầng `chip/` và
`phan-mem/` để còn đọc lại được.
