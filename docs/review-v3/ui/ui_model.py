# -*- coding: utf-8 -*-
"""Nguồn sự thật duy nhất cho UI v3: danh mục yêu cầu (từ EIDE-MDD-40 v3.0) + cây UI 3 cấp + ánh xạ hai chiều."""

# ---------------------------------------------------------------- YÊU CẦU
# (id, nhóm, mô tả, nguồn §)
REQS = []
def R(i, g, d, s): REQS.append(dict(id=i, group=g, desc=d, src=s))

for i, d in enumerate([
    "Datasheet là nguồn sự thật — mọi con số truy vết tới tài liệu/trang",
    "Bốn tầng tin cậy VÀNG/BẠC/NGƯỜI/ĐỒNG; ĐỒNG không là vế so sánh",
    "Kiểm kê xác định — tình trạng dự án do mã dựng, hiển thị cho người",
    "Hỏi một cụm, ≤ 2 lần/lượt, nói ra giả định",
    "Cổng an toàn đứng trước phép đoán (S0, G-OPS never_auto)",
    "Không đạt giả — tiêu chí của người; log rỗng ≠ đạt; phần chưa mô phỏng nói rõ",
    "Chỉ thị cho tác tử ≠ yêu cầu sản phẩm; rủi ro tách riêng",
    "Mọi thứ tác tử làm ra có dạng người hiểu được (lớp giải thích 6 trường)",
    "Mọi thay đổi là changeset hoàn tác được; sửa của người được tác tử biết; snapshot bất biến"], 1):
    R(f"N{i}", "Nguyên tắc", d, "MDD-40 A3")
for i, d in enumerate([
    "Một cửa vào: console.act / HumanAct", "Một dòng hội thoại: mọi HumanAct và lời tác tử trong transcript",
    "Giao diện không quyết — chỉ render SurfaceModel/Card", "Lõi không biết giao diện — chỉ thấy HumanAct + origin",
    "Có thứ tự, không trùng, khôi phục được (seq/resume)", "Cổng là thẻ riêng — text 'có' không mở cổng"], 1):
    R(f"I{i}", "Bất biến giao thức", d, "MDD-40 D1")
for i, d in enumerate(["Làm rõ ý tưởng & đề xuất giải pháp", "Tài liệu & Bản đồ tri thức mạch", "Môi trường công cụ", "Firmware",
                       "Mô phỏng", "Mạch thật", "Xuyên suốt (lịch sử, snapshot, sổ cái, tài liệu, báo cáo)"], 1):
    R(f"C{i}", "Chặng", d, "MDD-40 A4")
UC = ["Làm rõ ý tưởng và đề xuất phương án", "Từ phương án đến thiết kế mạch", "Sinh firmware, biên dịch, mô phỏng", "Nhập thiết kế có sẵn → mô phỏng → sửa code",
      "Nạp mạch thật và gỡ lỗi", "Rà soát thiết kế", "Hỏi đáp datasheet có trích trang", "Thay thế linh kiện", "Porting", "Phân tích log/crash/capture",
      "Kiểm thử tự động / HIL", "Tối ưu bộ nhớ/hiệu năng/điện", "Tính toán kỹ thuật", "Bảo mật & OTA", "Chuẩn bị sản xuất (NGOÀI PHẠM VI)",
      "Tài liệu & truy vết", "Quản lý phiên/dự án", "An toàn thao tác & kiểm soát quyền", "Sự cố của chính tác tử"]
for i, d in enumerate(UC, 1): R(f"UC{i:02d}", "Usecase", d, "Excel 76 TC")
for k, d in [("say", "Gõ tự do"), ("choose", "Chọn mục trong thẻ"), ("decide", "Quyết định cổng"), ("confirm", "Xác nhận/từ chối/sửa Fact hoặc nguồn"),
             ("edit", "Sửa hiện vật rồi lưu"), ("upload", "Kéo thả/chọn tệp"), ("stop", "Dừng khẩn"), ("undo", "Hoàn tác"), ("resume", "Tiếp tục sau sự cố/mở lại"),
             ("attend", "Chuyển tab/chọn hiện vật"), ("set", "Đổi thiết lập"), ("snapshot", "Ghi bản ưng ý"), ("branch", "Rẽ/chuyển/gộp nhánh")]:
    R(f"HA-{k}", "HumanAct", d, "MDD-40 D2")
for k, d in [("console.post", "Đăng lời tác tử + thẻ"), ("console.stream", "Stream văn bản"), ("card.resolve", "Đóng thẻ"), ("card.expire", "Thẻ hết hạn"),
             ("surface.set", "Thay mô hình bề mặt"), ("surface.patch", "Vá bề mặt"), ("surface.append", "Nối log/timeline"), ("surface.focus", "Đưa mắt tới vị trí"),
             ("surface.highlight", "Tô sáng"), ("surface.lock", "Soft-lock khối tác tử đang sửa"), ("surface.unlock", "Bỏ khoá"), ("run.update", "Thẻ Run"),
             ("notice", "Thông báo ngắn"), ("ui.set", "Thiết lập UI do lõi"), ("history.update", "Cập nhật changeset/snapshot/STALE"), ("explain.show", "Hiện lớp giải thích")]:
    R(f"UI-{k}", "UICommand", d, "MDD-40 D2")
for k, d in [("DATA", "Duyệt nguồn tài liệu"), ("DESIGN", "Chốt phương án/thiết kế"), ("SCOPE", "Duyệt kế hoạch việc lớn"), ("TOOL", "Cài công cụ"),
             ("QUAL", "Đổi tiêu chí/test"), ("FILE", "Ghi đè tệp người đã sửa"), ("FLASH", "Nạp firmware"), ("OPS", "Không đảo ngược (RDP/eFuse/erase)"),
             ("SAFE", "Điện lưới/nhiệt — cảnh báo đứng đầu"), ("HIST", "Hoàn tác lượt / khôi phục snapshot"), ("SNAP", "Tác tử đề xuất snapshot")]:
    R(f"G-{k}", "Cổng", d, "MDD-40 B4/E7")
ARTS = ["Đặc tả yêu cầu (REQ set)", "Phương án + phương án chọn", "ADR", "Fact", "Hộ chiếu chip", "Bản đồ tri thức mạch (KG)", "Pinout", "Sơ đồ khối",
        "Schematic/netlist", "BOM", "Phát hiện ERC/rà soát", "Kế hoạch (plan mode)", "Mã nguồn", "Diff của tác tử", "Kết quả build", "Tiêu chí mô phỏng",
        "Kết quả mô phỏng", "Phân tích capture/log/HardFault", "Dò board/nạp/verify", "Giả định đang dùng", "Báo cáo lượt", "Changeset", "Snapshot"]
for i, d in enumerate(ARTS, 1): R(f"AR{i:02d}", "Hiện vật (E2)", d, "MDD-40 E2")
for k, d in [("summary", "Tóm tắt 1 câu"), ("why", "Vì sao"), ("sources", "Nguồn bấm được + tầng"), ("diff_prev", "Khác bản trước"), ("next", "Việc tiếp theo"), ("confidence", "Tin được đến đâu")]:
    R(f"EX-{k}", "Lớp giải thích", d, "MDD-40 E3.1")
for k, d in [("why-button", "Nút 'Vì sao?' (0 token)"), ("explain-more", "Nút 'Giải thích thêm' → tác tử trả lời"), ("habit", "Thói quen trình bày theo người dùng")]:
    R(f"EX-{k}", "Lớp giải thích", d, "MDD-40 E3.3–3.4")
for i, d in enumerate(["Tóm tắt trước, chi tiết sau (gập)", "Mọi con số là liên kết ra nguồn", "Luôn nói khác biệt; băng STALE", "Chỉ ra đúng một việc cần người", "Không giấu thất bại — khối riêng"], 1):
    R(f"PR{i}", "Quy tắc trình bày", d, "MDD-40 E3.2")
for i, d in enumerate(["Sửa trên Surface bằng widget đúng loại; cảnh báo soft-lock", "Lưu → HumanAct edit qua Console; dòng '[Bạn] Sửa…'", "Kiểm lược đồ + 3-way merge; xung đột → thẻ hai bản",
                       "Changeset author=human; STALE hạ nguồn", "Đồng bộ: EIDE.md §Người vừa sửa; <human_edits>; Fact NGƯỜI", "Tác tử phản hồi: nhắc, hệ quả, đề nghị; không ghi đè"], 1):
    R(f"ED{i}", "Đồng bộ khi người sửa", d, "MDD-40 E4")
for k, d in [("content", "Sửa nội dung → STALE + đề nghị"), ("decision", "Sửa quyết định → ADR mới, hỏi nhánh"), ("presentation", "Sửa trình bày → không STALE"),
             ("reject", "Bác bỏ → EIDE.md §Đừng"), ("lockbroken", "Sửa tệp đang khoá → merge, không ghi đè")]:
    R(f"EDK-{k}", "Loại sửa của người", d, "MDD-40 E4.1")
for k, d in [("unit", "Changeset: tác giả, inverse ops, reversible"), ("undo1", "Hoàn tác một changeset"), ("undo2", "Hoàn tác cả lượt (G-HIST)"), ("undo3", "Về snapshot (G-HIST)"),
             ("irreversible", "Hành động không hoàn tác được — cảnh báo, đề nghị snapshot"), ("stale", "Đồ thị phụ thuộc + STALE + chấp nhận STALE"),
             ("branch", "Rẽ nhánh phương án; so sánh; gộp"), ("undo30s", "Hoàn tác lượt vừa xong trong 30 s không cần thẻ")]:
    R(f"CS-{k}", "Changeset & rollback", d, "MDD-40 E5")
