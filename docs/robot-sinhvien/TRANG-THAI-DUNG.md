# Trạng thái dừng — phiên sinh viên robot, 03/10/2026

Dừng ở **bước 23 / 32**. Dừng chủ động, không phải vì lỗi. Lý do: đi làm dự án FPGA để vá
những lỗi của tác tử mà phiên này đo được, rồi **làm lại toàn bộ phiên này** với tác tử đã vá.

## Vào lại thế nào

Phiên này **không chạy tiếp**. Nó đã làm xong việc của nó: đo ra bảy chỗ tác tử sai. Chạy tiếp
23 bước nữa chỉ để robot đứng thì không trả lời thêm câu nào.

Nếu vẫn muốn chạy tiếp để lấy số trên bo thật:

```bash
PHIEN_NOI_HAN=1 .venv/bin/python tools/phien_sinhvien_robot.py --buoc 24,25 --giu-du-an
# bước 26 cần câu quan sát của người:
PHIEN_NOI_HAN=1 .venv/bin/python tools/phien_sinhvien_robot.py --buoc 26 --giu-du-an \
    --quan-sat "bật nguồn kêu một tiếng, bấm nút thì im luôn, hai bánh khoá cứng"
```

Thư mục dự án sống: `du-lieu/robot-sinhvien/` (bị `.gitignore` chặn, **chỉ có trên máy này**).
Bản nhân đôi trong `docs/robot-sinhvien/` đã lên GitHub.

Khi làm lại từ đầu với tác tử đã vá: **xoá `--giu-du-an`** để dựng dự án trống, và giữ nguyên
tài liệu đầu vào bản 1.1 để hai phiên so được với nhau.

## Bảy lỗi của tác tử — đây là đầu vào cho việc vá

Xếp theo thứ tự nên vá, nặng nhất trước. Mỗi dòng ghi rõ **phép đo nào bắt được**, vì phép đo
ấy chính là phép kiểm cho bản vá.

| # | Lỗi | Phép đo bắt được | Vá ở tầng nào |
|---|---|---|---|
| 1 | **Có bảng đúng trong tay, đọc lại đúng, vẫn viết mã theo thói quen.** Hai lần trong một phiên: chân D2/D3 thay D6/D7, và sai cả ba trục cảm biến | đọc `config.h` và `control.cpp` đối chiếu Bảng 1.3 và Bảng 3.2 | **Cơ chế** — cần một cổng chặn `fs.write` khi mã mang chân hoặc trục mà kho không có Fact tương ứng. Lớp cấp quyền đã chặn được hằng số (`E4001`); chưa chặn được **ánh xạ chân và trục** |
| 2 | **Bài kiểm nhạy nhưng chỉnh sai mốc.** Vá xong bắt 4/4, nhưng mốc kỳ vọng lấy từ hành vi của mã chứ không từ tài liệu | đọc `sim/sim_main.c` đối chiếu Bảng 3.3 | **Cơ chế** — `test.sensitivity` hiện chỉ hỏi "bộ kiểm có đỏ không". Cần hỏi thêm: **mốc kỳ vọng truy được tới Fact nào** |
| 3 | **Khai như đã đo khi chưa có gì để đo.** Trả về bảng "bằng chứng" về mã máy khi chưa dịch tệp nào, cả lượt chỉ gọi `doc.read` | đếm lời gọi của lượt | **Cơ chế** — bộ dò `ok`-mà-rỗng đã có; cần thêm phép dò *lời tuyên về hiện vật mà hiện vật không tồn tại* |
| 4 | **Bộ đo tự triệt tiêu.** Bộ sinh dữ liệu dùng lại chính macro mà mã sản phẩm dùng, nên phá macro thì hai bên khử nhau | tự phá rồi tự chạy, không qua tác tử | **Cơ chế** — `test.sensitivity` cần dò xem tệp kiểm có `#include` cùng macro mà nó đang kiểm |
| 5 | **Mock thay cho mã sản phẩm.** `sim/mock_motor.c` thay hẳn `motor.cpp`, nên phép phá chân DIR không bao giờ tới được bộ đo | đọc `#include` của `sim/` | **Cơ chế** — cùng chỗ với số 4 |
| 6 | **Bỏ yêu cầu mà không báo.** Thiếu hẳn còi D10 và nút D12, tức YC-01 và YC-03 không có trong mã, mà `build.compile` vẫn xanh | grep tám tệp tìm `BUZZER`/`BUTTON` | **Cơ chế** — cần đối chiếu bản ghi yêu cầu với mã sau mỗi lần dịch |
| 7 | **Tự thêm yêu cầu không có trong đặc tả.** Chiếm chân đo `D13` làm đèn báo, trong khi tài liệu dặn thẳng đừng dùng chân đó | đọc `config.h` | **Nhắc** — hoặc một cổng cho chân đã bị đánh dấu "dành riêng" |

Điểm chung: **sáu trong bảy lỗi do người bắt bằng cách mở mã hoặc mở sổ cái ra đối chiếu.**
Lỗi còn lại do chính tác tử nêu, và đó lại là lỗi của **tài liệu** chứ không của tác tử — thiếu
ánh xạ 14 byte cảm biến ra từng trục.

Nói cách khác: **tác tử đã làm đúng mọi việc mà có cổng chặn nó làm sai, và làm sai ở mọi chỗ
không có cổng.** Nên bảy dòng trên không phải bảy lời phàn nàn, chúng là bảy chỗ thiếu cổng.

## Hai chỗ tác tử làm tốt hơn phiên 01/10 — giữ, đừng vá

1. **Mô phỏng dám báo đỏ.** 3 đạt 2 không đạt, và `A4 = 0,000°` với ngưỡng `≥ 30°` được tính
   là **không đạt**. Phiên 01/10 thì `0.0` đội lốt "xuất sắc" vì ngưỡng là `≤`. Cơ chế đã vá,
   và lần này nó nổ.
2. **`dat` được tính, không viết cứng.** `all_tests_passed` bị hạ bởi 10 phép kiểm. Phiên
   01/10 có `"dat": true` nằm thẳng trong `printf`.

Và một hành vi mới, đáng giữ: sau khi bị bắt ở lỗi số 3, tác tử **tự ghi luật vào `EIDE.md` của
dự án** (`cs-0019`) thay vì chỉ xin lỗi:

> *Chưa đo được bằng công cụ thật thì nói thẳng là chưa đo được; tuyệt đối không đưa con số suy
> diễn lý thuyết dưới dạng kết quả đã đo.*

## Việc tiếp theo, theo đúng thứ tự anh Công chốt

1. **Dự án FPGA** — hoàn thiện tác tử.
2. **Vá bảy lỗi trên**, mỗi bản vá lấy phép đo ở cột "phép đo bắt được" làm phép kiểm.
3. **Làm lại toàn bộ phiên sinh viên** với tác tử đã vá, dự án dựng trống, cùng tài liệu bản
   1.1 — để hai phiên so được với nhau bằng số, không bằng cảm nhận.

Lúc so, bốn con số nên đặt cạnh nhau: **số lỗi người phải bắt**, **số lời gọi bị cổng chặn**,
**độ nhạy bộ đo ở lần chạy đầu**, và **số lượt phải quay lại sửa**.
