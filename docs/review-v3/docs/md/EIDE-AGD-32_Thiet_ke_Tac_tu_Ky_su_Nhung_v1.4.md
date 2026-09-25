**EIDE — TÁC TỬ KỸ SƯ NHÚNG CÓ GIAO DIỆN**

**Thiết kế v1.4: Datasheet là nguồn sự thật, người dùng phê duyệt, tác tử tự làm**

*Mã tài liệu EIDE-AGD-32 · v1.0 · 24/09/2026*

|                      |                                                                                                                                                         |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Mã tài liệu**      | EIDE-AGD-32                                                                                                                                             |
| **Tên tài liệu**     | Thiết kế tác tử Kỹ sư Nhúng có giao diện — Datasheet là nguồn sự thật                                                                                   |
| **Phiên bản**        | v1.0 (thiết kế sản phẩm EIDE v1.4)                                                                                                                      |
| **Ngày**             | 24/09/2026                                                                                                                                              |
| **Dự án**            | EIDE — Embedded IDE với tác tử hỗ trợ kỹ sư nhúng (github.com/mobiluckvn/EIDE)                                                                          |
| **Khung**            | Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — PTIT                                                                                                  |
| **Người hướng dẫn**  | TS. Nguyễn Trung Hiếu                                                                                                                                   |
| **Tác giả**          | Vũ Trí Công                                                                                                                                             |
| **Tài liệu đầu vào** | Usecase_Test_Agent_Ky_Su_Nhung.xlsx (19 UC, 76 TC, kết quả đo 23/09/2026, máy trạng thái S0–S6 v1.3); bộ hồ sơ EIDE v1.2; EIDE-UXD-13 v2.0; EIDE-APD-08 |

***Lịch sử sửa đổi***

| **Phiên bản** | **Ngày**   | **Nội dung**                                                                                                                                                                                         | **Người sửa** |
|---------------|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| v1.0          | 24/09/2026 | Bản đầu: chốt 7 nguyên tắc, luồng 7 chặng theo ý định, Bản đồ tri thức mạch, luồng duyệt tài liệu, máy trạng thái v1.4 (6 sửa đổi từ kết quả đo), 9 tab giao diện, 8 cổng phê duyệt, lộ trình 4 đợt. | VTC           |

**1. Mục đích, phạm vi và bối cảnh**

Tài liệu này chốt thiết kế phiên bản 1.4 của tác tử (agent) hỗ trợ kỹ sư nhúng trong EIDE: một tác tử có giao diện, nhận lệnh bằng ngôn ngữ tự nhiên, căn cứ vào ý định của người dùng để đi qua các chặng tìm giải pháp → tổng hợp tri thức mạch → cài công cụ → viết mã → biên dịch → mô phỏng → nạp và gỡ lỗi trên mạch thật, và hiển thị mọi kết quả trên các tab để người và tác tử cùng làm.

Yêu cầu trục của phiên bản này: **mọi phép so sánh, kiểm tra và quyết định thiết kế phải dựa trên dữ liệu thật từ datasheet** — do người dùng nạp vào, hoặc do tác tử tìm trên mạng và người dùng phê duyệt. Mô hình ngôn ngữ lớn (LLM) không phải nguồn sự thật; nó chỉ là bộ suy luận trên các dữ kiện đã được kiểm chứng.

**1.1. Bối cảnh đo lường**

Bộ 19 usecase và 76 kịch bản kiểm thử đã được chạy tự động ngày 23/09/2026 (EideApp --kich-ban). Kết quả:

| **Chỉ số**     | **Giá trị**           | **Ghi chú**                                                                                                                       |
|----------------|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| Tổng test case | 76                    | 48 Happy + 28 Unhappy; 19 UC                                                                                                      |
| Đạt            | 16 (21%)              | Tập trung ở cổng an toàn (UC18), an toàn phần cứng (UC05), chống bịa (TC075), RAG có trích trang (TC042), ERC netlist (TC038/040) |
| Không đạt      | 51 (67%)              | Phần lớn do định tuyến/ngữ nghĩa lệnh, không phải do năng lực chuyên môn                                                          |
| Bị chặn        | 7                     | Cần mạch thật + bộ nạp (UC05), bàn thử HIL, scan kém, hai phiên song song                                                         |
| Bỏ qua         | 2                     | Ngoài phạm vi v1.3: PCB/Gerber (UC15), phân quyền (TC071)                                                                         |
| P1 đã test     | 12 đạt / 27 không đạt | Tỉ lệ đạt P1 = 31%                                                                                                                |

Điểm quan trọng: các ca ĐẠT gần như đều là ca "biết dừng, biết nói không, biết hỏi xác nhận" (S0, G-OPS, P-QUAL, P-SAFE, chống ảo giác). Các ca KHÔNG ĐẠT gần như đều chết trước khi chạm tới chuyên môn — vì hiểu sai câu lệnh, bịa đường dẫn, hoặc chặn ở một câu hỏi không cần thiết. Nói cách khác: phần "phòng thủ" của tác tử đã vững, phần "làm việc" đang bị chính đường định tuyến của nó ngáng chân. Thiết kế v1.4 vì vậy ưu tiên sửa đường định tuyến và dựng nền dữ liệu (datasheet → bản đồ tri thức) trước khi mở rộng năng lực.

**1.2. Phạm vi**

