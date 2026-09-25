# EIDE v3.0 — Brief giao việc cho Claude Code: RÀ SOÁT mã hiện tại so với thiết kế và SỬA

> **CẬP NHẬT 25/09/2026 — ĐỌC TRƯỚC:** Tài liệu thiết kế có hiệu lực duy nhất là **`docs/md/EIDE-MDD-40_v3.0_Thiet_ke_Tong_the.md`** (hợp nhất và thay thế AGD-32, AAD-33 v1/v2, UIP-34). Các tài liệu cũ chỉ để tham khảo chi tiết khi MDD-40 dẫn chiếu. Lộ trình làm theo **Phần G (G1→G7)** của MDD-40; gap report (§7 dưới) ánh xạ vào G1–G7. Bộ đo = 76 TC + 16 CX (Phần F).

Ngày: 24/09/2026 · Chủ sản phẩm: Vũ Trí Công · Repo: github.com/mobiluckvn/EIDE
Khung: Đề án tốt nghiệp ThS Kỹ thuật Điện tử — PTIT · Người hướng dẫn: TS. Nguyễn Trung Hiếu

> Tài liệu này là **điểm vào duy nhất**. Đọc nó trước, rồi đọc ba tài liệu thiết kế trong `docs/md/` theo thứ tự đã ghi ở §2. Nguyên tắc làm việc của dự án: **"đọc tài liệu và phát triển"** — tài liệu là nguồn sự thật; mọi sai lệch phát hiện khi sửa phải được ghi lại (xem §8) để cập nhật tài liệu, không được im lặng làm khác.

---

## 1. Nhiệm vụ

1. **Rà soát** toàn bộ mã lõi tác tử hiện tại (Python: `rpc.py`, `src/eide/**`, `caps.json`, `intent.schema.json`, `chains.yaml`…) và cầu giao diện, đối chiếu với thiết kế v1.4 trong gói này.
2. **Lập báo cáo sai lệch** (gap report) theo mẫu §7: mỗi mục thiết kế → có/không/một phần trong mã, ở tệp nào, dòng nào.
3. **Sửa mã theo Đợt 1** (§5) — các sửa đổi Đ1–Đ6 — rồi **chạy lại bộ 76 kịch bản** (`EideApp --kich-ban`) mỗi ca **5 lần**, ghi tỉ lệ đạt, cập nhật cột "Trạng thái / Kết quả thực tế" trong `test/Usecase_Test_Agent_Ky_Su_Nhung.xlsx`.
4. Không mở rộng phạm vi: **không** làm PCB/Gerber (UC15), **không** làm tài khoản/phân quyền (TC071). Đợt 2–4 chỉ làm khi Đợt 1 đã xanh và chủ sản phẩm gật.

## 2. Gói tài liệu (đọc theo thứ tự này)

| # | Tệp | Vai trò | Đọc phần nào trước |
|---|---|---|---|
| 1 | `README_REVIEW_BRIEF.md` (tệp này) | Nhiệm vụ, thứ tự, tiêu chí, mẫu báo cáo | Toàn bộ |
| 2 | `docs/md/EIDE-AGD-32_Thiet_ke_Tac_tu_Ky_su_Nhung_v1.4.md` | **Thiết kế sản phẩm v1.4**: 7 nguyên tắc, 7 chặng, Bản đồ tri thức mạch, luồng duyệt datasheet, máy trạng thái S0–S6 + sửa đổi Đ1–Đ6, 9 tab, 8 cổng, lộ trình | §2, §5, §6, §9 |
| 3 | `docs/md/EIDE-AAD-33_v2.0_Kien_truc_Tac_tu_theo_Vong_lap.md` (**ưu tiên**, thay thế v1.0) và `EIDE-AAD-33_Kien_truc_Tac_tu_Ky_su_Nhung_v1.0.md` (tham khảo chi tiết NLU/tool) | **Kiến trúc chi tiết** từ NLU đến thực thi: 6 lớp, DX, S0 rule engine, tách kênh, ý định/slot, DST, S3, Inventory, planner có tiền đề, Router, Policy, sổ cái, Fact/compare/constant-guard, LLM gateway, bộ nhớ, sandbox/build/sim/hardware, lược đồ JSON, 4 luồng tuần tự | §2, §3, §4, §10, §13 |
| 4 | `docs/md/EIDE-UIP-34_Giao_thuc_Dieu_khien_Giao_dien_v1.0.md` | **Giao thức giao diện UAP v1**: một cửa vào `console.act`/`HumanAct`, `UICommand`, `SurfaceModel`, `Card`, phiên/seq/resume, 12 ca tuân thủ UP01–UP12 | §1.2, §3, §4, §7, §11 |
| 5 | `test/Usecase_Test_23-09-2026.md` (+ `.xlsx` gốc) | 19 UC, 76 TC, **kết quả đo 23/09** với nguyên nhân từng ca, máy trạng thái v1.3 | Sheet "Test case" cột Kết quả thực tế + Ghi chú |
| 6 | `docs/img/*.png` | 5 sơ đồ (6 lớp, NLU, máy trạng thái, tô-pô giao thức, luồng xác nhận Fact) | Khi cần hình dung |
| 7 | `docs/docx/` | Bản Word của 2, 3, 4 (để chủ sản phẩm đọc; nội dung giống bản .md) | Không cần |

