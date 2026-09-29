**EIDE — QUẢN LÝ BỘ NHỚ VÀ NÉN BỘ NHỚ CỦA TÁC TỬ**

Năm tầng bộ nhớ · ngân sách ngữ cảnh · quản lý theo lượt · nén năm cấp có kiểm chứng · bộ nhớ dự án và người dùng · truy hồi · giao diện · kiểm thử

*Mã tài liệu EIDE-MEM-42 · v1.0 · 25/09/2026 · bổ sung và thay thế mục B6 của EIDE-MDD-40 v3.0*

|                    |                                                                                                                                                                                                                                       |
|--------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Mã tài liệu**    | EIDE-MEM-42 (Memory Architecture & Compaction) v1.0                                                                                                                                                                                   |
| **Quan hệ**        | Chi tiết hoá và thay thế mục B6 "Bộ nhớ và nén ngữ cảnh" của EIDE-MDD-40 v3.0; bổ sung yêu cầu MEM-01…MEM-24 vào danh mục yêu cầu và khối A14.6 vào mô hình UI (ui_model.py)                                                          |
| **Ngày**           | 25/09/2026                                                                                                                                                                                                                            |
| **Đề tài**          | PHÁT TRIỂN PHẦN MỀM NHÚNG CÓ ỨNG DỤNG TRÍ TUỆ NHÂN TẠO (AI)                                |
| **Khung**          | Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — PTIT · Người hướng dẫn: TS. Nguyễn Trung Hiếu                                                                                                                                       |
| **Tác giả**        | Vũ Trí Công                                                                                                                                                                                                                           |
| **Bằng chứng đo**  | TC074 (ngữ cảnh dài quên quyết định), TC065 (previous_session.summary = null), TC028 (repo \> 500 tệp), TC008 (mô hình tự mô tả dự án → REQ bịa), TC006 (đổi yêu cầu giữa chừng), TC043 (không tất định), TC072/073 (sự cố giữa lượt) |
| **Mẫu tham chiếu** | Cách Claude Code quản lý ngữ cảnh: CLAUDE.md, tool result lớn lưu ra tệp, auto-compact có tóm tắt cấu trúc, ghim quyết định của người, subagent ngữ cảnh sạch                                                                         |

***Lịch sử sửa đổi***

| **Phiên bản** | **Ngày**   | **Nội dung**                                                                                                                                                                                                                                                                                                                                                                                                         | **Người sửa** |
|---------------|------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| v1.0          | 25/09/2026 | Bản đầu: rà soát B6; 5 tầng M0–M4; 8 nguyên tắc bộ nhớ; ngân sách ngữ cảnh theo khối và 4 ngưỡng; quản lý theo lượt (cắt, blob, dedup, ghim, hết hạn); nén 5 cấp C0–C4 với lược đồ tóm tắt 10 mục và kiểm sau nén; EIDE.md chi tiết; store/ledger/blob/retention; bộ nhớ người dùng và quyền quên; tri thức toàn cục; truy hồi; giao diện bộ nhớ (A14.6); sự cố; đo lường; MEM01–MEM14; API và bố cục tệp; lộ trình. | VTC           |

**1. Rà soát: bộ nhớ trong MDD-40 v3.0 còn thiếu gì**

Mục B6 của MDD-40 nêu 5 tầng bộ nhớ, ngưỡng nén 70 %, hook PreCompact và cách mở lại dự án — đủ làm định hướng nhưng chưa đủ để hiện thực. Rà soát theo bằng chứng đo và theo cách Claude Code làm, các khoảng trống sau phải được lấp:

| **\#** | **Khoảng trống**                                                                          | **Hậu quả nếu bỏ qua**                                                       | **Bằng chứng** | **Giải quyết ở** |
|--------|-------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|----------------|------------------|
| 1      | Chưa có ngân sách token theo khối; ngữ cảnh "phình" không kiểm soát                       | Mô hình quên quyết định đầu phiên; chi phí tăng tuyến tính theo độ dài phiên | TC074          | §4               |
| 2      | tool_result lớn (fs.read cả tệp, log dài, ingest hàng trăm trang) đi thẳng vào transcript | Vài tool call là hết cửa sổ; repo \> 500 tệp không làm được                  | TC028          | §5.1             |
| 3      | Chưa định nghĩa cái gì KHÔNG được nén mất (quyết định, giả định, sửa của người, thẻ chờ)  | Nén xong tác tử làm ngược ý người                                            | TC006, TC074   | §3 P3, §6.3 ghim |
| 4      | Nén chưa có kiểm chứng; không biết nén có làm mất gì                                      | Lỗi im lặng, chỉ lộ ra khi người hỏi lại                                     | TC074          | §6.6             |
| 5      | Tóm tắt do mô hình sinh không có lược đồ; previous_session.summary rỗng                   | Mở lại dự án không thuật lại được đã quyết gì                                | TC065          | §6.4, §7.5       |
| 6      | Chưa tách "nhớ" khỏi "đọc": mô hình có thể mô tả tình trạng dự án từ trí nhớ              | REQ bịa (REQ_HW_I2C…)                                                        | TC008          | §3 P1            |
| 7      | EIDE.md chưa có quy tắc kích thước, cấu trúc, nguồn gốc dòng, và ai được ghi mục nào      | Tệp phình, mâu thuẫn, mô hình tự thêm "Đừng"                                 | —              | §7.1             |
| 8      | Bộ nhớ người dùng chưa có ranh giới (được nhớ gì, không nhớ gì, quên thế nào)             | Rò rỉ, nhớ sai, không xoá được                                               | —              | §8               |
| 9      | Chưa có cơ chế truy hồi có chủ đích cho câu hỏi về quá khứ ("quyết định ban đầu là gì?")  | Mô hình đoán thay vì tra                                                     | TC074          | §10              |
| 10     | Người không nhìn thấy bộ nhớ tác tử (đang nhớ gì, vừa nén gì)                             | Không tin, không sửa được                                                    | —              | §11              |
| 11     | Sự cố giữa lượt: chưa nói transcript được ghi thế nào để resume không mất                 | Mất công việc                                                                | TC072, TC073   | §12              |
| 12     | Chưa đo: tần suất nén, tỉ lệ kiểm đạt, số lần "quên"                                      | Không biết bộ nhớ có tốt lên không                                           | —              | §13              |

**2. Mô hình bộ nhớ năm tầng**

![](../img/m1_tiers.png)