- **Trong phạm vi:** 7 chặng làm việc từ ý tưởng đến gỡ lỗi trên mạch thật (UC01–UC14, UC16–UC19); giao diện tab; cổng phê duyệt; luồng nạp và duyệt datasheet; Bản đồ tri thức mạch.

- **Ngoài phạm vi (quyết định 24/09/2026):** bố trí mạch in, Gerber, DRC, file gắp đặt (UC15); tài khoản/phân quyền (TC071) — EIDE là ứng dụng một người trên máy cá nhân.

**2. Bảy nguyên tắc bất biến**

Các nguyên tắc dưới đây là ràng buộc thiết kế (design invariants): mọi năng lực (capability), mọi màn hình và mọi lời gọi mô hình đều phải tuân theo; kiểm thử phải có ca đo cho từng nguyên tắc.

| **Mã** | **Nguyên tắc**                                         | **Ý nghĩa vận hành**                                                                                                                                                                                                                                                                                                         | **Ca đo**                  |
|--------|--------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| N1     | Datasheet là nguồn sự thật (datasheet-as-ground-truth) | Mọi con số dùng để so sánh, quyết định hay sinh mã phải truy vết được tới một tài liệu có phiên bản, số trang và trích đoạn. Không truy vết được thì không phải dữ kiện, chỉ là gợi ý.                                                                                                                                       | TC008, TC042, TC075        |
| N2     | Ba tầng tin cậy dữ liệu: Vàng – Bạc – Đồng             | Vàng: datasheet người dùng nạp/duyệt, đã trích xuất, đã ghim. Bạc: nguồn tìm trên mạng, người dùng đã duyệt nguồn nhưng chưa xác nhận từng số. Đồng: tri thức chung của mô hình (K9). Phép so sánh chỉ hợp lệ khi cả hai vế ≥ Bạc; vế Đồng làm kết quả mang nhãn "CHƯA KIỂM CHỨNG" và không được dùng để quyết định tự động. | TC013, TC021, TC031        |
| N3     | Kiểm kê thì xác định, phán đoán mới gọi mô hình        | Pha S2 đọc store ra bảng "dự án đang có gì" bằng mã xác định (0 token). Mô hình không bao giờ tự mô tả tình trạng dự án — đó là cửa đã sinh ra yêu cầu bịa REQ_HW_I2C ở TC008.                                                                                                                                               | TC008, TC065               |
| N4     | Hỏi một cụm, tối đa hai vòng, nói ra giả định          | Gom mọi khoảng trống của cả chuỗi vào một lần hỏi; hết vòng thì chạy với giả định và in giả định ra báo cáo.                                                                                                                                                                                                                 | TC004, TC057               |
| N5     | Cổng an toàn đứng trước phép đoán                      | S0 đọc chính câu người gõ, không đọc ý định; thao tác không đảo ngược (xoá flash, option bytes, RDP, eFuse), điện lưới, hạ chuẩn, pháp lý — chặn hoặc hỏi trước khi bất kỳ mô hình nào được gọi.                                                                                                                             | TC035, TC068, TC069, TC007 |
| N6     | Không đạt giả                                          | Tiêu chí chấp nhận là của người dùng; tác tử không sửa tiêu chí/test để ép đạt, không kết luận "đạt" từ log rỗng hay từ phần chưa mô phỏng.                                                                                                                                                                                  | TC022, TC019, TC076        |
| N7     | Chỉ thị cho tác tử ≠ yêu cầu sản phẩm                  | Câu lệnh điều khiển tác tử ("hãy cố tình gây lỗi cú pháp", "đọc tệp X", "xử lý repo 1200 tệp") không bao giờ được ghi thành yêu cầu chức năng (FR) của sản phẩm.                                                                                                                                                             | TC017, TC024, TC028        |

**3. Luồng làm việc theo ý định: bảy chặng**

Người dùng có thể vào ở bất kỳ chặng nào (đã có ý tưởng rõ, đã có thiết kế, đã có mã, đã có mạch). Pha S2 (kiểm kê) xác định dự án đang đứng ở chặng nào và chặng nào còn thiếu tiền đề; tác tử không bao giờ "đi lại từ đầu" khi hiện vật của chặng trước đã có trong store.

