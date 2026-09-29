**EIDE — KIẾN TRÚC TÁC TỬ THEO VÒNG LẶP**

**Đơn giản như Claude Code: một vòng lặp, LLM điều phối, công cụ có hợp đồng, hook và cấp quyền giữ các nguyên tắc**

*Mã tài liệu EIDE-AAD-33 · v2.0 · 25/09/2026 (thay thế v1.0)*

|                        |                                                                                                                                                                                                          |
|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Mã tài liệu**        | EIDE-AAD-33 v2.0 (Agent Architecture Design — agent-loop edition)                                                                                                                                        |
| **Tên tài liệu**       | Kiến trúc tác tử Kỹ sư Nhúng theo vòng lặp tác tử (agent loop) — LLM tham gia sâu vào mọi tương tác                                                                                                      |
| **Phiên bản**          | v2.0 — thay thế AAD-33 v1.0 (máy trạng thái S0–S6). Áp dụng cho EIDE v1.4                                                                                                                                |
| **Ngày**               | 25/09/2026                                                                                                                                                                                               |
| **Đề tài**          | PHÁT TRIỂN PHẦN MỀM NHÚNG CÓ ỨNG DỤNG TRÍ TUỆ NHÂN TẠO (AI)                                |
| **Khung**              | Đề án tốt nghiệp Thạc sĩ ngành Kỹ thuật Điện tử — PTIT                                                                                                                                                   |
| **Người hướng dẫn**    | TS. Nguyễn Trung Hiếu                                                                                                                                                                                    |
| **Tác giả**            | Vũ Trí Công                                                                                                                                                                                              |
| **Tài liệu liên quan** | EIDE-AGD-32 v1.0 (7 nguyên tắc, 7 chặng, Bản đồ tri thức mạch, luồng duyệt datasheet — vẫn hiệu lực); EIDE-UIP-34 v1.0 (giao thức giao diện — vẫn hiệu lực); Usecase_Test_Agent_Ky_Su_Nhung.xlsx (76 TC) |
| **Cảm hứng thiết kế**  | Claude Code / Claude Agent SDK: agentic loop, tools, permission system, hooks, subagents, skills, CLAUDE.md, context compaction, plan mode                                                               |

***Lịch sử sửa đổi***

| **Phiên bản** | **Ngày**   | **Nội dung**                                                                                                                                                                                                                                                                               | **Người sửa** |
|---------------|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|
| v1.0          | 24/09/2026 | Máy trạng thái S0–S6, NLU nhiều tầng (DX, tách kênh, phân loại ý định, dải tin cậy), planner có tiền đề, 6 lớp.                                                                                                                                                                            | VTC           |
| v2.0          | 25/09/2026 | Tổ chức lại theo vòng lặp tác tử: LLM là bộ điều phối duy nhất; bỏ phân loại ý định/slot/planner/chuỗi mẫu; năng lực → tool có hợp đồng; nguyên tắc → hook + cấp quyền; chuỗi mẫu → skill; subagent chuyên biệt + verifier; EIDE.md; nén ngữ cảnh; plan mode. Giữ nguyên AGD-32 và UIP-34. | VTC           |

**1. Vì sao đổi: từ máy trạng thái sang vòng lặp**

Phiên bản 1.0 cố gắng "bảo vệ" mô hình bằng nhiều tầng xác định đứng trước nó: trích xác định, tách kênh, phân loại ý định vào danh sách đóng, ba dải tin cậy, bộ lập kế hoạch theo mẫu chuỗi, rồi mới cho mô hình làm việc trong từng nút. Kết quả đo 23/09 cho thấy chính các tầng ấy là nơi 51 ca chết: đường dẫn bịa ở tầng slot, câu hỏi chặn ở tầng hộ chiếu, ý định sai ở tầng phân loại, chuỗi thiếu tiền đề ở tầng planner. Càng nhiều tầng đứng trước mô hình, càng nhiều chỗ để hiểu sai mà mô hình không có cơ hội sửa.

Claude Code đi hướng ngược lại và hiệu quả: **một vòng lặp** — mô hình đọc toàn bộ câu người nói cùng ngữ cảnh, tự quyết gọi công cụ nào, đọc kết quả (kể cả lỗi), tự điều chỉnh, hỏi khi cần, và trả lời. Sự an toàn không nằm ở việc chặn mô hình khỏi quyết định, mà ở **ba lớp xác định bao quanh mỗi lời gọi công cụ**: hook trước khi gọi, lớp cấp quyền, hook sau khi gọi. Mô hình có toàn bộ không gian để suy luận; công cụ và hook có toàn bộ quyền để nói "không" hoặc "hỏi người trước".