*Hình 1. Năm tầng bộ nhớ (trái) và cách chúng đổ vào cửa sổ ngữ cảnh mỗi lượt (phải)*

| **Tầng**             | **Chứa gì**                                                                                                                  | **Hình thức**                                       | **Sống bao lâu**                      | **Ai ghi**                                   | **Ai đọc**                                      | **Độ tin cậy**                                              |
|----------------------|------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|---------------------------------------|----------------------------------------------|-------------------------------------------------|-------------------------------------------------------------|
| M0 Working           | tool_result thô của lượt, stream delta, card đang mở, cờ cancel                                                              | RAM                                                 | Một lượt                              | Vòng lặp                                     | LLM (qua M1)                                    | Là dữ liệu thô của tool — tin theo tool                     |
| M1 Transcript phiên  | messages đã qua chính sách cắt/ghim/nén; bản tóm tắt phiên; con trỏ blob                                                     | JSONL (.eide/sessions/\<id\>/transcript.jsonl)      | Phiên; giữ để resume; lưu trữ 90 ngày | Vòng lặp; compact                            | LLM mỗi lượt; resume                            | Không phải nguồn sự thật — chỉ là dòng hội thoại            |
| M2 Bộ nhớ dự án      | EIDE.md; Store (REQ, phương án, ADR, module, Fact, hộ chiếu, tài liệu, netlist, BOM, criteria, run); Ledger; Changeset; Blob | Markdown + SQLite + JSONL + git + content-addressed | Vĩnh viễn theo dự án                  | CHỈ qua tool (changeset); người qua HumanAct | \<inventory\>, fact.query, ledger.query, resume | Nguồn sự thật (N1, N3, N9)                                  |
| M3 Bộ nhớ người dùng | Mức tự chủ, "tin" theo tool/gói/nguồn, nguồn tin cậy, thói quen trình bày, đường toolchain, chip hay dùng                    | ~/.eide/memory.md + settings.json                   | Xuyên dự án; người xoá được           | Policy engine, UI, memory.note(scope=user)   | Policy, prompt assembly                         | Do người; không có tầng                                     |
| M4 Tri thức toàn cục | Registry chip, ISA manifest, skill, hiến pháp, cache tài liệu theo hash                                                      | Gói có phiên bản (chỉ đọc)                          | Theo phiên bản gói                    | Bản phát hành; cache tài liệu do ingest      | DX, skill.load, doc cache                       | Theo nguồn gói; cache tài liệu giữ nguyên tầng của tài liệu |

**Điểm then chốt:** chỉ M2 là nguồn sự thật. Transcript (M1) là "những gì đã nói", không phải "những gì đúng"; vì vậy nén M1 không bao giờ được làm mất sự thật — sự thật đã nằm ở M2 trước khi nén (hook PreCompact bảo đảm điều đó).

**3. Tám nguyên tắc bộ nhớ**

| **Mã** | **Nguyên tắc**                                                                                                                                                                  | **Hiện thực bằng gì**                                                                             | **Ca canh**  |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|--------------|
| P1     | Không nhớ thay cho đọc: tình trạng dự án, số liệu, quyết định luôn đọc từ M2 qua tool/khối xác định; mô hình không được kể lại từ trí nhớ transcript khi có thể tra             | \<inventory\>, \<facts\>, ledger.query; hiến pháp §3; store.req_create cần source_quote           | TC008, TC074 |
| P2     | Mọi ghi vào bộ nhớ dài hạn (M2, M3) đi qua tool, có changeset, có nguồn gốc dòng                                                                                                | memory.note(scope, category, text, provenance) → changeset; EIDE.md dòng có \[run-xx\]/\[h-xxxx\] | MEM03        |
| P3     | Nén không mất: quyết định, giả định, Fact, sửa của người, thẻ chờ, kế hoạch đã duyệt, hành động không đảo ngược — phần có cấu trúc rút vào M2 trước, nén chỉ chạm văn bản tự do | Hook PreCompact; ghim (pin) message; lược đồ tóm tắt 10 mục                                       | MEM05–07     |
| P4     | Nén phải kiểm được: sau nén, hỏi ngược từ ledger; sai thì huỷ nén                                                                                                               | Hook PostCompact (§6.6)                                                                           | MEM08        |
| P5     | Bộ nhớ có tuổi và độ tin cậy: mọi mục ghi ngày, nguồn, tầng; mục cũ bị đề nghị lược, không tự xoá                                                                               | Trường ts/provenance/tier; memory.prune đề xuất                                                   | MEM10        |
| P6     | Người thấy và sửa được bộ nhớ tác tử: EIDE.md, memory.md, bản tóm tắt phiên, "đang nhớ gì trong ngữ cảnh"                                                                       | Khối A14.6 Bộ nhớ tác tử (UI); memory.status                                                      | MEM11–12     |
| P7     | Quên có chủ đích: người xoá được bất kỳ mục nào; mục "Đừng" chỉ người tạo/xoá; mục đã quên không được tự hồi sinh từ transcript cũ                                              | memory.forget → tombstone trong ledger; compact kiểm tombstone                                    | MEM13        |
| P8     | Ngân sách cố định theo khối: mỗi khối ngữ cảnh có trần; vượt thì nén khối đó, không "mượn" của khối khác; trả lời + tool_result lượt này luôn có 20 % dự trữ                    | Prompt assembly (§4)                                                                              | MEM01–02     |

**4. Ngân sách ngữ cảnh**

**4.1. Bố cục cửa sổ theo khối**

