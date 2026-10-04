# So với người làm tay — phiên robot 04/10/2026

Hai cột dưới đây **không cùng loại số**, nói trước cho rõ: cột Agent là **đo được** từ sổ cái và
nhật ký mô hình; cột người là **ước lượng** PERT. Trộn hai loại vào một bảng mà không nói thì
bảng đó nói sai.

Phương pháp giữ **đúng** bản [`docs/robot-tu-can-bang/BAO-CAO-SO-SANH.md`](../../robot-tu-can-bang/BAO-CAO-SO-SANH.md)
để hai phiên so được với nhau: PERT ba mức, đơn giá bằng lương tháng × 1,4 ÷ 21 ngày, tỉ giá
25 000 đồng/USD.

---

## 1 · Phiên Agent — số đo được

| | |
|---|---|
| Thời gian từ đầu tới cuối | **4,53 giờ** (16:57 → 21:29) |
| Lời gọi mô hình | **670**, tất cả `gemini-3.8-flash`, 20 phiên con |
| Thời gian chờ mô hình | **0,69 giờ** trong 4,53 giờ đó |
| Lời gọi công cụ | **541** · 32 loại · 18 lượt bị chặn (3,3 %) |
| Phần mềm giao ra | **1 124 dòng C**, 10 mô-đun, ảnh **9 382 byte** / 32 KB Flash |
| Kết quả | **robot đứng được** (quan sát của người) |

### Token và tiền

Cách tách: trong mỗi phiên con, lượt đầu là token **mới**; các lượt sau, phần trùng với lượt
trước là **đọc lại từ đệm**, phần tăng thêm là mới. Quy đổi 3,5 ký tự một token (văn bản Việt
lẫn mã nguồn).

| | ký tự | token |
|---|---|---|
| vào mới | 8 475 140 | **2,42 M** |
| đọc lại từ đệm | 83 857 928 | **23,96 M** |
| ra | 620 985 | **0,18 M** |

Đệm chiếm **90,8 %** token vào — cùng cơ chế như phiên 01/10 (93,6 %): mỗi lượt gửi lại cả đoạn
hội thoại đã có, và loại token này rẻ hơn nhiều.

Kho không lưu bảng giá, nên tiền trình bày dưới dạng ba kịch bản đơn giá:

| Kịch bản (USD / triệu token) | Vào mới | Đệm | Ra | **Tiền cả phiên** |
|---|---|---|---|---|
| A — thấp | 0,075 | 0,019 | 0,30 | **≈ 0,69 USD · 17 nghìn đồng** |
| **B — giữa** | 0,15 | 0,0375 | 0,60 | **≈ 1,37 USD · 34 nghìn đồng** |
| C — cao | 0,30 | 0,075 | 2,50 | **≈ 2,97 USD · 74 nghìn đồng** |

---

## 2 · Nếu một đội người làm tay — ước lượng PERT

Đủ bốn khâu: phân tích, thiết kế, viết mã, kiểm thử. Mỗi dòng ba mức, lấy theo
`(nhanh + 4 × thường + chậm) / 6`.

| Việc | Vai | Nhanh | Thường | Chậm | **Ngày công** |
|---|---|---|---|---|---|
| Đọc tài liệu phần cứng và phụ lục mốc NGƯỜI, lập bản đồ chân | Senior | 1 | 2 | 4 | **2,17** |
| Dựng bảng điều kiện nghiệm thu đối chiếu được | Mid | 1 | 2 | 4 | **2,17** |
| Thiết kế cấu trúc 10 mô-đun, chốt phân tầng | Senior | 1 | 2 | 4 | **2,17** |
| Thiết kế máy trạng thái 7 trạng thái | Mid | 0,5 | 1 | 2 | **1,08** |
| **Hàm ngắt 50 kHz: 0 số thực, 0 phép chia** | Senior | 1 | 3 | **8** | **3,50** |
| I2C bare-metal, MPU6050, bộ lọc bù | Mid | 1 | 2 | 4 | **2,17** |
| PID và quy đổi ngõ ra sang chu kỳ bước | Senior | 1 | 2 | 5 | **2,33** |
| Máy trạng thái, đo pin bằng ADC, chế độ khoá khi chạy USB | Mid | 1 | 2 | 3 | **2,00** |
| UART vòng đệm, bản tin 10 trường có số thứ tự | Mid | 1 | 2 | 4 | **2,17** |
| **Gỡ lỗi trên bo tới khi robot đứng** | Senior | 2 | 5 | **12** | **5,67** |
| Đo nghiệm thu: tần số ISR neo đồng hồ tường, objdump, chu kỳ vòng | Senior | 1 | 2 | 5 | **2,33** |
| Bộ kiểm trên máy và đo độ nhạy bộ kiểm | QA | 1 | 2 | 4 | **2,17** |
| Tài liệu và báo cáo | Mid | 1 | 2 | 4 | **2,17** |
| **TỔNG** | | **13,5** | **29** | **63** | **32,1 ngày công** |