Thứ tự ưu tiên khi tài liệu mâu thuẫn nhau: **AAD-33 > AGD-32 > UIP-34 > bộ hồ sơ v1.2 cũ** (SRS-02, SAD-03, CDS-12, CXD-10, MEM-11, APD-08, DPS-09, UXD-13). Bộ v1.2 vẫn có hiệu lực cho những gì ba tài liệu mới không nói tới. Phát hiện mâu thuẫn → ghi vào §8, không tự chọn.

## 3. Bối cảnh đo lường — vì sao phải sửa

Kết quả 23/09/2026 (76 TC): **16 đạt / 51 không đạt / 7 bị chặn / 2 bỏ qua**; P1: 12 đạt / 27 không đạt.

Các ca ĐẠT gần như đều là ca "biết dừng, biết từ chối, biết hỏi xác nhận" (S0, G-OPS, P-SAFE, P-QUAL, chống bịa, RAG có trích trang, ERC netlist). Các ca KHÔNG ĐẠT phần lớn **chết trước khi chạm tới chuyên môn**, vì đường định tuyến:

| Cụm nguyên nhân gốc | Số ca | Ca tiêu biểu | Sửa bằng |
|---|---|---|---|
| Đường dẫn **bịa từ chính câu người dùng** → `archive.list` E2000/E1000 | 11 | TC016, TC023, TC072 | **Đ1** |
| Chặn ở câu hỏi "Chưa ghim hộ chiếu chip — chip nào?" dù chip đã nêu / chưa cần | 6 | TC002, TC008, TC015 | **Đ3** |
| Chỉ thị cho tác tử hoặc rủi ro bị ghi thành **yêu cầu sản phẩm (FR)** | 4 | TC003, TC017, TC024, TC028 | **Đ4** |
| Thiếu tiền đề trong chuỗi (planner không chèn `arch.decompose` trước `diagram.*`) | 3 | TC009, TC013, TC064 | **Đ5** |
| Không tất định / hai nhánh ý định / tạo dự án LỒNG | 3 | TC001, TC004, TC043 | **Đ1, Đ6** |
| Tệp không phải archive bị đưa vào `archive.list` ("không nhận ra định dạng nén" cho .net/.c/.sh/.PcbDoc) | 5 | TC023, 025, 026, 062, 070 | **Đ2** |
| Nền biên dịch – mô phỏng chưa dựng | ~12 | TC015–021, 052, 055, 058–060 | Đợt 3 |
| Năng lực chuyên môn chưa có (capture, HardFault, port, OTA, tối ưu, tính toán) | ~10 | TC049, 050, 047, 054, 056 | Đợt 3–4 |
| Khôi phục ngữ cảnh: đường đi đã sửa, **nội dung** chưa có (`previous_session.summary = null`) | 3 | TC065, 066, 074 | Đợt 2 |

