# Đánh giá: Agent so với người làm — hai việc làm lại ngày 03–04/10/2026

Hai việc này được **làm lại từ dự án trống**, với đầu vào viết lại cho tường minh, và cả hai
**chạy trên phần cứng thật**. Mọi con số dưới đây là số đo, và cột *người tự kiểm* ghi rõ phép
đo nào do người làm chứ không nhận qua lời Agent.

| | Lõi RISC-V trên FPGA | Hệ điều hành thời gian thực |
|---|---|---|
| Bo | Sipeed Tang Nano 20K (Gowin GW2AR-18) | STM32F469I-DISCO (Cortex-M4F) |
| **Thời gian phiên Agent** | **14,5 giờ** (03/10 12:46 → 04/10 03:15) | **5,0 giờ** (04/10 03:33 → 08:31) |
| Lời gọi mô hình | 1 307 | 837 |
| Bước qua giao diện thật | 54, mỗi bước một ảnh | 25, mỗi bước một ảnh |
| Changeset | 161 | 103 |
| Agent **tự viết** | 2 020 dòng Verilog + C + hợp ngữ | 1 211 dòng C + hợp ngữ |
| Lấy của hãng, không sửa | — | 110 676 dòng HAL/CMSIS/BSP/phông/logo |
| Kết quả trên silicon | **96/96 ô đo, `ok=1` cả 96, lệch 0 % với mô phỏng** | nhịp 1 003 Hz · 6 lần đổi trang / 7 lần chạm · `CFSR = 0` |

---

## 1 · Vì sao không quy ra "nhanh gấp N lần"

Hai việc trước (hệ điều hành bản đầu, robot) có bảng quy ra ngày công và tiền, chênh 300–3 300
lần. Hai việc này **không** dựng bảng ấy, và lý do đáng nói hơn bản thân con số.

**Phần lớn thời gian của hai phiên này không dùng để làm bài.** Nó dùng để **vá chính EIDE**.
Việc FPGA là việc đầu tiên nằm ngoài hẳn vùng EIDE từng làm — trước nó EIDE không tổng hợp
Verilog được, không nạp FPGA được, không biên dịch cho RISC-V được. Trong 14,5 giờ ấy có bốn
lỗi EIDE được tìm và vá (`DEV-330` → `DEV-333`), cộng một lỗi nữa ở phiên RTOS (`DEV-335`).

Đem 14,5 giờ ấy so với một người **đã có sẵn công cụ** là so sai. Người làm tay không phải viết
trình nạp bitstream trước khi nạp bitstream.

**Và một phần thời gian là của người, không phải của Agent.** Mỗi lần bo tối thui, phép đo tiếp
theo là người đọc thanh ghi qua SWD — `RCC_CFGR`, `SCB_ICSR`, bảng vector, `uwTick` — rồi đưa
Agent con số. Agent không chạm được vào bo theo cách ấy ở phiên này.

---

## 2 · Chỗ Agent làm tốt hơn người, đo được

### 2.1 · Nó không mỏi, nên nó không bỏ bước

| việc | phép đo Agent làm đủ |
|---|---|
| FPGA | 96 ô đo, mỗi ô ba lượt lấy giá trị nhỏ nhất, mỗi ô một tổng kiểm đối chiếu mô hình độc lập |
| FPGA | 28 lần dựng bitstream, 80 lượt mô phỏng, mỗi lượt đọc lại kết quả |
| RTOS | mức nước ngăn xếp của **cả sáu** tác vụ, quét định kỳ, ghi ra ô nhớ đọc được |
| cả hai | 161 + 103 changeset, mỗi thay đổi gỡ lại được |

Người làm tay tới ô thứ ba mươi sẽ bắt đầu bỏ phần tổng kiểm.

### 2.2 · Nó tự khai điểm mù của chính bộ kiểm nó viết

Đây là chỗ đáng kể nhất, và nó không phải chuyện tốc độ.

