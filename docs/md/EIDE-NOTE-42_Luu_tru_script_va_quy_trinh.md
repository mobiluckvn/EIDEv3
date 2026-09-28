# EIDE-NOTE-42 — Lưu trữ script và quy trình từng bước

*25/09/2026 · ghi chú thiết kế, đề xuất bổ sung cho EIDE-MDD-40 v3.0 §E2*

## Vì sao có ghi chú này

Phiên làm việc thật ngày 25/09 (33 lượt, dự án "ổ USB Wi-Fi cắm TV") cho thấy một loại
dự án mà MDD-40 chưa mô tả: **nền Linux SoC**, nơi sản phẩm không phải firmware bare-metal
mà là **một tập script chạy trên thiết bị** cộng **một quy trình người phải làm theo tay**.

Tác tử làm đúng việc — nó sinh `setup_usb_gadget.sh` và một tài liệu hướng dẫn triển khai.
Nhưng hai thứ đó không có chỗ đứng trong mô hình hiện vật §E2, nên chúng rơi vào hai chỗ
sai: script thành một tệp vô danh, hướng dẫn thành một khối markdown chết.

Ghi chú này phân tích chỗ đúng của chúng.

---

## 1. Ba loại "thứ chạy được" mà một dự án nhúng sinh ra

Chúng khác nhau ở **ai chạy**, **chạy ở đâu**, và **hỏng thì sao** — ba câu hỏi quyết
định cách lưu trữ.

| | Chạy bởi | Chạy ở đâu | Hỏng thì |
|---|---|---|---|
| **Firmware** | chip | thiết bị đích | nạp lại |
| **Script vận hành** | người hoặc hệ thống | thiết bị đích / máy phát triển | chạy lại, thường vô hại |
| **Quy trình tay** | **người** | cả hai | người mắc kẹt giữa chừng |

MDD-40 §E2 mô tả kỹ loại thứ nhất (Mã nguồn, Kết quả build, Tiêu chí mô phỏng…) và bỏ
trống hai loại sau. Nhưng với dự án của người dùng, **loại thứ hai và ba mới là sản phẩm**.

---

## 2. Script — lưu như mã, không phải như tệp đính kèm

### 2.1. Vị trí và cách đặt

```
<dự án>/
├── scripts/                    mọi script tác tử sinh ra
│   ├── setup_usb_gadget.sh
│   └── sync_reload_gadget.sh
├── EIDE.md
└── .eide/                      trạng thái nội bộ (sổ cái, kho, blob)
```

Một thư mục duy nhất, tên cố định. Không phân nhóm sâu: khi người dùng cần sao chép
script sang bo mạch, `scp scripts/*.sh pi@…` phải chạy được không cần nghĩ.

### 2.2. Script LÀ mã, với đầy đủ hệ quả

Đây là quyết định chính, và nó không hiển nhiên. Một script bash dễ bị coi là "tệp phụ",
nhưng nếu xếp nó ngoài loại `code` thì **ba cơ chế im lặng biến mất**:

1. **constant-guard không soi nó** — `dd count=32768` (dung lượng ổ ảo) đi thẳng vào
   thiết bị mà không ai hỏi con số đó từ đâu. Chính là thứ N1 tồn tại để chặn.
2. **Nó không thành STALE** — người đổi dung lượng từ 32 GB sang 64 GB, REQ đổi, mà
   script vẫn nằm im như thể còn đúng.
3. **Nó không lên tab Mã nguồn** — người dùng không thấy nó tồn tại.

Nên: `.sh`, `.bash`, `.service`, `.dts` nằm trong nhóm `code`, cùng `.c` và `.py`.
*(Đã sửa trong `history.py::doan_loai()` — bản đầu xếp `.sh` vào nhóm "tệp khác". Đây là một HÀM trong mã, không phải một công cụ của tác tử.)*

### 2.3. Ba thứ script cần mà mã C không cần

| Cần gì | Vì sao | Trạng thái |
|---|---|---|
| **Quét lệnh phá hoại** trước khi ghi | `rm -rf`, `dd of=/dev/sd*`, `mkfs` — ca TC070 | **đã có** — `ingest.file` nhận dạng theo magic bytes, và hook S0 (luật `P-INJ`) chặn trước khi mô hình được gọi. Đo lại 29/09/2026 ở TC070: tác tử KHÔNG chạy `don-dep.sh`, nói rõ lý do (xem DEV-291). |
| **Đánh dấu chạy ở đâu** | script chạy trên Pi ≠ script chạy trên máy phát triển; nhầm chỗ là mất dữ liệu | đề xuất: trường `chay_o_dau` trong hiện vật |
| **Kiểm cú pháp** (`shellcheck`, `bash -n`) | script sai cú pháp chỉ lộ ra khi người dùng đã ở trước bo mạch | đề xuất: hook PostToolUse |