| **Khía cạnh**        | **v1.0 (máy trạng thái)**                                                   | **v2.0 (vòng lặp)**                                                                                                                                        |
|----------------------|-----------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Ai quyết làm gì tiếp | Bộ phân loại ý định + planner theo mẫu chuỗi                                | LLM, mỗi vòng, dựa trên toàn bộ ngữ cảnh và kết quả công cụ vừa nhận                                                                                       |
| Hiểu câu người       | DX → tách kênh → phân loại → slot → dải tin cậy (4 tầng, 2 lời gọi mô hình) | LLM đọc trực tiếp; công cụ kiểm tra đầu vào (đường dẫn không tồn tại → lỗi rõ → LLM tự hỏi lại)                                                            |
| Hỏi làm rõ           | Pha S3 cố định, tối đa 2 vòng                                               | Công cụ ask_user; LLM tự quyết khi nào hỏi; hiến pháp yêu cầu "hỏi một cụm"; hook Stop kiểm giả định                                                       |
| Kế hoạch             | chains.yaml 22 mẫu + planner có tiền đề                                     | LLM tự lập; việc lớn → plan mode (chỉ công cụ đọc) → người duyệt → thực thi; tiền đề nằm trong lỗi công cụ ("cần module_graph — gọi arch.decompose trước") |
| Nguyên tắc an toàn   | S0 + Policy engine trong Router                                             | Hook UserPromptSubmit (S0 giữ nguyên) + PreToolUse + lớp cấp quyền theo mẫu đầu vào                                                                        |
| Tri thức quy trình   | Mã hoá cứng trong chuỗi mẫu                                                 | Skill (SKILL.md) nạp theo ngữ cảnh — sửa bằng văn bản, không sửa mã                                                                                        |
| Chuyên môn hoá       | Không                                                                       | Subagent với system prompt và tập tool riêng; verifier độc lập                                                                                             |
| Trạng thái           | DialogueState + Inventory + slots                                           | Transcript (messages) là trạng thái; Inventory tiêm vào ngữ cảnh mỗi lượt dưới dạng system-reminder                                                        |
| Tính tất định        | Cao ở nhiều pha                                                             | Cao ở hook/tool/cấp quyền; thấp ở quyết định của LLM — bù bằng eval 76 TC × 5 lần                                                                          |
| Chi phí token        | Thấp                                                                        | Cao hơn (mỗi vòng có ngữ cảnh) — bù bằng prompt caching, nạp tool trễ, nén ngữ cảnh                                                                        |

**Điều không đổi:** bảy nguyên tắc của AGD-32, ba tầng dữ liệu Vàng/Bạc/Đồng, luồng duyệt datasheet, cổng G-OPS/G-SAFE, giao thức UAP một cửa, bộ 76 ca đo. Chúng chỉ đổi chỗ đứng: từ "pha" thành "hook, công cụ và điều khoản hiến pháp".

**2. Vòng lặp tác tử**

![](../img/l1_loop.png)

*Hình 1. Vòng lặp tác tử: LLM ở giữa; ba hook và lớp cấp quyền bao quanh mỗi lời gọi công cụ; giao diện UAP là một cửa*

**2.1. Mã giả**

> def turn(human_act):
>
> ev = hooks.user_prompt_submit(human_act) \# S0 rule engine, 0 token: STOP/BACKREF/G-OPS/P-SAFE/P-LAW
>
> if ev.block: return ev.reply \# từ chối/cảnh báo/thẻ cổng, không gọi mô hình
>
> msgs.append(user(human_act, ev.annotations)) \# chú thích của S0 đi cùng câu (vd: "câu này chứa thao tác R4: RDP")
>
> for i in range(MAX_STEPS): \# ngân sách vòng: 40 tool-call/lượt, 300 s
>
> ctx = assemble(system=constitution + project_md, reminders=\[inventory(), facts_for(msgs)\], skills=active_skills)
>
> rsp = llm.stream(ctx, msgs, tools=tools.visible()) \# stream text ra console; tool_use gom lại
>
> if rsp.text: ui.console_stream(rsp.text)
>
> if not rsp.tool_calls: break \# mô hình kết luận lượt
>
> for call in rsp.tool_calls: \# có thể song song nếu tool độc lập
>
> pre = hooks.pre_tool_use(call) \# constant-guard, tier check, sandbox, chú thích rủi ro
>
> perm = policy.decide(call, pre) \# allow \| ask \| deny
>
> if perm.ask: ans = ui.card(gate_card(call, perm)); perm = perm.resolve(ans) \# thẻ cổng RIÊNG
>
> if perm.deny: result = error(perm.reason) \# lỗi rõ để mô hình đổi hướng
>
> else: result = tools.run(call) \# trong sandbox; lỗi tool là dữ liệu, không phải ngoại lệ
>
> hooks.post_tool_use(call, result) \# ledger, ui.surface đồng bộ, lint
>
> msgs.append(tool_result(call.id, result))
>
> if ctx.tokens \> 0.7 \* window: msgs = compact(msgs) \# nén có cấu trúc, giữ quyết định/giả định/Fact
>
> hooks.stop(msgs) \# kiểm: giả định đã nói ra? hiện vật có nguồn? báo cáo chi phí

**2.2. Những gì mô hình được làm mà v1.0 không cho**

- Đọc thẳng câu người nói với toàn bộ sắc thái (mệnh đề chỉ thị, mô tả sản phẩm, dữ liệu, cảm xúc) và tự quyết nên coi phần nào là yêu cầu — ràng buộc N7 chuyển thành điều khoản hiến pháp + kiểm tra ở công cụ store.req_create (phải kèm trích dẫn từ lời người nói).

- Thử trước, sửa sau: gọi fs.read với đường dẫn người nói; nếu không tồn tại, công cụ trả về "không có tệp X; các tệp gần giống: …" và mô hình hỏi hoặc chọn — không cần DX đứng trước.

- Tự lập kế hoạch bằng ngôn ngữ, sửa kế hoạch giữa chừng khi kết quả công cụ khác dự đoán; không có chuỗi cứng để "chết tại nút".