for k, d in [("human", "Người ghi bản ưng ý bất cứ lúc nào"), ("propose", "Tác tử đề xuất sau mốc (G-SNAP)"), ("checkpoint", "Checkpoint ngầm trước run/hoàn tác"),
             ("release", "Snapshot release — điều kiện cho RDP/eFuse"), ("restore", "Khôi phục: liệt kê sẽ mất gì, vào nhánh mới"), ("compare", "So sánh hai snapshot"),
             ("resume-info", "Mở lại dự án nêu snapshot gần nhất + khoảng cách"), ("export", "Xuất gói release")]:
    R(f"SN-{k}", "Snapshot", d, "MDD-40 E6")
for k, d in [("VANG", "Tầng VÀNG — nền vàng, khoá, mở trang nguồn"), ("BAC", "Tầng BẠC — nền xám, nút Xác nhận"), ("NGUOI", "Tầng NGƯỜI — 'anh cho, chưa có tài liệu', nút Tìm tài liệu"), ("DONG", "Tầng ĐỒNG — nghiêng, 'chưa kiểm chứng'")]:
    R(f"T-{k}", "Tầng dữ liệu", d, "MDD-40 C1")
for i, d in enumerate(["Kích hoạt: nạp tệp hoặc thẻ đề nghị 3 lựa chọn", "Tìm: ứng viên có nguồn/phiên bản/hash", "Duyệt nguồn (G-DATA)", "Trích xuất: tiến trình, Fact ứng viên",
                       "Rà soát Fact: xác nhận hàng loạt/từng dòng", "Ghim hộ chiếu; đối chiếu ISA", "Phòng thủ: cảnh báo P-INJ; không tìm thấy nói thẳng"], 1):
    R(f"DS{i}", "Luồng datasheet", d, "MDD-40 C3")
for k, d in [("console3", "Console 3 cỡ"), ("tabs", "Tab 1–9 với summary + Vì sao + băng STALE + thanh tác giả"), ("history", "Tab 10 Lịch sử"),
             ("statusbar", "Thanh trạng thái: dự án, nhánh, chip, Fact theo tầng, chặng, snapshot + khoảng cách, STALE"), ("gatecards", "Thẻ cổng 11 loại"), ("runcard", "Thẻ Run: tiến trình, Hoàn tác 30 s, Ghi bản ưng ý")]:
    R(f"LY-{k}", "Bố cục", d, "MDD-40 E7")
for k, d in [("eide-md", "EIDE.md xem/sửa được (người & tác tử)"), ("inventory", "<inventory> hiển thị cho người"), ("skills", "Skill đang nạp / gợi ý"),
             ("plan", "Plan mode: kế hoạch có checkbox, duyệt"), ("subagent", "Subagent đang chạy hiển thị trong Run"), ("budget", "Ngân sách: tool/lượt, thời gian, ngữ cảnh"), ("assumptions", "Giả định đang dùng: xác nhận/bác bỏ")]:
    R(f"CX-{k}", "Ngữ cảnh tác tử", d, "MDD-40 B2/B5")
for k, d in [("autonomy", "Mức tự chủ A0–A4"), ("trusted", "Danh sách nguồn tin cậy"), ("habit", "Thói quen trình bày"), ("model", "Chọn mô hình theo vai trò"), ("remember", "'Tin' theo tool (R0–R2)")]:
    R(f"MM-{k}", "Bộ nhớ người dùng", d, "MDD-40 B6/E3.4")
for k, d in [("network", "Mất mạng: báo đúng lỗi mạng, lưu trạng thái"), ("timeout", "Quá 300 s: thả người, nói thật"), ("llm", "LLM lỗi/quá tải: retry rồi báo"), ("resume", "Tiếp tục sau sự cố")]:
    R(f"IN-{k}", "Sự cố (UC19)", d, "MDD-40 B1/UC19")
for k, d in [("inventory", "Kiểm kê toolchain/ISA/simulator/probe"), ("install", "Đề nghị cài (lệnh cụ thể) → G-TOOL"), ("build", "Biên dịch; warning giải thích; Flash/RAM vs Fact"),
             ("criteria", "Tiêu chí mô phỏng nêu trước"), ("simrun", "Chạy mô phỏng: log/VCD/verdict/không mô phỏng được"), ("test", "Unit test/HIL: đạt/không, độ phủ"),
             ("detect", "Dò board: cổng, probe, ID chip ↔ hộ chiếu; checklist khi không thấy"), ("flash", "Nạp: tóm tắt gì→đâu, hash → G-FLASH"), ("verify", "Verify; rút cáp giữa chừng → hướng khôi phục"),
             ("log", "Log UART/RTT có dấu thời gian"), ("debug", "Breakpoint, thanh ghi, backtrace"), ("dangerous", "Erase/option bytes/RDP/eFuse → G-OPS"),
             ("capture", "Giải mã capture I2C/SPI/UART/CAN"), ("hardfault", "Phân tích HardFault CFSR/PC → hàm"), ("calc", "Tính toán bằng mã, tham số có nguồn"),
             ("port", "Bảng ánh xạ ngoại vi khi porting"), ("opt", "Tối ưu: số đo trước/sau"), ("ota", "OTA A/B, chữ ký, rollback"), ("replace", "Thay thế linh kiện có phân tích ảnh hưởng"), ("trace", "Ma trận truy vết yêu cầu↔thiết kế↔mã↔test")]:
    R(f"TL-{k}", "Năng lực chuyên môn", d, "MDD-40 B3/UC")


MEM = ["Ngân sách ngữ cảnh cố định theo 10 khối; dự trữ 20 %", "Đồng hồ token theo khối hiển thị cho người; 4 ngưỡng 60/70/85/95 %",
       "Mọi ghi M2/M3 qua tool memory.note/store.* có changeset + provenance; fs.write EIDE.md bị deny", "C0: cắt theo chính sách tool, blob content-addressed, tham chiếu artefact id+version",
       "C1: stub/dedup/supersede/hết hạn 8 lượt; 0 token", "C2: PreCompact rút cấu trúc vào M2; tóm tắt 10 mục có trần; giữ K lượt + ghim; atomic swap",
       "Ghim tự động (decide/confirm/edit/snapshot/set, trả lời thẻ, kế hoạch duyệt, không đảo ngược); ghim thủ công", "PostCompact: 3 câu hỏi ngược từ ledger; sai → huỷ, K += 4, tối đa 2 lần",
       "C3 bậc thang có chuỗi hash; C4 khẩn cấp; thông báo [Hệ thống] sau nén; huỷ nén trong 24 h", "EIDE.md: trần 3 k, cấu trúc cố định, nguồn gốc dòng, quyền ghi theo mục, memory.prune",
       "Bản tóm tắt phiên xem/sửa được trên UI", "Người thấy cửa sổ ngữ cảnh hiện tại (khối, token, ghim)",
       "Quên có chủ đích: memory.forget → tombstone; không hồi sinh", "M3: danh sách trắng category; đề xuất ghi nhớ phải người đồng ý; không nhớ bí mật/suy đoán",
       "Subagent ngữ cảnh sạch, báo cáo ≤ 800 token; không C2", "ledger.query cho câu hỏi về quá khứ; tra trước khi trả lời",
       "Resume 5 bước; mô hình tự thuật; không summary null", "Write-ahead transcript; nén là giao dịch; hash chuỗi ledger/changeset",
       "Retention và gc blob theo tham chiếu", "Cache tài liệu M4 theo hash; Fact không đi theo cache; 'dùng lại Fact' tạo BẠC",
       "<facts> chọn theo thực thể 3 lượt gần, ưu tiên tầng và độ gần", "Skill không dùng 5 lượt bị bỏ khỏi ngữ cảnh",
       "Nhiều phiên cùng dự án: khoá tệp, phiên sau chỉ đọc", "Đo lường bộ nhớ ghi ledger và hiển thị trong Thiết lập"]
for i, d in enumerate(MEM, 1): R(f"MEM-{i:02d}", "Bộ nhớ & nén (MEM-42)", d, "EIDE-MEM-42")