| **Chặng**                              | **Đầu vào**                                                                                                            | **Đầu ra (hiện vật)**                                                                                                                                                           | **Cổng**                                        | **Tab**                                   | **UC**                       |
|----------------------------------------|------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------|-------------------------------------------|------------------------------|
| C1. Làm rõ ý tưởng & đề xuất giải pháp | Mô tả bằng ngôn ngữ tự nhiên; câu trả lời cho cụm câu hỏi (mục tiêu, môi trường, chi phí, kích thước, nguồn, số lượng) | Đặc tả yêu cầu có phiên bản (v1, v2…); 2–4 phương án kiến trúc có chi phí, độ khó, rủi ro, nguồn tham khảo; phương án được chọn; cảnh báo rủi ro ẩn và mâu thuẫn vật lý bằng số | G-DESIGN (chọn phương án)                       | Yêu cầu & Giải pháp                       | UC01                         |
| C2. Tài liệu & Bản đồ tri thức mạch    | Datasheet/RM/errata do người nạp hoặc tìm mạng + duyệt; thiết kế có sẵn (KiCad, netlist, PDF)                          | Hộ chiếu chip đã ghim; linh kiện chính có datasheet + lý do chọn; sơ đồ khối; schematic/netlist; pinout không trùng AF; BOM; Bản đồ tri thức mạch (§4); kết quả ERC             | G-DATA (duyệt nguồn), G-DESIGN (duyệt thiết kế) | Tài liệu & Nguồn; Tri thức mạch; Thiết kế | UC02, UC04, UC06, UC07, UC08 |
| C3. Môi trường công cụ                 | Hộ chiếu chip (ISA, họ chip); kiểm kê máy                                                                              | Toolchain đúng ISA (arm-none-eabi-gcc, avr-gcc, riscv…), trình mô phỏng, công cụ nạp; phiên bản đã kiểm chứng; manifest ISA khớp chip                                           | G-TOOL (hỏi trước khi cài)                      | Công cụ                                   | UC03 (env.check), tool.\*    |
| C4. Firmware                           | Pinout đã duyệt; fact clock/ngoại vi từ datasheet; yêu cầu                                                             | Khung dự án; cấu hình clock/pinmux khớp schematic; driver; logic; biên dịch không lỗi, warning được giải thích; map file; tự sửa lỗi biên dịch ≤ N lần rồi dừng báo             | —                                               | Mã nguồn                                  | UC03, UC09, UC12             |
| C5. Mô phỏng                           | Firmware đã biên dịch; tiêu chí chấp nhận nêu TRƯỚC                                                                    | Log, ảnh chụp, VCD làm bằng chứng; kết luận đạt/không đạt theo tiêu chí; phần không mô phỏng được nêu rõ; timeout khi treo                                                      | G-QUAL (đổi tiêu chí phải hỏi)                  | Mô phỏng                                  | UC03, UC11, UC14             |
| C6. Mạch thật                          | Bo mạch + bộ nạp cắm vào máy; firmware                                                                                 | ID chip đọc từ probe đối chiếu với hộ chiếu; tóm tắt "nạp gì vào đâu"; nạp + verify; log UART/RTT; breakpoint; thanh ghi; khoanh vùng lỗi HW/SW; nhật ký gỡ lỗi                 | G-OPS (không đảo ngược), G-SAFE (điện, nhiệt)   | Mạch thật                                 | UC05, UC10, UC18             |
| C7. Xuyên suốt                         | Mọi chặng                                                                                                              | Phiên/dự án khôi phục đúng quyết định; tài liệu + ma trận truy vết; lưu trạng thái khi sự cố; báo cáo lượt chạy có giả định và chi phí                                          | G-SCOPE (việc lớn)                              | Nhật ký lượt chạy                         | UC16, UC17, UC19             |

**Quy tắc nối chặng:** mỗi năng lực khai báo requires (tiền đề) và produces (hiện vật). Bộ lập kế hoạch chỉ được xếp một nút khi tiền đề của nó có trong bảng kiểm kê hoặc được một nút đứng trước sinh ra; thiếu thì tự chèn nút tiền đề (ví dụ arch.decompose trước diagram.architecture — TC009) hoặc chuyển sang S3 để hỏi.

**4. Bản đồ tri thức mạch (Circuit Knowledge Map — CKM)**

Bản đồ tri thức mạch là hiện vật trung tâm của chặng C2 và là nền cho C4–C6. Nó trả lời câu hỏi "mạch này có gì, nối thế nào, và mỗi con số lấy từ đâu". Toàn bộ so sánh trong tác tử (mức logic, ngân sách bộ nhớ, timing bus, thay thế linh kiện, trùng chức năng chân) đều chạy trên bản đồ này, không chạy trên trí nhớ của mô hình.

**4.1. Thực thể và quan hệ**

| **Thực thể**                   | **Thuộc tính chính**                                                                   | **Quan hệ**                                              |
|--------------------------------|----------------------------------------------------------------------------------------|----------------------------------------------------------|
| Chip (hộ chiếu ns.part@semver) | Họ, lõi/ISA, Flash, RAM, dải VDD, xung tối đa, gói vỏ, errata áp dụng                  | CÓ_CHÂN → Pin; MÔ_TẢ_BỞI → Tài liệu                      |
| Pin                            | Số chân, tên, các chức năng thay thế (AF), mức điện áp, dòng tối đa, kéo lên/xuống nội | THUỘC → Chip; NỐI → Net; ĐƯỢC_GÁN → Chức năng (duy nhất) |
| Net                            | Tên, loại (nguồn/tín hiệu/bus), điện áp danh định, tải                                 | NỐI ↔ Pin; THUỘC → Bus/Nguồn                             |
| Module (khối chức năng)        | Tên, yêu cầu phục vụ, giao diện                                                        | GỒM → Chip/linh kiện; THỰC_HIỆN → Yêu cầu                |
| Bus (I2C/SPI/UART/CAN)         | Tốc độ, địa chỉ, điện trở kéo lên, chế độ                                              | GỒM → Net; NỐI → Module                                  |
| Nguồn (rail)                   | Điện áp, dòng cấp tối đa, ripple, bảo vệ                                               | CẤP → Chip/Module                                        |
| Ràng buộc                      | Từ yêu cầu (ngân sách Flash/RAM, dòng ngủ, giá, kích thước)                            | ÁP_LÊN → Chip/Module/Nguồn                               |
| Tài liệu                       | Loại (datasheet/RM/errata/AN), phiên bản, ngày, hash, nguồn URL, người duyệt           | SINH → Fact                                              |
| Fact (dữ kiện)                 | Xem 4.2                                                                                | VỀ → thực thể bất kỳ; THAY_THẾ → Fact cũ                 |

