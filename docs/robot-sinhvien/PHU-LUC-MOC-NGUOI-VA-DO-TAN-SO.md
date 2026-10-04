# Phụ lục bổ sung cho `YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx` bản 1.1

Thêm ngày 04/10/2026, **trước khi giao việc cho tác tử**, sau khi soát lại tài liệu của chính
mình bằng đúng ba lỗi đã tìm thấy ở hai việc trước (FPGA và RTOS).

Hai lỗ dưới đây là lỗi của người viết tài liệu, không phải của tác tử. Cả hai đều thuộc một
dạng: **tiêu chí viết lỏng thì không đo được gì, và tác tử sẽ làm đúng theo cái lỏng ấy.**

---

## A · Mốc so sánh phải ở trong tài liệu, tầng NGƯỜI

### Lỗ đã có

Mục 4.1 viết điều kiện đạt là *"các bit chân cổng và góc tính ra **khớp đúng với bản mẫu đã
chạy được**"*. Câu ấy không nói **con số mốc ở đâu**. Nếu tác tử tự sinh mốc bằng cách chạy
chính mã nó vừa viết thì bài kiểm chỉ còn so mã với chính nó — **nó bắt được 4/4 phép phá mà
vẫn bảo vệ nguyên cái lỗi**, vì phá mã thì mốc cũng dịch theo.

Chuyện này **đã xảy ra thật** ở phiên robot ngày 03/10/2026: bộ kiểm bắt đủ bốn phép phá, mà
mốc lại lấy từ đầu ra của mã sản phẩm.

### Bản sửa

Mốc dưới đây do **người tự tính**, bằng công thức ghi ở **mục 2.2 của tài liệu**, không đọc mã
sản phẩm. Công thức ấy là:

```
giá trị = kẹp(gia tốc Z thô + số bù 92, -8200, 8200)
góc theo gia tốc = asin(giá trị / 8200) × 57,29578
```

**Bảng A.1 — Góc theo gia tốc, tầng NGƯỜI**

| gia tốc Z thô | góc phải tính ra (độ) |
|---:|---:|
| −4 000 | **−28,4626** |
| −2 000 | **−13,4551** |
| −500 | **−2,8520** |
| 0 | **0,6428** |
| 500 | **4,1401** |
| 2 000 | **14,7808** |
| 4 000 | **29,9355** |
| 8 108 | **90,0000** |

Sai số cho phép: **0,001 độ**. Mã của bạn lệch với bảng này thì mã sai, không phải bảng sai.

**Bảng A.2 — Bit chân chiều quay, tầng NGƯỜI**

Hai động cơ lắp đối xứng nên chiều tiến của hai bên **không cùng mức điện**. Đây là dữ kiện
phần cứng, không suy ra được từ mã:

| | chân | robot tiến | robot lùi |
|---|---|---|---|
| bánh trái | D6 | **mức thấp (0)** | mức cao (1) |
| bánh phải | D4 | **mức cao (1)** | mức thấp (0) |

### Vì sao bảng này làm bộ kiểm có nghĩa

Bảng 4.2 đòi bốn phép phá. Với mốc trong tài liệu, mỗi phép phá có một con số **tính trước**:

| phá gì | đổi thành | góc tại gia tốc Z = 0 | lệch so bảng A.1 |
|---|---|---|---|
| số bù gia tốc | 92 → 535 | 3,7409° | **+3,0980°** |
| dấu khi áp số bù | cộng → trừ | −0,6428° | **−1,2857°**, tức gấp **2,0 lần** |
| chiều tiến bánh trái | thấp → cao | — | bit D6 khác bảng A.2 |
| chiều tiến bánh phải | cao → thấp | — | bit D4 khác bảng A.2 |

Hai con số `3,0980` và `gấp 2,0 lần` người đã tự tính lại và **khớp** với chữ *"khoảng 3,1 độ"*
và *"lệch gấp đôi"* ở bảng 4.2 bản 1.1.

---

## B · Phải ĐO tần số ngắt, không được tin giá trị cấu hình

