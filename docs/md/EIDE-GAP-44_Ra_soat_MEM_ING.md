# EIDE-GAP-44 — Rà soát mã hiện tại theo MEM-42, ING-43 và SCH-44

*25/09/2026 · Vũ Trí Công · rà trên nhánh `main` tại commit `e3ad881` (sau G5)*

Đối chiếu **EIDE-MEM-42** (thay §B6 của MDD-40), **EIDE-ING-43** (chi tiết hoá §C3) và
**EIDE-SCH-44** (tính năng mới, cộng thêm) với mã đang chạy. Mỗi dòng có tệp:dòng đã đọc, không suy từ tên hàm.

Ký hiệu: **CÓ** đủ theo tài liệu · **MỘT PHẦN** có xương, thiếu phần chính · **KHÔNG**
chưa có gì · **KHÁC** mã làm khác tài liệu một cách có chủ đích (phải ghi DEV-2xx).

---

## 0. Bức tranh chung trước khi vào bảng

Ba nhận định dẫn tới mọi thứ bên dưới:

**(a) Toàn bộ tầng M1 hiện nằm trong RAM.** `Agent.messages` là một `list` Python
(`src/eide/loop.py:143`). `Paths.transcripts` được tạo thư mục (`src/eide/config.py:161`)
nhưng **không có một dòng mã nào ghi vào đó** — `grep -rn "paths.transcripts" src/` trả
về rỗng. Hệ quả dây chuyền: không write-ahead transcript, không resume ngữ cảnh mô hình,
không ghim, không huỷ nén, không `.eide/sessions/`. Sổ cái vẫn đầy đủ và giao diện dựng
lại được dòng hội thoại từ đó (`rpc.py:155`), nhưng **mô hình mở lại dự án với ngữ cảnh
trắng** ngoài EIDE.md + `<inventory>`. Đây là gốc của 7 trong 24 mục MEM.

**(b) Không có `ToolResultEnvelope`.** Kết quả tool đi thẳng vào transcript nguyên văn:
`self.messages.append({..., "result": res.to_model()})` (`src/eide/loop.py:405`). Chỉ
`fs.read` tự cắt theo byte (`tools/builtin.py:86`) và `fs.grep` cắt 200 ký tự mỗi dòng
(`:140`). `BlobStore` đã có, content-addressed, `sha256`, đã chạy thật cho snapshot
(`src/eide/changeset.py:214–239`) — nhưng **chưa bao giờ được dùng cho tool_result**.
Đây là mục MEM-42 gọi là "biện pháp quan trọng nhất và rẻ nhất" (§5.1).

**(c) `.docx` hiện bị phân loại thành ARCHIVE.** `phan_loai()` duyệt `_MAGIC` và khớp
`PK\x03\x04` → `archive` ở `src/eide/knowledge/ingest.py:178–181`, **trước** khi có bất
kỳ phép kiểm `[Content_Types].xml` nào. Đây đúng là lỗi ING-43 §3 chỉ ra, và nó cùng
một hình dạng với TC023 mà G4 đã sửa cho netlist — chỉ là chưa sửa cho Office. Tệp mẫu
`.docx` của chính anh (`docs/20260925/EIDE-ING-43…docx`) nếu nạp vào hôm nay sẽ bị bóc
thành `word/document.xml`.

---

## 1. MEM-01 … MEM-24

