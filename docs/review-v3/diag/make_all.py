# -*- coding: utf-8 -*-
from diagram_html import box, render, shoot
import html
names = []

# ================= l1_loop =================
b = f"""<div class="rows">
<div class="row">{box('ui','GIAO DIỆN (UAP — một cửa: console.act / HumanAct · chi hiển thị: 10 Surface)',['Transcript = chính dòng messages của vòng lặp · thẻ = kết quả tool ask_user · tác tử tự vẽ Surface bằng tool ui.* · văn bản LLM stream thẳng vào Console; UICommand từ hook PostToolUse'],'red wide')}</div>
<div class="row">{box('hook0','Hook UserPromptSubmit (S0)',['rule engine, 0 token','STOP · BACKREF · G-OPS · P-SAFE · P-LAW · P-QUAL','không chặn → gắn chú thích cho LLM'],'gold')}{box('ctx','LẮP NGỮ CẢNH (mỗi lượt)',['System: Hiến pháp (9 nguyên tắc) + EIDE.md','System-reminder: <inventory> · <facts> · <human_edits> · <pending> · <plan>','Skill đang nạp · gợi ý skill theo câu','Messages: transcript (nén khi > 70 %)'],'teal','style="flex:2 1 0"')}</div>
<div class="row">{box('llm','LLM (Claude / Gemini)',['đọc câu người + ngữ cảnh → nghĩ →','nói với người | gọi 1..n tool | hỏi (ask_user)','tự lập kế hoạch (plan mode nếu việc lớn)','tự phục hồi từ lỗi tool (thông điệp lỗi có gợi ý)'],'plain')}{box('pre','tool_use → Hook PreToolUse + CẤP QUYỀN',['policy: allow / ask / deny theo (tool, mẫu đầu vào, rủi ro R0–R4, mức A0–A4)','ask → thẻ cổng riêng · deny → lỗi trả về LLM (nét đứt)','G-OPS luôn ask · constant-guard trên fs.write · fact.compare chặn vế ĐỒNG · kiểm explain · sandbox'],'gold')}{box('tools','allow → TOOLS (≈40 nhóm, nạp trễ, chạy trong sandbox)',['store.* · fact.* · rag.* · passport.* · doc.search · ingest.*','fs.read/edit/write · bash · build.* · sim.* · target.* · board.check · calc.*','ask_user · ui.surface_* · history.* · snapshot.* · Task (subagent) · memory.note · skill.load · plan.*'],'grey')}</div>
<div class="row">{box('post','Hook PostToolUse / Stop',['sau mỗi tool: changeset + ledger.append (append-only) · ui.surface đồng bộ tự động · đánh dấu STALE · lint (log rỗng ≠ đạt)','Stop: giả định đã nói ra? sửa của người đã nhắc? hiện vật có explain? · SubagentStop: verifier độc lập · PreCompact: rút cấu trúc vào M2 trước khi nén'],'gold wide')}</div>
<div class="row center"><div class="note">Vòng lặp: LLM đọc tool_result → gọi tool tiếp / trả lời người / hỏi · Ngân sách: ≤ 40 tool/lượt · 300 s · nén ngữ cảnh khi > 70 % cửa sổ</div></div>
</div>"""
ar = [dict(**{'from': 'ui', 'to': 'hook0', 'dir': 'down', 'label': 'HumanAct', 'color': '#B8121F'}), dict(**{'from': 'hook0', 'to': 'ctx', 'dir': 'right'}), dict(**{'from': 'ctx', 'to': 'llm', 'dir': 'down', 'ox': -180, 'ox2': 0}),
      dict(**{'from': 'llm', 'to': 'pre', 'dir': 'right', 'oy': -10, 'oy2': -10}), dict(**{'from': 'pre', 'to': 'llm', 'dir': 'left', 'oy': 14, 'oy2': 14, 'color': '#777', 'dash': True}),
      dict(**{'from': 'pre', 'to': 'tools', 'dir': 'right'}), dict(**{'from': 'tools', 'to': 'post', 'dir': 'down', 'label': 'tool_result', 'color': '#1B7F79', 'ox2': 0}),
      dict(**{'from': 'post', 'to': 'llm', 'dir': 'up', 'label': 'tool_result → LLM', 'color': '#1B7F79', 'ox': -300, 'ox2': 40, 'lx': 60})]
render('l1_loop', b, ar, width=1000, gap=44); names.append('l1_loop')