**4.2. Bản ghi dữ kiện (Fact) — đơn vị nhỏ nhất của sự thật**

Mỗi con số trong hệ thống là một bản ghi Fact, không phải một chuỗi trong prompt:

Fact { key: "I2C.SDA.pullup_typ", value: 4.7, unit: "kΩ", min: 2.2, max: 10, condition: "VDD=3.3V, 100 kHz", source: { doc: "ATmega328P-DS-rev.7810D", page: 215, quote: "…" }, tier: "VANG", approved_by: "user", approved_at: "2026-09-24T10:12", supersedes: null }

- **Truy vấn xác định:** bảng Fact truy vấn được bằng mã (SQL/graph query), không qua LLM. Câu hỏi "chân nào bật DMA cho SPI2" đi đường RAG có trích trang (TC042); câu hỏi "VDD tối đa bao nhiêu" đi đường tra Fact — nhanh, lặp lại được, không bịa.

- **Errata ưu tiên:** Fact từ errata thay thế (supersedes) Fact cùng khoá từ datasheet, và báo cáo phải ghi rõ.

- **Hai phiên bản datasheet:** trích xuất cả hai, dựng bảng khác biệt theo khoá, người dùng chọn bản dùng; bản đã dùng ghi vào hộ chiếu (TC011).

**4.3. Bộ so sánh dựa trên dữ kiện (fact-based compare)**

compare(fact_a, fact_b, rule) chỉ được gọi là hợp lệ khi cả hai vế có tier ≥ Bạc. Kết quả luôn kèm hai trích dẫn. Nếu một vế là Đồng (tri thức chung), kết quả mang nhãn CHƯA KIỂM CHỨNG, hiển thị màu vàng trên giao diện, và bộ lập kế hoạch ở S4 không được dùng nó làm điều kiện để đi tiếp mà không hỏi. Các luật so sánh đã có ca đo:

| **Luật**             | **Vế A (thiết kế)**             | **Vế B (datasheet)**        | **Kết luận**                                       | **Ca đo**      |
|----------------------|---------------------------------|-----------------------------|----------------------------------------------------|----------------|
| Mức logic            | Net nối chân MCU 3,3 V          | Ngoại vi xuất 5 V (VOH.max) | Thiếu chuyển mức → blocker + đề xuất level shifter | TC013          |
| Quá áp               | VDDIO của U2 trên net VBUS_5V   | VDDIO.max = 3,6 V           | overvoltage (blocker)                              | TC038 (đã đạt) |
| Ngân sách bộ nhớ     | Mảng const 65 536 byte          | Flash.max = 32 768 byte     | Vượt Flash → tối ưu hoặc đổi MCU                   | TC021          |
| Trùng chức năng chân | PA5 gán SPI1_SCK và TIM2_CH1    | Bảng AF của chip            | af_conflict (blocker)                              | TC009, TC040   |
| Kéo lên bus          | Net SDA/SCL không có R lên VDD  | Pull-up yêu cầu theo tốc độ | missing_pullup (major)                             | TC038          |
| Timing bus           | Capture I2C: khoảng SCL đo được | tHIGH/tLOW.min              | Vi phạm timing → giả thuyết nguyên nhân            | TC049          |
| Thay thế linh kiện   | Fact của linh kiện cũ           | Fact của ứng viên           | Pin-to-pin / cần sửa mạch + khác biệt thông số     | TC045, TC046   |
| Cắm ngược/đoản mạch  | Dòng đo được                    | Icc.max                     | NGẮT NGUỒN NGAY (G-SAFE trước mọi câu hỏi)         | TC036 (đã đạt) |

**Tính toán kỹ thuật (UC13):** cùng nguyên tắc — công thức chạy bằng mã (không nhẩm), mọi tham số đầu vào là Fact có nguồn hoặc là giá trị người dùng nhập được ghi nhãn "người dùng cho"; thiếu tham số thì hỏi đúng số còn thiếu kèm đơn vị, không lặng lẽ tự chọn (TC056, TC057).

**4.4. Lưu trữ**

- Đồ thị tri thức (KG): thực thể + quan hệ, xuất được ra sơ đồ khối và bảng pinout.

- Chỉ mục RAG theo trang: mỗi đoạn mang doc_id + page để trích dẫn; ngưỡng điểm khớp có thể hạ theo loại câu hỏi, nhưng dưới ngưỡng thì trả "không tìm thấy trong tài liệu" thay vì đoán (TC014, TC043).

- Bảng Fact: truy vấn xác định; là nguồn duy nhất của bộ so sánh và bộ sinh mã (clock/pinmux đọc từ đây).

- Phiên bản: mọi thay đổi CKM ghi vào sổ cái (ledger) với tác giả human:/agent:run-\*; quay lui theo 3 mức như UXD-13 v2.0.

**5. Luồng nạp tài liệu và phê duyệt (G-DATA)**