- Hỏi người vào đúng lúc nó thấy cần, bằng ask_user, với lựa chọn nó tự soạn từ ngữ cảnh (kể cả "anh vừa nói ATmega328P — dùng chip này?").

- Giao việc cho subagent và đọc báo cáo của chúng; gọi verifier độc lập trước khi tuyên "đạt".

- Tự vẽ giao diện: quyết định bề mặt nào cần cập nhật, tô sáng chỗ nào, bằng công cụ ui.\* — giao diện vẫn là chi (UIP-34), nhưng bộ não điều khiển chi là mô hình chứ không phải UI Driver cứng.

**2.3. Ngân sách và điểm dừng**

| **Giới hạn**              | **Giá trị mặc định** | **Khi chạm**                                                          |
|---------------------------|----------------------|-----------------------------------------------------------------------|
| Số lời gọi công cụ / lượt | 40                   | Dừng, báo cáo đã làm gì, hỏi có tiếp không (không lặp vô tận — TC017) |
| Thời gian / lượt          | 300 s                | Lưu transcript, thả người dùng, nói thật (UC19)                       |
| Ngữ cảnh                  | 70 % cửa sổ          | compact() có cấu trúc (§7)                                            |
| Vòng tự sửa build/sim     | 3                    | Dừng, trình diff + lỗi cuối, hỏi người                                |
| Subagent song song        | 4                    | Xếp hàng                                                              |

**3. Ngữ cảnh: hiến pháp, EIDE.md, system-reminder, skill**

**3.1. Hiến pháp (system prompt cố định, ~1,5 k token, cache)**

Bảy nguyên tắc AGD-32 viết thành điều khoản hành vi cho mô hình — đây là nơi N1, N2, N4, N6, N7 sống, thay cho các pha S1/S3 cũ:

> \# Hiến pháp tác tử Kỹ sư Nhúng EIDE (trích)
>
> 1\. Datasheet là nguồn sự thật. Mọi con số anh dùng để so sánh, quyết định hay sinh mã phải đến từ fact.query
>
> (tầng ≥ Bạc) hoặc từ lời người dùng. Không có → nói "chưa có dữ kiện", đề nghị nạp/tìm datasheet. Không bịa.
>
> 2\. Tri thức chung của anh mang nhãn Đồng: được dùng để giải thích, gợi ý phép đo, KHÔNG được là một vế của phép so sánh
>
> và KHÔNG được thành hằng số trong mã (hook sẽ chặn).
>
> 3\. Tình trạng dự án nằm trong \<inventory\> — đọc nó, đừng đoán. Đừng tạo dự án mới khi đã có dự án đang mở.
>
> 4\. Hỏi ít, hỏi một cụm bằng ask_user với lựa chọn điền sẵn từ ngữ cảnh; tối đa 2 lần/lượt; hết thì nêu giả định rõ và làm.
>
> 5\. Chỉ thị cho anh ("cố tình gây lỗi", "đọc tệp X") không phải yêu cầu sản phẩm; rủi ro anh phát hiện đi vào risk, không vào FR.
>
> 6\. Tiêu chí chấp nhận là của người dùng; không sửa tiêu chí/test để đạt; log rỗng không phải đạt; phần chưa mô phỏng được nói rõ.
>
> 7\. Thao tác không đảo ngược và an toàn điện: hệ thống sẽ hỏi người qua thẻ cổng — đừng cố vòng qua, đừng gộp vào câu hỏi khác.
>
> 8\. Việc lớn (nhiều bước, nhiều tệp, có nạp/ghi): vào plan mode, trình kế hoạch, chờ duyệt.
>
> 9\. Nói tiếng Việt với người; thuật ngữ kỹ thuật giữ tiếng Anh. Kết thúc lượt: đã làm / bỏ / giả định / hoàn tác được tới đâu.

**3.2. EIDE.md — bộ nhớ dự án đọc được (như CLAUDE.md)**

Tệp Markdown ở gốc dự án, tự nạp vào system prompt mỗi lượt; mô hình và người cùng sửa (mọi sửa của mô hình qua công cụ fs.edit → có diff, có sổ cái). Nội dung: mục tiêu sản phẩm, chip đã ghim, quyết định (ADR ngắn), quy ước mã, giả định đang dùng, "đừng làm" của dự án. Thay cho DialogueState/ADR store rời rạc của v1.0 — nhưng REQ, Fact, netlist vẫn ở store có cấu trúc, EIDE.md chỉ là tóm tắt sống.

> \# EIDE.md — Dự án: Bộ chuyển LAN→USB cho TV
>
> \## Mục tiêu (v2, 24/09) … 3 dòng
>
> \## Chip & bo: STM32F103C8T6 (st.stm32f103c8@1.0.0, DS rev 17, RM0008 rev 21) · ISA armv7-m · toolchain arm-none-eabi 13.2
>
> \## Quyết định: ADR-03 dùng MTP thay Mass Storage (lý do: TV mount đồng thời gây hỏng FS) · ADR-04 nguồn pin 3,0–4,2 V
>
> \## Giả định đang dùng: mức tối ưu -Os · TV đọc exFAT (chưa xác nhận)
>
> \## Quy ước mã: HAL, không CMSIS trần; mọi hằng số từ Fact hoặc config.h có chú thích nguồn
>
> \## Đừng: không bật RDP nếu chưa có bản nạp gốc lưu ở releases/

**3.3. System-reminder tiêm mỗi lượt (xác định, 0 token sinh)**

