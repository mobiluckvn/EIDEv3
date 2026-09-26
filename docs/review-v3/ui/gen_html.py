# -*- coding: utf-8 -*-
import json, html
from ui_model import UI, REQS, all_items

REQ = {r['id']: r for r in REQS}
TAB_AREAS = ["A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A14"]
TAB_LABEL = {"A2": "Yêu cầu & Giải pháp", "A3": "Tài liệu & Nguồn", "A4": "Tri thức mạch", "A5": "Thiết kế", "A6": "Công cụ", "A7": "Mã nguồn",
             "A8": "Mô phỏng", "A9": "Mạch thật", "A10": "Nhật ký", "A11": "Lịch sử", "A14": "Dự án & Bộ nhớ"}
# hạ nguồn khi người sửa một khối (dùng cho STALE demo)
DOWNSTREAM = {"A2.1": ["A2.3", "A5.1", "A7.1", "A8.2"], "A2.3": ["A5.1", "A5.2", "A5.3", "A7.1"], "A4.2": ["A4.4", "A7.1"], "A5.2": ["A5.3", "A7.1", "A7.3"],
              "A5.3": ["A5.4", "A5.5", "A7.1"], "A7.1": ["A7.3", "A8.2", "A9.2"], "A8.1": ["A8.2"], "A14.2": []}

# --------- nội dung mẫu cho một số khối (dự án: bộ chuyển LAN→USB cho TV)
RICH = {}
RICH["A2.1"] = """
<table class="t"><tr><th>Mã</th><th>Yêu cầu</th><th>Tiêu chí đo</th><th>Trích lời anh</th><th>Tầng</th></tr>
<tr><td>FR-01</td><td contenteditable data-edit="A2.1.3">Nhận tệp phim qua LAN và lưu vào bộ nhớ trong</td><td contenteditable data-edit="A2.1.3">≥ 5 MB/s</td><td class="q">"copy phim qua mạng LAN vào đó"</td><td><span class="tier nguoi">NGƯỜI</span></td></tr>
<tr><td>FR-02</td><td contenteditable data-edit="A2.1.3">TV đọc được bộ nhớ như USB Mass Storage</td><td contenteditable data-edit="A2.1.3">TV liệt kê được tệp trong 10 s</td><td class="q">"cắm vào TV… để TV xem"</td><td><span class="tier nguoi">NGƯỜI</span></td></tr>
<tr><td>UR-03</td><td contenteditable data-edit="A2.1.3">Nguồn pin 3,0–4,2 V</td><td contenteditable data-edit="A2.1.3">chạy ≥ 8 h</td><td class="q">"phải chạy bằng pin" (v2)</td><td><span class="tier nguoi">NGƯỜI</span></td></tr>
</table>"""
RICH["A2.2"] = """<table class="t"><tr><th>Rủi ro</th><th>Mức</th><th>Đề xuất</th><th>Nguồn</th></tr>
<tr><td>TV đang mount USB mà thiết bị ghi tệp mới → hỏng hệ thống tệp (TV có bộ đệm riêng)</td><td><b class="sev-maj">Nghiêm trọng</b></td><td>Ngắt–gắn lại USB sau khi copy; hoặc MTP; hoặc chia phân vùng</td><td><a class="src" data-tier="dong">tri thức chung — ĐỒNG</a></td></tr></table>"""
RICH["A2.3"] = """<table class="t"><tr><th></th><th>A · SBC Linux (USB gadget)</th><th>B · MCU + Ethernet PHY + eMMC</th><th>C · DLNA/SMB thay USB</th></tr>
<tr><td>Chi phí</td><td><i class="dong">~1,2 triệu (ước)</i></td><td><i class="dong">~600 k (ước)</i></td><td><i class="dong">~900 k (ước)</i></td></tr>
<tr><td>Thông lượng</td><td><a class="src" data-tier="vang">≥ 20 MB/s · USB 2.0 HS, DS p.12</a></td><td><a class="src" data-tier="vang">≈ 1 MB/s · ENC28J60 DS p.4</a> <b class="sev-blk">✗ FR-01</b></td><td>phụ thuộc TV</td></tr>
<tr><td>Độ khó</td><td>Thấp</td><td>Cao</td><td>Trung bình (TV phải hỗ trợ)</td></tr>
<tr><td>Rủi ro</td><td>Nguồn tiêu thụ cao (UR-03)</td><td>Không đạt FR-01 với 5 MB/s</td><td>Không đúng "cắm USB"</td></tr>
<tr><td></td><td><button class="btn act" data-act="A2.3.3" data-gate="G-DESIGN">Chọn A</button></td><td><button class="btn" data-act="A2.3.3" data-gate="G-DESIGN">Chọn B</button></td><td><button class="btn" data-act="A2.3.3" data-gate="G-DESIGN">Chọn C</button></td></tr></table>"""
RICH["A4.2"] = """<table class="t"><tr><th>Khoá</th><th>Giá trị</th><th>Điều kiện</th><th>Tầng</th><th>Nguồn</th><th></th></tr>
<tr><td>vdd.max</td><td>5,5 V</td><td>TA −40…85 °C</td><td><span class="tier vang">VÀNG</span></td><td><a class="src" data-tier="vang">DS40002061B p.258</a></td><td></td></tr>
<tr><td>i2c.sda.pullup_typ</td><td>4,7 kΩ</td><td>100 kHz, 3,3 V</td><td><span class="tier bac">BẠC</span></td><td><a class="src" data-tier="bac">DS p.215 (chưa xác nhận)</a></td><td><button class="btn sm" data-act="A4.2.2">Xác nhận</button></td></tr>
<tr><td>usb.hs.throughput</td><td>20 MB/s</td><td>bulk</td><td><span class="tier vang">VÀNG</span></td><td><a class="src" data-tier="vang">DS p.12</a></td><td></td></tr>
<tr><td>i2c.timeout</td><td>50 ms</td><td>—</td><td><span class="tier nguoi">NGƯỜI</span></td><td><a class="src" data-tier="nguoi">anh cho (h-0940), chưa có tài liệu</a></td><td><button class="btn sm" data-act="A4.2.4">Tìm tài liệu chứng thực</button></td></tr>
<tr><td>flash.size</td><td>32 768 B</td><td>—</td><td><span class="tier vang">VÀNG</span></td><td><a class="src" data-tier="vang">DS p.1</a></td><td></td></tr>
<tr><td>eth.throughput_est</td><td><i>~1 MB/s</i></td><td>—</td><td><span class="tier dong">ĐỒNG</span></td><td><a class="src" data-tier="dong">tri thức chung — chưa kiểm chứng</a></td><td><button class="btn sm" data-act="A4.2.4">Tìm tài liệu</button></td></tr></table>"""
RICH["A5.2"] = """<table class="t"><tr><th>Chân</th><th>Tên</th><th>Chức năng</th><th>Net</th><th>AF hợp lệ (Fact)</th></tr>
<tr><td>27</td><td>PC4</td><td><select data-edit="A5.2.2"><option>SDA (TWI)</option><option>ADC4</option><option>GPIO</option></select></td><td>SDA</td><td><a class="src" data-tier="vang">DS p.85</a></td></tr>
<tr><td>28</td><td>PC5</td><td><select data-edit="A5.2.2"><option>SCL (TWI)</option><option>ADC5</option><option>GPIO</option></select></td><td>SCL</td><td><a class="src" data-tier="vang">DS p.85</a></td></tr>
<tr><td>2</td><td>PD0</td><td><select data-edit="A5.2.2"><option>RXD</option><option>GPIO</option></select></td><td>UART_RX</td><td><a class="src" data-tier="vang">DS p.90</a></td></tr>
<tr class="conf"><td>16</td><td>PB2</td><td><select data-edit="A5.2.2"><option>SS</option><option>OC1B</option></select></td><td>CS_ETH</td><td><b class="sev-maj">af_conflict với OC1B (PWM)</b></td></tr></table>"""
RICH["A5.5"] = """<table class="t"><tr><th>Mức</th><th>Vị trí</th><th>Phát hiện</th><th>Bằng chứng</th><th>Sửa</th></tr>
<tr><td><b class="sev-blk">BLOCKER</b></td><td>U2.VDDIO / net VBUS_5V</td><td>Quá áp</td><td><a class="src" data-tier="vang">VDDIO.max 3,6 V · DS p.61</a></td><td>Cấp từ +3V3</td></tr>
<tr><td><b class="sev-maj">MAJOR</b></td><td>net SDA, SCL</td><td>Thiếu điện trở kéo lên</td><td><a class="src" data-tier="bac">pull-up 4,7 kΩ · DS p.215</a></td><td>Thêm R 4,7 kΩ lên +3V3</td></tr>
<tr><td><b class="sev-maj">MAJOR</b></td><td>NRST</td><td>Chỉ có một nút, không có R/C</td><td><a class="src" data-tier="vang">RM §6.2</a></td><td>R 10 kΩ + C 100 nF</td></tr></table>"""
RICH["A7.2"] = """<pre class="diff"><span class="f">src/drv_i2c.c · v8 → v9 (đề xuất) · lý do: FR-01 timeout, Fact i2c.timeout (NGƯỜI)</span>
 static uint8_t i2c_wait(void) {
-    while (!(TWCR &amp; (1&lt;&lt;TWINT)));
+    uint32_t t0 = millis();
+    while (!(TWCR &amp; (1&lt;&lt;TWINT))) {
+        if (millis() - t0 &gt; I2C_TIMEOUT_MS) return I2C_ERR_TIMEOUT;   /* I2C_TIMEOUT_MS = 50 — Fact NGƯỜI h-0940 */
+    }
     return I2C_OK;
 }</pre>"""