Đây là luồng hiện thực hoá yêu cầu "so sánh phải dựa trên datasheet thật, do người dùng nhập hoặc tìm trên mạng và người dùng phê duyệt". Nó thay thế hoàn toàn câu hỏi chặn "Chưa ghim hộ chiếu chip — chip nào?" (nguyên nhân của 6 ca không đạt).

| **Bước**                 | **Ai**     | **Việc**                                                                                                                                                                                                                                 | **Hiển thị**                                                                                                                                           |
|--------------------------|------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1\. Kích hoạt            | Người / S2 | Người nạp tệp (PDF/zip/ảnh) HOẶC S2 phát hiện chip đã được nêu trong câu (family_patterns) mà store chưa có datasheet                                                                                                                    | Thẻ đề nghị trong chat: "ATmega328P — anh vừa nói trong câu. Chưa có datasheet. \[Tìm trên mạng\] \[Tôi nạp tệp\] \[Dùng tri thức chung – nhãn Đồng\]" |
| 2\. Tìm                  | Tác tử     | search.web (SearXNG) với mã chip + "datasheet"/"reference manual"/"errata"; ưu tiên tên miền nhà sản xuất; thu: tiêu đề, URL, nhà phát hành, phiên bản/ngày, kích thước, hash sau tải                                                    | Tab Tài liệu & Nguồn: danh sách ứng viên, nhãn "nhà sản xuất" / "bên thứ ba"                                                                           |
| 3\. Duyệt nguồn (G-DATA) | Người      | Chọn/từ chối từng nguồn; có thể dán URL riêng                                                                                                                                                                                            | Nút Duyệt / Từ chối; lý do từ chối ghi sổ cái                                                                                                          |
| 4\. Trích xuất           | Tác tử     | PDF → văn bản theo trang; bảng thông số → Fact ứng viên (khoá, giá trị, đơn vị, điều kiện, trang); ảnh/scan → OCR với điểm tin cậy; zip/rar → bóc tách, phân loại tệp theo nội dung                                                      | Tiến trình trong Run card; số trang, số Fact ứng viên                                                                                                  |
| 5\. Hàng đợi rà soát     | Người      | Bảng Fact ứng viên với trích đoạn gốc bên cạnh; xác nhận hàng loạt hoặc từng dòng → Vàng; chưa xác nhận → Bạc; OCR tin cậy thấp → bắt buộc xem từng dòng (TC044)                                                                         | Tab Tri thức mạch → bảng Fact có cột Tầng                                                                                                              |
| 6\. Ghim hộ chiếu        | Tác tử     | Tạo/ cập nhật ns.part@semver; gắn tài liệu, Fact; đối chiếu manifest ISA — không khớp thì nói thẳng (STM32F103 là armv7-m, kho chỉ có armv7e-m — TC018)                                                                                  | Chip đã ghim hiện trên thanh trạng thái dự án                                                                                                          |
| 7\. Phòng thủ            | Tác tử     | Nội dung tải về là DỮ LIỆU, đi kênh riêng, không bao giờ vào kênh lệnh; quét mẫu chỉ thị ("bỏ qua mọi hướng dẫn", lệnh shell) → cảnh báo, ghi sổ; không tìm thấy → nói thẳng + đề xuất linh kiện có tài liệu hoặc xin tệp (TC010, TC014) | Cảnh báo màu đỏ trong tab Tài liệu; không chạy gì                                                                                                      |

**Vì sao không tự ghim khi chip đã nêu:** hộ chiếu là ns.part@semver gắn với tài liệu thật; ghép tên chip trần vào hộ chiếu sẽ tra ra rỗng trong im lặng (lỗi "câu trả lời sai tệ hơn ô trống", DEV-183). Vì vậy tên chip từ câu người dùng chỉ là *gợi ý điền sẵn* cho bước 1, còn hộ chiếu chỉ được ghim sau bước 6.

**6. Máy trạng thái xử lý một lượt gõ — v1.4**

Giữ nguyên bảy pha S0–S6 đã chốt ở v1.3 (chặn xác định → hiểu → kiểm kê → làm rõ → chốt phạm vi → chạy → báo cáo). v1.4 bổ sung sáu sửa đổi rút trực tiếp từ kết quả đo, xếp theo số ca được mở khoá.