| **Khối**                                   | **Nguồn**                                                     | **Trần (token)**      | **Cache?**           | **Khi vượt trần**                                                       |
|--------------------------------------------|---------------------------------------------------------------|-----------------------|----------------------|-------------------------------------------------------------------------|
| 1 Hiến pháp                                | PRS-16 v3                                                     | 2 000                 | Có (prompt caching)  | Không xảy ra (cố định)                                                  |
| 2 Lược đồ tool hiển thị                    | tool registry (nạp trễ)                                       | 4 000                 | Có                   | Ẩn bớt tool ít dùng; mô hình gọi tool.search                            |
| 3 EIDE.md                                  | M2                                                            | 3 000                 | Có (đổi khi tệp đổi) | memory.prune đề xuất gộp/lược; băng cảnh báo trong UI                   |
| 4 \<inventory\>                            | Mã dựng từ Store                                              | 800                   | Không                | Rút gọn danh sách (chỉ đếm + 5 mục mới nhất)                            |
| 5 \<facts\>                                | fact.query theo thực thể 3 lượt gần                           | 2 000                 | Không                | Giảm top-N; ưu tiên VÀNG/NGƯỜI, thực thể nhắc gần nhất                  |
| 6 \<human_edits\> + \<pending\> + \<plan\> | Changeset human chưa acknowledged; thẻ chờ; kế hoạch đã duyệt | 1 600                 | Không                | Tóm tắt diff bằng mã (số dòng, trường đổi); kế hoạch chỉ bước chưa xong |
| 7 Skill đã nạp                             | skill.load                                                    | 6 000                 | Có theo skill        | Bỏ skill không dùng 5 lượt; báo mô hình                                 |
| 8 Bản tóm tắt phiên                        | compact (C2/C3)                                               | 3 000                 | Không                | C3 tóm tắt của tóm tắt                                                  |
| 9 Transcript gần nhất                      | M1 sau C0/C1                                                  | phần còn lại − dự trữ | Không                | C1 → C2 → C3 → C4                                                       |
| 10 Dự trữ                                  | Trả lời + tool_result lượt này                                | 20 % cửa sổ           | —                    | Bất khả xâm phạm                                                        |

**4.2. Bốn ngưỡng**

| **Mức sử dụng**                  | **Hành động**                                                                               | **Ai thấy**                                             |
|----------------------------------|---------------------------------------------------------------------------------------------|---------------------------------------------------------|
| \< 60 %                          | C0 liên tục                                                                                 | Đồng hồ token ở thanh trạng thái                        |
| 60–70 %                          | C1 thu gọn cơ học (0 token); cảnh báo vàng                                                  | Thanh trạng thái đổi màu                                |
| 70 % (hoặc cuối lượt nếu ≥ 65 %) | C2 tóm tắt có cấu trúc (một lời gọi mô hình) + kiểm                                         | \[Hệ thống\] "Đã nén 38 k → 6 k, giữ 10 lượt, kiểm 3/3" |
| 85 %                             | C3 bậc thang; K giảm 10 → 6                                                                 | Như trên + gợi ý "mở lượt mới cho việc khác"            |
| 95 %                             | C4 khẩn cấp: bỏ mọi tool_result thô, giữ ghim + tóm tắt; nếu vẫn vượt → dừng lượt, lưu, báo | \[Hệ thống\] đỏ; thẻ đề nghị mở phiên mới               |

Đo token bằng tokenizer của mô hình đang dùng (hoặc ước lượng 1 token ≈ 3,2 ký tự tiếng Việt có dấu khi không có tokenizer); mọi message trong M1 mang trường tokens để tính nhanh không cần đếm lại.

**5. Quản lý bộ nhớ theo lượt (C0 — liên tục)**

**5.1. Chính sách cắt theo tool (tool_result không đi nguyên văn)**

Đây là biện pháp quan trọng nhất và rẻ nhất: mô hình nhận đúng lượng nó cần, phần còn lại nằm ở blob và được đọc lại bằng tool khi cần (giống Claude Code lưu kết quả lớn ra tệp).

| **Tool**                    | **Đưa vào ngữ cảnh**                                                                                                | **Lưu blob**                   | **Mô hình đọc thêm bằng**    |
|-----------------------------|---------------------------------------------------------------------------------------------------------------------|--------------------------------|------------------------------|
| fs.read                     | ≤ 400 dòng theo range yêu cầu; có số dòng; nếu tệp \> 400 dòng → đầu 60 + đề mục hàm/cấu trúc (ctags) + gợi ý range | Toàn tệp (đã có trong git)     | fs.read(path, range)         |
| fs.grep / fs.glob           | ≤ 80 dòng khớp, mỗi dòng ≤ 200 ký tự; đếm tổng                                                                      | Danh sách đầy đủ               | fs.grep(…, page)             |
| bash                        | Đầu 40 dòng + cuối 40 dòng + mã thoát; báo "đã cắt N dòng"                                                          | stdout/stderr đầy đủ           | blob.read(ref, range)        |
| build.compile               | ok/fail, ≤ 20 lỗi/warning đầu tiên (đã gom trùng), Flash/RAM                                                        | Log đầy đủ + map               | build.log(ref)               |
| sim.run                     | verdict theo assert + 30 dòng log quanh điểm quyết định + exit_reason                                               | Log, VCD                       | analyze.log(ref, query)      |
| target.log                  | 50 dòng cuối theo cửa sổ thời gian; đếm                                                                             | Toàn bộ                        | target.log(ref, range)       |
| ingest.file                 | Số trang/bảng/Fact ứng viên, tier, 5 tiêu đề bảng đầu                                                               | Text theo trang, Fact ứng viên | rag.ask, fact.review_queue   |
| rag.ask                     | top-3 đoạn ≤ 300 token mỗi đoạn + trích dẫn                                                                         | Toàn bộ kết quả                | rag.ask(page)                |
| doc.search_web              | ≤ 8 ứng viên (tiêu đề, domain, phiên bản, kích thước)                                                               | Toàn bộ                        | doc.search_web(page)         |
| analyze.capture             | Khung đã giải mã quanh sự kiện bất thường ≤ 40 dòng + thống kê                                                      | Toàn bộ khung                  | analyze.capture(ref, window) |
| Task (subagent)             | CHỈ báo cáo có lược đồ ≤ 800 token                                                                                  | Transcript riêng của subagent  | Task.report(ref) (hiếm)      |
| history.list / ledger.query | ≤ 30 mục, mỗi mục 1 dòng                                                                                            | Toàn bộ                        | phân trang                   |

**5.2. Blob và tham chiếu**

> ToolResultEnvelope { tool, call_id, ts, truncated: bool, shown_tokens, blob_ref: "blob:sha256:…" \| null,
>
> artefact_ref: {type, id, version} \| null, summary_line: "fs.read src/drv_i2c.c v8 (312 dòng, hiện 1–120)" }

- Blob content-addressed (.eide/blobs/\<sha256\>), không trùng lặp, không bị xoá khi nén (chỉ bị dọn theo retention §7.4). Tham chiếu artefact theo id+version để mô hình luôn biết đang nói về bản nào.

**5.3. Khử trùng lặp và hết hạn**

- **Dedup:** fs.read cùng path cùng version lần thứ hai → message cũ thay bằng stub "(đã đọc ở \#12, không đổi)"; giữ lần mới.

- **Supersede:** tệp được sửa (changeset mới) → tool_result đọc bản cũ thành stub "(bản v7 — đã có v8 ở \#31)".

