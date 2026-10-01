# V1 nhà cung cấp — bản ĐÃ ĐỨNG ĐƯỢC. Gói để test trên phần cứng MỚI

Đóng gói 01/10/2026 từ kho `DAPTIT`, nhánh `nam-ban-thu-ha-dao-dong`.
Nguồn: `firmware/ncc/V1_Balancing_Robot_HC05_JQ6500/`.

Đây là cấu hình **đầu tiên trong cả đề án làm robot tự đứng được không cắm
cáp** (28/08/2026), và được xác nhận đứng vững lại ngày 02/09/2026. Nó là
**mốc đối chứng**: khi nó đứng, ta biết phần cứng, jack động cơ, IMU và
nguồn đều tốt — mọi lỗi sau đó là lỗi phần mềm.

## Có gì trong gói

| | |
|---|---|
| `V1_Balancing_Robot_HC05_JQ6500/` | mã V1, đúng bản đã đứng được |
| `V0_Balancing_Hardware/` | **bài đo `acc_calibration_value`** — chạy TRƯỚC V1 trên phần cứng mới |
| `libraries/` | ba thư viện cần để dựng, không cần gói 266 MB của nhà cung cấp |
| `hex/*.hex` | bản đã biên dịch sẵn (14.208 B flash · 692 B SRAM), nạp được không cần `arduino-cli` |
| `board_blk_v1.json` | bản đồ chân của bo BLKLab, để đối chiếu khi đấu lại dây |
| `README_goc_ncc.md` | hồ sơ đầy đủ: một dòng đã sửa, và chuyện hai jack động cơ |

## ⚠ Việc PHẢI làm đầu tiên trên phần cứng mới: ĐO LẠI `acc_calibration_value`

`V1_...ino:76` đang đặt **92**. Con số đó đo trên **con robot cũ**, không
mang sang bo/IMU khác được — mỗi module IMU lắp một góc khác nhau. Dùng số
cũ trên phần cứng mới thì robot nghiêng đi rồi ngã, và rất dễ bị đổ oan cho
PID.

```bash
make ncc-nap-v0 PORT=/dev/cu.usbserial-XXXX   # rồi đọc ở 9600 baud
```

Kê robot **đứng thẳng, cứng, không cầm tay** rồi reset — V0 chỉ lấy **một
mẫu duy nhất**, nên tư thế lúc reset là tất cả. Đọc dòng `Balance value:`
và thay vào dòng 76 của V1.

## Nạp V1

```bash
make ncc-nap-v1 PORT=/dev/cu.usbserial-XXXX
```

Hoặc nạp thẳng bản `.hex` kèm theo:

```bash
avrdude -c arduino -p m328p -P /dev/cu.usbserial-XXXX -b 57600 \
        -U flash:w:hex/V1_Balancing_Robot_HC05_JQ6500.ino.hex:i
```

Dựng lại từ mã nguồn (cần `arduino-cli`):

```bash
arduino-cli compile --fqbn arduino:avr:nano:cpu=atmega328old \
            --libraries libraries V1_Balancing_Robot_HC05_JQ6500
```

## Bốn cái bẫy đã trả giá bằng nhiều lượt chẩn đoán

1. **Bootloader CŨ ⇒ nạp ở `BAUD=57600`** (`cpu=atmega328old`). Mặc định
   115200 báo `not in sync`, trông y hệt hỏng cổng.
2. **Tháo module JQ6500 khỏi D0/D1.** Nó dùng chung hai chân với cổng USB;
   còn cắm thì vừa không nạp được vừa không nói chuyện được.
3. **Bật CẢ HAI công tắc.** Công tắc mạch điều khiển và công tắc động cơ là
   hai cái riêng. Quên cái thứ hai thì robot vẫn nói chuyện qua cáp nhưng
   bánh không bao giờ quay.
4. **Nghi thức dựng:** đặt robot **NẰM NGANG**, bật nguồn, **đợi LED chuyển
   từ đỏ sang cầu vồng**, RỒI MỚI từ từ dựng lên và thả tay. Hiệu chuẩn con
   quay chạy ngay lúc khởi động — nâng sớm là hỏng phép hiệu chuẩn, và robot
   sẽ lao đi một phía. Đó **không phải** lỗi dấu.

## Nếu robot lao đi rồi ngã về trước

Thử **đổi hai jack động cơ cho nhau TRƯỚC** khi đụng vào bất kỳ tham số nào.
Hai header có quy ước DIR ngược mức nhau (`MOTOR_LEFT_FWD_DIR_HIGH 1` ·
`MOTOR_RIGHT_FWD_DIR_HIGH 0`) vì hai động cơ lắp đối xứng gương; đổi jack
thì **cả hai cùng đảo chiều** ⇒ phản hồi ngược dấu ⇒ bánh đẩy nhanh cú ngã
thay vì đỡ. Đúng một ngày 28/08 mất vào chuyện này.

## Và đo pin bằng đồng hồ trước khi tin số nào

Trên con robot cũ, đường đo pin **đứt dần trong buổi** 02/09: `PIN` từ
503–515 ổn định xuống 0 trên 100 % của 854 mẫu. Firmware thấy `PIN` dưới
ngưỡng thì **ngắt động cơ** (đúng thiết kế), nên "robot vật vã rồi ngã" có
thể chỉ là bị cắt nguồn giữa chừng. Trên phần cứng mới, đo ba điểm một phút:
hai đầu pin (2S đầy ≈ 8,4 V) · sau công tắc mạch điều khiển · chân A0 so với
GND (phải ≈ điện áp pin / 3,55).