| Mã | Trạng thái | Bằng chứng trong mã | Thiếu gì | Ca đo | Bước |
|---|---|---|---|---|---|
| MEM-01 Ngân sách 10 khối, dự trữ 20 % | **MỘT PHẦN** | `ContextBudget` có 7 khối với trần đúng như MDD-40 §B2 (`config.py:62–70`); `assemble()` áp trần từng khối (`context/assemble.py:220–229`) | Thiếu 3 khối: lược đồ tool (4 k), skill đã nạp (6 k), bản tóm tắt phiên (3 k). **Không có dự trữ 20 %** — không chỗ nào trừ chỗ cho câu trả lời + tool_result của lượt | MEM02 | MEM-A |
| MEM-02 Đồng hồ token theo khối, 4 ngưỡng | **MỘT PHẦN** | `Assembled.tokens` có token từng khối (`assemble.py:247`); `_context_pressure` tính tỉ lệ (`loop.py:775`) | Chỉ MỘT ngưỡng (`compact_at = 0.70`, `config.py:58`), thiếu 60/85/95. Giao diện hiện tool/giây chứ không hiện token theo khối (`RootView.swift:151`) | MEM02 | MEM-A |
| MEM-03 Ghi M2/M3 qua tool có changeset + provenance; deny `fs.write` EIDE.md | **MỘT PHẦN** | `memory.note` ghi qua tool và tạo changeset (`tools/writing.py:198–216`) | **Không có luật deny `fs.write` vào EIDE.md** — `grep "EIDE.md" policy.yaml` rỗng. Tác tử ghi đè thẳng được. Không có `scope=user`, không có `category` danh sách trắng | MEM03 | MEM-B |
| MEM-04 C0: cắt theo tool, blob, ref artefact id+version | **KHÔNG** | — | Xem §0(b). Cần `ToolResultEnvelope` + bảng chính sách 12 tool (MEM-42 §5.1) | MEM01 | MEM-A |
| MEM-05 C1: stub/dedup/supersede/hết hạn 8 lượt | **KHÔNG** | `_compact` chỉ cắt cụt: giữ 10 message cuối, phần còn lại thành một dòng (`loop.py:779–794`) | Không dedup, không supersede, không stub có `blob_ref`. Và nó đếm **message**, không đếm **lượt** | MEM05 | MEM-A |
| MEM-06 C2: PreCompact rút cấu trúc, tóm tắt 10 mục, atomic swap | **KHÔNG** | Docstring `_compact` có nhắc PreCompact nhưng thân hàm không gọi hook nào (`loop.py:780`) | `HookBus` chỉ có 3 điểm móc: `on_pre_tool`/`on_post_tool`/`on_stop` (`hooks/base.py:58–66`). Cần thêm `pre_compact`/`post_compact`. Chưa có lược đồ `SessionSummary v1` | MEM05, MEM06 | MEM-C |
| MEM-07 Ghim tự động + thủ công | **KHÔNG** | — | Không có khái niệm `pinned` trên message | MEM12 | MEM-C |
| MEM-08 PostCompact 3 câu hỏi ngược, sai → huỷ | **KHÔNG** | — | Đây là mục mình đánh giá có giá trị cao nhất trong cả MEM-42: nó biến "nén có mất gì không" từ câu hỏi thành phép đo | MEM08 | MEM-C |
| MEM-09 C3 bậc thang, C4 khẩn cấp, huỷ nén 24 h | **KHÔNG** | — | Phụ thuộc M1 có trên đĩa (§0a) | MEM09 | MEM-D |
| MEM-10 EIDE.md: trần 3 k, cấu trúc, nguồn gốc dòng, quyền ghi, prune | **MỘT PHẦN** | Cấu trúc mục cố định (`store/eide_md.py:23`); cắt theo trần khi render (`:146–159`); ring buffer 10 dòng "Người vừa sửa" (`:27, :133`) | Cắt chỉ xảy ra **lúc đưa vào ngữ cảnh** — tệp thật vẫn phình, không có băng cảnh báo, không có `memory.prune`. Không có nguồn gốc dòng `[run-xx]`/`[h-xxxx]`. Không có quyền ghi theo mục (tác tử ghi được vào "Đừng") | MEM10 | MEM-B |
| MEM-11 Tóm tắt phiên xem/sửa trên UI | **KHÔNG** | — | Chưa có bản tóm tắt nào để mà sửa | MEM11 | MEM-C |
| MEM-12 Người thấy cửa sổ ngữ cảnh | **KHÔNG** | — | Cần khối A14.6 | MEM12 | MEM-C |
| MEM-13 `memory.forget` → tombstone | **KHÔNG** | — | Không có tool, không có loại sự kiện tombstone trong `EVENT_KINDS` (`protocol/ledger.py:30–42`) | MEM13 | MEM-B |
| MEM-14 M3 danh sách trắng, đề xuất phải người đồng ý | **KHÔNG** | — | Không có `~/.eide/memory.md`. `config.user_memory_path()` đã khai đường dẫn (`config.py:166`) nhưng không ai gọi | — | MEM-B |
| MEM-15 Subagent ngữ cảnh sạch, báo cáo ≤ 800 token | **KHÔNG** | — | Subagent là G6, chưa tới | — | MEM-D |
| MEM-16 `ledger.query` cho câu hỏi về quá khứ | **MỘT PHẦN** | `Ledger.find_run()` tra được (`protocol/ledger.py`), `ledger.verify` có trong registry | **Không có tool `ledger.query`** cho mô hình (48 tool hiện có, không có mục này). Hiến pháp cũng chưa bắt tra trước khi trả lời câu hỏi về quá khứ | MEM06 | MEM-B |
| MEM-17 Resume 5 bước, không có summary null | **MỘT PHẦN** | `ui.sync` dựng lại 60 dòng transcript từ sổ cái cho **giao diện** (`rpc.py:155`); `<inventory>` dựng mỗi lượt | Mô hình **không** được nạp lại gì — messages rỗng. Không có bước kiểm toàn vẹn khi mở, không có "mô hình tự thuật 5–8 câu". Điểm tốt: vì không có trường `summary` sinh riêng nên lỗi TC065 (`summary = null`) **không tái diễn được** — nhưng đó là do chưa làm, không phải do thiết kế | MEM06 | MEM-C |
| MEM-18 Write-ahead transcript; nén là giao dịch; hash chuỗi | **MỘT PHẦN** | Sổ cái write-ahead thật, có `fsync` mỗi lần ghi (`ledger.py:115–119`) và hash chuỗi kiểm được (`:124`) | Transcript (M1) không write-ahead (§0a). Changeset chưa có `prev_hash` nối chuỗi | MEM14 | MEM-B |
| MEM-19 Retention và gc blob | **KHÔNG** | — | Blob chỉ có `put`/`get`/`exists` (`changeset.py:228–239`), không đếm tham chiếu | — | MEM-D |
| MEM-20 Cache tài liệu M4 theo hash; Fact không theo cache | **KHÔNG** | — | Tài liệu nạp vào từng dự án, không có `~/.eide/docs-cache` | — | MEM-D |
| MEM-21 `<facts>` chọn theo thực thể 3 lượt gần, ưu tiên tầng | **MỘT PHẦN** | Rút thực thể bằng regex từ 3 lượt gần (`assemble.py:219`, `mentioned_entities`), dựng `<facts>` có tầng + trích dẫn (`:122–143`). Ô rỗng nói thẳng "chưa có Fact nào" thay vì im lặng (`:135`) | **Không sắp xếp theo tầng** — lấy theo thứ tự kho rồi cắt bằng `body[:cap]`, nên một Fact VÀNG có thể bị cắt mất trong khi Fact ĐỒNG ở trên vẫn còn | — | MEM-A |
| MEM-22 Bỏ skill không dùng 5 lượt | **KHÔNG** | `build_skills_hint` có (`assemble.py:190`) nhưng không có `skill.load`, không có skill nào được nạp | — | MEM-D |
| MEM-23 Khoá tệp nhiều phiên | **KHÔNG** | Chỉ có soft-lock **tệp trong một phiên** (`loop.py:92–99`) — khác việc | — | MEM-D |
| MEM-24 Đo lường §13 | **MỘT PHẦN** | Token theo lượt và theo phiên đã tách đúng (`loop.py:823`, DEV-232); sổ cái có `llm_call` | Không có 6 chỉ số của §13, không có màn hình Thiết lập | — | MEM-D |

