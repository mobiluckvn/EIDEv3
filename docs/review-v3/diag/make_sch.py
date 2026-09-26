# -*- coding: utf-8 -*-
from diagram_html import box, render, shoot
b = f"""<div class="rows">
<div class="row center"><div class="note b">Nguồn sự thật KHÔNG đổi: CKM (chip · chân · net · module · Fact pinout đã duyệt). Sơ đồ .kicad_sch là DẠNG NGƯỜI của CKM — sinh ra, không thay thế</div></div>
<div class="row">{box('ckm','CKM + Fact pinout (VÀNG/NGƯỜI)',['module_graph, netlist nội bộ, Fact pin.AF','đã có — không sửa'],'gold')}{box('skidl','sch.compose → SKiDL (Python)',['tác tử viết mô tả mạch bằng SKiDL','engine chung với KiCad SKiDL MCP','kiểm cú pháp + chạy trong sandbox'],'teal')}{box('net','Netlist KiCad + ERC',['SKiDL → .net (KiCad)','ERC SKiDL + board.check (ERC nội bộ)','0 blocker mới đi tiếp'],'plain')}</div>
<div class="row">{box('sym','sch.symbols',['kicad-symbols tải như DỮ LIỆU (đối chiếu tên chân ↔ Fact)','chip lạ: sinh symbol từ Fact pinout (.kicad_sym)'],'plain')}{box('place','sch.place — bố cục theo module',['mỗi module một vùng lưới · IC giữa, thụ động quanh chân','nguồn trên / GND dưới · dây dài → nhãn net','tiêu chí bằng số: 0 chồng, 0 cắt, ≤ N gấp'],'teal')}{box('write','sch.write → .kicad_sch (kiutils)',['S-expression KiCad 8/9 · uuid ổn định theo ref','ghi vào git = changeset author agent'],'plain')}</div>
<div class="row">{box('render','sch.render → SVG/PDF',['renderer nội bộ S-expr → SVG (chính; máy KHÔNG cài KiCad)','PDF/PNG bằng cairosvg','suy giảm: sơ đồ khối/đồ thị net (đã có)'],'gold')}{box('ui','Tab Thiết kế · khối A5.8',['SVG tương tác: bấm ký hiệu → Fact/nguồn','Vì sao? · diff sch v(n-1)→v(n) · STALE','Xuất gói (mở ở máy khác) · Nạp lại'],'red')}{box('rt','Round-trip (ING-D)',['người sửa ở máy có KiCad → chép về → nạp lại','diff netlist ↔ CKM → changeset human','net/linh kiện mới → STALE module, hỏi'],'red')}</div>
<div class="row center"><div class="note red">Round-trip: nạp lại .kicad_sch → so với CKM → changeset author = human → quay về ô đầu (CKM). Cách ly: mọi thứ ở namespace sch.* + cờ features.schematic (mặc định TẮT); không đổi hợp đồng tool hiện có; PCB/Gerber vẫn ngoài phạm vi (UC15)</div></div>
</div>"""
ar = [dict(**{'from': 'ckm', 'to': 'skidl', 'dir': 'right'}), dict(**{'from': 'skidl', 'to': 'net', 'dir': 'right'}), dict(**{'from': 'net', 'to': 'write', 'dir': 'down', 'label': 'netlist đã ERC'}),
      dict(**{'from': 'sym', 'to': 'place', 'dir': 'right'}), dict(**{'from': 'place', 'to': 'write', 'dir': 'right'}), dict(**{'from': 'ckm', 'to': 'sym', 'dir': 'down', 'label': 'Fact pinout'}),
      dict(**{'from': 'write', 'to': 'render', 'dir': 'down', 'ox': -300, 'ox2': 150, 'label': '.kicad_sch'}), dict(**{'from': 'render', 'to': 'ui', 'dir': 'right'}), dict(**{'from': 'ui', 'to': 'rt', 'dir': 'right', 'label': 'người sửa'})]
render('s1_sch_pipeline', b, ar, width=1000, gap=44)
shoot(['s1_sch_pipeline'])
print('ok')