- **Hết hạn:** tool_result không được nhắc trong 8 lượt và không ghim → stub 1 dòng có blob_ref (C1).

- **Card đã đóng:** giữ tiêu đề + câu trả lời của người (1–2 dòng), bỏ toàn bộ lựa chọn.

**5.4. Ghim (pin) — không bao giờ bị nén**

Message được ghim tự động khi: là HumanAct kind ∈ {decide, confirm, edit, snapshot, set}; là câu trả lời thẻ clarify; là kế hoạch đã duyệt; là báo cáo lượt có hành động không đảo ngược; hoặc người bấm "Ghim". Ghim có trần 2 000 token; vượt → những ghim cũ nhất đã có bản ghi ở M2 (ADR/changeset) chuyển thành stub trỏ M2 (vẫn không mất sự thật).

**5.5. Thuật toán C0 (chạy sau mỗi tool_result)**

> def on_tool_result(call, raw):
>
> env = policy_truncate(call.tool, raw) \# §5.1 → shown + blob_ref
>
> if is_reread_same_version(call): stub_previous(call) \# §5.3
>
> if superseded_by_changeset(call): stub_previous(call)
>
> msgs.append(tool_result(call.id, env))
>
> for m in msgs.older_than(turns=8):
>
> if m.kind == "tool_result" and not m.pinned and not m.referenced_recently: m.collapse_to_stub()
>
> ctx.tokens = sum(m.tokens for m in msgs) + fixed_blocks_tokens

**6. Nén bộ nhớ (C1–C4)**

![](../img/m2_ladder.png)

*Hình 2. Bậc thang nén C0–C4 và bước kiểm sau nén*

**6.1. C1 — Thu gọn cơ học (0 token)**

- Stub mọi tool_result cũ hơn 8 lượt (giữ summary_line + blob_ref).

- Gộp các console.stream delta thành một message; bỏ card đã đóng chỉ giữ tiêu đề + trả lời.

- Xoá system-reminder cũ (inventory/facts của lượt trước) — chúng được tiêm mới mỗi lượt.

- Kết quả: thường giảm 30–50 % mà không cần mô hình; ghi ledger compact.c1 {before, after}.

**6.2. C2 — Tóm tắt có cấu trúc (một lời gọi mô hình)**

***6.2.1. Hook PreCompact (bằng mã, trước khi gọi mô hình)***

1.  Quét đoạn sẽ bị nén (mọi message cũ hơn K = 10 lượt và không ghim), lấy ra các mục có cấu trúc từ tool_result và HumanAct: ADR mới, giả định mới (assumptions), Fact mới/đổi tầng, changeset human chưa acknowledged, gate.decision, kế hoạch, lỗi đã gặp và cách sửa.

2.  Đối chiếu với M2: mục nào chưa có trong Store/EIDE.md → ghi (qua memory.note / store.\*) với provenance = message id. Đây là bảo hiểm P3: sự thật vào M2 trước khi văn bản bị tóm.

3.  Tính "phiếu kiểm" (§6.6): chọn 3 sự kiện có thể kiểm (quyết định gần nhất, giả định đang dùng, sửa của người gần nhất) từ ledger.

4.  Ghi ledger compact.pre {segment_hash, extracted: \[...\]}.

***6.2.2. Lời gọi tóm tắt (mô hình, nhiệt độ 0)***

Đầu vào: đoạn cần nén (đã C1) + bản tóm tắt phiên hiện có (nếu có) + \<inventory\>. Đầu ra bắt buộc theo lược đồ 10 mục; mỗi mục có trần; mục không có nội dung ghi "—" chứ không bỏ:

> SessionSummary v1 {
>
> 1 muc_tieu: "1–2 câu: dự án làm gì, người muốn gì trong phiên này" ≤ 80 token
>
> 2 trang_thai_theo_chang: { C1..C7: "xong\|đang\|chưa" + 1 dòng } ≤ 150
>
> 3 quyet_dinh: \[ {adr_id \| "chưa ghi", noi_dung, ai: human\|agent, ref: msg/changeset} \] ≤ 300
>
> 4 gia_dinh_dang_dung: \[ {khoa, gia_tri, vi_sao, huy_khi} \] ≤ 150
>
> 5 sua_cua_nguoi: \[ {changeset, hien_vat, tom_tat, vi_sao, da_nhac: bool} \] ≤ 200
>
> 6 viec_con_lai: \[ "…" \] (theo kế hoạch đã duyệt nếu có) ≤ 200
>
> 7 tep_dang_sua: \[ {path, version, dang_lam_gi} \] ≤ 100
>
> 8 hien_vat_stale: \[ {id, ly_do} \] ≤ 100
>
> 9 cau_hoi_mo: \[ "… (thẻ k-9 đang chờ)" \] ≤ 100
>
> 10 loi_da_gap: \[ {mo_ta, cach_sua, ket_qua} \] ≤ 200
>
> meta: { covers_msgs: \[from,to\], prev_summary_hash, created_at, model, tokens } }

Quy tắc viết trong prompt tóm tắt: chỉ dùng thông tin trong đoạn và M2; không suy diễn; mọi quyết định phải kèm ref; nếu đoạn chứa mục "đã quên" (tombstone) thì không đưa vào; ngôn ngữ tiếng Việt, thuật ngữ giữ nguyên.

***6.2.3. Lắp lại transcript***

Transcript mới = \[bản tóm tắt phiên (message kind=summary)\] + \[mọi message ghim, giữ nguyên thứ tự thời gian, với stub nối "…" giữa chúng\] + \[K lượt gần nhất nguyên văn (đã C1)\]. Ghi tệp mới rồi đổi tên (atomic swap); bản cũ giữ 24 giờ để huỷ nén.

**6.3. Cái gì không bao giờ bị nén mất**

| **Loại**                                                   | **Vì sao**                                        | **Cơ chế**                                              |
|------------------------------------------------------------|---------------------------------------------------|---------------------------------------------------------|
| Quyết định của người (decide, choose, edit, set, snapshot) | Là ý chí của người — nén mất là làm ngược ý người | Ghim tự động + ADR/changeset ở M2 + mục 3/5 của tóm tắt |
| Giả định đang dùng                                         | Mất giả định = mô hình "quên" rằng mình đang đoán | assumptions trong Store + mục 4 + \<pending\>           |
| Fact và tầng                                               | Nguồn sự thật                                     | Ở Store, không ở transcript                             |
| Thẻ đang chờ và kế hoạch đã duyệt                          | Đang là hợp đồng với người                        | \<pending\>/\<plan\> tiêm mới mỗi lượt                  |
| Hành động không đảo ngược đã làm                           | Không thể "làm lại" — phải biết đã làm            | Changeset reversible=false + mục 3 + \<inventory\>      |
| Mục "Đừng" của EIDE.md                                     | Là ranh giới người đặt                            | EIDE.md không bị nén; chỉ người xoá                     |
| Tombstone (đã quên)                                        | Không được hồi sinh                               | compact kiểm danh sách tombstone trước khi ghi tóm tắt  |

