# ĐANG LÀM — game Flappy Bird + năng lực thiết kế UI nhúng

> Tệp này trả lời đúng một câu: **mở phiên mới thì làm gì tiếp.**
> Trạng thái chốt **11/10/2026**. `main` sạch, đã push.

## Việc còn treo, theo thứ tự nên làm

### 1. Xác nhận game chơi được — CHƯA AI XÁC NHẬN

Bản nạp cuối (**38 460 byte**, đọc ngược Flash khớp từng byte) có lớp vẽ động dirty-rect. Anh
Công **chưa xác nhận** chim có bay và cọc có chạy không. Trước đó lần lượt đã sửa: màn hình
trống → nút không ăn → nút tô sai màu → màn chơi đứng im.

Mở lại:

```bash
st-info --probe                      # bo còn cắm không
st-flash reset                       # cho chạy lại từ màn start
```

Rồi hỏi anh Công: chim có bay không, cọc có chạy sang trái không, điểm có tăng không.

**Nếu vẫn đứng im** thì đo trước khi đoán — và nhớ `s_state` **đổi địa chỉ mỗi lần dựng lại**:

```bash
A=$(arm-none-eabi-nm du-lieu/game-flappy/.eide/build/mach.elf | grep -E " b s_state$" | awk '{print "0x"$1}')
openocd -f interface/stlink.cfg -c "transport select hla_swd" -f target/stm32f4x.cfg \
  -c init -c halt -c "mdw $A 1" -c resume -c exit
```

Đọc ô cũ là cách tôi suýt báo sai một lần rồi.

### 2. Đo số khung hình mỗi giây — CHƯA ĐO ĐƯỢC

Mọi phép đo qua SWD đều **halt CPU**, nên nó làm méo đúng cái nó đo. Cách đúng: cho firmware
tự đếm (một biến tăng mỗi lần `render_play_frame` chạy), rồi đọc nó **một lần** sau 10 giây.

### 3. `ham_tra_hang` kêu oan 15 callback *weak* của HAL

Trên ảnh game nó báo 17 "hàm rỗng", trong đó có `HAL_DSI_MspInit`,
`HAL_DMA2D_LineEventCallback`… — những hàm **đúng ra phải rỗng** (bản mặc định yếu để người
dùng ghi đè). Kêu chúng lên làm cảnh báo mất nghĩa, đúng cái bẫy đã tránh cho `main` và
`*_Handler`.

**Đã đo trên ảnh thật 11/10/2026**, nên không phải đoán: trong 17 hàm bị kêu,
**15 là `W` (weak)** và 2 là `T`. Hai hàm `T` là `ft6x06_Reset` (rỗng) và `ft6x06_TS_ITStatus`
(trả 0) — **stub của driver hãng**, cũng không phải lỗi của người viết game.

Chỗ sửa: `doc_nm` **đã giữ loại ký hiệu** `T`/`W`, nên lọc *weak* là đường có sẵn —
`isr_bi_bo_quen` đang dùng `syms` rồi, `ham_tra_hang` thì chưa nhận. Lọc weak dọn 15/17. Hai
hàm còn lại nên dọn bằng cửa thứ hai: **bỏ tệp của hãng**, đúng cách `ham_bi_loai` đã bỏ
`vendor/` — `ham_tra_hang` chưa có cửa ấy.

Nhớ dựng tập phá kèm **ca âm**: một hàm `T` rỗng trong mã NGƯỜI VIẾT vẫn phải bị kêu, không
thì phép vá này giết luôn thứ nó sinh ra để bắt (tám hàm `BSP_LCD_*` rỗng của phiên này là
`T`).

### 4. Hiện vật màn hình trùng

`ui_screen:game_play` trùng `ui_screen:choi` — Agent đã gộp nội dung vào `choi` nhưng hiện vật
cũ vẫn trong kho, nên tab Màn hình hiện **bốn** màn cho một game **ba** màn.

## Mở lại phiên giao việc

```bash
# Kênh chỉ bật cho dự án app ĐANG MỞ — đặt trước rồi mới mở app
defaults write vn.mobiluck.eide duAnPath -string \\
  /Users/congvt/Documents/EIDE_v3/du-lieu/game-flappy

python tools/lai_phien_qua_gui.py mo
python tools/lai_phien_qua_gui.py go "câu giao việc"
python tools/lai_phien_qua_gui.py cong gate-00NN ok      # duyệt cửa G-FLASH
```

Nhật ký từng lượt tự ghi vào `du-lieu/game-flappy/NHAT-KY-GIAO-VIEC.md`.

**Lõi là tiến trình Python do app đẻ ra** — sửa mã trong `src/eide/` xong phải **mở lại app**
thì lõi mới nạp bản mới. Đã mất hai lượt vì quên chuyện này.

## Dựng lại firmware

`docs/game-flappy/firmware/` chỉ có mã Agent tự viết + ba tệp `ui_*.c` sinh từ thiết kế.
**74 tệp BSP của hãng không nằm trong git** (chúng đã có sẵn chỗ khác trong repo). Muốn dựng
lại:

```bash
mkdir -p du-lieu/game-flappy/firmware/bsp
cp docs/stm32f469/firmware-chay-duoc/* du-lieu/game-flappy/firmware/bsp/   # trừ main.c, logo_*, mach.bin
cp du-lieu/rtos-sinhvien/firmware/{ft6x06*,stm32469i_discovery_ts.*,stm32f4xx_hal_i2c*} \\
   du-lieu/game-flappy/firmware/bsp/
```

Rồi bật `HAL_I2C_MODULE_ENABLED` trong `bsp/stm32f4xx_hal_conf.h`, và giữ **đúng một** tệp
`.ld` và **đúng một** `startup.c` trong cây nguồn — bộ dịch từ chối khi có hai, và nó từ chối
đúng.

Tham số dịch: `isa=armv7-m`, `fpu=fpv4-sp-d16` *(tra từ bảng `cortex-m4` trong `toolchain.py`,
không nhớ)*.

## Năng lực thiết kế UI — phần chưa làm

* **Chỉ sinh `BSP_LCD_*`**, chưa sinh LVGL. Mô hình màn hình không phụ thuộc đích sinh code
  nên thêm LVGL không phải làm lại mô hình.
* **Chưa có bảng font tiếng Việt.** `E1108` chặn chữ có dấu và khuyên chuỗi không dấu.
* **Màn hình ký tự (HD44780) có hồ sơ mà chưa vẽ được** — `16x2` được nhận đúng là cột × dòng,
  và hồ sơ tự khai là chưa làm cho loại ấy.
* **Tab A15 chưa nằm trong bộ quét 11 tab giao diện** (`docs/review-v3/test/ket-qua-giao-dien/`).

## Việc khác đang treo, không liên quan game

Chiến dịch tối ưu tác tử: **34/106**, **P0 xong 30/30**, P1 chưa mở — xem
[`../../toi-uu/DANG-LAM.md`](../../toi-uu/DANG-LAM.md). Anh Công chưa quyết có mở P1 không.
