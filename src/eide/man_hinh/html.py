# -*- coding: utf-8 -*-
"""Dựng HTML từ `ManHinh` — bản xem 1:1 với panel thật.

Bốn lựa chọn của bộ render này, và mỗi lựa chọn là một chỗ nó có thể nói dối:

1. **Tỉ lệ 1:1, đơn vị `px`.** Render theo phần trăm sẽ cho một bản xem đẹp mà vô dụng: người
   xem không đối chiếu được nó với màn hình thật, và đó là toàn bộ lý do bản render tồn tại.
2. **Vẽ bằng màu PANEL SẼ HIỆN, không bằng màu người thiết kế gõ vào.** Nếu vẽ `#FF8040` trong
   khi panel RGB565 hiện `#FF8242` thì bản xem **đẹp hơn** màn hình thật, và người dùng duyệt
   một thứ họ sẽ không nhận được. Đây là N6 áp vào một bức tranh.
3. **Trang tự khai độ phân giải, driver, và TRÍCH DẪN nguồn của cấu hình ấy.** Một bản render
   không nói nó vẽ cho panel nào thì không phân biệt được với ảnh chụp màn hình máy tính.
4. **Trang tự khai những gì nó KHÔNG kiểm được.** Một phần tử tràn biên vẫn vẽ bình thường
   trong trình duyệt (trình duyệt không cắt như LTDC), nên nếu trang không tự khai thì nó đẹp
   hơn màn hình thật — đúng bài học DEV-362: một dòng "không thấy gì" không kèm phạm vi sẽ
   được đọc thành "không có gì".

Không tài nguyên mạng nào: giao diện mở trang này trong `WKWebView`, và một `<script src>` trỏ
ra Internet trong một trang do mô hình sinh là một đường ra ngoài mà dự án không cho phép. CSS
nội tuyến, không ảnh ngoài, không phông tải về.
"""
from __future__ import annotations

from html import escape

from ..knowledge.man_hinh import HoSoManHinh, kiem_dem_khung
from .mo_hinh import FONT_BSP, NGOAI_PHAM_VI, KetQuaKiem, ManHinh, PhanTu, luong_hoa

# Phông của trang xem. Dùng phông đơn cách của hệ thống để bề rộng chữ trong bản xem gần với
# bề rộng font bitmap đơn cách của BSP — gần, chứ KHÔNG bằng. Phép kiểm E1102 trong `mo_hinh`
# là chỗ nói chính xác chữ có vừa hay không; bản xem chỉ để nhìn.
_PHONG = ("ui-monospace, SFMono-Regular, Menlo, Consolas, monospace")


def _o(p: PhanTu, he_mau: str) -> str:
    """Một phần tử → một `<div>` đặt tuyệt đối theo pixel panel."""
    mau_chu = luong_hoa(p.mau_chu, he_mau) if p.mau_chu else ""
    mau_nen = luong_hoa(p.mau_nen, he_mau) if p.mau_nen else ""
    kieu = [f"left:{p.x}px", f"top:{p.y}px", f"width:{p.w}px", f"height:{p.h}px"]
    than = ""

    if p.loai == "line":
        kieu.append(f"background:{mau_nen or mau_chu or '#FFFFFF'}")
    elif p.loai == "rect":
        if mau_nen:
            kieu.append(f"background:{mau_nen}")
        else:
            kieu.append(f"border:1px solid {mau_chu or '#FFFFFF'}")
    elif p.loai == "image":
        # KHÔNG nhúng ảnh: tệp bitmap của firmware là `.bmp` trong mã nguồn, và vẽ một ảnh
        # giả vào đây sẽ là một bản xem nói dối. Vẽ khung + tên tệp, nói rõ là chỗ dành sẵn.
        kieu += ["border:1px dashed #9CA3AF", "color:#9CA3AF", "font-size:10px",
                 "display:flex", "align-items:center", "justify-content:center",
                 "text-align:center"]
        than = escape(p.nguon or "(chưa có tệp)")
    elif p.loai == "bar":
        gt = 0.0 if p.gia_tri is None else max(0.0, min(100.0, p.gia_tri))
        trong = int(p.w * gt / 100)
        kieu += [f"border:1px solid {mau_chu or '#FFFFFF'}", "box-sizing:border-box"]
        than = (f'<i style="display:block;height:100%;width:{trong}px;'
                f'background:{mau_chu or "#FFFFFF"}"></i>')
    elif p.loai in ("text", "button"):
        f = FONT_BSP.get(p.co_chu)
        kieu += [f"font-family:{_PHONG}",
                 f"font-size:{p.co_chu}px", f"line-height:{p.h}px",
                 f"color:{mau_chu or '#FFFFFF'}",
                 "white-space:pre", "overflow:hidden"]
        if f:
            # Ép bề rộng một ký tự đúng bằng `Width` của font BSP. Không ép thì bản xem dùng
            # bề rộng của phông hệ thống, và chữ trong bản xem dài ngắn khác trên panel —
            # tức bản xem nói sai về đúng cái người dùng nhìn nó để kiểm.
            kieu.append(f"letter-spacing:0; font-stretch:normal; width:{p.w}px")
            kieu.append(f"--bsp-w:{f[0]}px")
        if mau_nen:
            kieu.append(f"background:{mau_nen}")
        if p.loai == "button":
            kieu += [f"border:1px solid {mau_chu or '#FFFFFF'}", "box-sizing:border-box",
                     "display:flex", "align-items:center", "justify-content:center"]
        elif p.can_le == "center":
            kieu.append("text-align:center")
        elif p.can_le == "right":
            kieu.append("text-align:right")
        than = escape(p.chu)

    return (f'<div class="pt" data-id="{escape(p.id)}" data-loai="{escape(p.loai)}" '
            f'style="{";".join(kieu)}">{than}</div>')