**6.4. C3 — Bậc thang**

Khi bản tóm tắt phiên vượt 3 000 token (phiên rất dài, nhiều lần C2): gọi mô hình tóm tắt CÁC bản tóm tắt theo cùng lược đồ 10 mục; bản mới ghi prev_summary_hash; chuỗi tóm tắt lưu ledger để phát lại và truy vết ("mục 3 quyết định này xuất hiện ở tóm tắt nào, đoạn nào"). Đồng thời K giảm từ 10 xuống 6 lượt nguyên văn. Mục 3, 4, 5 (quyết định, giả định, sửa của người) chỉ được GỘP, không được bỏ: nếu vượt trần thì bản tóm tắt tham chiếu "xem ADR-01…ADR-09 trong Store" thay vì liệt kê.

**6.5. C4 — Khẩn cấp**

Ở 95 %: bỏ toàn bộ tool_result thô (kể cả trong K lượt gần nhất) thành stub; nếu vẫn \> 90 % → kết thúc lượt an toàn (lưu trạng thái, báo "ngữ cảnh đầy"), đề nghị mở phiên mới cho việc tiếp theo (phiên mới nạp M2 + tóm tắt, không nạp transcript cũ). Không bao giờ cắt câu trả lời đang stream giữa chừng để nhét thêm.

**6.6. Kiểm sau nén (hook PostCompact)**

1.  Từ phiếu kiểm (§6.2.1 bước 3) sinh 3 câu hỏi bằng mã, ví dụ: "Quyết định gần nhất về cơ chế truyền tệp là gì?" (đáp án: ADR-03 MTP), "Giả định về mức tối ưu?" (-Os), "Người vừa sửa hiện vật nào và vì sao?" (REQ FR-01, phim 4K).

2.  Gọi mô hình với ngữ cảnh ĐÃ NÉN (không có đoạn gốc), nhiệt độ 0, lược đồ {answers: \[...\]}.

3.  So khớp bằng mã: id/khoá/giá trị phải trùng (không so văn phong).

4.  Đạt 3/3 → chấp nhận nén, ghi compact.ok. Sai ≥ 1 → huỷ (khôi phục transcript cũ), K += 4, lặp lại tối đa 2 lần; vẫn sai → giữ nguyên transcript, chuyển sang C4 khi cần, báo người "\[Hệ thống\] Nén không qua kiểm — giữ nguyên ngữ cảnh".

Chi phí: 2 lời gọi nhỏ mỗi lần nén; đổi lại là phát hiện ngay lỗi "quên" thay vì để người phát hiện (TC074).

**6.7. Nén và subagent**

Subagent chạy trong ngữ cảnh sạch (hiến pháp riêng + EIDE.md + nhiệm vụ + tool), có ngân sách riêng và cùng C0/C1; không C2 (nếu chạm 70 % → subagent phải trả báo cáo với trạng thái "dở dang" và việc còn lại). Tác tử chính chỉ nhận báo cáo ≤ 800 token — đây là cách chống phình mạnh nhất cho việc lớn (đọc repo, rà soát dài).

**7. Bộ nhớ dự án (M2) chi tiết**

**7.1. EIDE.md — quy tắc cứng**

| **Quy tắc**               | **Nội dung**                                                                                                                                                                                                                               |
|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Kích thước                | ≤ 3 000 token (~ 120 dòng). Vượt → băng cảnh báo; memory.prune đề xuất gộp/chuyển lịch sử; người duyệt                                                                                                                                     |
| Cấu trúc cố định (thứ tự) | \# Dự án · \## Mục tiêu · \## Chip & bo · \## Quyết định (ADR ngắn, tối đa 15 dòng, dẫn ADR id) · \## Giả định đang dùng · \## Quy ước mã & trình bày · \## Đừng · \## Người vừa sửa (ring buffer 10) · \## Ghi chú tự do (tối đa 20 dòng) |
| Nguồn gốc dòng            | Mỗi dòng do tác tử ghi kết thúc bằng \[run-xx\]; do người ghi \[h-xxxx\] hoặc không có (sửa tay); ngày ISO ở dòng tiêu đề mục                                                                                                              |
| Ai được ghi mục nào       | "Đừng": chỉ người (hoặc tác tử đề xuất qua thẻ, người duyệt). "Quyết định": tác tử ghi khi có ADR/gate.decision; người sửa tự do. "Giả định": tác tử ghi, người xác nhận/bác bỏ. "Người vừa sửa": chỉ hook ED5 ghi                         |
| Cách tác tử ghi           | Chỉ qua memory.note(scope=project, category, text) → tool tự chèn đúng mục, kiểm trần, tạo changeset; không fs.write trực tiếp EIDE.md (deny trong policy)                                                                                 |
| Xung đột                  | Người và tác tử cùng sửa → 3-way merge theo mục; xung đột trong cùng mục → thẻ hai bản                                                                                                                                                     |
| Lược                      | Dòng "Người vừa sửa" đã acknowledged và \> 5 lượt → chuyển sang ledger; ADR \> 15 → giữ 15 mới nhất + "xem Store"; giả định đã xác nhận → xoá khỏi mục (đã thành REQ/Fact)                                                                 |

**7.2. Store, Ledger, Changeset, Blob**