**Tổng MEM: CÓ 0 · MỘT PHẦN 9 · KHÔNG 15.**

---

## 2. ING-01 … ING-20

| Mã | Trạng thái | Bằng chứng trong mã | Thiếu gì | Ca đo | Bước |
|---|---|---|---|---|---|
| ING-01 Phân loại theo nội dung, Office → archive → text, có lý do + độ tin cậy | **MỘT PHẦN** | Phân loại theo magic bytes thật, đuôi chỉ là gợi ý (`knowledge/ingest.py:155–236`); mỗi kết quả có `mo_ta` + `ly_do_khong_doc` + `de_xuat` | **Sai thứ tự**: zip → archive ở `:178–181` trước mọi phép kiểm Office (§0c). Không có trường `do_tin_cay` (confidence) trên kết quả phân loại | ING01 | ING-A |
| ING-02 Ba mức ĐẦY ĐỦ/MỘT PHẦN/KHÔNG hiển thị cho người | **KHÁC** | Hiện chỉ có nhị phân `doc_duoc: bool` (`ingest.py:130`) kèm đề xuất thay thế | Cần ba mức để người biết "đọc được nhưng không trích Fact tự động" | ING01 | ING-A |
| ING-03 Không đưa tệp không phải archive vào `archive.list` | **KHÁC** | Không có tool `archive.list` nào cả; `ingest.file` tự định tuyến theo loại | Tinh thần đã đạt (TC023 xanh trong `thu_g4.py`), nhưng **không đúng với .docx** vì .docx bị xếp vào archive | ING06 | ING-A |
| ING-04 Archive bóc đệ quy có giới hạn, chọn tệp khi > 20, chống zip bomb | **KHÔNG** | Chỉ liệt kê 50 mục đầu và kiểm CRC (`ingest.py:240–259`) | Không bóc, không giới hạn 3 cấp/500 MB/2000 tệp, **không kiểm tỉ lệ nén** | ING15 | ING-A |
| ING-05 Office .docx/.xlsx/.pptx đọc cấu trúc; định dạng cũ chuyển đổi | **KHÔNG** | — | Không có bộ đọc Office nào. Cần `python-docx`, `openpyxl`, `python-pptx`, LibreOffice headless | ING01–03 | ING-B |
| ING-06 Trích dẫn theo loại; docx → PDF phái sinh | **MỘT PHẦN** | PDF trích dẫn theo **trang**, và mọi Fact đều buộc có trang (`knowledge/docs.py`, đã đo trong `thu_g4.py`) | Không có heading/table/row, sheet!ô, slide# | ING06 | ING-B |
| ING-07 Bảng → Fact ứng viên; giá trị đọc bằng mã | **MỘT PHẦN** | `trich_fact_ung_vien` đọc số **bằng regex, không qua mô hình** (`docs.py:194`) — đúng nguyên tắc ING-07 | Trích theo **dòng văn bản**, chưa nhận diện cấu trúc bảng (cột Symbol/Min/Typ/Max/Unit). Mô hình chưa được giao việc ánh xạ tiêu đề cột | ING09 | ING-C |
| ING-08 Ô gộp, bảng xoay, min/typ/max chung ô, Note → condition | **KHÔNG** | `FactUngVien` có chỗ cho `condition` nhưng luôn rỗng (`docs.py:255`) | — | ING09 | ING-C |
| ING-09 EDA: KiCad .net/.kicad_sch; Eagle/EasyEDA; Altium từ chối đúng; BOM ↔ netlist | **MỘT PHẦN** | `.net` nhận đúng và đếm net (`ingest.py:211–214`, `_la_netlist`); Altium từ chối đúng tên + đường đi tiếp (`:49–59`, TC025 xanh) | `.kicad_sch` nhận loại nhưng **không có parser** (`:216`). **Eagle `.sch`/`.brd` bị xếp vào "không hỗ trợ" theo đuôi** (`:53–54`) — sai với Eagle XML, mà ING-43 xếp MỘT PHẦN. Không có đối chiếu BOM ↔ netlist | ING06, ING07 | ING-D |
| ING-10 Cấu hình vendor → Fact tầng CẤU HÌNH | **KHÔNG** | `.dts` chỉ được gắn nhãn "config" chung chung (`ingest.py:68, :227`) | Không có `.ioc`/`sdkconfig`/`.ld`/`map`; **không có tầng CẤU HÌNH** — hệ thống chỉ có 4 tầng (`store/inventory.py:29`) | ING08 | ING-D |
| ING-11 CẤU HÌNH không bao giờ là vế giới hạn vật lý | **KHÔNG** | `TANG_DUNG_DUOC = {VANG, BAC, NGUOI}` (`knowledge/compare.py:26`) | Cơ chế chặn **đã sẵn sàng**: thêm tầng CẤU HÌNH mà không thêm vào tập này là nó tự động bị loại khỏi so sánh. Rẻ | ING08 | ING-D |
| ING-12 Hình → đoạn RAG "figure" | **KHÔNG** | Ảnh bị từ chối kèm lý do đúng (`ingest.py:185–190`) | Không có RAG nói chung — không có `rag.ask` trong 48 tool | ING10 | ING-E |
| ING-13 Đối chiếu chéo cùng key, quy tắc ưu tiên | **MỘT PHẦN** | `fact.compare` so hai Fact có bằng chứng, 8 luật (`knowledge/compare.py`) | So **hai Fact do mô hình chỉ định**, không tự quét trùng key nhiều nguồn. Không có thứ tự ưu tiên errata > DS mới > DS cũ > cấu hình > mã | ING16 | ING-C |
| ING-14 Chuẩn hoá đơn vị bằng mã, giữ raw | **MỘT PHẦN** | `ve_si()` đưa về SI trước khi so (`docs.py:70–78`), bảng 40 đơn vị (`:55–68`) | Không có "3V3"/"4R7"/"100n"; không có dải "2.7–5.5 V"; không có "—"/"N/A"/"TBD" → null; **không giữ `raw`** | ING12 | ING-C |
| ING-15 Đa ngôn ngữ | **KHÔNG** | — | — | ING11 | ING-E |
| ING-16 E1001–E1008 có message_vi + hint + alternatives | **KHÁC** | Mọi lỗi đã có đủ 4 trường theo thiết kế (`errors.py`); E1001 định dạng không hỗ trợ (`:78–90`), E1002 hỏng/cụt (`:100`) | **Xung đột mã**: `E1003` hiện là "đường dẫn không tồn tại" (`errors.py:112–118`), ING-43 định nghĩa E1003 = "mật khẩu". Thiếu E1004–E1008. Phải chốt cách đánh số rồi ghi DEV | ING04, ING05 | ING-A |
| ING-17 Giới hạn kích thước/trang; OCR nền | **KHÔNG** | — | Không có trần 200 MB / 2000 trang | — | ING-E |
| ING-18 Bọc untrusted, quét P-INJ, không chạy macro | **MỘT PHẦN** | Quét tiêm lệnh 6 mẫu khi nạp tài liệu (`docs.py:113–121`), cảnh báo đi theo `TaiLieu.canh_bao_tiem_lenh`; S0 có luật `P-INJ-01` | Nội dung tài liệu **chưa thật sự được bọc `<document untrusted>`** khi vào ngữ cảnh — docstring `docs.py:110` tự nhận điều này. Không có xử lý macro | ING13, ING14 | ING-A |
| ING-19 Gán tầng theo nguồn (bảng §6) | **MỘT PHẦN** | Fact trích ra mặc định **BẠC**, không tự lên VÀNG (`docs.py:243`, đã đo trong `thu_g4.py`) | Không phân biệt nguồn: nhà sản xuất / bên thứ ba / OCR / Office tự viết đều BẠC như nhau. **Mục chờ anh chốt** (xem §4) | — | ING-C |
| ING-20 Hằng số trong mã → ĐỒNG-mã | **KHÔNG** | Chốt chặn hằng số đi **ngược chiều**: kiểm số trong mã có nguồn chưa (`hooks/standard.py:120–160`) | Chưa trích `#define` thành Fact ứng viên để so với datasheet. `_DEFINE` regex đã có sẵn (`standard.py:53`) — dùng lại được | — | ING-D |