RICH["A7.3"] = """<div class="kv"><div><b>Kết quả</b> <span class="ok">Biên dịch OK</span> · 2 warning (đã giải thích)</div>
<div><b>Flash</b> <div class="bar"><div style="width:9.6%"></div></div> 3 148 / 32 768 B <a class="src" data-tier="vang">flash.size · DS p.1</a></div>
<div><b>RAM</b> <div class="bar"><div style="width:31%"></div></div> 634 / 2 048 B <a class="src" data-tier="vang">DS p.1</a></div>
<div><b>Warning 1</b> <code>unused variable 'tmp'</code> — không ảnh hưởng; đề nghị xoá ở lần sửa sau</div></div>"""
RICH["A8.2"] = """<table class="t"><tr><th>Assert</th><th>Đo REQ</th><th>Ngưỡng (nguồn)</th><th>Kết quả</th><th>Bằng chứng</th></tr>
<tr><td>uart_contains "T=25"</td><td>FR-04</td><td>≤ 2 s (<a class="src" data-tier="nguoi">anh cho</a>)</td><td><span class="ok">ĐẠT</span></td><td>log 00:00:01.482</td></tr>
<tr><td>no_hardfault</td><td>NFR-01</td><td>—</td><td><span class="ok">ĐẠT</span></td><td>CFSR = 0</td></tr>
<tr><td>gpio_toggles LED</td><td>FR-05</td><td>1 Hz ±5 %</td><td><span class="ok">ĐẠT</span></td><td>VCD 0,50 s / 0,50 s</td></tr>
<tr><td>eth_rx ≥ 5 MB/s</td><td>FR-01</td><td>5 MB/s</td><td><b class="sev-maj">KHÔNG MÔ PHỎNG ĐƯỢC</b></td><td>simavr không mô hình hoá ENC28J60 → đề xuất HIL</td></tr></table>"""
RICH["A9.1"] = """<div class="kv"><div><b>Cổng</b> /dev/tty.usbmodem14201 · <b>Probe</b> ST-Link V2 · <b>ID chip</b> 0x410 → STM32F103 <span class="ok">khớp hộ chiếu st.stm32f103c8@1.0.0</span></div>
<div class="warn">Bo đang chạy bản <code>fw-0x9a1c</code> (run-42) ≠ mã hiện tại v9 — <button class="btn sm" data-act="A9.2.1" data-gate="G-FLASH">Nạp bản v9</button></div></div>"""
RICH["A11.1"] = """<div class="tl" id="timeline"></div>"""
RICH["A11.2"] = """<div id="snaps"></div>"""
RICH["A14.2"] = """<textarea data-edit="A14.2.1" rows="9" style="width:100%"># EIDE.md — Bộ chuyển LAN→USB cho TV
## Mục tiêu (v2, 24/09): copy phim qua LAN, TV đọc như USB, chạy pin 8 h
## Chip & bo: ATmega328P (mchp.atmega328p@1.0.0, DS40002061B) · ISA avr8 · avr-gcc 13.2
## Quyết định: ADR-03 dùng MTP thay Mass Storage (TV mount đồng thời gây hỏng FS)
## Giả định đang dùng: -Os · TV đọc exFAT (chưa xác nhận)
## Đừng: không bật RDP/fuse khi chưa có snapshot release
## Người vừa sửa: 25/09 FR-01 ≥5 MB/s (vì phim 4K) — tác tử đã nhắc ✓</textarea>"""
RICH["A14.3"] = """<pre class="inv">project: lan-usb-tv (nhánh: main) · chặng: C4
requirements: 3 (v2) · options: 3 (chọn: A) · passports: 1 (avr8 ✓ toolchain)
facts: VÀNG 98 · BẠC 41 · NGƯỜI 2 · ĐỒNG 1 · docs: 2 (DS 7810D, TMP102 rev C)
modules: 4 · netlist: v3 · erc: 1 blocker, 2 major · code: 6 tệp · build: OK (3,1 KB)
sim: run-41 4/5 (1 không mô phỏng được) · target: run-42 flash+verify ✓ (fw 0x9a1c)
runs: last run-43 stopped@node5 · STALE: A8.2, A9.2 · snapshot gần nhất: snap-3 (+4 changeset)</pre>"""