| **Kho**                           | **Lưu gì**                                                                                                         | **Kích thước/hiệu năng**                                                | **Ghi chú bộ nhớ**                                            |
|-----------------------------------|--------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------|---------------------------------------------------------------|
| Store (SQLite)                    | Hiện vật có cấu trúc + explain + version; bảng events (event-sourcing) + bảng trạng thái hiện tại                  | inventory \< 50 ms; fact.query \< 20 ms (chỉ mục theo subject/key/tier) | Nguồn cho \<inventory\>, \<facts\>                            |
| Ledger (JSONL)                    | Mọi HumanAct, tool_use/result (envelope, không phải blob), gate.decision, compact.\*, memory.note/forget, incident | Append-only; chỉ mục theo run_id, kind, ts                              | Nguồn cho ledger.query, phiếu kiểm, resume, transcript replay |
| Changesets (JSONL + git)          | E5 của MDD-40                                                                                                      | —                                                                       | Nguồn cho \<human_edits\>, STALE                              |
| Blob (.eide/blobs)                | tool_result đầy đủ, log, VCD, PDF text, transcript subagent                                                        | Content-addressed; dọn theo §7.4                                        | Mô hình đọc lại qua blob.read                                 |
| Sessions (.eide/sessions/\<id\>/) | transcript.jsonl, summaries/, pins.json, checkpoint trước nén                                                      | Mỗi phiên một thư mục                                                   | Resume; huỷ nén trong 24 h                                    |

**7.3. Bố cục tệp**

> \<project\>/
>
> EIDE.md \# bộ nhớ dự án đọc được (≤ 3 k token)
>
> .eide/store.sqlite \# hiện vật có cấu trúc + events
>
> .eide/ledger.jsonl \# sổ cái append-only
>
> .eide/changesets.jsonl \# chỉ mục changeset (tệp ↔ git sha, store ↔ event range)
>
> .eide/blobs/\<sha256\> \# nội dung lớn, content-addressed
>
> .eide/sessions/\<sid\>/transcript.jsonl \| summaries/\<n\>.json \| pins.json \| precompact.jsonl
>
> .eide/snapshots/\<id\>.json \# E6
>
> ~/.eide/memory.md · settings.json · trust.json · docs-cache/\<sha256\>.pdf \# M3 + cache M4

**7.4. Retention (giữ bao lâu)**

| **Đối tượng**                                        | **Giữ**                                    | **Dọn thế nào**                                  |
|------------------------------------------------------|--------------------------------------------|--------------------------------------------------|
| Transcript phiên                                     | 90 ngày sau phiên (hoặc đến khi người xoá) | Chuyển thành tóm tắt cuối + ledger; xoá messages |
| Blob không được changeset/snapshot/ledger tham chiếu | 30 ngày                                    | gc theo tham chiếu                               |
| Checkpoint ngầm trước nén/hoàn tác                   | 24 giờ (nén) / 30 ngày (hoàn tác)          | Tự xoá                                           |
| Ledger, changeset, Store, snapshot có tên, EIDE.md   | Vĩnh viễn                                  | Không dọn; nén ledger (gzip) theo tháng          |
| Cache tài liệu (M4)                                  | Vĩnh viễn theo hash                        | Người xoá thủ công                               |

**7.5. Mở lại dự án (resume) — thủ tục**

1.  Nạp EIDE.md; dựng \<inventory\>; đọc bản tóm tắt phiên cuối (nếu phiên trước chưa kết thúc sạch → chạy C2 trên transcript còn lại trước).

2.  Lấy từ ledger: 20 sự kiện gần nhất, thẻ đang chờ, run dở (nút dừng), snapshot gần nhất + khoảng cách, changeset human chưa acknowledged, hành động không đảo ngược gần nhất.

3.  Kiểm toàn vẹn: hash chuỗi changeset; transcript write-ahead khớp ledger; lệch → cảnh báo và dùng ledger làm chuẩn.

4.  Tiêm tất cả thành khối ngữ cảnh; mô hình tự thuật 5–8 câu "đang ở đâu, đã quyết gì, làm gì tiếp" — KHÔNG có trường summary sinh riêng để có thể null (TC065).

5.  Người có thể hỏi bất kỳ điều gì về quá khứ → ledger.query/history (§10), không dựa vào transcript cũ.

**8. Bộ nhớ người dùng (M3)**

| **Được nhớ**                                                                                                                                                                                | **Không bao giờ nhớ**                                                                                                                                      | **Cách ghi**                                                                                                 | **Cách quên**                                                                                           |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| Mức tự chủ; "tin" theo (tool, gói, nguồn) cho R0–R2; nguồn tin cậy; thói quen trình bày (ngắn/đủ/kỹ, diff nguyên văn, thuật ngữ, tab mặc định); đường toolchain; chip/bo hay dùng; ngôn ngữ | Khoá/mật khẩu/token API (đi vào keychain hệ điều hành); nội dung dự án (thuộc M2); suy đoán về người (trình độ, tính cách); bất cứ gì người bảo "đừng nhớ" | memory.note(scope=user) chỉ với category trong danh sách trắng; mỗi dòng có ngày; UI Thiết lập ghi trực tiếp | memory.forget(scope=user, key) → xoá dòng + tombstone; "tin" xoá trong Thiết lập; xoá toàn bộ = xoá tệp |

Tác tử chỉ đề xuất ghi vào M3 khi người lặp lại một sở thích ≥ 2 lần ("ngắn thôi") hoặc nói rõ "nhớ là…"; đề xuất bằng một dòng trong Console có nút Đồng ý/Không, không tự ghi (trừ "tin" trên thẻ cổng do người bấm).

**9. Tri thức toàn cục (M4) và con đường "thăng hạng"**

- M4 chỉ đọc, có phiên bản gói (registry chip v2026.09, ISA manifests v1.2, skills v3.0, hiến pháp v3). Tác tử không tự sửa M4.

- Cache tài liệu: PDF đã tải và duyệt được cache theo hash ở ~/.eide/docs-cache để dự án khác dùng lại không phải tải; tầng Fact KHÔNG đi theo cache — dự án mới phải rà soát lại (tầng là quyết định của người trong từng dự án), nhưng có nút "Dùng lại Fact đã xác nhận từ dự án X" → tạo Fact BẠC kèm nguồn gốc.

- Skill mới học từ dự án (ví dụ quy trình debug đã thành công): tác tử đề xuất "ghi thành skill" → người duyệt → skill nằm ở ~/.eide/skills (M3-mở-rộng), không vào gói M4 nếu chưa qua phát hành.

**10. Truy hồi (retrieval)**

