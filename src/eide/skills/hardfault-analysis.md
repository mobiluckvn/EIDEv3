# hardfault-analysis
tu_khoa: treo, hardfault, reset, watchdog, tràn ngăn xếp, khởi động lại, hang
khi_nao: Firmware treo, khởi động lại liên tục, hoặc nhảy vào trình xử lý lỗi phần cứng.

## Hỏi theo thứ tự rẻ tới đắt

1. **Watchdog có bị bỏ quên không?** Trên AVR: `MCUSR` còn `WDRF` thì bo reset vài chục ms
   một lần — triệu chứng giống hệt "firmware chạy được một lúc rồi chết".
2. **Ngăn xếp có tràn không?** Cộng `.data + .bss` từ `build.map`, so với SRAM; phần còn lại
   là chỗ cho ngăn xếp và biến cục bộ. Mảng cục bộ lớn trong một hàm được gọi từ ISR là
   nguyên nhân phổ biến nhất.
3. **Có truy cập con trỏ rỗng hay mảng vượt biên không?** Trên chip không MMU, cả hai đều
   ghi đè một biến khác thay vì báo lỗi — nên triệu chứng xuất hiện ở rất xa nguyên nhân.
4. **Biến chia sẻ với ISR đã `volatile` và đọc nguyên tử chưa?**
5. **Có vòng chờ cờ nào không bao giờ bật không?** Trong mô phỏng thì đây là ca timeout; trên
   bo thật thì là treo. Tìm `while (!cờ)` và hỏi ai bật cờ đó.

## Cách thu bằng chứng

Bật một chân làm điểm đo và đảo mức ở đầu mỗi ISR — xung đều nghĩa là nhịp còn sống. Ghi
nguyên nhân reset (`MCUSR`) ra UART ngay sau khi xoá nó: nó nói bo vừa chết vì watchdog, vì
brown-out, hay vì ai đó bấm nút reset.