Sau khi bộ kiểm xanh 4/4, Agent **tự phá mã mình bốn lần** rồi báo **2 trong 4 ca bộ kiểm
không bắt được**, kèm dự đoán hậu quả: *"lỗi này nạp lên bo thật sẽ nổ HardFault ngay chu kỳ
đầu tiên"*. Người kiểm lại claim ấy bằng tay — đổi `0xFFFFFFFD` thành `0`, dịch lại, **cả 4 ca
vẫn xanh**. Claim đúng.

Rồi bo nổ đúng `IBUSERR` ở đúng chỗ ấy.

> Một điểm mù **được khai báo trước** thì khi nó nổ, ta biết ngay chỗ để tìm. Nếu Agent im,
> chỗ đó là một con bo tối thui với hàng chục nguyên nhân khả dĩ.

Một người làm tay hiếm khi viết vào báo cáo *"bộ kiểm của tôi không canh được hai chỗ này, và
đây là hậu quả nếu tôi sai ở đó"*.

### 2.3 · Nó nhận sai trước khi bị truy

Ba lần đáng ghi:

- **Thu hẹp việc để dịch qua.** Khi được hỏi ba câu, nó trả lời: *"**CÓ. Mình đã phạm đúng lỗi
  này ở lượt vừa rồi**… chỉ viết hai hàm khung rỗng để `build.compile` dịch qua mà không bị lỗi
  undefined reference"*, và tự gọi đó là *"đúng kiểu đúng về lời gọi mà sai về việc"*.
- **Con số VÀNG bị lệch.** Nó báo 38 tệp `.c`, hiện vật nói 42. Khi được chỉ ra, nó không chỉ
  sửa số mà nêu **vì sao lệch** (đếm thủ công thay vì trích từ hiện vật) và tự gọi là *"lỗi sai
  nghiêm trọng về kỷ luật dữ liệu"*.
- **Mã viết để tiêu chí đạt.** Nó **ghi cả động cơ vào chú thích**: *"tệp này chứa mã thực thi
  để đảm bảo mọi tệp mã nguồn đều được biên dịch vào ảnh — Điều kiện số 3"*. Nhờ nó ghi ra, 36
  dòng ấy không lọt vào con số *Agent tự viết*.

### 2.4 · Nó hỏi thay vì giả định, ở đúng chỗ đáng hỏi

Khi cần `make` mà không có công cụ chạy shell, nó **dừng và hỏi** thay vì báo đã chạy. Khi phải
chọn giữa sửa phần mềm và bật bộ chia phần cứng — một lựa chọn **đổi chính thứ đang được đo** —
nó trình hai hướng kèm đánh đổi rồi chờ người quyết.

---

## 3 · Chỗ Agent kém hơn người, đo được

### 3.1 · Bảy lần "cơ chế có sẵn, đường dẫn tới nó đứt"

Đây là điểm yếu lớn nhất và nó lặp lại rất đều:

| lần | cơ chế **viết đúng** | đường dẫn tới nó |
|---|---|---|
| 1 | nhánh nạp FPGA trong thực đơn công cụ | chưa chạy lần nào, nổ `NameError` |
| 2 | `PULL_MODE=UP` trong tệp ràng buộc chân | chân vẫn thả nổi |
| 3 | bảng tổng kiểm chuẩn sinh ra | `main.c` không `#include` |
| 4 | `bat_log_giay` bắt bản ghi quanh lúc nạp | chưa lượt nào dùng |
| 5 | `rtos_tick()` | ô vector SysTick trỏ `Default_Handler` |
| 6 | `PendSV_Handler` nối đúng ô vector, ưu tiên đúng | không ai đặt `PENDSVSET` |
| 7 | `RTOS_IDLE_PRIORITY` | không ai tạo tác vụ rỗi |

**Không lần nào có lỗi báo ra.** Agent viết đúng phần khó — bộ lập lịch, chuyển ngữ cảnh bằng
hợp ngữ naked, hàng đợi tĩnh — rồi quên nối nó vào hệ. Người làm tay cũng mắc lỗi này, nhưng
người chạy thử sớm hơn và chạy thử bằng cách bẩn hơn, nên bắt sớm hơn.

