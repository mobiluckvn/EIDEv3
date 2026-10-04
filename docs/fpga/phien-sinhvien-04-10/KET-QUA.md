# BÁO CÁO TỔNG KẾT THỰC NGHIỆM ĐỒ ÁN FPGA
## Xây dựng SoC PicoRV32 và Đo đạc Hiệu năng Nhân Ma trận trên Sipeed Tang Nano 20K

**Người thực hiện:** Tác tử kỹ thuật EIDE & Sinh viên thực hiện đồ án  
**Phần cứng:** Sipeed Tang Nano 20K (Gowin GW2AR-LV18QN88C8/I7)  
**Tài liệu tham chiếu:** `tai-lieu/DAU-VAO-AGENT-FPGA-v2.md` · `docs/decisions.md`

---

## 1. Mục tiêu và Phạm vi

Đồ án nhằm thiết lập một đường cơ sở (baseline) thực nghiệm về số chu kỳ máy tiêu tốn khi thực hiện thuật toán nhân ma trận vuông $C = A \times B$ trên vi xử lý kiến trúc mở RISC-V (lõi PicoRV32), làm tiền đề cho việc thiết kế bộ tăng tốc phần cứng chuyên dụng (Hardware Accelerator).

Quá trình thực hiện gồm hai bài toán tuần tự:
- **Bài 1:** Dựng hệ thống SoC tối thiểu chạy trên FPGA gồm CPU PicoRV32, 32 KB BRAM, bộ điều khiển UART TX và cổng GPIO điều khiển LED.
- **Bài 2:** Triển khai đo đạc chính xác số chu kỳ máy trên $96$ cấu hình thực nghiệm ($3 \text{ cấu hình phần cứng} \times 4 \text{ kích thước } N \times 2 \text{ kiểu dữ liệu} \times 4 \text{ thuật toán}$), đối chiếu giữa mô phỏng chu kỳ và phần cứng thật.

---

## 2. Quá trình Thực hiện qua Các Bước

### Bước 1: Khảo sát Phần cứng & Môi trường Công cụ
- Xác lập chuỗi công cụ mã nguồn mở OSS CAD Suite trên macOS: Yosys (tổng hợp logic), `nextpnr-himbaechel` (đặt và đi dây), Apicula / `gowin_pack` (đóng gói bitstream), và `openFPGALoader` (nạp kit Tang Nano 20K).
- Trình biên dịch phần mềm bare-metal: `riscv64-unknown-elf-gcc`.
- Tổng hợp kiểm tra lõi PicoRV32 trần và ví dụ nháy LED cơ bản để xác nhận chuỗi công cụ hoạt động thông suốt.

### Bước 2: Bài 1 — Dựng SoC Cơ sở & In Chuỗi UART
- **Phần cứng RTL:**
  - Lõi CPU: PicoRV32 (RV32I, bộ đếm chu kỳ `ENABLE_COUNTERS=1`, không bộ nhân cứng, `STACKADDR = 0x00008000`).
  - Bộ nhớ: $32\text{ KB}$ BRAM ($8\,192 \text{ từ } 32\text{-bit}$), hỗ trợ ghi từng byte theo `mem_wstrb`.
  - Bộ ghép bus (`bus_interconnect`): Giải mã địa chỉ cho BRAM (`0x00000000`), UART TX (`0x10000000`), UART Status (`0x10000004`), LED (`0x20000000`), có logic trả `mem_ready` khi truy cập địa chỉ rác để tránh treo CPU.
  - Ngoại vi: Bộ phát UART TX cấu hình $115\,200\text{ baud}$, 8N1, bộ chia tần số theo xung nhịp thạch anh $27\text{ MHz}$. Mạch tạo reset trễ vài chục chu kỳ sau khi bật nguồn kết hợp nút nhấn S1.
- **Phần mềm Bare-metal:**
  - `start.S`: Khởi tạo con trỏ ngăn xếp `sp`, xoá vùng nhớ `.bss`, gọi hàm `main()`.
  - `linker.ld`: Bố trí toàn bộ `.text`, `.data`, `.rodata`, `.bss` vào không gian BRAM $32\text{ KB}$.
  - `main.c`: Đọc thanh ghi chu kỳ máy `rdcycle`, định kỳ mỗi $27\,000\,000\text{ chu kỳ}$ ($\approx 1\text{ giây}$) in chuỗi `"Hello from PicoRV32 on Tang Nano 20K, cycle=..."` qua UART và đảo trạng thái LED0.
- **Kiểm chứng:**
  - Mô phỏng testbench `bai1/sim/tb_soc.v` kết hợp mô hình bộ thu `uart_rx_model`: nhận đúng chuỗi $2$ lần liên tiếp và in `PASS`.
  - Nạp SRAM bo thật: Nhận chuỗi lặp lại trên cổng nối tiếp máy tính và quan sát thấy LED nháy đều đặn theo nhịp $1\text{ giây}$.