# --------- render
def esc(s): return html.escape(s, quote=True)
def badges(reqs): return "".join(f'<span class="req" title="{esc(REQ[r]["desc"])}">{r}</span>' for r in reqs)

def render_widget(w, block):
    kind = w['kind']
    lbl = f'<span class="wid">{w["id"]}</span>'
    if kind == "edit":
        ctrl = f'<button class="btn save" data-save="{w["id"]}" data-block="{block["id"]}">Lưu</button>'
    elif kind == "action":
        gate = next((r for r in w['reqs'] if r.startswith("G-")), "")
        ctrl = f'<button class="btn act" data-act="{w["id"]}" data-gate="{gate}">{esc(w["name"].split("(")[0].split("→")[0].strip()[:38])}</button>'
    elif kind == "nav":
        ctrl = '<button class="btn sm" data-nav="A11">Mở</button>'
    else:
        ctrl = ''
    return f'<div class="w w-{kind}" data-id="{w["id"]}">{lbl}<span class="wn">{esc(w["name"])}</span>{ctrl}<span class="badges">{badges(w["reqs"])}</span></div>'

def explain_html(block):
    art = block.get('art', '')
    return f"""<div class="explain">
<div><b>Tóm tắt</b> {esc(block['name'])} — hiện vật {esc(art or 'khối UI')} của dự án lan-usb-tv, phiên bản hiện tại do <i>agent:run-41</i> tạo.</div>
<div><b>Vì sao</b> Sinh từ REQ v2 và các Fact tầng ≥ BẠC; lựa chọn giữa các phương án theo ràng buộc FR-01/UR-03.</div>
<div><b>Nguồn</b> <a class="src" data-tier="vang">DS40002061B p.258</a> · <a class="src" data-tier="nguoi">h-0917 (lời anh)</a> · <a class="src" data-tier="dong">ước lượng chi phí (ĐỒNG)</a></div>
<div><b>Khác bản trước</b> v2: thêm UR-03 nguồn pin (từ sửa của anh); loại phương án B vì FR-01.</div>
<div><b>Việc tiếp theo</b> Anh chọn phương án A hoặc yêu cầu thêm phương án; sau đó tôi đi C2.</div>
<div><b>Tin được đến đâu</b> VÀNG/BẠC cho thông số; ĐỒNG cho chi phí ước lượng (đánh dấu nghiêng).</div></div>"""

def render_block(block, area):
    items = "".join(render_widget(w, block) for w in block['items'])
    rich = RICH.get(block['id'], "")
    art = f'<span class="art">{esc(block["art"])}</span>' if block.get('art') else ''
    return f"""<section class="blk" id="blk-{block['id']}" data-id="{block['id']}">
<header><span class="bid">{block['id']}</span><h3>{esc(block['name'])}</h3>{art}
<span class="author agent">agent:run-41</span><span class="cs">cs-0106</span><span class="stale-badge" hidden>STALE</span>
<button class="btn sm why" data-why="{block['id']}">Vì sao?</button><button class="btn sm" data-more="{block['id']}">Giải thích thêm</button>
<button class="btn sm fold" data-fold="{block['id']}">Gập</button><span class="badges">{badges(block['reqs'])}</span></header>
<div class="summary">Tóm tắt: {esc(block['name'])} — sẵn sàng; 0 việc chờ anh. <span class="next">Tiếp theo: xem phần Vì sao hoặc sửa trực tiếp.</span></div>
{explain_html(block)}
<div class="body">{rich}<div class="widgets">{items}</div></div></section>"""

def render_area(area):
    return "".join(render_block(b, area) for b in area['blocks'])

areas = {a['id']: a for a in UI}
tabs_html = "".join(f'<button class="tab" data-tab="{t}">{TAB_LABEL[t]}</button>' for t in TAB_AREAS)
panes_html = "".join(f'<div class="pane" id="pane-{t}" data-area="{t}"><h2>{esc(areas[t]["name"])} <span class="aid">{t}</span></h2>{render_area(areas[t])}</div>' for t in TAB_AREAS)
statusbar = "".join(f'<span class="st" data-id="{w["id"]}" title="{esc(w["name"])}">{esc(w["name"].split("(")[0].split("+")[0].strip()[:28])}<b id="st-{w["id"].replace(".", "-")}"></b>{badges(w["reqs"])}</span>' for w in areas["A0"]["blocks"][0]["items"])
console_html = render_area(areas["A1"])
settings_html = render_area(areas["A13"])
gate_variants = {w['reqs'][0]: w['name'].split(": ", 1)[1] for w in areas["A12"]["blocks"][0]["items"] if w['name'].startswith("Biến thể")}
gate_common = "".join(render_widget(w, areas["A12"]["blocks"][0]) for w in areas["A12"]["blocks"][0]["items"][:4])

model_json = json.dumps({"reqs": REQS, "ui": UI, "gates": gate_variants, "downstream": DOWNSTREAM}, ensure_ascii=False)