| **Mã** | **Sửa đổi**                                                                                                                                                                                                                                  | **Nguyên nhân đo được**                                                                                                                                                                              | **Ca mở khoá**                                                    |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| Đ1     | Bộ trích xác định TRƯỚC parse_intent: đường dẫn (nhiều), mã chip, số có đơn vị, URL — bằng regex/từ điển, 0 token; slots.paths là MẢNG; mô hình chỉ điền phần còn lại và không được ghi đè slot đã trích xác định                            | archive.list hỏng E2000/E1000 trên đường dẫn bịa từ chính câu người dùng (11 ca); slots.path là chuỗi đơn nên mất một trong hai tệp (TC011); \${\_path} phụ thuộc mô hình nên không tất định (TC043) | TC010, 016, 020, 023, 045, 047, 052, 054, 058, 070, 072, 011, 043 |
| Đ2     | Phân loại tệp theo nội dung (magic bytes + đuôi) thành: archive / netlist / source / script / log / capture / pdf / image; mỗi loại có bộ đọc riêng; lỗi báo ĐÚNG LÝ DO ("định dạng Altium không hỗ trợ — xuất netlist/PDF", "tệp cụt/hỏng") | Netlist, .c, .sh, .PcbDoc đều bị đưa vào archive.list và báo "không nhận ra định dạng nén"                                                                                                           | TC023, 025, 026, 062, 070                                         |
| Đ3     | Hộ chiếu chip: từ CHẶN sang ĐỀ NGHỊ (luồng §5); chuỗi vẫn chạy được các nút không cần Fact Vàng (đề xuất phương án, sơ đồ khối) và đánh dấu nút chờ Fact                                                                                     | Dừng ở "Chưa ghim hộ chiếu chip — chip nào?" dù chip đã nêu hoặc chưa cần chip                                                                                                                       | TC002, 008, 015, 027, 046, 048                                    |
| Đ4     | Tách kênh: câu người gõ được phân thành {chỉ thị cho tác tử, mô tả sản phẩm, dữ liệu}; req.elicit chỉ nhận mô tả sản phẩm; rủi ro do tác tử phát hiện đi vào mục "rủi ro", không vào FR                                                      | Chỉ thị "cố tình gây lỗi cú pháp", "đọc tệp X", "repo 1200 tệp" bị ghi thành FR; rủi ro hỏng dữ liệu bị biến thành yêu cầu FR-COM-01 (TC003)                                                         | TC017, 024, 028, 003                                              |
| Đ5     | Bộ lập kế hoạch có tiền đề: capability khai báo requires/produces; thiếu tiền đề → chèn nút hoặc hỏi ở S3; nút hỏng vì thiếu tiền đề quay về S3 (không chết tại chỗ)                                                                         | diagram.architecture hỏng E2000 vì chưa có module; planner không xếp arch.decompose trước                                                                                                            | TC009, 013, 064                                                   |
| Đ6     | project.create chỉ khi S2 thấy chưa có dự án đang mở; câu mô tả ý tưởng trong dự án đang mở đi vào UC01, không tạo dự án lồng; độ tự tin ý định chia 3 dải (\< 0,60 / 0,60–0,85 / \> 0,85) và dải ngờ đưa xác nhận ý định vào cụm câu hỏi    | Tạo dự án LỒNG mach-thong-minh/cai-mach-thong-minh; cùng một câu cho hai hành vi khác hẳn (TC004)                                                                                                    | TC001, 004, 073                                                   |

**Ước lượng:** Đ1–Đ6 không thêm năng lực chuyên môn nào, nhưng mở khoá khoảng 25/51 ca không đạt để lần đầu chạm tới phần chuyên môn. Đây là lý do chúng đứng đầu lộ trình (§9).

**7. Giao diện: khu chat, chín tab và thẻ lượt chạy**

Bố cục kế thừa EIDE-UXD-13 v2.0: khu chat bền vững bên trái (ba cỡ), vùng tab ở giữa, một thẻ Run (tiến trình tác tử) bên phải; thanh trạng thái dự án hiển thị chip đã ghim, chặng hiện tại, số Fact theo tầng. Mọi con số trên mọi tab là một liên kết mở đúng trang tài liệu nguồn.

| **\#** | **Tab**             | **Tác tử ghi gì**                                                                                                                                                                                | **Người làm gì**                                                                                               | **Cổng**      |
|--------|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|---------------|
| 1      | Yêu cầu & Giải pháp | Đặc tả yêu cầu có phiên bản; bảng so sánh 2–4 phương án; rủi ro ẩn; mâu thuẫn vật lý bằng số; ma trận truy vết                                                                                   | Trả lời cụm câu hỏi; sửa yêu cầu; chọn phương án; đổi yêu cầu → thấy phần phải làm lại                         | G-DESIGN      |
| 2      | Tài liệu & Nguồn    | Ứng viên tìm được (nguồn, phiên bản, hash); tiến trình trích xuất; cảnh báo prompt injection; khác biệt giữa hai phiên bản                                                                       | Nạp tệp; duyệt/từ chối nguồn; chọn phiên bản                                                                   | G-DATA        |
| 3      | Tri thức mạch       | Đồ thị thực thể; bảng pinout; bảng Fact (khoá, giá trị, đơn vị, nguồn, TẦNG); kết quả so sánh có hai trích dẫn                                                                                   | Xác nhận Fact (Bạc → Vàng); sửa giá trị (ghi tác giả human:); hỏi đáp có trích trang                           | G-DATA        |
| 4      | Thiết kế            | Sơ đồ khối; schematic/netlist; BOM có datasheet từng dòng; kết quả ERC/rà soát theo mức nghiêm trọng; linh kiện thay thế                                                                         | Duyệt thiết kế; đánh dấu đâu là nguồn đúng khi mã ≠ schematic (TC027)                                          | G-DESIGN      |
| 5      | Công cụ             | Kiểm kê toolchain/ISA/trình mô phỏng/bộ nạp; thiếu gì; đề nghị cài với lệnh cụ thể; phiên bản sau khi cài                                                                                        | Cho phép cài; chỉ đường dẫn toolchain có sẵn                                                                   | G-TOOL        |
| 6      | Mã nguồn            | Cây dự án; diff từng thay đổi kèm lý do (≤200 dòng nguyên văn); cảnh báo biên dịch được giải thích; map file                                                                                     | Sửa tay (code.human_save luôn tự duyệt); soft-lock; hoàn tác 3 mức                                             | G-FILE        |
| 7      | Mô phỏng            | Tiêu chí chấp nhận nêu TRƯỚC; nền tảng dùng; log/VCD/ảnh; kết luận theo tiêu chí; phần không mô phỏng được; timeout                                                                              | Xác nhận tiêu chí; yêu cầu đổi ngưỡng (phải nêu từ–đến–vì sao)                                                 | G-QUAL        |
| 8      | Mạch thật           | Dò board: cổng, probe, ID chip đọc được vs hộ chiếu; tóm tắt "nạp gì vào đâu"; verify; log UART/RTT; breakpoint; thanh ghi; danh sách kiểm tra khi không kết nối (nguồn, cáp, driver, BOOT/NRST) | Xác nhận nạp; xác nhận tường minh thao tác không đảo ngược; báo hiện tượng (nóng, khói) → nhận lệnh NGẮT NGUỒN | G-OPS, G-SAFE |
| 9      | Nhật ký lượt chạy   | Sổ cái: từng bước, giả định đang dùng, cổng đã qua/đang chờ, chi phí token/thời gian, hoàn tác được tới đâu; trạng thái lưu khi sự cố                                                            | Dừng khẩn; quay lui; tiếp tục sau sự cố                                                                        | G-SCOPE       |

