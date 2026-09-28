# Firmware CHẠY ĐƯỢC trên bo STM32F469I-DISCO

Bản chụp mã nguồn đúng lúc màn hình lên, 28/09/2026. Anh Công xác nhận bằng mắt:
*"Lên rồi bạn ơi. Đẹp quá"* — logo PTIT và bốn dòng thông tin trên màn 800×480.

**`mach.bin` ở đây là đúng ảnh đang nằm trên chip lúc đó**, đối chiếu bằng cách đọc ngược Flash:

```
sha256 = 67cdf4369f68d3dccaa1c12616329d4e…      261 340 byte
```

## Vì sao tệp này nằm ở đây

Dự án gốc sống ở `du-lieu/stm32f469-disco/`, mà `du-lieu/` **bị gitignore** (đó là thư mục dữ
liệu, nơi tác tử dựng dự án mẫu). Tệ hơn: `tools/phien_stm32.py` chạy **không** kèm
`--giu-du-an` sẽ `rmtree` cả thư mục ấy. Nên hiện vật quan trọng nhất của G7 — đoạn mã duy
nhất đã chứng minh chạy được trên phần cứng thật — có thể biến mất vì một lần chạy lại kịch
bản. Bản chụp này để điều đó không xảy ra.

Đây là bản **chụp tĩnh**, không phải nơi sửa mã. Muốn sửa thì sửa ở dự án gốc rồi chụp lại.

## Hai cái bẫy đã tốn 17 lượt gỡ lỗi

Cả hai nằm ở chỗ nối driver OTM8009A (API v2 của ST) với `DSI_IO_WriteCmd` của BSP (API v1),
và cả hai đều **im lặng** — HAL trả `HAL_OK` cho cả 101 lệnh trong khi không lệnh nào tới đích:

| loại gói | bố cục `DSI_IO_WriteCmd` đòi | lỗi đã mắc |
|---|---|---|
| **ngắn** (`Length == 0`) | lệnh + **một byte dữ liệu**, luôn dùng `SHORT_PKT_WRITE_P1` | lớp bọc vứt byte dữ liệu, gửi `0x00` |
| **dài** (`Length > 0`) | `{dữ liệu…, LỆNH}` — lệnh ở phần tử thứ `NbrParams` | lớp bọc dựng `{LỆNH, dữ liệu…}` |

`Length == 0` **không** có nghĩa "không có dữ liệu". Đó là quy ước của driver OTM8009A đời cũ,
không được viết ra ở đâu, và nó đã bị hiểu sai **hai lần** — lần thứ hai ngay sau khi vừa sửa
xong lần thứ nhất, ở một chỗ khác.

Hệ quả: lệnh `0xFF {0x80,0x09,0x01}` — **mở khoá CMD2** — gửi đi thành lệnh `0x01`. Không mở
được CMD2 thì panel bỏ qua toàn bộ cấu hình phía sau, kể cả bơm nguồn nội và điều khiển đèn
nền. Panel vẫn đủ sống để trả lời lệnh đọc ID `0x40`, nhưng tối tuyệt đối.

Chi tiết đầy đủ: `docs/md/EIDE-DEV-LOG.md`, mục **DEV-279**, các lần 1–17.

## Nạp lại

```sh
cp mach.bin /Volumes/DIS_F469NI/          # ST-LINK kiểu mass-storage
# hoặc
st-flash write mach.bin 0x08000000
```

Bo này đã bị **ghi đè bản demo gốc của ST**. Muốn khôi phục thì lấy lại từ
`STMicroelectronics/STM32CubeF4`, thư mục `Projects/STM32469I-Discovery/Demonstrations`.