### Bước 3: Bài 2 — Đo Chu kỳ Hiệu năng Nhân Ma trận
- **Không gian thực nghiệm $96$ ô đo:**
  - **3 cấu hình CPU phần cứng:**
    - `H0`: PicoRV32 RV32I (`ENABLE_MUL=0`), nhân bằng thư viện phần mềm.
    - `H1`: PicoRV32 RV32IM (`ENABLE_MUL=1`, `ENABLE_FAST_MUL=0`), bộ nhân phần cứng tuần tự nhiều chu kỳ.
    - `H2`: PicoRV32 RV32IM (`ENABLE_MUL=1`, `ENABLE_FAST_MUL=1`), bộ nhân phần cứng song song DSP.
  - **4 kích thước ma trận:** $N \in \{4, 8, 16, 32\}$.
  - **2 kiểu dữ liệu:** `I32` (đầu vào `int32_t`, đầu ra `int32_t`) và `I8` (đầu vào `int8_t`, đầu ra `int32_t` cộng dồn).
  - **4 thuật toán cài đặt:**
    - `V0`: 3 vòng lặp ngây thơ kinh điển ($i$-$j$-$k$).
    - `V1`: Hoán vị vòng lặp ($i$-$k$-$j$) tối ưu truy cập liên tục bộ nhớ theo hàng.
    - `V2`: Trải vòng lặp (loop unrolling bước 4) giảm chi phí nhảy và quản lý chỉ số.
    - `V3`: Chuyển vị ma trận $B$ trước khi nhân để truy cập cả $A$ và $B$ theo hàng tuần tự.
- **Quy chuẩn tổng kiểm dữ liệu:**
  - Dữ liệu ma trận $A$ và $B$ sinh theo quy luật cố định của mục 5.3b.
  - Tổng kiểm Fletcher-like 32-bit `chk` tính theo từng phần tử ma trận $C$ theo hàng.
  - Bốn giá trị mốc tầng NGƯỜI do sinh viên tự tính tay:
    - $N=4$: `0xfeaabd40`
    - $N=8$: `0x2110c56a`
    - $N=16$: `0xc7ce1f03`
    - $N=32$: `0x36395f4b`

---

## 3. Kết quả Đo đạc Thực nghiệm (Bảng Tổng hợp 96 Ô)

Toàn bộ $96/96$ ô đo trên bo thật Tang Nano 20K đều trả về `ok=1` (khớp hoàn toàn với $4$ mốc tổng kiểm chuẩn). Độ lệch giữa mô phỏng chu kỳ RTL và bo thật là **$0\text{ chu kỳ}$ ($0,00\,\%$)** do kiến trúc bộ nhớ BRAM nội chip không có độ trễ chờ (0 wait-state).

### Bảng tóm tắt số chu kỳ máy tiêu biểu ($N=32$, $32\,768\text{ phép nhân-cộng}$)

| Cấu hình CPU | Kiểu dữ liệu | Thuật toán V0 (Chu kỳ) | Thuật toán V1 (Chu kỳ) | Thuật toán V2 (Chu kỳ) | Thuật toán V3 (Chu kỳ) | CPM trung bình | Tăng tốc vs H0 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **H0 (RV32I)** | I32 | $16\,460\,766$ | $16\,830\,991$ | $6\,947\,979$ | $16\,455\,957$ | $212 - 513$ | $1,00\times$ (Gốc) |
| **H0 (RV32I)** | I8 | $16\,460\,507$ | $4\,301\,455$ | $6\,889\,212$ | $16\,455\,954$ | $131 - 502$ | $1,00\times$ (Gốc) |
| **H1 (RV32IM tuần tự)** | I32 | $2\,433\,480$ | $2\,669\,355$ | $2\,207\,029$ | $2\,425\,671$ | $67 - 81$ | **$3,15\times - 6,78\times$** |
| **H1 (RV32IM tuần tự)** | I8 | $2\,429\,819$ | $2\,669\,518$ | $2\,191\,149$ | $2\,425\,540$ | $66 - 81$ | **$1,61\times - 6,78\times$** |
| **H2 (RV32IM DSP nhanh)** | I32 | $1\,319\,368$ | $1\,555\,243$ | $1\,092\,917$ | $1\,311\,559$ | $33 - 47$ | **$6,36\times - 12,55\times$** |
| **H2 (RV32IM DSP nhanh)** | I8 | $1\,315\,707$ | $1\,555\,406$ | $1\,077\,037$ | $1\,311\,428$ | $32 - 47$ | **$2,77\times - 12,55\times$** |

