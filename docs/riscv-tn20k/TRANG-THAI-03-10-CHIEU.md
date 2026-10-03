# Trạng thái — chiều 03/10/2026, buổi đầu tiên có kit thật

Viết để tối mở lại mà không phải dò sổ cái. Nối tiếp
[`TRANG-THAI-TAM-DUNG.md`](TRANG-THAI-TAM-DUNG.md) của hết ngày 02/10.

**Việc duy nhất còn lại của cả đề án cần kit thật** — đối chiếu số mô phỏng với số đo trên bo,
đề bài đòi chênh ≤ 1 % — nay **đã đo được trên lượt đầu**, và kết quả tốt hơn ngưỡng rất xa.

---

## 1 · Kết quả đo được

### Bài 1 trên bo thật

| Dòng nghiệm thu (§E3) | Điều kiện | Trạng thái |
|---|---|---|
| 2 · nạp SRAM | thấy `Hello…` | **ĐẠT** — 127 byte, `Hello from PicoRV32 on Tang Nano 20K, cycle=126` |
| 3 · nạp flash, cấp lại nguồn | vẫn chạy | **chưa làm** — cần người rút điện bo rồi cắm lại |

Mục *"LED nháy"* của phần nghiệm thu cũng chưa ai nhìn thấy với `soc_top`.

### Bài 2, lượt 1 trên bo thật — 4/4 ô

| ver | mô phỏng | bo thật | lệch | checksum |
|---|---|---|---|---|
| V0 | 46 047 | **46 047** | **0,000 %** | `0xFFFE6A17` ✓ |
| V1 | 52 310 | **52 310** | **0,000 %** | `0xFFFE6A17` ✓ |
| V2 | 48 530 | **48 530** | **0,000 %** | `0xFFFE6A17` ✓ |
| V3 | 48 545 | **48 545** | **0,000 %** | `0xFFFE6A17` ✓ |

Lệch 0,000 % là con số **hợp lý** ở đây, không phải dấu hiệu đáng nghi: PicoRV32 tất định,
BRAM một cổng không đệm, không ngắt, không bộ nhớ đệm. Mô phỏng chu kỳ-chính-xác của cùng RTL
phải ra đúng cùng số chu kỳ. **Nếu lệch mới là chuyện phải giải thích.**

Lượt ấy chạy trên bản còn mạch chẩn đoán. **Đã chạy lại lượt 1 trên bản giao** (`DIAG_LEDS=0`,
2 168 LUT, bitstream mã băm `c479e8895da7`) và **ra đúng cùng bốn con số**.

Đó là một kết quả phụ đáng giữ: trước đó chỉ **lập luận** được rằng mạch đèn không nằm trên
đường dữ liệu CPU nên không ảnh hưởng số chu kỳ. Nay **đo được**. Lập luận thành phép đo.

**Còn 22 lượt chưa chạy** (lượt 2 đến 24) — xem mục 5.

### Bản giao

| | Dùng | Có | |
|---|---|---|---|
| LUT4 | 2 168 | 20 736 | 10,46 % |
| DFF | 820 | 15 552 | 5,27 % |
| BSRAM 18 Kbit | 16 | 46 | 34,78 % = 32 KB |
| Fmax | **102,13 MHz** | cần 27 MHz | dư 3,78 lần |

Bản chẩn đoán có 2 211 LUT; bản giao 2 168. Giảm đúng 43 LUT — bằng phần mạch đèn đã gỡ, nên
`DIAG_LEDS = 0` thật sự có tác dụng chứ không chỉ đổi tên tham số.

---

## 2 · Nguyên nhân gốc, và nó đã treo suốt buổi chiều

**Chân `btn_s1` (PIN 88) đọc ra 0, giữ CPU trong reset vĩnh viễn.**

Chốt bằng phép đo, không bằng suy luận: dựng một bitstream bỏ hẳn `btn_s1` khỏi mạch reset →
CPU chạy ngay, UART ra đủ bốn dòng `RESULT`. Ghi thành **`ADR-05`** (tầng VÀNG, tác giả
`agent:run-157`), nêu rõ chỗ lệch đặc tả §5 và nêu cả mặt dở là nút S1 không dùng để reset tay
được nữa.

Nó giải thích **toàn bộ** chuỗi hiện tượng mà buổi chiều cứ tưởng là nhiều lỗi khác nhau:

| Hiện tượng | Thật ra |
|---|---|
| Bài 1 in được lúc 15:41 rồi thôi | chân thả nổi đọc ra 1 lúc ấy, 0 về sau |
| "bo về demo nhà máy" | CPU trong reset, đèn không ai ghi |
| "không đèn nào sáng" | như trên |
| Bài 2 im lặng hoàn toàn | như trên |

Một nguyên nhân, bốn triệu chứng. Và nó thuộc loại tệ nhất để gỡ: **không lặp lại đều.**

### Tài liệu đã tiên đoán đúng lỗi này — và vẫn kết luận đạt

[`bai1/DANH-GIA-NAP-BO-THAT.md`](bai1/DANH-GIA-NAP-BO-THAT.md) mục 3, viết **01/10, trước khi
có kit**:

> *"Thiếu phần kéo lên này thì chân thả nổi có thể đọc ra 0, và bo **nằm trong reset vĩnh
> viễn** — một lỗi trông giống hệt 'nạp xong mà không chạy'."*

Tiêu đề mục đó là **"KIỂM MÃ"**. Nó mở tệp ràng buộc, thấy `PULL_MODE=UP` cho chân 88, rồi cho
qua. Chẩn đoán đúng, phép đo sai tầng.

> **Đọc chữ trong tệp ràng buộc không phải đo hành vi của chân trên silicon.**

Cùng một họ với hai lỗi EIDE vá hôm nay: `"openfpgaloader" in enum` không chứng minh nhánh gọi
được.

---

## 3 · Ba lỗ hổng EIDE đã vá, và một còn mở

### `DEV-330` — nhánh nạp FPGA chưa bao giờ chạy nổi

Hai `NameError` xếp lớp trong `build/mach_that.py`, chỉ lộ ra khi có kit cắm vào:

| | Lỗi | Dạng |
|---|---|---|
| 1 | `_tim_lenh` thiếu import | tên không nhập vào |
| 2 | `_bam_tep` không tồn tại ở đâu cả; ba nhánh nạp kia đều dùng `_hash_tep` | gõ sai tên |

Lỗi 2 nằm **sau** chỗ kiểm tệp, nên chỉ nổ khi có tệp `.fs` thật. Vá lỗi 1 thì lỗi 2 hiện ra —
đúng tính chất của một đường dẫn chưa bao giờ chạy.

Cả hai sống sót qua **1 575 ca kiểm**, vì ca duy nhất cho nhánh này chỉ kiểm chuỗi
`"openfpgaloader"` có nằm trong danh sách tuỳ chọn của công cụ.

### `DEV-331` — bắt bản ghi UART bao quanh lần nạp

`target.flash` thêm `bat_log_giay` và `cong_log`: **mở cổng trước, vét rác, nạp, rồi đọc**.

Vì sao `target.log` sau `target.flash` không thay được: firmware Bài 2 tính xong rồi in bốn
dòng rồi vào `while(1)` — khoảng **35 ms**. Nạp xong mới mở cổng thì byte đã phát lúc không ai
mở cổng, và chip cầu không giữ đệm. Mấu chốt: byte mất **vì không ai mở cổng**; khi đã có tiến
trình giữ `fd` thì hàng đợi tty của nhân giữ byte lại.

Bản vá này còn bắt được một lỗi đọc của **người**: đoạn LiteX BIOS tưởng là bo đang phát, hoá
ra là rác trong hàng đợi — hàm có bước vét mới cho ra `0 byte` thật.

### Bộ kiểm

**1 580 ca xanh** (1 575 → 1 580). Năm ca mới, mỗi ca đã thử độ nhạy:

| Ca | Phá gì thì đỏ |
|---|---|
| `test_duong_fpga_goi_duoc_khong_chi_co_trong_thuc_don` | bỏ import `_tim_lenh` |
| `test_duong_fpga_di_het_voi_tep_that` | trả `_hash_tep` về `_bam_tep` |
| `test_khong_module_nao_goi_ten_chua_dinh_nghia` | **cả hai lỗi trên**, quét cú pháp mọi mô-đun |
| `test_bat_log_mo_cong_truoc_khi_lam_viec` | bỏ bước vét rác trước khi làm việc |
| `test_bat_log_cong_khong_co_thi_noi_ra` | gộp "không có cổng" với "bo im lặng" |

Ca thứ ba là ca đáng giá nhất: nó bắt **cả lớp lỗi** chứ không từng con, và không cần phần cứng.

### Còn mở: `target.detect` không có đường JTAG