CSS = r"""
:root{--red:#B8121F;--navy:#1F2A44;--teal:#1B7F79;--gold:#B58900;--bg:#F6F7F9;--card:#fff;--line:#E1E4EA;--txt:#1d1d1f;--vang:#FFF3C4;--bac:#EDEDED;--nguoi:#DDF2F0;--dong:#F3ECFA}
*{box-sizing:border-box}body{margin:0;font:13px/1.45 -apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:var(--txt);background:var(--bg);height:100vh;display:flex;flex-direction:column;overflow:hidden}
#status{display:flex;gap:10px;align-items:center;padding:4px 10px;background:var(--navy);color:#fff;font-size:11.5px;overflow-x:auto;white-space:nowrap}
#status .st{padding:2px 6px;border-right:1px solid #3a4666}#status .st b{margin-left:4px;color:#FFD866}#status .req{display:none}
#main{flex:1;display:grid;grid-template-columns:var(--cw,380px) 1fr;min-height:0}
#console{display:flex;flex-direction:column;border-right:1px solid var(--line);background:#fff;min-height:0}
#console .blk{margin:6px;box-shadow:none;border:1px solid var(--line)}#console .blk header h3{font-size:12px}
#transcript{flex:1;overflow:auto;padding:8px;font-size:12.5px}
.msg{margin:4px 0;padding:6px 8px;border-radius:8px}.msg.agent{background:#EEF6F6;border-left:3px solid var(--teal)}.msg.human{background:#FDF3F4;border-left:3px solid var(--red)}.msg.sys{background:#F3F3F3;border-left:3px solid #999;font-size:11.5px}
.msg .who{font-weight:700;margin-right:4px}
#input{display:flex;gap:6px;padding:8px;border-top:1px solid var(--line)}#input input{flex:1;padding:8px;border:1px solid var(--line);border-radius:6px}
#center{display:flex;flex-direction:column;min-height:0}
#tabs{display:flex;gap:2px;padding:6px 8px 0;background:#fff;border-bottom:1px solid var(--line);overflow-x:auto}
.tab{border:1px solid var(--line);border-bottom:none;background:#F0F1F4;padding:6px 10px;border-radius:6px 6px 0 0;cursor:pointer;font-size:12px}.tab.on{background:#fff;color:var(--red);font-weight:700}
.tab .dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--gold);margin-left:4px;vertical-align:middle}
#panes{flex:1;overflow:auto;padding:10px}.pane{display:none}.pane.on{display:block}.pane h2{margin:4px 0 10px;font-size:16px;color:var(--red)}.aid{font-size:11px;color:#888;font-weight:400}
.blk{background:var(--card);border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin:0 0 12px;padding:8px 12px}
.blk header{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.blk header h3{margin:0;font-size:14px}
.bid,.wid{font-family:Consolas,Menlo,monospace;font-size:10.5px;color:#999;display:none}.trace .bid,.trace .wid{display:inline}
.art{font-size:11px;background:#EEF;padding:1px 6px;border-radius:10px}.author{font-size:10.5px;padding:1px 6px;border-radius:10px}.author.agent{background:#EEF6F6;color:var(--teal)}.author.human{background:#FDF3F4;color:var(--red)}
.cs{font-family:monospace;font-size:10.5px;color:#777}.stale-badge{background:var(--gold);color:#fff;font-size:10.5px;padding:1px 6px;border-radius:10px;font-weight:700}
.summary{margin:6px 0;color:#333}.summary .next{color:var(--teal);font-weight:600}
.explain{display:none;background:#FFFDF3;border:1px dashed var(--gold);border-radius:8px;padding:6px 10px;margin:6px 0;font-size:12.5px}.explain.on{display:block}.explain div{margin:2px 0}
.blk.folded .body,.blk.folded .explain{display:none}
.w{display:flex;gap:8px;align-items:center;padding:4px 6px;border-top:1px dotted #eee;font-size:12.5px;flex-wrap:wrap}.w .wn{flex:1}.w-edit .wn::before{content:"✎ ";color:var(--red)}.w-action .wn::before{content:"▶ ";color:var(--teal)}.w-nav .wn::before{content:"↗ "}
.badges{display:none;gap:3px;flex-wrap:wrap}.trace .badges{display:inline-flex}.req{font-family:monospace;font-size:9.5px;background:#EEF;border:1px solid #CCD;border-radius:4px;padding:0 4px;color:#335}
.btn{border:1px solid var(--line);background:#fff;padding:4px 9px;border-radius:6px;cursor:pointer;font-size:12px}.btn:hover{border-color:var(--navy)}.btn.act{border-color:var(--teal);color:var(--teal)}.btn.save{border-color:var(--red);color:var(--red)}.btn.sm{padding:2px 7px;font-size:11px}
.t{border-collapse:collapse;width:100%;font-size:12.5px;margin:4px 0}.t th,.t td{border:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}.t th{background:#F3F4F7}.t .q{color:#555;font-style:italic}.t tr.conf td{background:#FFF0F0}
.tier{font-size:10.5px;padding:1px 6px;border-radius:10px;font-weight:700}.tier.vang{background:var(--vang);color:#7a5b00}.tier.bac{background:var(--bac);color:#555}.tier.nguoi{background:var(--nguoi);color:#0d5c58}.tier.dong{background:var(--dong);color:#6a3fa0;font-style:italic}
a.src{cursor:pointer;text-decoration:underline dotted;padding:0 3px;border-radius:3px}a.src[data-tier=vang]{background:var(--vang)}a.src[data-tier=bac]{background:var(--bac)}a.src[data-tier=nguoi]{background:var(--nguoi)}a.src[data-tier=dong]{background:var(--dong);font-style:italic}
i.dong{background:var(--dong);padding:0 3px}.sev-blk{color:#fff;background:var(--red);padding:0 5px;border-radius:4px;font-size:11px}.sev-maj{color:var(--red)}.ok{color:#0a7a2a;font-weight:700}
pre.diff{background:#0f172a;color:#e2e8f0;padding:8px;border-radius:8px;font-size:11.5px;overflow:auto}pre.diff .f{color:#93c5fd}pre.inv{background:#F3F4F7;padding:8px;border-radius:8px;font-size:11.5px}
.kv div{margin:3px 0}.bar{display:inline-block;width:160px;height:8px;background:#eee;border-radius:4px;vertical-align:middle;margin:0 6px}.bar div{height:8px;background:var(--teal);border-radius:4px}.warn{background:#FFF3C4;padding:6px;border-radius:6px}
.tl .ev{display:flex;gap:8px;align-items:center;padding:4px 6px;border-left:3px solid #ccc;margin:3px 0;font-size:12px}.tl .ev.human{border-color:var(--red);background:#FDF3F4}.tl .ev.agent{border-color:var(--teal);background:#EEF6F6}.tl .ev.snap{border-color:var(--gold);background:#FFF8E1;font-weight:700}.tl .ev .id{font-family:monospace;color:#777}
.card{border:1px solid var(--gold);background:#FFFDF3;border-radius:8px;padding:8px;margin:6px 0;font-size:12.5px}.card h4{margin:0 0 4px;font-size:12.5px}.card .it{margin:3px 0}.card.gate{border-color:var(--red);background:#FFF5F5}.card.done{opacity:.55}
#run{border-top:1px solid var(--line);padding:8px;font-size:12px;background:#FAFAFA}#run .step{padding:2px 0}#run .step.done::before{content:"✓ ";color:#0a7a2a}#run .step.run::before{content:"⟳ ";color:var(--teal)}#run .step.wait::before{content:"⏸ ";color:var(--gold)}#run .step.todo::before{content:"· "}
#modal{position:fixed;inset:0;background:rgba(0,0,0,.35);display:none;align-items:center;justify-content:center;z-index:9}#modal.on{display:flex}#modal .box{background:#fff;border-radius:12px;padding:16px;width:min(760px,92vw);max-height:88vh;overflow:auto}
#toolbar{display:flex;gap:6px;align-items:center;padding:4px 10px;background:#fff;border-bottom:1px solid var(--line);font-size:12px}#toolbar label{margin-left:auto}
.notice{position:fixed;right:14px;bottom:14px;background:var(--navy);color:#fff;padding:8px 12px;border-radius:8px;font-size:12px;opacity:0;transition:.3s}.notice.on{opacity:1}
.stale-band{display:none;background:#FFF3C4;border:1px solid var(--gold);padding:4px 8px;border-radius:6px;margin:4px 0;font-size:12px}.blk.stale .stale-band{display:block}
"""