ING = ["Phân loại theo nội dung; thứ tự Office → archive → text; lý do + độ tin cậy", "Ba mức hỗ trợ ĐẦY ĐỦ/MỘT PHẦN/KHÔNG hiển thị, kèm gợi ý thay thế",
       "Không bao giờ đưa tệp không phải archive vào archive.list", "Archive: bóc đệ quy có giới hạn; chọn tệp khi > 20; chống zip bomb",
       "Office .docx/.xlsx/.pptx đọc cấu trúc; ảnh nhúng OCR; định dạng cũ chuyển đổi", "Trích dẫn theo loại (page/bbox; heading/table/row; sheet!ô; slide); docx → PDF phái sinh",
       "Bảng (PDF/Office/MD/HTML) → Fact ứng viên; giá trị đọc bằng mã", "Ô gộp, bảng xoay, min/typ/max chung ô, Note → condition",
       "EDA: KiCad .net/.kicad_sch; Eagle/EasyEDA chuyển đổi; Altium từ chối đúng lý do; BOM đối chiếu netlist", "Cấu hình vendor (.ioc/sdkconfig/.dts/.ld/map) → Fact tầng CẤU HÌNH",
       "CẤU HÌNH không là vế giới hạn vật lý; mâu thuẫn với datasheet → phát hiện", "Hình → đoạn RAG figure; đọc hình bằng vision là ĐỒNG",
       "Đối chiếu chéo nguồn cùng key; quy tắc ưu tiên", "Chuẩn hoá đơn vị/ký hiệu bằng mã; giữ raw; condition có cấu trúc",
       "Đa ngôn ngữ: nhận diện, OCR đúng gói, key bí danh, embedding đa ngữ", "Mã lỗi E1001–E1008 có message_vi + hint + alternatives",
       "Giới hạn kích thước/trang; OCR nền có tiến trình", "Nội dung tài liệu là dữ liệu: untrusted, quét P-INJ, không chạy macro",
       "Gán tầng theo nguồn; Office tự viết → NGƯỜI (chờ chốt)", "Hằng số trong mã → ĐỒNG-mã, chỉ để so sánh"]
for i, d in enumerate(ING, 1): R(f"ING-{i:02d}", "Nạp & trích xuất (ING-43)", d, "EIDE-ING-43")


SCH = ["Sinh sơ đồ từ CKM qua SKiDL; mô hình viết SKiDL, mã kiểm", "Netlist sinh ra đẳng cấu với CKM; lệch → E7001, dừng", "Không bịa chân: pinout phải ≥ NGƯỜI; thiếu → E7002",
       "Style flat/hierarchical; chọn module", "Bố cục theo module với tiêu chí số; xác định, lặp lại được", "Render SVG có id theo ref/net",
       "Tương tác: ký hiệu → Fact/nguồn; net → tô sáng + ERC", "Renderer nội bộ là đường chính; suy giảm về sơ đồ khối",
       "Không cài/không gọi/không đề nghị cài KiCad trên máy; thư viện ký hiệu chỉ là dữ liệu qua G-DATA", "Diff sơ đồ bằng lời (E3)",
       "Xuất gói để mở ở máy khác; theo dõi mtime; Nạp lại", "Round-trip phân loại thay đổi: bố cục / giá trị / cấu trúc",
       "Thay đổi cấu trúc từ KiCad → thẻ hỏi, không ghi đè CKM im lặng", "Symbol lib chính thức đối chiếu Fact ≥ 95 %",
       "Symbol sinh từ Fact có ghi nguồn", "Gói sch vào snapshot/release", "Cờ features.schematic mặc định tắt; tắt = không có nhánh mã sch nào chạy",
       "Không đổi hợp đồng tool cũ; lược đồ chỉ cộng thêm; migration có down()", "Hồi quy hai chế độ giống 100 % trước khi merge",
       "uuid ổn định theo ref; giữ bố cục người đã sửa khi sinh lại", "Mọi tệp sch là changeset hoàn tác được; G-FILE khi ghi đè tệp người sửa", "PCB/Gerber vẫn ngoài phạm vi"]
for i, d in enumerate(SCH, 1): R(f"SCH-{i:02d}", "Sơ đồ KiCad (SCH-44)", d, "EIDE-SCH-44")


HIER = ["Module là nút cây có parent/kind/path; linh kiện là lá; độ sâu đệ quy; > 4 cảnh báo", "Port ở biên khối: tên, hướng, kiểu, ràng buộc; lá có Port = pin từ Fact",
        "Net theo phạm vi khối; nối chỉ Port của con trực tiếp hoặc Port lên cha", "flatten(cây) bằng mã là nguồn cho mọi tool phẳng; tool cũ không đổi",
        "Bất biến E8001–E8006 kiểm sau mỗi thay đổi", "Fact/REQ gắn được ở mọi cấp; ràng buộc theo cây kiểm bằng mã",
        "STALE theo cây: nội bộ không lan; Port lan tới cha và anh em nối", "Thư viện khối block@semver: manifest, params, instantiate có nguồn, 3 tầng lưu",
        "Trích khối từ mạch thành thư viện có kiểm khép kín", "SKiDL 1-1 với cây; netlist SKiDL = flatten",
        "KiCad hierarchical: sheet = khối, sheet pin = Port; flat = vùng + global label", "Round-trip .kicad_sch phân cấp → cây",
        "UI cây gập/mở, breadcrumb, sơ đồ khối con, bảng Port, ERC theo khối, kéo thả = changeset", "Lớp giải thích cho khối (7 câu)",
        "Migration cộng thêm có down(); dự án cũ chạy như trước", "Snapshot/hộ chiếu ghi block@semver đã dùng",
        "ERC/BOM/truy vết báo theo path khối", "Hồi quy toàn bộ giống 100 % sau migration"]
for i, d in enumerate(HIER, 1): R(f"HIER-{i:02d}", "Cây khối phân cấp (HIER-45)", d, "EIDE-HIER-45")

# ---------------------------------------------------------------- CÂY UI 3 CẤP
# L1 = vùng; L2 = khối; L3 = widget/hành động: (id_suffix, tên, loại, [req...])
# loại: display | action | edit | nav
UI = []
def A(i, name, kind, note=""): UI.append(dict(id=i, name=name, kind=kind, note=note, blocks=[])); return UI[-1]
def K(area, i, name, art="", reqs=()): b = dict(id=f"{area['id']}.{i}", name=name, art=art, reqs=list(reqs), items=[]); area['blocks'].append(b); return b
def W(block, i, name, kind, reqs, note=""): block['items'].append(dict(id=f"{block['id']}.{i}", name=name, kind=kind, reqs=list(reqs), note=note))

# --- A0 Thanh trạng thái
a = A("A0", "Thanh trạng thái", "bar")
k = K(a, 1, "Trạng thái dự án", reqs=["LY-statusbar", "N3"])
W(k, 1, "Tên dự án + nhánh hiện tại", "display", ["LY-statusbar", "CS-branch", "UC17"])
W(k, 2, "Chip đã ghim (ns.part@semver) + ISA", "display", ["AR05", "DS6"])
W(k, 3, "Fact theo tầng (VÀNG/BẠC/NGƯỜI/ĐỒNG)", "display", ["T-VANG", "T-BAC", "T-NGUOI", "T-DONG", "N2"])
W(k, 4, "Chặng hiện tại C1–C7", "display", ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "CX-inventory"])
W(k, 5, "Snapshot gần nhất + khoảng cách (changeset)", "display", ["SN-resume-info", "LY-statusbar"])
W(k, 6, "Số hiện vật STALE (bấm → Lịch sử)", "nav", ["CS-stale", "PR3"])
W(k, 7, "Mức tự chủ hiện tại (A0–A4) + mô hình", "display", ["MM-autonomy", "MM-model"])
W(k, 8, "Ngân sách lượt: tool/40 · giây/300 · ngữ cảnh %", "display", ["CX-budget", "IN-timeout"])
W(k, 9, "Trạng thái kết nối lõi/mạng", "display", ["IN-network", "I5"])

# --- A1 Console
a = A("A1", "Bàn giao tiếp (Console)", "panel", "Điểm giao tiếp người–máy duy nhất")
k = K(a, 1, "Dòng hội thoại (transcript)", reqs=["I2", "UI-console.post", "UI-console.stream"])
W(k, 1, "Dòng [Tác tử] (stream, markdown, liên kết mở tab)", "display", ["UI-console.post", "UI-console.stream", "PR2"])
W(k, 2, "Dòng [Bạn] cho MỌI HumanAct (kể cả thao tác trên tab)", "display", ["I1", "I2", "ED2"])
W(k, 3, "Dòng [Hệ thống] sự cố/thông báo", "display", ["UI-notice", "IN-network", "IN-llm", "IN-timeout"])
W(k, 4, "Báo cáo lượt (đã làm / bỏ / giả định / hoàn tác tới đâu / chi phí)", "display", ["AR21", "N4", "CX-budget"])
W(k, 5, "Phát lại (replay) transcript từ sổ cái", "action", ["I2", "I5", "UC17"])
k = K(a, 2, "Ô nhập", reqs=["HA-say"])
W(k, 1, "Gõ tự do (say) + Enter gửi", "edit", ["HA-say", "I1"])
W(k, 2, "Đính kèm tệp (upload)", "edit", ["HA-upload", "DS1"])
W(k, 3, "Lệnh nhanh: /dung /tiep-tuc /hoan-tac /snapshot /nhanh", "action", ["HA-stop", "HA-resume", "HA-undo", "HA-snapshot", "HA-branch"])
W(k, 4, "Gợi ý điền sẵn từ ngữ cảnh (chip, tệp, run vừa nhắc)", "display", ["N4", "CX-inventory"])
k = K(a, 3, "Thẻ đang chờ (Card)", reqs=["HA-choose", "UI-card.resolve", "UI-card.expire"])
W(k, 1, "Thẻ làm rõ (clarify) nhiều mục, mục bắt buộc/tuỳ chọn có default", "edit", ["N4", "HA-choose", "UC01"])
W(k, 2, "Thẻ đề nghị (proposal) 3 lựa chọn — ví dụ datasheet chip", "edit", ["DS1", "HA-choose", "UC02"])
W(k, 3, "Thẻ kế hoạch (plan) có checkbox bước + chi phí + giả định", "edit", ["CX-plan", "G-SCOPE", "AR12"])
W(k, 4, "Thẻ tiêu chí (criteria) form assert", "edit", ["TL-criteria", "AR16", "N6"])
W(k, 5, "Thẻ báo cáo (report) + Mở tab / Hoàn tác", "display", ["AR21", "CS-undo30s"])
W(k, 6, "Thẻ đã đóng/hết hạn (mờ, giữ nội dung)", "display", ["UI-card.resolve", "UI-card.expire"])
k = K(a, 4, "Thẻ Run (lượt đang chạy)", reqs=["UI-run.update", "LY-runcard"])
W(k, 1, "Tiến trình theo bước/tool (đang chạy, xong, bỏ, chờ cổng)", "display", ["UI-run.update", "PR5"])
W(k, 2, "Subagent đang chạy (tên, tool được phép, trạng thái)", "display", ["CX-subagent"])
W(k, 3, "Nút Dừng khẩn", "action", ["HA-stop", "N5", "UC19"])
W(k, 4, "Nút Hoàn tác lượt (30 s không cần thẻ)", "action", ["CS-undo30s", "HA-undo"])
W(k, 5, "Nút Ghi bản ưng ý", "action", ["SN-human", "HA-snapshot"])
W(k, 6, "Giả định đang dùng của lượt", "display", ["AR20", "N4", "CX-assumptions"])
W(k, 7, "Chi phí token/giây đến hiện tại", "display", ["CX-budget"])
W(k, 8, "Nút Tiếp tục (sau sự cố/dừng)", "action", ["HA-resume", "IN-resume"])
k = K(a, 5, "Kích cỡ Console", reqs=["LY-console3"])
W(k, 1, "Chuyển 3 cỡ (hẹp/vừa/rộng)", "action", ["LY-console3", "HA-set", "UI-ui.set"])

