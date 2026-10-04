# Việc thứ 4 — Robot hai bánh tự cân bằng · kết quả phiên 04/10/2026

Tác tử đóng vai **sinh viên** làm lại việc từ dự án rỗng, chỉ được đọc tài liệu đầu vào
([`YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx`](../YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx)
và [`PHU-LUC-MOC-NGUOI-VA-DO-TAN-SO.md`](../PHU-LUC-MOC-NGUOI-VA-DO-TAN-SO.md)), không được xem
mã của bản người làm. Mọi việc cắm dây, cấp nguồn và quan sát do **người** làm.

Bo thật: **Arduino Nano / ATmega328P**, thạch anh 16 MHz, cảm biến **MPU6050** qua I2C, hai
driver bước **A4988**. Cổng `/dev/cu.usbserial-21410`, 115200 baud.

**Trạng thái: chạy trên nguồn USB. Chưa có pin và chưa có nguồn động cơ**, nên phần robot
đứng thẳng chưa nghiệm thu được.

---

## 1 · Phần đã nghiệm thu trên bo thật

| # | điều kiện | kết quả đo | cách đo | ai đo |
|---|---|---|---|---|
| **NT-A** | ngắt phát xung **50 kHz ± 1 %** | **50,0005 kHz** — lệch **+0,0009 %** | tỉ số Timer2/Timer0 qua 36 800 ms, neo vào đồng hồ tường 40,015 s | máy đếm, người đối chiếu đồng hồ tường |
| **NT-NGAT** | không nghẽn ngắt | **0/369** dòng thiếu | số thứ tự dòng tăng đơn điệu suốt 36,8 s | máy |
| **NT-C** | hàm ngắt 50 kHz không có số thực hay phép chia | **0 lệnh cấm** | `avr-objdump -d mach.elf`, tìm `__divsf3`, `__mulsf3`, `__udivmodsi4` | máy |
| **NT-UART** | chu kỳ bản tin theo dõi 100 ms | **372/372 khoảng đúng 100 ms** | 25 nhịp × 4 ms, phát lệch pha ở nhịp 12 | máy |
| **NT-OVERRUN** | vòng điều khiển không trễ khi chạy | **0 lần trễ / 9 225 nhịp** | hai lần `overrun` đếm được đều sinh ở pha hiệu chuẩn 1,5 s lúc khởi động (`fsm.c:90-92`) | máy |
| **NT-D** | góc tĩnh và hội tụ bộ lọc | góc tĩnh **72,96°**; 5 điểm trên đường hội tụ khớp `τ = 10 s`, lệch hẳn đường tuyến tính | đọc cổng nối tiếp từ chuyển tiếp lúc bật nguồn | người |
| **NT-PIN** | phát hiện pin yếu | `LOWBATT` đúng (A0 ≈ 0 vì **chưa cắm pin**) | đọc trạng thái máy trạng thái qua cổng | người |

Phần chủ (trên máy tính): **22/22 điều kiện đạt**, và **4/4 phép phá mã bị bắt** —
bộ kiểm có phản ứng khi mã thật bị phá, không chỉ xanh suông.

### Phép đo `NT-A` chi tiết

| | |
|---|---|
| Δ`millis` | 36 800 ms |
| Δ`step_ticks` | 1 840 017 lần |
| tỉ số | 50,00046 lần/ms |
| **tần số** | **50,0005 kHz** |
| lệch so với 50 kHz | **+0,0009 %** |
| ngưỡng `NT-A` cho phép | ±1 % |

Cấu hình thật trong mã: **Timer2**, chia tần **8**, `OCR2A = 39` (`firmware/timer.c:13-16`),
hàm ngắt `ISR(TIMER2_COMPA_vect)`.

Phép quy chiếu tuyệt đối khép lại: đồng hồ tường 40,015 s; robot báo đã chạy 38,398 s, cộng
1,598 s trước dòng đầu (bộ nạp khởi động) là 39,996 s — hụt 19 ms vì lượt thu cắt giữa dòng.
Nên con số này **neo vào đồng hồ tường**, không neo vào thanh ghi.

Bản ghi thô: [`ban-ghi-tho/nt-a-50khz.txt`](ban-ghi-tho/nt-a-50khz.txt).

---

## 2 · Phần chưa nghiệm thu, và lý do

Hai lý do khác nhau — không gộp, vì gộp lại làm người đọc tưởng cùng một nguyên nhân.