JS = r"""
const M = MODEL; const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
let seq=18, csn=110, transcript=$('#transcript'), csList=[], snaps=[{id:'snap-3',name:'v0.3-doc-nhiet-on',at:'cs-0107',note:'sim 5/5, chạy trên bo thật',kind:'checkpoint'}];
const post=(who,text,cls)=>{const d=document.createElement('div');d.className='msg '+cls;d.innerHTML=`<span class="who">[${who}]</span>${text}`;transcript.appendChild(d);transcript.scrollTop=1e9;return d;};
const notice=t=>{const n=$('#notice');n.textContent=t;n.classList.add('on');setTimeout(()=>n.classList.remove('on'),2200)};
function humanAct(kind,target,text,data){seq++;const id='h-'+String(900+seq).padStart(4,'0');post('Bạn',`${text} <span class="cs">${id} · ${kind}${target?' · '+target:''}</span>`,'human');logEv('human',`HumanAct ${kind} ${target||''} — ${text}`);return id;}
function changeset(author,what,touches,reversible=true,reason=''){csn++;const id='cs-'+String(csn).padStart(4,'0');csList.push({id,author,what,touches,reversible,reason});renderTimeline();$('#st-A0-1-5').textContent=`snap-3 (+${csList.length+4})`;return id;}
function logEv(cls,text){const tl=$('#timeline');if(!tl)return;}
function renderTimeline(){const tl=$('#timeline');if(!tl)return;const base=[['cs-0101','agent','REQ v1'],['cs-0102','agent','modules'],['cs-0103','human','REQ v2 (+pin) — vì: ngoài trời'],['cs-0104','agent','code ×3'],['cs-0105','agent','build OK'],['cs-0106','agent','sim 4/5'],['cs-0107','snap','★ snapshot v0.3-doc-nhiet-on'],['cs-0108','agent','flash+verify (⚠ không hoàn tác được)'],['cs-0109','agent','code ×2 (-O3)']];
 tl.innerHTML=base.map(([i,c,w])=>`<div class="ev ${c}"><span class="id">${i}</span><span>${w}</span>${c!=='snap'?`<button class="btn sm" data-undo="${i}">Hoàn tác</button><button class="btn sm" data-snapat="${i}">★ Snapshot tại đây</button>`:''}</div>`).join('')+csList.map(c=>`<div class="ev ${c.author}"><span class="id">${c.id}</span><span>${c.what}${c.reversible?'':' (⚠ '+c.reason+')'}</span><button class="btn sm" data-undo="${c.id}">Hoàn tác</button><button class="btn sm" data-snapat="${c.id}">★ Snapshot tại đây</button></div>`).join('');
 const sn=$('#snaps');if(sn)sn.innerHTML=snaps.map(s=>`<div class="ev snap tl"><span class="id">${s.id}</span>★ ${s.name} <small>(${s.kind}, tại ${s.at}) — ${s.note}</small> <button class="btn sm" data-restore="${s.id}">Khôi phục</button><button class="btn sm" data-release="${s.id}">Đánh dấu release</button><button class="btn sm" data-cmp="${s.id}">So sánh</button></div>`).join('');}
function markStale(blockId,why){(M.downstream[blockId]||[]).forEach(b=>{const el=document.getElementById('blk-'+b);if(!el)return;el.classList.add('stale');el.querySelector('.stale-badge').hidden=false;let band=el.querySelector('.stale-band');if(!band){band=document.createElement('div');band.className='stale-band';el.insertBefore(band,el.querySelector('.summary'));}band.innerHTML=`⚠ Cần cập nhật vì ${why} <button class="btn sm" data-acceptstale="${b}">Chấp nhận STALE</button> <button class="btn sm" data-plan="${b}">Lập kế hoạch cập nhật</button>`;const tab=$(`.tab[data-tab="${b.split('.')[0]}"]`);if(tab&&!tab.querySelector('.dot'))tab.insertAdjacentHTML('beforeend','<span class="dot"></span>');});
 const n=$$('.blk.stale').length;$('#st-A0-1-6').textContent=n;}
function gate(code,ctx){const v=M.gates[code]||'';const box=$('#modal .box');box.innerHTML=`<div class="card gate"><h4>Thẻ cổng ${code} · rủi ro ${['G-OPS','G-SAFE'].includes(code)?'R4':['G-QUAL','G-TOOL','G-FILE','G-FLASH','G-HIST'].includes(code)?'R2':'R1'}</h4><div class="it"><b>Nội dung:</b> ${v}</div><div class="it"><b>Ngữ cảnh:</b> ${ctx}</div><div class="it"><b>Hậu quả (từ hợp đồng tool, không do mô hình viết):</b> ${code==='G-OPS'?'Chip KHÔNG BAO GIỜ đọc/gỡ lỗi lại được. Không hoàn tác. Cần snapshot release.':code==='G-FLASH'?'Không hoàn tác được trên chip; đề nghị snapshot trước.':code==='G-HIST'?'Sẽ mất: 2 changeset của tác tử, 1 của anh (drv_i2c.c v12). Gợi ý: snapshot bản hiện tại trước.':'Có thể hoàn tác bằng changeset.'}</div>
 <div class="it">${code==='G-QUAL'?'<input placeholder="từ" size=6> → <input placeholder="đến" size=6> vì: <input placeholder="lý do (bắt buộc)" size=24>':''}${code==='G-SNAP'?'<input id="snapname" placeholder="tên bản ưng ý" size=24> <input placeholder="ghi chú" size=30>':''}</div>
 <button class="btn act" data-decide="approve" data-code="${code}">Duyệt</button> <button class="btn" data-decide="reject" data-code="${code}">Từ chối</button> ${['G-OPS','G-SAFE','G-HIST','G-SNAP'].includes(code)?'':'<button class="btn sm" data-decide="trust" data-code="'+code+'">Tin (R0–R2)</button>'}
 <div style="margin-top:6px;font-size:11px;color:#777">Gõ "có" trong Console KHÔNG mở cổng này (I6). Hết hạn sau ${code==='G-OPS'?'10':'60'} phút.</div></div>`;$('#modal').classList.add('on');}
function agentReply(text,card){setTimeout(()=>{post('Tác tử',text,'agent');if(card)transcript.appendChild(card);transcript.scrollTop=1e9;},650);}
function clarifyCard(title,items){const c=document.createElement('div');c.className='card';c.innerHTML=`<h4>${title}</h4>`+items.map((it,i)=>`<div class="it">${it.q} ${it.opts.map((o,j)=>`<label><input type="${it.multi?'checkbox':'radio'}" name="q${i}" ${j===0?'checked':''}> ${o}</label> `).join('')}</div>`).join('')+`<button class="btn act" data-choose="1">Gửi</button> <button class="btn sm" data-choose="0">Bỏ qua (dùng giả định)</button>`;return c;}
document.addEventListener('click',e=>{const t=e.target.closest('button,a.src,.tab');if(!t)return;
 if(t.classList.contains('tab')){$$('.tab').forEach(x=>x.classList.remove('on'));t.classList.add('on');$$('.pane').forEach(p=>p.classList.toggle('on',p.dataset.area===t.dataset.tab));return;}
 if(t.dataset.nav){$(`.tab[data-tab="${t.dataset.nav}"]`).click();return;}
 if(t.dataset.why!==undefined){const ex=document.getElementById('blk-'+t.dataset.why).querySelector('.explain');ex.classList.toggle('on');return;}
 if(t.dataset.fold){document.getElementById('blk-'+t.dataset.fold).classList.toggle('folded');t.textContent=t.textContent==='Gập'?'Mở':'Gập';return;}
 if(t.dataset.more){const b=t.dataset.more;humanAct('say','artefact:'+b,`Giải thích thêm về "${document.getElementById('blk-'+b).querySelector('h3').textContent}"`);agentReply(`(ui.explain) Khối này được tạo ở run-41 từ REQ v2. Điểm anh nên để ý: các số nghiêng là ước lượng (ĐỒNG), chưa dùng để quyết định. Tôi đã tô sáng chỗ liên quan trên tab. <a class="src" data-tier="vang">DS p.12</a>`);return;}
 if(t.classList.contains('src')){const tier=t.dataset.tier;notice(tier==='vang'?'Mở PDF đúng trang/bbox (VÀNG)':tier==='bac'?'Mở trang nguồn — chưa xác nhận dòng (BẠC)':tier==='nguoi'?'Từ lời anh (HumanAct) — chưa có tài liệu':'Suy đoán của mô hình — không dùng để quyết định');return;}
 if(t.dataset.save){const b=t.dataset.block;const name=document.getElementById('blk-'+b)?.querySelector('h3').textContent||b;const why=prompt('Vì sao anh sửa? (tuỳ chọn — giúp tác tử hiểu)','')||'(không ghi)';const id=humanAct('edit',b+'@v'+(2+csList.length),`Sửa <b>${name}</b> — vì: ${why}`);const cs=changeset('human',`sửa ${name} — vì: ${why}`,[b]);markStale(b,`${cs} (anh sửa ${name})`);
   const el=document.getElementById('blk-'+b);if(el){el.querySelector('.author').className='author human';el.querySelector('.author').textContent='human';el.querySelector('.cs').textContent=cs;}
   const down=(M.downstream[b]||[]);agentReply(`Anh vừa sửa <b>${name}</b> (${cs}) — vì: <i>${why}</i>. Tôi ghi vào EIDE.md §"Người vừa sửa"${/\d/.test(why+name)?' và tạo Fact tầng NGƯỜI cho số mới':''}. Hệ quả: ${down.length?down.length+' hiện vật hạ nguồn cần cập nhật ('+down.join(', ')+')':'không có hạ nguồn'}. Tôi <b>không</b> tự sửa lại phần của anh.`,down.length?clarifyCard('Anh muốn tôi làm gì tiếp?',[{q:'',opts:['Lập kế hoạch cập nhật '+down.length+' hiện vật STALE','Chỉ cập nhật mã, giữ thiết kế','Để đó, tôi tự làm']}]):null);return;}
 if(t.dataset.act){const w=t.dataset.act,g=t.dataset.gate;const name=t.textContent.trim();if(g){humanAct('say','',name);agentReply(`Việc này đi qua cổng <b>${g}</b> — tôi đã phát thẻ cổng riêng (không gộp với câu hỏi khác).`);setTimeout(()=>gate(g,name+' ('+w+')'),900);return;}
   if(w==='A1.4.3'){humanAct('stop','run:run-43','DỪNG run-43');agentReply('Đã dừng sau nút 4/9 (đang nạp thì chờ verify xong mới dừng). Trạng thái đã lưu. Bấm Tiếp tục khi sẵn sàng.');$$('#run .step.run').forEach(s=>s.className='step wait');return;}
   if(w==='A1.4.4'){humanAct('undo','run:run-43','Hoàn tác run-43 (trong 30 s)');const cs=changeset('human','hoàn tác run-43 (2 changeset)',['A7.1','A7.3']);agentReply(`Đã hoàn tác run-43 → ${cs}. Lịch sử không bị xoá. Bo vẫn chạy bản fw-0x9a1c ≠ mã hiện tại — anh muốn nạp lại không?`);return;}
   if(w==='A1.4.5'||w==='A11.2.2'||w==='A1.2.3'){const n=prompt('Tên bản ưng ý:','v0.4-truoc-khi-doi-PHY');if(!n)return;humanAct('snapshot','',`Ghi bản ưng ý "${n}"`);const cs=changeset('human',`★ snapshot ${n}`,[]);snaps.push({id:'snap-'+(snaps.length+3),name:n,at:cs,note:'do anh ghi',kind:'checkpoint'});renderTimeline();$('#st-A0-1-5').textContent=`${n} (+0)`;agentReply(`Đã ghi bản ưng ý <b>${n}</b> (bất biến): mã v9, netlist v3, 142 Fact (98 VÀNG), DS 7810D, sim 4/5. Khôi phục bất cứ lúc nào ở tab Lịch sử.`);return;}
   if(w==='A1.4.8'){humanAct('resume','run:run-43','Tiếp tục run-43');agentReply('Tiếp tục từ nút 5/9.');$$('#run .step.wait').forEach(s=>s.className='step run');return;}
   if(w==='A4.2.2'){humanAct('confirm','fact:12','Xác nhận Fact i2c.sda.pullup_typ = 4,7 kΩ');t.closest('tr').querySelector('.tier').className='tier vang';t.closest('tr').querySelector('.tier').textContent='VÀNG';t.remove();agentReply('Đã ghi VÀNG: i2c.sda.pullup_typ 4,7 kΩ (DS p.215). 40 Fact BẠC còn lại.');return;}
   if(w==='A4.2.4'){humanAct('say','','Tìm tài liệu chứng thực cho Fact');agentReply('Tôi tìm trên microchip.com/ti.com → sẽ đưa ứng viên vào tab Tài liệu để anh duyệt (G-DATA).');return;}
   if(w==='A2.1.7'||t.dataset.acceptstale){return;}
   humanAct('say','',name);agentReply(`Đã nhận "${name}". Tôi làm và cập nhật tab tương ứng (surface.patch).`);return;}
 if(t.dataset.acceptstale){const b=t.dataset.acceptstale;humanAct('confirm','artefact:'+b,'Chấp nhận STALE '+b+' (lý do: sẽ cập nhật sau)');const el=document.getElementById('blk-'+b);el.classList.remove('stale');el.querySelector('.stale-badge').hidden=true;$('#st-A0-1-6').textContent=$$('.blk.stale').length;return;}
 if(t.dataset.plan){humanAct('say','',`Lập kế hoạch cập nhật ${t.dataset.plan}`);agentReply('Vào plan mode (khoá tool ghi). Kế hoạch 4 bước, ~18 k token — thẻ G-SCOPE:');setTimeout(()=>gate('G-SCOPE','Kế hoạch cập nhật hạ nguồn: (1) arch.decompose, (2) code.fix drv_eth, (3) build, (4) sim'),1200);return;}
 if(t.dataset.undo){humanAct('undo','changeset:'+t.dataset.undo,'Hoàn tác '+t.dataset.undo);if(t.dataset.undo==='cs-0108'){agentReply('cs-0108 là nạp firmware — KHÔNG hoàn tác được trên chip. Tôi chỉ đánh dấu và đề nghị nạp lại bản khác.');return;}const cs=changeset('human','hoàn tác '+t.dataset.undo,[]);agentReply(`Đã tạo ${cs} áp inverse ops của ${t.dataset.undo}. Nếu có changeset sau nó chạm cùng hiện vật, tôi đã cảnh báo ở thẻ.`);return;}
 if(t.dataset.snapat){const n=prompt('Tên snapshot tại '+t.dataset.snapat+':','');if(!n)return;humanAct('snapshot','changeset:'+t.dataset.snapat,`Ghi bản ưng ý "${n}" tại ${t.dataset.snapat}`);snaps.push({id:'snap-'+(snaps.length+3),name:n,at:t.dataset.snapat,note:'do anh ghi',kind:'checkpoint'});renderTimeline();return;}
 if(t.dataset.restore){humanAct('undo','snapshot:'+t.dataset.restore,'Khôi phục '+t.dataset.restore);gate('G-HIST','Khôi phục '+t.dataset.restore);return;}
 if(t.dataset.release){humanAct('set','snapshot:'+t.dataset.release,'Đánh dấu release '+t.dataset.release);snaps.find(s=>s.id===t.dataset.release).kind='release';renderTimeline();agentReply('Đã đánh dấu release. Từ giờ target.dangerous (RDP/eFuse) mới được phép qua G-OPS.');return;}
 if(t.dataset.cmp){humanAct('say','','So sánh '+t.dataset.cmp+' với hiện tại');agentReply('So sánh snap-3 ↔ hiện tại: REQ +1 (UR-03) · Fact đổi 2 · mã 4 tệp (+61 −12) · Flash 3,1→3,4 KB · sim 4/5 → 4/5 · tài liệu giống.');return;}
 if(t.dataset.decide){const code=t.dataset.code,d=t.dataset.decide;humanAct('decide','gate:'+code,`${d==='approve'?'DUYỆT':d==='reject'?'TỪ CHỐI':'TIN'} cổng ${code}`);$('#modal').classList.remove('on');
   if(d==='approve'){if(code==='G-SNAP'){const n=($('#snapname')||{}).value||'v0.4';snaps.push({id:'snap-'+(snaps.length+3),name:n,at:'cs-now',note:'tác tử đề xuất, anh đặt tên',kind:'checkpoint'});renderTimeline();agentReply(`Đã ghi snapshot <b>${n}</b>.`);}else if(code==='G-DESIGN'){const cs=changeset('agent:run-44','ADR-05 chọn phương án',['A2.4']);agentReply(`Đã chốt (${cs}, ADR-05 có human_act_ref). STALE: C2 trở đi sẽ dựng theo phương án này.`);}else if(code==='G-FLASH'){const cs=changeset('agent:run-44','flash+verify v9',[],false,'đã nạp vào chip');agentReply(`Đã nạp v9 (sha 4f2a…, 3 148 B) vào STM32F103 @0x08000000, verify OK — ${cs} (không hoàn tác được).`);}else if(code==='G-OPS'){agentReply('Đã thực hiện. Không hoàn tác được. Ghi sổ cái gate.decision.');}else if(code==='G-HIST'){const cs=changeset('human','khôi phục snapshot → nhánh mới',[]);agentReply(`Đã khôi phục vào nhánh <b>khoi-phuc-snap-3</b> (${cs}); bản hiện tại được giữ trên main.`);}else agentReply(`Cổng ${code} đã duyệt — tiếp tục.`);}else if(d==='reject')agentReply(`Cổng ${code} bị từ chối — tôi bỏ bước này và ghi "bỏ vì người từ chối".`);else agentReply(`Đã ghi "tin" cho ${code} (R0–R2) vào bộ nhớ người dùng.`);return;}
 if(t.dataset.choose!==undefined){const c=t.closest('.card');c.classList.add('done');humanAct('choose','card',t.dataset.choose==='1'?'Trả lời thẻ: '+[...c.querySelectorAll('input:checked')].map(i=>i.parentNode.textContent.trim()).join('; '):'Bỏ qua thẻ (dùng giả định)');agentReply('Đã nhận. Tôi tiếp tục và nêu giả định trong báo cáo lượt.');return;}
});
$('#send').onclick=()=>{const v=$('#say').value.trim();if(!v)return;$('#say').value='';
 if(/^\/dung/.test(v)){$('[data-act="A1.4.3"]').click();return;}if(/^\/tiep/.test(v)){$('[data-act="A1.4.8"]').click();return;}if(/^\/hoan/.test(v)){$('[data-act="A1.4.4"]').click();return;}if(/^\/snap/.test(v)){$('[data-act="A1.4.5"]').click();return;}
 if(/^\/nhanh/.test(v)){humanAct('branch','',v);agentReply('Đã tạo nhánh phuong-an-B từ snap-3. Tab hiện tên nhánh.');$('#st-A0-1-1').textContent='lan-usb-tv · phuong-an-B';return;}
 humanAct('say','',v);
 if(/rdp|efuse|xo[aá] .*flash|option bytes/i.test(v)){agentReply('S0 bắt thao tác không đảo ngược. Phần "nạp" tôi làm; phần RDP cần anh bấm Duyệt trên thẻ cổng riêng:');setTimeout(()=>gate('G-OPS','Bật RDP mức 2 trên STM32F103C8T6'),900);return;}
 if(/nóng|khói|cháy|220 ?v|điện lưới/i.test(v)){agentReply('<b>NGẮT NGUỒN NGAY</b> — rút cáp cấp điện và cáp nạp trước khi làm bất cứ việc gì khác (G-SAFE, P-SAFE-01). Sau khi ngắt: (1) sờ IC nào nóng, (2) đo trở kháng VCC–GND, (3) kiểm cực tính nguồn.');return;}
 if(/^(có|ok|đồng ý|làm đi)\b/i.test(v)&&$('#modal').classList.contains('on')){agentReply('Với thao tác qua cổng, tôi cần anh bấm <b>Duyệt</b> trên thẻ (I6) — chữ "có" trong hội thoại không mở cổng.');return;}
 if(/phá sóng|jammer/i.test(v)){agentReply('Tôi không hỗ trợ phần này: thiết bị gây nhiễu/phá sóng bị cấm (P-LAW-01, REJECT). Hướng hợp pháp: che chắn thụ động bằng lồng Faraday.');return;}
 if(/datasheet|chip|stm32|atmega|esp32/i.test(v)&&/thêm|dùng|đổi/i.test(v)){agentReply('Tôi thấy anh nhắc một chip mới. Chưa có datasheet trong dự án — anh muốn:',clarifyCard('Datasheet cho chip mới',[{q:'',opts:['Tìm trên mạng (ưu tiên nhà sản xuất)','Tôi nạp tệp','Dùng tri thức chung — nhãn ĐỒNG']}]));return;}
 if(/mơ hồ|thông minh$/i.test(v)){agentReply('Tôi chưa đủ thông tin để thiết kế — hỏi một cụm (tối đa 2 lần):',clarifyCard('Làm rõ ý tưởng',[{q:'Mục tiêu chính?',opts:['Điều khiển','Đo lường','Truyền dữ liệu']},{q:'Nguồn cấp?',opts:['Pin','Adapter 5 V','Điện lưới (sẽ cảnh báo an toàn)']},{q:'Ngân sách?',opts:['< 500 k','< 2 triệu','Không giới hạn']}]));return;}
 agentReply(`Đã hiểu: "${v}". Tôi kiểm <inventory> (dự án đang mở, chặng C4), gọi tool cần thiết và cập nhật tab. Giả định đang dùng: -Os. Nếu việc lớn tôi sẽ vào plan mode và trình kế hoạch (G-SCOPE).`);};
$('#say').addEventListener('keydown',e=>{if(e.key==='Enter')$('#send').click();});
$('#trace').onchange=e=>document.body.classList.toggle('trace',e.target.checked);
$$('.cw').forEach(b=>b.onclick=()=>{document.documentElement.style.setProperty('--cw',b.dataset.w);humanAct('set','ui.console_size','Đổi cỡ Console '+b.textContent);});
$('#gear').onclick=()=>{$('#modal .box').innerHTML='<h3 style="margin-top:0;color:var(--red)">Thiết lập (A13)</h3>'+SETTINGS+'<p><button class="btn" onclick="document.getElementById(\'modal\').classList.remove(\'on\')">Đóng</button></p>';$('#modal').classList.add('on');};
$('#modal').addEventListener('click',e=>{if(e.target.id==='modal')$('#modal').classList.remove('on');});
$$('.tab')[0].click();renderTimeline();
// mock status & run
$('#st-A0-1-1').textContent='lan-usb-tv · main';$('#st-A0-1-2').textContent='mchp.atmega328p@1.0.0 · avr8';$('#st-A0-1-3').textContent='98 / 41 / 2 / 1';$('#st-A0-1-4').textContent='C4 Firmware';$('#st-A0-1-5').textContent='snap-3 (+4)';$('#st-A0-1-6').textContent='2';$('#st-A0-1-7').textContent='A3 · Sonnet/Gemini Pro';$('#st-A0-1-8').textContent='12/40 · 84 s · 41 %';$('#st-A0-1-9').textContent='lõi ✓ · mạng ✓';
post('Hệ thống','Mở lại dự án <b>lan-usb-tv</b>. Snapshot gần nhất snap-3 (+4 changeset, 2 STALE).','sys');
post('Tác tử','Đang ở chặng C4 (firmware). Đã quyết: ADR-03 MTP thay Mass Storage; UR-03 nguồn pin (anh sửa 24/09). Giả định: -Os, TV đọc exFAT. Việc tiếp theo: sửa drv_eth cho FR-01 ≥ 5 MB/s — tôi đề nghị kế hoạch 4 bước. <span class="cs">c-4301</span>','agent');
const rc=clarifyCard('Trước khi tôi sửa drv_eth',[{q:'Giữ ENC28J60 (≈1 MB/s, không đạt FR-01) hay đổi PHY?',opts:['Đổi sang W5500 (cần tìm datasheet → G-DATA)','Giữ ENC28J60, hạ FR-01 (→ G-QUAL)','Chuyển sang phương án A (SBC)']}]);transcript.appendChild(rc);
"""

