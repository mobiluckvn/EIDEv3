# Báo cáo tổng — chạy toàn bộ usecase và quét toàn bộ giao diện

Hai phép đo, một bảng. Nguồn đề bài: `docs/review-v3/test/Usecase_Test_23-09-2026.md` (19 usecase · 76 ca kiểm).

## Tự kiểm: có sót gì không

| Câu hỏi | Trả lời |
|---|---|
| Đủ 76 mã TC trong kết quả? | đủ 76/76 |
| Có mã lạ không nằm trong đề bài? | không |
| Đủ 11 bề mặt trong bộ quét giao diện? | đủ 11/11 |
| Số ô kiểm giao diện | 124/124 đạt |

## Tổng ca kiểm

Hai cột: **máy chấm** (từ khoá + chuỗi công cụ) và **sau khi đọc tay** (đọc nguyên văn từng lời đáp). Máy chấm là lượt sàng, không phải phán quyết — nó đã cho cả ô xanh giả lẫn ô đỏ giả trong chính đợt này, xem `LOI-TIM-DUOC.md`.

| Nhãn | Máy chấm | Sau khi đọc tay |
|---|---|---|
| Đạt | 64 | 65 |
| Không đạt | 4 | 3 |
| Ngoài phạm vi | 2 | 2 |
| Cần người | 3 | 3 |
| Cần thiết bị | 3 | 3 |
| Chưa chạy | 0 | 0 |
| **Tổng** | **76** | **76** |

**1 ca đổi nhãn sau khi đọc tay:**

| TC | Máy chấm | Đọc tay | Loại | Vì sao |
|---|---|---|---|---|
| TC028 | Không đạt | Đạt | lỗi PHÉP CHẤM | Ô ĐỎ GIẢ, và tác tử ĐÚNG hơn đề bài: tôi viết 'dự án có hơn 500 tệp' mà không dựng tệp nào. Nó quét rồi trả lời 'dự án thực tế chỉ có 2 tệp .c, không phải hơn 500' — đúng thứ N6 đòi. Lỗi nằm ở bộ dữ liệu mẫu của tôi, không ở sản phẩm. |

Trong **68 ca đo được**: **65 đạt** (96 %). 8 ca còn lại mang nhãn riêng — gọi chúng là *không đạt* thì bảng nói sai về sản phẩm.

## Theo usecase

| UC | Tên | Đạt / đo được | Ca không đạt |
|---|---|---|---|
| UC01 | Làm rõ ý tưởng và đề xuất phương án giải pháp | 6/7 | TC006 |
| UC02 | Từ phương án đến thiết kế mạch | 6/7 | TC008 |
| UC03 | Sinh mã, biên dịch và mô phỏng | 8/8 | — |
| UC04 | Nhập dự án có sẵn (KiCad + mã nguồn) | 6/6 | — |
| UC05 | Nạp và gỡ lỗi trên mạch thật | 6/6 | — |
| UC06 | Rà soát thiết kế và mã nguồn | 4/4 | — |
| UC07 | Hỏi đáp trên tài liệu kỹ thuật | 2/2 | — |
| UC08 | Tìm linh kiện thay thế | 2/2 | — |
| UC09 | Chuyển firmware sang nền tảng khác (port) | 2/2 | — |
| UC10 | Phân tích log và capture | 3/3 | — |
| UC11 | Kiểm thử đơn vị với mock phần cứng | 0/1 | TC052 |
| UC12 | Tối ưu năng lượng | 2/2 | — |
| UC13 | Tính toán kỹ thuật | 2/2 | — |
| UC14 | Cập nhật firmware từ xa (OTA) | 3/3 | — |
| UC15 | Xuất hồ sơ sản xuất | 1/1 | — |
| UC16 | Truy vết và tài liệu | 2/2 | — |
| UC17 | Quản lý phiên và phiên bản | 2/2 | — |
| UC18 | An toàn và thao tác nguy hiểm | 3/3 | — |
| UC19 | Chịu lỗi hệ thống | 5/5 | — |

