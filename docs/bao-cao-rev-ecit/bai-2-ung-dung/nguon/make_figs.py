# -*- coding: utf-8 -*-
"""Vẽ hình cho bài báo: SVG tự dựng (toạ độ cố định, kiểm không đè) → PNG bằng Chromium."""
import asyncio, textwrap, os
from playwright.async_api import async_playwright

OUT = os.path.dirname(os.path.abspath(__file__))
FONT = "Inter, 'DejaVu Sans', sans-serif"
INK = "#1a1a1a"; LINE = "#333333"
FILL_A = "#ffffff"; FILL_B = "#eef2f7"; FILL_C = "#fdf3e1"; FILL_D = "#e8f3ea"

class Canvas:
    def __init__(self, w, h, base=30):
        self.w, self.h, self.base = w, h, base
        self.items = []
        self.boxes = []  # (x,y,w,h,name) để kiểm đè
    def rect(self, x, y, w, h, fill=FILL_A, stroke=LINE, sw=3, r=10, dash=None, name=""):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
        self.boxes.append((x, y, w, h, name))
    def text(self, x, y, s, size=None, weight=400, anchor="start", color=INK, italic=False):
        size = size or self.base
        st = ' font-style="italic"' if italic else ""
        self.items.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{color}"{st}>{s}</text>')
    def box(self, x, y, w, h, lines, fill=FILL_A, size=None, weight=400, title=None, tsize=None, align="center", name="", r=10, sw=3, stroke=LINE):
        """Hộp với tiêu đề (đậm) và các dòng; tự xếp dọc, kiểm tràn."""
        size = size or self.base; tsize = tsize or size
        self.rect(x, y, w, h, fill=fill, r=r, sw=sw, stroke=stroke, name=name or (title or lines[0] if lines else ""))
        lh = size * 1.3
        n = len(lines) + (1 if title else 0)
        total = (tsize * 1.3 if title else 0) + len(lines) * lh
        assert total <= h - 10, f"tràn chữ trong hộp '{title or lines}': cần {total:.0f}, có {h}"
        cy = y + (h - total) / 2
        ax = x + w / 2 if align == "center" else x + 18
        anchor = "middle" if align == "center" else "start"
        if title:
            cy += tsize * 1.0
            self.text(ax, cy, title, size=tsize, weight=700, anchor=anchor)
            cy += tsize * 0.3
        for ln in lines:
            cy += size * 1.0
            self.text(ax, cy, ln, size=size, weight=weight, anchor=anchor)
            cy += size * 0.3
        # kiểm bề rộng gần đúng (0,55 em / ký tự)
        for ln in ([title] if title else []) + lines:
            est = len(ln) * (tsize if ln == title else size) * 0.53
            assert est <= w - 24, f"dòng quá rộng trong hộp '{title or lines[0]}': '{ln}' ({est:.0f} > {w-24})"
    def arrow(self, x1, y1, x2, y2, label=None, size=None, lx=None, ly=None, dash=None, color=LINE, sw=3):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.items.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" marker-end="url(#ah)"{d}/>')
        if label:
            self.text(lx if lx is not None else (x1 + x2) / 2 + 12, ly if ly is not None else (y1 + y2) / 2 - 10, label, size=size or self.base - 4, italic=True, color="#444")
    def path(self, d, color=LINE, sw=3, dash=None, arrow=True):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        m = ' marker-end="url(#ah)"' if arrow else ""
        self.items.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{sw}"{da}{m}/>')
    def check_overlap(self):
        for i, a in enumerate(self.boxes):
            for b in self.boxes[i+1:]:
                ax, ay, aw, ah, an = a; bx, by, bw, bh, bn = b
                inside = (ax <= bx and ay <= by and ax+aw >= bx+bw and ay+ah >= by+bh) or (bx <= ax and by <= ay and bx+bw >= ax+aw and by+bh >= ay+ah)
                if inside: continue
                if ax < bx+bw and bx < ax+aw and ay < by+bh and by < ay+ah:
                    raise AssertionError(f"ĐÈ KHỐI: '{an}' và '{bn}'")
    def svg(self):
        head = f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}"><defs><marker id="ah" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L12,6 L0,12 z" fill="{LINE}"/></marker></defs><rect width="100%" height="100%" fill="white"/>'
        return head + "".join(self.items) + "</svg>"