### Lỗ đã có

Tài liệu nói hàm ngắt phát xung chạy **50 kHz**, và cấm số thực cùng phép chia trong đó vì mỗi
lần ngắt chỉ có 320 nhịp. Nhưng trong toàn bộ danh mục nghiệm thu **không có một dòng nào đòi
đo tần số thật**. Chữ *"tần số"* xuất hiện **0 lần** ở phần nghiệm thu bản 1.1.

Đây đúng là lỗ đã làm mất một lượt nạp ở việc RTOS: tài liệu cho sẵn hằng số PLL, người tưởng
thế là xong, và bản nạp đầu chạy ở **16 MHz thay vì 180 MHz** — mọi mốc thời gian chậm 11,25
lần, **không fault, không treo, thanh ghi nào cũng trông hợp lý**.

> **Giá trị cấu hình không phải phép đo.** Một thanh ghi nạp đúng chỉ nói *tần số sẽ đúng NẾU
> xung nhịp đúng*.

### Bản sửa — thêm ba dòng vào danh mục nghiệm thu

| # | điều kiện | ai đo | cách đo |
|---|---|---|---|
| **NT-A** | Ngắt phát xung chạy **đúng 50 kHz ± 1 %** | máy | đếm số lần ngắt trong một khoảng đã biết, in ra cổng nối tiếp; hoặc đảo một chân rồi đo bằng máy hiện sóng ở **D13** |
| **NT-B** | Vòng tính góc chạy **đúng 250 lần mỗi giây ± 1 %** | máy | đảo chân **A1** mỗi vòng, đo bằng máy hiện sóng — tài liệu đã dành riêng chân này |
| **NT-C** | Hàm ngắt 50 kHz **không chứa** lệnh số thực hay phép chia | máy | đọc **mã máy** của hàm ngắt bằng `objdump`, tìm lệnh gọi `__divsf3`, `__mulsf3`, `__udivmodsi4`… — đọc mã nguồn **không** trả lời được câu này |

Dòng **NT-C** quan trọng riêng: ở việc RTOS, một hàm `memset` tự viết bị trình biên dịch đổi
thành lời gọi **chính nó**, và chuyện ấy chỉ thấy khi mở `objdump`. Mã nguồn không chứa phép
chia vẫn có thể sinh ra mã máy gọi hàm chia.

### Cái bẫy nằm ở phía người đọc dữ liệu, không ở phía thiết bị

`NT-A` đã đo được: **50,0005 kHz, lệch +0,0009 %** — tỉ số Timer2/Timer0 trên 36,8 giây, neo
vào đồng hồ tường 40,015 s. Nhưng đường tới con số ấy lộ ra một lỗ **không nằm trong thiết bị**:

Hai lần trong cùng một phiên, phép **lọc dữ liệu thô** theo định dạng *tự nhớ* đã làm sai, với
hai giá chênh nhau rất xa:

| phép lọc sai | đầu ra | giá phải trả |
|---|---|---|
| bỏ qua dòng `#STAGE` dùng chung bộ đếm | `115,7` / `112,2` / `90,85 ms` | **năm lượt** đuổi một lỗi định thời không tồn tại |
| lọc theo tiền tố `#T ` không hề có | thu 406 dòng, lọc ra **0 dòng** | **một lượt** |

Sự thật ở ca thứ nhất: 372/372 khoảng đúng 100 ms, 0 số thứ tự thiếu — **chưa từng có lỗi định
thời nào**. Phép lọc đã tự sinh ra khoảng trống rồi báo cáo chúng như số đo.

Rút ra, và nó áp cho mọi phép đo trong tài liệu này: một phép lọc sai mà trả về **rỗng** thì
gãy to nên rẻ; cùng phép lọc ấy mà trả về **số trông hợp lý** thì không ai nghi, nên nó đi
thẳng vào kết luận. **Giá của lỗi tỉ lệ với độ hợp lý của đầu ra, không tỉ lệ với độ sai.**