# --- A2 Yêu cầu & Giải pháp
a = A("A2", "Tab Yêu cầu & Giải pháp", "tab")
k = K(a, 1, "Đặc tả yêu cầu (có phiên bản)", "AR01", ["AR01", "C1", "UC01", "N7"])
W(k, 1, "Tóm tắt + Vì sao? + Giải thích thêm (lớp giải thích)", "display", ["EX-summary", "EX-why", "EX-why-button", "EX-explain-more", "N8", "UI-explain.show"])
W(k, 0, "Khối chuẩn: gập/mở chi tiết; một hành động tiếp theo nổi bật (next)", "display", ["PR1", "PR4", "EX-next"])
W(k, 2, "Bảng REQ (FR/NFR/UR): mô tả, tiêu chí đo, cột 'trích lời anh' (source_quote)", "display", ["AR01", "N7", "PR2"])
W(k, 3, "Sửa mô tả/tiêu chí inline + ô 'vì sao'", "edit", ["HA-edit", "ED1", "ED2", "EDK-content"])
W(k, 4, "Thêm / xoá REQ", "edit", ["HA-edit", "EDK-content"])
W(k, 5, "Đánh dấu 'không đúng ý tôi'", "edit", ["EDK-reject", "HA-confirm"])
W(k, 6, "Chọn phiên bản v1/v2… và diff bằng lời + tô màu", "display", ["EX-diff_prev", "PR3", "AR01"])
W(k, 7, "Băng STALE (hạ nguồn cần cập nhật) + nút Chấp nhận STALE", "action", ["CS-stale", "PR3", "ED4"])
W(k, 8, "Thanh tác giả (người/tác tử) + changeset", "display", ["N9", "AR22", "LY-tabs"])
k = K(a, 2, "Rủi ro (tách riêng khỏi FR)", "AR01", ["N7", "UC01"])
W(k, 1, "Bảng rủi ro: mô tả, mức, đề xuất, nguồn", "display", ["N7", "PR2", "EX-sources"])
W(k, 2, "Chấp nhận rủi ro có lý do", "edit", ["EDK-reject", "HA-confirm"])
k = K(a, 3, "Phương án (2–4) so sánh", "AR02", ["AR02", "UC01", "G-DESIGN"])
W(k, 1, "Bảng so sánh: kiến trúc, linh kiện, chi phí, độ khó, rủi ro, nguồn; điểm theo ràng buộc", "display", ["AR02", "PR2", "EX-confidence"])
W(k, 2, "Số ước lượng (ĐỒNG) tô nghiêng vs số có nguồn", "display", ["T-DONG", "N2"])
W(k, 3, "Chọn phương án (→ thẻ G-DESIGN)", "action", ["HA-choose", "G-DESIGN", "EDK-decision"])
W(k, 4, "Sửa chi phí/độ khó; thêm phương án bằng lời", "edit", ["HA-edit", "EDK-content"])
W(k, 5, "Rẽ nhánh để thử phương án khác song song", "action", ["CS-branch", "HA-branch"])
k = K(a, 4, "Quyết định (ADR)", "AR03", ["AR03"])
W(k, 1, "Thẻ ADR: context, options, choice, consequences, ai quyết", "display", ["AR03", "EX-why"])
W(k, 2, "Sửa/ghi đè quyết định (→ ADR mới có human_act_ref)", "edit", ["EDK-decision", "HA-edit"])
k = K(a, 5, "Mâu thuẫn & khả thi vật lý", "", ["UC01", "N1"])
W(k, 1, "Khối 'Mâu thuẫn phát hiện' bằng số có nguồn (băng thông, pin…)", "display", ["N1", "PR5", "UC01"])
W(k, 2, "Đề xuất nới ràng buộc nào", "display", ["EX-next", "N4"])
k = K(a, 6, "Ma trận truy vết", "", ["TL-trace", "UC16"])
W(k, 1, "REQ ↔ module ↔ mã ↔ test, cột 'đứt ở đâu'", "display", ["TL-trace", "UC16", "PR5"])

# --- A3 Tài liệu & Nguồn
a = A("A3", "Tab Tài liệu & Nguồn", "tab")
k = K(a, 1, "Nạp tài liệu", "", ["DS1", "HA-upload"])
W(k, 1, "Kéo thả / chọn tệp (PDF, zip, ảnh, netlist, mã)", "edit", ["HA-upload", "DS1", "UC04"])
W(k, 2, "Dán URL nguồn riêng", "edit", ["DS3", "HA-upload"])
W(k, 3, "Phân loại tệp theo nội dung + lý do lỗi đúng (Altium không hỗ trợ, tệp hỏng)", "display", ["UC04", "PR5"])
k = K(a, 2, "Ứng viên tìm được", "", ["DS2", "UC02"])
W(k, 1, "Bảng: tiêu đề, URL, nhà phát hành (nhãn nhà sản xuất/bên thứ ba), phiên bản, kích thước, hash", "display", ["DS2", "MM-trusted"])
W(k, 2, "Duyệt / Từ chối từng nguồn (→ thẻ G-DATA)", "action", ["G-DATA", "HA-confirm", "DS3"])
W(k, 3, "Không tìm thấy — khối riêng, đề xuất thay thế/xin tệp", "display", ["DS7", "PR5", "UC02"])
k = K(a, 3, "Trích xuất", "", ["DS4"])
W(k, 1, "Tiến trình: trang, bảng, OCR (điểm tin cậy), Fact ứng viên", "display", ["DS4", "UI-surface.append"])
W(k, 2, "Cảnh báo đỏ P-INJ (nội dung chứa chỉ dẫn lạ)", "display", ["DS7", "UC19"])
k = K(a, 4, "Phiên bản tài liệu", "AR05", ["UC02"])
W(k, 1, "Bảng khác biệt giữa hai phiên bản theo key; chọn bản dùng", "edit", ["UC02", "HA-confirm", "N1"])
W(k, 2, "Errata áp dụng (supersedes)", "display", ["N1", "AR04"])

k = K(a, 6, "Nạp & trích xuất theo định dạng (ING-43)", reqs=["ING-01", "ING-02"])
W(k, 1, "Cây tệp sau phân loại: loại, độ tin cậy, lý do, mức hỗ trợ + gợi ý thay thế", "display", ["ING-01", "ING-02", "ING-03"])
W(k, 2, "Chọn tệp nào nạp khi archive > 20 tệp; chống zip bomb", "edit", ["ING-04", "HA-choose"])
W(k, 3, "Xem Office theo cây tiêu đề / sheet / slide; trích dẫn heading/ô/slide", "display", ["ING-05", "ING-06"])
W(k, 4, "Bảng Fact ứng viên từ Office/Markdown/HTML với cột nguồn (Sheet!ô, Bảng#)", "display", ["ING-07", "ING-08", "DS5"])
W(k, 5, "Fact CẤU HÌNH (.ioc/.dts/.ld/map) tầng riêng + cảnh báo mâu thuẫn với datasheet", "display", ["ING-10", "ING-11"])
W(k, 6, "Hình trong tài liệu: ảnh + caption + OCR; nút 'Nhờ tác tử đọc hình' (ĐỒNG)", "action", ["ING-12", "T-DONG", "HA-say"])
W(k, 7, "Bảng khác biệt chéo nguồn (v1/v2, datasheet/.ld, BOM/netlist) + chọn bản", "edit", ["ING-13", "ING-09", "HA-confirm"])
W(k, 8, "Giá trị chuẩn hoá + chuỗi gốc (4R7 → 4,7 Ω)", "display", ["ING-14"])
W(k, 9, "Ngôn ngữ tài liệu + gói OCR; chọn lại", "edit", ["ING-15", "HA-set"])
W(k, 10, "Lỗi E1001–E1008 với gợi ý định dạng thay thế (Altium → netlist/PDF)", "display", ["ING-16", "UC04"])
W(k, 11, "Tiến trình OCR nền cho tài liệu lớn; giới hạn kích thước/trang", "display", ["ING-17", "UI-run.update"])
W(k, 12, "Cảnh báo untrusted/P-INJ; macro bị bỏ qua (E1006)", "display", ["ING-18", "DS7"])
W(k, 13, "Chuyển .docx → PDF phái sinh (cùng doc_id) để có số trang", "action", ["ING-06", "HA-say"])
W(k, 14, "Tầng theo nguồn: nhãn 'bên thứ ba', 'Office tự viết → NGƯỜI'; hằng số mã → ĐỒNG-mã", "display", ["ING-19", "ING-20", "T-NGUOI"])