**Tổng ING: CÓ 0 · MỘT PHẦN 9 · KHÔNG 8 · KHÁC 3.**

---

## 2b. SCH-01 … SCH-22

SCH-44 là **tính năng mới**, không phải chỗ hở của bản đang chạy — nên bảng này gần như
toàn **KHÔNG**, và điều đó không nói lên gì xấu. Thứ đáng rà ở đây là khác: *(a)* tiền đề
nào chưa có, *(b)* bảy lớp bảo vệ của §2.1 dựa vào cơ chế nào mà hôm nay chưa tồn tại.

### 2b.1 Hai tiền đề chưa có — phải xử lý trước khi bắt đầu SCH-A

**(1) CKM chưa tồn tại.** SCH-44 mở đầu bằng *"từ Bản đồ tri thức mạch (CKM) đã có"*, và
lộ trình ghi điều kiện của SCH-A là *"sau G4 (CKM/Fact) của MDD-40"*. Mã có `"ckm"`,
`"pinout"`, `"netlist"`, `"block_diagram"` trong `ARTEFACT_TYPES` (`store/db.py:88`) —
nhưng **không công cụ nào ghi bốn loại đó**. 48 công cụ hiện có, không có `board.*`,
không có `diagram.render`, không có gì dựng `module_graph`. Tab Thiết kế chỉ hiện BOM và
pinout rỗng (`surfaces.py:305–342`, ô trống còn ghi `buoc="G4"`).

Nói thẳng: **`sch.compose` hôm nay không có đầu vào.** Điều này không có trong bảng 2.2
"điểm chạm" của SCH-44 vì tài liệu giả định G4 đã sinh CKM — nhưng G4 mà repo đã làm là
*nền tri thức* (tài liệu, Fact, hộ chiếu, so sánh), không phải *bản đồ mạch*.

**(2) Không có cơ chế cờ tính năng.** SCH-44 §2.1 dòng 2 đặt `features.schematic = false`
làm lớp bảo vệ số một. `Config` không có trường `features` nào (`config.py`), và
`settings.json` chưa tồn tại. Registry **có** sẵn thứ gần nhất — `core=False` cho nạp trễ
(`tools/registry.py:64, 125`) — nhưng nạp trễ ≠ cờ tính năng: `core=False` vẫn đăng ký
công cụ, chỉ giấu khỏi lược đồ cho tới khi `tool.search` mở ra. §2.1 đòi *"tool sch.\*
không được đăng ký (mô hình không thấy)"*.

### 2b.2 Bảng SCH-01 … SCH-22

