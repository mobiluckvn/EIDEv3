# Hướng dẫn cài đặt EIDE v3

*Đề tài: **Phát triển phần mềm nhúng có ứng dụng trí tuệ nhân tạo (AI)***
*Vũ Trí Công · GVHD: TS. Nguyễn Trung Hiếu · Học viện Công nghệ Bưu chính Viễn thông*

---

## Đọc trước 30 giây

EIDE có **hai phần chạy được độc lập**, và biết điều này tiết kiệm cho anh nhiều thời gian:

| Phần | Cần gì | Không có thì sao |
|---|---|---|
| **Lõi tác tử** (Python) | Python ≥ 3.11 + một khoá Gemini | — |
| **Giao diện** (macOS) | Thêm Xcode Command Line Tools | Vẫn dùng được lõi ở dòng lệnh |

Lõi chạy **không cần giao diện**. Nếu anh chỉ muốn xem tác tử làm việc, dừng ở **Bước 3** là đủ.

Mọi thứ khác — chuỗi biên dịch ARM, bộ nạp chip, OCR, LibreOffice — đều **tuỳ chọn**. Thiếu
cái nào thì EIDE **nói ra thiếu cái gì và cài bằng lệnh nào**, chứ không lỗi cứng và không âm
thầm làm sai. Đừng cài trước những thứ anh chưa cần.

---

## Bước 1 — Lấy mã nguồn

```bash
git clone git@github.com:mobiluckvn/EIDEv3.git
cd EIDEv3
```

Kiểm Python. Cần **3.11 trở lên** (`pyproject.toml`); máy dựng tài liệu này chạy 3.14.7.

```bash
python3 --version
```

macOS chưa có Python đủ mới thì:

```bash
brew install python@3.12
```

---

## Bước 2 — Dựng môi trường Python

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

`-e` (editable) là **có chủ ý**: sửa mã trong `src/` là dùng được ngay, không phải cài lại.
`[dev]` kéo thêm `pytest` để chạy bộ kiểm.

Lệnh này kéo về: `google-genai` (gọi mô hình) · `pyyaml`, `jsonschema`, `websockets` (giao
thức và luật) · `python-docx`, `openpyxl`, `python-pptx` (đọc Office, **không cần cài Office**)
· `pytesseract`, `pillow` (OCR) · `kiutils` (đọc/ghi `.kicad_sch` — **thư viện Python thuần,
không phải KiCad**).

**Kiểm ngay:**

```bash
.venv/bin/python -m eide --help
```

Phải in ra `usage: eide-core …`. Nếu báo `No module named eide` thì bước `pip install -e` chưa
chạy xong — chạy lại, đừng bỏ qua.

---

## Bước 3 — Khoá Gemini

```bash
cp .env.example .env
```

Mở `.env`, điền khoá lấy ở <https://aistudio.google.com/apikey>:

```
GEMINI_API_KEY=...
```

Ba điều về khoá này, đều là ràng buộc trong mã chứ không phải lời dặn:

- `.env` **nằm ngoài git** (`.gitignore`). Khoá không bao giờ đi vào lịch sử mã nguồn.
- EIDE chỉ nhận **`gemini-3.8-flash`**. Đặt tên mô hình khác thì mã **từ chối ngay khi khởi
  động** — không phải một cảnh báo rồi chạy tiếp.
- Không dán khoá vào bất kỳ tệp nào khác, kể cả tệp tạm.

**Chạy thử một lượt, không cần giao diện:**

```bash
mkdir -p du-lieu/thu-dau-tien
.venv/bin/python -m eide --du-an du-lieu/thu-dau-tien \
  --go "Chào bạn, dự án này đang có gì?"
```

