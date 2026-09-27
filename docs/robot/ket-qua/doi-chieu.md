# Đối chiếu sơ đồ sinh ra với tài liệu bàn giao

- Sơ đồ: `du-lieu/robot-canbang/sch/mach.net`
- Tài liệu: `docs/robot/MOBILUCK_Robot2Banh_BanGiaoPhanCung_v1.1.docx`
- Kết quả: **14/14** net khớp

Một net được coi là KHỚP khi: có trong sơ đồ, chạm đúng chân vi điều khiển mà tài liệu ghi, và có từ hai đầu trở lên (một net một đầu là một net hở).

| Chân | Cổng | Net theo tài liệu | Đầu nối trong sơ đồ | Trích dẫn | Khớp |
|---|---|---|---|---|---|
| D0 | PD0 | JQ6500_TX | JQ6500.TX, U1.D0 | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 2 | ✅ |
| D1 | PD1 | JQ6500_RX | JQ6500.RX, U1.D1 | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 3 | ✅ |
| D2 | PD2 | SRF04_ECHO | SRF04.ECHO, U1.D2 | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 4 | ✅ |
| D3 | PD3 | SRF04_TRIG | SRF04.TRIG, U1.D3 | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 5 | ✅ |
| D4 | PD4 | DIR1 | U1.D4, U2.DIR | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 6 | ✅ |
| D5 | PD5 | STEP1 | U1.D5, U2.STEP | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 7 | ✅ |
| D6 | PD6 | DIR2 | U1.D6, U3.DIR | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 8 | ✅ |
| D7 | PD7 | STEP2 | U1.D7, U3.STEP | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 9 | ✅ |
| D10 | PB2 | BUZZER | BUZZER.IN, U1.D10 | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 12 | ✅ |
| D11 | PB3 | WS2812 DIN | U1.D11, WS2812.DIN | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 13 | ✅ |
| D12 | PB4 | BUTTON | BUTTON.OUT, U1.D12 | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 14 | ✅ |
| A0 | PC0 | ADC_BAT | R_DIVIDER.ADC_OUT, U1.A0 | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 16 | ✅ |
| A4 | PC4 | SDA | U1.A4, U4.SDA | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 20 | ✅ |
| A5 | PC5 | SCL | U1.A5, U4.SCL | 4. Bản đồ chân > 4.2 Bảng chân đầy đủ > Bảng 13, dòng 21 | ✅ |
