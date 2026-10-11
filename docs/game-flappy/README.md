# Game Flappy Bird trên STM32F469I-DISCO — việc thật số 4

Phiên ngày **11/10/2026**, giao qua **chính giao diện EIDE** (không qua dòng lệnh). Đây là việc
đầu tiên đi hết đường **tài liệu → hồ sơ panel → thiết kế màn hình → HTML xem được → mã C →
ảnh nạp → chạy trên bo**.

Đọc [`NHAT-KY-GIAO-VIEC.md`](NHAT-KY-GIAO-VIEC.md) để xem từng lượt: câu người gõ, Agent gọi
công cụ nào, ghi hiện vật nào. Phần kể lại kèm con số nằm ở §7.4 của README gốc.

## Thư mục này có gì

| | |
|---|---|
| [`tai-lieu/`](tai-lieu/) | đầu vào Agent đọc: đề bài, và tài liệu kiến trúc của bo |
| [`thiet-ke/`](thiet-ke/) | **bộ thiết kế**: 4 bản render HTML (mở bằng trình duyệt, tỉ lệ 1:1 với panel) + 17 hiện vật xuất ra JSON — yêu cầu, ADR, hồ sơ panel, mô hình màn hình, tệp C sinh ra |
| [`firmware/`](firmware/) | mã: nhân RTOS tự viết, game, lớp vẽ động, và ba tệp `ui_*.c` **sinh từ bản thiết kế** |
| `mach.bin` | đúng ảnh đã nạp lên chip (đọc ngược Flash khớp từng byte) |
| [`anh/`](anh/) | ảnh tab Màn hình trong app |

**Không có trong này:** 74 tệp BSP của hãng (HAL, CMSIS, driver LCD/SDRAM/cảm ứng, phông) — ·
chúng đã nằm sẵn ở [`../stm32f469/firmware-chay-duoc/`](../stm32f469/firmware-chay-duoc/) và
[`../../du-lieu/rtos-sinhvien/firmware/`](../../du-lieu/rtos-sinhvien/firmware/), chép lại chỉ
làm repo nặng thêm 4,3 MB. Muốn dựng lại thì chép chúng vào `firmware/bsp/`.

## Đo được trên silicon

| phép đo | kết quả |
|---|---|
| nhịp nhân RTOS | bộ đếm `+2 005` trong 2 s = **1 000 Hz**, đúng thiết kế |
| đọc ngược Flash | **khớp từng byte**, cùng SHA-256 |
| ảnh | `text 37 912 · data 548 · bss 9 284` |
| bảng vector | ô 14 → `PendSV_Handler`, ô 15 → `SysTick_Handler` (kèm bit Thumb) · 0 ngắt bỏ quên |
| logic game | ghi `s_state = 1` qua SWD → 3 s sau tự thành `GAMEOVER` |
| chơi thật | chạm màn hình → vòng `START → PLAY → GAMEOVER → PLAY` đo được qua SWD |

## Mã nào của ai

| | dòng |
|---|---|
| Agent **tự viết** (nhân RTOS, game, khởi tạo, lớp vẽ động) | **1 084** |
| **Sinh từ bản thiết kế** (`screen.codegen` → `BSP_LCD_*`) | **296** |
| Lấy của hãng, không sửa, **không nằm trong thư mục này** | 94 877 |

## Chỗ chưa làm được

* Chưa đo được FPS thật — mọi phép đo đều halt CPU nên làm méo thời gian.
* Tệp C sinh từ thiết kế vẽ **một lần**; phần chuyển động là lớp vẽ do Agent tự viết thêm.
* Chim và cọc vẽ bằng khối `rect`, chưa dùng bitmap.
* Còn một hiện vật màn hình trùng (`game_play` ↔ `choi`).