Các phát hiện đã biết trong mã (từ bảng "May trang thai" v1.3 — **kiểm lại, đừng tin mù**):
- Đường sống `rpc.py::_chat_send`: chặn xác định → `parse_intent` → `ground` → `fill_defaults` → `orchestrate` → CHẠY. **Không có cổng làm rõ nào.**
- `chat.clarify` ĐÃ hiện thực và ĐÃ nối — nhưng nối trong `src/eide/orchestrator.py` (69 dòng) **không ai import** → mã chết.
- `intent.schema.json`: `slots.path` là **chuỗi đơn** do mô hình điền → mất tệp thứ hai (TC011), không tất định (TC043); `${_path}` phụ thuộc mô hình.
- `is_big` được ghi vào ledger rồi **không dùng ở đâu**.
- `parse_intent`: `< 0,6 → unknown`, `≥ 0,6 → coi như chắc` — không có dải ngờ.
- Kho ISA manifest chỉ có `armv7e-m`, `avr8`, `rv32imac` — thiếu `armv7-m` (STM32F103, TC018).
- `search.web` cần SearXNG (`make searxng` đã sẵn) — chưa dựng.
- `target.erase_fuse` chưa hiện thực (TC035 đạt nhờ S0 nói thẳng điều đó — giữ hành vi này).
- Bộ dữ liệu mẫu `mach-khong-loi` từng có lỗi (C4 pin 1 trên hai net) — đã sửa; kiểm lại trước khi đo TC040.

## 4. Bảy nguyên tắc bất biến — mọi sửa đổi phải giữ (AGD-32 §2)

| Mã | Nguyên tắc | Kiểm bằng ca |
|---|---|---|
| N1 | **Datasheet là nguồn sự thật**: mọi con số dùng để so sánh/quyết định/sinh mã phải truy vết tới tài liệu có phiên bản + trang + trích đoạn | TC008, 042, 075 |
| N2 | **Ba tầng tin cậy Vàng/Bạc/Đồng**: so sánh chỉ hợp lệ khi cả hai vế ≥ Bạc; vế Đồng (tri thức chung LLM) → "CHƯA KIỂM CHỨNG", không được dùng để quyết định tự động | TC013, 021, 031 |
| N3 | **Kiểm kê thì xác định** (S2, 0 token); mô hình không bao giờ tự mô tả tình trạng dự án | TC008, 065 |
| N4 | **Hỏi một cụm**, tối đa 2 vòng, nói ra giả định | TC004, 057 |
| N5 | **Cổng an toàn đứng trước phép đoán** (S0 đọc câu người gõ, không đọc ý định) | TC007, 035, 036, 068, 069 |
| N6 | **Không đạt giả**: không sửa tiêu chí/test để ép đạt; log rỗng ≠ đạt | TC019, 022, 076 |
| N7 | **Chỉ thị cho tác tử ≠ yêu cầu sản phẩm**: lệnh điều khiển tác tử không bao giờ thành FR | TC003, 017, 024, 028 |

Các ca đang ĐẠT (TC005, 007, 022, 031, 032, 035, 036, 037, 038, 040, 042, 063, 068, 069, 075, 076) là **hồi quy bắt buộc giữ** — chạy chúng sau mỗi thay đổi.

## 5. Đợt 1 — Sửa đổi Đ1–Đ6 (làm theo thứ tự này)

Chi tiết thiết kế từng mục: AGD-32 §6 (bảng Đ1–Đ6) và AAD-33 §2–§3. Dưới đây là tóm tắt hành động + nơi có khả năng phải sửa (**xác minh bằng cách đọc mã, đường dẫn dưới đây là dự đoán từ tài liệu đo, không phải sự thật**).

### Đ1 — Bộ trích xác định (DX) TRƯỚC `parse_intent`; `slots.paths` là MẢNG
- Mới: `src/eide/nlu/dx.py` — regex/từ điển trích `paths[]`, `chips[]` (family_patterns + registry), `numbers[]` (số + đơn vị → SI), `urls[]`, `ids[]` (REQ/ADR/UC/TC/run), `back_refs`, `quoted[]`. 0 token. Unit test riêng.
- `intent.schema.json` → v2: `slots.paths: array`, mỗi slot có `origin ∈ {dx, user, model, default}`; **slot `origin=model` không bao giờ được dùng làm đường dẫn/mã chip để chạy nút**, chỉ để điền sẵn câu hỏi.
- Hợp nhất slot theo ưu tiên: DX > câu trả lời người ở S3 > mô hình > `fill_defaults`. Router ghi `origin` vào sổ cái.
- Mọi nơi dùng `${_path}` → đọc từ `slots.paths` (DX). Không tồn tại → `exists=false` → S3 hỏi, **không chạy `archive.list` trên đường dẫn không tồn tại**.
- Mở khoá: TC010, 011, 016, 020, 023, 043, 045, 047, 052, 054, 058, 070, 072.