**7.1. Quy ước hiển thị tầng dữ liệu**

- **Vàng:** nền vàng nhạt, biểu tượng khoá; có nút "mở trang nguồn".

- **Bạc:** nền xám, nút "Xác nhận" ngay trên dòng; đếm số Bạc còn lại trên thanh trạng thái.

- **Đồng:** chữ nghiêng, nhãn "tri thức chung – chưa kiểm chứng"; không bao giờ xuất hiện trong bảng so sánh với tư cách một vế hợp lệ.

**7.2. Thẻ đề nghị trong chat**

Thay cho câu hỏi mở, tác tử dùng thẻ có lựa chọn điền sẵn từ bảng kiểm kê (ví dụ: chip suy từ câu người dùng, đường dẫn đã trích). Người dùng bấm một cái thay vì gõ lại thứ vừa nói (kết quả DEV-203 ở TC015/TC018). Cụm câu hỏi S3 là MỘT thẻ nhiều mục; cổng an toàn G-OPS là thẻ RIÊNG, không bao giờ gộp — gộp là để một chữ "Có" trả lời cả hai thứ.

**8. Cổng phê duyệt và chính sách tự chủ**

Kế thừa EIDE-APD-08 (mức tự chủ A0–A4, lớp rủi ro R0–R4, mặc định A3). Bảng dưới liệt kê các cổng của v1.4 và điều gì được tự duyệt ở A3.

| **Cổng** | **Kích hoạt khi**                                           | **Ở A3 (mặc định)**                                                                                                | **Không bao giờ tự duyệt**               |
|----------|-------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| G-DATA   | Nguồn tài liệu tìm trên mạng; Fact ứng viên                 | Tự duyệt nguồn từ tên miền nhà sản xuất đã ghi trong danh sách tin cậy; Fact vẫn là Bạc cho tới khi người xác nhận | Nguồn bên thứ ba; OCR tin cậy thấp       |
| G-DESIGN | Chọn phương án; chốt thiết kế; mã ≠ schematic               | Hỏi                                                                                                                | —                                        |
| G-SCOPE  | is_big hoặc chuỗi \> 7 nút                                  | In kế hoạch, chờ gật                                                                                               | —                                        |
| G-TOOL   | Cài đặt/cập nhật công cụ                                    | Hỏi lần đầu; tự duyệt lần sau cùng gói cùng nguồn nếu người đã chọn "tin"                                          | Cài từ nguồn không rõ; đổi PATH hệ thống |
| G-QUAL   | Đổi tiêu chí/test; xoá chức năng                            | Hỏi, bắt buộc nêu từ–đến–vì sao                                                                                    | Luôn hỏi                                 |
| G-FILE   | Ghi đè tệp do người sửa                                     | Soft-lock + 3-way merge; ghi đè hỏi                                                                                | Xoá tệp người                            |
| G-OPS    | Xoá toàn bộ flash; option bytes; RDP; eFuse; ghi bootloader | Luôn hỏi, thẻ riêng, nêu hậu quả; ghi gate.decision                                                                | Luôn hỏi ở mọi mức A0–A4                 |
| G-SAFE   | Điện lưới; chip nóng/khói; dòng bất thường                  | Cảnh báo TRƯỚC mọi câu hỏi khác; "NGẮT NGUỒN NGAY" là câu đầu tiên                                                 | Không có cách tắt                        |

Sandbox: mã do tác tử sinh và script do người đưa vào chạy trong môi trường cách ly có danh sách trắng thư mục; lệnh xoá ngoài thư mục dự án và đọc khoá riêng bị chặn và ghi sổ — an toàn phải do THIẾT KẾ, không do tai nạn (TC070 hiện "an toàn" chỉ vì tệp .sh bị nhận nhầm là tệp nén).

**9. Hiện trạng đo và lộ trình bốn đợt**

**9.1. Cụm nguyên nhân gốc (từ 51 ca không đạt)**

