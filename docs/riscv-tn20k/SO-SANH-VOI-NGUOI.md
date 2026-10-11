# So với người làm tay — lõi RISC-V trên FPGA Tang Nano 20K

Dựng bằng `tools/uoc_luong_pert.py`, cùng phương pháp đã dùng cho robot 04/10. Script **tự
kiểm**: nó tính lại bảng robot và so với con số đã in trong
[`../robot-sinhvien/phien-sinhvien-04-10/SO-SANH-VOI-NGUOI.md`](../robot-sinhvien/phien-sinhvien-04-10/SO-SANH-VOI-NGUOI.md);
lệch một chữ số là nó kêu. Nên ba bảng dùng **chung một thước**, so được với nhau.

```
python tools/uoc_luong_pert.py riscv
```

---

## 1 · Phiên Agent — số đo được

| | |
|---|---|
| Thời gian | **khoảng 14 giờ, trải hai ngày** (02–03/10/2026) |
| Lượt mô hình | **1 307** |
| Lượt chạy có ghi chi phí | 100 |
| Agent tự viết | **2 020 dòng** — Verilog, C, hợp ngữ, linker script, Python, ràng buộc chân |

### Token và tiền

Cách tách y như lần trước: token **vào mới** là phần tăng thêm so với lượt trước, phần trùng là
**đọc lại từ đệm**. Kho không lưu bảng giá, nên tiền trình bày thành ba kịch bản đơn giá.

| | token |
|---|---|
| vào mới | **5,33 M** |
| đọc lại từ đệm | **31,83 M** (85,7 % token vào) |
| ra (kể cả phần suy nghĩ) | **0,37 M** |

| Kịch bản (USD / triệu token) | Vào mới | Đệm | Ra | **Tiền cả phiên** |
|---|---|---|---|---|
| A — thấp | 0,075 | 0,019 | 0,30 | ≈ 1,12 USD · **28 nghìn đồng** |
| **B — giữa** | 0,15 | 0,0375 | 0,60 | ≈ 2,22 USD · **55 nghìn đồng** |
| C — cao | 0,30 | 0,075 | 2,50 | ≈ 4,92 USD · **122 nghìn đồng** |

*(tỉ giá 24 818 đ/USD, suy từ chính cặp số đã in ở tài liệu robot: 1,37 USD ↔ 34 nghìn đồng)*

---

## 2 · Nếu một đội người làm tay — ước lượng PERT

Đủ bốn khâu: phân tích, thiết kế, viết mã, kiểm thử. Mỗi dòng ba mức, lấy theo
`(nhanh + 4 × thường + chậm) / 6`.

Phạm vi lấy theo **những gì đã làm xong**, ghi trong thư mục này và README §7.3: lõi RV32I
tuần tự ba cấu hình bộ nhân, chuỗi công cụ, phần mềm nhúng, bốn cách cài đặt nhân ma trận, bộ
thu 96 ô, mô phỏng Verilator, và bảng tổng kiểm tính tay ở tầng NGƯỜI.

| Việc | Vai | Nhanh | Thường | Chậm | **Ngày công** |
|---|---|---|---|---|---|
| Đọc tài liệu kit Tang Nano 20K / GW2AR-18, bảng chân, mức điện | Senior | 1 | 2 | 4 | **2,17** |
| **Dựng chuỗi công cụ: Yosys + nextpnr + openFPGALoader + riscv32-gcc, chạy thông tới bitstream** | Senior | 1 | 3 | **8** | **3,50** |
| Thiết kế vi kiến trúc lõi RV32I tuần tự: giải mã, khối thanh ghi, bus BRAM | Senior | 2 | 4 | 8 | **4,33** |
| **Viết RTL lõi RV32I + bộ nhớ + UART phát** | Senior | 3 | 6 | **12** | **6,50** |
| Ba cấu hình bộ nhân: không nhân · tuần tự · DSP | Senior | 1 | 3 | 6 | **3,17** |
| Ràng buộc chân `.cst`, mạch reset, cây xung nhịp | Mid | 0,5 | 1 | 3 | **1,25** |
| Bài 1: nạp bitstream, LED chạy trên bo thật | Mid | 0,5 | 1 | 3 | **1,25** |
| Phần mềm nhúng: startup hợp ngữ, linker script, Makefile ba cấu hình | Mid | 1 | 2 | 5 | **2,33** |
| Bốn cách cài đặt nhân ma trận × hai kiểu dữ liệu | Mid | 1 | 3 | 6 | **3,17** |
| Bộ đếm chu kỳ, giao thức bản tin UART, tổng kiểm | Mid | 1 | 2 | 4 | **2,17** |
| Mô phỏng Verilator: testbench, chạy khớp RTL | Senior | 1 | 3 | 6 | **3,17** |
| Bộ thu 96 ô qua cổng nối tiếp bằng Python, gộp bảng | Mid | 1 | 2 | 4 | **2,17** |
| Bảng bốn tổng kiểm tính tay ở tầng NGƯỜI, chốt trước khi đo | Senior | 0,5 | 1 | 2 | **1,08** |
| Chạy đủ 96 ô trên bo, đối chiếu bo ↔ mô phỏng | QA | 1 | 3 | 6 | **3,17** |
| **Gỡ lỗi tới khi 96/96 ô đạt** | Senior | 2 | 5 | **12** | **5,67** |
| Tài liệu, báo cáo, bảng kết quả | Mid | 1 | 2 | 4 | **2,17** |
| **TỔNG** | | **18,5** | **43** | **93** | **47,2 ngày công** |

