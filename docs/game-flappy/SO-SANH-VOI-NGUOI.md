# So với người làm tay — game Flappy Bird + nhân RTOS, 11/10/2026

Dựng bằng `tools/uoc_luong_pert.py`, cùng phương pháp đã dùng cho robot 04/10. Script **tự
kiểm**: nó tính lại bảng robot và so với con số đã in trong
[`../robot-sinhvien/phien-sinhvien-04-10/SO-SANH-VOI-NGUOI.md`](../robot-sinhvien/phien-sinhvien-04-10/SO-SANH-VOI-NGUOI.md);
lệch một chữ số là nó kêu. Nên hai bảng dùng **chung một thước**, so được với nhau.

```
python tools/uoc_luong_pert.py game
```

---

## 1 · Phiên Agent — số đo được

| | |
|---|---|
| Thời gian | **5,09 giờ** (23:22 → 04:28, một mạch) |
| Lượt người gõ | 77 |
| Lượt mô hình | **366** |
| Lời gọi công cụ | 430 |
| Changeset | 46 |
| Hiện vật vào kho | 44 |

Trong 77 lượt người có **6 lượt trùng** do một lỗi của chính kênh kiểm giao diện (nó đọc lại
inbox và gửi cùng một câu sáu lần — đã vá, xem README §7.4). Sáu lượt ấy tiêu mô hình thật.

### Token và tiền

Cách tách y như lần trước: token **vào mới** là phần tăng thêm so với lượt trước, phần trùng là
**đọc lại từ đệm**. Kho không lưu bảng giá, nên tiền trình bày thành ba kịch bản đơn giá.

| | token |
|---|---|
| vào mới | **3,98 M** |
| đọc lại từ đệm | **26,57 M** (87,0 % token vào) |
| ra (kể cả phần suy nghĩ) | **0,25 M** |

| Kịch bản (USD / triệu token) | Vào mới | Đệm | Ra | **Tiền cả phiên** |
|---|---|---|---|---|
| A — thấp | 0,075 | 0,019 | 0,30 | ≈ 0,88 USD · **22 nghìn đồng** |
| **B — giữa** | 0,15 | 0,0375 | 0,60 | ≈ 1,74 USD · **43 nghìn đồng** |
| C — cao | 0,30 | 0,075 | 2,50 | ≈ 3,82 USD · **95 nghìn đồng** |

*(tỉ giá 24 818 đ/USD, suy từ chính cặp số đã in ở tài liệu robot: 1,37 USD ↔ 34 nghìn đồng)*

---

## 2 · Nếu một đội người làm tay — ước lượng PERT

Đủ bốn khâu: phân tích, thiết kế, viết mã, kiểm thử. Mỗi dòng ba mức, lấy theo
`(nhanh + 4 × thường + chậm) / 6`.

**Không tính 94 877 dòng BSP của hãng** — một đội người cũng lấy nguyên nó, không sửa, nên nó
không phải ngày công của ai.

| Việc | Vai | Nhanh | Thường | Chậm | **Ngày công** |
|---|---|---|---|---|---|
| Đọc tài liệu bo (LCD/DSI/SDRAM/cảm ứng/nút), chốt yêu cầu nghiệm thu | Senior | 0,5 | 1 | 2 | **1,08** |
| Lập hồ sơ panel: độ phân giải, hệ màu, DPI, bộ đệm khung so với RAM | Mid | 0,5 | 1 | 2 | **1,08** |
| Thiết kế ba màn hình theo toạ độ pixel thật, bảng phần tử sửa được | Mid | 1 | 2 | 4 | **2,17** |
| Thiết kế nhân RTOS: bảng tác vụ, TCB, ngân sách ngăn xếp, cơ chế chuyển ngữ cảnh | Senior | 1 | 2 | 5 | **2,33** |
| **Viết nhân RTOS: lập lịch, SysTick, PendSV hợp ngữ naked, ngữ cảnh FPU** | Senior | 1 | 3 | **8** | **3,50** |
| **Dựng nền BSP: xung nhịp 180 MHz + Over-Drive, LTDC/DSI, SDRAM, cảm ứng I2C** | Senior | 1 | 3 | **8** | **3,50** |
| Viết mã vẽ ba màn hình bằng `BSP_LCD_*` | Mid | 1 | 2 | 4 | **2,17** |
| Lớp vẽ từng khung theo dirty-rect: xoá/vẽ chim, cọc, điểm | Mid | 1 | 2 | 5 | **2,33** |
| Máy trạng thái game, vật lý, va chạm, tính điểm | Mid | 1 | 2 | 4 | **2,17** |
| Đường đầu vào: nút PA0 chống rung và cảm ứng FT6206 qua I2C | Mid | 0,5 | 1 | 3 | **1,25** |
| Chỉnh vật lý cho chơi được (trọng lực, xung vỗ cánh, khe cọc) | Mid | 0,5 | 1 | 3 | **1,25** |
| **Nạp và gỡ lỗi trên bo tới khi chơi được** | Senior | 1 | 3 | **8** | **3,50** |
| Đo nghiệm thu: nhịp nhân, đọc ngược Flash, bảng vector, ngân sách RAM | QA | 0,5 | 1 | 3 | **1,25** |
| Tài liệu và báo cáo | Mid | 0,5 | 1 | 3 | **1,25** |
| **TỔNG** | | **11** | **25** | **62** | **28,8 ngày công** |