Nên trước khi lọc bất kỳ bản ghi thô nào: mở vài dòng thô ra xem, đếm tiền tố thật
(`awk '{print $1}' | sort | uniq -c`), và so **số dòng vào với số dòng được dùng**. Chênh bao
nhiêu thì đúng chỗ ấy là chỗ cần đọc. Và cách chữa đã hiệu nghiệm hai lần: **bắt thiết bị tự
khai mốc thời gian và số thứ tự của nó**, rồi đếm số thiếu — đừng để phía chủ đo suy ra thứ tự.

---

## C · Một câu thêm vào mục 2.6

Bảng 2.5 liệt kê mười tệp kèm số dòng. **Số dòng ấy là thông tin, không phải chỉ tiêu.** Nếu
việc của bạn cần ít tệp hơn hoặc ít dòng hơn thì cứ làm ít, và nói ra.

Lý do có câu này: ở việc RTOS, tiêu chí người viết là *"mọi tệp mã nguồn đều vào được ảnh"* —
mà một tệp rỗng thì không vào được ảnh, nên tác tử **viết thêm 36 dòng mã không ai gọi** cho
tệp rỗng có ký hiệu, rồi ghi cả động cơ vào chú thích. Tiêu chí ấy tự nó khuyến khích làm sai.

**Tệp nào không có việc gì để làm thì xoá đi.** Thà nhận một dự án ít tệp hơn mà tệp nào cũng
có lý do tồn tại.

---

## D · Chân A2 dành cho đo chặng trong vòng 4 ms

Thêm 04/10/2026, khi cần đo thời gian từng chặng trong vòng tính góc.

Bảng 1.3 của tài liệu chính dành **D13** cho hàm ngắt 50 kHz và **A1** cho vòng 4 ms. Cả hai
đã có việc. Nên mình cấp thêm **một** chân:

| chân trên bo | chân của chip | hướng | dùng để làm gì |
|---|---|---|---|
| **A2** | **PC2** | ra | đo chặng bên trong vòng 4 ms, dùng cho máy hiện sóng |

Mình ghi chân này vào đây **trước khi** mã dùng tới nó, vì ở lượt trước có ba chân bị đổi im
lặng khỏi bảng 1.3 — và hậu quả là một bản firmware dịch sạch, nạp sạch, mà nút chết và còi
im. Lệch bảng chân thì không có lỗi nào kêu lên.

Vẫn giữ nguyên: **đừng dùng A1 và D13 cho việc khác.**

---

## E · Tham số điều khiển đã chạy thật — tầng NGƯỜI

Thêm 04/10/2026. Mình tra từ bản firmware **đã đứng được trên bo thật** ngày 01/10/2026
(`docs/robot-tu-can-bang/firmware/`), và chỉ lấy số từ những tệp **thật sự nằm trong đường
chạy**.

### E.0 · Vì sao mình phải nói chuyện này trước

Bản chạy được ấy có tệp `control.c` với bốn hàm, và cả bốn **đều nằm trong ảnh đã nạp**. Nhưng
mình đọc mã máy:

```
avr-nm mach.elf   → control_init, control_reset, control_set_state, control_update_4ms
avr-objdump -d    → số lời gọi tới control_* = 0
```

**Không ai gọi chúng.** `control.c` là mã chết trong chính bản đã làm robot đứng. Nên mọi hằng
số trong tệp ấy **chưa bao giờ góp phần vào việc robot đứng**, và lấy số từ đó là cấp cho bạn
một bộ tham số chưa từng chạy.

Đường chạy thật là `fsm.c` → `pid.c` → `motor.c`. Mọi số dưới đây lấy từ ba tệp ấy.

### E.1 · Bộ điều khiển PID

| | giá trị | lấy ở đâu |
|---|---|---|
| hệ số tỉ lệ `Kp` | **12,0** | `pid.c:4` |
| hệ số tích phân `Ki` | **0,4** | `pid.c:5` |
| hệ số vi phân `Kd` | **10,0** | `pid.c:6` |
| kẹp bộ nhớ tích phân | **±400,0** | `pid.c:36-37` |
| kẹp ngõ ra | **±400,0** | `pid.c:45-46` |

