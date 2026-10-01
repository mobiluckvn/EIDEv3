# EIDE.md — robot-tu-can-bang

Tệp này là bộ nhớ dài hạn của dự án. Cả anh và tác tử đều sửa được. Tác tử đọc nó
mỗi lượt, nên những gì viết ở đây có hiệu lực cho mọi việc về sau.

## Mục tiêu

- Xây dựng firmware điều khiển robot 2 bánh tự cân bằng MOBILUCK trên ATmega328P với kiến trúc thời gian thực 3 tầng, hỗ trợ tự hiệu chuẩn, kích hoạt bằng nút nhấn và bảo vệ an toàn khi ngã. [run-002]

## Chip & phần cứng

- Chân EN của 2 driver A4988 nối cứng GND trên bo mạch: phần mềm KHÔNG THỂ tắt tầng công suất; dừng động cơ thực hiện bằng cách ngắt xung STEP (động cơ luôn ở chế độ giữ mô-men khi có nguồn). [run-006]

## Quyết định

_(chưa có ADR nào)_

## Giả định

_(chưa có giả định nào đang dùng)_

## Quy ước

- Ngôn ngữ trao đổi: tiếng Việt. Thuật ngữ kỹ thuật giữ nguyên tiếng Anh, giải thích khi lần đầu xuất hiện.
- Mọi con số dùng để quyết định phải truy vết được tới tài liệu (N1).
- Trước khi sửa bất kỳ tệp firmware nào, bắt buộc mở `tai-lieu/BANG-TRA-TUAN-THU.md` để đối chiếu các mục kỹ thuật liên quan đến vị trí sắp sửa; sửa xong bắt buộc cập nhật lại cột kết luận của những mục ấy. [run-065]
- Sau mỗi lần nạp firmware, bắt buộc mở cổng nối tiếp đọc các dòng log khởi động đầu tiên để đối chiếu với dấu hiệu nhận dạng đặc thù của chương trình vừa nạp; nếu dòng in ra không khớp với bản vừa nạp thì coi như nạp sai dù trình nạp báo verified. [run-106]

## Đừng

- Không bật khoá đọc (RDP) hay ghi eFuse khi chưa có một snapshot đánh dấu release.

## Người vừa sửa

_(chưa có thay đổi nào của anh chờ tác tử nhắc tới)_