k = K(a, 5, "Hỏi đáp tài liệu", "", ["UC07"])
W(k, 1, "Hỏi → trả lời kèm trang/mục/phiên bản; 'không có trong tài liệu' tách rõ tri thức chung", "display", ["UC07", "N1", "T-DONG", "PR5"])

# --- A4 Tri thức mạch
a = A("A4", "Tab Tri thức mạch", "tab")
k = K(a, 1, "Hộ chiếu chip", "AR05", ["AR05", "DS6"])
W(k, 1, "kv: họ, ISA, Flash/RAM, VDD, gói, tài liệu (phiên bản), số Fact theo tầng; ISA có toolchain chưa", "display", ["AR05", "TL-inventory", "EX-sources"])
W(k, 2, "Đổi phiên bản tài liệu dùng; thêm bí danh", "edit", ["HA-edit", "AR05"])
W(k, 3, "Thẻ đề nghị khi chưa có datasheet: Tìm mạng / Nạp tệp / Tri thức chung", "action", ["DS1", "HA-choose"])
k = K(a, 2, "Bảng Fact", "AR04", ["AR04", "N1", "N2"])
W(k, 1, "Cột: khoá, giá trị, đơn vị, điều kiện, Tầng (màu), Nguồn (mở trang PDF đúng bbox)", "display", ["AR04", "T-VANG", "T-BAC", "T-NGUOI", "T-DONG", "PR2"])
W(k, 2, "Xác nhận (BẠC→VÀNG) hàng loạt / từng dòng", "action", ["HA-confirm", "DS5", "T-BAC"])
W(k, 3, "Từ chối / sửa giá trị (→ NGƯỜI nếu không kèm tài liệu)", "edit", ["HA-confirm", "T-NGUOI", "ED3"])
W(k, 4, "Nút 'Tìm tài liệu chứng thực' trên Fact NGƯỜI", "action", ["T-NGUOI", "DS2"])
W(k, 5, "Hàng đợi rà soát Fact ứng viên + trích đoạn gốc bên cạnh", "display", ["DS5", "EX-sources"])
k = K(a, 3, "Đồ thị tri thức mạch", "AR06", ["AR06", "C2"])
W(k, 1, "Đồ thị tương tác: chip, chân, net, bus, nguồn; chọn nút → panel Fact + nguồn", "display", ["AR06", "HA-attend", "UI-surface.focus"])
W(k, 2, "Lọc theo bus/nguồn; chỗ 'đứt' (chưa có Fact) tô đỏ", "display", ["AR06", "PR5"])
W(k, 3, "Kéo nối net–chân → sinh đề xuất sửa netlist (không sửa KG trực tiếp)", "edit", ["HA-edit", "AR09"])
k = K(a, 4, "Kết quả so sánh (fact.compare)", "", ["N2", "UC06"])
W(k, 1, "Bảng: luật, vế A, vế B, kết luận, mức, hai trích dẫn; nhãn CHƯA KIỂM CHỨNG nếu có vế ĐỒNG", "display", ["N2", "T-DONG", "EX-sources"])
k = K(a, 5, "Thay thế linh kiện", "", ["UC08", "TL-replace"])
W(k, 1, "Danh sách thay thế xếp hạng: pin-to-pin/cần sửa mạch, khác biệt thông số, vòng đời (nếu có nguồn), ảnh hưởng", "display", ["TL-replace", "UC08", "PR5"])

# --- A5 Thiết kế
a = A("A5", "Tab Thiết kế", "tab")
k = K(a, 1, "Sơ đồ khối", "AR08", ["AR08", "UC02"])
W(k, 1, "Hình + danh sách khối ↔ REQ", "display", ["AR08", "EX-why"])
W(k, 2, "Đổi tên/ghép/tách khối (form module_graph); đổi tên = sửa trình bày, không STALE", "edit", ["HA-edit", "EDK-content", "EDK-presentation"])
k = K(a, 2, "Pinout", "AR07", ["AR07"])
W(k, 1, "Bảng chân: chức năng, AF, net, xung đột; hình chip", "display", ["AR07", "PR2"])
W(k, 2, "Đổi chức năng chân — dropdown chỉ AF có trong Fact", "edit", ["HA-edit", "N1", "ED1"])
k = K(a, 3, "Schematic / netlist", "AR09", ["AR09", "UC04"])
W(k, 1, "Netlist viewer + bảng net + hình (nếu có)", "display", ["AR09"])
W(k, 2, "Sửa netlist trong editor có kiểm lược đồ / nạp tệp mới", "edit", ["HA-edit", "HA-upload"])
W(k, 3, "Mã ≠ schematic: chỉ ra từng điểm, hỏi đâu là nguồn đúng", "action", ["UC04", "HA-confirm", "G-DESIGN"])
k = K(a, 4, "BOM", "AR10", ["AR10"])
W(k, 1, "Bảng: linh kiện, số lượng, datasheet (nút), lý do chọn, tình trạng", "display", ["AR10", "PR2"])
W(k, 2, "Thay linh kiện / sửa số lượng", "edit", ["HA-edit", "TL-replace"])
k = K(a, 5, "Phát hiện ERC / rà soát", "AR11", ["AR11", "UC06"])
W(k, 1, "Bảng theo mức: bằng chứng (số + nguồn), hậu quả, cách sửa; bấm → tô sáng net/dòng", "display", ["AR11", "UI-surface.highlight", "PR2"])
W(k, 2, "'0 phát hiện' nêu checklist đã rà", "display", ["PR5", "N6"])
W(k, 3, "Chấp nhận rủi ro có lý do / 'không phải lỗi'", "edit", ["EDK-reject", "HA-confirm"])
W(k, 4, "Chốt thiết kế (→ thẻ G-DESIGN)", "action", ["G-DESIGN", "HA-decide"])

k = K(a, 8, "Sơ đồ nguyên lý KiCad (SCH-44, cờ features.schematic)", "AR09", ["SCH-17", "SCH-18", "SCH-22"])
W(k, 1, "Nút 'Sinh sơ đồ KiCad' (flat/hierarchical, chọn module)", "action", ["SCH-01", "SCH-04", "HA-say"])
W(k, 2, "SVG tương tác (renderer nội bộ): bấm ký hiệu → Fact/nguồn/BOM; bấm net → tô sáng + ERC; hover chân → AF", "display", ["SCH-06", "SCH-07", "SCH-08"])
W(k, 3, "Băng chất lượng bố cục (0 chồng / 0 cắt / % nhãn) + nút 'Bố cục lại'", "action", ["SCH-05", "HA-say"])
W(k, 4, "Mức render đang dùng (nội bộ / sơ đồ khối); không bao giờ đề nghị cài KiCad", "display", ["SCH-08", "SCH-09"])
W(k, 5, "Diff sơ đồ v(n-1)→v(n) bằng lời + tô", "display", ["SCH-10", "EX-diff_prev"])
W(k, 6, "Xuất gói (mở ở máy có KiCad) · Nạp lại · thẻ hỏi khi CKM ≠ sơ đồ", "action", ["SCH-11", "SCH-12", "SCH-13", "HA-upload"])
W(k, 7, "Symbol sinh từ Fact: xem, xác nhận, sửa kiểu chân; symbol lib đối chiếu Fact", "edit", ["SCH-14", "SCH-15", "HA-confirm"])
W(k, 8, "Cảnh báo pinout chưa duyệt (E7002) / netlist lệch CKM (E7001) với nút nạp datasheet", "display", ["SCH-02", "SCH-03", "DS1"])
W(k, 9, "Xuất gói sch (.kicad_sch + .kicad_sym + .net + SVG) vào snapshot", "action", ["SCH-16", "SN-human"])
W(k, 10, "Giữ bố cục người đã sửa khi sinh lại (uuid theo ref); ghi đè tệp người sửa → G-FILE", "display", ["SCH-20", "SCH-21", "G-FILE"])
W(k, 11, "Kết quả hồi quy hai chế độ (cờ tắt/bật) trước khi bật tính năng", "display", ["SCH-19", "SCH-17"])