### Đ2 — Phân loại tệp theo nội dung (`ingest.classify`)
- Magic bytes + đuôi → `archive | netlist | source | script | log | capture | pdf | image | unknown`; mỗi loại một bộ đọc; `archive.list` **chỉ** nhận `archive`.
- Lỗi phải đúng lý do: "định dạng Altium (.PcbDoc) không hỗ trợ — xuất netlist/PDF" (TC025); "tệp cụt/hỏng" (TC026); script → quét tĩnh lệnh phá hoại/đọc khoá riêng → ASK (TC070).
- Mở khoá: TC023, 025, 026, 062, 070.

### Đ3 — Hộ chiếu chip: từ CHẶN sang ĐỀ NGHỊ (`passport.propose` + luồng G-DATA)
- Khi DX thấy chip mà store chưa có datasheet → **thẻ đề nghị** 3 lựa chọn: *Tìm trên mạng* / *Tôi nạp tệp* / *Dùng tri thức chung – nhãn Đồng*; các nút không cần Fact ≥ Bạc (đề xuất phương án, sơ đồ khối) **vẫn chạy**; nút cần Fact đánh dấu chờ.
- KHÔNG tự ghim tên chip trần vào `ns.part@semver` (lỗi "câu trả lời sai tệ hơn ô trống", DEV-183). Ghim chỉ sau khi có tài liệu (luồng AGD-32 §5, 7 bước).
- `doc.search_web` (SearXNG, ưu tiên tên miền nhà sản xuất, thu metadata + hash) → `doc.approve` (G-DATA) → `fact.extract` → hàng đợi rà soát → `passport.pin`; đối chiếu ISA manifest, thiếu → nói thẳng (TC018) và **bổ sung manifest `armv7-m`**.
- Mở khoá: TC002, 008, 015, 027, 046, 048.

### Đ4 — Tách kênh DIRECTIVE / PRODUCT / DATA (`nlu.split_channels`)
- Một lời gọi mô hình nhỏ với lược đồ (AAD-33 §2.4). `req.elicit` **chỉ** nhận `product_text`; `directive_text` đi S1b; `DATA` thành literal slot.
- Rủi ro tác tử tự phát hiện → `spec.risk[]`, không bao giờ thành FR (TC003).
- Mở khoá: TC003, 017, 024, 028.

### Đ5 — Bộ lập kế hoạch có tiền đề (`plan.with_preconditions`)
- Mỗi capability trong `caps.json` khai báo `requires[] {artefact, min_count, tier_min?, how_to_get?}` và `produces[]`. Planner đối chiếu với Inventory ∪ produces của nút trước; thiếu + có `how_to_get` → chèn nút (đệ quy ≤ 3, phát hiện vòng); thiếu không có `how_to_get` → gap cho S3.
- Nút hỏng E2xxx (thiếu tiền đề) lúc chạy → quay về S3, không chết tại chỗ; giữ DEV-216 (`on_ask: skip` không kéo lượt xuống).
- `is_big` (đã ghi ledger) **phải được dùng**: `is_big OR nút > 7` → thẻ kế hoạch chờ gật.
- Mở khoá: TC009, 013, 064.

### Đ6 — Không tạo dự án lồng; ba dải tin cậy; nối lại S3
- `project.create` chỉ khi Inventory thấy **chưa có dự án đang mở**; câu mô tả ý tưởng trong dự án đang mở → UC01 (`req.elicit`), không tạo `mach-thong-minh/cai-mach-thong-minh`.
- `parse_intent` confidence 3 dải: `> 0,85 → S2`; `0,60–0,85 → S3` với mục đầu là xác nhận ý định (kèm `alt_intents`); `< 0,60 → S3` hỏi thẳng, không chạy gì.
- **Nối `chat.clarify` (S3) vào đường sống** `rpc.py::_chat_send` theo máy trạng thái S0→S1→S2→S3→S4→S5→S6 (AGD-32 sheet "May trang thai", AAD-33 §1.3). Xoá/hợp nhất `src/eide/orchestrator.py` mã chết.
- Nhiệt độ parse/clarify/report = 0, seed cố định nếu nhà cung cấp hỗ trợ.
- Mở khoá: TC001, 004, 006, 073.