# ================= l2_subagents =================
subs = [('datasheet-ingest', ['doc.search · ingest · fact.extract', 'KHÔNG fs.write, KHÔNG target']), ('design-review', ['board.check · fact.compare', 'chỉ đọc + báo cáo']), ('firmware', ['fs.* · build.* · skill HAL', 'sandbox; không target']),
        ('sim-runner', ['sim.* · analyze.log', 'tiêu chí nêu trước']), ('hardware', ['target.* · G-OPS luôn ask', 'không fs.write']), ('verifier', ['chưa thấy việc; chỉ đọc', 'chấm theo tiêu chí gốc'])]
b = f"""<div class="rows"><div class="row center">{box('main','Tác tử chính (orchestrator)',['toàn bộ tool · nói chuyện với người · giao việc bằng Task(subagent, prompt)'],'teal fixed','style="width:420px"')}</div>
<div class="row">{''.join(box('s'+str(i),t,ls,'plain') for i,(t,ls) in enumerate(subs))}</div>
<div class="row center"><div class="note">Mỗi subagent: system prompt riêng + tập tool bị giới hạn + ngữ cảnh sạch; trả về MỘT báo cáo có cấu trúc ≤ 800 token; chạy song song được (tối đa 4)</div></div></div>"""
render('l2_subagents', b, [dict(**{'from': 'main', 'to': 's' + str(i), 'dir': 'down', 'color': '#777'}) for i in range(6)], width=1000, gap=30); names.append('l2_subagents')

# ================= u1_topology =================
b = f"""<div class="rows">
<div class="row center"><div class="note">Kênh máy–máy (không có người): hello · resume(seq) · ui.status · heartbeat</div></div>
<div class="row">{box('hum','NGƯỜI',['gõ · bấm · duyệt · sửa · kéo thả · dừng khẩn','KHÔNG có đường nào khác vào lõi'],'grey fixed','style="width:190px"')}{box('con','BÀN GIAO TIẾP (Console) — điểm giao tiếp người–máy duy nhất',['Dòng hội thoại (transcript): mọi HumanAct + mọi lời tác tử','Ô nhập + thẻ (card) đang chờ','Vào lõi: console.act (một RPC, một loại thông điệp HumanAct)'],'red')}{box('core','LÕI TÁC TỬ',['← HumanAct (console.act, đỏ) · → UICommand (console.post, card.*, xanh)','Vòng lặp · hook · cấp quyền · tool','UI Driver: hiện vật → SurfaceModel; câu hỏi/cổng → Card; tiến trình → Run','Sổ cái = transcript + sự kiện'],'teal')}</div>
<div class="row">{box('surf','BỀ MẶT HIỂN THỊ (10 Surface = 10 tab) — chi hiển thị của tác tử',['surface.set / patch / append / focus / highlight / lock ← tác tử vẽ; người chỉ NHÌN và CHẠM; mọi cái chạm → HumanAct{origin.surface} qua Console'],'gold wide')}</div></div>"""
ar = [dict(**{'from': 'hum', 'to': 'con', 'dir': 'right', 'color': '#B8121F'}), dict(**{'from': 'con', 'to': 'core', 'dir': 'right', 'color': '#B8121F', 'oy': -14, 'oy2': -14}),
      dict(**{'from': 'core', 'to': 'con', 'dir': 'left', 'color': '#1B7F79', 'oy': 14, 'oy2': 14}), dict(**{'from': 'core', 'to': 'surf', 'dir': 'down', 'label': 'UICommand surface.*', 'color': '#1B7F79', 'ox': 60, 'ox2': 250}),
      dict(**{'from': 'surf', 'to': 'con', 'dir': 'up', 'label': 'mọi cái chạm → HumanAct', 'color': '#B8121F', 'ox': -150, 'ox2': 0})]
render('u1_topology', b, ar, width=1000, gap=40); names.append('u1_topology')

# ================= u2_seq (sequence) =================
lanes = ['Người', 'Surface "Tri thức mạch"', 'Console', 'Lõi (UI Driver)', 'Kho Fact / Sổ cái']
msgs = [(3, 1, 'surface.patch {facts[12].tier:"BẠC"} (seq 41)', '#1B7F79'), (0, 1, 'bấm "Xác nhận" dòng Fact #12', '#B8121F'), (1, 2, 'HumanAct{kind:confirm, target:fact:12, origin:{surface:"ckm", row:12}}', '#B8121F'),
        (2, 3, 'console.act (id h-0917, seq 18) — đồng thời ghi 1 dòng vào transcript', '#B8121F'), (3, 4, 'fact.review(confirm) → tier VÀNG · ledger human.confirm', '#1F2A44'),
        (3, 2, 'console.post {ack h-0917, "Đã ghi Vàng: vdd.max 5,5 V (p.258)"} (seq 42)', '#1B7F79'), (3, 1, 'surface.patch {facts[12].tier:"VÀNG", approved_by:"user"} (seq 43)', '#1B7F79'), (2, 0, 'transcript: [Bạn] Xác nhận Fact #12 · [Tác tử] Đã ghi Vàng…', '#555')]