| Mã | Trạng thái | Bằng chứng / chỗ dựa đã có | Thiếu gì | Bước |
|---|---|---|---|---|
| SCH-01 Sinh sơ đồ từ CKM qua SKiDL | **KHÔNG** | — | Cả CKM lẫn SKiDL | SCH-A |
| SCH-02 Netlist đẳng cấu với CKM, lệch → E7001 | **KHÔNG** | Họ mã `E7xxx` đã dành cho lịch sử/changeset (`errors.py`), `E7001`–`E7007` **đã dùng hết** cho undo/snapshot | **Xung đột mã lỗi lần hai.** `E7001` trong mã là lỗi hoàn tác. Xem §2b.3 | SCH-A |
| SCH-03 Không bịa chân: pinout ≥ NGƯỜI, thiếu → E7002 | **MỘT PHẦN** | Cơ chế chặn đã sẵn sàng và đã chứng minh: `TANG_DUNG_DUOC` (`compare.py:26`) và `kiem_truoc_khi_ghim` từ chối ghim hộ chiếu không có tài liệu (DEV-183) | Chưa có Fact loại `pinout`; chưa có tầng để so `≥ NGƯỜI` trên pinout | SCH-A |
| SCH-04 Style flat/hierarchical | **KHÔNG** | — | — | SCH-A/D |
| SCH-05 Bố cục có tiêu chí số, xác định | **KHÔNG** | — | Thuật toán §4 (vùng, A\* có phạt gấp) | SCH-B |
| SCH-06 SVG có id theo ref/net | **KHÔNG** | — | Renderer nội bộ | SCH-B |
| SCH-07 Tương tác ký hiệu → Fact/nguồn | **KHÔNG** | `ViSaoView.swift` đã là đúng cái panel cần bật lên khi bấm ký hiệu — dùng lại được | Khối A5.8; SVG trong SwiftUI | SCH-B |
| SCH-08 Renderer nội bộ là chính, suy giảm về sơ đồ khối | **KHÔNG** | Mẫu suy giảm đã có và đã đo: `doc.search_web` thiếu cấu hình thì báo `E3001` nói rõ "trạng thái đã lưu, tiếp tục được" | Chưa có cả mức R1 lẫn R3 | SCH-A |
| SCH-09 Không cài/gọi/đề nghị cài KiCad | **CÓ (do chưa có gì)** | Không chỗ nào trong mã nhắc `kicad-cli`. `tool.install` có trong bảng policy nhưng **chưa được đăng ký** làm công cụ | Cần một phép kiểm **chủ động** canh chữ "cài KiCad" không lọt vào thông điệp nào — xem §2b.4 | SCH-A |
| SCH-10 Diff sơ đồ bằng lời (E3) | **MỘT PHẦN** | `so_sanh_kho`/`se_mat_gi` đã diff theo loại hiện vật và nói bằng lời (`snapshot.py:207–280`); `diff_prev` bắt buộc trên mọi hiện vật (G3) | Chưa có diff hình học (vị trí) | SCH-B |
| SCH-11 Xuất gói, theo dõi mtime, Nạp lại | **KHÔNG** | `vcs.py` theo dõi tệp qua git, không theo mtime | — | SCH-C |
| SCH-12 Round-trip phân loại thay đổi | **MỘT PHẦN** | `human_edit.phan_loai()` đã phân loại sửa của người thành 5 nhóm và **`trinh_bay` không gây STALE** (G3) — đúng hình dạng mà §7.3(a) "chỉ đổi vị trí → không STALE" cần | Cần thêm nhóm cho thay đổi hình học sơ đồ | SCH-C |
| SCH-13 Thay đổi cấu trúc → thẻ hỏi, không ghi đè im lặng | **MỘT PHẦN** | Đường thẻ làm rõ đã chạy và vừa được sửa trong G5 (DEV-246); `snapshot.propose` là mẫu sẵn cho "đề xuất rồi dừng" | — | SCH-C |
| SCH-14 Symbol lib đối chiếu Fact ≥ 95 % | **KHÔNG** | — | — | SCH-A |
| SCH-15 Symbol sinh từ Fact có ghi nguồn | **KHÔNG** | N1 đã áp cho Fact và hằng số trong mã; áp cho ký hiệu là cùng một cơ chế | — | SCH-B |
| SCH-16 Gói sch vào snapshot/release | **MỘT PHẦN** | `Snapshot.contents` đã gói kho + `git_sha` + blob (G5); thêm tệp sch là thêm khoá | — | SCH-A |
| SCH-17 Cờ mặc định tắt, tắt = không nhánh nào chạy | **KHÔNG** | Xem §2b.1(2) | Cơ chế cờ tính năng | SCH-A |
| SCH-18 Không đổi hợp đồng cũ; lược đồ chỉ cộng thêm; migration có `down()` | **KHÔNG** | **Store không có hệ thống migration nào** — ba bảng dựng bằng `CREATE TABLE IF NOT EXISTS` (`store/db.py:31, 46, 66`), không có `PRAGMA user_version` | Cần đánh số lược đồ + `up()/down()` trước khi thêm `sch_sheets` | SCH-A |
| SCH-19 Hồi quy hai chế độ giống 100 % | **MỘT PHẦN** | Có bộ hồi quy thật chạy được: 218 ca đơn vị + 4 bộ E2E (G3 31 · G4 23 · G5 35 · ING-A 29) | Chưa có cách **so hai lần chạy** tự động; hiện đọc bằng mắt | SCH-A |
| SCH-20 uuid ổn định theo ref | **KHÔNG** | `IdGen` sinh id người đọc được nhưng không phải uuid theo khoá | — | SCH-B |
| SCH-21 Mọi tệp sch là changeset, G-FILE khi ghi đè | **CÓ** | `history.ghi_tep` → changeset có nghịch đảo (G2); hook `ghi_de_ban_cua_nguoi` đã bật G-FILE đúng (`hooks/standard.py:194`) | Chỉ cần gọi đúng đường có sẵn | SCH-A |
| SCH-22 PCB/Gerber ngoài phạm vi | **CÓ** | `.kicad_pcb` xếp MỘT PHẦN, Gerber không nhận (ING-A) | — | — |