k = K(a, 9, "Cây khối phân cấp (HIER-45)", "AR06", ["HIER-01", "HIER-13"])
W(k, 1, "Cây gập/mở: mạch → khối → khối con → linh kiện (lá); breadcrumb path; cảnh báo depth > 4", "display", ["HIER-01", "HIER-13"])
W(k, 2, "Bấm khối → sơ đồ khối con + bảng Port (tên, hướng, kiểu, ràng buộc) + net cục bộ + ERC của khối + BOM con", "display", ["HIER-02", "HIER-03", "HIER-17"])
W(k, 3, "Bấm lá → Fact pinout/BOM; Port của lá = pin (từ Fact, không bịa)", "display", ["HIER-02", "N1"])
W(k, 4, "Kéo thả lá/khối giữa cha; thêm/bớt/nối Port (= thay đổi cấu trúc → changeset)", "edit", ["HIER-13", "HIER-05", "HA-edit"])
W(k, 5, "Lỗi bất biến E8001–E8006 với gợi ý (ví dụ 'khai Port')", "display", ["HIER-05", "HIER-03"])
W(k, 6, "Tô STALE theo nút cây + lý do (changeset); Chấp nhận STALE cho nút/nhánh", "action", ["HIER-07", "CS-stale"])
W(k, 7, "Ràng buộc theo cây: Iout ≥ Σ I, mức logic, trùng địa chỉ bus, pull-up theo bus — kết quả + 'chưa đủ dữ kiện'", "display", ["HIER-06", "N2", "PR5"])
W(k, 8, "Thêm khối từ thư viện (block@semver, params) → thẻ G-DESIGN; 'Lưu làm khối thư viện' có kiểm khép kín", "action", ["HIER-08", "HIER-09", "G-DESIGN"])
W(k, 9, "Lớp giải thích khối: làm gì / giao tiếp gì / gồm gì / dựa vào đâu / khác bản trước / tiếp theo / tin được đến đâu", "display", ["HIER-14", "N8"])
W(k, 10, "Chế độ xem: cây · phẳng (flatten) · sheet KiCad phân cấp; đối chiếu netlist SKiDL = flatten", "display", ["HIER-04", "HIER-10", "HIER-11"])
W(k, 11, "Nạp lại .kicad_sch phân cấp → cây; cấu trúc lệch → thẻ hỏi", "action", ["HIER-12", "SCH-13"])
W(k, 12, "Trạng thái migration dự án cũ + kết quả hồi quy; block@semver trong snapshot", "display", ["HIER-15", "HIER-18", "HIER-16"])

k = K(a, 7, "Chuẩn bị sản xuất", "", ["UC15"])
W(k, 1, "Nút Gerber/DRC/file gắp đặt hiển thị 'ngoài phạm vi v3' (không giả vờ có)", "display", ["UC15", "PR5"])
k = K(a, 6, "Bảo mật & OTA (thiết kế)", "", ["UC14", "TL-ota"])
W(k, 1, "Phân vùng A/B, chữ ký, rollback; kịch bản mất điện/gói sai chữ ký", "display", ["TL-ota", "UC14"])

# --- A6 Công cụ
a = A("A6", "Tab Công cụ", "tab")
k = K(a, 1, "Kiểm kê công cụ", "", ["TL-inventory", "C3"])
W(k, 1, "kv: toolchain theo ISA, phiên bản, mô phỏng, bộ nạp; khớp ISA chip; thiếu manifest nói thẳng", "display", ["TL-inventory", "N3", "PR5"])
k = K(a, 2, "Cài đặt", "", ["TL-install", "G-TOOL"])
W(k, 1, "Đề nghị cài: lệnh cụ thể theo HĐH, nguồn, kích thước → thẻ G-TOOL", "action", ["TL-install", "G-TOOL", "HA-decide"])
W(k, 2, "'Tin' gói này lần sau (R0–R2)", "action", ["MM-remember", "HA-set"])
W(k, 3, "Log cài đặt", "display", ["UI-surface.append"])
k = K(a, 3, "Skill & subagent", "", ["CX-skills", "CX-subagent"])
W(k, 1, "Skill đang nạp / gợi ý (mở SKILL.md)", "display", ["CX-skills"])
W(k, 2, "Danh sách subagent + tool được phép", "display", ["CX-subagent"])

# --- A7 Mã nguồn
a = A("A7", "Tab Mã nguồn", "tab")
k = K(a, 1, "Editor", "AR13", ["AR13", "C4", "UC03"])
W(k, 1, "Cây dự án + editor; hằng số gạch chân nguồn (hover → Fact)", "display", ["AR13", "N1", "PR2"])
W(k, 2, "Sửa tự do; Lưu = HumanAct edit (luôn tự duyệt)", "edit", ["HA-edit", "ED2", "EDK-content"])
W(k, 3, "Thanh soft-lock 'tác tử đang sửa' + cảnh báo lock_broken", "display", ["UI-surface.lock", "UI-surface.unlock", "EDK-lockbroken", "ED1"])
W(k, 4, "Xung đột → hai bản cạnh nhau, chọn từng đoạn", "edit", ["ED3", "G-FILE"])
k = K(a, 2, "Thay đổi của tác tử (diff)", "AR14", ["AR14"])
W(k, 1, "Diff viewer ≤ 200 dòng nguyên văn / tóm tắt; lý do; hằng số mới có nguồn?", "display", ["AR14", "EX-why", "N1"])
W(k, 2, "Hoàn tác từng diff", "action", ["CS-undo1", "HA-undo"])
W(k, 3, "Duyệt ghi đè tệp người đã sửa (thẻ G-FILE)", "action", ["G-FILE", "HA-decide"])
k = K(a, 3, "Kết quả build", "AR15", ["AR15", "TL-build"])
W(k, 1, "kv đạt/không; warning có giải thích; thanh Flash/RAM so với Fact budget", "display", ["AR15", "TL-build", "UC03"])
W(k, 2, "Vòng tự sửa: diff + lỗi cuối sau 3 lần", "display", ["UC03", "PR5"])
k = K(a, 4, "Porting & tối ưu", "", ["UC09", "UC12"])
W(k, 1, "Bảng ánh xạ ngoại vi cũ→mới; điểm không port được", "display", ["TL-port", "UC09"])
W(k, 2, "Số đo trước/sau tối ưu; hồi quy", "display", ["TL-opt", "UC12"])
k = K(a, 5, "Kiểm thử tự động", "", ["UC11", "TL-test"])
W(k, 1, "Kết quả unit test/HIL: đạt/không, độ phủ, flaky", "display", ["TL-test", "UC11"])

# --- A8 Mô phỏng
a = A("A8", "Tab Mô phỏng", "tab")
k = K(a, 1, "Tiêu chí (nêu trước)", "AR16", ["AR16", "N6", "TL-criteria"])
W(k, 1, "Form assert: loại, ngưỡng (đơn vị), timeout; mỗi assert đo REQ nào; ngưỡng từ đâu", "display", ["AR16", "EX-sources"])
W(k, 2, "Xác nhận tiêu chí (choose)", "action", ["HA-choose", "TL-criteria"])
W(k, 3, "Sửa ngưỡng sau khi có kết quả → thẻ G-QUAL (từ–đến–vì sao)", "action", ["G-QUAL", "N6", "HA-edit"])
k = K(a, 2, "Kết quả mô phỏng", "AR17", ["AR17", "TL-simrun", "UC03"])
W(k, 1, "Verdict theo từng assert + bằng chứng (dòng log/thời điểm VCD)", "display", ["AR17", "PR2", "N6"])
W(k, 2, "Log có dấu thời gian (follow)", "display", ["UI-surface.append"])
W(k, 3, "VCD viewer / ảnh", "display", ["AR17"])
W(k, 4, "Khối 'KHÔNG mô phỏng được' + đề xuất mock/HIL", "display", ["PR5", "N6", "UC03"])
W(k, 5, "Timeout/treo: vị trí vòng chờ", "display", ["UC03", "PR5"])
W(k, 6, "Log rỗng → 'không kết luận được'", "display", ["N6", "UC19"])
W(k, 7, "Chạy lại / Dừng", "action", ["HA-stop", "HA-say"])
W(k, 8, "Đề xuất snapshot sau khi đạt (thẻ G-SNAP)", "action", ["SN-propose", "G-SNAP"])