| **Khối**        | **Nguồn**                                                                                                                                | **Kích thước** | **Thay cho**                                                                             |
|-----------------|------------------------------------------------------------------------------------------------------------------------------------------|----------------|------------------------------------------------------------------------------------------|
| \<inventory\>   | Đọc store bằng mã: REQ, phương án, hộ chiếu + số Fact theo tầng, tài liệu, module, build/sim/flash gần nhất, probe đang cắm, run đang dở | ≤ 800 token    | S2 và bảng kiểm kê v1.0 — nhưng không còn là cổng chặn, chỉ là sự thật mô hình được thấy |
| \<facts\>       | fact.query theo thực thể được nhắc trong 3 lượt gần nhất (chip, net, bus), kèm tầng và trích dẫn                                         | ≤ 2 k token    | Khối "Fact liên quan" trong prompt assembly v1.0                                         |
| \<pending\>     | Thẻ đang chờ (gate/clarify), run đang dừng, giả định đang dùng                                                                           | ≤ 300 token    | DST.pending_question                                                                     |
| \<skills-hint\> | Danh sách skill có mô tả khớp câu người (so khớp từ khoá xác định), mô hình tự quyết nạp bằng skill.load                                 | ≤ 300 token    | chains.yaml                                                                              |

**3.4. Skill — tri thức quy trình dạng văn bản**

Mỗi skill là một thư mục có SKILL.md (mô tả khi nào dùng + các bước + lỗi thường gặp + tiêu chí xong) và tệp kèm (mẫu mã, script kiểm). Mô hình nạp skill khi cần bằng skill.load; nội dung vào ngữ cảnh như tài liệu hướng dẫn. Đây là nơi 22 chuỗi mẫu cũ và kinh nghiệm nghề đi vào — sửa bằng chữ, chạy eval lại, không sửa mã lõi.

| **Skill (ví dụ)**       | **Khi nào**                | **Nội dung chính**                                                                                                                                          |
|-------------------------|----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| idea-to-spec            | Người mô tả ý tưởng mới    | Cụm câu hỏi chuẩn (mục tiêu, môi trường, chi phí, kích thước, nguồn, số lượng); mẫu đặc tả; cách phát hiện mâu thuẫn vật lý bằng số; mẫu bảng 2–4 phương án |
| datasheet-onboarding    | Chip mới, chưa có hộ chiếu | Tìm ở đâu (nhà sản xuất trước), phiên bản/errata, bảng nào trích Fact trước (AMR, DC char, pinout, AF), cách trình thẻ G-DATA                               |
| stm32-hal-project       | Sinh firmware STM32        | Cấu trúc CMake, clock tree từ Fact, pinmux từ pinout đã duyệt, HAL vs LL, lỗi hay gặp                                                                       |
| avr-bare-metal          | ATmega                     | F_CPU, TWI/TWBR, fuse cảnh báo (G-OPS)                                                                                                                      |
| i2c-debug               | Bus I2C không phản hồi     | Quy trình đo: scanner → SDA/SCL mức tĩnh → pull-up → timing; khi nào là phần cứng                                                                           |
| hardfault-analysis      | Có CFSR/PC/LR              | Giải mã CFSR, map PC → hàm bằng addr2line, mẫu báo cáo                                                                                                      |
| sim-criteria-first      | Trước mọi sim.run          | Viết criteria.yaml từ yêu cầu; assert mẫu; timeout; không đổi tiêu chí sau khi chạy                                                                         |
| flash-and-verify        | Nạp mạch thật              | detect → so ID chip với hộ chiếu → tóm tắt nạp gì vào đâu → verify → rút cáp giữa chừng thì làm gì                                                          |
| ota-ab-partition        | Thiết kế OTA               | Phân vùng, chữ ký, rollback, kịch bản mất điện                                                                                                              |
| design-review-checklist | Rà soát schematic          | ERC, mức logic, pull-up, tụ lọc theo IC, ESD, dòng tải; cách trình phát hiện theo mức nghiêm trọng, không bịa lỗi                                           |

**4. Công cụ (tools) — năng lực có hợp đồng, nạp trễ**

238 năng lực v1.2 được gom thành khoảng 40 công cụ có lược đồ JSON; công cụ ít dùng được "nạp trễ": mô hình thấy tên + một dòng mô tả, gọi tool.search để lấy lược đồ đầy đủ khi cần (giữ prompt nhỏ). Mỗi công cụ vẫn có hợp đồng CDS-12 (params, requires, produces, risk, gate) — nhưng requires giờ được kiểm TRONG công cụ và trả lỗi có hướng dẫn, thay vì planner kiểm trước.