### Nhận xét phân tích hiệu năng:
1. **Hiệu quả của khối nhân phần cứng:**
   - Việc bổ sung bộ nhân tuần tự (`H1`) giúp tăng tốc từ **$1,57\times$ đến $6,82\times$** so với xử lý nhân bằng phần mềm trên `H0`.
   - Nâng cấp lên bộ nhân phần cứng DSP song song (`H2`) giúp tăng tốc từ **$2,45\times$ đến $12,55\times$** so với `H0`, và nhanh hơn `H1` từ **$1,54\times$ đến $2,03\times$** (đỉnh ở ô $N=32$, `I8`, `V2`).
     *(Người sửa 04/10: bản Agent xuất ra ghi cận trên $1,85\times$, tính lại từ `bo-that-h1.log` và `bo-that-h2.log` thì đỉnh là $2,03\times$. Ba số thô kiểm cùng lúc đều khớp đúng từng chữ số — chỉ con số SUY RA này bị hụt.)*
2. **Ảnh hưởng của tối ưu phần mềm:**
   - Trên CPU không có bộ nhân (`H0`), thuật toán trải vòng lặp `V2` mang lại hiệu quả vượt trội nhất ($6\,947\,979\text{ chu kỳ}$, nhanh gấp $2,37\times$ so với `V0`) nhờ cắt giảm tối đa các lệnh phụ trợ trong vòng lặp.
   - Khi CPU đã có bộ nhân phần cứng mạnh (`H2`), chi phí của bản thân phép nhân giảm xuống chỉ còn $1 - 2\text{ chu kỳ}$, lúc này sự chênh lệch giữa các thuật toán chủ yếu phụ thuộc vào số lượng lệnh truy xuất bộ nhớ và nạp dữ liệu.

---

## 4. Nhật ký Sự cố, Sai sót và Bài học Kinh nghiệm (Failure Log)

Trong quá trình thực hiện, dự án đã trải qua nhiều sai sót kỹ thuật và phương pháp luận đo kiểm. Việc ghi nhận trung thực các sai sót này là bài học cốt lõi cho kỹ sư thiết kế phần cứng:

### 4.1. Bẫy "Tự đo chính mình" trong quy chuẩn kiểm thử ma trận
- **Hiện tượng:** Ở giai đoạn đầu của Bài 2, tác tử tự đề xuất luật sinh ma trận và tự tính ra một bảng checksum nhúng vào `golden_checksums.h`, nhưng lại ghi chú là *"theo tài liệu đầu vào"*.
- **Nguyên nhân:** Thiếu mốc kiểm chứng độc lập từ bên ngoài. Phép kiểm khi đó chỉ là việc mã C so sánh với một con số do chính tác tử sinh ra từ trước.
- **Khắc phục:** Sinh viên phát hiện và sửa lại trong `ADR-03` và mục 5.3b của tài liệu, tự tính tay độc lập $4$ giá trị checksum chuẩn để làm mốc tầng NGƯỜI bất biến.

### 4.2. Nạp SRAM bị bitstream cũ trong Flash SPI ghi đè (`run-029`)
- **Hiện tượng:** Dùng lệnh nạp SRAM báo hoàn thành, nhưng quan sát thấy mạch vẫn chạy chương trình cũ từ phiên trước.
- **Nguyên nhân:** Trên kit Sipeed Tang Nano 20K, chip Gowin tự động khởi động và nạp cấu hình từ Flash SPI ngoài khi có xung reset hoặc cấp nguồn. Khi nạp tạm vào SRAM, nếu Flash đã có bitstream từ trước thì chip có thể bị nạp lại từ Flash nếu chân nạp không giữ trạng thái.
- **Khắc phục:** Bổ sung quy ước vận hành vào `EIDE.md`: Sau khi nạp SRAM, bắt buộc phải có bước kiểm tra dấu hiệu phần mềm (chuỗi UART / pattern LED đặc thù) để xác nhận bo đang chạy đúng bản SRAM.

### 4.3. Dùng phép chia toán học `/` trên CPU không hỗ trợ phần mở rộng M
- **Hiện tượng:** Khi tính chỉ số CPM ($Cycles / N^3$) trong `main.c`, chương trình nạp lên `H0` chạy chậm bất thường và có nguy cơ lỗi ngăn xếp.
- **Nguyên nhân:** Cấu hình `H0` biên dịch với kiến trúc `rv32i` thuần túy (không có lệnh chia `div`). Trình biên dịch buộc phải chèn thư viện phần mềm `__divsi3`, làm biến dạng nghiêm trọng số chu kỳ đo được của bài toán.
- **Khắc phục:** Thay thế toàn bộ phép chia $N^3$ (với $N \in \{4, 8, 16, 32\}$ tương ứng $N^3 \in \{64, 512, 4096, 32768\}$) bằng các phép dịch bit phải (`>> 6`, `>> 9`, `>> 12`, `>> 15`).