# --- A9 Mạch thật
a = A("A9", "Tab Mạch thật", "tab")
k = K(a, 1, "Dò board", "AR19", ["AR19", "TL-detect", "UC05"])
W(k, 1, "kv: cổng, probe, ID chip đọc được ↔ hộ chiếu (khớp/không)", "display", ["TL-detect", "AR19", "N1"])
W(k, 2, "Không thấy: checklist nguồn/cáp/driver/BOOT/NRST + nút Dò lại", "action", ["TL-detect", "PR5", "HA-say"])
k = K(a, 2, "Nạp & verify", "AR19", ["TL-flash", "TL-verify", "G-FLASH"])
W(k, 1, "Tóm tắt 'nạp gì (hash, kích thước) vào đâu' → thẻ G-FLASH", "action", ["G-FLASH", "HA-decide", "TL-flash"])
W(k, 2, "Kết quả verify; rút cáp giữa chừng → trạng thái + hướng khôi phục", "display", ["TL-verify", "PR5"])
W(k, 3, "Cảnh báo 'không hoàn tác được' + đề nghị snapshot trước", "display", ["CS-irreversible", "SN-propose"])
W(k, 4, "Bo đang chạy bản ≠ mã hiện tại (sau hoàn tác)", "display", ["CS-irreversible", "PR3"])
k = K(a, 3, "Gỡ lỗi", "", ["TL-log", "TL-debug", "UC05"])
W(k, 1, "Log UART/RTT có dấu thời gian", "display", ["TL-log", "UI-surface.append"])
W(k, 2, "Breakpoint, thanh ghi (SVD), backtrace", "display", ["TL-debug"])
W(k, 3, "Giả thuyết HW/SW + phép đo đề xuất", "display", ["UC05", "EX-next"])
k = K(a, 4, "Phân tích", "AR18", ["AR18", "UC10"])
W(k, 1, "Capture đã giải mã (I2C/SPI/UART/CAN) + đối chiếu timing", "display", ["TL-capture", "N1"])
W(k, 2, "HardFault: CFSR → loại lỗi, PC → hàm", "display", ["TL-hardfault"])
W(k, 3, "Bảng giả thuyết xếp hạng; 'không đủ dữ liệu' + cách thu thập lại", "display", ["PR5", "UC10"])
W(k, 4, "Đánh dấu giả thuyết đã loại; thêm quan sát (→ NGƯỜI)", "edit", ["HA-confirm", "T-NGUOI"])
k = K(a, 5, "Thao tác không đảo ngược", "", ["G-OPS", "TL-dangerous", "N5"])
W(k, 1, "Erase all / option bytes / RDP / eFuse → thẻ G-OPS riêng (never_auto)", "action", ["G-OPS", "HA-decide", "N5", "I6"])
W(k, 2, "Chặn nếu chưa có snapshot release", "display", ["SN-release", "N9"])
k = K(a, 6, "An toàn điện", "", ["G-SAFE", "UC18"])
W(k, 1, "Băng cảnh báo đứng đầu: NGẮT NGUỒN NGAY; điện lưới: cách ly/creepage", "display", ["G-SAFE", "N5"])
k = K(a, 7, "Tính toán kỹ thuật", "", ["UC13", "TL-calc"])
W(k, 1, "Công thức chạy bằng mã, tham số có nguồn/NGƯỜI, đơn vị, biên an toàn; thiếu tham số → hỏi đúng số", "display", ["TL-calc", "N1", "N4"])

# --- A10 Nhật ký
a = A("A10", "Tab Nhật ký lượt chạy", "tab")
k = K(a, 1, "Sổ cái", "", ["I2", "I5", "UC17"])
W(k, 1, "Timeline: HumanAct, tool_use/result, gate.decision, incident, chi phí", "display", ["I2", "UI-surface.append"])
W(k, 2, "Lọc theo lượt / tác giả / loại", "action", ["HA-attend"])
W(k, 3, "Xuất sổ cái", "action", ["UC16", "UC17"])
k = K(a, 2, "Sự cố", "", ["UC19"])
W(k, 1, "Danh sách sự cố: mạng, LLM, timeout, sandbox — trạng thái đã lưu, nút Tiếp tục", "action", ["IN-network", "IN-llm", "IN-timeout", "IN-resume", "HA-resume"])

# --- A11 Lịch sử
a = A("A11", "Tab Lịch sử", "tab")
k = K(a, 1, "Dòng thời gian changeset", "AR22", ["AR22", "CS-unit", "LY-history", "UI-history.update"])
W(k, 1, "Mỗi changeset: ai, cái gì, thuộc lượt nào, hoàn tác được không (lý do), STALE kéo theo", "display", ["AR22", "CS-unit", "CS-irreversible"])
W(k, 2, "Lọc theo tác giả / hiện vật / lượt", "action", ["HA-attend"])
W(k, 3, "Hoàn tác một changeset (cảnh báo chuỗi chạm cùng hiện vật)", "action", ["CS-undo1", "HA-undo"])
W(k, 4, "Hoàn tác cả lượt (thẻ G-HIST liệt kê sẽ mất gì)", "action", ["CS-undo2", "G-HIST", "HA-undo"])
W(k, 5, "Đặt snapshot tại changeset này", "action", ["SN-human", "HA-snapshot"])
W(k, 6, "Xem diff của changeset", "display", ["AR14", "AR22"])
k = K(a, 2, "Snapshot (bản ưng ý)", "AR23", ["AR23", "SN-human", "SN-propose"])
W(k, 1, "Dấu ★: tên, ghi chú, chip, tài liệu, REQ đã đạt, bằng chứng, kind checkpoint/release", "display", ["AR23", "SN-release"])
W(k, 2, "Ghi bản ưng ý (đặt tên, ghi chú, chọn gồm gì)", "edit", ["SN-human", "HA-snapshot"])
W(k, 3, "Khôi phục: thẻ G-HIST 'sẽ mất gì', gợi ý snapshot hiện tại, vào nhánh mới", "action", ["SN-restore", "CS-undo3", "G-HIST"])
W(k, 4, "So sánh hai snapshot: REQ, Fact, mã, Flash/RAM, sim, tài liệu", "display", ["SN-compare"])
W(k, 5, "Đánh dấu release / Xuất gói", "action", ["SN-release", "SN-export"])
W(k, 6, "Checkpoint ngầm (ẩn mặc định, bật hiện)", "display", ["SN-checkpoint"])
k = K(a, 3, "Nhánh", "", ["CS-branch", "HA-branch"])
W(k, 1, "Danh sách nhánh; tạo từ snapshot/changeset; chuyển", "action", ["CS-branch", "HA-branch"])
W(k, 2, "Gộp: hiện vật không xung đột tự gộp; còn lại chọn từng cái", "edit", ["CS-branch", "ED3"])
k = K(a, 4, "Hiện vật STALE", "", ["CS-stale"])
W(k, 1, "Danh sách STALE + lý do (changeset) + nút 'Lập kế hoạch cập nhật' / 'Chấp nhận'", "action", ["CS-stale", "CX-plan", "ED6"])

# --- A12 Thẻ cổng
a = A("A12", "Thẻ cổng (overlay)", "overlay", "Do lớp cấp quyền phát; đúng 1 mục; không default")
k = K(a, 1, "Thẻ cổng chung", reqs=["LY-gatecards", "I6", "HA-decide"])
W(k, 1, "Tiêu đề + mã cổng + mức rủi ro + hậu quả (consequences cố định từ hợp đồng tool)", "display", ["I6", "N5"])
W(k, 2, "Duyệt / Từ chối (decide)", "action", ["HA-decide", "I6"])
W(k, 3, "'Tin' (chỉ R0–R2)", "action", ["MM-remember"])
W(k, 4, "Hết hạn (R4: 10 phút) → mờ", "display", ["UI-card.expire"])
for i, (g, d) in enumerate([("DATA", "Danh sách nguồn chọn/từ chối"), ("DESIGN", "Phương án/thiết kế chốt"), ("SCOPE", "Kế hoạch bước + chi phí"), ("TOOL", "Lệnh cài + nguồn"),
                             ("QUAL", "Từ – đến – vì sao (bắt buộc)"), ("FILE", "Diff sẽ ghi đè bản của người"), ("FLASH", "Gì → đâu, hash, có snapshot chưa"),
                             ("OPS", "Hậu quả vĩnh viễn; không auto; cần release"), ("SAFE", "Cảnh báo đứng đầu, không tắt được"), ("HIST", "Sẽ mất gì / giữ gì"), ("SNAP", "Người đặt tên/ghi chú")], 5):
    W(k, i, f"Biến thể G-{g}: {d}", "display", [f"G-{g}"])

# --- A13 Thiết lập
a = A("A13", "Thiết lập", "modal")
k = K(a, 1, "Tự chủ & cấp quyền", reqs=["MM-autonomy", "UC18"])
W(k, 1, "Mức tự chủ A0–A4 (mô tả từng mức)", "edit", ["MM-autonomy", "HA-set"])
W(k, 2, "Danh sách 'đã tin' theo tool/gói/nguồn — xoá được", "edit", ["MM-remember", "HA-set"])
W(k, 3, "Nguồn tin cậy (tên miền nhà sản xuất)", "edit", ["MM-trusted", "HA-set"])
k = K(a, 2, "Mô hình", reqs=["MM-model"])
W(k, 1, "Chọn mô hình theo vai trò (chính, subagent, tóm tắt, embed)", "edit", ["MM-model", "HA-set"])
k = K(a, 3, "Trình bày", reqs=["EX-habit", "MM-habit"])
W(k, 1, "Mức chi tiết mặc định; diff nguyên văn?; thuật ngữ; tab mở theo chặng", "edit", ["EX-habit", "MM-habit", "HA-set"])
k = K(a, 5, "Chẩn đoán giao thức (dành cho phát triển)", reqs=["I3", "I4", "I5"])
W(k, 1, "Bộ xem UAP: HumanAct đã gửi / UICommand đã nhận (id, seq, surface.set/patch/append…)", "display", ["I3", "I4", "I5", "UI-surface.set", "UI-surface.patch"])
W(k, 2, "Chế độ truy vết: hiện mã UI (Ax.y.z) và yêu cầu ánh xạ trên mọi phần tử", "action", ["I3", "N8"])
k = K(a, 4, "Sandbox & ngân sách", reqs=["CX-budget", "UC18"])
W(k, 1, "Thư mục cho phép; mạng theo tool; tool/lượt; giây/lượt", "edit", ["CX-budget", "HA-set", "UC18"])
W(k, 2, "Cờ tính năng: features.schematic (mặc định tắt)", "edit", ["SCH-17", "HA-set"])

