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

---

## C · Một câu thêm vào mục 2.6

Bảng 2.5 liệt kê mười tệp kèm số dòng. **Số dòng ấy là thông tin, không phải chỉ tiêu.** Nếu
việc của bạn cần ít tệp hơn hoặc ít dòng hơn thì cứ làm ít, và nói ra.

Lý do có câu này: ở việc RTOS, tiêu chí người viết là *"mọi tệp mã nguồn đều vào được ảnh"* —
mà một tệp rỗng thì không vào được ảnh, nên tác tử **viết thêm 36 dòng mã không ai gọi** cho
tệp rỗng có ký hiệu, rồi ghi cả động cơ vào chú thích. Tiêu chí ấy tự nó khuyến khích làm sai.

**Tệp nào không có việc gì để làm thì xoá đi.** Thà nhận một dự án ít tệp hơn mà tệp nào cũng
có lý do tồn tại.
