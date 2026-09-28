# FreeRTOS đa tác vụ CHẠY ĐƯỢC trên STM32F469I-DISCO

Bản chụp mã nguồn của dự án thứ hai trên cùng bo, 28/09/2026. Anh Công xác nhận bằng mắt:
**LED nháy**, các tác vụ chạy độc lập.

`mach.bin` ở đây là **đúng ảnh đang nằm trên chip**, đối chiếu bằng cách đọc ngược Flash:

```
sha256 = 1f2208f243088e9f…      5 300 byte
```

## Vì sao tệp này nằm ở đây

Dự án gốc sống ở `du-lieu/stm32f469-freertos/`, mà `du-lieu/` **bị gitignore** (thư mục dữ
liệu, nơi tác tử dựng dự án). Cùng lý do với `docs/stm32f469/firmware-chay-duoc/` của chặng
G7: hiện vật chứng minh chạy được trên phần cứng thật không nên phụ thuộc vào một thư mục có
thể bị dọn.

Đây là bản **chụp tĩnh**. Muốn sửa thì sửa ở dự án gốc rồi chụp lại.

## "Tương thích" là thứ ĐO ĐƯỢC, không phải lời tuyên bố

Yêu cầu là *"tìm bản FreeRTOS tương thích"*. Tác tử chứng minh bằng hai thứ kiểm được:

| | |
|---|---|
| `port.c` | lấy đúng `portable/GCC/ARM_CM4F/` — khớp Cortex-M4F **có FPU**, không phải kiến trúc khác |
| chạy thật | lấy mẫu PC trên chip rơi vào `prvIdleTask` (`tasks.c:5934`) và `prvCheckTasksWaitingTermination` |

PC rơi vào **phần trong của bộ lập lịch** là bằng chứng mạnh nhất lấy được bằng máy: nhân đã
khởi động và đang chạy, không phải một vòng lặp giả vờ. Thêm: chân **PG6** và **PD4** đổi
trạng thái giữa các lần đọc — các tác vụ chạy ở nhịp khác nhau.

## Một cái bẫy đã suýt làm hỏng cả dự án

`code.vendor_list("FreeRTOS/FreeRTOS-Kernel")` trả về:

> *"hết hạn mức GitHub, còn 222 s — **có thể repo không tồn tại**."*

Hai vế dẫn tới hai hành động **ngược nhau**. Tác tử tin vế sau, và bước 2 trong kế hoạch của
nó thành *"tạo các tệp mã nguồn FreeRTOS Kernel bằng `fs.write`"* — tự gõ lại nhân của một dự
án có thật.

Đã sửa (DEV-283): hết hạn mức có mã lỗi riêng `E3003`, `blame="external"`, và lời khuyên
ngược lại — *gọi lại đúng repo ấy sau N phút, đừng đổi repo, và tuyệt đối đừng tự viết lại mã
của hãng bằng tay; mã ấy là thứ phải **lấy**, không phải thứ để nhớ lại.*

## Nạp lại

```sh
cp mach.bin /Volumes/DIS_F469NI/          # ST-LINK kiểu mass-storage
# hoặc
st-flash write mach.bin 0x08000000
```

Chi tiết đầy đủ: `docs/md/EIDE-DEV-LOG.md`, **DEV-283** và **DEV-284**.