HTML = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>EIDE v3.0 — UI tác tử Kỹ sư Nhúng (prototype)</title><style>{CSS}</style></head><body>
<div id="status">{statusbar}<button class="btn sm" id="gear" style="margin-left:auto;color:#fff;background:transparent;border-color:#5a6a99">⚙ Thiết lập (A13)</button></div>
<div id="toolbar"><b style="color:var(--red)">EIDE v3.0</b> · prototype UI sinh từ mô hình 3 cấp (15 vùng · 63 khối · 191 widget) · <span>Console:</span><button class="btn sm cw" data-w="300px">hẹp</button><button class="btn sm cw" data-w="380px">vừa</button><button class="btn sm cw" data-w="520px">rộng</button>
<label><input type="checkbox" id="trace"> Chế độ truy vết (hiện mã UI + yêu cầu) — A13.5.2</label></div>
<div id="main"><div id="console"><div style="padding:6px 8px;font-weight:700;color:var(--red);border-bottom:1px solid var(--line)">Bàn giao tiếp (A1) — điểm giao tiếp người–máy duy nhất <span class="aid">console.act</span></div>
<div id="transcript"></div>
<div id="input"><input id="say" placeholder="Gõ tự do… (/dung /tiep-tuc /hoan-tac /snapshot /nhanh; thử: 'nạp rồi bật RDP mức 2', 'chip nóng', 'làm cái mạch thông minh')"><button class="btn" title="A1.2.2 upload">📎</button><button class="btn act" id="send">Gửi</button></div>
<div id="run"><b>Thẻ Run — run-43</b> · <span class="cs">A1.4</span><div class="step done">1 fs.read drv_eth.c</div><div class="step done">2 fact.query eth.*</div><div class="step done">3 Task(design-review)</div><div class="step done">4 code.fix drv_eth.c</div><div class="step run">5 build.compile</div><div class="step todo">6 sim.criteria → sim.run</div><div class="step todo">7 Task(verifier)</div>
<div style="margin-top:4px"><small>Subagent: design-review (đọc) ✓ · verifier (chờ) · Giả định: -Os · Chi phí: 12 tool / 84 s / 23 k token</small></div>
<div style="margin-top:6px"><button class="btn sm" data-act="A1.4.3" style="border-color:var(--red);color:var(--red)">■ Dừng khẩn</button> <button class="btn sm" data-act="A1.4.4">↶ Hoàn tác lượt (30 s)</button> <button class="btn sm" data-act="A1.4.5">★ Ghi bản ưng ý</button> <button class="btn sm" data-act="A1.4.8">▶ Tiếp tục</button></div></div>
<details style="padding:6px 8px;border-top:1px solid var(--line);font-size:11.5px"><summary>Cấu trúc Console theo mô hình (A1.1–A1.5)</summary>{console_html}</details>
</div>
<div id="center"><div id="tabs">{tabs_html}</div><div id="panes">{panes_html}</div></div></div>
<div id="modal"><div class="box"></div></div><div class="notice" id="notice"></div>
<script>const MODEL={model_json};const SETTINGS={json.dumps(settings_html, ensure_ascii=False)};{JS}</script>
</body></html>"""
open('./EIDE_v3.0_UI_prototype.html', 'w').write(HTML)
print('html ok', len(HTML) // 1024, 'KB')