# ---------------------------------------------------------------- Hình 1: kiến trúc (toàn trang)
def fig1():
    c = Canvas(2100, 1260, base=30)
    c.box(60, 40, 300, 190, ["gõ một câu,", "bấm Duyệt / Không,", "sửa tệp bằng tay"], title="Kỹ sư", size=26, tsize=30, fill=FILL_C, name="ky su")
    c.box(460, 40, 1580, 190, ["một ô nhập lệnh · thẻ cửa duyệt · 11 tab xem kho (yêu cầu, tài liệu, mạch, thiết kế, công cụ,",
                              "mã nguồn, mô phỏng, mạch thật, nhật ký, lịch sử, bộ nhớ). Giao diện không tự quyết gì:",
                              "chỉ vẽ lại 16 loại lệnh lõi gửi sang; mọi cái chạm của người đi qua một cửa duy nhất vào lõi."],
          title="Giao diện (Swift, macOS)", size=26, tsize=30, fill=FILL_B, name="giao dien")
    c.arrow(360, 135, 460, 135)
    c.arrow(1250, 230, 1250, 300); c.arrow(1290, 300, 1290, 230)
    c.text(1310, 272, "JSON-RPC 2.0 qua stdio — không mở cổng mạng", size=26, italic=True, color="#444")
    O = 50  # dời phần lõi xuống
    c.rect(60, 250+O, 1980, 700, fill="#fafafa", r=14, name="loi")
    c.text(80, 290+O, "Lõi tác tử (Python)", size=34, weight=700)
    c.box(90, 320+O, 600, 150, ["luật nền · bộ nhớ dự án EIDE.md", "kiểm kê kho · thông số liên quan", "sửa đổi của người · lịch sử lượt"], title="Dựng ngữ cảnh (10 khối, có trần)", size=24, tsize=28, name="ngu canh")
    c.box(750, 320+O, 600, 150, ["nhận ngữ cảnh → chọn MỘT công cụ", "hoặc trả lời; lặp tới khi xong", "lỗi và lời từ chối quay về như dữ liệu"], title="Mô hình ngôn ngữ (gemini-3.8-flash)", size=24, tsize=28, fill=FILL_D, name="mo hinh")
    c.arrow(690, 395+O, 750, 395+O)
    c.box(1410, 320+O, 600, 150, ["giả định đã nói ra chưa?", "sửa của người đã nhắc chưa? việc ghi mà", "chưa kiểm? → chưa đạt thì thêm một vòng"], title="Kiểm trước khi kết thúc lượt", size=24, tsize=28, name="stop")
    c.arrow(1350, 395+O, 1410, 395+O)
    c.text(90, 505+O, "Ba lớp chặn bằng mã quanh MỖI lời gọi công cụ (không tốn token):", size=28, weight=700)
    c.box(90, 525+O, 600, 120, ["công cụ này được gọi lúc này không,", "trong chế độ này không? (10 luật, 0,06 ms)"], title="Lớp 1 — Luật", size=24, tsize=28, name="lop1")
    c.box(750, 525+O, 600, 120, ["việc có hậu quả thì dừng, hiện thẻ:", "G-FLASH, G-DATA, G-TOOL, G-QUAL, G-SAFE…"], title="Lớp 2 — 11 cửa duyệt", size=24, tsize=28, fill=FILL_C, name="lop2")
    c.box(1410, 525+O, 600, 120, ["tệp phải nằm trong thư mục dự án;", "hằng số sắp ghi vào mã phải có nguồn"], title="Lớp 3 — Hộp cát và nguồn số", size=24, tsize=28, name="lop3")
    c.arrow(1050, 470+O, 1050, 525+O)
    c.arrow(690, 585+O, 750, 585+O); c.arrow(1350, 585+O, 1410, 585+O)
    c.text(90, 700+O, "127 công cụ, xếp theo việc người cần làm (số công cụ trong ngoặc):", size=28, weight=700)
    chips = ["Làm rõ đề bài (11)", "Đọc tài liệu (20)", "Viết tài liệu (1)", "Thiết kế mạch (27)", "Viết mã (8)", "Chạy thử (2)", "Bo thật (6)", "Chip trên FPGA (5)", "Nhớ & quản việc (28)", "Tự viết công cụ mới (4)"]
    x = 90; y = 720+O
    for i, ch in enumerate(chips):
        w = int(len(ch) * 26 * 0.58) + 40
        if x + w > 2010: x = 90; y += 70
        c.box(x, y, w, 56, [ch], size=26, fill=FILL_B if i < 9 else FILL_D, r=28, name=ch)
        x += w + 16
    c.arrow(1040, 645+O, 1040, 720+O)
    c.box(90, 860+O, 1920, 70, ["Mỗi lời gọi (tham số, kết quả, mã lỗi) ghi vào sổ ghi việc · mỗi thay đổi tệp là một changeset gỡ lại được · lần sửa đầu mỗi lượt tự đánh mốc lùi"], size=24, fill=FILL_A, name="ghi so")
    c.arrow(1040, 848+O, 1040, 860+O)
    c.arrow(600, 950+O, 600, 1000+O); c.arrow(1500, 950+O, 1500, 1000+O)
    c.box(60, 1000+O, 1000, 150, ["ledger.jsonl (mỗi dòng móc băm vào dòng trước) · changesets.jsonl · snapshots.jsonl", "blobs/ tệp theo mã băm · llm/ nguyên văn lời gọi mô hình · EIDE.md bộ nhớ dài hạn"], title="Kho dự án  &lt;thư mục dự án&gt;/.eide/", size=22, tsize=28, fill=FILL_B, name="kho")
    c.box(1100, 1000+O, 940, 150, ["dò bo (đọc mã chip từ silicon) · nạp qua ST-Link / avrdude / openFPGALoader", "đọc ngược từng byte · đọc cổng nối tiếp · giải mã thanh ghi lỗi · ảnh từ chip"], title="Bo mạch thật", size=22, tsize=28, fill=FILL_C, name="bo")
    c.path(f"M 60 {1075+O} L 30 {1075+O} L 30 135 L 60 135", dash="10,8")
    c.text(72, 1000+O-18, "11 tab là hình chiếu của kho (đường đứt)", size=24, italic=True, color="#444")
    c.check_overlap()
    return c.svg()

