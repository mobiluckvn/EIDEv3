# EIDE.md — stm32f469-freertos

Tệp này là bộ nhớ dài hạn của dự án. Cả anh và tác tử đều sửa được. Tác tử đọc nó
mỗi lượt, nên những gì viết ở đây có hiệu lực cho mọi việc về sau.

## Mục tiêu

_(chưa có — tác tử sẽ ghi vào đây khi đặc tả yêu cầu được chốt)_

## Chip & phần cứng

- Bo STM32F469I-DISCO, MCU STM32F469NIH6 (Cortex-M4F, BGA216, Flash 2 MB, RAM 324 KB, SDRAM ngoài tại 0xC0000000; 4 LED PG6/PD4/PD5/PK3 tích cực thấp, nút PA0 tích cực cao; LCD DSI OTM8009A). [run-001]

## Quyết định

_(chưa có ADR nào)_

## Giả định

_(chưa có giả định nào đang dùng)_

## Quy ước

- Ngôn ngữ trao đổi: tiếng Việt. Thuật ngữ kỹ thuật giữ nguyên tiếng Anh, giải thích khi lần đầu xuất hiện.
- Mọi con số dùng để quyết định phải truy vết được tới tài liệu (N1).
- Chuỗi công cụ arm-none-eabi-gcc thiếu newlib (bắt buộc link -nostdlib). Không dùng VCP ST-LINK (/dev/cu.usbmodem1103) để log vì không nối chân USART. Lấy mã nguồn ST từ GitHub do st.com bị chặn mạng. [run-001]

## Đừng

- Không bật khoá đọc (RDP) hay ghi eFuse khi chưa có một snapshot đánh dấu release.

## Người vừa sửa

_(chưa có thay đổi nào của anh chờ tác tử nhắc tới)_

## Sổ cái của dự án này bị đứt đoạn ngày 28/09/2026 — và vì sao nói ra

Kỹ sư chạy kịch bản phiên với `--buoc 20` mà quên `--giu-du-an`, nên thư mục dự án bị xoá
sạch rồi dựng lại. Mã firmware khôi phục được từ bản chụp đã commit
(`docs/stm32f469-freertos/firmware-chay-duoc/`), tệp này khôi phục từ
`docs/stm32f469-freertos/ho-so-tac-tu/EIDE.md`. **Không khôi phục** sổ cái và changesets:
nối một sổ cái cũ vào một sổ cái mới sẽ làm chuỗi băm khớp giả, mà một chuỗi băm khớp giả
còn tệ hơn một chuỗi bị đứt có ghi chú. Lịch sử đầy đủ nằm ở
`docs/stm32f469-freertos/ho-so-tac-tu/`.

Mất hẳn: `test/test_ui.c` mà tác tử tự viết ở lượt trước. Không tiếc — nó đã được đo là
**không chạm** vào mã sản phẩm (xem mục dưới).

## Bộ kiểm phải chạm được mã sản phẩm — đo bằng `test.sensitivity`

Bài học đo được ở dự án này: tác tử viết `test/test_ui.c` đủ sáu ca, đủ tên, đủ ngưỡng, đủ
báo cáo JSON — và **tự định nghĩa lại** `UI_ToggleScreen`/`UI_HandleTouch` ngay trong tệp
test. Phá `firmware/ui.c` thật (đổi toạ độ nút thành `99999`) thì cả sáu ca **vẫn ĐẠT**.

Nguyên nhân gốc không phải tính lười: `firmware/ui.c` `#include "stm32469i_discovery.h"`, nên
nó **không dịch được trên máy chủ**, và tác tử chép logic sang tệp test để có thứ mà chạy.

Quy ước từ nay ở dự án này:

- Phần LOGIC (máy trạng thái màn hình, kiểm toạ độ chạm, tính toán) nằm ở tệp `.c` **không**
  `#include` header của bo. Phần chạm thanh ghi nằm riêng.
- Tệp test **dịch cùng** tệp logic thật, không chép lại nó.
- Sau khi `test.run` xanh, chạy `test.sensitivity`. Nó phá mã sản phẩm rồi xem bộ kiểm có đỏ
  không. Không đỏ ⇒ bộ kiểm chưa đo gì, dù báo cáo có bao nhiêu ô xanh.

## Vòng chạm đã được người xác nhận sau khi tách logic

28/09/2026, sau khi tách `ui_state.c` và cho `ui.c` uỷ quyền: người dùng bấm nút "Chi tiet"
trên bo thật và xác nhận vẫn chạy tốt. Đây là bằng chứng mà máy **không lấy được**: đọc khung
ảnh chỉ nói chương trình đã vẽ, lấy mẫu PC chỉ nói nhân còn chạy — cả hai đều không đi qua
đoạn ngón tay → I2C → `UI_State_CheckTouch` → `UI_State_Toggle` → vẽ lại, mà đó chính là đoạn
vừa bị sửa. Lần sau đụng vào `ui_state.c` thì phải xin người bấm lại, đừng coi ba số đo kia là
đủ.