### 2.1 · Chờ máy hiện sóng — **đo được ngay trên nguồn USB, không cần pin**

| # | điều kiện | cần gì |
|---|---|---|
| **NT-B** | vòng tính góc chạy **250 Hz ± 1 %** | kẹp que đo vào chân **A1**: firmware đảo chân ấy mỗi vòng (`fsm.c:98`), nên nó phát sóng vuông **125 Hz, mỗi sườn 4 ms** |

Đã có một phép đo **trung bình dài hạn** đạt 250,0 Hz (372 khung × 25 nhịp, 0 lần trễ), nhưng
nó **không thay được máy hiện sóng**, vì hai lẽ:

1. **`millis()` phân giải 1 ms.** Chu kỳ 4 ms nhìn qua thang 1 ms có sai số lượng tử tức thời
   tới **±25 %**. Nó chứng minh trung bình, không chứng minh **các nhịp cách đều nhau**. Mà
   ngắt 50 kHz đang chiếm 15–20 % CPU, nên nhịp không đều là kiểu hỏng hợp lý nhất.
2. **Vòng lặp dùng bộ tích lũy triệt tiêu trôi dạt** (`g_last_loop_time += 4`). Nên 25 nhịp ra
   đúng 100 ms **do xây dựng**, kể cả khi các nhịp lệch nhau. Giãn cách chỉ lộ ra nếu một nhịp
   quá hạn hơn 4 ms, không lộ ra nếu nhịp **không đều**.

Ghi lại vì chính người làm đã suy ra "đủ rồi" và **tác tử bác lại bằng lý do 1** — lý do người
chưa nghĩ tới.

### 2.2 · Chờ pin và nguồn động cơ

| # | điều kiện | cần gì |
|---|---|---|
| **NT-MOTOR** | động cơ bước đảo chiều, phát xung đúng tốc độ | pin 2S/3S cấp nguồn động lực qua A4988. Chế độ USB **khoá** phát xung để chống sụt áp cổng USB |
| **NT-BALANCE** | robot đứng thẳng, giữ quanh 0° | pin, khung xe, bánh xe, mặt sàn phẳng |
| **ba dấu** | `STATE_SELF_TEST` tách ba dấu, hiệu chuẩn, ngưỡng `LOWBATT` | như trên |

---

## 3 · Lỗi EIDE phát hiện trong phiên

| mã | lỗi | bộ kiểm |
|---|---|---|
| **DEV-336** | `sim.run` đem số đo của chương trình này so với tiêu chí của chương trình khác, rồi trả `dat: False` — sở cứ nói ngược báo cáo | [`tests/test_sim_lech_tieu_chi.py`](../../../tests/test_sim_lech_tieu_chi.py) |
| **DEV-337** | nạp `.hex` cũ hơn `.elf` bên cạnh; **đối chiếu sau nạp vẫn ĐẠT** vì nó so chip với tệp vừa ghi, không so với bản vừa dựng | [`tests/test_hex_cu_hon_elf.py`](../../../tests/test_hex_cu_hon_elf.py) |

`DEV-337` là anh em sinh đôi của lỗi bitstream FPGA hôm 03/10, chỉ nằm ở đường AVR. Ba lượt
liền không thấy dòng `#STAGE` mà mã nguồn có; mọi mắt kiểm đều nối; chỉ **đọc ngược flash từ
chip rồi so nội dung** mới thấy chip đang chạy bản khác — lệch 6 937 byte.

---

## 4 · Lỗi của phía người đo

Ghi vào đây vì nó tốn nhiều lượt hơn cả hai lỗi EIDE trên.

| phép lọc sai | đầu ra | giá |
|---|---|---|
| bỏ qua dòng `#STAGE` dùng chung bộ đếm | `115,7` / `112,2` / `90,85 ms` | **năm lượt** đuổi một lỗi định thời **không tồn tại** |
| lọc theo tiền tố `#T ` không hề có | thu 406 dòng, lọc ra **0 dòng** | một lượt |

Sự thật ở ca thứ nhất: 372/372 khoảng đúng 100 ms, 0 số thứ tự thiếu. Phép lọc đã **tự sinh
ra** các khoảng trống rồi báo cáo chúng như số đo.

**Giá của lỗi tỉ lệ với độ hợp lý của đầu ra, không tỉ lệ với độ sai.** Lọc sai trả về rỗng thì
gãy to nên rẻ; cùng phép lọc ấy trả về số trông hợp lý thì không ai nghi. Chi tiết ở mục B phụ
lục.