**Tổng SCH: CÓ 3 · MỘT PHẦN 6 · KHÔNG 13.**

### 2b.3 Xung đột mã lỗi lần hai — E7001/E7002

SCH-44 §3 dùng `E7001` cho "netlist lệch CKM" và `E7002` cho "chưa có pinout đã duyệt".
Trong mã, họ `E7xxx` **đã được dành cho lịch sử/changeset** (`errors.py:25–33`) và đã dùng
hết `E7001`…`E7007` cho hoàn tác, khôi phục snapshot, đánh dấu release, rẽ nhánh, ghi
bản ưng ý.

Đây đúng tình huống anh đã chốt cách xử lý ở DEV-249. Áp lại cùng quy tắc, **đề nghị**:

| SCH-44 gọi | Đề nghị dùng | Nghĩa |
|---|---|---|
| E7001 | **E8001** | netlist sinh ra không đẳng cấu với CKM — dừng, kèm diff |
| E7002 | **E8002** | chưa có pinout đã duyệt cho một ref — không bịa chân |

Mở họ **E8xxx cho sơ đồ/EDA**, để SCH-B…D còn chỗ đánh số tiếp. Mình chưa sửa gì, chờ
anh gật ở đây như lần trước.

### 2b.4 Hai chỗ SCH-44 đòi một phép kiểm mà tài liệu chưa nói cách làm

**(a) SCH-09 "không đề nghị cài KiCad ở bất kỳ thông điệp nào".** Đây là một ràng buộc
về *thứ không được xuất hiện*, và loại ràng buộc đó không tự giữ được. Mô hình rất dễ
"giúp" bằng câu *"anh cài KiCad rồi mở tệp này"* — đúng lúc nó tưởng đang hữu ích.

Đề nghị làm giống chốt chặn tên bản ưng ý (DEV-246): một phép kiểm ở hook `Stop` quét
lời tác tử trong lượt, thấy mẫu "cài KiCad"/"install KiCad"/"kicad-cli" thì chặn và bắt
nói lại. Cấm bằng lời trong hiến pháp là cấm không đo được.

**(b) SCH-19 "hồi quy hai chế độ giống 100 %".** Hiện bốn bộ E2E in bảng ra màn hình và
người đọc bằng mắt. Để so được hai lần chạy, `Bo.tong()` phải **xuất kết quả ra JSONL**
rồi có một lệnh so. Việc nhỏ (nửa ngày) nhưng phải làm **trước** SCH-A, vì nó chính là
bằng chứng mà §8 bước B và C đòi.

---

## 3. Mười sai lệch quan trọng nhất

Xếp theo *hậu quả cho người dùng thật*, không theo thứ tự tài liệu.

| # | Sai lệch | Vì sao nó đứng đây | Công |
|---|---|---|---|
| 1 | **.docx bị phân loại thành archive** (`ingest.py:178`) | Anh đưa yêu cầu bằng .docx. Hôm nay nạp vào thì nó bóc ra XML. Đây đúng là hình dạng lỗi TC023 mà G4 đã sửa — chỉ là sửa chưa hết | 0,5 ngày |
| 2 | **Không có ToolResultEnvelope** (`loop.py:405`) | Một `fs.read` tệp 3000 dòng hoặc một log build dài là hết cửa sổ. Repo thật > 500 tệp không làm việc được (TC028). Blob đã có sẵn, chỉ là chưa nối | 1,5 ngày |
| 3 | **M1 không nằm trên đĩa** (§0a) | Chặn 7 mục MEM. Lõi chết giữa lượt là mất hết ngữ cảnh mô hình; mở lại dự án hôm sau thì mô hình không biết hôm qua đã bàn gì | 1 ngày |
| 4 | **Không có PostCompact** (MEM-08) | Đây là mục mình đánh giá cao nhất trong MEM-42. Không có nó thì "nén có làm mất gì không" mãi là câu hỏi cảm tính. Có nó thì nó là một phép đo 3/3 hoặc huỷ | 1 ngày |
| 5 | **`fs.write` vào EIDE.md không bị chặn** (MEM-03) | Bộ nhớ dự án là thứ mô hình đọc mỗi lượt. Cho nó ghi đè thẳng thì nó tự viết thêm mục "Đừng" — đúng loại lỗi N7 cấm | 0,5 ngày |
| 6 | **Không có bộ đọc Office** (ING-05) | Trong môi trường làm việc thật, spec nội bộ và bảng đo là .docx/.xlsx nhiều hơn là PDF | 2 ngày |
| 7 | **Không có tầng CẤU HÌNH** (ING-10/11) | `.ld` khai FLASH 64 K còn chip 32 K là lỗi kinh điển và im lặng. Cơ chế chặn đã có sẵn ở `compare.py:26`, thêm tầng là xong | 1,5 ngày |
| 8 | **Bảng → Fact chưa nhận cấu trúc bảng** (ING-07/08) | Hiện trích theo dòng văn bản nên bảng Min/Typ/Max ra sai hoặc thiếu mà **không có cảnh báo** — im lặng là phần tệ nhất | 2 ngày |
| 9 | **Xung đột mã lỗi E1003** (ING-16) | Hai nghĩa cho một mã trong cùng sản phẩm. Phải chốt sớm, sửa sau thì mọi thông báo đã in ra đều sai | 0,25 ngày |
| 10 | **`<facts>` không xếp theo tầng** (MEM-21) | Cắt bằng `body[:cap]` nghĩa là Fact VÀNG có thể rơi mất trong khi ĐỒNG ở lại. Ngược đúng thứ tự mà N2 dựng nên | 0,25 ngày |

Ba mục nữa, thuộc SCH nhưng **phải xử lý trước khi chạm vào SCH**:

| # | Việc | Vì sao đứng đây | Công |
|---|---|---|---|
| 11 | **CKM chưa tồn tại** | `sch.compose` không có đầu vào. Bốn loại hiện vật `ckm`/`pinout`/`netlist`/`block_diagram` có tên trong kho mà không công cụ nào ghi | chưa ước được |
| 12 | **Không có cơ chế cờ tính năng** | Lớp bảo vệ số một của SCH-44 §2.1 dựa vào nó. `core=False` của registry là nạp trễ, không phải cờ | 0,5 ngày |
| 13 | **Store không có migration** | SCH-18 đòi `down()`. Ba bảng dựng bằng `CREATE TABLE IF NOT EXISTS`, không có `user_version` | 0,5 ngày |

---

## 4. Quyết định của chủ sản phẩm — 25/09/2026

Ba điểm đã chốt, ghi ở đây để mọi bước sau không phải hỏi lại.

| # | Điểm | Quyết định | Hệ quả trong mã |
|---|---|---|---|
| 1 | ING-19 — Office do người dùng tự viết | **Tầng NGƯỜI** | `ingest`/`doc.load` gán `tier="NGUOI"` khi nguồn không phải nhà sản xuất; trích dẫn trỏ về người, không về datasheet |
| 2 | Thứ tự bước | **Đồng ý đổi ING-A lên trước MEM-A** | Bảng §5 giữ nguyên thứ tự đã đề nghị |
| 3 | Xung đột mã lỗi E1003 | **Cấp mã mới cho các lỗi của ING-43** | `E1003` giữ nghĩa cũ ("không có tệp ở đường dẫn"), vì nó đã nằm trong thông báo người dùng đã thấy và trong ca đo đang xanh. Sáu lỗi mới của ING-43 nhận mã E1010–E1015 — xem DEV-249 |
| 4 | Xung đột mã lỗi E7001/E7002 của SCH-44 | **Mở họ E8xxx cho sơ đồ/EDA** | `E8001` netlist lệch CKM · `E8002` chưa có pinout đã duyệt. Họ `E7xxx` giữ nguyên nghĩa lịch sử/changeset |
| 5 | Thứ tự | **SCH-0 trước MEM-A** | Cờ tính năng · migration Store · so hồi quy hai chế độ — ba thứ mà SCH-44 §2.1 và §8 dựa vào, và MEM-A cũng dùng lại |
| 6 | Ngưỡng bố cục SCH | **Giữ mặc định** | ≤ 70 % net dùng nhãn · ≤ 3 đoạn gấp |

Điểm (2) kéo theo: K = 10 lượt và ngưỡng 70 % **giữ nguyên** cho tới khi có số đo, nhưng
sai lệch "10 message thay vì 10 lượt" (`loop.py:785`) phải sửa trong MEM-A.

---

## 4b. Hai điểm chờ anh chốt (README §3) — ĐÃ CHỐT, giữ lại để truy vết

**(1) ING-19 — tài liệu Office do người dùng tự viết gán tầng nào?**
Tài liệu đề xuất **NGƯỜI**. Mình đồng ý, và đây là lý do bằng mã: tầng NGƯỜI nằm trong
`TANG_DUNG_DUOC` (`compare.py:26`) nên vẫn so sánh được — nhưng trích dẫn của nó trỏ về
*anh*, không về datasheet, nên khi in ra người đọc thấy ngay nguồn là nội bộ. Nếu gán
BẠC thì nó đứng ngang hàng datasheet nhà sản xuất trong mọi bảng so sánh, và đó là thứ
sáu tháng sau không ai phân biệt được nữa.

**(2) MEM — K = 10 lượt và ngưỡng 70 %?**
Đề nghị **giữ nguyên** và không chỉnh cho tới khi có số đo. Hiện `compact_at = 0.70`
(`config.py:58`) và `_compact` giữ 10 **message** (`loop.py:785`) — lưu ý đây là một sai
lệch nhỏ cần sửa luôn: tài liệu nói 10 **lượt**, mà một lượt thường là 4–10 message.

**(3) SCH — ngưỡng % net dùng nhãn (≤ 70 %) và số đoạn gấp tối đa (3)?**
Đề nghị **giữ mặc định**: chưa có mạch mẫu nào chạy qua để nói khác.

**(4) MỚI — họ mã lỗi cho sơ đồ.** SCH-44 dùng `E7001`/`E7002`, nhưng cả hai đã có
nghĩa khác trong mã (hoàn tác, khôi phục). Đề nghị mở họ **E8xxx cho sơ đồ/EDA** và
dùng `E8001`/`E8002` — xem §2b.3. **Chờ anh gật.**

---

## 5. Thứ tự thực hiện đề nghị

Tài liệu đề nghị MEM-A → ING-A → MEM-B → ING-B → MEM-C → ING-C → ING-D → MEM-D → ING-E.
Mình đề nghị **đổi hai bước đầu**: **ING-A trước MEM-A**.

Lý do: ING-A là nửa ngày, sửa một lỗi anh gặp ngay hôm nay với chính tệp của anh, và
không đụng tới vòng lặp. MEM-A đụng vào đường đi của mọi tool_result — làm nó trước
nghĩa là mọi ca đo ING sau đó chạy trên một đường ống vừa thay. Làm ING-A trước thì khi
MEM-A thay đường ống, đã có 6 ca ING xanh để phát hiện hồi quy.