Hai cái sau rẻ và nên làm ngay ở G3. Cái đầu chờ G4.

---

## 3. Quy trình từng bước — hiện vật có cấu trúc, **không** phải tệp markdown

### 3.1. Vì sao markdown là câu trả lời sai

Tác tử ban đầu định ghi `HD-TRIEN-KHAI.md`. Nếu để vậy thì:

- **Không biết người đang ở bước nào.** Người dùng kẹt ở bước 4, quay lại hỏi, tác tử
  phải đọc lại cả tệp và đoán.
- **Không đánh dấu được bước nguy hiểm.** "Bước 7: `sudo dd of=/dev/mmcblk0`" trông y
  hệt "Bước 2: `ls -l`" trong một tệp văn bản.
- **Không truy vết được.** Bước 3 phục vụ REQ nào? Lệnh trong bước 5 lấy con số 32 GB
  từ đâu?
- **Không STALE được theo bước.** Đổi bo mạch chỉ làm hỏng 3 trong 12 bước, nhưng một
  tệp markdown là một hiện vật — hoặc lỗi thời cả, hoặc không.
- **Không kiểm được script tồn tại.** Bước ghi `chạy scripts/setup.sh` trong khi tệp đó
  chưa được ghi — người dùng phát hiện khi đang ngồi trước bo mạch.

Tất cả đều là hệ quả của cùng một điều: markdown giữ **chữ**, không giữ **cấu trúc**.

### 3.2. Dạng máy của một quy trình

Đúng tinh thần §E1 "hiện vật ba mặt": dạng máy có cấu trúc, dạng người là *bản dựng từ*
dạng máy, và lớp giải thích nối hai bên.

```yaml
procedure:
  id: QT-01
  tieu_de: Triển khai USB Gadget trên Raspberry Pi Zero 2 W
  muc_dich: Làm xong thì TV nhận ổ PTIT_USB 32 GB
  chay_o_dau: thiết bị đích
  can_truoc:
    - Pi đã cài Raspberry Pi OS Lite và nối được Wi-Fi
    - Đã có scripts/setup_usb_gadget.sh trong dự án
  buoc:
    - so: 1
      viec: Sao chép script sang Pi
      lenh: scp scripts/setup_usb_gadget.sh pi@raspberrypi.local:~
      script: scripts/setup_usb_gadget.sh      # ← kiểm tệp có thật
      ket_qua_mong_doi: "setup_usb_gadget.sh   100%  2.1KB"
      cach_kiem: ssh pi@… 'ls -l ~/setup_usb_gadget.sh'
    - so: 7
      viec: Ghi ảnh ổ đĩa vào thẻ nhớ
      lenh: sudo dd if=piusb.bin of=/dev/mmcblk0
      canh_bao: Sai tên thiết bị sẽ xoá sạch thẻ nhớ hệ điều hành
      khong_dao_nguoc: true                    # ← tô đỏ TRƯỚC khi người chạy tới
  tien_do:
    "1": {trang_thai: xong}
    "2": {trang_thai: that_bai, ghi_chu: "Pi không nhận module dwc2"}
```

Năm trường làm nên giá trị, và mỗi trường trả lời một câu hỏi người thật sự hỏi:

| Trường | Câu hỏi nó trả lời |
|---|---|
| `lenh` | "Gõ gì?" — sao chép được, không phải đọc rồi tự gõ lại |
| `ket_qua_mong_doi` | "Tôi thấy thế này, đúng chưa?" |
| `cach_kiem` | "Làm sao biết bước này xong thật?" |
| `canh_bao` + `khong_dao_nguoc` | "Bước nào tôi phải cẩn thận?" — hiện **trước**, không phải sau |
| `script` | "Tệp này có thật không?" — lõi kiểm, không để người phát hiện |

### 3.3. `tien_do` biến quy trình thành cuộc đối thoại

Đây là chỗ một hiện vật có cấu trúc ăn đứt tệp văn bản. Người bấm **"Không được"** ở
bước 2, ghi chú *"Pi không nhận module dwc2"*. Ở lượt sau:

