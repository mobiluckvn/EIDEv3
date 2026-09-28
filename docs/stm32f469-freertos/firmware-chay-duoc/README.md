# FreeRTOS + màn hình tương tác — CHẠY ĐƯỢC trên STM32F469I-DISCO

Bản chụp lúc anh Công xác nhận: *"Đã chạy hoàn hảo."* — 28/09/2026.

Trên màn: logo PTIT · thông tin đề tài, học viên **Vũ Trí Công**, GVHD **TS. Nguyễn Trung
Hiếu** · nút **“Chi tiết”** chạm được → màn chi tiết → **Close** quay lại. LED nháy song song
suốt thời gian đó, do FreeRTOS lập lịch.

`mach.bin` là đúng ảnh trên chip, đối chiếu bằng đọc ngược Flash:

```
sha256 094546e6afedb70b…      263 344 byte
```

## Đo được trên phần cứng lúc chụp

| phép đo | kết quả |
|---|---|
| chuỗi hiển thị 11 mắt | **thông suốt cả 11** |
| PC lấy mẫu | `prvIdleTask`, `prvCheckTasksWaitingTermination` — nhân FreeRTOS đang chạy |
| khung ảnh trong SDRAM | **687 màu** |
| `RCC_CFGR.SWS` | 2 → SYSCLK từ **PLL**, `PLLN = 360`, Flash 5 wait state |

## Ba lỗi đáng nhớ của chặng này

**1. Tác tử BỊA TÊN NGƯỜI.** Màn từng hiện *"Sinh vien : Nguyen Dinh Cong"* và *"GVHD : Nhom
Nghien Cuu He Thong Nhung"* — cả hai không có thật, trong khi bốn dòng ấy được đưa **nguyên
văn** trong yêu cầu. N1 áp vào **chữ**, và nặng hơn một Fact sai: không ai kiểm một cái tên
bằng máy được.

**2. Chip chạy 16 MHz thay vì 180 MHz.** Màn sáng nhưng **nhấp nháy**. Đo trên silicon:
`RCC_CFGR = 0` → `SWS = 0`, tức SYSCLK vẫn ở HSI 16 MHz; mã bật HSE và đặt `PLLM` bằng tay
nhưng **không chuyển SYSCLK sang PLL**. Mọi thông số nhịp của BSP màn hình tính cho 180 MHz →
`DSI_ISR1` bit 7 (`LPWRE`) bám dai → nhấp nháy. Sửa xong thì mắt thứ 11 tự tắt.

**3. Nút vẽ ở ba toạ độ khác nhau.** Hình chữ nhật thật ở x 154…759 (đo trên khung ảnh), mã
vẽ `FillRect(160, 400, 480, 50)` → x 160…640, còn chữ vẽ `CENTER_MODE` nên căn giữa **cả màn
800 px**. Người nhìn thấy một mảng xanh trôi lệch khỏi dòng chữ của chính nó — anh Công hỏi
*"vùng màu xanh là cái gì?"*.

## `cong-cu-tac-tu-tu-viet/`

Ba công cụ **tác tử tự viết cho chính nó** trong chặng này, mỗi cái kèm bộ kiểm riêng phải
XANH mới được đăng ký: `plan.get` · `fs.copy` · `fs.remove`. Chúng sống ở `.eide/cong-cu/` của
dự án và được nạp lại mỗi lần mở dự án.

Chi tiết: `docs/md/EIDE-DEV-LOG.md`, **DEV-285** và **DEV-286**.