| **Nhu cầu**                                                                | **Cơ chế**                                                                                                                                                          | **Xác định?**          |
|----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------|
| Tình trạng dự án                                                           | \<inventory\> mỗi lượt                                                                                                                                              | Có                     |
| Số liệu về thực thể đang nói                                               | Trích thực thể bằng regex/từ điển từ 3 lượt gần (chip, net, pin, REQ id, tệp) → fact.query top-N (ưu tiên VÀNG \> NGƯỜI \> BẠC; nhắc gần hơn xếp trước) → \<facts\> | Có                     |
| Nội dung tài liệu                                                          | rag.ask theo yêu cầu của mô hình; kết quả cắt theo §5.1                                                                                                             | Lai (embedding + BM25) |
| Quá khứ hội thoại/quyết định ("ban đầu anh nói gì về…", "vì sao chọn MTP") | ledger.query(kind, text, range) + history.diff + ADR; hiến pháp yêu cầu tra trước khi trả lời câu hỏi về quá khứ; UI có nút "Tìm trong lịch sử"                     | Có (FTS trên ledger)   |
| Kết quả tool đã cắt                                                        | blob.read(ref, range)                                                                                                                                               | Có                     |
| Sửa của người                                                              | \<human_edits\> đến khi acknowledged; sau đó changeset/ledger                                                                                                       | Có                     |
| Sở thích người dùng                                                        | M3 vào hiến pháp (khối 1 mở rộng ≤ 300 token)                                                                                                                       | Có                     |

**11. Giao diện bộ nhớ (khối A14.6 — bổ sung vào mô hình UI)**

| **Widget**                                                                 | **Loại** | **Yêu cầu**            |
|----------------------------------------------------------------------------|----------|------------------------|
| Đồng hồ ngữ cảnh theo khối (10 khối §4.1, % và token, màu theo ngưỡng)     | display  | MEM-01, MEM-02         |
| Bản tóm tắt phiên hiện tại (10 mục) — xem, sửa (edit → HumanAct), ghim mục | edit     | MEM-05, MEM-06, MEM-11 |
| Danh sách message ghim; bỏ ghim/ghim thủ công                              | edit     | MEM-07                 |
| Nút "Nén ngay" (C1/C2) và "Huỷ nén gần nhất" (trong 24 h)                  | action   | MEM-04, MEM-09         |
| Nhật ký nén: trước/sau, kiểm 3/3, thời điểm, chuỗi tóm tắt (C3)            | display  | MEM-08, MEM-09         |
| Bộ nhớ người dùng (memory.md): xem, sửa, quên từng dòng, xoá toàn bộ       | edit     | MEM-13, MEM-14         |
| Đề xuất ghi nhớ của tác tử (Đồng ý/Không)                                  | action   | MEM-14                 |
| Tìm trong lịch sử (ledger.query) + kết quả có ref                          | action   | MEM-16                 |
| Cảnh báo EIDE.md vượt trần + đề xuất lược (memory.prune) — duyệt           | action   | MEM-10, MEM-12         |
| Thông báo \[Hệ thống\] sau mỗi lần nén (một dòng)                          | display  | MEM-09                 |

Các yêu cầu MEM-01…MEM-24 (§14) và khối A14.6 đã được thêm vào ui_model.py; HTML prototype và Excel ánh xạ đã sinh lại, vẫn kín hai chiều.

**12. Sự cố và toàn vẹn**

- Write-ahead: mỗi message (HumanAct, tool_result envelope, agent text) được ghi transcript.jsonl (fsync) TRƯỚC khi xử lý tiếp; lõi chết giữa lượt → resume từ dòng cuối hợp lệ; tool đã chạy nhưng chưa ghi kết quả → đánh dấu "không rõ kết quả", không chạy lại tool có tác dụng phụ (flash, write) mà hỏi người.

- Nén là giao dịch: ghi transcript mới → kiểm → đổi tên atomic → ghi ledger compact.ok; bất kỳ bước nào hỏng → bản cũ còn nguyên.

- Hash chuỗi: ledger và changesets có hash nối (prev_hash) — mở dự án kiểm; lệch → chế độ chỉ đọc + báo người.

- Mất mạng/LLM lỗi trong lúc tóm tắt (C2): huỷ nén, giữ nguyên, thử lại lượt sau; không bao giờ để transcript ở trạng thái "đã cắt nhưng chưa có tóm tắt".

- Nhiều phiên trên cùng dự án (TC067): khoá tệp .eide/lock có pid; phiên thứ hai chỉ đọc và cảnh báo.

**13. Đo lường và ca kiểm**

| **Chỉ số**                                             | **Mục tiêu**                              | **Cách đo**                                       |
|--------------------------------------------------------|-------------------------------------------|---------------------------------------------------|
| Token vào mỗi lượt (trung vị) ở phiên 100 lượt         | ≤ 45 % cửa sổ                             | Ledger tokens                                     |
| Tần suất C2                                            | ≤ 1 lần / 25 lượt trong phiên bình thường | compact.\* events                                 |
| Tỉ lệ kiểm sau nén đạt lần đầu                         | ≥ 95 %                                    | compact.ok / compact.pre                          |
| Sự cố "quên" (người phải nhắc lại quyết định/giả định) | 0 trong bộ kịch bản; theo dõi thực tế     | HumanAct có mẫu "tôi đã nói…" + gắn nhãn thủ công |
| Thời gian resume dự án 500 changeset                   | \< 3 s tới lúc mô hình bắt đầu thuật      | Đo                                                |
| Chi phí nén / chi phí phiên                            | ≤ 5 %                                     | Kế toán token                                     |

| **Mã** | **Ca kiểm**                                                        | **Mong đợi**                                                                             |
|--------|--------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| MEM01  | fs.read tệp 3 000 dòng                                             | Ngữ cảnh nhận ≤ 400 dòng + đề mục; blob có đủ; mô hình đọc range tiếp được               |
| MEM02  | Chạy 40 tool/lượt với log lớn                                      | Không vượt 70 % nhờ C0/C1; dự trữ 20 % nguyên                                            |
| MEM03  | Tác tử cố fs.write EIDE.md trực tiếp                               | Policy deny; phải dùng memory.note; changeset có provenance                              |
| MEM04  | Bấm "Nén ngay" ở 40 %                                              | C1 chạy; C2 chỉ khi người xác nhận; huỷ nén được trong 24 h                              |
| MEM05  | Phiên 60 lượt có 4 ADR, 3 giả định, 2 sửa của người → nén          | PreCompact ghi đủ vào M2 trước; tóm tắt 10 mục đủ; mục 3/4/5 khớp ledger 100 %           |
| MEM06  | Hỏi "quyết định ban đầu về định dạng hệ thống tệp?" sau 3 lần nén  | Trả lời đúng ADR + ref (TC074)                                                           |
| MEM07  | Người sửa REQ rồi phiên bị nén trước khi tác tử nhắc               | Sau nén \<human_edits\> vẫn còn; tác tử nhắc ở lượt kế                                   |
| MEM08  | Cố tình làm tóm tắt sai (mock mô hình)                             | PostCompact phát hiện, huỷ, K += 4, thử lại; ghi ledger                                  |
| MEM09  | Nén ở 95 %                                                         | C4: bỏ tool_result thô, giữ ghim + tóm tắt; báo người; đề nghị phiên mới                 |
| MEM10  | EIDE.md 4 000 token                                                | Băng cảnh báo; memory.prune đề xuất; không tự xoá                                        |
| MEM11  | Sửa bản tóm tắt phiên trên UI                                      | HumanAct edit → changeset; lượt sau dùng bản đã sửa                                      |
| MEM12  | Ghim thủ công một message rồi nén                                  | Message còn nguyên văn                                                                   |
| MEM13  | memory.forget một dòng M3, rồi transcript cũ có nội dung đó bị nén | Tóm tắt không chứa nội dung đã quên (tombstone)                                          |
| MEM14  | Lõi chết giữa tool build                                           | Resume: message write-ahead còn; build đánh dấu "không rõ", hỏi người trước khi chạy lại |

