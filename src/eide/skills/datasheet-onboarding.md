# datasheet-onboarding
tu_khoa: datasheet, tài liệu, nạp, trích, fact, pinout, bàn giao
khi_nao: Dự án vừa có tài liệu mới (datasheet, tài liệu bàn giao) và cần đưa dữ kiện vào kho.

## Bốn bước, và đừng nhảy cóc

1. `ingest.file` → biết tệp là gì (theo magic bytes, không theo đuôi tên).
2. `doc.load` → vào kho, có `doc_id`, có hash. Tài liệu nội bộ thì khai `nguon: noi_bo` —
   Fact trích ra sẽ ở tầng NGƯỜI, và mỗi lần dùng phải nói rõ "nguồn nội bộ".
3. **Đọc trước khi trích.** `doc.read` theo mục hoặc từ khoá để biết tài liệu có gì. Trích mà
   chưa đọc là trích những thứ trình trích xuất biết tìm, không phải những thứ tài liệu có.
4. Trích theo loại dữ liệu:
   - số kèm đơn vị → `fact.extract`
   - bảng bản đồ chân → `fact.extract_pinout`
   - hằng số, giá trị thanh ghi, địa chỉ → `fact.from_doc` (chọn đúng đoạn, mã sẽ kiểm giá
     trị có mặt trong đoạn đó)

## Sau khi trích

Trình bảng cho người dùng rà soát. Fact trích tự động ở tầng BẠC; chỉ lên VÀNG khi người xác
nhận **từng dòng**. Đừng gọi `fact.review` thay họ.

Bảng nào tài liệu có mà EIDE không đọc được (ảnh chụp, bảng trong hình) thì nói thẳng là
không đọc được, và hỏi người dùng — đừng điền bằng tri thức chung về chip.