`mach_that.py:93` chỉ có đường AVR (`doc_chu_ky_avr`) và ST-Link. Không có
`openFPGALoader --detect`. Nên "dò bo FPGA" hiện tại = liệt kê cổng USB + **đọc mã chip từ tài
liệu dự án**. Tác tử nói rõ điều đó chứ không giấu, nhưng công cụ vẫn thiếu một mảnh.

Phép kiểm cho bản vá **đã có, chạy được**:

```
openFPGALoader --detect
  → idcode 0x81b · manufacturer Gowin · family GW2A · model GW2A(R)-18(C)
```

So IDCODE đọc được với hộ chiếu chip là xong. Với FPGA, đây là phép đo **duy nhất** chứng minh
đúng con chip này đang cắm.

---

## 4 · Sao lưu bitstream nhà máy

Ghi flash trên kit thì ghi đè bitstream Sipeed. Dự án này đã trả giá một lần cho đúng chuyện
ấy — `eide-v3-lo-hong-con-lai` còn treo việc khôi phục demo gốc của ST cho bo STM32F469. Nên
sao lưu trước:

```
Con flash tự khai : Jedec ID 0x0b · type 0x40 · capacity 0x17 → 2^23 = 8 MiB
Tệp               : du-lieu/riscv-tn20k-b/sao-luu-flash/flash-nha-may-tangnano20k-8MiB.bin
                    8 388 608 B · sha256 e5bf8c5b7c6c89cd23fcf594fbf8487d1c2802229c2eb83cb78460083018a139
```

Dung lượng lấy **từ chính con flash**, không từ ký ức. Kiểm bản sao lưu ba cách: hai lần đọc
độc lập cùng vùng 64 KB **khớp**; dấu nhận dạng Gowin `a5c3` có trong 64 byte đầu; bitstream
nhà máy chiếm 907 408 B, phần còn lại trắng.

Khôi phục: `openFPGALoader -b tangnano20k -f --verify <tệp .bin>` — nhưng **chưa thử lần nào**,
nên đừng coi là đã kiểm. Demo Sipeed cũng tải lại được từ `sipeed/TangNano-20K-example`.

Tệp sao lưu nằm trong `du-lieu/` nên **bị `.gitignore` chặn — chỉ có trên máy này.**

---

## 5 · Còn 22 lượt — và một lỗ hổng thứ hai chặn đường

Bước 18 chạy xong **đúng 1 lượt** rồi dừng lại lập kế hoạch cho 23 lượt còn lại, chứ không
chạy tiếp. Lý do tác tử nêu:

> *"Do mỗi lượt nạp phần cứng qua `target.flash` đều đi qua cổng an toàn `G-FLASH`..."*

Đếm trong sổ cái khớp: lượt ấy có đúng 1 × `build.compile`, 1 × `hdl.synth`, 1 × `hdl.pnr`,
1 × `hdl.bitstream`, 2 × `target.flash` (1 lỗi, 1 đạt). Không phải hết ngân sách — hạn là 220
lời gọi.

**Đây là lỗ hổng thứ hai của loại "việc dài hơn một lượt".** Cổng `G-FLASH` được duyệt ở ranh
giới lượt, nên một quét 24 lần nạp **không thể xong trong một lượt** dù ngân sách còn thừa.
Cùng họ với mục c của [`TRANG-THAI-TAM-DUNG.md`](TRANG-THAI-TAM-DUNG.md) — *`tool.install` để
lại thẻ duyệt treo, thẻ được duyệt sang lượt sau mà tác tử thử lại trong cùng lượt.*

Ba cách đi tiếp, chưa chọn:

1. **Chạy từng lượt một qua `--buoc 18`**, 22 lần. Chậm nhưng không sửa gì, và mỗi lượt có ranh
   giới để duyệt cổng.
2. **Cho `G-FLASH` một chế độ duyệt-một-lần-cho-cả-quét** — người duyệt trước N lần nạp vào
   cùng một kit. Sửa ở tầng chính sách.
3. **Viết một kịch bản quét riêng** gọi thẳng `hdl.*` và `target.flash` ngoài vòng tác tử. Mất
   phần dấu vết qua giao diện, nên chỉ dùng nếu hai cách trên tắc.

Nghiêng về **cách 1 trước** để lấy xong số liệu, rồi **cách 2** cho lần sau.