**14. Danh mục yêu cầu MEM-01…MEM-24 (đưa vào Excel ánh xạ)**

| **Mã** | **Yêu cầu**                                                                                                              |
|--------|--------------------------------------------------------------------------------------------------------------------------|
| MEM-01 | Ngân sách ngữ cảnh cố định theo 10 khối; dự trữ 20 %                                                                     |
| MEM-02 | Đồng hồ token theo khối hiển thị cho người; 4 ngưỡng 60/70/85/95 %                                                       |
| MEM-03 | Mọi ghi M2/M3 qua tool memory.note/store.\* có changeset + provenance; fs.write EIDE.md bị deny                          |
| MEM-04 | C0: cắt theo chính sách tool, blob content-addressed, tham chiếu artefact id+version                                     |
| MEM-05 | C1: stub/dedup/supersede/hết hạn 8 lượt; 0 token                                                                         |
| MEM-06 | C2: PreCompact rút cấu trúc vào M2; tóm tắt 10 mục có trần; giữ K lượt + ghim; atomic swap                               |
| MEM-07 | Ghim tự động cho decide/confirm/edit/snapshot/set, trả lời thẻ, kế hoạch duyệt, hành động không đảo ngược; ghim thủ công |
| MEM-08 | PostCompact: 3 câu hỏi ngược từ ledger; sai → huỷ, K += 4, tối đa 2 lần                                                  |
| MEM-09 | C3 bậc thang với chuỗi hash; C4 khẩn cấp; thông báo \[Hệ thống\] sau mỗi nén; huỷ nén trong 24 h                         |
| MEM-10 | EIDE.md: trần 3 k, cấu trúc cố định, nguồn gốc dòng, quyền ghi theo mục, memory.prune đề xuất                            |
| MEM-11 | Bản tóm tắt phiên xem/sửa được trên UI                                                                                   |
| MEM-12 | Người thấy cửa sổ ngữ cảnh hiện tại (khối, token, ghim)                                                                  |
| MEM-13 | Quên có chủ đích: memory.forget → tombstone; không hồi sinh từ transcript                                                |
| MEM-14 | M3: danh sách trắng category; đề xuất ghi nhớ phải người đồng ý; không nhớ bí mật/suy đoán                               |
| MEM-15 | Subagent ngữ cảnh sạch, chỉ trả báo cáo ≤ 800 token; không C2                                                            |
| MEM-16 | ledger.query cho câu hỏi về quá khứ; hiến pháp bắt tra trước khi trả lời                                                 |
| MEM-17 | Resume: 5 bước §7.5; mô hình tự thuật; không có summary null                                                             |
| MEM-18 | Write-ahead transcript; nén là giao dịch; hash chuỗi ledger/changeset                                                    |
| MEM-19 | Retention §7.4 và gc blob theo tham chiếu                                                                                |
| MEM-20 | Cache tài liệu M4 theo hash; Fact không đi theo cache; "dùng lại Fact" tạo BẠC có nguồn gốc                              |
| MEM-21 | \<facts\> chọn theo thực thể 3 lượt gần, ưu tiên tầng và độ gần                                                          |
| MEM-22 | Skill không dùng 5 lượt bị bỏ khỏi ngữ cảnh; báo mô hình                                                                 |
| MEM-23 | Nhiều phiên cùng dự án: khoá tệp, phiên sau chỉ đọc                                                                      |
| MEM-24 | Đo lường §13 ghi vào ledger và hiển thị trong Thiết lập                                                                  |

**15. API và lộ trình hiện thực**

> \# eide/memory/ — giao diện công khai
>
> memory.note(scope: project\|user, category, text, provenance) -\> changeset_id
>
> memory.forget(scope, key_or_line) -\> tombstone_id
>
> memory.pin(msg_id, on: bool)
>
> memory.status() -\> { blocks: \[{name, tokens, cap}\], pinned: \[...\], last_compact: {...}, summary_ref }
>
> memory.compact(level: C1\|C2\|C3, reason) -\> CompactReport { before, after, verified: 3/3, summary_ref }
>
> memory.undo_compact() -\> bool \# trong 24 h
>
> memory.prune_suggest() -\> \[ {section, lines, why} \]
>
> ledger.query(kind?, text?, run_id?, range?) -\> \[events\]
>
> blob.read(ref, range?) -\> text
>
> \# hooks: on_tool_result (C0) · pre_compact · post_compact · on_turn_end (ngưỡng) · on_resume

| **Bước**                   | **Nội dung**                                                                         | **Ca kiểm**               |
|----------------------------|--------------------------------------------------------------------------------------|---------------------------|
| MEM-A (cùng G1 của MDD-40) | Envelope + chính sách cắt theo tool + blob; đồng hồ token; C1                        | MEM01, 02, 05             |
| MEM-B (cùng G2)            | memory.note/forget + EIDE.md quy tắc + policy deny; ledger.query; write-ahead + hash | MEM03, 10, 13, 14, 16, 18 |
| MEM-C (cùng G3)            | C2 + PreCompact/PostCompact + lược đồ tóm tắt + ghim; UI A14.6; resume 5 bước        | MEM04, 06–09, 11, 12, 17  |
| MEM-D (cùng G6)            | C3/C4; subagent ngân sách riêng; retention/gc; đo lường                              | MEM09, 15, 19, 24         |