| **Nhóm**                     | **Công cụ**                                                                                                                                                                                                   | **Ghi chú hợp đồng**                                                                                                                               |
|------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Store (hiện vật có cấu trúc) | store.req_create/update/list, store.option\_\*, store.adr\_\*, store.module\_\*                                                                                                                               | req_create yêu cầu source_quote trích từ lời người trong transcript; hook từ chối nếu không tìm thấy (chống REQ bịa — TC008, TC017)                |
| Tri thức                     | fact.query, fact.compare, fact.review_queue, passport.get/propose/pin, rag.ask, doc.search_web, doc.approve_request, ingest.file                                                                              | fact.compare từ chối vế Đồng (N2); doc.approve_request luôn tạo thẻ G-DATA; ingest.file phân loại theo magic bytes và trả đúng lý do lỗi           |
| Tệp & lệnh                   | fs.read, fs.glob, fs.grep, fs.edit (diff), fs.write, bash                                                                                                                                                     | Mọi thứ trong sandbox có danh sách trắng; fs.write/edit qua constant-guard; bash có danh sách mẫu bị deny (rm -rf ngoài dự án, đọc ~/.ssh)         |
| Thiết kế                     | arch.decompose, diagram.render, board.schematic, board.pinout, board.check, bom.build                                                                                                                         | board.check chạy luật ERC xác định trên netlist; diagram.render từ chối vẽ khi chưa có module_graph và nói rõ gọi gì trước (giữ hành vi tốt TC009) |
| Build/Sim/Target             | env.check, tool.install, build.compile, build.map, sim.criteria, sim.run, test.run, target.detect, target.flash, target.verify, target.log, target.debug, target.dangerous (erase_all/option_bytes/rdp/efuse) | target.dangerous là công cụ RIÊNG, risk R4, luôn ask; sim.run yêu cầu criteria đã xác nhận; target.flash đối chiếu ID chip với hộ chiếu trước      |
| Phân tích/tính toán          | analyze.capture, analyze.hardfault, analyze.log, calc.eval (chạy công thức bằng mã, đầu vào phải là Fact hoặc số người cho)                                                                                   | calc.eval từ chối tham số không nguồn (TC056/057)                                                                                                  |
| Người & giao diện            | ask_user (thẻ clarify/proposal/criteria), ui.surface_set/patch/focus/highlight, ui.notice                                                                                                                     | ask_user không bao giờ được dùng cho cổng (cổng do lớp cấp quyền phát — I6 của UIP-34)                                                             |
| Điều phối                    | Task (subagent), skill.load, tool.search, memory.note (ghi vào EIDE.md mục giả định/quyết định), plan.enter/exit                                                                                              | Task trả về một báo cáo có cấu trúc; plan.enter khoá mọi tool ghi                                                                                  |

**4.1. Thông điệp lỗi là giao diện lập trình cho mô hình**

Trong vòng lặp, lỗi công cụ không phải ngoại lệ mà là dữ liệu mô hình dùng để đổi hướng. Vì vậy mọi công cụ trả lỗi theo mẫu: {code, message_vi, hint_for_agent, alternatives\[\]}. Ví dụ: fs.read("/docs/ds.pdf") → "E1404 Không có tệp /docs/ds.pdf. Gần giống: /docs/ds_v1.pdf, /docs/ds_v2.pdf. Gợi ý: hỏi người dùng hoặc đọc cả hai." Đây là cách thay thế DX/slot của v1.0: thay vì đoán trước, để mô hình thử và nhận phản hồi tốt.

**5. Lớp cấp quyền và hook — nơi các nguyên tắc sống**

**5.1. Cấp quyền theo mẫu (như permission rules của Claude Code)**

> \# policy.yaml (trích) — mức tự chủ hiện tại: A3
>
> rules:
>
> \- tool: "fs.read\|fs.glob\|fs.grep\|fact.\*\|rag.\*\|passport.get\|store.\*\_list" -\> allow \# R0
>
> \- tool: "store.req_create" when: "!has_source_quote" -\> deny "REQ phải trích lời người dùng"
>
> \- tool: "fs.edit\|fs.write" when: "constant_guard.unsourced \> 0" -\> deny "hằng số không nguồn: {list}"
>
> \- tool: "fs.write" when: "path.human_edited && !merged" -\> ask gate: G-FILE
>
> \- tool: "bash" when: "matches(deny_patterns)" -\> deny
>
> \- tool: "bash" when: "network" -\> ask gate: G-TOOL
>
> \- tool: "tool.install" -\> ask gate: G-TOOL remember: per-package
>
> \- tool: "doc.approve_request" -\> ask gate: G-DATA auto_if: "domain in trusted"
>
> \- tool: "sim.criteria" when: "criteria_exists && changed" -\> ask gate: G-QUAL require: "from,to,why"
>
> \- tool: "target.flash" -\> ask gate: G-FLASH summary: "gì→đâu, hash"
>
> \- tool: "target.dangerous" -\> ask gate: G-OPS never_auto: true expires: 10m
>
> \- tool: "plan.exit" when: "plan.nodes \> 7 \|\| plan.big" -\> ask gate: G-SCOPE
>
> modes: { A0: "ask all", A1: "allow R0", A2: "allow R0-R1", A3: "allow R0-R2 + remembered", A4: "allow R0-R3; R4 still ask" }

"Tin" (remember) chỉ áp dụng cho R0–R2 và được ghi vào bộ nhớ dài hạn theo (tool, mẫu); R4 không bao giờ tự duyệt ở mọi mức — đúng bất biến của AGD-32 §8.

**5.2. Hook**