Độ lệch chuẩn PERT **±2,6 ngày**:

| Mức tin | Khoảng |
|---|---|
| ~68 % | **26 – 31 ngày công** |
| ~95 % | **24 – 34 ngày công** |

Ba dòng có mức chậm gấp tám lần mức nhanh, và đó là ba chỗ rủi ro thật — cả ba đều đã **rơi về
phía mức chậm** trong phiên này:

* **Nhân RTOS** (1 → 8). `PendSV` phải lưu `r4-r11` + `EXC_RETURN`, và lưu `s16-s31` *có điều
  kiện* theo bit 4 của `EXC_RETURN`. Sai chỗ này là `HardFault` không có vết.
* **Nền BSP** (1 → 8). Phiên này Agent đi đường tắt: tự khai một header với tám hàm
  `BSP_LCD_*` **rỗng**. Liên kết sạch, nạp được, màn hình trống. Phải đưa BSP thật vào rồi
  dựng lại.
* **Gỡ lỗi trên bo** (1 → 8). Bốn vòng: màn hình trống → nút không ăn → nút tô sai màu →
  màn chơi đứng im.

### Cần mấy người, bao lâu

| Vai | Ngày công | Phần |
|---|---|---|
| Kỹ sư nhúng **Senior** | **13,9** | 48 % |
| Kỹ sư nhúng **Mid** | 13,7 | 47 % |
| **QA** nhúng | 1,2 | 4 % |
| Quản lý dự án (20 % thời lượng) | 5,8 | — |

Đội ít nhất: **1 Senior + 1 Mid + QA một phần**. Lịch khoảng **3 tuần**. Khác bài robot ở chỗ
Senior và Mid gần bằng nhau — phần thiết kế màn hình và phần game là việc chia được, nên hai
người chạy song song được; chỉ nhân RTOS, nền BSP và gỡ lỗi trên bo là không chia.

### Tiền nhân sự

Cùng bảng lương với lần trước *(lương tháng, triệu đồng; chia 21 ngày làm việc, nhân 1,4 cho
bảo hiểm, chỗ ngồi, thiết bị)*.

| Kịch bản | Tiền phát triển | Kèm quản lý |
|---|---|---|
| Thấp | 56,6 triệu | **≈ 70 triệu** |
| **Giữa** | **77,3 triệu** | **≈ 97 triệu** |
| Cao | 98,9 triệu | **≈ 124 triệu** |

---

## 3 · Hai cột cạnh nhau

| | Đội người (ước lượng PERT) | Phiên Agent (đo được) |
|---|---|---|
| Thời gian | **28,8 ngày công ±2,6** · ~3 tuần lịch | **5,09 giờ**, một đêm |
| Giờ người | **230 giờ** (28,8 × 8) | **5,09 giờ** |
| Tiền | **≈ 97 triệu đồng** | **≈ 43 nghìn đồng** |
| Chạy trên bo | có | **có** — màn hình lên, chạm chơi được |

Chênh **≈ 45 lần về giờ** và **≈ 2 300 lần về tiền**.

---

## 4 · Bốn điều bảng trên KHÔNG chứng minh

**Một — ba mức của mỗi dòng là PHÁN ĐOÁN, không phải số đo.** Không có bộ dữ liệu lịch sử của
đội nào ở đây. Con số ra là một **thang so sánh giữa các việc dùng chung một thước**, không
phải một lời hứa về chi phí.

**Hai — độ lệch chuẩn HẸP hơn thực tế.** Công thức cộng phương sai, tức giả định các dòng trượt
**độc lập** với nhau. Trong một dự án thật, việc trượt thường trượt cùng nhau: cùng một hiểu
lầm về phần cứng làm hỏng cả ba dòng.

**Ba — 5,09 giờ của Agent KHÔNG so được trực tiếp với 230 giờ của người.** Phần lớn thời gian
phiên này là **vá chính EIDE**, không phải làm game: ba lỗi công cụ (kênh giao diện gửi trùng
sáu lần, một `enum` số làm Agent tê liệt, tab Màn hình không hiện trong app) và ba lỗi của bộ
công cụ thiết kế (hàm rỗng không bị bắt, bản dựng lỗi thời, HTML và C vẽ khác nhau). Cột người
chỉ tính phần làm game. So thẳng hai con số là so sai — chênh thật **có lợi cho Agent hơn**
con số in ở trên, nhưng tôi không dựng một con số "đã hiệu chỉnh", vì tách giờ nào cho việc nào
trong một phiên đan xen là một phép chia tôi không đo được.

**Bốn — game CHƯA được xác nhận chơi đúng hoàn toàn.** Cột người tính cả dòng *"gỡ lỗi trên bo
tới khi chơi được"*. Phía Agent, tới lúc chốt tài liệu này thì đã đo được: nhịp nhân 1 kHz, đọc
ngược Flash khớp từng byte, chạm màn hình vào được game, vòng `START → PLAY → GAMEOVER → PLAY`
chạy đủ. **Chưa đo được**: số khung hình mỗi giây thật, và chưa có một lượt chơi dài nào được
xác nhận. Nên hai cột chưa hoàn toàn cùng một mức "xong".