def _bang_kiem(kq: KetQuaKiem | None) -> str:
    """Phần "trang tự khai" — lỗi, cảnh báo, chưa kiểm được, và NGOÀI phạm vi."""
    p: list[str] = ['<section class="kiem">']
    if kq is None:
        p.append('<p class="chua">Bản vẽ này <b>chưa qua phép kiểm nào</b>. Gọi '
                 '<code>screen.check</code> để biết nó có chạy được trên panel thật không.</p>')
        return "".join(p) + "</section>"

    if kq.loi:
        p.append(f'<h3 class="xau">{len(kq.loi)} lỗi — thiết kế này KHÔNG chạy đúng trên panel'
                 " thật</h3><ul>")
        for x in kq.loi:
            p.append(f'<li><code>{escape(x["ma"])}</code>'
                     + (f' <b>{escape(x["phan_tu"])}</b>' if x.get("phan_tu") else "")
                     + f' — {escape(x["vi_sao"])} <i>{escape(x.get("cach_sua", ""))}</i></li>')
        p.append("</ul>")
    else:
        p.append('<h3 class="tot">Không lỗi nào ở những chỗ phép kiểm này chạm tới</h3>')

    if kq.canh_bao:
        p.append(f"<h3>{len(kq.canh_bao)} cảnh báo</h3><ul>")
        for x in kq.canh_bao:
            p.append(f'<li><code>{escape(x["ma"])}</code> — {escape(x["vi_sao"])} '
                     f'<i>{escape(x.get("cach_sua", ""))}</i></li>')
        p.append("</ul>")

    if kq.chua_kiem:
        p.append("<h3>Chưa đủ dữ kiện để kiểm</h3><ul>")
        for x in kq.chua_kiem:
            p.append(f'<li><code>{escape(x.get("ma", ""))}</code> — '
                     f'{escape(x["vi_sao"])}</li>')
        p.append("</ul>")

    # Luôn in, kể cả khi không lỗi — đây là chỗ giữ cho câu "không lỗi" ở trên còn nghĩa.
    p.append("<h3>Phép kiểm này đã chạm tới</h3><ul>"
             "<li>biên panel: mọi phần tử có nằm trong khung không</li>"
             "<li>cỡ chữ: có trong thư viện BSP không, và chữ có vừa ô không</li>"
             "<li>hệ màu: hai màu khác nhau có thành một màu trên panel không</li>"
             "<li>bộ đệm khung: có vừa RAM không</li></ul>")
    p.append("<h3>Và nó KHÔNG kiểm được</h3><ul>")
    for x in NGOAI_PHAM_VI:
        p.append(f"<li>{escape(x)}</li>")
    p.append("</ul></section>")
    return "".join(p)


def _bang_ho_so(hs: HoSoManHinh, he_mau: str, mh: ManHinh) -> str:
    """Hồ sơ panel + trích dẫn nguồn của từng trường."""
    dong: list[tuple[str, str, str]] = [
        ("Độ phân giải", f"{hs.rong} × {hs.cao} px", hs.nguon.get("lcd.width", "")),
        ("Hệ màu", he_mau + (f" (panel cũng nhận {', '.join(hs.he_mau_khac)})"
                             if hs.he_mau_khac else ""), hs.nguon.get("lcd.format", "")),
        ("Đường chéo", f"{hs.inch:g}\"" if hs.inch else "— tài liệu không nói",
         hs.nguon.get("lcd.inch", "")),
        ("DPI", (f"{hs.dpi:.0f}" + (" — TÍNH ra từ hai dòng trên, không đọc được từ tài liệu"
                                    if hs.dpi_la_tinh_ra else "")) if hs.dpi
         else "— chưa tính được (thiếu đường chéo)", ""),
        ("Driver panel", hs.driver or "— tài liệu không nói", hs.nguon.get("lcd.driver", "")),
        ("Bus", hs.bus or "— tài liệu không nói", hs.nguon.get("lcd.bus", "")),
        ("Cảm ứng", {True: "có", False: "KHÔNG", None: "— tài liệu không nói"}[hs.cam_ung],
         hs.nguon.get("lcd.touch", "")),
    ]
    h = ['<section class="hoso"><h3>Panel này — cấu hình đọc từ tài liệu, không tự đặt</h3>',
         "<table>"]
    for ten, gt, tr in dong:
        h.append(f"<tr><th>{escape(ten)}</th><td>{escape(gt)}</td>"
                 f'<td class="tr">{escape(tr[:150]) if tr else ""}</td></tr>')
    h.append("</table>")
    dem = kiem_dem_khung(hs.rong, hs.cao, he_mau)
    h.append(f'<p class="dem">{escape(dem["note_vi"])}</p>')
    if hs.thieu:
        h.append('<p class="chua">Tài liệu KHÔNG nói: '
                 + ", ".join(f"<code>{escape(k)}</code>" for k in hs.thieu)
                 + ". Những trường ấy chưa được điền bằng bất kỳ giá trị mặc định nào.</p>")
    h.append("</section>")
    return "".join(h)