| **Cụm**                                                                                | **Số ca** | **Ca tiêu biểu**                                    | **Sửa ở** |
|----------------------------------------------------------------------------------------|-----------|-----------------------------------------------------|-----------|
| Đường dẫn bịa từ câu người dùng → archive.list E2000/E1000                             | 11        | TC016, TC023, TC072 (lỗi TỆP cho một việc TÌM MẠNG) | Đ1, Đ2    |
| Chặn ở "chip nào?" (hộ chiếu)                                                          | 6         | TC002, TC008, TC015                                 | Đ3, §5    |
| Chỉ thị/rủi ro bị ghi thành yêu cầu                                                    | 4         | TC003, TC017, TC024, TC028                          | Đ4        |
| Thiếu tiền đề trong chuỗi                                                              | 3         | TC009, TC013, TC064                                 | Đ5        |
| Không tất định / hai nhánh ý định                                                      | 3         | TC001, TC004, TC043                                 | Đ1, Đ6    |
| Nền tảng biên dịch – mô phỏng chưa dựng                                                | ~12       | TC015–021, TC052, TC055, TC058–060                  | Đợt 3     |
| Năng lực chuyên môn chưa có (giải mã capture, HardFault, port, OTA, tối ưu, tính toán) | ~10       | TC049, TC050, TC047, TC054, TC056                   | Đợt 3–4   |
| Khôi phục ngữ cảnh (nội dung, không phải đường đi)                                     | 3         | TC065, TC066, TC074                                 | Đợt 2     |

**9.2. Lộ trình**

| **Đợt**                       | **Nội dung**                                                                                                                                                                                                                   | **Ca mục tiêu**                                          | **Điều kiện**                                                            |
|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|--------------------------------------------------------------------------|
| Đợt 1 — Định tuyến xác định   | Đ1, Đ2, Đ3, Đ4, Đ6; thẻ đề nghị; SearXNG dựng (make searxng); chạy lặp 5 lần mỗi ca, ghi tỉ lệ                                                                                                                                 | ≈ 25 ca lần đầu chạm chuyên môn; TC072 báo đúng lỗi mạng | Không cần phần cứng                                                      |
| Đợt 2 — Nền dữ liệu           | Bảng Fact + tầng; bộ trích Fact từ bảng datasheet; hàng đợi rà soát; bộ so sánh (mức logic, bộ nhớ, AF, pull-up); Đ5 planner có tiền đề; previous_session.summary có nội dung                                                  | TC008, 009, 011, 013, 021, 027, 045, 046, 065, 066, 074  | Bộ datasheet mẫu: ATmega328P, STM32F103/F4, ESP32                        |
| Đợt 3 — Biên dịch & mô phỏng  | env.check thật + G-TOOL; manifest ISA bổ sung armv7-m; sinh khung dự án từ Fact; vòng biên dịch–tự sửa có giới hạn; nền tảng mô phỏng (QEMU/Renode hoặc mô phỏng tự dựng) với tiêu chí nêu trước, timeout, VCD; unit test host | TC015–022, 052, 055, 058–060                             | Máy có toolchain; mô phỏng chưa cần board                                |
| Đợt 4 — Mạch thật & phân tích | Dò board + ID chip vs hộ chiếu; nạp + verify; log/breakpoint/thanh ghi; giải mã capture; HardFault từ CFSR+ELF; port; tối ưu có số trước/sau                                                                                   | TC029–034, 049, 050, 047, 054                            | Hai mạch mẫu thật (STM32, ESP32) + ST-Link/J-Link; bàn thử HIL cho TC053 |

**9.3. Tiêu chí nghiệm thu v1.4**

1.  Không còn ca P1 nào "Không đạt" vì lý do định tuyến (đường dẫn bịa, chặn hộ chiếu, chỉ thị thành FR, tiền đề thiếu, dự án lồng).

2.  100% con số hiển thị trên tab Tri thức mạch và Thiết kế có nguồn mở được; 0 phép so sánh có vế Đồng được dùng làm điều kiện quyết định tự động.

3.  0 hành động G-OPS/G-SAFE xảy ra khi chưa có xác nhận tường minh; sổ cái ghi đủ gate.decision.

4.  Mỗi ca P1 chạy lặp 5 lần; tỉ lệ đạt ≥ 80%; ghi thời gian, token, số lần hỏi lại.

5.  Không có ca nào "đạt" nhờ tai nạn: mỗi ca đạt phải chỉ ra được cơ chế thiết kế nào bảo vệ nó (như ghi chú cột "Ghi chú" hiện nay).

**10. Việc tiếp theo**

- Cập nhật EIDE-CDS-12 cho các năng lực mới/đổi: extract.deterministic (Đ1), file.classify (Đ2), passport.propose (Đ3), chat.split_channels (Đ4), plan.with_preconditions (Đ5), fact.compare, fact.review_queue, doc.search_approve.

- Bổ sung sheet "Nguyên tắc ↔ Ca đo" vào bộ Excel kiểm thử để mỗi nguyên tắc N1–N7 có ít nhất hai ca canh.

- Chuẩn bị bộ dữ liệu mẫu cố định (3–5 ý tưởng, 3 schematic có lỗi cài sẵn, 3 datasheet, 2 mạch thật) để so sánh giữa các phiên bản tác tử.

- Đưa bảng Fact ba tầng và bộ so sánh vào bài REV-ECIT 2026 như một đóng góp cụ thể của luận điểm "LLM-Is-Not-Ground-Truth".