Mỗi lượt cần một bitstream riêng vì chương trình nhúng vào BRAM lúc tổng hợp — `$readmemh`
trong `rtl/bram.v:51`. Nên 8 chương trình × 3 cấu hình CPU = **24 lần** `yosys` → `nextpnr` →
`gowin_pack`, việc hàng giờ.

### Soát gì khi xong 24 lượt

1. **Số bitstream thật sự dựng — phải là 24.** Nếu chỉ 3 thì 8 lượt cùng cấu hình cho số giống
   hệt nhau, mà bảng vẫn đủ 96 ô và vẫn `ok=1`. Cách bắt: trùng `cycles` giữa các `(N, dtype)`
   khác nhau.
2. **`results/board.csv` phải 96 dòng.** Thiếu thì phải thiếu **có khai**.
3. **Lệch so với `all.csv` ≤ 1 %.** Dòng nào lệch khác 0 là dòng đáng đọc kỹ — nó nói có thứ
   trên bo mà mô phỏng không có.

---

## 6 · Việc còn lại

| | Việc | Cần người |
|---|---|---|
| a | Soát 24 lượt theo mục 5 | không |
| b | **Dòng 3 nghiệm thu Bài 1**: rút điện bo rồi cắm lại, xem còn chạy | **có** — chỉ việc rút cắm |
| c | **"LED nháy"** của Bài 1: nhìn LED0 với bản giao `DIAG_LEDS=0` | **có** |
| d | Vá `target.detect` thêm đường JTAG, phép kiểm đã có ở mục 3 | không |
| e | Nút S1: `ADR-05` đã ghi quyết định bỏ, nhưng vẫn lệch §5. Nếu muốn đúng đặc tả thì phải tìm ra vì sao PIN 88 kẹp 0 | **có** — cần biết bo có chữ `S1` cạnh nút nào |

Mục b và c gộp làm một lần: rút điện, cắm lại, rồi nhìn đèn.

---

## 7 · Số đo của phiên

| | |
|---|---|
| Sổ cái dự án | **19 681 dòng** |
| Changeset | **148** |
| Lời gọi mô hình | **1 746** |
| Ảnh cửa sổ EIDE | **25** |
| Nhật ký phiên | 1 996 dòng |
| Nạp bo | **5 đạt / 12 lần gọi** — 7 lần lỗi đều đã truy ra nguyên nhân |
| Bộ kiểm Python | **1 580 ca xanh** |

---

## 8 · Ba điều về cách làm việc, đo được trong buổi này

**Trước khi nhận một quan sát trên bo, so mốc dựng bitstream với mốc nạp cuối.** Suýt hai lần
nhận trạng thái của bitstream cũ làm kết quả của bản mới. Lần đầu bị chặn vì mốc lệch 6 phút
12 giây. Phép so này rẻ, và nó chặn đúng loại sai mà không ai nhìn ra được từ bản thân quan sát.

**Người cũng sai đúng kiểu tác tử sai, và sai nhiều hơn.** Ba lần trong buổi này người suy ra
nguyên nhân trước khi đo rồi sai: V3 lùi về V2 (bỏ qua `matmul.c`), dòng tiêu đề bị cho là bịa
(nhầm số dòng trong tệp với thứ tự chạy), và `BANK_VCCIO` bị nghi phá chân nút (mốc giờ bác).
Hai lần đầu **tác tử đúng và người sai** — nó đọc thêm tệp thứ hai, người dừng ở tệp thứ nhất.

Ở phiên robot người bắt được bảy lỗi của tác tử bằng cách mở mã ra đối chiếu. Ở phiên này tác
tử bắt lại hai lỗi của người bằng đúng cách ấy. **Phương pháp không thiên vị ai — ai dừng đọc
sớm thì người đó sai.**

**Dựng dụng cụ đo đáng giá hơn đoán thêm một vòng.** Sơ đồ ba tầng đèn — LED5 từ đồng hồ, LED4
từ `sys_resetn`, LED3–0 từ CPU — mỗi tầng độc lập với tầng dưới. Một câu *"chỉ LED5 nháy"* của
người loại được bốn khả năng cùng lúc, và câu *"tất cả sáng trừ LED5 nháy"* chốt luôn nguyên
nhân. Trước đó cả buổi đoán không ra.

Và một chi tiết tiết kiệm được cả vòng sửa mã: **mốc 3 của sơ đồ ấy đã có sẵn trong mã** —
`bai2/sw/main.c:199` có `LED_REG = 0x01` ngay lệnh đầu `main()`. Đọc mã trước khi thêm mã.