### Cũng trong Đợt 1
- Dựng SearXNG (`make searxng`); `search.web` mất mạng → lỗi **mạng** (E3xxx), lưu trạng thái, tiếp tục được (TC072).
- Bộ chạy kịch bản: **mỗi ca 5 lần**, ghi tỉ lệ đạt + thời gian + token + số lần hỏi lại; chấm theo lần chạy đầy đủ, không theo lần đẹp nhất (Huong dan sheet).

## 6. Tiêu chí nghiệm thu Đợt 1 (AGD-32 §9.3, AAD-33 §12)

- [ ] Không còn ca P1 "Không đạt" **vì lý do định tuyến** (đường dẫn bịa, chặn hộ chiếu, chỉ thị thành FR, thiếu tiền đề, dự án lồng).
- [ ] 16 ca đang đạt vẫn đạt (hồi quy).
- [ ] Cùng câu + cùng store → cùng DX/S0/S2/S4 (100 %); S1/S3 ≥ 90 % cùng intent/gaps qua 5 lần.
- [ ] 0 hành động G-OPS/G-SAFE không xác nhận; 0 lệnh chạy ngoài sandbox.
- [ ] `intent.schema.json` v2 + `dx.schema.json` + `inventory.schema.json` + `clarify.schema.json` + `plan.schema.json` + `capability.schema.json` có trong `schemas/` và được kiểm trong CI (AAD-33 §10).
- [ ] Mỗi ca đạt phải chỉ ra được **cơ chế thiết kế nào** bảo vệ nó (ghi vào cột Ghi chú) — không có ca "đạt nhờ tai nạn" (như TC070 v1.3).
- [ ] Sổ cái ghi `s0.decision, s1.intent (kèm origin từng slot), s2.inventory, s3.gaps, s4.plan, gate.decision` cho mọi lượt.

## 7. Mẫu báo cáo sai lệch (gap report) — nộp trước khi sửa

Tạo `docs/md/EIDE-GAP-35_Ra_soat_ma_v1.4.md`, một bảng, mỗi dòng một mục thiết kế:

| ID | Tài liệu §  | Yêu cầu thiết kế (1 câu) | Trạng thái trong mã: CÓ / MỘT PHẦN / KHÔNG / KHÁC | Tệp:dòng | Ca đo liên quan | Hành động đề xuất | Đợt |
|---|---|---|---|---|---|---|---|
| G-001 | AAD-33 §2.2 | DX trích `paths[]` bằng regex trước parse_intent | KHÔNG | — | TC011, TC043 | Tạo `nlu/dx.py` | 1 |
| G-002 | AAD-33 §1.3 | Đường sống đi qua S3 | KHÁC (S3 có nhưng không được nối) | `src/eide/orchestrator.py:1-69`, `rpc.py::_chat_send` | TC004 | Nối theo máy trạng thái | 1 |
| … | | | | | | | |

Tối thiểu phải rà các mục sau (đánh số theo tài liệu): AAD-33 §2.1–2.7 (NLU), §3.1–3.6 (điều phối), §4 (12 năng lực mới/đổi), §5.2–5.4 (Fact/tầng/compare/constant-guard), §6.3 (đầu ra có cấu trúc, retry, nhiệt độ), §7.2 (resume bằng đọc sổ cái), §8.1 (sandbox), §8.2 (tool manager + ISA manifest), §8.4 (SimBackend + tiêu chí trước), §8.5 (target.detect đối chiếu ID chip), §10 (14 lược đồ); UIP-34 §1.2 (I1–I6), §3 (11 HumanAct), §4 (14 UICommand), §7 (hello/seq/resume), §11 (UP01–UP12); AGD-32 §5 (7 bước duyệt tài liệu), §8 (8 cổng).

## 8. Nhật ký sai lệch tài liệu ↔ mã (bắt buộc)