n = len(lanes); lw = 100 / n
body = '<div class="seq">' + ''.join(f'<div class="lane">{html.escape(l)}</div>' for l in lanes)
body += ''.join(f'<div class="vl" style="left:{(i+0.5)*lw}%"></div>' for i in range(n))
for a, bb, t, c in msgs:
    x1, x2 = (a + 0.5) * lw, (bb + 0.5) * lw
    left, right = min(x1, x2), max(x1, x2); cls = 'left' if x2 < x1 else ''
    body += f'<div class="msg" style="--c:{c}"><div class="line {cls}" style="left:{left}%;width:{right-left}%"></div><div class="txt" style="left:{(left+right)/2}%;transform:translateX(-50%)">{html.escape(t)}</div></div>'
body += '</div>'
render('u2_seq', body, [], width=1000, nlanes=n); names.append('u2_seq')

# ================= x1_edit_sync =================
steps = [('1. Người sửa trên Surface', ['widget sửa theo loại hiện vật (đặc tả / Fact / pinout / mã / tiêu chí)', 'soft-lock nếu tác tử đang sửa → cảnh báo nhưng vẫn cho sửa'], 'red'),
         ('2. Lưu → HumanAct{edit}', ['qua console.act (một cửa)', 'base_version + patch + note "vì sao"', 'ghi sổ cái TRƯỚC khi xử lý (write-ahead)'], 'red'),
         ('3. Kiểm & hợp nhất', ['lược đồ hợp lệ?', '3-way merge nếu tác tử đã đổi', 'số mới không nguồn → Fact tầng NGƯỜI'], 'gold'),
         ('4. Changeset (author: human)', ['version +1 · inverse ops', 'đánh dấu hiện vật phụ thuộc STALE', 'git commit (tệp) + event (store)'], 'gold'),
         ('5. Đồng bộ bộ nhớ tác tử', ['EIDE.md §"Người vừa sửa"', 'system-reminder <human_edits> lượt sau', 'Fact NGƯỜI vào kho'], 'teal'),
         ('6. Tác tử phản hồi', ['bắt buộc nhắc tới thay đổi (hook Stop kiểm)', 'đề nghị chạy lại phần STALE', 'không ghi đè im lặng (G-FILE)'], 'teal')]
b = '<div class="rows"><div class="row">' + ''.join(box(f'e{i}', t, ls, c) for i, (t, ls, c) in enumerate(steps[:3])) + '</div><div class="row">' + ''.join(box(f'e{i+3}', t, ls, c) for i, (t, ls, c) in enumerate(steps[3:])) + '</div><div class="row center"><div class="note">Dòng transcript sinh ra ở bước 2: "[Bạn] Sửa đặc tả v3: thêm ràng buộc pin 3,0–4,2 V — vì: chạy ngoài trời"</div></div></div>'
ar = [dict(**{'from': 'e0', 'to': 'e1', 'dir': 'right'}), dict(**{'from': 'e1', 'to': 'e2', 'dir': 'right'}), dict(**{'from': 'e2', 'to': 'e3', 'dir': 'down', 'ox': 0, 'ox2': 0, 'label': 'tiếp'}), dict(**{'from': 'e3', 'to': 'e4', 'dir': 'right'}), dict(**{'from': 'e4', 'to': 'e5', 'dir': 'right'})]
render('x1_edit_sync', b, ar, width=1000, gap=44); names.append('x1_edit_sync')

# ================= x2_changeset (timeline) =================
cs = [('cs-101', 'agent:run-40', 'REQ v1', True, ''), ('cs-102', 'agent:run-40', 'modules', True, ''), ('cs-103', 'human', 'REQ v2 (+pin)', True, 'human'), ('cs-104', 'agent:run-41', 'code ×3', True, ''), ('cs-105', 'agent:run-41', 'build OK', True, ''),
      ('cs-106', 'agent:run-41', 'sim ĐẠT', True, ''), ('cs-107', 'human', '★ snapshot "v0.3-ổn"', True, 'snap'), ('cs-108', 'agent:run-42', 'flash + verify', False, ''), ('cs-109', 'agent:run-43', 'code ×2', True, ''), ('cs-110', 'human', 'rollback → cs-107', True, 'human')]
