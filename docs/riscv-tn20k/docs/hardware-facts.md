# Bảng thông số phần cứng Tang Nano 20K (G0)

| Hạng mục | Giá trị | Link nguồn |
|---|---|---|
| 1. Mã chip, chuỗi device cho nextpnr/gowin_pack và cho Gowin EDA | `GW2AR-LV18QN88C8/I7`, family `GW2A-18C`, package `QFN88` | https://wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html |
| 2. LUT4, flip-flop | 20.736 LUT4, 15.552 Flip-Flop (FF) | https://www.gowinsemi.com/en/support/database/ |
| 3. BSRAM: số khối, dung lượng mỗi khối, tổng KB | 46 khối BSRAM × 18 Kbit = 828 Kbit (~103,5 KB); thêm 180 Kbit Shadow SRAM | https://www.gowinsemi.com/en/support/database/ |
| 4. Số khối DSP / bộ nhân cứng | 48 bộ nhân 18×18 bit (hoặc 96 bộ nhân 9×9 bit) | https://www.gowinsemi.com/en/support/database/ |
| 5. Thạch anh và chân clock | 27 MHz, chân PIN 4 (IOT13A) | https://wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html |
| 6. 6 chân LED, mức tích cực | PIN 15, 16, 17, 18, 19, 20 (LED0 – LED5); tích cực thấp (Active-Low) | https://wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html |
| 7. Chân nút S1, S2 | S1: PIN 88 (User/Reset); S2: PIN 87 (User); tích cực thấp | https://wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html |
| 8. Chân UART TX/RX nối tới chip cầu USB (BL616) | FPGA TX: PIN 69; FPGA RX: PIN 70 (chuẩn 3.3V LVCMOS) | https://wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html |
| 9. Tên cổng serial trên macOS khi cắm kit | BL616 cấp 2 interface USB CDC: thường nhận dạng `/dev/tty.usbmodem*` (đối chiếu cụ thể bằng `ls /dev/tty.*` khi cắm kit) | https://wiki.sipeed.com/hardware/en/tang/tang-nano-20k/nano-20k.html |
| 10. Chân đa chức năng (dual-purpose) cần cấu hình riêng | Chân MSPI (PIN 48, 49, 79, 80) và JTAG; cần bật dual-purpose pin nếu dùng làm user I/O | https://www.gowinsemi.com/en/support/database/ |
| 11. PLL: tần số ra hợp lệ từ 27 MHz | CLKIN 27 MHz (fIN 3–400 MHz), VCO 400–1000 MHz; sinh được 27 MHz, 54 MHz, 81 MHz | https://www.gowinsemi.com/en/support/database/ |
| 12. Dự án mẫu chính thức của Sipeed | Kho mã mẫu chính thức (Blinky, UART, WS2812, PicoRV32) | https://github.com/sipeed/TangNano-20K-example |