## 3 ca không đạt — chi tiết

### TC006 · Người dùng đổi yêu cầu giữa chừng

- **Người gõ:** À thêm nữa, phải chạy bằng pin.
- **Đề bài chờ:** Cập nhật đặc tả (v2), đánh giá lại phương án bị ảnh hưởng, nói rõ phần nào phải làm lại
- **Máy chấm:** 1/2 dấu hiệu: ảnh hưởng · 24s
- **Công cụ đã gọi:** `store.list → store.list → store.req_create → ask_user`

<details><summary>Nguyên văn lời đáp</summary>

```
[Tác tử] Yêu cầu chạy bằng pin ảnh hưởng trực tiếp đến công suất tiêu thụ của cả 3 phương án kiến trúc đang xét (PA-A, PA-B, PA-C) và kéo theo khối quản lý sạc/nguồn (PMIC/BMS). Tôi cần làm rõ một số kỳ vọng về nguồn pin:

1. Thời lượng hoạt động bằng pin liên tục mong muốn là bao lâu?  *(Khoảng 3-4 giờ liên tục — anh vừa nói trong câu)*
   _vì sao hỏi: Để tính toán dung lượng pin cần thiết và kiểm tra xem các phương án vi tính nhúng (như SBC) có khả thi về mặt nhiệt và kích thước không._
   [Xem trọn vẹn 1-2 bộ phim (~2 - 4 giờ)] · [Xem cả ngày hoặc nửa ngày (> 6 giờ)] · [Càng lâu càng tốt / Chưa chốt]
2. Anh có ưu tiên loại pin hay kích thước thiết bị cụ thể nào không?  *(Pin Li-ion 18650 hoặc Li-Po — anh vừa nói trong câu)*
   _vì sao hỏi: Để thiết kế mạch sạc, kích thước hộp và cân nhắc tính an toàn khi sử dụng._
   [Pin Li-ion 18650 (dễ tháo lắp/thay thế)] · [Pin Li-Po gắn trong (mỏng gọn)] · [Chưa định hình / Nhờ tư vấn]
3. Kết nối mạng LAN để nhận phim mới là Wi-Fi hay cắm dây cáp?  *(Wi-Fi — anh vừa nói trong câu)*
   _vì sao hỏi: Cắm dây Ethernet tiêu hao thêm dòng đáng kể và làm giảm tính cơ động của thiết bị chạy pin._
   [Wi-Fi (không dây hoàn toàn)] · [Cắm dây mạng Ethernet RJ45] · [Cả hai]

_Nếu anh bỏ qua, tôi sẽ đi tiếp với giả định: Nếu chưa có thông tin cụ thể, tôi sẽ tạm giả định thiết bị dùng 1-2 cell pin Li-ion 18650 (hoặc Li-Po ~2500-3000 mAh), sạc qua USB-C, thời lượng xem liên tục tối thiểu khoảng 3-4 giờ và dùng kết nối Wi-Fi._
```

</details>

### TC008 · Tìm tài liệu và chọn linh kiện có trích nguồn

- **Người gõ:** Lên thiết kế mạch giúp mình: bộ đo nhiệt độ dùng STM32F103 và cảm biến DS18B20, cấp nguồn 5 V từ USB.
- **Đề bài chờ:** Mỗi linh kiện chính có datasheet (đường dẫn, phiên bản), lý do chọn; thông số quan trọng có trích trang
- **Máy chấm:** 0/1 dấu hiệu: — · 37s
- **Công cụ đã gọi:** `ledger.query → store.req_create → store.req_create → memory.note → ask_user`

<details><summary>Nguyên văn lời đáp</summary>