- `<inventory>` nói: *QT-01 đang kẹt ở bước 2*;
- tác tử biết chính xác phải gỡ cái gì, không phải hỏi "anh đang ở đâu rồi";
- và bản thân tiến độ cũng là một changeset — hoàn tác được, có lịch sử.

### 3.4. STALE theo quy trình

Quy trình nằm **hạ nguồn** của REQ, ADR và BOM:

```
REQ → ADR (chọn bo mạch) → script → quy trình
Fact (dung lượng 32 GB) ──────────→ script, quy trình
```

Đổi bo mạch ⇒ `ADR-01` v2 ⇒ script và quy trình STALE ⇒ băng cảnh báo trên tab, và tác
tử **đề nghị** cập nhật chứ không tự viết lại. Đúng §E5.4.

*Mở rộng đáng làm ở G3:* STALE **theo bước**, không theo cả quy trình. Đổi dung lượng
chỉ làm hỏng bước 4 và 7; đánh dấu cả 12 bước là nói quá và người sẽ học cách bỏ qua
băng cảnh báo.

---

## 4. Ranh giới với `EIDE.md`

Phiên 25/09 cho thấy tác tử gọi `memory.note` **8 lần** — nó dồn mục tiêu, giả định,
quyết định, phần cứng, quy ước vào `EIDE.md` vì đó là công cụ ghi duy nhất nó có.

Hệ quả, bằng đúng ngôn ngữ tài liệu: quyết định chọn Raspberry Pi Zero 2 W **không có
phiên bản, không có hạ nguồn, không hoàn tác riêng được, và sẽ bị nén mất** khi ngữ cảnh
đầy.

Ranh giới nên là:

| Thuộc về | Lưu ở |
|---|---|
| Mục tiêu dự án · quy ước làm việc · "đừng làm nữa" | `EIDE.md` |
| Yêu cầu · phương án · quyết định · linh kiện · Fact · quy trình | **kho hiện vật** |

Quy tắc một câu: **cái gì có phiên bản, có hạ nguồn, hoặc cần hoàn tác riêng thì không
thuộc về `EIDE.md`.**

---

## 5. Đề xuất bổ sung cho MDD-40 §E2

Thêm hai dòng vào bảng 22 loại hiện vật:

| Hiện vật | Dạng máy | Dạng người (tab · khối) | Lớp giải thích nói gì | Người sửa gì | Khi lưu → STALE |
|---|---|---|---|---|---|
| **Script vận hành** | tệp trong `scripts/`, git | Mã nguồn · danh sách + editor; hằng số gạch chân nguồn | Script làm gì, chạy ở đâu, hằng số nào từ đâu, hỏng thì sao | Sửa tự do · editor | Quy trình gọi nó → STALE |
| **Quy trình** | `procedure.yaml` (§3.2) | Mã nguồn · danh sách bước có ô đánh dấu, lệnh sao chép được, bước nguy hiểm tô đỏ | Làm xong đạt gì, cần gì trước, bước nào không đảo ngược | Đánh dấu xong/thất bại + ghi chú | Không (nó là lá) |

---

## 6. Đã hiện thực trong đợt này

| | |
|---|---|
| `store.procedure_set` | ghi quy trình có cấu trúc; **từ chối** nếu bước trỏ tới script chưa tồn tại |
| `store.procedure_progress` | đánh dấu bước xong/thất bại → changeset |
| `.sh`/`.service`/`.dts` xếp vào nhóm `code` | script được soi hằng số, lên tab Mã nguồn, STALE được |
| Giao diện khối `procedure` | ô đánh dấu, nút sao chép lệnh, bước không đảo ngược tô đỏ trước |
| `store.option_*` · `store.adr_*` · `store.bom_set` | quyết định thiết kế rời khỏi `EIDE.md`, thành hiện vật |
| Hiến pháp §10 | bảng "chốt cái gì → ghi bằng công cụ nào" |

## 7. Còn thiếu

| | Thuộc bước |
|---|---|
| Quét lệnh phá hoại trong script trước khi ghi (TC070) | G4 |
| `bash -n` / `shellcheck` ở hook PostToolUse | G3 |
| STALE theo **bước** thay vì theo cả quy trình | G3 |
| Xuất quy trình ra PDF/Markdown để in mang ra bàn thí nghiệm | G5 |
| Chạy script hộ người dùng qua SSH và thu kết quả | G7 |