Trong khi rà/sửa, mọi chỗ mã **phải** khác tài liệu (vì lý do kỹ thuật thực tế) ghi vào `docs/md/EIDE-DEV-LOG.md` theo dạng:

```
[DEV-2xx] <ngày> <tệp> — <tài liệu §> nói X; mã làm Y; vì sao; đề nghị cập nhật tài liệu: có/không
```

Tiếp nối dãy DEV-2xx hiện có (DEV-183, 200–207, 212, 215, 216 đã dùng). Không sửa tài liệu thiết kế trong gói này — chủ sản phẩm sẽ cập nhật từ nhật ký.

## 9. Cách làm việc

1. Đọc §2 theo thứ tự. Đọc **toàn bộ** AAD-33 §2–§3 trước khi chạm vào `rpc.py`.
2. Nộp gap report (§7) **trước** khi sửa; chờ chủ sản phẩm gật hoặc làm tiếp nếu được uỷ quyền "làm hết Đợt 1".
3. Sửa theo thứ tự Đ1 → Đ2 → Đ3 → Đ4 → Đ5 → Đ6. Mỗi Đ là một nhánh/commit riêng, có unit test cho phần xác định (DX, classify, planner, S0 YAML) và chạy hồi quy 16 ca đạt.
4. Sau mỗi Đ: chạy các ca "mở khoá" của Đ đó ×5, cập nhật Excel (cột vàng: Trạng thái, Kết quả thực tế, Người test = "Claude Code", Ngày test, Ghi chú = cơ chế bảo vệ).
5. Kết thúc Đợt 1: tổng hợp bảng thống kê (sheet Thong ke tự tính) + danh sách DEV-2xx mới + đề xuất Đợt 2.
6. Ngôn ngữ: mã, tên biến tiếng Anh; thông điệp cho người dùng, thẻ, báo cáo **tiếng Việt** (thuật ngữ kỹ thuật tiếng Anh giữ nguyên, kèm giải thích khi lần đầu xuất hiện).
7. Không cài/đổi toolchain hệ thống ngoài sandbox của dự án; không xoá dữ liệu mẫu trong `du-lieu/`.

## 10. Phạm vi ngoài (không làm dù thấy dễ)

- PCB/Gerber/DRC (UC15) · tài khoản/phân quyền (TC071) · thay đổi ngôn ngữ giao diện Swift (chỉ sửa **cầu giao thức** nếu cần cho UAP) · Đợt 2–4 (Fact store đầy đủ, SimBackend, hardware) — chỉ khi được gật.

---
*Gói này tổng hợp từ: EIDE-AGD-32 v1.0, EIDE-AAD-33 v1.0, EIDE-UIP-34 v1.0 (đều ngày 24/09/2026) và Usecase_Test_Agent_Ky_Su_Nhung.xlsx (đo 23/09/2026).*

---

## PHỤ LỤC (25/09/2026) — Kiến trúc v2.0 theo vòng lặp thay thế Đ1–Đ6

Chủ sản phẩm quyết định (25/09): tổ chức lại tác tử theo **vòng lặp tác tử kiểu Claude Code** (EIDE-AAD-33 **v2.0**). Khi làm theo v2.0:
- **Bỏ** các sửa đổi Đ1 (DX/slot), Đ4 (tách kênh), Đ5 (planner có tiền đề), Đ6 (dải tin cậy) — chúng thuộc kiến trúc máy trạng thái cũ.
- **Giữ** Đ2 (phân loại tệp theo nội dung → trong tool `ingest.file`) và Đ3 (luồng duyệt datasheet → skill `datasheet-onboarding` + tool `doc.approve_request`), S0 (→ hook `UserPromptSubmit`), Policy (→ `policy.yaml` + lớp cấp quyền), Inventory (→ system-reminder).
- Thứ tự làm mới: **4 bước ở AAD-33 v2.0 §12**; thước đo vẫn là 76 TC × 5 lần qua HumanAct; mục tiêu P1 ≥ 80 % (không tính bị chặn).
- Gap report (§7) vẫn nộp trước; cột "Hành động đề xuất" ánh xạ vào 4 bước §12 của v2.0 thay vì Đ1–Đ6.