Độ lệch chuẩn PERT **±3,5 ngày**:

| Mức tin | Khoảng |
|---|---|
| ~68 % | **44 – 51 ngày công** |
| ~95 % | **40 – 54 ngày công** |

Đây là việc **lớn nhất** trong bốn việc — lớn hơn bài robot 15 ngày công, và lý do nằm ở ba
dòng mà ba việc kia không có:

* **Viết RTL lõi RV32I** (3 → 12), dòng nặng nhất bảng. Không phải viết phần mềm: sai một chỗ
  trong giải mã lệnh thì triệu chứng hiện ra ở một lệnh khác, vài nghìn chu kỳ sau.
* **Dựng chuỗi công cụ** (1 → 8). Yosys, nextpnr, openFPGALoader, `riscv32-unknown-elf-gcc` —
  bốn công cụ phải khớp nhau tới tận định dạng bitstream của đúng con FPGA ấy.
* **Gỡ lỗi tới khi 96/96 ô đạt** (2 → 12). Không phải "chạy được", mà là **96 ô cùng đạt**, và
  mỗi ô phải khớp giữa bo thật và mô phỏng.

### Cần mấy người, bao lâu

| Vai | Ngày công | Phần |
|---|---|---|
| Kỹ sư **FPGA/RTL Senior** | **29,6** | 63 % |
| Kỹ sư nhúng **Mid** | 14,5 | 31 % |
| **QA** | 3,2 | 7 % |
| Quản lý dự án (20 % thời lượng) | 9,5 | — |

Đội ít nhất: **1 Senior RTL + 1 Mid nhúng + QA một phần + quản lý 20 %**. Lịch khoảng **6
tuần**, và **29,6 ngày công của Senior là chỗ không chia việc được**: phải có vi kiến trúc rồi
mới viết RTL, có RTL rồi mới có bitstream, có bitstream rồi mới gỡ lỗi trên bo. Tỉ lệ Senior ở
đây **cao nhất trong bốn việc** (63 %) — đó là đặc điểm của việc thiết kế phần cứng số.

### Tiền nhân sự

Cùng bảng lương với lần trước *(lương tháng, triệu đồng; chia 21 ngày làm việc, nhân 1,4 cho
bảo hiểm, chỗ ngồi, thiết bị)*. Lưu ý: bảng này dùng mức **kỹ sư nhúng** cho vai Senior, trong
khi một kỹ sư **FPGA/RTL** trên thị trường thường đắt hơn — nên con số dưới đây là **cận dưới**.

| Kịch bản | Tiền phát triển | Kèm quản lý |
|---|---|---|
| Thấp | 101,4 triệu | **≈ 123 triệu** |
| **Giữa** | **138,8 triệu** | **≈ 170 triệu** |
| Cao | 177,2 triệu | **≈ 218 triệu** |

---

## 3 · Hai cột cạnh nhau

| | Đội người (ước lượng PERT) | Phiên Agent (đo được) |
|---|---|---|
| Thời gian | **47,2 ngày công ±3,5** · ~6 tuần lịch | **≈ 14 giờ**, hai ngày |
| Giờ người | **378 giờ** (47,2 × 8) | **≈ 14 giờ** |
| Tiền | **≈ 170 triệu đồng** | **≈ 55 nghìn đồng** |
| Kết quả đo được | — | **96/96 ô** trên bo, lệch 0 % so với mô phỏng |

Chênh **≈ 27 lần về giờ** và **≈ 3 100 lần về tiền**.

---

## 4 · Bốn điều bảng trên KHÔNG chứng minh

**Một — ba mức của mỗi dòng là PHÁN ĐOÁN, không phải số đo.** Không có bộ dữ liệu lịch sử của
đội nào ở đây. Con số ra là một **thang so sánh giữa các việc dùng chung một thước**, không
phải một lời hứa về chi phí.

**Hai — độ lệch chuẩn HẸP hơn thực tế.** Công thức cộng phương sai, tức giả định các dòng trượt
**độc lập**. Ở một dự án RTL thì giả định ấy đặc biệt yếu: một hiểu lầm về giao thức bộ nhớ
BRAM làm trượt cùng lúc dòng viết RTL, dòng mô phỏng và dòng gỡ lỗi trên bo.

**Ba — 14 giờ của Agent KHÔNG so được trực tiếp với 378 giờ của người.** README §7.3 đã nói:
đây là việc **đầu tiên nằm ngoài hẳn vùng EIDE từng làm** — trước nó EIDE không có một dòng nào
về HDL — nên phần lớn hai ngày ấy là **vá chính EIDE** (bốn lỗi, `DEV-330` đến `DEV-333`),
không phải làm bài. Cột người chỉ tính phần làm bài. Chênh thật **có lợi cho Agent hơn** con số
in ở trên, nhưng tôi không dựng một con số "đã hiệu chỉnh", vì tách giờ nào cho việc nào trong
một phiên đan xen là một phép chia tôi không đo được.

**Bốn — tỉ lệ chênh về tiền KHÔNG phải tỉ lệ về giá trị.** 55 nghìn đồng mua được 2 020 dòng đã
chạy đúng trên silicon, nhưng nó **không** mua được người biết đọc lại chúng. Sáu lỗi của Agent
trong phiên ấy đều bị bắt bằng cách **mở mã hoặc mở sổ cái ra đối chiếu** — trong đó có một lỗi
mà mô phỏng và bitstream chạy **hai chương trình khác nhau**. Không ai làm việc ấy thì con số
96/96 là một ô xanh rỗng.
