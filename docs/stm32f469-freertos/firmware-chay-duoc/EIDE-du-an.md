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