Độ lệch chuẩn PERT **±2,6 ngày**:

| Mức tin | Khoảng |
|---|---|
| ~68 % | **29 – 35 ngày công** |
| ~95 % | **27 – 37 ngày công** |

Con số này **cao hơn bản 01/10 đúng 1,1 ngày** (31,0 → 32,1), và chênh ấy nằm ở một dòng: phiên
này có thêm việc **đo nghiệm thu** mà phiên trước không có. Hai bản dùng cùng mức cho mọi dòng
còn lại, nên chúng so được với nhau.

Hai dòng có mức chậm nhất gấp bốn đến sáu lần mức nhanh nhất, và đó là hai chỗ rủi ro thật:

- **Hàm ngắt 50 kHz** (1 → 8). Tài liệu cấm số thực và phép chia trong hàm này. Ai chưa từng
  viết bộ tích luỹ pha nguyên thì mất vài vòng thử.
- **Gỡ lỗi trên bo** (2 → 12). Ở phiên 01/10 dòng này **đã rơi về phía mức chậm**: mười vòng
  cắm bo, và chỉ xong khi có một bản chạy được để so. Phiên này **không rơi về mức chậm**, và
  mục 4 nói vì sao.

### Cần mấy người, bao lâu

| Vai | Ngày công | Phần |
|---|---|---|
| Kỹ sư nhúng **Senior** | **18,2** | 57 % |
| Kỹ sư nhúng **Mid** | 11,7 | 37 % |
| **QA** nhúng | 2,2 | 7 % |
| Quản lý dự án (20 % thời lượng) | 6,4 | — |

Đội ít nhất: **1 Senior + 1 Mid + QA một phần + quản lý 20 %**. Lịch khoảng **4 tuần**, và
18,2 ngày công của Senior là chỗ **không chia việc được** — đọc tài liệu rồi mới thiết kế, có
mã rồi mới gỡ lỗi trên bo. Thêm người thứ ba không rút ngắn phần này.

### Tiền nhân sự

| Vai | Thấp | Giữa | Cao |
|---|---|---|---|
| Senior nhúng | 40 | 55 | 70 |
| Mid nhúng | 20 | 27 | 35 |
| QA nhúng | 15 | 20 | 25 |
| Quản lý dự án | 35 | 50 | 65 |

*(lương tháng, triệu đồng; chia 21 ngày làm việc, nhân 1,4 cho bảo hiểm, chỗ ngồi, thiết bị)*

| Kịch bản | Tiền phát triển | Kèm quản lý | Quy đổi |
|---|---|---|---|
| Thấp | 66,3 triệu | **≈ 81 triệu** | ≈ 3 250 USD |
| **Giữa** | **90,6 triệu** | **≈ 112 triệu** | ≈ 4 482 USD |
| Cao | 115,8 triệu | **≈ 144 triệu** | ≈ 5 744 USD |

---

## 3 · Hai cột cạnh nhau

| | Đội người làm tay (ước lượng) | Phiên Agent (đo được) |
|---|---|---|
| Thời gian | **32,1 ngày công ±2,6** · khoảng **4 tuần** lịch | **4,53 giờ**, một buổi chiều |
| Nhân lực | 1 Senior + 1 Mid + QA + quản lý | **1 người** + Agent |
| Tiền | **≈ 112 triệu đồng** (mức giữa) | **≈ 34 nghìn đồng** tiền mô hình |
| Robot có đứng được không | có | **có** |

| | |
|---|---|
| Chênh về **giờ** | 32,1 ngày × 8 giờ = **257 giờ** so với **4,53 giờ** → **≈ 57 lần** |
| Chênh về **tiền** | 112 triệu so với 34 nghìn → **≈ 3 300 lần** |

Và so với chính phiên robot 01/10, cùng con robot, cùng phương pháp tính:

| | 01/10 | 04/10 |
|---|---|---|
| Thời gian phiên | 7,4 giờ | **4,53 giờ** |
| Lời gọi mô hình | 1 415 | **670** |
| Lời gọi công cụ | 1 108 | **541** |
| Lời gọi bị chặn | 89 (8,0 %) | **18 (3,3 %)** |
| Tiền mô hình (mức giữa) | 340 nghìn đồng | **34 nghìn đồng** |
| Phần mềm giao ra | 1 820 dòng | **1 124 dòng** |
| Robot đứng | có, sau **mười** vòng cắm bo | **có** |