```
[Tác tử] Mình đã ghi nhận yêu cầu và mục tiêu dự án. Để tiến hành thiết kế sơ đồ mạch và chọn linh kiện chính xác, mình cần làm rõ một số chi tiết kỹ thuật sau:

1. Bạn muốn thiết kế mạch tích hợp toàn bộ chip rời STM32F103C8T6 trên bo, hay thiết kế dạng cắm module STM32 Blue Pill?  *(STM32F103 (bạn vừa nêu) — anh vừa nói trong câu)*
   _vì sao hỏi: Xác định mức độ chi tiết của sơ đồ nguyên lý và danh mục linh kiện (BOM)._
   [Thiết kế toàn bộ linh kiện rời trên bo (chip STM32F103C8T6 LQFP-48, thạch anh, LDO...)] · [Dùng chân cắm cho module bo mạch có sẵn (như STM32 Blue Pill)]
2. Dữ liệu nhiệt độ đo được sẽ hiển thị hoặc truyền đi đâu?  *(Chưa có thông tin hiển thị/truyền dữ liệu — anh vừa nói trong câu)*
   _vì sao hỏi: Quyết định các khối giao tiếp ngoại vi và chân GPIO cần phân bổ._
   [Truyền qua USB Virtual COM Port (USB-CDC) về máy tính] · [Xuất ra UART qua chip nạp/giao tiếp UART-USB (như CH340)] · [Hiển thị lên màn hình OLED I2C 0,96 inch (SSD1306)] · [Cả truyền USB và hỗ trợ kết nối màn hình OLED]
3. Bạn muốn dùng chuẩn cổng USB nào và cổng USB có cần nối dữ liệu vào STM32 không?  *(Cấp nguồn 5 V từ USB (bạn vừa nêu) — anh vừa nói trong câu)*
   _vì sao hỏi: Quyết định chân giắc USB và mạch bảo vệ/phần cứng USB Full-Speed._
   [USB Type-C (chỉ lấy nguồn 5 V)] · [USB Type-C (cấp nguồn 5 V và nối chân D+/D- vào USB của STM32)] · [Micro-USB]
4. Cảm biến DS18B20 sẽ được lắp đặt theo dạng nào?  *(DS18B20 (bạn vừa nêu) — anh vừa nói trong câu)*
   _vì sao hỏi: Xác định linh kiện footprint đầu nối và cách cấp nguồn (3 dây chuẩn hay ký sinh 2 dây)._
   [Cọc nối vít (terminal block/domino 3 chân) cho đầu dò DS18B20 dây chống nước] · [Hàn trực tiếp cảm biến vỏ TO-92 trên bo mạch] · [Hàng rào cắm (header 3 chân 2,54 mm)]

_Nếu anh bỏ qua, tôi sẽ đi tiếp với giả định: Nếu bỏ qua, tạm thời mặc định: dùng chip rời STM32F103C8T6 (LQFP-48), cổng USB Type-C chỉ cấp nguồn + hỗ trợ USB Full-Speed chuyển dữ liệu về máy tính, có chân header cắm màn hình OLED I2C 0,96 inch, và chân header/domino 3 chân cho DS18B20 cấp nguồn thường (VDD, GND, DQ)._
```

</details>

### TC052 · Sinh và chạy unit test với mock phần cứng

- **Người gõ:** Viết unit test cho phần logic của firmware rồi chạy giúp mình, báo độ phủ.
- **Đề bài chờ:** Test chạy trên máy chủ, có báo cáo đạt/không đạt và độ phủ
- **Máy chấm:** công cụ mong đợi: KHÔNG gọi cái nào · 40s
- **Công cụ đã gọi:** `fs.glob → fs.read → fs.read → ledger.query → tool.search → ledger.query → ledger.query → ask_user`

<details><summary>Nguyên văn lời đáp</summary>