---

## 5 · So với phiên 03/10 — bốn con số [`TRANG-THAI-DUNG.md`](../TRANG-THAI-DUNG.md) đặt ra

Phiên này **là bản làm lại** mà tệp trạng thái ấy chốt ở việc số 3: dự án dựng trống, tác tử
đã vá, cùng loại tài liệu đầu vào.

| | phiên 1 · 03/10 | phiên 2 · 04/10 |
|---|---|---|
| lời gọi công cụ | 394 | **541** |
| lời gọi bị chặn / không thành công | 26 (6,6 %) | **18 (3,3 %)** |
| dừng ở | bước 23/32, **chủ động** | chạy tới hết phần làm được trên USB |
| việc đạt trên bo thật | không có — chưa tới bo | **7 điều kiện đo trên silicon** |

### Các cổng đã nổ, theo mã lỗi

| phiên 1 | | phiên 2 | |
|---|---|---|---|
| `task.run → E5007` | 6 | `task.run → E5007` | 4 |
| `fs.write → E4001` | 5 | `fs.write → E4001` | 4 |
| `sim.run → E4004` | 3 | **`sim.run → E4023`** | **3** |
| `fact.extract_pinout → E2003` | 1 | `fs.write → E4020` | 2 |
| `ckm.chip_add → E8002` | 1 | `sim.run → E4004` | 1 |
| `ckm.pinout_set → E8002` | 1 | `sim.run → E5001` | 1 |
| `doc.read → E2004` | 1 | `build.compile → E4001` | 1 |
| `store.option_choose → E5009` | 1 | `target.flash → E4013` | 1 |

**`E4023` là chốt `DEV-336` vá trong chính phiên này, và nó nổ 3 lần.** Đáng ghi riêng, vì bài
học cũ của dự án là *cơ chế có sẵn mà đường dẫn tới nó đứt* — có cổng chạy 0/402 lượt. Lần này
cổng mới **được gọi thật**, không chỉ xanh trong bộ kiểm.

### Chỗ đổi chiều, và nó là kết quả chính của việc so hai phiên

Phiên 1 kết luận: *sáu trong bảy lỗi do **người** bắt bằng cách mở mã ra đối chiếu.*

Phiên 2 đảo lại. Đếm tay trên nhật ký, phần robot:

| | số | nội dung |
|---|---|---|
| lỗi **tác tử** do người bắt | **1** | bảng nghiệm thu gọi sai ngoại vi (Timer1 thay Timer2) **và** chấm `NT-A` ĐẠT bằng cấu hình thay vì số đo |
| lỗi **người** do tác tử bắt | **3** | (a) cảnh báo trước cái bẫy *đếm bằng chính bộ đếm đang đo*; (b) tìm ra lỗ **đọc rách** biến `uint32_t` trong phép đo người đề xuất; (c) **bác kết luận của người** về `NT-B` bằng lý do lượng tử hóa `millis` 1 ms mà người chưa nghĩ tới |
| lỗi **người** do chính người bắt | **2** | hai phép lọc dữ liệu thô sai, xem mục 4 |

Nên con số đáng báo cáo của phiên này không phải "tác tử đã giỏi hơn", mà: **tác tử đã bác được
kết luận sai của người, bằng lý do kỹ thuật người chưa nghĩ tới, trước khi kết luận ấy vào báo
cáo.** Ở phiên 1 chuyện ngược hẳn.

Một chỗ phải nói thẳng để con số không bị đọc quá: bảng trên **đếm tay**, phạm vi là phần robot
sau khi tài liệu đầu vào đã dựng lại — không phải phép đo tự động, và không so được trực tiếp
với con số "bảy lỗi" của phiên 1 vì hai phiên dừng ở hai chỗ khác nhau.

---

## 6 · Sở cứ trong thư mục này

| tệp | nội dung |
|---|---|
| `NHAT-KY.md` | toàn bộ đối thoại người ↔ tác tử, từng bước |
| `buoc.jsonl` | bản ghi máy của từng bước |
| `quan-sat-nguoi.jsonl` | các quan sát người nhập vào |
| `so-cai.jsonl` | sổ cái EIDE của dự án robot |
| `firmware/` | mã nguồn tác tử viết, **đúng bản đang nằm trên chip** |
| `ban-ghi-tho/nt-a-50khz.txt` | bản ghi cổng nối tiếp dùng cho `NT-A` và `NT-NGAT` |