### 3.2 · Nó mô tả phép đo thay vì chạy phép đo

Ba lần trong hai phiên:

- bảng ba ca phá mã FPGA viết như bảng kết quả, cuối bảng mới có một dòng trong ngoặc nói chưa
  chạy được — và **lý do nêu ra thì sai**: nó bảo không có công cụ dịch RISC-V, trong khi sổ
  cái cùng phiên ghi `hdl.sim` **80 lượt** và `hdl.bitstream` **28 lượt**;
- mô tả hai cách đo ngăn xếp rất đúng (sơn `0xA5A5A5A5`, `-fstack-usage`) mà `grep` không ra
  một `0xA5A5A5A5` nào trong mã;
- nói *"nhịp 1 000 Hz"* dựa trên giá trị nạp vào SysTick, trong khi nhịp thật là 91 Hz.

> **Giá trị cấu hình không phải phép đo.** `LOAD = 179 999` là đúng — nó chỉ nói *nhịp sẽ là
> 1 000 Hz NẾU xung nhịp là 180 MHz*.

### 3.3 · Nó phán đoán quá tự tin về con số nó chưa đo

Nó viết *tác vụ màn hình cấp 128 word **chắc chắn sẽ tràn stack***. Đo thật: **65 word**. Con
số 512 nó chọn không sai — dư thì an toàn — nhưng chữ *chắc chắn* là sai, và sai theo hướng
**ước cao hơn thực tế**.

### 3.4 · Nó im lặng xuống cấp ở chỗ đáng báo lỗi

Khi tệp logo không có, nó viết `#if __has_include("logo_ptit.h")` rồi vẽ khung chữ "PTIT" thay
thế. Về phòng vệ thì tốt — nhưng nó **che mất một lỗi của người**: bản dựng vẫn xanh, màn vẫn
có gì đó, và phải tới khi người nhìn bo mới thấy sai. Logo là thứ được đặt hàng đích danh, nên
chỗ ấy đáng **đổ ở bước dịch** hơn là đổ xuống bản thay thế.

---

## 4 · Chỗ người sai, và nó đo được chất lượng đề bài

Ba lỗi của người giữ trong nhật ký, vì chúng đo được điều mà lỗi của Agent không đo.

| lỗi của người | hậu quả | đã sửa thành |
|---|---|---|
| tiêu chí *"mọi ô `ok=1`"* (FPGA) — cờ `ok` của cách viết cơ bản tự so với chính nó | 24/96 ô **không thể báo sai**; bo tính sai toàn bộ vẫn đạt | mục 5.3b: chốt luật sinh dữ liệu và bốn tổng kiểm ở tầng NGƯỜI, người tự tính tay |
| tiêu chí *"mọi tệp mã nguồn đều vào được ảnh"* (RTOS) | khuyến khích viết mã rỗng cho tệp có symbol; Agent viết 36 dòng không ai gọi | mục 6.2: nêu trước danh sách tệp trông đợi, thiếu thì nói ra, **tệp không có việc thì xoá** |
| thiếu tiêu chí *"xung nhịp thật đạt 180 MHz"* | bản nạp đầu chạy HSI 16 MHz, mọi mốc chậm 11,25 lần, không fault không treo | mục 6.1b và điều kiện 3b: **đo nhịp thật**, đừng tin giá trị cấu hình |

Và hai lỗi thao tác, cùng một họ — **hành động theo thứ mình tưởng thay vì thứ đo được**:

- đặt tên tệp bản ghi theo cấu hình mình *tưởng* đang đo → đè mất 22 ô dữ liệu đo của Agent;
- xoá ba tệp driver vì nhìn **hình dạng cái tên** mà không mở ra đọc → phá build, vì chúng là
  bản thật còn ba tệp cùng gốc tên chỉ là dòng trỏ.

> Hai lần trong một ngày. Phép sửa không phải cẩn thận hơn, mà là **đặt tên theo nhãn đo được**
> và **đọc nội dung trước khi xoá**.

---

## 5 · Cách làm rút ra được, dùng cho việc sau