tl = '<div class="tl">' + ''.join(f'<div class="cs {k}" id="{i}"><b>{i}</b><i>{w}</i>{html.escape(x)}<i class="{"u" if u else "n"}">{"↶ hoàn tác được" if u else "⚠ không hoàn tác"}</i></div>' for i, w, x, u, k in cs) + '</div>'
b = f"""<div class="rows"><div class="row center"><div class="note b">Dòng thời gian dự án = chuỗi Changeset (append-only): ai · cái gì · có hoàn tác được không</div></div>
<div class="row"><div style="width:100%">{tl}</div></div>
<div class="row center"><div class="note red">rollback = changeset MỚI áp inverse ops của cs-108..109 — cs-108 (flash) không hoàn tác được → cảnh báo: mạch vẫn chạy bản cũ</div></div>
<div class="row">{box('n1','Ba mức hoàn tác',['(1) một changeset · (2) cả một lượt (run) · (3) về snapshot — lịch sử không bao giờ bị xoá'],'plain')}{box('n2','SNAPSHOT (bất biến)',['git tag + store export + EIDE.md + ledger ptr + hash ELF + bằng chứng sim + REQ đã đạt'],'gold')}{box('n3','Rẽ nhánh & phụ thuộc',['branch "phuong-an-B" từ snapshot → so sánh → gộp','REQ → module → code → build → sim → flash: đổi thượng nguồn → hạ nguồn STALE (đánh dấu, không tự xoá)'],'plain')}</div></div>"""
render('x2_changeset', b, [], width=1000, gap=18); names.append('x2_changeset')

# ================= x3_dualform =================
b = f"""<div class="rows"><div class="row">{box('m','DẠNG MÁY (canonical)',['JSON/YAML/tệp có lược đồ','tác tử đọc & ghi qua tool','kho có phiên bản (git/store)','nguồn: Fact / lời người / tool'],'teal')}{box('x','LỚP GIẢI THÍCH (explain — 6 trường bắt buộc)',['tóm tắt 1 câu · vì sao','nguồn + tầng tin cậy','khác gì so với bản trước','việc tiếp theo · tin được đến đâu'],'gold')}{box('h','DẠNG NGƯỜI (view)',['khối UI theo loại (bảng, đồ thị, diff, form…)','widget sửa được đúng trường','nút: Vì sao? · Nguồn · Hoàn tác','Lưu → HumanAct{edit}'],'red')}</div>
<div class="row center"><div class="note red">→ render → · ← người sửa: dạng người → chuyển ngược về dạng máy (parse + kiểm lược đồ) → changeset author = human</div></div></div>"""
ar = [dict(**{'from': 'm', 'to': 'x', 'dir': 'right'}), dict(**{'from': 'x', 'to': 'h', 'dir': 'right'})]
render('x3_dualform', b, ar, width=1000, gap=30); names.append('x3_dualform')

# ================= m1_tiers =================
tiers = [('M0 · Working (một lượt)', ['tool_result thô, stream, card · sống: đến hết lượt · ghi: vòng lặp · đọc: LLM'], 'plain'),
         ('M1 · Transcript phiên', ['messages JSONL (đã cắt/ghim/nén) · sống: phiên → lưu để resume · ghi: vòng lặp + compact'], 'teal'),
         ('M2 · Bộ nhớ dự án (nguồn sự thật)', ['EIDE.md · Store (REQ/ADR/Fact/CKM) · Ledger + Changeset · Blob (hash) · sống: vĩnh viễn · ghi: CHỈ qua tool'], 'gold'),
         ('M3 · Bộ nhớ người dùng', ['~/.eide/memory.md: tự chủ, "tin", thói quen trình bày, toolchain · ghi: policy/UI · người sửa/quên được'], 'red'),
         ('M4 · Tri thức toàn cục (chỉ đọc)', ['registry chip · ISA manifest · skill · hiến pháp · cache tài liệu theo hash · ghi: theo phiên bản gói'], 'grey')]
