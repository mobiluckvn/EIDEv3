# -*- coding: utf-8 -*-
"""Sinh tài liệu yêu cầu phát triển phần mềm robot hai bánh tự cân bằng.
Mọi con số lấy thẳng từ mã đã chạy được: du-lieu/robot-tu-can-bang/firmware/
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

RA = "docs/robot-tu-can-bang/YEU-CAU-PHAT-TRIEN-PHAN-MEM-ROBOT-TU-CAN-BANG.docx"
FONT = "Times New Roman"

doc = Document()

# ---------------------------------------------------------------- trang giấy
for sec in doc.sections:
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.top_margin = Cm(2.0)
    sec.bottom_margin = Cm(2.0)
    sec.left_margin = Cm(3.0)
    sec.right_margin = Cm(2.0)

# ---------------------------------------------------------------- kiểu chữ
st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.3

for name, size in (("Heading 1", 16), ("Heading 2", 13.5), ("Heading 3", 12.5)):
    s = doc.styles[name]
    s.font.name = FONT
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.color.rgb = RGBColor(0x00, 0x00, 0x00)
    s.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    s.paragraph_format.space_before = Pt(14 if name == "Heading 1" else 10)
    s.paragraph_format.space_after = Pt(6)
    s.paragraph_format.keep_with_next = True


def p(text="", bold=False, italic=False, align=None, size=None, space_after=None):
    par = doc.add_paragraph()
    if text:
        r = par.add_run(text)
        r.bold = bold
        r.italic = italic
        if size:
            r.font.size = Pt(size)
    if align == "center":
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "right":
        par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    else:
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if space_after is not None:
        par.paragraph_format.space_after = Pt(space_after)
    return par


def rich(parts, align=None):
    """parts: list các (chữ, kiểu) với kiểu trong {'', 'b', 'i', 'c'} (c = chữ máy)."""
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if align is None else WD_ALIGN_PARAGRAPH.CENTER
    for txt, kind in parts:
        r = par.add_run(txt)
        if "b" in kind:
            r.bold = True
        if "i" in kind:
            r.italic = True
        if "c" in kind:
            r.font.name = "Consolas"
            r.font.size = Pt(10.5)
            r.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    return par


def bullet(text, level=0, bold_head=None):
    par = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    par.paragraph_format.space_after = Pt(3)
    par.paragraph_format.line_spacing = 1.25
    if bold_head:
        par.add_run(bold_head).bold = True
    par.add_run(text)
    for r in par.runs:
        r.font.name = FONT
        r.font.size = Pt(12)
    return par


def numbered(text, bold_head=None):
    par = doc.add_paragraph(style="List Number")
    par.paragraph_format.space_after = Pt(3)
    par.paragraph_format.line_spacing = 1.25
    if bold_head:
        par.add_run(bold_head).bold = True
    par.add_run(text)
    for r in par.runs:
        r.font.name = FONT
        r.font.size = Pt(12)
    return par


def code(lines):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Cm(0.6)
    par.paragraph_format.space_before = Pt(4)
    par.paragraph_format.space_after = Pt(8)
    par.paragraph_format.line_spacing = 1.0
    pPr = par._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), "F2F2F2")
    pPr.append(shd)
    for i, ln in enumerate(lines):
        r = par.add_run(ln + ("\n" if i < len(lines) - 1 else ""))
        r.font.name = "Consolas"
        r.font.size = Pt(10)
        r.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    return par


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def table(caption, headers, rows, widths=None, mono_cols=(), font_size=10.5):
    cnt = doc.add_paragraph()
    cnt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cnt.paragraph_format.space_before = Pt(8)
    cnt.paragraph_format.space_after = Pt(3)
    r = cnt.add_run(caption)
    r.bold = True
    r.font.name = FONT
    r.font.size = Pt(11)

    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        par = hdr[i].paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_after = Pt(2)
        run = par.add_run(h)
        run.bold = True
        run.font.name = FONT
        run.font.size = Pt(font_size)
        shade(hdr[i], "DCE6F1")

    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            par = cells[i].paragraphs[0]
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.line_spacing = 1.1
            run = par.add_run(str(val))
            if i in mono_cols:
                run.font.name = "Consolas"
                run.font.size = Pt(9.5)
                run.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            else:
                run.font.name = FONT
                run.font.size = Pt(font_size)

    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# ================================================================= TRANG BÌA
p()
p()
p("HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG", bold=True, align="center", size=12)
p()
p()
p("YÊU CẦU PHÁT TRIỂN PHẦN MỀM", bold=True, align="center", size=20)
p("ROBOT HAI BÁNH TỰ CÂN BẰNG", bold=True, align="center", size=20)
p()
p("Bộ điều khiển ATmega328P 16 MHz — hai động cơ bước qua mạch lái A4988", align="center", size=12.5)
p("Cảm biến góc MPU6050 nối bằng đường I2C", align="center", size=12.5)
p()
p()
tb = doc.add_table(rows=7, cols=2)
tb.alignment = WD_TABLE_ALIGNMENT.CENTER
meta = [
    ("Mã tài liệu", "YCPM-ROBOT-CB-01"),
    ("Bản", "1.1"),
    ("Ngày", "03/10/2026"),
    ("Người đọc tài liệu này", "Kỹ sư phần mềm nhúng mới vào việc"),
    ("Nguồn số liệu", "Mã nguồn bản đã chạy đứng được trên bo thật, ngày 01/10/2026"),
    ("Sửa so với bản 1.0", "Thêm mục 3.2: ánh xạ 14 byte đọc từ cảm biến ra từng trục"),
    ("Trạng thái", "Chờ duyệt"),
]
for i, (k, v) in enumerate(meta):
    c0, c1 = tb.rows[i].cells
    c0.width, c1.width = Cm(5.0), Cm(9.5)
    for cell, txt, bold in ((c0, k, True), (c1, v, False)):
        cell.text = ""
        par = cell.paragraphs[0]
        par.paragraph_format.space_after = Pt(3)
        run = par.add_run(txt)
        run.bold = bold
        run.font.name = FONT
        run.font.size = Pt(11)

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ================================================================= MỤC LỤC
p("MỤC LỤC", bold=True, align="center", size=15)
par = doc.add_paragraph()
fld = OxmlElement("w:fldSimple")
fld.set(qn("w:instr"), r'TOC \o "1-3" \h \z \u')
inner = OxmlElement("w:r")
t_ = OxmlElement("w:t")
t_.text = "Bấm chuột phải vào đây rồi chọn Update Field để hiện mục lục."
inner.append(t_)
fld.append(inner)
par._p.append(fld)

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ================================================================= MỞ ĐẦU
doc.add_heading("Tài liệu này dùng để làm gì", level=1)

p("Tài liệu này mô tả phần mềm cần viết cho một con robot hai bánh tự đứng. Người đọc là kỹ sư "
  "phần mềm nhúng mới vào việc, đã biết ngôn ngữ C và đã từng nạp chương trình vào vi điều khiển, "
  "nhưng chưa làm bài điều khiển cân bằng nào.")

p("Điểm khác của tài liệu này so với một bản yêu cầu thông thường: tất cả con số trong đây đã được "
  "thử trên bo thật và robot đứng được với đúng những con số đó. Không có con số nào do người viết "
  "tự nghĩ ra để đó rồi chờ người làm tự dò. Nếu bạn làm đúng những gì ghi ở Chương 3, robot sẽ đứng.")

p("Hãy đọc hết Chương 1 trước khi viết dòng mã đầu tiên. Có bốn điều cấm trong đó, và vi phạm bất kỳ "
  "điều nào cũng làm robot không đứng được, nhưng chương trình vẫn dịch ra bình thường nên bạn sẽ "
  "không biết mình sai ở đâu.")

table(
    "Bảng 0.1 — Bốn chương và việc phải làm trong từng chương",
    ["Chương", "Tên", "Bạn làm gì sau khi đọc"],
    [
        ["1", "Phân tích", "Hiểu bài toán, biết các chân nối, biết bốn điều cấm"],
        ["2", "Thiết kế", "Hiểu ba tầng thời gian, tám trạng thái và đường đi của dữ liệu"],
        ["3", "Viết mã", "Có đủ mọi con số và mọi thanh ghi để viết ra mã chạy được"],
        ["4", "Kiểm thử", "Biết cách đo để chứng minh phần mềm mình viết đúng, không phải đoán"],
    ],
    widths=[1.8, 3.2, 10.0],
)

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ================================================================= CHƯƠNG 1
doc.add_heading("Chương 1 — Phân tích", level=1)

doc.add_heading("1.1. Robot phải làm được gì", level=2)

p("Robot có hai bánh đặt cùng một trục, không có bánh chống. Để nó khỏi đổ, phần mềm phải liên tục "
  "đo độ nghiêng của thân robot rồi cho hai bánh chạy về phía robot đang nghiêng tới. Robot nghiêng "
  "về trước thì bánh chạy tới, nghiêng về sau thì bánh chạy lùi. Việc đó lặp lại 250 lần mỗi giây.")

table(
    "Bảng 1.1 — Những việc phần mềm phải làm được",
    ["Mã", "Việc", "Làm xong nghĩa là"],
    [
        ["YC-01", "Báo hiệu bằng còi khi bật nguồn và khi đổi trạng thái",
         "Nghe tiếng còi là biết robot đang ở bước nào, không cần cắm máy tính"],
        ["YC-02", "Đo độ lệch của cảm biến góc khi người bấm nút",
         "Lấy 500 mẫu khi robot nằm yên, tính giá trị trung bình rồi trừ ra khỏi số đo sau này"],
        ["YC-03", "Nhận lệnh từ một nút bấm",
         "Bấm nhả nhanh thì đổi trạng thái, giữ 2 giây thì vào phần đo điểm cân bằng"],
        ["YC-04", "Tự vào chế độ giữ cân bằng khi người dựng robot lên",
         "Khi độ nghiêng đi qua khoảng cộng trừ 0,5 độ thì tự bật, không cần bấm thêm"],
        ["YC-05", "Ngắt động cơ khi robot đã đổ",
         "Độ nghiêng vượt 30 độ thì tắt xung bước trong vòng 4 ms và còi báo"],
        ["YC-06", "Ngắt động cơ khi pin yếu",
         "Số đọc từ chân A0 xuống dưới 420 thì không cho chạy nữa"],
        ["YC-07", "Gửi số đo ra cổng nối tiếp",
         "Mỗi 100 ms gửi một dòng chữ đọc được bằng mắt trên màn hình máy tính"],
        ["YC-08", "Có chế độ tự kiểm để dò dấu",
         "Giữ nút lúc bật nguồn thì vào chế độ kiểm dấu góc rồi kiểm chiều quay bánh"],
    ],
    widths=[1.7, 5.3, 8.0],
)

doc.add_heading("1.2. Phần cứng bạn sẽ làm việc với", level=2)

table(
    "Bảng 1.2 — Linh kiện chính",
    ["Khối", "Linh kiện", "Điều cần nhớ khi viết mã"],
    [
        ["Bộ điều khiển", "ATmega328P chạy ở 16 MHz",
         "Chỉ có 2 KB bộ nhớ chạy và 32 KB bộ nhớ chương trình. Không có bộ tính số thực bằng mạch, "
         "mọi phép số thực đều do thư viện làm bằng phần mềm nên rất chậm"],
        ["Cảm biến góc", "MPU6050 nối bằng đường I2C, địa chỉ 0x68",
         "Đọc một lần 14 byte liên tiếp từ thanh ghi 0x3B. Thang đo gia tốc đặt ở cộng trừ 4 g"],
        ["Mạch lái động cơ", "Hai mạch A4988",
         "Mỗi mạch cần một chân phát xung và một chân chọn chiều. Mỗi xung làm động cơ đi một bước"],
        ["Động cơ", "Hai động cơ bước",
         "Tốc độ quay do số xung trên giây quyết định, không do mức điện áp"],
        ["Còi", "Còi chip ở chân D10",
         "Chỉ cần bật tắt mức điện, không cần phát xung điều tần"],
        ["Nút bấm", "Một nút ở chân D12",
         "Dùng điện trở kéo lên bên trong chip. Bấm xuống thì chân đọc được mức thấp"],
        ["Đo pin", "Cầu chia điện trở vào chân A0",
         "Đọc bằng bộ đổi tín hiệu tương tự sang số, so với ngưỡng 420"],
    ],
    widths=[3.0, 4.0, 8.0],
)

doc.add_heading("1.3. Bảng chân nối", level=2)

p("Đây là bảng quan trọng nhất của chương này. Nối sai một chân thì robot không đứng, và chương "
  "trình vẫn dịch ra bình thường.")

table(
    "Bảng 1.3 — Các chân và việc của từng chân",
    ["Chân trên bo", "Chân của chip", "Hướng", "Dùng để làm gì"],
    [
        ["D4", "PD4", "ra", "Chọn chiều quay bánh phải"],
        ["D5", "PD5", "ra", "Phát xung bước bánh phải"],
        ["D6", "PD6", "ra", "Chọn chiều quay bánh trái"],
        ["D7", "PD7", "ra", "Phát xung bước bánh trái"],
        ["D10", "PB2", "ra", "Còi báo hiệu"],
        ["D12", "PB4", "vào, kéo lên bên trong", "Nút bấm"],
        ["D13", "PB5", "ra", "Chân đo thời gian chạy của hàm ngắt, dùng cho máy hiện sóng"],
        ["A0", "PC0", "vào", "Đo điện áp pin qua cầu chia"],
        ["A4", "PC4", "hai chiều", "Đường dữ liệu I2C"],
        ["A5", "PC5", "hai chiều", "Đường nhịp I2C"],
        ["D0", "PD0", "vào, kéo lên bên trong", "Nhận của cổng nối tiếp"],
        ["D1", "PD1", "ra", "Gửi của cổng nối tiếp"],
    ],
    widths=[2.6, 2.6, 4.2, 7.0],
)

p("Chân A1 được tài liệu phần cứng dành làm chân đo cho vòng 4 ms. Bản mã đã chạy chưa dùng chân "
  "này. Bạn có thể thêm, nhưng đừng dùng A1 và D13 cho việc khác, vì hai chân đó là chỗ cắm máy "
  "hiện sóng khi nghiệm thu.")

doc.add_heading("1.4. Bốn điều cấm", level=2)

p("Bốn điều dưới đây là điều kiện bắt buộc của phần cứng. Vi phạm thì chương trình vẫn dịch được, "
  "vẫn nạp được, nhưng robot sẽ không đứng và bạn sẽ mất nhiều ngày để tìm ra lý do.")

doc.add_heading("Cấm 1 — Không được dùng số thực hoặc phép chia trong hàm ngắt 50 kHz", level=3)

p("Hàm ngắt phát xung bước chạy 50 000 lần mỗi giây. Chip chạy 16 triệu nhịp mỗi giây, nên mỗi lần "
  "ngắt chỉ có đúng 320 nhịp. Một phép chia số thực trên chip này mất khoảng 100 đến 400 nhịp, nên "
  "chỉ cần một phép chia là hàm ngắt chạy không kịp và xung bước bị lỗi nhịp.")

rich([("Cách làm đúng: dùng một bộ đếm số nguyên. Mỗi lần ngắt thì tăng bộ đếm lên một. Khi bộ đếm "
       "vượt quá giá trị ", ""), ("throttle", "c"),
      (" thì phát một xung rồi đặt bộ đếm về không. Như vậy chu kỳ xung bằng ", ""),
      ("(|throttle| + 1) × 20 µs", "cb"),
      (", và cả hàm chỉ gồm phép cộng, phép so sánh và phép gán.", "")])

doc.add_heading("Cấm 2 — Không được dùng hàm chờ chặn trong toàn bộ chương trình chính", level=3)

rich([("Không gọi ", ""), ("_delay_ms", "c"), (" hay bất kỳ vòng lặp chờ nào trong vòng lặp chính "
      "và trong các hàm nền. Khi chương trình đứng chờ thì hai hàm ngắt vẫn chạy, nhưng vòng tính "
      "góc 4 ms sẽ bị trễ hạn, và robot đổ. Mọi việc cần đo thời gian đều làm bằng cách so mốc thời "
      "gian hiện tại với mốc đã lưu, rồi đi tiếp ngay. Cách này gọi là làm việc không chặn.", "")])

doc.add_heading("Cấm 3 — Không được điều khiển dãy đèn WS2812", level=3)

p("Loại đèn này đòi phải cấm ngắt trong vài chục micro giây mỗi lần gửi dữ liệu. Cấm ngắt lâu như "
  "vậy sẽ làm trượt hạn của hàm ngắt 50 kHz. Nếu cần đèn báo trạng thái, hãy dùng loại đèn thường "
  "bật tắt bằng một chân, và không được lấy chân D13 hoặc A1 làm việc đó.")

doc.add_heading("Cấm 4 — Không được tắt động cơ bằng chân cho phép của mạch lái", level=3)

p("Chân cho phép của hai mạch A4988 đã được nối thẳng xuống đất ngay trên bo. Phần mềm không chạm "
  "được vào chân đó. Muốn dừng động cơ thì chỉ có một cách: ngừng phát xung bước. Khi ngừng phát "
  "xung, động cơ vẫn còn điện giữ trục nên bánh xe vẫn cứng, không quay tự do được. Muốn trục quay "
  "tự do thì phải tắt công tắc nguồn động cơ bằng tay.")

p("Hệ quả khi thử nghiệm: đang có nguồn động cơ thì đừng dùng tay quay cưỡng bức bánh xe, sẽ làm "
  "hỏng mạch lái.")

doc.add_heading("1.5. Ba thứ chỉ đo được trên bo, không suy ra được từ mã", level=2)

p("Phần này cho bạn biết trước chỗ sẽ mất thời gian, để khỏi đi tìm lỗi ở chỗ không có lỗi.")

table(
    "Bảng 1.4 — Những thứ phải dựng robot lên mới biết",
    ["Thứ cần biết", "Vì sao không đọc mã mà ra được", "Cách lấy"],
    [
        ["Dấu của cả vòng điều khiển",
         "Có ba chỗ có thể bị ngược dấu: chiều lắp cảm biến, chiều lắp động cơ, và dấu của phép tính. "
         "Khi robot đứng yên thì ba dấu này nhân với nhau thành một dấu duy nhất, nên đọc mã không tách "
         "ra được dấu nào đang sai",
         "Dùng chế độ tự kiểm ở mục 4.3. Chế độ đó tách ba dấu thành ba bài đo riêng"],
        ["Số bù của cảm biến gia tốc",
         "Mỗi bo lắp lệch một chút khác nhau, nên số này khác nhau theo từng bo",
         "Giữ nút 2 giây ở trạng thái dừng, chương trình tự lấy 500 mẫu rồi in kết quả ra cổng nối tiếp"],
        ["Hệ số của cầu chia đo pin",
         "Điện trở có sai số, mỗi bo cho số đọc khác nhau",
         "Đo điện áp pin bằng đồng hồ, so với số mà chương trình đọc được, rồi tính lại ngưỡng"],
    ],
    widths=[3.6, 7.0, 5.0],
)

p("Giá trị cho bo đang có sẵn trong Bảng 3.3. Nếu bạn làm trên đúng bo đó thì dùng luôn, khỏi đo lại.", italic=True)

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ================================================================= CHƯƠNG 2
doc.add_heading("Chương 2 — Thiết kế", level=1)

doc.add_heading("2.1. Ba tầng thời gian", level=2)

p("Phần mềm chia làm ba tầng chạy ở ba nhịp khác nhau. Tầng nhanh nhất làm việc đơn giản nhất. "
  "Chia như vậy để việc nặng không bao giờ chen vào việc gấp.")

table(
    "Bảng 2.1 — Ba tầng và việc của từng tầng",
    ["Tầng", "Nhịp", "Chạy ở đâu", "Làm gì", "Được dùng số thực"],
    [
        ["1", "50 000 lần mỗi giây", "Hàm ngắt của bộ đếm Timer2",
         "Phát xung bước và đặt mức chân chiều cho hai bánh", "Không"],
        ["2", "250 lần mỗi giây, tức 4 ms một lần", "Vòng lặp chính, chạy khi có cờ từ Timer0",
         "Đọc cảm biến, tính góc nghiêng, tính đầu ra điều khiển, đổi sang giá trị xung", "Có"],
        ["3", "Chạy liên tục khi rảnh", "Vòng lặp chính",
         "Quét nút bấm, bật tắt còi, đo pin, gửi số đo ra cổng nối tiếp", "Có"],
    ],
    widths=[1.3, 3.4, 3.6, 5.6, 2.3],
)

p("Tầng 2 không chạy trong hàm ngắt. Bộ đếm Timer0 ngắt mỗi 1 ms và chỉ làm một việc: đếm đến 4 rồi "
  "dựng một cờ. Vòng lặp chính thấy cờ dựng thì hạ cờ và chạy phần tính toán. Làm vậy để phần tính "
  "toán có số thực không bao giờ nằm trong hàm ngắt, và nếu nó chạy quá hạn thì ta đếm được số lần "
  "quá hạn thay vì bị treo chương trình.")

doc.add_heading("2.2. Đường đi của dữ liệu trong một vòng 4 ms", level=2)

code([
    "Đọc 14 byte từ cảm biến  ->  tách ra gia tốc 3 truc va toc do goc 3 truc",
    "                              |   (byte nao la gi: xem Bang 3.2)",
    "        cong so bu 92 vao gia toc truc Z (truc truoc sau), kep trong -8200..8200",
    "                              |",
    "        goc theo gia toc = asin(gia tri / 8200) x 57,29578",
    "                              |",
    "        goc chay = goc chay + toc do goc truc Y (truc nghieng) da tru do lech x 0,000031",
    "        goc chay = goc chay - toc do goc truc X (truc xoay) da tru do lech x 0,0000003",
    "        goc chay = goc chay x 0,9996 + goc theo gia toc x 0,0004",
    "                              |",
    "        bo dieu khien PID nhan goc chay, tra ra mot so trong khoang -400..400",
    "                              |",
    "        doi so do sang gia tri xung bang cong thuc o muc 3.7",
    "                              |",
    "        ghi gia tri xung vao bien dung chung cho tang 1",
])

p("Chỗ cần giải thích thêm là ba dòng tính góc chạy. Cảm biến gia tốc cho góc đúng về lâu dài nhưng "
  "bị rung động cơ làm nhiễu rất nhiều. Cảm biến tốc độ góc thì mượt nhưng cộng dồn sai số theo thời "
  "gian nên bị trôi. Ba dòng đó lấy phần mượt của cảm biến tốc độ góc, rồi mỗi vòng kéo nhẹ về phía "
  "góc gia tốc một lượng bằng bốn phần mười nghìn. Kết quả là góc vừa mượt vừa không trôi.")

doc.add_heading("2.3. Tám trạng thái", level=2)

table(
    "Bảng 2.2 — Tám trạng thái của robot",
    ["Tên trạng thái", "Robot đang làm gì", "Động cơ"],
    [
        ["STATE_INIT", "Chỉ là giá trị khai báo ban đầu. Không dùng, xem ghi chú dưới bảng", "Không phát xung"],
        ["STATE_CALIBRATING", "Đang lấy 500 mẫu để đo độ lệch của cảm biến tốc độ góc", "Không phát xung"],
        ["STATE_READY", "Đã đo xong, chờ người dựng robot lên", "Không phát xung"],
        ["STATE_BALANCING", "Đang giữ cân bằng", "Phát xung theo đầu ra điều khiển"],
        ["STATE_FALLEN", "Đã đổ hoặc pin yếu, chờ người bấm nút xác nhận", "Không phát xung"],
        ["STATE_STOPPED", "Đang dừng. Đây cũng là trạng thái ngay sau khi bật nguồn", "Không phát xung"],
        ["STATE_DIAG_ANGLE", "Chế độ kiểm dấu góc, còi kêu theo chiều nghiêng", "Không phát xung"],
        ["STATE_DIAG_MOTOR", "Chế độ kiểm chiều quay, hai bánh chạy tới 3 giây", "Phát xung cố định"],
    ],
    widths=[4.2, 8.0, 3.8],
    mono_cols=(0,),
)

rich([("Ghi chú về ", ""), ("STATE_INIT", "c"),
      (": trong bản đã chạy, hàm đặt ban đầu của phần trạng thái gán ngay giá trị ", ""),
      ("STATE_STOPPED", "c"), (", nên nhánh xử lý ", ""), ("STATE_INIT", "c"),
      (" không bao giờ chạy tới. Bạn vẫn nên khai báo tên đó để giữ số thứ tự, nhưng đừng trông chờ "
       "vào nó. Hệ quả cần nhớ: ", ""),
      ("sau khi bật nguồn robot nằm ở trạng thái dừng và chờ người bấm nút", "b"),
      (", nó không tự đo cảm biến. Có một bản hướng dẫn cũ trong kho ghi là robot tự đo ngay khi bật "
       "nguồn; điều đó không đúng với mã đã chạy.", "")])

doc.add_heading("2.4. Khi nào đổi trạng thái", level=2)

table(
    "Bảng 2.3 — Bảng chuyển trạng thái",
    ["Từ", "Sang", "Điều kiện"],
    [
        ["bật nguồn", "STATE_STOPPED", "Ngay khi hàm đặt ban đầu chạy, kèm một tiếng còi 100 ms"],
        ["STATE_STOPPED", "STATE_CALIBRATING", "Người bấm rồi nhả nút trong vòng dưới 2 giây"],
        ["STATE_CALIBRATING", "STATE_READY", "Đã lấy đủ 500 mẫu, kèm một tiếng còi 100 ms"],
        ["STATE_CALIBRATING", "STATE_DIAG_ANGLE", "Đã lấy đủ 500 mẫu và người đã giữ nút lúc bật nguồn"],
        ["STATE_CALIBRATING", "STATE_STOPPED", "Đọc cảm biến bị lỗi, hoặc người bấm nút để bỏ"],
        ["STATE_READY", "STATE_BALANCING", "Góc nghiêng nằm trong khoảng cộng trừ 0,5 độ và pin không yếu"],
        ["STATE_BALANCING", "STATE_FALLEN", "Góc nghiêng vượt quá cộng trừ 30 độ, hoặc pin yếu"],
        ["STATE_BALANCING", "STATE_STOPPED", "Người bấm nút"],
        ["STATE_READY", "STATE_STOPPED", "Người bấm nút"],
        ["STATE_FALLEN", "STATE_STOPPED", "Người bấm nút để xác nhận đã biết robot đổ"],
        ["STATE_STOPPED", "chế độ đo số bù", "Người giữ nút từ 2 giây trở lên"],
        ["STATE_DIAG_ANGLE", "STATE_DIAG_MOTOR", "Người bấm nhả nút, kèm một tiếng còi 600 ms"],
        ["STATE_DIAG_MOTOR", "STATE_STOPPED", "Đã chạy đủ 3 giây"],
    ],
    widths=[3.6, 3.8, 8.6],
    mono_cols=(0, 1),
)

doc.add_heading("2.5. Tiếng còi nói gì", level=2)

p("Còi là cách duy nhất để biết robot đang ở trạng thái nào khi không cắm máy tính. Hãy làm đúng "
  "bảng này, vì Chương 4 dùng nó để nghiệm thu.")

table(
    "Bảng 2.4 — Mã tiếng còi",
    ["Nghe thấy", "Nghĩa là"],
    [
        ["Một tiếng 100 ms ngay khi bật nguồn", "Chương trình đã chạy. Robot đang dừng, chờ bấm nút"],
        ["Tiếng 100 ms lặp lại mỗi 500 ms, nhiều nhất 5 tiếng", "Đang lấy 500 mẫu, giữ robot nằm yên"],
        ["Một tiếng 100 ms rồi 150 ms sau thêm một tiếng nữa", "Đã sẵn sàng, dựng robot lên được rồi"],
        ["Ba tiếng ngắn 50 ms liền nhau, nghỉ 600 ms rồi lặp lại", "Robot đã đổ, bấm nút để xác nhận"],
        ["Ba tiếng 80 ms trong mỗi giây, lặp không ngừng", "Không đọc được cảm biến. Bấm nút để tắt tiếng"],
        ["Một tiếng 200 ms", "Đã vào chế độ tự kiểm, hoặc đã xong phần kiểm chiều quay"],
        ["Một tiếng 600 ms", "Bắt đầu phần kiểm chiều quay bánh"],
        ["Một tiếng 500 ms", "Đã đo xong 500 mẫu số bù, kết quả in ra cổng nối tiếp"],
    ],
    widths=[7.0, 9.0],
)

doc.add_heading("2.6. Chia mã thành mười tệp", level=2)

table(
    "Bảng 2.5 — Mười tệp mã và việc của từng tệp",
    ["Tệp", "Việc", "Dòng"],
    [
        ["config.h", "Chứa toàn bộ số và tên chân. Không có mã chạy", "96"],
        ["main.c", "Đặt phần cứng ban đầu theo thứ tự, rồi vào vòng lặp chính", "87"],
        ["timer.c", "Đặt hai bộ đếm, chứa hai hàm ngắt, đếm thời gian theo ms", "75"],
        ["i2c.c", "Nói chuyện với cảm biến qua hai dây", "130"],
        ["mpu6050.c", "Đánh thức cảm biến, kiểm tra nhận dạng, đọc số, đo độ lệch", "189"],
        ["filter.c", "Trộn hai nguồn số đo thành một góc", "19"],
        ["pid.c", "Bộ điều khiển và phần tự học điểm cân bằng", "80"],
        ["motor.c", "Phát xung bước, đổi đầu ra điều khiển sang giá trị xung", "203"],
        ["fsm.c", "Tám trạng thái, nút bấm, còi, đo pin, vòng tính 4 ms", "431"],
        ["uart.c", "Gửi chữ ra cổng nối tiếp không chặn chương trình", "151"],
    ],
    widths=[3.4, 10.2, 1.8],
    mono_cols=(0,),
)

rich([("Lưu ý quan trọng: bản mã gốc còn một tệp tên ", ""), ("control.c", "c"),
      (" chứa một vòng điều khiển thứ hai, tính góc theo cách khác. Tệp đó ", ""),
      ("không chạy trên bo", "b"),
      (" và không được gọi từ đâu cả. Đừng viết tệp đó, và đừng lấy nó làm mẫu. Vòng điều khiển "
       "thật nằm trong ", ""), ("fsm.c", "c"), (".", "")])

doc.add_heading("2.7. Bộ nhớ dùng hết bao nhiêu", level=2)

p("Con số đo từ tệp nạp của bản đã chạy, bằng công cụ đọc kích thước đoạn mã. Bản của bạn nên nằm "
  "quanh mức này. Nếu lớn hơn nhiều thì nên xem lại chỗ nào gọi hàm số thực không cần thiết.")

table(
    "Bảng 2.6 — Bộ nhớ của bản đã chạy",
    ["Loại bộ nhớ", "Dùng", "Có tất cả", "Phần trăm"],
    [
        ["Bộ nhớ chương trình", "13 690 byte", "32 768 byte", "41,8 phần trăm"],
        ["Bộ nhớ chạy", "909 byte", "2 048 byte", "44,4 phần trăm"],
    ],
    widths=[5.0, 3.6, 3.6, 3.4],
)

p("Trong 13 690 byte đó có khoảng 532 byte là tệp control.c nói ở mục 2.6, tức phần không chạy. "
  "Bản của bạn không viết tệp đó nên sẽ nhỏ hơn chừng đó.", italic=True)

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ================================================================= CHƯƠNG 3
doc.add_heading("Chương 3 — Viết mã", level=1)

p("Chương này là phần bạn gõ theo. Mọi con số dưới đây đã chạy đúng trên bo thật. Đừng đổi con số "
  "nào trước khi robot đứng được lần đầu.", bold=True)

doc.add_heading("3.1. Thứ tự đặt phần cứng lúc mới bật nguồn", level=2)

p("Thứ tự này có lý do, làm sai thứ tự thì có bước không chạy.")

table(
    "Bảng 3.1 — Mười bước đặt ban đầu",
    ["Bước", "Làm gì", "Vì sao phải ở đúng chỗ này"],
    [
        ["1", "Đọc rồi lưu thanh ghi nguyên nhân khởi động lại, sau đó xoá nó về 0",
         "Thanh ghi này bị xoá khi chương trình chạy tiếp, nên phải đọc ở lệnh đầu"],
        ["2", "Tắt bộ đếm canh treo", "Nếu lần khởi động trước bị treo thì bộ đếm này còn đang bật"],
        ["3", "Đặt bốn chân động cơ là chân ra, rồi hạ hai chân xung xuống mức thấp",
         "Phải làm trước khi mở ngắt, để động cơ không giật một cái lúc mới bật"],
        ["4", "Đặt chân còi là chân ra, chân nút là chân vào có kéo lên", "Cần đọc được nút ở bước 7"],
        ["5", "Đặt cổng nối tiếp ở 9 600 baud", "Để các bước sau in được thông báo lỗi"],
        ["6", "In ra nguyên nhân khởi động lại đã lưu ở bước 1", "Giúp biết lần trước robot tắt vì lý do gì"],
        ["7", "Đọc chân nút. Nếu đang bị giữ thì bật cờ vào chế độ tự kiểm",
         "Phải đọc trước khi vào vòng lặp, vì người giữ nút ngay lúc bật nguồn"],
        ["8", "Đặt hai bộ đếm Timer0 và Timer2", "Sau bước này hai hàm ngắt sẵn sàng chạy"],
        ["9", "Mở ngắt chung", "Trước bước này mọi việc đặt phần cứng đã xong"],
        ["10", "Đặt đường I2C rồi đánh thức cảm biến. Nếu lỗi thì chuyển sang trạng thái dừng và bật còi lỗi",
         "Cần ngắt đã mở để hàm đếm thời gian chạy được"],
    ],
    widths=[1.3, 7.2, 7.5],
)

doc.add_heading("3.2. Mười bốn byte đọc từ cảm biến là byte nào", level=2)

p("Mỗi vòng 4 ms bạn đọc một lần 14 byte liên tiếp, bắt đầu từ thanh ghi 0x3B. Bảng dưới đây cho "
  "biết byte nào là số đo nào. Điều cần để ý: trong sáu số đo lấy được, vòng điều khiển chỉ dùng "
  "đúng ba số.")

table(
    "Bảng 3.2 — Mười bốn byte và cách dùng từng số",
    ["Byte", "Ghép thành", "Tên dùng trong tài liệu này", "Vòng điều khiển có dùng"],
    [
        ["0 và 1", "gia tốc trục X", "trục dựng, hướng từ dưới lên", "Không dùng"],
        ["2 và 3", "gia tốc trục Y", "trục ngang, hướng sang hai bên", "Không dùng"],
        ["4 và 5", "gia tốc trục Z", "trục trước sau", "Dùng — cộng số bù 92 vào số này"],
        ["6 và 7", "nhiệt độ", "—", "Không dùng"],
        ["8 và 9", "tốc độ góc trục X", "trục xoay", "Dùng — nhân 0,0000003 rồi trừ khỏi góc chạy"],
        ["10 và 11", "tốc độ góc trục Y", "trục nghiêng", "Dùng — nhân 0,000031 rồi cộng vào góc chạy"],
        ["12 và 13", "tốc độ góc trục Z", "—", "Không dùng"],
    ],
    widths=[2.2, 3.4, 4.6, 5.8],
)

p("Cách ghép mỗi cặp byte: byte đọc trước là byte cao, byte đọc sau là byte thấp, ghép lại thành "
  "một số nguyên có dấu rộng 16 bit. Trong C viết là dịch byte cao sang trái 8 bit rồi hợp bit với "
  "byte thấp, sau đó đổi kiểu sang số nguyên 16 bit có dấu.")

p("Hai số tốc độ góc ở byte 8 đến 11 đều phải trừ đi độ lệch đã đo được ở phần 500 mẫu, trước khi "
  "đưa vào công thức. Số gia tốc thì không trừ độ lệch, nó chỉ cộng số bù 92.")

p("Cảnh báo về bảng này: ánh xạ trên đúng với cách cảm biến được hàn trên bo mẫu. Nếu bạn lắp cảm "
  "biến xoay đi một phần tư vòng thì trục nghiêng và trục xoay đổi chỗ nhau, và robot sẽ không đứng "
  "được dù mọi con số khác đều đúng. Bài 1 ở mục 4.3 là cách kiểm: nghiêng robot về trước mà còi "
  "không đổi nhịp thì bạn đang đọc sai trục, chứ không phải sai dấu. Sai dấu thì còi vẫn đổi nhịp "
  "nhưng đổi ngược.", bold=True)

doc.add_heading("3.3. Bảng tham số đã chạy được", level=2)

p("Đây là bảng quan trọng nhất của toàn bộ tài liệu. Robot đứng được với đúng những con số này. "
  "Năm lần thử trước đó dùng con số khác và đều đổ.", bold=True)

table(
    "Bảng 3.3 — Toàn bộ tham số của bản đã chạy",
    ["Tham số", "Giá trị", "Dùng ở đâu và nghĩa là gì"],
    [
        ["Số bù gia tốc", "92", "Cộng vào giá trị gia tốc trục trước sau. Đây là độ lệch cơ khí của bo. "
         "Lấy sai số này thì điểm cân bằng lệch và robot vọt qua rồi đổ"],
        ["Cách áp số bù", "phép cộng", "Cộng chứ không trừ. Dấu sai thì độ lệch thành hai lần"],
        ["Khoảng kẹp gia tốc", "-8200 đến 8200", "Giá trị ứng với một g ở thang đo cộng trừ 4 g"],
        ["Đổi radian sang độ", "57,29578", "Nhân vào kết quả của hàm asin"],
        ["Hệ số cộng dồn tốc độ góc", "0,000031", "Nhân với tốc độ góc trục nghiêng rồi cộng vào góc chạy"],
        ["Hệ số bù khi xoay", "0,0000003", "Nhân với tốc độ góc trục xoay rồi trừ khỏi góc chạy. "
         "Thiếu dòng này thì robot vừa đứng vừa trôi dần sang một bên"],
        ["Trọng số trộn góc", "0,9996 và 0,0004", "Lấy 0,9996 phần góc chạy cộng 0,0004 phần góc gia tốc"],
        ["Hệ số tỉ lệ", "12,0", "Hệ số của phần đáp theo sai số hiện tại"],
        ["Hệ số cộng dồn", "0,4", "Hệ số của phần đáp theo sai số đã dồn lại"],
        ["Hệ số vi phân", "10,0", "Hệ số của phần đáp theo mức thay đổi của sai số"],
        ["Ngưỡng bật phần hãm", "10,0", "Khi đầu ra vượt quá mức này thì cộng thêm phần hãm vào sai số"],
        ["Hệ số hãm", "0,015", "Nhân với đầu ra lần trước rồi cộng vào sai số, để đỡ vọt lố"],
        ["Kẹp phần cộng dồn", "-400 đến 400", "Chặn phần cộng dồn phình to khi bánh bị kẹt"],
        ["Kẹp đầu ra", "-400 đến 400", "Giới hạn cuối của đầu ra điều khiển"],
        ["Vùng chết", "-5 đến 5", "Đầu ra nằm trong khoảng này thì cho về 0, để robot khỏi rung tại chỗ"],
        ["Bước tự học điểm cân bằng", "0,002", "Mỗi vòng dịch điểm cân bằng 0,002 độ về phía ngược với "
         "dấu đầu ra. Đây là cách robot tự tìm điểm đứng thật của nó"],
        ["Khoảng bật giữ cân bằng", "-0,5 đến 0,5 độ", "Góc nghiêng vào khoảng này thì tự chuyển sang giữ cân bằng"],
        ["Ngưỡng coi là đã đổ", "30 độ", "Vượt quá thì ngắt xung bước ngay"],
        ["Ngưỡng pin yếu", "420", "Số đọc từ chân A0 thấp hơn mức này thì không cho chạy"],
        ["Nhịp đo pin", "500 ms", "Khoảng cách giữa hai lần đo"],
        ["Chiều tiến bánh trái", "mức thấp ở chân D6", "Giá trị xung lớn hơn hoặc bằng 0 thì chân D6 ở mức thấp"],
        ["Chiều tiến bánh phải", "mức cao ở chân D4", "Giá trị xung lớn hơn hoặc bằng 0 thì chân D4 ở mức cao"],
        ["Số mẫu đo độ lệch", "500", "Số mẫu lấy khi robot nằm yên"],
        ["Giãn cách giữa hai mẫu", "3 ms", "Nên 500 mẫu mất khoảng 1,5 giây"],
        ["Hệ số đổi tốc độ góc", "131", "Số đơn vị đọc được cho mỗi độ trên giây"],
        ["Hệ số đổi gia tốc", "8192", "Số đơn vị đọc được cho mỗi g ở thang cộng trừ 4 g"],
        ["Chu kỳ vòng tính", "4 ms", "Tức 250 lần mỗi giây"],
        ["Hệ số bộ trộn", "0,9996", "Truyền vào hàm đặt bộ trộn ban đầu, cùng chu kỳ 0,004 giây"],
    ],
    widths=[4.0, 3.2, 8.8],
)

p("Hai dòng cần nhấn mạnh thêm, vì đây là hai chỗ đã làm robot đổ năm lần:", bold=True)

bullet("Số bù gia tốc phải là 92 và phải cộng. Trước đó bản mã dùng 535, tức điểm cân bằng lệch "
       "3,1 độ. Robot đuổi theo một thế đứng mà nó không giữ được, nên nó vọt qua rồi đổ. Nhìn bên "
       "ngoài thì giống như hệ số tỉ lệ quá lớn, nên rất dễ đi sai hướng khi tìm lỗi.",
       bold_head="Số bù gia tốc: ")
bullet("Chân D6 của bánh trái tiến ở mức thấp, chân D4 của bánh phải tiến ở mức cao. Hai chân ngược "
       "nhau vì hai động cơ lắp đối xứng. Đặt cùng mức cho cả hai thì robot xoay tại chỗ thay vì "
       "tiến lùi.", bold_head="Chiều hai bánh ngược nhau: ")

doc.add_heading("3.4. Bảng thanh ghi phải đặt", level=2)

table(
    "Bảng 3.4 — Giá trị thanh ghi",
    ["Khối", "Thanh ghi", "Giá trị", "Kết quả"],
    [
        ["Bộ đếm Timer0", "TCCR0A", "bật bit WGM01", "Chạy ở chế độ đếm tới rồi xoá"],
        ["", "TCCR0B", "bật bit CS01 và CS00", "Chia nhịp cho 64"],
        ["", "OCR0A", "249", "Ngắt mỗi 1 ms"],
        ["", "TIMSK0", "bật bit OCIE0A", "Mở ngắt so sánh"],
        ["Bộ đếm Timer2", "TCCR2A", "bật bit WGM21", "Chạy ở chế độ đếm tới rồi xoá"],
        ["", "TCCR2B", "bật bit CS21", "Chia nhịp cho 8"],
        ["", "OCR2A", "39", "Ngắt 50 000 lần mỗi giây"],
        ["", "TIMSK2", "bật bit OCIE2A", "Mở ngắt so sánh"],
        ["Đường I2C", "TWSR", "0x00", "Không chia thêm nhịp"],
        ["", "TWBR", "12", "Nhịp đường truyền 400 kHz"],
        ["", "TWCR", "bật bit TWEN", "Bật khối I2C"],
        ["Cổng nối tiếp", "UBRR0H và UBRR0L", "0 và 103", "Tốc độ 9 600 baud"],
        ["", "UCSR0C", "bật bit UCSZ01 và UCSZ00", "Khung 8 bit dữ liệu, 1 bit dừng, không kiểm chẵn lẻ"],
        ["", "UCSR0B", "bật bit RXEN0 và TXEN0", "Bật cả gửi và nhận"],
        ["Đổi tương tự sang số", "ADMUX", "bật bit REFS0, chọn kênh 0", "Lấy mốc điện áp trong chip, đọc chân A0"],
        ["", "ADCSRA", "bật ADEN, ADSC, ADPS2, ADPS1, ADPS0", "Bật khối, bắt đầu đọc, chia nhịp cho 128"],
        ["Cảm biến góc", "0x6B", "0x00", "Đánh thức cảm biến"],
        ["", "0x1A", "0x03", "Bật bộ lọc trong cảm biến"],
        ["", "0x1B", "0x00", "Thang đo tốc độ góc nhỏ nhất"],
        ["", "0x1C", "0x08", "Thang đo gia tốc cộng trừ 4 g"],
        ["", "0x75", "chỉ đọc", "Phải đọc ra 0x68 hoặc 0x72, khác thì coi là lỗi cảm biến"],
    ],
    widths=[3.4, 4.0, 4.4, 4.2],
    mono_cols=(1, 2),
)

rich([("Sau khi ghi 0x08 vào thanh ghi 0x1C, hãy ", ""), ("đọc lại thanh ghi đó", "b"),
      (" và kiểm tra hai bit thang đo đúng bằng 0x08. Bước đọc lại này bắt buộc. Có loại cảm biến "
       "nhận lệnh ghi mà không đổi thang đo, và nếu không đọc lại thì bạn tin là đã đặt xong trong "
       "khi thang đo vẫn là mức cũ, dẫn tới góc sai gấp đôi.", "")])

doc.add_heading("3.5. Đặt đường I2C: chín xung giải phóng", level=2)

p("Trước khi bật khối I2C của chip, phải phát chín xung nhịp bằng cách bật tắt chân trực tiếp. Lý "
  "do: nếu lần trước chương trình bị khởi động lại giữa lúc đang đọc cảm biến, cảm biến còn đang "
  "giữ đường dữ liệu ở mức thấp và sẽ không nhả ra. Chín xung làm cảm biến gửi hết byte đang dở rồi "
  "nhả đường. Thiếu bước này thì cứ vài lần khởi động lại sẽ có một lần không đọc được cảm biến.")

code([
    "ha hai chan A4 va A5 ve muc thap trong thanh ghi cong",
    "dat chan A4 lam chan vao  (nha duong du lieu)",
    "lap 9 lan:",
    "    dat chan A5 lam chan ra   -> keo nhip xuong",
    "    cho khoang 10 vong lap rong",
    "    dat chan A5 lam chan vao  -> nha nhip len",
    "    cho khoang 10 vong lap rong",
    "tao mot dieu kien dung bang tay tren chan A4",
    "sau do moi ghi TWSR = 0, TWBR = 12, TWCR = bat TWEN",
])

doc.add_heading("3.6. Hàm ngắt 50 kHz", level=2)

p("Đây là phần khó nhất của cả bài. Đọc kỹ sáu điều kiện dưới đây rồi mới viết.")

table(
    "Bảng 3.5 — Sáu điều kiện của hàm ngắt phát xung",
    ["Số", "Điều kiện", "Vì sao"],
    [
        ["1", "Đọc thanh ghi cổng vào một biến tạm ở đầu hàm, sửa biến tạm, rồi ghi ra cổng đúng một "
         "lần ở cuối hàm",
         "Ghi nhiều lần sẽ làm chân nhảy mức giữa hàm, sinh xung giả"],
        ["2", "Hạ hai chân xung xuống mức thấp ngay ở đầu hàm",
         "Xung được dựng lên ở lần ngắt trước, hạ ở lần này, nên xung rộng đúng 20 micro giây"],
        ["3", "Tăng bộ đếm rồi so sánh theo kiểu lớn hơn hẳn giá trị xung, không phải lớn hơn hoặc bằng",
         "Dùng lớn hơn hoặc bằng thì chu kỳ bị ngắn đi một nhịp và tốc độ sai"],
        ["4", "Giá trị xung bằng 0 thì xử lý riêng là đứng im, đặt bộ đếm về 0",
         "Không xử lý riêng thì giá trị 0 sẽ cho tốc độ cao nhất thay vì đứng im"],
        ["5", "Chốt chiều quay và độ lớn cùng một lúc, tại đúng lúc nạp lại bộ đếm",
         "Chốt lệch nhau thì có lần ngắt phát xung theo độ lớn mới nhưng chiều cũ"],
        ["6", "Khi cờ cho phép chạy đang tắt thì đặt mọi biến đếm về 0 rồi ra khỏi hàm",
         "Để lần bật lại bắt đầu từ trạng thái sạch, không còn số cũ"],
    ],
    widths=[1.2, 6.6, 8.2],
)

p("Mã giả của hàm, viết cho một bánh. Bánh còn lại làm giống hệt với bộ biến riêng:")

code([
    "bien tam = doc thanh ghi cong",
    "bien tam &= xoa hai bit chan xung           # dieu kien 2",
    "",
    "neu chieu hien tai cua banh = 1:  bat bit chan chieu",
    "nguoc lai:                        xoa bit chan chieu",
    "",
    "neu co cho phep chay dang tat:               # dieu kien 6",
    "    bo dem = 0 ; do lon dang chay = 0",
    "    ghi bien tam ra cong ; ra khoi ham",
    "",
    "neu gia tri xung dich = 0:                   # dieu kien 4",
    "    bo dem = 0 ; do lon dang chay = 0",
    "nguoc lai:",
    "    neu do lon dang chay = 0:",
    "        do lon dang chay = tri tuyet doi cua gia tri xung dich",
    "        chieu hien tai  = chieu suy ra tu dau cua gia tri xung dich",
    "        bo dem = 0",
    "    bo dem = bo dem + 1",
    "    neu bo dem > do lon dang chay:            # dieu kien 3",
    "        bat bit chan xung trong bien tam",
    "        bo dem = 0",
    "        do lon dang chay = tri tuyet doi cua gia tri xung dich   # dieu kien 5",
    "        chieu hien tai  = chieu suy ra tu dau cua gia tri xung dich",
    "",
    "ghi bien tam ra cong                          # dieu kien 1, dung mot lan",
])

p("Cả hàm chỉ có phép cộng, phép so sánh, phép gán và phép toán trên bit. Không có phép chia, không "
  "có số thực, không gọi hàm nào khác. Mục 4.4 cho bạn cách tự kiểm điều này trên tệp đã dịch.")

doc.add_heading("3.7. Đổi đầu ra điều khiển sang giá trị xung", level=2)

p("Đầu ra của bộ điều khiển là một số trong khoảng trừ 400 đến 400. Giá trị xung mà hàm ngắt cần "
  "lại có nghĩa ngược: số càng nhỏ thì bánh càng nhanh, vì nó là số lần ngắt phải chờ giữa hai xung. "
  "Công thức đổi như sau:")

code([
    "neu dau ra > 0:",
    "    trung gian  = 405,0 - (5500,0 / (dau ra + 9,0))",
    "    gia tri xung = (so nguyen)(400,0 - trung gian)",
    "nguoc lai neu dau ra < 0:",
    "    trung gian  = -405,0 - (5500,0 / (dau ra - 9,0))",
    "    gia tri xung = (so nguyen)(-400,0 - trung gian)",
    "nguoc lai:",
    "    gia tri xung = 0",
])

p("Công thức này không thẳng. Nó cho bước đi rất nhỏ khi robot gần thẳng đứng, và bước lớn khi robot "
  "nghiêng nhiều. Nhờ vậy robot vừa đứng êm lúc yên, vừa đủ sức kéo lại lúc bị đẩy. Đừng thay bằng "
  "phép nhân thẳng, robot sẽ rung liên tục quanh điểm cân bằng.")

p("Hai phép chia trong công thức này nằm ở tầng 2 chạy 4 ms một lần, không nằm trong hàm ngắt 50 kHz, "
  "nên không vi phạm Cấm 1.", italic=True)

doc.add_heading("3.8. Bộ điều khiển và phần tự học điểm cân bằng", level=2)

code([
    "sai so = goc - diem can bang tu hoc - diem dat",
    "",
    "neu dau ra lan truoc > 10 hoac < -10:",
    "    sai so = sai so + dau ra lan truoc x 0,015",
    "",
    "phan don = phan don + 0,4 x sai so",
    "kep phan don trong khoang -400 .. 400",
    "",
    "dau ra = 12,0 x sai so + phan don + 10,0 x (sai so - sai so lan truoc)",
    "kep dau ra trong khoang -400 .. 400",
    "",
    "sai so lan truoc = sai so",
    "",
    "neu dau ra trong khoang -5 .. 5:  dau ra = 0",
    "",
    "neu diem dat = 0:",
    "    neu dau ra < 0:  diem can bang tu hoc = diem can bang tu hoc + 0,002",
    "    neu dau ra > 0:  diem can bang tu hoc = diem can bang tu hoc - 0,002",
    "",
    "neu khong duoc chay, hoac goc > 30, hoac goc < -30:",
    "    dau ra = 0 ; phan don = 0 ; diem can bang tu hoc = 0",
])

p("Phần tự học điểm cân bằng là chỗ dễ bỏ sót nhất. Điểm đứng thật của robot không bao giờ đúng 0 độ, "
  "vì trọng tâm lệch và cảm biến lắp lệch. Nếu không có bốn dòng tự học đó, robot sẽ đứng được vài "
  "giây rồi trôi dần về một phía cho tới khi hết đường rồi đổ. Bước dịch 0,002 độ mỗi vòng, tức "
  "khoảng nửa độ mỗi giây, đủ nhanh để bắt kịp và đủ chậm để không làm rung.")

rich([("Phần vi phân tính theo mức thay đổi của ", ""), ("sai số", "b"),
      (", không phải theo mức thay đổi của góc. Hai cách này khác nhau khi điểm cân bằng tự học đang "
       "dịch, và dùng sai cách thì robot rung mạnh.", "")])

doc.add_heading("3.9. Hai việc phải cấm ngắt khi làm", level=2)

p("Biến chứa giá trị xung rộng 16 bit, mà chip này xử lý 8 bit một lần. Tầng 2 ghi biến đó, tầng 1 "
  "đọc biến đó. Nếu hàm ngắt chen vào đúng giữa lúc tầng 2 mới ghi xong một nửa, tầng 1 sẽ đọc được "
  "một số lai giữa giá trị cũ và giá trị mới, và bánh xe sẽ giật một cái rất mạnh.")

bullet("Mọi lần ghi và đọc biến giá trị xung đều phải bọc trong một khối cấm ngắt rồi trả lại trạng "
       "thái ngắt như trước.")
bullet("Hàm đọc số đếm thời gian theo ms cũng vậy, vì số đó rộng 32 bit.")

p("Khối cấm ngắt này rất ngắn, chỉ vài lệnh, nên không ảnh hưởng tới hạn của hàm ngắt.")

doc.add_heading("3.10. Gửi chữ ra cổng nối tiếp mà không chặn chương trình", level=2)

p("Ở 9 600 baud, một ký tự chiếm 10 bit nên mất khoảng 1 ms. Một dòng 60 ký tự mất khoảng 62 ms, dài "
  "hơn 15 lần chu kỳ vòng tính 4 ms. Nên không được chờ gửi xong.")

bullet("Dùng một vùng đệm vòng 128 byte. Hàm gửi chỉ đổ chữ vào đệm rồi quay ra ngay.")
bullet("Một hàm ngắt riêng của cổng nối tiếp lấy từng byte trong đệm ra gửi. Đệm hết thì tắt ngắt đó "
       "để khỏi ngắt liên tục không có việc.")
bullet("Đệm đầy thì bỏ cả dòng và tăng một biến đếm số dòng bị bỏ. Đếm số dòng bị bỏ quan trọng: nếu "
       "số đó tăng thì bạn biết mình đang in quá nhiều, chứ không ngồi đoán vì sao thiếu dòng.")
bullet("Mỗi 100 ms gửi một dòng gồm: tên trạng thái, góc nghiêng, giá trị gia tốc thô, giá trị xung "
       "hai bánh, số lần vòng tính bị quá hạn, và số dòng đã bị bỏ.")

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ================================================================= CHƯƠNG 4
doc.add_heading("Chương 4 — Kiểm thử", level=1)

p("Chương này cho bạn cách chứng minh phần mềm mình viết là đúng. Nguyên tắc chung: một phép đo mà "
  "báo đạt bất kể sản phẩm đúng hay sai thì nó không đo gì cả. Nên mỗi bài kiểm dưới đây đều kèm "
  "cách tự thử xem bài kiểm có thật sự biết phát hiện lỗi hay không.", bold=True)

doc.add_heading("4.1. Kiểm trên máy tính trước khi nạp bo", level=2)

p("Viết hai chương trình thử chạy trên máy tính. Điều kiện bắt buộc: hai chương trình đó phải "
  "nạp thẳng tệp mã sản phẩm vào, không được chép lại logic sang tệp kiểm.")

rich([("Lý do điều kiện này tồn tại: trong lần làm đầu, ba bài kiểm liên tiếp đã chép logic sang tệp "
       "kiểm rồi so logic với chính nó. Cả ba đều báo đạt, kể cả khi mã sản phẩm bị phá hỏng. Cách "
       "làm đúng là trong tệp kiểm dùng ", ""), ("#include \"../firmware/fsm.c\"", "c"),
      (" và dựng vài biến giả thay cho thanh ghi phần cứng.", "")])

table(
    "Bảng 4.1 — Hai bài kiểm trên máy",
    ["Bài", "Kiểm cái gì", "Đạt nghĩa là"],
    [
        ["Đối chiếu tham số",
         "Nạp mã sản phẩm của phần phát xung và phần trạng thái, cho chạy với số đo giả",
         "Các bit chân cổng và góc tính ra khớp đúng với bản mẫu đã chạy được"],
        ["Đo số bù",
         "Nạp mã sản phẩm của phần trạng thái, giả lập 500 mẫu gia tốc",
         "Số trung bình in ra đúng bằng số trung bình của dãy mẫu đưa vào"],
    ],
    widths=[3.4, 6.2, 6.4],
)

doc.add_heading("4.2. Thử xem bài kiểm có biết báo lỗi không", level=2)

p("Sau khi hai bài kiểm báo đạt, hãy cố tình phá mã sản phẩm bốn lần rồi chạy lại. Bài kiểm phải "
  "báo lỗi cả bốn lần. Nếu có lần nào nó vẫn báo đạt thì bài kiểm đó vô dụng, phải viết lại.")

table(
    "Bảng 4.2 — Bốn phép phá bắt buộc",
    ["Phá gì", "Đổi thành", "Bài kiểm phải báo lỗi ở đâu"],
    [
        ["Số bù gia tốc 92", "535", "Góc tính ra lệch khoảng 3,1 độ so với bản mẫu"],
        ["Chiều tiến bánh trái", "đổi từ mức thấp sang mức cao", "Bit chân D6 khác bản mẫu"],
        ["Chiều tiến bánh phải", "đổi từ mức cao sang mức thấp", "Bit chân D4 khác bản mẫu"],
        ["Dấu khi áp số bù", "đổi phép cộng thành phép trừ", "Góc tính ra lệch gấp đôi"],
    ],
    widths=[4.0, 5.0, 7.0],
)

p("Nhớ khôi phục lại mã sau khi thử xong. Hãy ghi lại cả bốn lần phá và bốn lần khôi phục, để sau "
  "này có người hỏi thì chỉ ra được là bài kiểm đã từng báo lỗi đúng lúc.")

doc.add_heading("4.3. Ba bài đo trên bo để tách ba dấu", level=2)

p("Mục 1.5 đã nói: ba dấu của vòng điều khiển khi robot đứng yên thì nhân lại thành một dấu, nên "
  "không tách được bằng cách đọc mã. Ba bài đo dưới đây tách từng dấu ra.")

p("Cách vào chế độ tự kiểm: giữ nút D12 trong lúc bật nguồn, rồi nhả nút ra trong vòng dưới 2 giây. "
  "Nhả muộn hơn 2 giây thì robot vào chế độ đo số bù của Bài 3 chứ không vào chế độ kiểm dấu. Sau khi "
  "nhả, robot lấy 500 mẫu rồi vào chế độ kiểm dấu góc, kèm một tiếng còi 200 ms.", bold=True)

doc.add_heading("Bài 1 — Dấu của cảm biến góc", level=3)

p("Sau khi lấy xong 500 mẫu, robot vào chế độ kiểm dấu góc. Động cơ không chạy. Còi kêu theo chiều "
  "nghiêng:")

table(
    "Bảng 4.3 — Còi trong bài kiểm dấu góc",
    ["Bạn nghiêng robot", "Còi phải kêu", "Nếu kêu ngược"],
    [
        ["Giữ thẳng, lệch dưới 2 độ", "Im lặng", "—"],
        ["Nghiêng về trước, từ 3 độ trở lên", "Bíp chậm, chu kỳ 600 ms", "Dấu cảm biến bị ngược"],
        ["Nghiêng về sau, từ 3 độ trở lên", "Bíp nhanh, chu kỳ 200 ms", "Dấu cảm biến bị ngược"],
    ],
    widths=[5.0, 5.0, 6.0],
)

p("Nếu kêu ngược thì chỉ cần đảo dấu ở một chỗ duy nhất: dấu của giá trị gia tốc trục trước sau. "
  "Đừng đảo dấu ở nhiều chỗ, sẽ rất khó lần lại.")

doc.add_heading("Bài 2 — Chiều quay của hai bánh", level=3)

p("Ở chế độ kiểm dấu góc, bấm nhả nút một lần. Còi kêu 600 ms và hai bánh chạy tới trong 3 giây ở "
  "tốc độ chậm, rồi tự dừng và kêu 200 ms.")

bullet("Hãy nhấc robot lên cho bánh không chạm sàn, và nhìn chiều quay của hai bánh.")
bullet("Cả hai bánh phải quay theo cùng một chiều, là chiều làm robot tiến về trước.")
bullet("Nếu một bánh quay ngược bánh kia thì sửa mức chân chiều của riêng bánh đó trong tệp số liệu. "
       "Đừng đảo dây động cơ, vì sau này nhìn mã sẽ không hiểu vì sao.")
bullet("Nếu cả hai bánh cùng quay ngược thì đảo cả hai mức chân chiều.")

doc.add_heading("Bài 3 — Số bù của điểm cân bằng", level=3)

p("Đặt robot đứng đúng thế mà bạn muốn nó giữ. Giữ cho thật yên. Ở trạng thái dừng, giữ nút D12 từ "
  "2 giây trở lên. Còi kêu 200 ms, cổng nối tiếp in ra một dòng báo đang đo. Giữ yên robot thêm "
  "khoảng 2 giây. Còi kêu dài 500 ms và cổng nối tiếp in ra số trung bình của 500 mẫu.")

p("Lấy số đó, đổi dấu, rồi đặt vào chỗ số bù gia tốc. Nếu số in ra là trừ 92 thì số bù là 92.")

doc.add_heading("4.4. Hai bài đo trên tệp đã dịch", level=2)

p("Hai bài này kiểm điều kiện của hàm ngắt. Chúng đọc tệp đã dịch, không tin vào mã nguồn.")

table(
    "Bảng 4.4 — Kiểm trên tệp đã dịch",
    ["Bài", "Lệnh", "Phải thấy gì"],
    [
        ["Kiểm điều kiện của hàm ngắt",
         "avr-objdump -d mach.elf, rồi tìm phần của hàm phát xung",
         "Không có lệnh gọi hàm, không có lệnh chia, không có tên hàm số thực nào"],
        ["Kiểm bộ nhớ",
         "avr-size -A mach.elf",
         "Đoạn mã cộng đoạn dữ liệu không vượt 32 768 byte. Đoạn dữ liệu cộng đoạn dữ liệu trống "
         "không vượt 2 048 byte"],
    ],
    widths=[4.0, 5.4, 6.6],
    mono_cols=(1,),
)

rich([("Lưu ý khi đọc kết quả của lệnh đo bộ nhớ: bộ nhớ chương trình dùng hết bằng ", ""),
      (".text", "c"), (" cộng ", ""), (".data", "c"),
      (", và bộ nhớ chạy dùng hết bằng ", ""), (".data", "c"), (" cộng ", ""), (".bss", "c"),
      (". Lấy riêng một đoạn thì ra số nhỏ hơn thực tế, và bạn sẽ tưởng còn nhiều chỗ trống trong "
       "khi không còn.", "")])

doc.add_heading("4.5. Nạp chương trình vào bo", level=2)

table(
    "Bảng 4.5 — Các bước nạp",
    ["Bước", "Làm gì", "Lưu ý"],
    [
        ["1", "Rút giắc nguồn động cơ", "Cắm cáp nạp khi còn nguồn động cơ có thể làm hỏng cổng máy tính"],
        ["2", "Cắm cáp nạp từ máy tính vào bo", "Đèn nguồn 5 V trên bo phải sáng liên tục"],
        ["3", "Nạp tệp đã dịch bằng công cụ nạp", "Xem mục bên dưới"],
        ["4", "Đọc ngược tệp trên chip rồi so với tệp vừa nạp", "Phải báo 0 byte lệch"],
        ["5", "Mở màn hình xem cổng nối tiếp ở 9 600 baud", "Phải thấy dòng số đo chạy mỗi 100 ms"],
        ["6", "Rút cáp nạp, cắm lại nguồn động cơ", "Lần thử đầu nên đặt giới hạn dòng 1,5 A"],
    ],
    widths=[1.3, 6.0, 8.7],
)

p("Một chỗ rất dễ sai ở bước 4. Công cụ nạp so tệp trên chip với đúng cái tệp bạn đưa cho nó. Nếu "
  "bạn đưa sai tệp thì nó vẫn báo 0 byte lệch, và bạn tưởng đã nạp đúng. Trong lần làm đầu đã xảy "
  "ra đúng chuyện này. Cách tránh: sau khi nạp, mở cổng nối tiếp đọc dòng nhận dạng mà chương trình "
  "in ra, xem có đúng bản mình vừa dịch không.", bold=True)

doc.add_heading("4.6. Trình tự bật nguồn và những gì phải thấy", level=2)

table(
    "Bảng 4.6 — Năm bước vận hành",
    ["Bước", "Bạn làm gì", "Phải thấy và nghe gì"],
    [
        ["1", "Đặt robot nằm yên trên mặt phẳng rồi bật nguồn. Không cầm trên tay, không rung lắc",
         "Một tiếng còi 100 ms, rồi im lặng. Robot đang dừng và chờ lệnh"],
        ["2", "Bấm rồi nhả nút D12 một lần, nhanh dưới 2 giây. Vẫn giữ robot nằm yên",
         "Một tiếng 100 ms, rồi các tiếng 100 ms lặp mỗi 500 ms trong lúc lấy 500 mẫu"],
        ["3", "Chờ khoảng 1,5 đến 2 giây, vẫn giữ robot yên",
         "Một tiếng 100 ms rồi 150 ms sau thêm một tiếng nữa. Robot đã sẵn sàng"],
        ["4", "Dùng tay dựng robot đứng thẳng dần lên",
         "Khi góc đi qua khoảng cộng trừ 0,5 độ, hai bánh bắt đầu chạy tới lui để giữ thân. Buông nhẹ tay"],
        ["5", "Muốn dừng thì bấm nút D12 một lần",
         "Bánh ngừng ngay, còi kêu 100 ms"],
    ],
    widths=[1.3, 6.4, 8.3],
)

p("Bước 2 là bước dễ bỏ sót nhất. Robot không tự đo cảm biến khi bật nguồn, phải có người bấm nút. "
  "Nếu bạn bật nguồn rồi ngồi chờ thì sẽ không bao giờ thấy tiếng báo sẵn sàng, và dễ tưởng là mã sai.",
  bold=True)

p("Trong lúc lấy 500 mẫu ở bước 2 và bước 3, nếu robot bị rung lắc thì giá trị độ lệch đo được sẽ "
  "sai, và góc nghiêng sẽ trôi liên tục. Robot vẫn chạy, vẫn kêu còi đúng, nhưng không bao giờ đứng "
  "được. Đây là lỗi thao tác, không phải lỗi mã, và rất dễ bị hiểu lầm thành lỗi mã.", bold=True)

doc.add_heading("4.7. Dấu hiệu sai và chỗ cần xem", level=2)

table(
    "Bảng 4.7 — Tra lỗi theo hiện tượng",
    ["Bạn thấy gì", "Nguyên nhân thường gặp", "Xem lại chỗ nào"],
    [
        ["Bật nguồn mà không có tiếng còi nào",
         "Chương trình không chạy, hoặc nạp sai tệp, hoặc chân còi đặt sai hướng",
         "Mục 4.5 bước 4 và 5. Đọc dòng nhận dạng trên cổng nối tiếp"],
        ["Bật nguồn, kêu một tiếng rồi im, chờ mãi không thấy gì nữa",
         "Đây là đúng. Robot đang chờ người bấm nút",
         "Bảng 4.6 bước 2. Bấm rồi nhả nút D12"],
        ["Bấm nút rồi mà mãi không tới tiếng báo sẵn sàng",
         "Không đọc được cảm biến góc",
         "Dây ở chân A4 và A5. Điện cấp cho cảm biến. Mục 3.5 về chín xung giải phóng"],
        ["Còi kêu ba tiếng liên tục không ngừng",
         "Mã đã nhận ra lỗi cảm biến. Đây là báo đúng",
         "Đọc dòng lỗi in ra cổng nối tiếp, nó ghi rõ hỏng ở bước nào"],
        ["Dựng lên thì hai bánh phóng mạnh về một phía rồi đổ ngay",
         "Vòng điều khiển bị ngược dấu, thành đẩy thay vì kéo lại",
         "Làm Bài 1 và Bài 2 ở mục 4.3. Đừng sửa hệ số điều khiển"],
        ["Dựng lên thì bánh chạy rất mạnh, vọt qua điểm cân bằng rồi đổ",
         "Số bù gia tốc sai, nên robot đuổi theo một thế đứng không giữ được",
         "Làm Bài 3 ở mục 4.3 để đo lại số bù. Đây đúng là lỗi đã gặp với số 535"],
        ["Đứng được nhưng rung giật biên độ lớn, càng rung càng mạnh",
         "Hệ số tỉ lệ hoặc hệ số vi phân quá lớn, hoặc rung động cơ truyền vào cảm biến",
         "Lót cao su dưới cảm biến trước. Chỉ hạ hệ số sau khi đã làm xong ba bài ở mục 4.3"],
        ["Đứng được vài giây rồi trôi dần sang một phía tới khi đổ",
         "Thiếu phần tự học điểm cân bằng, hoặc thiếu dòng bù khi xoay",
         "Mục 3.8 bốn dòng tự học, và dòng bù 0,0000003 ở mục 2.2"],
        ["Hai bánh xoay tại chỗ thay vì tiến lùi",
         "Hai chân chiều đặt cùng mức, trong khi hai động cơ lắp đối xứng",
         "Bảng 3.3, hai dòng về chiều tiến của hai bánh"],
        ["Đang chạy thì bánh thỉnh thoảng giật một cái rất mạnh",
         "Đọc biến 16 bit mà không cấm ngắt, nên đọc được số lai",
         "Mục 3.9"],
        ["Số đếm số lần vòng tính quá hạn tăng dần",
         "Có đoạn mã chặn CPU, hoặc in ra cổng nối tiếp quá nhiều",
         "Cấm 2 ở mục 1.4. Xem cả số dòng bị bỏ ở mục 3.9"],
        ["Bánh đột ngột ngừng, còi kêu ba tiếng dồn dập",
         "Robot đã đổ quá 30 độ, hoặc pin đã yếu",
         "Đây là báo đúng. Dựng lại, bấm nút xác nhận. Nếu pin yếu thì sạc pin"],
        ["Để bánh quay trên không thì tốc độ tăng dần tới mức cao nhất",
         "Không có phản lực sàn nên phần cộng dồn phình to",
         "Đây là chuyện bình thường, không phải lỗi. Luôn thử với bánh chạm sàn"],
    ],
    widths=[5.0, 5.2, 5.8],
)

doc.add_heading("4.8. Nghiệm thu", level=2)

p("Phần mềm coi là xong khi làm được đủ chín điều sau, và mỗi điều đều có số đo kèm theo chứ không "
  "phải lời nói:")

for i, item in enumerate([
    "Hai bài kiểm trên máy báo đạt, và đã phá bốn lần thì báo lỗi cả bốn lần.",
    "Tệp đã dịch cho thấy hàm ngắt không có lệnh gọi hàm, không có phép chia, không có số thực.",
    "Bộ nhớ chương trình và bộ nhớ chạy đều dưới mức cho phép, tính đủ cả hai đoạn như ở mục 4.4.",
    "Nạp vào chip rồi đọc ngược lại, báo 0 byte lệch, và dòng nhận dạng trên cổng nối tiếp đúng bản vừa dịch.",
    "Trình tự tiếng còi nghe đúng Bảng 2.4 ở cả bốn bước của Bảng 4.6.",
    "Ba bài đo ở mục 4.3 đều cho kết quả đúng chiều.",
    "Robot đứng liên tục ít nhất 30 giây mà không cần người chạm vào.",
    "Đẩy nhẹ vào thân robot thì nó lấy lại thế đứng, không đổ.",
    "Nghiêng robot quá 30 độ thì bánh ngừng trong vòng 4 ms và còi báo đã đổ.",
]):
    numbered(item)

p("Điều cuối cùng, và là điều dễ bỏ qua nhất: khi bạn báo xong, hãy nói rõ mình đã đo cái gì để biết "
  "là xong. Câu chương trình chạy được chỉ nói rằng lệnh đã thực hiện, nó không nói kết quả có đúng "
  "hay không.", bold=True)

doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

# ================================================================= PHỤ LỤC
doc.add_heading("Phụ lục — Chỗ tra lại số liệu", level=1)

p("Mọi con số trong tài liệu này lấy từ mã nguồn của bản đã chạy đứng được. Bảng dưới đây cho biết "
  "chỗ tra lại từng nhóm số.")

table(
    "Bảng P.1 — Chỗ tra lại",
    ["Nhóm số liệu", "Tệp", "Dòng"],
    [
        ["Số bù gia tốc, chiều hai bánh, khoảng bật cân bằng, ngưỡng đổ, ngưỡng pin", "firmware/config.h", "72, 73, 81, 82, 83, 87"],
        ["Hệ số điều khiển, hãm, kẹp, vùng chết, bước tự học", "firmware/pid.c", "4, 5, 6, 30, 31, 36, 37, 45, 46, 51, 57, 58"],
        ["Cách tính góc, trộn hai nguồn, bù khi xoay", "firmware/fsm.c", "366, 367, 368, 370, 380, 381, 382"],
        ["Tám trạng thái và các lần đổi trạng thái", "firmware/fsm.c", "119 đến 431"],
        ["Hàm phát xung và sáu điều kiện", "firmware/motor.c", "113 đến 203"],
        ["Công thức đổi đầu ra sang giá trị xung", "firmware/motor.c", "55 đến 64"],
        ["Thanh ghi hai bộ đếm và hai hàm ngắt", "firmware/timer.c", "13 đến 49"],
        ["Chín xung giải phóng và thanh ghi đường I2C", "firmware/i2c.c", "5 đến 28"],
        ["Thanh ghi cảm biến và bước đọc lại để kiểm", "firmware/mpu6050.c", "31 đến 84"],
        ["Thanh ghi cổng nối tiếp và vùng đệm vòng", "firmware/uart.c", "19 đến 48"],
        ["Hai bài kiểm nạp thẳng mã sản phẩm", "sim/test_v1_sync.c, sim/test_offset.c", "—"],
    ],
    widths=[6.6, 5.4, 4.0],
    mono_cols=(1,),
)

doc.add_heading("Những chỗ tài liệu cũ ghi khác mã đã chạy", level=2)

p("Trong lúc dựng tài liệu này, có một bản hướng dẫn cũ trong kho ghi khác với mã đã chạy ở bảy chỗ. "
  "Tài liệu này lấy theo mã. Ghi lại đây để người sau khỏi lẫn.")

table(
    "Bảng P.2 — Bảy chỗ bản hướng dẫn cũ ghi khác mã",
    ["Chỗ", "Bản hướng dẫn cũ ghi", "Mã đã chạy"],
    [
        ["Trình tự lúc bật nguồn", "tự đo cảm biến ngay khi bật nguồn",
         "nằm ở trạng thái dừng, phải bấm nút mới đo"],
        ["Khoảng bật giữ cân bằng", "cộng trừ 2 độ", "cộng trừ 0,5 độ"],
        ["Ngưỡng coi là đã đổ", "45 độ", "30 độ"],
        ["Tốc độ cổng nối tiếp", "115 200 baud", "9 600 baud"],
        ["Chân chọn chiều", "D2 và D4", "D6 và D4"],
        ["Bộ nhớ dùng hết", "5 710 byte chương trình, 87 byte chạy", "13 690 byte chương trình, 909 byte chạy"],
        ["Hệ số tỉ lệ", "hạ từ 15,0 xuống 12,0", "đã là 12,0, không phải hạ"],
    ],
    widths=[4.6, 5.8, 5.6],
)

doc.save(RA)
print("Đã ghi:", RA)