| Thứ tự | Bước | Nội dung chính | Ca đo | Công |
|---|---|---|---|---|
| 1 | **ING-A** | classify v3 (Office trước archive), ba mức hỗ trợ, E1001–E1008, giới hạn archive | ING01, 03–06, 14, 15 | 1 ngày |
| 2 | **MEM-A** | `ToolResultEnvelope` + bảng cắt 12 tool + nối blob; đồng hồ token 10 khối; C1 thật | MEM01, 02, 05 | 2 ngày |
| 3 | **MEM-B** | M1 lên đĩa + write-ahead; `memory.note/forget/status`; quy tắc EIDE.md + deny `fs.write`; `ledger.query` | MEM03, 10, 13, 14, 16, 18 | 2,5 ngày |
| 4 | **ING-B** | Bộ đọc Office; trích dẫn theo loại; PDF phái sinh | ING01–03 | 2 ngày |
| 5 | **MEM-C** | C2 + PreCompact/PostCompact + lược đồ 10 mục + ghim; UI A14.6; resume 5 bước | MEM04, 06–09, 11, 12, 17 | 3 ngày |
| 6 | **ING-C** | Bảng → Fact thống nhất; chuẩn hoá đơn vị đầy đủ; đối chiếu chéo | ING09, 12, 16 | 2,5 ngày |
| 7 | **ING-D** | EDA + cấu hình vendor + tầng CẤU HÌNH | ING07, 08 | 2 ngày |
| 8 | **MEM-D** | C3/C4; retention/gc; đo lường | MEM09, 15, 19, 24 | 1,5 ngày |
| 9 | **ING-E** | Hình/figure; đa ngôn ngữ; OCR nền | ING10, 11 | 2 ngày |
| 10 | **SCH-0** | *(mới)* Cơ chế cờ tính năng · lược đồ Store có `user_version` + `up()/down()` · xuất kết quả E2E ra JSONL để so hai lần chạy | — | 1,5 ngày |
| 11 | **SCH-A** | Module `eide/sch/` · `sch.compose/netlist/symbols` · E8001/E8002 · suy giảm R3 · hồi quy hai chế độ | SCH01–04, 14, 16, 18 | 3 ngày |
| 12 | **SCH-B** | `sch.place`/`write`/`render` nội bộ · khối A5.8 SVG tương tác | SCH05–09, 15, 17 | 4 ngày |
| 13 | **SCH-C** | Round-trip `export`/`import` · phân loại thay đổi · G-FILE | SCH10–13 | 2 ngày |
| 14 | **SCH-D** | Hierarchical sheets · symbol sinh từ Fact có xác nhận · gói vào snapshot | SCH07, SCH-16 | 2 ngày |

Tổng ước lượng **≈ 31 ngày công** (18,5 cho MEM+ING, 12,5 cho SCH). Lưu ý **SCH-A
chưa có đầu vào**: `sch.compose` cần CKM, mà CKM chưa được công cụ nào ghi (§2b.1).
Việc dựng CKM **không nằm trong** ba tài liệu bổ sung này — nó thuộc MDD-40 §C2 và
chưa được làm. Phải tính thêm, hoặc chốt rằng SCH đứng sau một bước CKM riêng.

Mỗi bước một commit, unit test cho phần xác định
(classify, envelope, C1, PostCompact, chuẩn hoá đơn vị), và chạy hồi quy bộ E2E hiện có
(`thu_g3.py` 39 ca · `thu_g4.py` 31 ca · `thu_g5.py` 35 ca) trước khi đóng bước.

---

## 6. Phụ thuộc mới cần thêm

| Thư viện | Cho | Bước |
|---|---|---|
| `python-docx`, `openpyxl`, `python-pptx` | Office | ING-B |
| LibreOffice headless (ngoài pip) | .doc/.xls/.ppt/.odt, docx→PDF | ING-B |
| `pdfplumber` (+ `camelot-py` khi có kẻ ô) | Bảng PDF | ING-C |
| `sexpdata` hoặc `kiutils` | `.kicad_sch` | ING-D |
| `pydevicetree` | `.dts` | ING-D |
| `pytesseract` + gói `vie`/`eng`/`chi_sim` | OCR | ING-E |
| `langdetect` | Nhận ngôn ngữ | ING-E |
| `skidl` | CKM → mô tả mạch | SCH-A |
| `kiutils` + `sexpdata` | Đọc/ghi `.kicad_sch` KiCad 8/9 | SCH-A/B |
| `networkx` | Bố cục theo module | SCH-B |
| `cairosvg` hoặc `resvg` | SVG → PDF/PNG | SCH-B |
| dữ liệu `kicad-symbols` (git tag có hash, qua G-DATA) | Ký hiệu chính thức | SCH-A |

Mỗi phụ thuộc là một thứ phải giải trình khi bảo vệ đề án, nên đề nghị: thêm theo bước,
không thêm trước; và mọi thứ chạy trong sandbox, không mạng (ING-43 §11).

**KHÔNG cài KiCad, KHÔNG gọi `kicad-cli`** (SCH-44, quyết định 25/09). Thư viện ký hiệu
chỉ là *dữ liệu* tải về có hash, không phải phần mềm cài đặt.

---

## 7. Điều gói bổ sung **không** nói mà mã đang làm khác

Ghi ở đây để không bị bỏ quên khi so tài liệu ↔ mã:

- **Tầng ĐỒNG trả về `chua_kiem_chung`** chứ không trả kết luận kèm cờ (DEV-244). ING-43
  §6 nói "hằng số trong mã → ĐỒNG-mã, chỉ để so" — hợp nhau, nhưng cách *thể hiện* là
  quyết định của mã, cần giữ khi thêm tầng CẤU HÌNH.
- **Nhánh dựa trên git, không phải copy-on-write** (DEV-245) — ảnh hưởng tới MEM-19 khi
  tính retention theo tham chiếu.
- **`snapshot.create` có chốt chặn "tên phải do người đặt"** (DEV-246) — cùng họ với
  MEM-14 "đề xuất ghi nhớ phải người đồng ý". Khi làm MEM-B nên dùng lại đúng cơ chế đó
  thay vì dựng cái mới.
