# `firmware/ncc` — mã nhà cung cấp, BẢN ĐÃ ĐỨNG ĐƯỢC

> **Đây là cấu hình ĐẦU TIÊN trong cả đề án làm robot tự đứng được mà
> KHÔNG CẮM CÁP.** 28/08/2026. Đừng sửa gì trong thư mục này khi chưa có
> lý do — nó là mốc đối chứng, không phải mã đang phát triển.

Nguồn: `docs/BLKLab_BalancingRobot_Fix29102025/BLKLab_Balancing_Robot_Code/`
(gói 266 MB của nhà cung cấp, để ngoài git). Chép vào đây **chỉ phần mã**
cộng ba thư viện, tổng 748 KB, để dựng lại được mà không cần gói kia.

Đã bỏ: `.apk`, các `.png` hướng dẫn, `flowchart` — vẫn còn trong gói gốc.

## Đúng MỘT dòng bị sửa so với bản gốc

```c
int acc_calibration_value = 92;   // nguyên bản của họ: -2576
```

Số 92 **đo trên chính con robot này**, ngày 28/08/2026, bằng đúng quy trình
hai bước của nhà cung cấp (`V0_Balancing_Hardware.ino:8-12`):

```
Scanning I2C bus...
I2C device found at address 0x68
WHO_AM_I response: 0x72          <- hàng nhái, mã của họ chấp nhận mọi mã
Balance value: 92
```

Robot được **kê cứng đứng thẳng**, không cầm tay — V0 chỉ lấy **một mẫu
duy nhất**, nên tư thế lúc reset là tất cả.

## ⚠ Phần cứng đã phải sửa mới chạy được

Chạy V1 lần đầu với `acc_calibration_value = 92`: **robot chạy loạn.**

Nguyên nhân: **hai jack động cơ cắm hoán đổi cho nhau** so với quy ước mà
firmware giả định.

Hai header có quy ước DIR **ngược mức nhau** (`MOTOR_LEFT_FWD_DIR_HIGH 1` ·
`MOTOR_RIGHT_FWD_DIR_HIGH 0`) vì hai động cơ lắp đối xứng gương. Đổi jack
cho nhau thì mỗi động cơ nhận mức DIR ngược với trước, nên **cả hai cùng
đảo chiều — toàn bộ chiều lái bị lật**. Hai bánh vẫn đồng bộ với nhau, chỉ
là chạy ngược hướng cần thiết. Đó đúng là chữ ký của *thả tay ra là lao đi
và ngã về phía trước*: phản hồi ngược dấu thì bánh đẩy nhanh cú ngã.

Đổi jack lại thì V1 cân bằng ngay và rất tốt.

**Cách cắm ĐÚNG cho V1 là cách hiện tại** — nếu sau này tháo robot ra lắp
lại mà nó lao đi rồi ngã, thử đổi hai jack động cơ cho nhau TRƯỚC khi đụng
vào bất kỳ tham số nào.

Hệ quả với phần còn lại của đề án — **phải đọc kỹ trước khi tin bất kỳ số
nào ghi trước 28/08/2026**:

- **Quy ước dấu của firmware đề án nay ngược với phần cứng.** `DAO_DAU`,
  `DAO_DAU_VONG_NGOAI`, kết luận của `make thu-dau` (26/08) và các hằng số
  hướng trong `board_blk_v1.h` đều thiết lập với cách cắm jack CŨ.
  `build/dau_nghich.hex` (`DAO_DAU=1`) là thứ đáng thử đầu tiên.
- `hw/board_blk_v1.json` **không sai** — bản đồ chân và quy ước DIR ngược
  mức vẫn đúng. Thứ khác đi là *động cơ nào cắm vào header nào*: dữ kiện
  LẮP RÁP, không phải dữ kiện mạch. Đừng sửa bản đồ chân.
- `DIEM_CAN_BANG_DEG = -0,40`, `KI_TOC_Q4 = 512`, `KD_TOC_Q4 = 256`,
  `KD_Q4 = 27` — dò trên cách cắm cũ, phải đo lại.
- **Còn để ngỏ:** nếu chiều lái cũ ngược thì vì sao `tu_dung_len` có cáp
  lại đứng 89 giây với biên độ ±0,97°? Cách đọc hợp lý nhất: firmware đề
  án đúng dấu cho cách cắm CŨ, còn V1 giả định cách cắm KIA — hai bên
  ngược nhau và mỗi bên tự nhất quán. Nếu vậy thì việc nó thất bại khi
  KHÔNG cáp là một vấn đề khác, chưa tìm ra. Chưa có bằng chứng.

## Dựng và nạp

Cần `arduino-cli` và core `arduino:avr`. Bo mạch dùng **bootloader cũ**,
nên FQBN phải là `cpu=atmega328old` (tương đương `BAUD=57600` của
`tools/flash.mjs`).

```bash
make ncc-v0                                  # dựng V0
make ncc-nap-v0 PORT=/dev/cu.usbserial-XXXX  # nạp V0, đọc ở 9600 baud
make ncc-v1
make ncc-nap-v1 PORT=/dev/cu.usbserial-XXXX
```

## Nghi thức chạy V1 — khác hẳn firmware của đề án

Bản của họ **không có** cửa sổ chờ, không bíp báo. Nó chốt mốc khi góc gia
tốc kế đi qua khoảng **±0,5°** trong lúc bạn dựng robot lên
(`V1_Balancing_Robot_HC05_JQ6500.ino:415`). Nên:

1. Đặt robot **NẰM NGANG**.
2. Bật công tắc nguồn.
3. Đợi LED WS2812 chuyển từ **đỏ** sang **cầu vồng**.
4. **Từ từ** dựng robot lên — dựng nhanh thì nó lướt qua cửa sổ ±0,5°.
5. Thả tay.

Họ cũng dặn: **tháo module JQ6500 trước khi nạp** (dùng chung TX/RX với
Arduino), và **không dùng `Serial.print()`** khi JQ6500 đang cắm.