Hai chi tiết mình thấy trong mã mà **tài liệu chính không nêu**, nên ghi vào đây:

- **Phản hồi ngõ ra vào sai số.** Khi `|ngõ ra| > 10` thì sai số được cộng thêm
  `ngõ ra × 0,015` (`pid.c:30-31`). Nó làm bộ điều khiển bớt hăng khi đã ra lệnh mạnh.
- **Tự học điểm cân bằng.** Mỗi vòng, nếu ngõ ra âm thì điểm cân bằng `+= 0,002`; nếu dương thì
  `-= 0,002` (`pid.c:57-58`). Đây chính là chỗ tài liệu chính mục 3.8 nói mơ hồ, và bạn đã nêu
  ra ở lượt đọc đề — mình nhận, và đây là con số thật.
- **Triệt tiêu khi ngã.** `!đang chạy` hoặc `|góc| > 30°` thì ngõ ra và bộ nhớ tích phân về 0
  (`pid.c:62`).

### E.2 · Quy đổi ngõ ra PID sang giá trị xung

Công thức phi tuyến ở `motor.c:57-61`:

```c
nếu ngõ ra > 0:   out_nl =  405,0 - (5500,0 / (ngõ ra + 9,0));   xung =  400,0 - out_nl
nếu ngõ ra < 0:   out_nl = -405,0 - (5500,0 / (ngõ ra - 9,0));   xung = -400,0 - out_nl
```

### E.3 · Dải chu kỳ bước

| | giá trị | lấy ở đâu |
|---|---|---|
| quan hệ | `|thr| = (50 000 / f) − 1`, chu kỳ `= (|thr| + 1) × 20 µs` | `motor.c:44-45` |
| dưới **10 Hz** | trả về 0, đứng im tường minh | `motor.c:41-42` |
| `thr` nhỏ nhất | **1** → 25 000 xung/s, tốc độ tối đa thiết kế | `motor.c:48-49` |
| `thr` lớn nhất | **2 000** → 25 xung/s, sát điểm thăng bằng | `motor.c:50-51` |

### E.4 · Ngưỡng và hiệu chuẩn

| | giá trị | xuất xứ trong bản chạy được |
|---|---|---|
| ngưỡng ngã, ngắt xung | **±30,0°** | `config.h:81`, ghi `(V1:319)` |
| cửa sổ kích hoạt cân bằng | **±0,5°** | `config.h:82`, ghi `(V1:414)` |
| hiệu chuẩn gia tốc tĩnh | **92** | `config.h:83`, ghi `(V1:76)` |
| chiều tiến bánh trái D6 | **mức THẤP (0)** | `config.h:72`, ghi `(V1:581)` |
| chiều tiến bánh phải D4 | **mức CAO (1)** | `config.h:73`, ghi `(V1:598)` |
| số mẫu đo offset | **500** | `config.h:94` |
| timeout chống treo I2C | **1 000** vòng | `config.h:91` |

Ghi chú `(V1:nnn)` trỏ về dòng trong mã **V1 của nhà cung cấp**
(`docs/robot-tu-can-bang/ncc/V1_Balancing_Robot_HC05_JQ6500/`) — tức bộ số đã làm một con
robot đứng thật, không phải số mình nghĩ ra.

### E.5 · Hai điều về cách dùng bộ số này

**Dùng được ngay, nhưng không phải chân lý.** Số bù gia tốc **92** là của bo mẫu — bạn đã nói
đúng chỗ này ở lượt đọc đề, và bo của mình cần tự đo lấy số riêng. Ba hệ số PID thì nên chạy
được trước khi tinh chỉnh.

**Và đừng lấy số từ `control.c`.** Mình nhắc lại vì nó dễ nhầm: tệp ấy có trong bản chạy được,
có trong ảnh đã nạp, nhưng không ai gọi. Nếu bạn thấy hằng số nào trong đó khác với bảng trên,
thì bảng trên đúng — vì bảng trên lấy từ mã đã thật sự thi hành.
