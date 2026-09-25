# EIDE v3.0 — GÓI BỔ SUNG (nâng cấp) cho Claude Code: Bộ nhớ (MEM-42) + Nạp & trích xuất tài liệu (ING-43)

Ngày: 25/09/2026 · Chủ sản phẩm: Vũ Trí Công · Repo: github.com/mobiluckvn/EIDE
Tiền đề: repo đã (hoặc đang) làm theo gói `docs/review-v3/` (EIDE-MDD-40 v3.0). Gói này **bổ sung**, không thay thế, MDD-40.

## 1. Gói này chứa gì

| Tệp | Vai trò |
|---|---|
| `docs/md/EIDE-MEM-42_Quan_ly_Bo_nho_va_Nen_Bo_nho.md` | **Thay thế mục B6 của MDD-40.** Năm tầng bộ nhớ M0–M4; 8 nguyên tắc; ngân sách ngữ cảnh 10 khối + 4 ngưỡng; quản lý theo lượt (cắt theo tool, blob, dedup, ghim); nén 5 cấp C0–C4 với lược đồ tóm tắt 10 mục và kiểm sau nén; EIDE.md quy tắc cứng; store/ledger/blob/retention; resume 5 bước; bộ nhớ người dùng; truy hồi; UI A14.6; sự cố; đo lường; MEM01–14; API `memory.*`; yêu cầu MEM-01…MEM-24 |
| `docs/md/EIDE-ING-43_Duong_ong_Nap_Tai_lieu_va_Trich_xuat.md` | **Chi tiết hoá mục C3 và tool ingest.file/fact.extract của MDD-40.** Sửa bỏ sót Office (**docx/xlsx/pptx** + .doc/.xls/.ppt/.odt), Markdown/HTML, EDA (.kicad_sch, Eagle, EasyEDA, BOM), cấu hình vendor (.ioc/sdkconfig/.dts/.ld/map → tầng CẤU HÌNH), hình trong tài liệu, đa ngôn ngữ, chuẩn hoá đơn vị; bộ phân loại theo nội dung (Office TRƯỚC archive); mã lỗi E1001–E1008; ING01–16; yêu cầu ING-01…ING-20 |
| `docs/docx/` | Bản Word của hai tài liệu (cho chủ sản phẩm) |
| `docs/img/` | 2 sơ đồ bộ nhớ (tầng, bậc thang nén) |
| `ui/` | Mô hình UI + HTML prototype + Excel ánh xạ **đã gồm** khối A14.6 (Bộ nhớ tác tử, 16 widget) và A3.6 (Nạp & trích xuất theo định dạng, 14 widget). Kiểm hai chiều: **242 yêu cầu ↔ 221 widget, ĐẠT**. Thay thế thư mục `ui/` của gói v3 |
| `diag/` | Trình sinh sơ đồ HTML/CSS (nếu cần vẽ thêm) |

## 2. Việc cần làm (theo thứ tự)

### Phần A — Bộ nhớ (MEM-42 §15, đi cùng G1/G2/G3/G6 của MDD-40)
1. **MEM-A** (cùng G1): `ToolResultEnvelope` + chính sách cắt theo tool (§5.1, 12 tool) + blob content-addressed `.eide/blobs/<sha256>` + đồng hồ token theo 10 khối + C1 thu gọn cơ học. Ca: MEM01, 02, 05.
2. **MEM-B** (cùng G2): `memory.note/forget/pin/status`, quy tắc EIDE.md (§7.1: trần 3 k, cấu trúc cố định, nguồn gốc dòng, quyền ghi theo mục), policy **deny `fs.write` vào EIDE.md**, `ledger.query`, write-ahead transcript + hash chuỗi. Ca: MEM03, 10, 13, 14, 16, 18.
3. **MEM-C** (cùng G3): C2 tóm tắt có cấu trúc (hook PreCompact rút cấu trúc vào M2 → LLM tóm theo lược đồ 10 mục → lắp lại transcript atomic) + **hook PostCompact hỏi ngược 3 câu, sai thì huỷ**; ghim tự động; UI A14.6; resume 5 bước (không còn `previous_session.summary = null`). Ca: MEM04, 06–09, 11, 12, 17.
4. **MEM-D** (cùng G6): C3 bậc thang, C4 khẩn cấp, subagent ngân sách riêng, retention/gc, đo lường §13. Ca: MEM09, 15, 19, 24.

