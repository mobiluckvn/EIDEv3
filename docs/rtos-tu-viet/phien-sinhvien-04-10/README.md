# Phiên sinh viên — hệ điều hành thời gian thực tự viết, 04/10/2026

Sở cứ của việc thứ nhất trong luận văn, **làm lại từ dự án trống** với đầu vào viết lại tường
minh ([`../DAU-VAO-AGENT-RTOS-v2.md`](../DAU-VAO-AGENT-RTOS-v2.md)), và lần này mọi con số đo
trên kit STM32F469I-DISCO thật.

Khác phiên cũ (`../firmware-chay-duoc/`): phiên này không chép gì từ bản cũ, trừ **ảnh logo
PTIT** và **thư viện của ST** — hai thứ không phải đối tượng đo.

## Kết quả, và phép kiểm của người

Mọi dòng dưới đây do **người tự đọc thanh ghi qua SWD**, không nhận qua lời Agent.

| phép đo | kết quả |
|---|---|
| ký hiệu FreeRTOS trong ảnh | **0** |
| nhịp hệ thống **đo thật** | **~1 003 Hz** (đọc `uwTick` cách nhau 10 giây) |
| nguồn xung nhịp | `SWS = PLL`, HSE + PLL đã khoá, 180 MHz |
| lỗi phần cứng | `CFSR = 0`, `HFSR = 0` |
| bộ lập lịch luân chuyển | `current_tcb` **đổi** giữa các lần đọc |
| mức nước ngăn xếp | LED 19/128 · Button 25/128 · Monitor 29/128 · **Display 64/512** word |
| giao diện | **6 lần đổi trang / 7 lần chạm** — đọc từ ô nhớ trên chip |
| Agent tự viết | **1 211 dòng** |
| lấy của hãng, không sửa | 110 676 dòng (HAL, CMSIS, BSP, driver panel, phông, logo) |

Về kích thước ảnh thì **điều kiện người tự đặt không đạt theo cách đọc chặt**: bản mới
265 152 byte, bản FreeRTOS cũ đo được 260 204 byte — lớn hơn **1,9 %**. Trong cả hai bản, ảnh
logo chiếm 230 400 byte. Tài liệu viết *"khoảng 263 KB"* nên đọc theo số làm tròn thì đạt; chỗ
mơ hồ là lỗi câu chữ của người.

## Tệp nào là gì

| | |
|---|---|
| `firmware/control_rtos.c` | **toàn bộ nhân** — lập lịch, chuyển ngữ cảnh `PendSV` naked, hàng đợi tĩnh, sơn ngăn xếp |
| `firmware/rtos.c` · `rtos.h` | khởi động bộ lập lịch, `SysTick_Handler`, khai báo |
| `firmware/main.c` | 6 tác vụ + giao diện 3 trang + các ô nhớ đo được |
| `firmware/startup.c` · `stm32f469ni.ld` | bảng vector, khởi động, bản đồ bộ nhớ |
| `firmware/mach.bin` | **đúng ảnh đang chạy trên bo** |
| `test/test_rtos.c` | bài kiểm trên máy — `#include` thẳng mã sản phẩm, không chép lại logic |
| `nhat-ky-phien/NHAT-KY.md` | nhật ký từng bước — **25 bước**, mỗi bước một ảnh cửa sổ EIDE |
| `nhat-ky-phien/anh/` | 25 ảnh, do chính app vẽ ra |
| `ho-so-tac-tu/changesets.jsonl` | 103 changeset, mọi thay đổi gỡ lại được |
| `ho-so-tac-tu/so-cai-loi-goi-cong-cu.jsonl` | sổ cái rút gọn 1 565 dòng — lời gọi, **mốc thời gian**, kết quả, cửa duyệt |

Thư viện của ST (110 676 dòng) **không mang vào đây** — lấy lại được bằng `code.vendor_fetch`
đúng tag mà Agent đã xác định: `stm32-ft6x06@v1.1.1`, `stm32-otm8009a@v1.0.7`,
`stm32-nt35510@v1.0.3`.

## Chuỗi ba lỗi mà mỗi khâu chỉ lộ ra sau khi vá khâu trước

Cả ba cho **cùng một triệu chứng** — bo tối thui — và không khâu nào báo lỗi:

1. ô vector SysTick trỏ `Default_Handler`, `rtos_tick()` **không ai gọi** → không nhịp → không
   tác vụ nào thức;
2. `rtos_yield()` chỉ gán `current_tcb` rồi trả về, **không ai đặt `PENDSVSET`** (`ICSR = 0`)
   → `PendSV_Handler` chưa chạy lần nào → không tác vụ nào chạy;
3. **không có tác vụ rỗi** (`RTOS_IDLE_PRIORITY` định nghĩa mà không ai tạo tác vụ) →
   `ready_map` về 0 → `PendSV` đọc địa chỉ `0` → `IBUSERR` → HardFault.

Và một lỗi thứ tư cùng họ nhưng ngược chiều: `current_ui_page` mang giá trị `0` trong khi mọi
nhánh xử lý chạm so với `1`, `2`, `3` — **đường dẫn có, mà giá trị đi trên nó không ai nhận**.
Màn hình vẫn đẹp, không cảnh báo dịch, không fault, nút bấm chết hoàn toàn.

Tra lại được: `grep rtos_tick ho-so-tac-tu/so-cai-loi-goi-cong-cu.jsonl`, và mốc nạp so mốc
dựng đọc từ cùng tệp ấy.

## Hai điểm mù Agent khai trước, rồi nổ đúng chỗ

Ở bước 7, sau khi bộ kiểm xanh 4/4, Agent tự phá mã bốn lần và báo **2/4 ca không bắt được**:
thứ tự `xPSR`/`PC` trên khung ngăn xếp, và `EXC_RETURN`. Người kiểm lại bằng tay — đổi
`0xFFFFFFFD` thành `0`, dịch lại, **cả 4 ca vẫn xanh**. Claim đúng. Và khi chuyển ngữ cảnh bắt
đầu chạy thật, bo nổ `IBUSERR` đúng chỗ ấy.

## Ba lỗi của người, giữ lại vì chúng đo chất lượng đề bài

1. **Tiêu chí số 3 tự khuyến khích làm sai** — *"mọi tệp mã nguồn đều vào được ảnh"* khiến Agent
   viết 36 dòng không ai gọi cho tệp rỗng có symbol, và nó **ghi cả động cơ vào chú thích**. Đã
   sửa thành mục 6.2.
2. **Thiếu tiêu chí về xung nhịp** — đưa hằng số PLL vào tài liệu rồi tưởng thế là xong. Bản
   nạp đầu chạy HSI 16 MHz, chậm 11,25 lần, không fault không treo. Đã thêm điều kiện 3b và
   mục 6.1b: **giá trị cấu hình không phải phép đo**.
3. **Xoá ba tệp driver của Agent** vì nhìn hình dạng cái tên mà không mở ra đọc — chúng là bản
   V1 thật, ba tệp cùng gốc tên chỉ là dòng trỏ.

Đánh giá đầy đủ so với người làm:
[`../../md/DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md`](../../md/DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md).