Phiên làm lại **rẻ hơn 10 lần** và **nhanh hơn 1,6 lần** cho cùng kết quả.

---

## 4 · Năm điều bảng trên KHÔNG chứng minh

Nói trước để không ai đọc quá tay. Điều thứ nhất là điều quan trọng nhất.

1. **Tham số đã được trao sẵn, Agent không tự tìm ra.** Phụ lục
   [`PHU-LUC-MOC-NGUOI-VA-DO-TAN-SO.md`](../PHU-LUC-MOC-NGUOI-VA-DO-TAN-SO.md) mục E trao cho
   Agent **bộ số đã chạy thật**: `KP 12,0 · KI 0,4 · KD 10,0` và `ACCEL_OFFSET_Z 92`. Chính con
   số `92` là chỗ phiên 01/10 ghi sai thành `535`, lệch 3,1° điểm cân bằng, và là lỗi nặng nhất
   của phiên ấy. Phiên này đúng ngay từ đầu **vì được cho**, không vì tự tìm ra.

   Nên con số "nhanh hơn 1,6 lần" **không** đo năng lực Agent tăng lên bấy nhiêu. Nó đo việc
   **một phiên đã làm xong phần khó nhất và ghi lại được**. Đó vẫn là một kết quả thật — tài
   liệu hoá được thì lần sau rẻ đi — nhưng nó là kết quả của *quy trình*, không của *mô hình*.

2. **Người vẫn nằm trên đường quyết định.** Agent không chạm được vào robot. Mọi lượt cấp nguồn,
   dựng robot lên, quan sát nó ngã về phía nào đều do người làm. Phần ấy nằm **trong** 4,53 giờ
   nhưng không rút ngắn được.

3. **34 nghìn đồng không phải toàn bộ chi phí.** Chưa tính giờ của người, chưa tính phần cứng
   (bo, cảm biến, driver, pin), chưa tính thời gian dựng chính EIDE.

4. **Một lỗi trong phiên này do người đo gây ra, không do Agent.** Phép lọc dữ liệu thô sai đã
   làm mất **năm lượt** đuổi một lỗi định thời không tồn tại. Thời gian ấy nằm trong 4,53 giờ.
   Nếu người đo cẩn thận hơn thì con số còn thấp hơn — nghĩa là **4,53 giờ không phải mức sàn**.

5. **Phép đo lúc robot đứng chưa lấy được.** Lần thu đầu bị chính phép đo phá: mở cổng nối tiếp
   làm reset bo, reset làm chạy lại pha hiệu chuẩn con quay, mà lúc ấy người **đang giữ robot
   trên tay** — chuyển động tay bị chốt thành độ lệch con quay, nên góc trôi đều 3,1°/giây và
   robot ngã ở `30°`. Số liệu ấy **không dùng được**, và câu "robot đứng được" hiện là **quan
   sát của người** chứ chưa có phân bố góc kèm theo.

---

## 5 · Rút ra

Phiên 01/10 kết luận: *sáu trong bảy lỗi do **người** bắt bằng cách mở mã ra đối chiếu.*

Phiên 04/10 đảo chiều. Đếm tay trên nhật ký:

| | số | nội dung |
|---|---|---|
| lỗi **Agent** do người bắt | **1** | bảng nghiệm thu gọi sai ngoại vi, và chấm ĐẠT bằng cấu hình thay vì số đo |
| lỗi **người** do Agent bắt | **3** | cảnh báo trước bẫy *đếm bằng chính bộ đếm đang đo*; tìm ra lỗ **đọc rách** biến 32 bit; **bác kết luận của người** về điều kiện 250 Hz bằng lý do lượng tử hoá `millis` 1 ms |
| lỗi **người** do chính người bắt | **2** | hai phép lọc dữ liệu thô sai |

Nên kết quả đáng báo cáo của phiên này không phải mấy con số rút ngắn, mà: **Agent đã bác được
kết luận sai của người, bằng lý do kỹ thuật người chưa nghĩ tới, trước khi kết luận ấy vào báo
cáo.** Ở phiên 01/10, không một chỗ sai nào do Agent tự tìm ra.

Bảng trên **đếm tay**, phạm vi là phần robot sau khi tài liệu đầu vào đã dựng lại — không phải
phép đo tự động, và không so trực tiếp được với con số "bảy lỗi" của phiên 01/10 vì hai phiên
dừng ở hai chỗ khác nhau.