blocks = [('Hiến pháp (cache)', '2 k', 'grey'), ('Lược đồ tool hiển thị (cache)', '4 k', 'grey'), ('EIDE.md', '≤ 3 k', 'gold'), ('<inventory> (mã dựng)', '≤ 0,8 k', 'gold'), ('<facts> theo thực thể 3 lượt gần', '≤ 2 k', 'gold'),
          ('<human_edits> · <pending> · <plan>', '≤ 1,6 k', 'red'), ('Skill đã nạp', '≤ 6 k', 'grey'), ('Bản tóm tắt phiên (sau nén)', '≤ 3 k', 'teal'), ('Transcript gần nhất (≥ 10 lượt + ghim)', 'phần còn lại', 'teal'), ('Dự trữ: trả lời + tool_result lượt này', '20 %', '')]
left = '<div class="rows" style="flex:1 1 0;gap:10px">' + ''.join(box(f't{i}', t, ls, c) for i, (t, ls, c) in enumerate(tiers)) + '</div>'
right = '<div class="box plain" id="cw" style="flex:1 1 0"><h4>CỬA SỔ NGỮ CẢNH MỖI LƯỢT (ngân sách cố định theo khối)</h4><div class="stack">' + ''.join(f'<div class="{c}"><span>{html.escape(n)}</span><span>{s}</span></div>' for n, s, c in blocks) + '</div><p class="note red">ngưỡng: 60 % cảnh báo · 70 % nén C1+C2 · 85 % nén C3 · 95 % khẩn cấp</p></div>'
b = f'<div class="row" style="gap:130px">{left}{right}</div>'
ar = [dict(**{'from': 't2', 'to': 'cw', 'dir': 'right', 'label': 'M2 → khối xác định', 'color': '#B58900', 'oy2': -60, 'ly': -6, 'lx': -4}), dict(**{'from': 't1', 'to': 'cw', 'dir': 'right', 'label': 'M1 → tóm tắt + gần nhất', 'color': '#1B7F79', 'oy2': 90, 'ly': 26, 'lx': 4}), dict(**{'from': 't3', 'to': 'cw', 'dir': 'right', 'label': 'M3 → thói quen', 'color': '#B8121F', 'oy2': -20, 'ly': 14, 'lx': -10})]
render('m1_tiers', b, ar, width=1000); names.append('m1_tiers')

# ================= m2_ladder =================
steps = [('C0 · Liên tục (mỗi tool_result)', ['cắt theo chính sách tool', 'blob + ref thay nguyên văn', 'dedup đọc lại cùng version', '0 token'], 'plain'),
         ('C1 · Thu gọn cơ học (60–70 %)', ['stub tool_result cũ > 8 lượt', 'gộp stream delta', 'bỏ card đã đóng', '0 token'], 'gold'),
         ('C2 · Tóm tắt có cấu trúc (70 %)', ['PreCompact rút ADR/giả định/Fact/sửa của người → M2 (bằng mã)', 'LLM tóm phần cũ theo lược đồ 10 mục', 'giữ ≥ 10 lượt + mọi message ghim'], 'teal'),
         ('C3 · Bậc thang (85 %)', ['tóm tắt của các tóm tắt', 'chuỗi tóm tắt lưu ledger (hash), phát lại được', 'K giảm 10 → 6 lượt'], 'red'),
         ('C4 · Khẩn cấp (95 %)', ['bỏ toàn bộ tool_result thô', 'chỉ giữ ghim + tóm tắt', 'báo người, gợi ý mở phiên mới'], 'red')]
b = '<div class="rows"><div class="row center"><div class="note b">Bất biến: không mất quyết định · giả định · Fact · sửa của người · thẻ chờ · kế hoạch đã duyệt — phần có cấu trúc luôn ở M2, nén chỉ chạm văn bản tự do</div></div><div class="row">' + ''.join(box(f'c{i}', t, ls, c) for i, (t, ls, c) in enumerate(steps)) + '</div><div class="row">' + box('chk', 'KIỂM SAU NÉN (hook PostCompact) — nén chỉ được chấp nhận khi qua kiểm', ['3 câu hỏi ngược sinh từ ledger (quyết định, giả định, sửa của người gần nhất) → LLM trả lời từ ngữ cảnh ĐÃ NÉN → so với ledger bằng mã → sai ≥ 1 → huỷ nén, K += 4, thử lại (tối đa 2 lần); vẫn sai → giữ nguyên, báo người'], 'gold wide') + '</div></div>'
ar = [dict(**{'from': f'c{i}', 'to': f'c{i+1}', 'dir': 'right'}) for i in range(4)] + [dict(**{'from': 'c2', 'to': 'chk', 'dir': 'down', 'color': '#B58900', 'label': 'sau C2/C3'})]
render('m2_ladder', b, ar, width=1000, gap=24); names.append('m2_ladder')

shoot(names)
print('done', names)