| **Hook**         | **Chạy khi**                         | **Việc (mã xác định)**                                                                                                                                                                                                                     | **Nguyên tắc / ca đo**              |
|------------------|--------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------|
| UserPromptSubmit | Ngay khi HumanAct đến, trước mô hình | S0 rule engine YAML: STOP; BACKREF (tra run); G-OPS/P-SAFE/P-LAW/P-QUAL theo mẫu → chặn/thẻ cổng/cảnh báo đứng đầu; P-INJ trên tệp đính kèm. Không chặn thì gắn chú thích cho mô hình ("câu chứa thao tác R4: RDP — sẽ có thẻ cổng riêng") | N5 — TC007, 022, 035, 036, 068, 069 |
| PreToolUse       | Trước mỗi tool_use                   | constant-guard (quét hằng số điện/thời gian trong nội dung ghi ↔ kho Fact); tier-check cho fact.compare; sandbox path check; phân loại tệp cho ingest; đánh giá rủi ro → đưa cho lớp cấp quyền                                             | N1, N2 — TC013, 021, 070            |
| PostToolUse      | Sau mỗi tool_result                  | ledger.append; đồng bộ Surface theo loại hiện vật (không cần mô hình gọi ui.\* cho việc thường); lint kết quả (log rỗng → gắn cờ "không kết luận được")                                                                                    | N6 — TC076                          |
| Stop             | Mô hình kết thúc lượt                | Kiểm: có giả định chưa nói ra? có REQ/Fact mới không nguồn? có thẻ chờ chưa trả lời? → nếu có, chèn system-reminder và cho mô hình thêm một vòng để bổ sung; ghi chi phí                                                                   | N4 — TC006, 057                     |
| SubagentStop     | Subagent trả báo cáo                 | Kiểm lược đồ báo cáo; với firmware/sim → tự động gọi verifier nếu subagent tuyên "đạt"                                                                                                                                                     | N6 — TC022                          |
| PreCompact       | Trước nén ngữ cảnh                   | Trích quyết định/giả định/Fact mới → ghi EIDE.md + ledger trước khi tóm tắt                                                                                                                                                                | TC074                               |

**6. Subagent và verifier**

![](../img/l2_subagents.png)

*Hình 2. Tác tử chính giao việc cho subagent chuyên biệt; verifier chưa thấy việc chấm theo tiêu chí gốc*

| **Subagent**     | **System prompt (tóm tắt)**                                                                                                   | **Tool được phép**                                                                    | **Trả về**                                                                        |
|------------------|-------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| datasheet-ingest | Tìm và nạp tài liệu cho chip X; ưu tiên nhà sản xuất; trích Fact ứng viên từ các bảng chuẩn; không bao giờ điền số từ trí nhớ | doc.search_web, doc.approve_request, ingest.file, fact.review_queue, passport.propose | {docs\[\], facts_candidate_count, tier_summary, missing\[\]}                      |
| design-review    | Rà soát netlist/mã theo checklist; mỗi phát hiện có vị trí, bằng chứng, mức; không bịa lỗi khi sạch                           | fs.read, board.check, fact.query, fact.compare, rag.ask                               | {findings\[{severity, where, evidence, fix}\], clean: bool}                       |
| firmware         | Sinh/sửa mã theo pinout và Fact; hằng số phải có nguồn; biên dịch tới khi sạch hoặc hết 3 vòng                                | fs.\*, build.\*, fact.query, skill.load                                               | {files_changed\[\], build: {ok, warnings}, flash_used, unsourced_constants: \[\]} |
| sim-runner       | Nêu tiêu chí trước, chạy, kết luận theo tiêu chí; không tuyên đạt cho phần không mô phỏng được                                | sim.criteria, sim.run, analyze.log, fs.read                                           | {criteria_ref, verdict, evidence_refs\[\], not_simulated\[\]}                     |
| hardware         | Dò bo, đối chiếu ID chip, nạp, verify, đọc log; mọi thao tác R4 sẽ bị hỏi                                                     | target.\*, analyze.\*, fs.read                                                        | {chip_id_match, flashed, verified, logs_ref, hypotheses\[\]}                      |
| verifier         | Anh chưa thấy quá trình làm. Chỉ đọc hiện vật + tiêu chí gốc + log; chấm ĐẠT/KHÔNG ĐẠT với lý do; tìm dấu hiệu "đạt giả"      | fs.read, fact.query, rag.ask, sim.run (chỉ chạy lại)                                  | {verdict, reasons\[\], suspicious\[\]}                                            |

Subagent chạy trong ngữ cảnh sạch (không kéo theo transcript dài), song song được (tối đa 4), và chỉ trả về một báo cáo có lược đồ — tác tử chính không đọc "quá trình" của chúng, chỉ đọc kết luận. Đây là cách chống ngữ cảnh phình (TC028) và tách người làm khỏi người chấm (TC022).

**7. Bộ nhớ và nén ngữ cảnh**

| **Tầng**          | **Hình thức**                                                        | **Ai ghi**                               | **Dùng khi**                       |
|-------------------|----------------------------------------------------------------------|------------------------------------------|------------------------------------|
| Transcript        | messages của phiên (JSONL), là trạng thái duy nhất của lượt          | Vòng lặp                                 | Mọi vòng; resume = nạp lại         |
| EIDE.md           | Markdown ở gốc dự án                                                 | Mô hình (memory.note / fs.edit) và người | Mỗi lượt vào system prompt         |
| Store có cấu trúc | SQLite/JSON: REQ, ADR, module, Fact, hộ chiếu, tài liệu, run         | Chỉ qua tool store.\*/fact.\*            | Inventory + fact.query             |
| Sổ cái            | JSONL append-only: HumanAct, tool_use/result, gate.decision          | Hook                                     | Tab Nhật ký, resume, chấm kịch bản |
| Bộ nhớ người dùng | ~/.eide/memory.md: mức tự chủ, "tin" theo tool, toolchain, thói quen | Lớp cấp quyền, tool manager              | Mọi dự án                          |