# --- A15 Màn hình & Giao diện nhúng
#
# Tab MỚI, thêm 10/10/2026 theo yêu cầu của chủ sản phẩm: "một số KIT hoặc phần cứng có cả màn
# hình, cần thêm năng lực thiết kế UI và màn hình trên UI để render màn hình do Agent thiết kế;
# khi thiết kế thì phải dùng cấu hình màn hình THẬT theo tài liệu/thiết kế KIT".
#
# Vì sao một tab RIÊNG chứ không phải một nhóm trong A5 "Thiết kế": A5 là thiết kế MẠCH (sơ đồ
# khối, pinout, netlist, BOM, ERC, cây phân cấp, chuẩn bị sản xuất) — khác hẳn chủ thể. Và khối
# chính của tab này là một khung vẽ tỉ lệ 1:1 với panel, tức một khối cần bề rộng riêng.
a = A("A15", "Màn hình & Giao diện nhúng", "tab")
k = K(a, 1, "Hồ sơ panel — đọc từ tài liệu, KHÔNG tự đặt", reqs=["N1", "PR2"])
W(k, 1, "Bảng: độ phân giải, hệ màu, đường chéo, DPI, driver, bus, cảm ứng — mỗi dòng kèm TRÍCH DẪN nguyên văn", "display", ["N1", "EX-sources"])
W(k, 2, "Trường tài liệu KHÔNG nói thì để trống và nói ra; không điền mặc định", "display", ["N2", "PR5"])
W(k, 3, "Bộ đệm khung cần bao nhiêu byte, có vừa RAM nội / RAM ngoài không", "display", ["N1"])
k = K(a, 2, "Bản thiết kế màn hình", reqs=["N6"])
W(k, 1, "Khung vẽ HTML tỉ lệ 1:1 với panel; màu là màu PANEL SẼ HIỆN sau lượng hoá, không phải màu gõ vào", "display", ["N6", "PR5"])
W(k, 2, "Bấm một phần tử → hỏi lõi về phần tử ấy", "action", ["HA-say"])
W(k, 3, "Bảng phần tử: id, loại, toạ độ, cỡ chữ", "display", ["PR2"])
k = K(a, 3, "Phép kiểm trên phần cứng THẬT", reqs=["N6", "PR5"])
W(k, 1, "Lỗi E11xx: ra ngoài biên · chữ dài hơn ô · cỡ chữ không có trong BSP · ký tự ngoài bảng font · chữ trùng màu nền sau lượng hoá", "display", ["N6"])
W(k, 2, "Cảnh báo W11xx: hai màu thành một màu trên panel · vùng chạm nhỏ hơn hướng dẫn nhân trắc (TỰ KHAI là hướng dẫn, không phải số đo)", "display", ["N1"])
W(k, 3, "'Không lỗi' luôn kèm danh sách ĐÃ KIỂM GÌ và KHÔNG kiểm được gì", "display", ["N6", "PR5"])
k = K(a, 4, "Tệp C sinh ra", reqs=["N6"])
W(k, 1, "Đường dẫn tệp + tên hàm vẽ; tệp tự khai TIỀN ĐỀ (BSP_LCD_Init…) và những gì nó KHÔNG sinh", "display", ["PR5"])
W(k, 2, "Nút 'Dịch thử' → build.compile; dịch được mới là bằng chứng", "action", ["HA-say", "N6"])

# --- A14 Dự án & bộ nhớ tác tử
a = A("A14", "Dự án & Bộ nhớ tác tử", "panel")
k = K(a, 1, "Dự án", reqs=["UC17"])
W(k, 1, "Mở / tạo dự án; không tạo lồng khi đang mở", "action", ["UC17", "N3"])
W(k, 2, "Mở lại: tác tử tự thuật 'đang ở đâu, đã quyết gì, làm gì tiếp' + snapshot gần nhất", "display", ["UC17", "SN-resume-info", "HA-resume"])
W(k, 3, "Xuất toàn bộ dự án", "action", ["UC17", "SN-export"])
k = K(a, 2, "EIDE.md", reqs=["CX-eide-md"])
W(k, 1, "Xem/sửa EIDE.md (mục tiêu, chip, ADR, giả định, quy ước, Đừng, Người vừa sửa)", "edit", ["CX-eide-md", "HA-edit", "ED5"])
W(k, 2, "§'Người vừa sửa' — tác tử đã nhắc chưa (acknowledged)", "display", ["ED5", "ED6", "N9"])
k = K(a, 3, "Kiểm kê (inventory) & giả định", reqs=["CX-inventory", "CX-assumptions"])
W(k, 1, "Bảng <inventory> đúng như tác tử thấy", "display", ["CX-inventory", "N3"])
W(k, 2, "Giả định đang dùng: xác nhận thành sự thật / bác bỏ", "edit", ["CX-assumptions", "AR20", "HA-confirm"])
k = K(a, 4, "Kế hoạch (plan mode)", "AR12", reqs=["CX-plan", "G-SCOPE"])
W(k, 1, "Kế hoạch đã duyệt: bước ✓/đang/chưa; đối chiếu 'đã làm'", "display", ["CX-plan", "AR12"])
W(k, 2, "Bỏ/thêm bước; sửa giả định", "edit", ["HA-edit", "CX-plan"])

k = K(a, 6, "Bộ nhớ tác tử (MEM-42)", reqs=["MEM-12", "MEM-02"])
W(k, 1, "Đồng hồ ngữ cảnh theo 10 khối (% và token, màu theo ngưỡng 60/70/85/95)", "display", ["MEM-01", "MEM-02", "CX-budget"])
W(k, 2, "Bản tóm tắt phiên hiện tại (10 mục): xem, sửa, ghim mục", "edit", ["MEM-06", "MEM-11", "HA-edit"])
W(k, 3, "Danh sách message ghim; ghim/bỏ ghim thủ công", "edit", ["MEM-07", "HA-set"])
W(k, 4, "Nén ngay (C1/C2) · Huỷ nén gần nhất (24 h)", "action", ["MEM-05", "MEM-09", "HA-say"])
W(k, 5, "Nhật ký nén: trước/sau, kiểm 3/3, chuỗi tóm tắt (C3)", "display", ["MEM-08", "MEM-09", "MEM-18"])
W(k, 6, "Bộ nhớ người dùng (memory.md): xem, sửa, quên từng dòng, xoá toàn bộ", "edit", ["MEM-13", "MEM-14", "MM-habit", "MM-remember"])
W(k, 7, "Đề xuất ghi nhớ của tác tử — Đồng ý / Không", "action", ["MEM-14", "HA-choose"])
W(k, 8, "Tìm trong lịch sử (ledger.query) — kết quả có ref", "action", ["MEM-16", "UC17"])
W(k, 9, "Cảnh báo EIDE.md vượt trần + đề xuất lược (memory.prune) — duyệt", "action", ["MEM-10", "MEM-03", "CX-eide-md"])
W(k, 10, "Dòng [Hệ thống] sau mỗi lần nén; tool_result lớn hiện 'đã cắt, xem blob'", "display", ["MEM-04", "MEM-09", "UI-notice"])
W(k, 11, "Khoá dự án khi phiên khác đang mở (chỉ đọc)", "display", ["MEM-23", "UC17"])
W(k, 12, "Chỉ số bộ nhớ: token/lượt, tần suất nén, kiểm đạt, số lần 'quên'", "display", ["MEM-24", "CX-budget"])
W(k, 13, "Resume: tác tử tự thuật + snapshot gần nhất + thẻ chờ (không summary rỗng)", "display", ["MEM-17", "SN-resume-info"])
W(k, 14, "Subagent: báo cáo ≤ 800 token, trạng thái 'dở dang' nếu chạm ngân sách", "display", ["MEM-15", "CX-subagent"])
W(k, 15, "Dùng lại Fact đã xác nhận từ dự án khác (→ BẠC có nguồn gốc); retention/gc blob", "action", ["MEM-20", "MEM-19", "HA-confirm"])
W(k, 16, "Cửa sổ <facts> hiện thực thể được chọn và lý do; skill hết hạn 5 lượt được báo", "display", ["MEM-21", "MEM-22", "CX-skills"])

k = K(a, 5, "Tài liệu & truy vết", reqs=["UC16"])
W(k, 1, "Sinh tài liệu thiết kế/hướng dẫn; đánh dấu phần lỗi thời sau khi sửa", "action", ["UC16", "CS-stale", "TL-trace"])

# ---------------------------------------------------------------- KIỂM HAI CHIỀU
def all_items():
    for a in UI:
        for b in a['blocks']:
            for w in b['items']:
                yield a, b, w

def check():
    req_ids = {r['id'] for r in REQS}
    used = {}
    bad = []
    for a, b, w in all_items():
        if not w['reqs']: bad.append(('UI không có yêu cầu', w['id']))
        for r in w['reqs']:
            if r not in req_ids: bad.append(('Yêu cầu không tồn tại', f"{w['id']} → {r}"))
            used.setdefault(r, []).append(w['id'])
        for r in b['reqs']:
            if r not in req_ids: bad.append(('Yêu cầu không tồn tại (khối)', f"{b['id']} → {r}"))
            used.setdefault(r, []).append(b['id'])
    missing = [r for r in req_ids if r not in used]
    return bad, missing, used

if __name__ == '__main__':
    bad, missing, used = check()
    print('L1', len(UI), 'L2', sum(len(a['blocks']) for a in UI), 'L3', sum(1 for _ in all_items()), 'REQ', len(REQS))
    print('bad', bad)
    print('missing', missing)