Tác tử trả lời trong terminal là **lõi đã chạy được**. Thư mục `du-lieu/thu-dau-tien` giờ có
`EIDE.md`, `du-an.json` và `.eide/` — xem [§Dữ liệu dự án](#dữ-liệu-dự-án-nằm-ở-đâu).

---

## Bước 4 — Giao diện macOS *(tuỳ chọn)*

Cần **Xcode Command Line Tools**:

```bash
xcode-select --install
swift --version          # cần Swift 5.9 trở lên; máy dựng tài liệu này chạy 6.3
```

Dựng và mở:

```bash
cd ui/EIDEApp && ./dong-goi.sh
open EIDE.app
```

Lần đầu mở, màn hình hỏi ba đường dẫn:

| Ô | Điền gì |
|---|---|
| **Thư mục dự án** | Thư mục tác tử được phép đọc/ghi — đây cũng là **hộp cát** của nó |
| **Gốc mã nguồn EIDE** | Thư mục chứa `src/eide`, tức chỗ anh vừa `git clone` |
| **Python** | Bỏ trống = dùng `.venv/bin/python` trong gốc mã nguồn |

App tự nhớ cho lần sau và tự mở lại dự án gần nhất. Thư mục **rỗng cũng mở được** — EIDE tự
dựng dự án mới trong đó.

App chạy lõi Python làm **tiến trình con**, nói JSON-RPC trên stdio. **Không mở cổng mạng
nào** — EIDE là ứng dụng một người trên máy cá nhân.

---

## Bước 5 — Công cụ phần cứng *(chỉ khi cần)*

**Đừng cài trước.** Khi tác tử cần một công cụ, nó chạy `env.check`, nói rõ thiếu gì và đề
nghị cài qua cổng `G-TOOL` để anh duyệt. Bảng dưới để anh biết trước mình sẽ được hỏi gì.

| Việc | Công cụ | Cài trên macOS |
|---|---|---|
| Biên dịch ARM Cortex-M (STM32…) | `arm-none-eabi-gcc` | `brew install --cask gcc-arm-embedded` |
| Biên dịch AVR (Arduino, ATmega) | `arduino-cli` (kèm luôn `avr-gcc`) | `brew install arduino-cli` |
| Nạp và đọc ngược Flash qua ST-LINK | `st-flash`, `st-info` | `brew install stlink` |
| Soi chip: thanh ghi, ngăn xếp, khung ảnh | `openocd` | `brew install openocd` |
| OCR hình trong datasheet | `tesseract` + gói ngôn ngữ | `brew install tesseract tesseract-lang` |
| Đọc `.doc`/`.xls`/`.ppt` đời cũ | LibreOffice | `brew install --cask libreoffice` |

Kiểm máy có gì:

```bash
.venv/bin/python -m eide --du-an du-lieu/thu-dau-tien \
  --go "Kiểm xem máy này đã đủ công cụ biên dịch cho STM32 chưa?"
```

> **Một điều đã đo được, và nó sẽ làm anh mất buổi chiều nếu không biết trước:**
> `arm-none-eabi-gcc` bản Homebrew **không kèm newlib**. Mọi hàm thư viện chuẩn (`memset`,
> `memcpy`, `printf`…) sẽ báo `undefined reference` khi liên kết — **kể cả khi anh không gọi
> chúng**, vì trình biên dịch tự sinh `memcpy`/`memset` cho phép gán cấu trúc và khởi tạo
> mảng. EIDE tự liên kết ở chế độ `-nostdlib` và **nói ra điều này** trong kết quả biên dịch.

### Bo mạch thật

Đề tài này chạy trên **STM32F469I-DISCO**. Cắm cáp USB vào cổng **ST-LINK** (không phải cổng
USB OTG). Kiểm:

```bash
ls /Volumes/ | grep DIS_       # ổ nạp kiểu ổ đĩa: DIS_F469NI
st-info --probe                # đọc ID chip qua SWD
```

Hai điều đã đo trên chính bo này:

- Cổng ảo `/dev/cu.usbmodem*` **không nối vào USART nào** của chip. Đừng chờ log qua đó —
  `target.log` sẽ nói thẳng là cổng im lặng.
- `system_profiler SPUSBDataType` trả rỗng trên macOS bản này. EIDE dò bo bằng `/Volumes/*`
  và `/dev/cu.*`.

---

## Kiểm lại toàn bộ

Ba lệnh, từ rẻ tới đắt. **Lệnh cuối mới là lệnh chứng minh cài đúng** — hai lệnh đầu chỉ
chứng minh mã chạy được.

```bash
# 1. Bộ kiểm đơn vị — 0 token, ~2 phút
.venv/bin/python -m pytest -q
#    → 1252 passed

# 2. Tài liệu có nói khác mã không — 0 token, tức thì
.venv/bin/python tools/kiem_tai_lieu.py
#    → 0 chỗ LỆCH CHẮC CHẮN

# 3. Quét toàn bộ giao diện — cần app đã dựng ở Bước 4
.venv/bin/python tools/quet_giao_dien.py --du-an du-lieu/thu-dau-tien
#    → 123/124 ô đạt trên một dự án TRỐNG
```

**Về con số 123/124:** trên một dự án vừa tạo, đúng một ô đỏ — *"có ít nhất một khối cho
người sửa trực tiếp bằng widget"*. Nó đỏ vì **dự án chưa có hiện vật nào để sửa**, không phải
vì cài sai. Chạy trên một dự án đã làm việc thì đủ **124/124**.

Nói ra con số thật thay vì con số đẹp: một hướng dẫn hứa 124/124 rồi người cài thấy 123 sẽ đi
tìm lỗi không tồn tại.

---

## Dữ liệu dự án nằm ở đâu

Tất cả nằm **trong thư mục dự án**, không có gì ở nơi khác. Chép cả thư mục là mang cả dự án.

| Đường dẫn | Là gì | Mất thì sao |
|---|---|---|
| `EIDE.md` | Bộ nhớ dài hạn — anh và tác tử cùng sửa | **Mất hẳn** |
| `du-an.json` | Thẻ căn cước: đang ở đâu, chép đi phải mang gì | Tự sinh lại |
| `.eide/ledger.jsonl` | Sổ cái append-only, có chuỗi hash | **Mất hẳn** |
| `.eide/store.sqlite` | Kho hiện vật | **Mất hẳn** |
| `.eide/changesets.jsonl` + `blobs/` | Phép hoàn tác | **Mất hẳn** |
| `.eide/build/` | Bản biên dịch | Dựng lại được |
| `.git/` | Mỗi changeset một commit | **Mất hẳn** |

Ngoài thư mục dự án chỉ có đúng một tệp: `~/.eide/memory.md` — sở thích của anh dùng chung
mọi dự án.

**Chuyển máy:** File ▸ **Xuất dự án…** (gói `.zip`, tự bỏ phần dựng lại được — đo được
14,4 MB → 2,0 MB) rồi File ▸ **Nhập dự án…** ở máy mới. Nhập xong nó **kiểm chuỗi hash sổ cái
trước khi nói xong** — gói hỏng thì nói gãy ở đâu, không mở im lặng.

---

## Khi gặp trục trặc

| Hiện tượng | Nguyên nhân thường gặp | Cách xử |
|---|---|---|
| `No module named eide` | Chưa `pip install -e ".[dev]"` | Chạy lại Bước 2 |
| App mở lên rồi báo mất kết nối lõi | Sai ô **Gốc mã nguồn** hoặc ô **Python** | Kiểm `<gốc>/src/eide` có thật; để trống ô Python |
| Tác tử báo thiếu khoá | `.env` chưa có `GEMINI_API_KEY` | Bước 3 |
| Khởi động là từ chối ngay | Đặt tên mô hình khác `gemini-3.8-flash` | Bỏ dòng `EIDE_MODEL_MAIN` trong `.env` |
| Nạp bo không thấy thiết bị | Cắm nhầm cổng USB OTG | Đổi sang cổng **ST-LINK** |
| `undefined reference to memcpy` | `arm-none-eabi-gcc` thiếu newlib | Bình thường — EIDE liên kết `-nostdlib` và nói ra |
| Tác tử bảo không đọc được tệp anh vừa kéo vào | Tệp nằm **ngoài** thư mục dự án | Dùng nút 📎 hoặc kéo–thả vào Console: EIDE tự chép vào `tai-lieu/` |
| Muốn lùi việc tác tử vừa làm | `⌘Z` là Undo của **ô văn bản** | Dùng **Tác tử ▸ Hoàn tác việc vừa làm ⌥⌘Z** |

Còn vướng thì mở tab **Nhật ký** trong app — mọi lời gọi công cụ, mã lỗi và lý do đều ở đó;
hoặc đọc `<dự án>/.eide/ledger.jsonl`.

---

## Đọc tiếp

| Tài liệu | Nói về |
|---|---|
| [`README.md`](../../README.md) | Tác tử làm được những gì — 119 công cụ theo việc |
| [EIDE-C4-46](EIDE-C4-46_Kien_truc_theo_mo_hinh_C4.md) | Kiến trúc theo mô hình C4 |
| [EIDE-MDD-40](../review-v3/docs/md/EIDE-MDD-40_v3.0_Thiet_ke_Tong_the.md) | Thiết kế tổng thể — nguồn sự thật |
| [EIDE-DEV-LOG](EIDE-DEV-LOG.md) | Mọi lệch mã ↔ tài liệu, theo thời gian |
