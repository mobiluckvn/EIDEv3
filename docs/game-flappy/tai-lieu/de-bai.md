# Đề bài — game Flappy Bird trên kit STM32F469I-DISCO

Người giao: Vũ Trí Công (chủ sản phẩm). Ngày: 11/10/2026.

## Muốn gì

Một game Flappy Bird đơn giản chạy trên màn hình LCD của kit STM32F469I-DISCO.

## Yêu cầu về cách làm, không chỉ về kết quả

1. **Phân tích và thiết kế đầy đủ trước khi viết mã.** Không nhảy thẳng vào code.
2. **Thiết kế màn hình phải render ra được** trên tab Màn hình, đúng độ phân giải thật của
   panel, và đủ chi tiết để tôi mở ra chỉnh sửa được từng phần tử.
3. **Viết một nhân RTOS** để chạy game — không dùng FreeRTOS có sẵn, tự viết nhân.

## Điều kiện

- Chữ trên màn hình viết **không dấu**: bảng font của BSP chỉ có ASCII.
- Cấu hình màn hình phải đọc từ tài liệu của bo, không tự đặt.
