# avr-bare-metal
tu_khoa: avr, atmega, firmware, thanh ghi, isr, ngắt, timer, watchdog, bare metal
khi_nao: Viết firmware AVR (ATmega/ATtiny) không dùng thư viện Arduino ở tầng thời gian thực.

## Trình tự khởi tạo

1. **Đọc và xoá `MCUSR`, rồi mới tắt watchdog.** Chừng nào `WDRF` còn được đặt, phần cứng
   bật lại watchdog ngay sau khi phần mềm xoá nó — lệnh `wdt_disable()` đứng một mình không
   có tác dụng, và bo khởi động lại vài chục ms một lần.
2. Đặt hướng chân (`DDRx`) trước khi bật ngoại vi nào chạm tới chúng.
3. Khởi tạo UART **sớm**: lỗi ở những bước sau không có cách nào báo ra nếu chưa có kênh.
4. Đặt biến điều khiển về giá trị an toàn **trước** khi cho phép ngắt. Cho phép ngắt khi
   biến chưa xác định làm cơ cấu chấp hành chạy ngay lúc bật nguồn.

## Trong ISR

- Không chia, không số thực, không `delay()`, không `Serial.print()`.
- Biến chia sẻ với ISR: `volatile`, và đọc/ghi nhiều byte phải nguyên tử (cấm ngắt quanh
  khối đọc). Ghi 16 bit trên AVR là hai lệnh — một ngắt xen vào giữa cho ra một giá trị
  chưa từng tồn tại.
- ISR càng ngắn càng tốt: đặt cờ, để tầng dưới làm việc.

## Bộ nhớ

- 2 KB SRAM, không MMU: không `malloc`, không `String`, không đệ quy. Tràn ngăn xếp **không**
  sinh ngoại lệ — nó lặng lẽ ghi đè biến.
- Chuỗi hằng nằm trong RAM trừ khi đánh dấu `PROGMEM`.
- `build.map` cho biết symbol nào chiếm chỗ; đọc nó trước khi nghĩ tới đổi chip.

## Định thời

Tính giá trị thanh ghi từ `F_CPU` và ghi công thức vào chú thích:
`OCR2A = F_CPU/8/50000 - 1 = 39` — người đọc sau sáu tháng cần thấy 39 từ đâu ra.