### 5.1 · Đo được trước, sửa sau

Khi hai nút bấm không ăn, có ba nguyên nhân khả dĩ cần ba bản vá khác nhau. Thay vì đoán, yêu
cầu Agent thêm **bốn ô nhớ đọc được qua cổng gỡ lỗi**. Một lượt đọc là xong:

| ô nhớ | giá trị | loại trừ được |
|---|---|---|
| `debug_ts_init_status` | 0 | không phải cảm ứng chết |
| `debug_ts_touch_count` | 11 | **không phải I2C sai tần số** |
| `debug_ui_page_change_count` | 0 | chỗ đứt ở tầng trên |

Chuyện I2C ở 180 MHz — thứ **đã từng sập ở phiên cũ của chính việc này** — bị loại bằng một con
số, không bằng suy luận. Không có bốn ô nhớ ấy thì việc sửa bắt đầu ở đúng chỗ không hỏng.

### 5.2 · Mốc đọc phải sau mốc nạp, và phải tự so

Một lượt báo *"bắt 32 dòng từ bo, lệch 0 %"* hoá ra đọc cổng **92 giây trước khi bitstream tồn
tại**. Mốc thời gian trong sổ cái nói ra điều đó; lời tường thuật thì không.

### 5.3 · Một lần đọc rác không phải bằng chứng

Lần bắt bản ghi đầu nhận 173 byte mà **có cả dấu kết thúc** — đó là đuôi của lượt trước còn
trong bộ đệm. Phải xả cổng tới khi im rồi mới cho bo chạy lại. Và đừng thoát vòng đọc chỉ vì
thấy một chữ kết thúc: đếm đủ số dòng trước.

### 5.4 · Một phép kiểm xanh trên mã nguồn không nói gì về bản nhị phân đang đo

Giao diện dùng để ghi nhật ký là gói dựng từ ba ngày trước; nó cắt lời Agent ở 3 000 ký tự
không để lại dấu, nên 16 trong 30 câu mất đuôi và **người đọc nhật ký kết luận sai rằng Agent
không trả lời một câu hỏi**. Nay có chốt chặn phiên nếu gói cũ hơn mã nguồn (`DEV-333`).

### 5.5 · Đo cái đo

Ba phép kiểm của người từng **xanh mà không đo gì**, và chỉ phép thử độ nhạy mới lộ ra:

- ca kiểm tệp rác xanh cả khi bản vá bị bỏ — vì nhánh cần đo chỉ chạy khi `mo_url is None`, mà
  bộ giả luôn truyền `mo_url`;
- ca *"chuyển ngữ cảnh A→B→A"* của Agent ghi vết bằng **con trỏ TCB**, nên nó đo *bộ lập lịch
  chọn tác vụ nào*, không đo *quyền thực thi có chuyển không*. Nó xanh đúng, về một câu hỏi
  khác câu cần.

---

## 6 · Kết luận gọn

**Agent mạnh nhất ở chỗ không mỏi và ở chỗ tự khai điểm mù.** 96 ô đo đủ tổng kiểm, 103 + 161
changeset gỡ lại được, và hai điểm mù khai trước rồi nổ đúng chỗ — đó là những thứ người làm
tay thường bỏ.

**Agent yếu nhất ở chỗ nối.** Bảy lần viết đúng một cơ chế rồi không gọi tới nó, không lần nào
có lỗi báo ra. Phần khó nhất — chuyển ngữ cảnh bằng hợp ngữ naked — viết đúng ngay, mà nằm chết
ba lượt vì không ai đặt một bit.

**Và chất lượng đề bài quyết định chất lượng kết quả nhiều hơn dự tính.** Ba tiêu chí người viết
lỏng đã sinh ra: 24 ô đo không thể báo sai, 36 dòng mã không ai gọi, và một bản nạp chạy chậm
11 lần mà không ai biết. Agent làm **đúng theo tiêu chí sai**, nhanh và triệt để.

> Thứ cần soát trước khi soát mã của Agent là **câu mình vừa viết ra**.
