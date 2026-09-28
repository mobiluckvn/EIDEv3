# EIDE.md — stm32f469-disco

Tệp này là bộ nhớ dài hạn của dự án. Cả anh và tác tử đều sửa được. Tác tử đọc nó
mỗi lượt, nên những gì viết ở đây có hiệu lực cho mọi việc về sau.

## Mục tiêu

_(chưa có — tác tử sẽ ghi vào đây khi đặc tả yêu cầu được chốt)_

## Chip & phần cứng

- Chip chính: STM32F469NIH6 (ARM Cortex-M4, 2 MB Flash, 324 KB RAM, BGA216) trên bo STM32F469I-Discovery. [run-007]

## Quyết định

_(chưa có ADR nào)_

## Giả định

_(chưa có giả định nào đang dùng)_

## Quy ước

- Ngôn ngữ trao đổi: tiếng Việt. Thuật ngữ kỹ thuật giữ nguyên tiếng Anh, giải thích khi lần đầu xuất hiện.
- Mọi con số dùng để quyết định phải truy vết được tới tài liệu (N1).
- Driver OTM8009A quy ước Length == 0 nghĩa là gói ngắn mang 1 byte dữ liệu (nằm ở pData/pParams[1]), DSI luôn dùng gói P1 (DSI_DCS_SHORT_PKT_WRITE_P1). [run-381]

## Đừng

- Không bật khoá đọc (RDP) hay ghi eFuse khi chưa có một snapshot đánh dấu release.

## Người vừa sửa

_(chưa có thay đổi nào của anh chờ tác tử nhắc tới)_