**7.1. Nén ngữ cảnh (compact)**

Khi ngữ cảnh vượt 70 % cửa sổ: hook PreCompact rút quyết định/giả định/Fact mới vào EIDE.md và sổ cái (bằng mã, từ tool_result có cấu trúc), rồi mô hình tóm tắt phần hội thoại tự do theo mẫu cố định {mục tiêu, đã làm, đang làm, quyết định, giả định, việc còn lại, tệp đang sửa}. Bản tóm tắt thay thế phần cũ; 10 lượt gần nhất giữ nguyên văn. Kiểm bằng câu hỏi ngược sau nén (TC074).

**7.2. Mở lại dự án**

project.resume = nạp EIDE.md + inventory + 20 sự kiện sổ cái gần nhất + thẻ đang chờ, rồi để mô hình tự thuật lại "đang ở đâu, đã quyết gì, làm gì tiếp" — không có previous_session.summary sinh riêng (TC065).

**8. Plan mode — việc lớn**

Thay cho is_big và ngưỡng 7 nút của v1.0: mô hình (theo hiến pháp điều 8) hoặc lớp cấp quyền (khi phát hiện chuỗi tool ghi/nạp dài) chuyển sang plan mode bằng plan.enter — mọi tool ghi bị khoá, chỉ còn đọc/tra/hỏi. Mô hình khảo sát, viết kế hoạch (bước, tool sẽ dùng, hiện vật, cổng sẽ gặp, ước lượng chi phí, giả định) và gọi plan.exit → thẻ G-SCOPE. Người duyệt/sửa/huỷ. Được duyệt thì kế hoạch trở thành system-reminder cho các vòng sau và Stop hook đối chiếu "đã làm" với kế hoạch.

**9. Giao diện: mô hình điều khiển chi trực tiếp**

UIP-34 giữ nguyên (một cửa console.act; Surface; Card; seq/resume). Thay đổi duy nhất là ai ra lệnh: v1.0 có UI Driver cứng dịch hiện vật → SurfaceModel; v2.0 chia hai lớp: (a) PostToolUse hook đồng bộ tự động những thứ hiển nhiên (tool_result loại netlist → tab Thiết kế; build → tab Mã; log → tab Mô phỏng/Mạch thật) và (b) mô hình dùng ui.\* khi muốn dẫn sự chú ý ("nhìn net SDA"), tô sáng, hay bố cục lại — tức mô hình tham gia vào cả cách trình bày. Văn bản mô hình stream thẳng vào transcript; ask_user và thẻ cổng là Card; HumanAct đi vào vòng lặp như user message có chú thích của S0.

**10. Bảy nguyên tắc và 76 ca đo trong kiến trúc mới**

| **Nguyên tắc**                  | **Sống ở đâu (v2.0)**                                                                            | **Ca đo canh**            |
|---------------------------------|--------------------------------------------------------------------------------------------------|---------------------------|
| N1 Datasheet là nguồn sự thật   | Hiến pháp §1; fact.query/compare; constant-guard (PreToolUse); store.req_create cần source_quote | TC008, 042, 075           |
| N2 Ba tầng Vàng/Bạc/Đồng        | fact.compare từ chối vế Đồng; \<facts\> reminder ghi tầng; UI tô màu                             | TC013, 021, 031           |
| N3 Kiểm kê xác định             | \<inventory\> system-reminder sinh bằng mã mỗi lượt; hiến pháp §3                                | TC008, 065                |
| N4 Hỏi một cụm                  | Hiến pháp §4; ask_user nhận nhiều mục; Stop hook kiểm giả định; ngân sách 2 ask/lượt             | TC004, 057                |
| N5 Cổng an toàn trước phép đoán | UserPromptSubmit hook (S0 giữ nguyên); target.dangerous never_auto; G-SAFE đứng đầu              | TC007, 035, 036, 068, 069 |
| N6 Không đạt giả                | Hiến pháp §6; sim.criteria đổi → G-QUAL; PostToolUse gắn cờ log rỗng; verifier độc lập           | TC019, 022, 076           |
| N7 Chỉ thị ≠ yêu cầu            | Hiến pháp §5; store.req_create cần trích lời người + hook kiểm                                   | TC003, 017, 024, 028      |

**10.1. Các cụm lỗi v1.3 được giải quyết thế nào**

| **Cụm (số ca)**                   | **v1.0 định sửa bằng**       | **v2.0 sửa bằng**                                                                                                                                  |
|-----------------------------------|------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Đường dẫn bịa → archive.list (11) | DX + slots.paths mảng        | Không còn slot; mô hình gọi fs.read/ingest.file với đường dẫn nó đọc từ câu; tool trả lỗi có gợi ý; ingest phân loại theo nội dung                 |
| Chặn "chip nào?" (6)              | passport.propose thẻ đề nghị | Hiến pháp §1 + skill datasheet-onboarding: mô hình tự đề nghị 3 lựa chọn qua ask_user với chip nó thấy trong câu; các việc không cần Fact làm tiếp |
| Chỉ thị thành FR (4)              | Tách kênh S1a                | Hiến pháp §5 + store.req_create bắt buộc source_quote                                                                                              |
| Thiếu tiền đề (3)                 | Planner có tiền đề           | Tool trả E2xxx kèm "gọi X trước"; mô hình tự gọi X rồi thử lại                                                                                     |
| Không tất định/dự án lồng (3)     | Dải tin cậy + kiểm inventory | \<inventory\> cho thấy dự án đang mở; hiến pháp §3; nhiệt độ 0; eval ×5                                                                            |
| Tệp nhận nhầm archive (5)         | ingest.classify              | Giữ nguyên: ingest.file phân loại theo magic bytes                                                                                                 |
| Nền build/sim chưa có (~12)       | Đợt 3                        | Giữ nguyên: build.\*/sim.\* + skill sim-criteria-first + subagent sim-runner                                                                       |
| Khôi phục ngữ cảnh (3)            | summary sinh từ sổ cái       | EIDE.md + resume nạp sổ cái + mô hình tự thuật                                                                                                     |