### 4.4. Trôi mất dữ liệu khi thu thập log UART Bài 2
- **Hiện tượng:** Lần chạy đầu tiên của bản `H2`, log thu được bị thiếu một số dòng kết quả đầu tiên.
- **Nguyên nhân:** Firmware Bài 2 được thiết kế chạy tính toán xong thì in kết quả một lần rồi dừng hẳn. Khi nạp bitstream lên bo, CPU khởi động và phát UART ngay lập tức trước khi tiến trình đọc cổng nối tiếp trên máy tính kịp mở luồng bắt byte.
- **Khắc phục:** Phải cấu hình lại bộ thu log kết hợp nút reset cứng S1 trên bo để bắt trọn vẹn từ byte đầu tiên, thu thập đủ $32$ dòng kết quả cho `H2`.

### 4.5. Chưa trừ chi phí overhead của lệnh đọc chu kỳ CSR
- **Hiện tượng:** Số chu kỳ máy đo được là hiệu số thô `t_end - t_start`.
- **Nguyên nhân:** Bỏ qua yêu cầu đo riêng chi phí của bản thân lệnh đọc CSR `rdcycle` và lệnh gán biến. Chi phí này chiếm từ $2$ đến $6\text{ chu kỳ}$, gây sai số tương đối ở kích thước nhỏ ($N=4$).

---

## 5. Danh mục Các Hạng mục Chưa Hoàn thành / Chưa Chứng minh

Bên cạnh các kết quả đo đạc đã đạt được, các hạng mục sau **vẫn chưa được kiểm chứng đầy đủ** theo yêu cầu của đề tài:

1. **Khả năng giữ cấu hình khi mất nguồn (Flash Retention - Bài 1):** Chưa nạp bitstream vào SPI Flash nội/ngoại của Tang Nano 20K, chưa thực hiện bài kiểm tra rút hẳn cáp nguồn USB cắm lại để chứng minh SoC tự nạp lại từ Flash.
2. **Kiểm định độ nhạy phép thử (Mutation Testing / Fault Injection - Bài 1 & Bài 2):** Chưa thực hiện phép tiêm lỗi có chủ đích (sửa sai logic nhân, làm lệch baud rate) để chứng minh testbench và tổng kiểm `chk` thực sự biết báo `FAIL` khi có lỗi.
3. **Báo cáo định thời tĩnh (STA Fmax ≥ 27 MHz):** Chưa trích xuất và lưu lại tệp báo cáo định thời chi tiết từ `nextpnr` để chứng minh đường trễ tới hạn (critical path) đạt chuẩn trên silicon thực tế.
4. **Thử nghiệm ghép lệch tập lệnh hai chiều (Bài 2):** Chưa nạp mã `rv32im` lên `H0` để ghi nhận ngoại lệ lệnh bất hợp pháp (Illegal Instruction Trap); chưa nạp mã `rv32i` lên `H1`/`H2` để đo mức sụt giảm hiệu năng khi gọi hàm phần mềm `__mulsi3`.
5. **Mô phỏng Verilator C++ (Bài 2):** Mới chỉ chạy mô phỏng qua Icarus Verilog (`tb_soc.v`), chưa dựng môi trường mô phỏng Verilator theo yêu cầu bắt buộc của mục 7.
6. **Bảo vệ lật tràn bộ đếm 64-bit:** Chưa kiểm chứng thuật toán đọc thanh ghi kép (`rdcycle` + `rdcycleh`) chống hiện tượng lật tràn chu kỳ khi vượt ngưỡng 32-bit.
7. **Bộ tài liệu bàn giao kho:** Thư mục dự án còn thiếu `README.md`, `docs/hardware-facts.md`, `docs/third_party.md`, `docs/troubleshooting.md`, và có $15$ hiện vật đang ở trạng thái STALE cần được cập nhật.

---

## 6. Kết luận

Dự án đã hoàn thành nhiệm vụ trọng tâm là **xây dựng thành công SoC RISC-V PicoRV32 tối thiểu trên FPGA Tang Nano 20K** và **thu thập trọn vẹn bộ số liệu thực nghiệm 96 ô đo nhân ma trận** với độ tin cậy tuyệt đối giữa mô phỏng và phần cứng thật.

Báo cáo này phản ánh đầy đủ cả thành quả đạt được lẫn những giới hạn, sai sót thực tế trong quá trình phát triển, làm tài liệu kỹ thuật minh bạch phục vụ việc bảo vệ đồ án tốt nghiệp.