```
[Tác tử] Hiện trong dự án chưa có phần logic được tách riêng (firmware/main.c đang ghi trực tiếp thanh ghi phần cứng 0x24/0x25, còn dem_xung.c nằm ở thư mục gốc). Em cần làm rõ đối tượng và cách anh muốn kiểm thử.

1. Anh muốn viết unit test cho logic của phần nào?  *(Tách logic nháy LED từ firmware/main.c sang firmware/control.c rồi viết test — anh vừa nói trong câu)*
   _vì sao hỏi: firmware/main.c đang gắn cứng thanh ghi AVR PB5 không chạy trực tiếp trên máy chủ được; cần tách hàm logic thuần (pure logic) hoặc chỉ định rõ tệp cần kiểm._
   [Tách logic nháy LED từ firmware/main.c sang firmware/control.c rồi viết test] · [Viết test cho logic đếm xung của dem_xung.c] · [Cả hai]

_Nếu anh bỏ qua, tôi sẽ đi tiếp với giả định: Nếu anh bỏ qua, em sẽ giả định mục tiêu là firmware/main.c (nháy LED): tách logic điều khiển LED sang firmware/control.c để chạy được trên máy chủ, viết bộ test trong test/test_control.c, rồi chạy test.run đo độ phủ._
```

</details>

## Ca không đo bằng máy được — và vì sao

| TC | Nhãn | Lý do |
|---|---|---|
| TC032 | Cần người | Cần RÚT bo ra khỏi máy để đo. Bo đang cắm thường trực và các ca khác cần nó. |
| TC033 | Cần người | Cần một bàn tay rút cáp đúng lúc đang ghi Flash. Máy không tự làm được, và tự động hoá việc này có thể để lại chip ở trạng thái dở dang. |
| TC034 | Cần thiết bị | Cần một bo thứ hai mang MCU khác. Trên bàn chỉ có STM32F469I-DISCO. |
| TC044 | Cần thiết bị | Cần một bản scan datasheet chất lượng kém THẬT. Dựng ảnh scan giả sẽ đo chính ảnh tôi dựng, không đo tài liệu thật. |
| TC053 | Cần thiết bị | Cần bàn thử HIL (hardware-in-the-loop) để chạy lặp 20 lần. |
| TC061 | Ngoài phạm vi | NGOÀI PHẠM VI v1.3 — chủ sản phẩm chốt 24/09/2026: phần PCB (bố trí mạch in, Gerber, drill, file gắp đặt, DRC) chưa làm trong sản phẩm này. |
| TC067 | Cần người | Bộ lái chạy một tiến trình một phiên; dựng phiên thứ hai là đổi công cụ đo giữa lúc đang đo. (Sổ cái ĐÃ có khoá liên tiến trình — xem DEV log.) |
| TC071 | Ngoài phạm vi | NGOÀI PHẠM VI v1.3 — EIDE là ứng dụng một người trên máy cá nhân, không có khái niệm tài khoản hay vai trò. |

## Giao diện

124/124 ô đạt qua 18 phần (11 bề mặt · khung chung · thanh trạng thái · widget sửa tay · bảng Giới thiệu · khổ cửa sổ nhỏ nhất). Ảnh từng bề mặt do chính app tự vẽ, ở `ket-qua-giao-dien/anh/`.

Không ô nào đỏ.

## Đọc bảng này thế nào

Máy chấm ca kiểm bằng **dấu hiệu bề mặt** — cụm từ phải/không được có trong lời đáp, và công cụ phải được gọi. Một lời đáp nhắc đúng chữ mà sai ý vẫn qua được; một lời đáp đúng ý mà dùng từ khác vẫn trượt. Nên ô xanh nghĩa là *có dấu hiệu của thứ đề bài chờ*, không phải *đã làm đúng*. Nguyên văn nằm ở `ket-qua-chay-lai/ket-qua.jsonl` — đó mới là chỗ kết luận.

Bộ quét giao diện thì đo trực tiếp thứ app đang hiện (số khối, nhãn rỗng, khối tràn khung, thẻ còn nút bấm được), nên nó chắc hơn. Nhưng nó cũng đã từng xanh trong khi màn hình sai hai lần — xem DEV-289 và DEV-290 — nên ảnh chụp là một phần của kết quả, không phải minh hoạ.