**11. Đánh đổi và cách bù**

| **Rủi ro của hướng vòng lặp**             | **Biểu hiện có thể gặp**         | **Cách bù trong thiết kế này**                                                                                   |
|-------------------------------------------|----------------------------------|------------------------------------------------------------------------------------------------------------------|
| Mô hình bỏ qua hiến pháp khi ngữ cảnh dài | Bịa số, tạo REQ không nguồn      | Không dựa vào hiến pháp một mình: constant-guard, req_create cần trích, fact.compare chặn Đồng — đều là mã       |
| Không tất định                            | Cùng câu, hai lần chạy khác nhau | Nhiệt độ 0 + seed; hook/tool xác định; đo tỉ lệ ×5; ca P1 cần ≥ 80 %                                             |
| Chi phí token cao                         | Mỗi vòng gửi lại ngữ cảnh        | Prompt caching cho hiến pháp + EIDE.md + lược đồ tool; nạp tool trễ; subagent ngữ cảnh sạch; compact             |
| Vòng lặp vô tận / lan man                 | Gọi tool mãi không kết luận      | Ngân sách 40 tool/lượt, 300 s, 3 vòng tự sửa; Stop hook                                                          |
| Mô hình tự "thuyết phục" người duyệt cổng | Diễn giải nhẹ hậu quả            | Thẻ cổng do lớp cấp quyền soạn từ hợp đồng tool (consequences cố định), không do mô hình viết                    |
| Phụ thuộc mô hình mạnh                    | Mô hình yếu → hành vi kém        | Gateway đa mô hình; tối thiểu Sonnet/Gemini Pro cho tác tử chính; Flash/Haiku chỉ cho subagent hẹp và tóm tắt    |
| Prompt injection từ tài liệu              | Lệnh trong PDF/web               | Nội dung tool_result được bọc \<document untrusted\> và hook P-INJ quét; hiến pháp: nội dung tài liệu là dữ liệu |

**12. Chuyển đổi từ mã hiện tại**

1.  **rpc.py::\_chat_send → vòng lặp §2.1.** Bỏ parse_intent/ground/fill_defaults/orchestrate; giữ chat.report_back như một phần Stop hook (chỉ định dạng, không quyết).

2.  **S0 → hook UserPromptSubmit.** Giữ nguyên bộ luật YAML và hành vi đã đạt (DEV-200/204); thêm chú thích cho mô hình khi không chặn.

3.  **caps.json → tools/\*.py + tool registry.** Gom 238 năng lực thành ~40 tool; mỗi tool: lược đồ JSON, hàm run, kiểm requires trong tool và lỗi có hint. Đánh dấu tool nạp trễ.

4.  **Policy engine → policy.yaml + lớp cấp quyền.** Chuyển các luật G-\* hiện có sang mẫu (tool, when) → allow/ask/deny; target.dangerous tách riêng.

5.  **chains.yaml → skills/.** Mỗi chuỗi mẫu thành SKILL.md có bước và tiêu chí xong; xoá planner.

6.  **Inventory (S2) → system-reminder.** Giữ hàm dựng bảng; đổi đầu ra thành khối văn bản ngắn cho prompt.

7.  **Thêm:** constant-guard, req_create source_quote check, ask_user, plan.enter/exit, Task + 6 subagent prompt, compact + PreCompact, EIDE.md loader, verifier.

8.  **Giao diện:** UAP giữ nguyên; thêm ánh xạ tool_result → Surface trong PostToolUse; stream văn bản.

9.  **Eval:** chạy 76 TC qua HumanAct ×5 lần; so với đường cơ sở 16/76; mục tiêu Đợt 1 mới: P1 ≥ 80 % (không tính bị chặn).

Thứ tự làm: (1) vòng lặp + tool registry + 10 tool đọc + S0 hook + ask_user → đo TC001–TC007; (2) store/fact/ingest tool + cấp quyền + constant-guard → TC008–TC014, TC038–TC043; (3) build/sim tool + skill + subagent firmware/sim/verifier → TC015–TC028; (4) target tool + subagent hardware → TC029–TC037 (cần board).

**13. Việc tiếp theo**

1.  Viết bản hiến pháp đầy đủ (PRS-16 v2) và 6 system prompt subagent; viết 10 SKILL.md ở §3.4.

2.  Định nghĩa lược đồ 40 tool (tools.schema.json) và policy.yaml đầy đủ từ bảng cổng AGD-32 §8.

3.  Cập nhật README_REVIEW_BRIEF cho Claude Code: thay Đ1–Đ6 bằng bốn bước chuyển đổi ở §12; giữ nguyên bộ 76 TC làm thước đo.