### Phần B — Nạp & trích xuất (ING-43 §11, đi cùng G4 của MDD-40)
1. **ING-A**: `ingest.classify` v3 theo §3 (thứ tự **Office → archive → text**; `.docx` là zip có `word/` → DOCX, KHÔNG phải archive); mã lỗi E1001–E1008 có `message_vi + hint_for_agent + alternatives`; cây tệp trên tab Tài liệu. Ca: ING01, 03–06, 14, 15.
2. **ING-B**: bộ đọc Office (python-docx, openpyxl, python-pptx; LibreOffice headless cho .doc/.xls/.ppt/.odt); trích dẫn theo loại (heading/table/row · sheet!ô · slide); .docx → PDF phái sinh cùng doc_id khi cần số trang. Ca: ING01–03.
3. **ING-C**: bảng → Fact ứng viên thống nhất cho PDF/Office/MD/HTML (giá trị đọc bằng mã, mô hình chỉ ánh xạ tiêu đề cột); ô gộp/xoay/min-typ-max chung ô; chuẩn hoá đơn vị §5.2 (4R7, 3V3, µ/u, Ω, dải); đối chiếu chéo nguồn. Ca: ING09, 12, 16.
4. **ING-D**: EDA (.kicad_sch, Eagle, EasyEDA, BOM ↔ netlist) + cấu hình vendor (.ioc/sdkconfig/.dts/.ld/map) → Fact tầng **CẤU HÌNH** (không bao giờ là vế giới hạn vật lý). Ca: ING07, 08.
5. **ING-E**: hình → đoạn RAG "figure"; đa ngôn ngữ (OCR vie/eng/chi_sim); OCR nền. Ca: ING10, 11.

## 3. Điểm chờ chủ sản phẩm chốt (ghi vào gap report, không tự quyết)
- ING-19: tài liệu Office **do người dùng tự viết** (spec nội bộ, bảng đo) gán tầng **NGƯỜI** (đề xuất) hay BẠC?
- MEM: giá trị K (10 lượt giữ nguyên văn) và ngưỡng 70 % — giữ mặc định trừ khi đo thấy khác.

## 4. Nguyên tắc làm việc (như gói v3)
- Đọc `README_BO_SUNG.md` → đọc **toàn bộ** MEM-42 rồi ING-43 → rà mã → **gap report bổ sung** `docs/md/EIDE-GAP-44_Ra_soat_MEM_ING.md` (mỗi mục MEM-01…24, ING-01…20: CÓ / MỘT PHẦN / KHÔNG / KHÁC, tệp:dòng, ca đo, bước) → **dừng chờ gật** → làm theo thứ tự §2.
- Mỗi bước một nhánh/commit; unit test cho phần xác định (classify, envelope, compact C1, PostCompact, chuẩn hoá đơn vị); chạy 14 MEM + 16 ING + hồi quy 16 ca đang đạt của bộ 76 TC.
- Sai lệch mã ↔ tài liệu → `docs/md/EIDE-DEV-LOG.md` dạng `[DEV-2xx]`; không sửa tài liệu trong gói.
- Thay thư mục `ui/` của gói v3 bằng `ui/` của gói này (mô hình đã cộng dồn MEM + ING; kiểm tra Excel phải ra "ĐẠT — kín hai chiều").
- Ngôn ngữ: mã tiếng Anh; thông điệp người dùng, explain, tài liệu tiếng Việt.