# ---------------------------------------------------------------- Hình 2: một lượt làm việc (cột)
def fig2():
    c = Canvas(1000, 1250, base=28)
    W = 560; X = 60
    steps = [
        ("1. Kỹ sư gõ một câu", ["ví dụ: “viết lại nhân thời gian thực”"], FILL_C),
        ("2. Lõi dựng ngữ cảnh từ kho", ["yêu cầu, tài liệu đã nạp, thông số, lịch sử"], FILL_A),
        ("3. Mô hình chọn một công cụ", ["hoặc quyết định trả lời"], FILL_D),
        ("4. Ba lớp chặn kiểm lời gọi", ["luật → cửa duyệt → hộp cát / nguồn số"], FILL_A),
        ("5. Chạy công cụ, ghi vào sổ", ["tham số, kết quả, mã lỗi; sửa tệp → changeset"], FILL_A),
        ("6. Kết quả quay về mô hình", ["kể cả lỗi và lời từ chối, dưới dạng dữ liệu"], FILL_A),
        ("7. Kiểm trước khi kết thúc lượt", ["giả định? sửa của người? việc chưa kiểm?"], FILL_A),
        ("8. Trả lời; 11 tab vẽ lại từ kho", ["mọi thứ hiện ra đều lần về được sổ ghi việc"], FILL_C),
    ]
    ys = []
    y = 40
    for i, (t, ls, f) in enumerate(steps):
        c.box(X, y, W, 100, ls, title=t, size=22, tsize=26, fill=f, name=t)
        ys.append(y)
        if i < len(steps) - 1:
            c.arrow(X + W/2, y + 100, X + W/2, y + 150)
        y += 150
    # thẻ cửa duyệt bên phải bước 4
    c.box(690, ys[3] - 30, 270, 160, ["dừng lượt, hiện thẻ:", "làm gì · lên cái gì", "hậu quả · bản lùi?", "→ Duyệt / Không"], title="Thẻ cửa duyệt", size=20, tsize=23, fill=FILL_C, name="the")
    c.arrow(X + W, ys[3] + 50, 690, ys[3] + 50)
    c.text(655, ys[3] + 36, "có hậu", size=19, italic=True, color="#444", anchor="middle")
    c.text(655, ys[3] + 80, "quả", size=19, italic=True, color="#444", anchor="middle")
    c.text(825, ys[3] + 152, "một chữ “có” gõ trong ô chat", size=19, italic=True, color="#444", anchor="middle")
    c.text(825, ys[3] + 176, "không mở được cửa", size=19, italic=True, color="#444", anchor="middle")
    # vòng lặp 6 → 3
    c.path(f"M {X} {ys[5]+50} L 30 {ys[5]+50} L 30 {ys[2]+50} L {X} {ys[2]+50}")
    c.text(22, (ys[2] + ys[5]) / 2 + 60, "lặp", size=22, italic=True, color="#444", anchor="start")
    # 7 → 3 nếu chưa đạt
    c.path(f"M {X+W} {ys[6]+50} L 985 {ys[6]+50} L 985 {ys[2]+80} L {X+W} {ys[2]+80}", dash="10,8")
    c.text(975, ys[5] + 20, "chưa đạt →", size=22, italic=True, color="#444", anchor="end")
    c.text(975, ys[5] + 48, "thêm một vòng", size=22, italic=True, color="#444", anchor="end")
    c.check_overlap()
    return c.svg()

async def render(svg, name, scale=1):
    p = os.path.join(OUT, name + ".svg")
    open(p, "w").write(svg)
    async with async_playwright() as pw:
        b = await pw.chromium.launch()
        pg = await b.new_page(device_scale_factor=scale)
        await pg.set_content(f'<html><body style="margin:0">{svg}</body></html>')
        el = await pg.query_selector("svg")
        await el.screenshot(path=os.path.join(OUT, name + ".png"))
        await b.close()

async def main():
    await render(fig1(), "fig1_kien_truc")
    await render(fig2(), "fig2_mot_luot")
    print("ok")

asyncio.run(main())