_CSS = """
*{box-sizing:border-box}
body{margin:0;padding:16px;background:#F3F4F6;color:#111827;
     font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
h2{margin:0 0 4px;font-size:15px}
h3{margin:14px 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.04em;
   color:#6B7280}
h3.xau{color:#B91C1C}h3.tot{color:#15803D}
.khung{position:relative;overflow:hidden;border-radius:4px}
.vien{display:inline-block;padding:14px;background:#1F2937;border-radius:12px;
      box-shadow:0 2px 10px rgba(0,0,0,.25)}
.nhan{color:#9CA3AF;font-size:11px;margin:0 0 8px;font-variant-numeric:tabular-nums}
.pt{position:absolute;overflow:hidden}
.kiem,.hoso{background:#fff;border:1px solid #E5E7EB;border-radius:6px;padding:12px 14px;
            margin-top:14px;max-width:980px}
table{border-collapse:collapse;width:100%}
th,td{text-align:left;padding:3px 8px 3px 0;vertical-align:top;font-weight:400}
th{color:#6B7280;white-space:nowrap;width:120px}
td.tr{color:#6B7280;font-size:11px;font-style:italic}
ul{margin:4px 0 0;padding-left:18px}li{margin:3px 0}
code{background:#F3F4F6;padding:1px 4px;border-radius:3px;font-size:11px}
i{color:#6B7280;font-style:normal}
.chua{color:#92400E;background:#FFFBEB;padding:7px 9px;border-radius:4px;margin:8px 0 0}
.dem{margin:8px 0 0;color:#374151}
.goc{max-width:980px;color:#6B7280;font-size:11px;margin-top:14px}
@media (prefers-color-scheme:dark){
  body{background:#111827;color:#E5E7EB}
  .kiem,.hoso{background:#1F2937;border-color:#374151}
  code{background:#374151}
  th,td.tr,i,.nhan{color:#9CA3AF}
  .chua{background:#422006;color:#FDE68A}
  .dem{color:#D1D5DB}
}
"""


def dung_html(mh: ManHinh, hs: HoSoManHinh, *, kq: KetQuaKiem | None = None) -> str:
    """Trang HTML xem bản thiết kế — 1:1 với panel, tự khai cấu hình và tự khai giới hạn."""
    he_mau = mh.he_mau or hs.he_mau
    nen = luong_hoa(mh.mau_nen, he_mau)
    o = "".join(_o(p, he_mau) for p in mh.phan_tu)

    nhan = (f"{mh.rong} × {mh.cao} px · {he_mau}"
            + (f" · {hs.driver}" if hs.driver else "")
            + (f" · {hs.bus}" if hs.bus else "")
            + " · tỉ lệ 1:1")
    return f"""<!DOCTYPE html>
<meta charset="utf-8">
<title>Màn hình “{escape(mh.ten)}” — {mh.rong}×{mh.cao}</title>
<style>{_CSS}</style>
<h2>Màn hình “{escape(mh.ten)}”</h2>
<p class="nhan">{escape(nhan)}</p>
<div class="vien">
  <div class="khung" style="width:{mh.rong}px;height:{mh.cao}px;background:{nen}">{o}</div>
</div>
{_bang_ho_so(hs, he_mau, mh)}
{_bang_kiem(kq)}
<p class="goc">Trang này do <code>screen.render</code> dựng ra từ hiện vật
<code>ui_screen:{escape(mh.ten)}</code> — nó KHÔNG phải bản vẽ tay, và sửa trang này không sửa
bản thiết kế. Màu trong khung là màu <b>panel sẽ hiện</b> sau khi hệ màu {escape(he_mau)} cắt
bit, không phải màu gõ vào bản thiết kế.</p>
"""
