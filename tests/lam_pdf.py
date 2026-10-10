# -*- coding: utf-8 -*-
"""Sinh PDF tối giản cho kiểm thử — không thêm phụ thuộc.

Bài kiểm nền tri thức cần một "datasheet" thật để trích Fact. Kéo `reportlab` vào chỉ
để dựng vài trang chữ là thêm một phụ thuộc nữa phải giải trình khi bảo vệ đề án.

PDF là định dạng có cấu trúc rõ: một danh mục, một cây trang, và mỗi trang một luồng
nội dung dùng toán tử `Tj` để đặt chữ. Chừng đó đủ để `pypdf.extract_text()` đọc ra —
tức đủ để kiểm đúng thứ cần kiểm.
"""

from __future__ import annotations

from pathlib import Path


def _thoat(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def lam_pdf(path: Path, trang: list[list[str]], *, tieu_de: str = "Datasheet thử") -> Path:
    """Dựng PDF, mỗi phần tử của `trang` là danh sách dòng chữ cho một trang."""
    doi_tuong: list[bytes] = []

    def them(noi_dung: bytes) -> int:
        doi_tuong.append(noi_dung)
        return len(doi_tuong)          # số hiệu đối tượng, đánh từ 1

    # 1 danh mục, 2 cây trang — số hiệu đặt trước để tham chiếu chéo.
    so_catalog, so_pages = 1, 2
    doi_tuong.extend([b"", b""])

    so_font = them(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    so_trang: list[int] = []
    for dong in trang:
        chu = ["BT", "/F1 10 Tf", "1 0 0 1 56 760 Tm", "12 TL"]
        for d in dong:
            chu.append(f"({_thoat(d)}) Tj T*")
        chu.append("ET")
        luong = "\n".join(chu).encode("latin-1", "replace")
        so_stream = them(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(luong), luong))
        so_p = them(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (so_pages, so_font, so_stream))
        so_trang.append(so_p)

    kids = b" ".join(b"%d 0 R" % n for n in so_trang)
    doi_tuong[so_pages - 1] = (b"<< /Type /Pages /Count %d /Kids [%s] >>"
                               % (len(so_trang), kids))
    doi_tuong[so_catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % so_pages

    ra = bytearray(b"%PDF-1.4\n")
    vi_tri: list[int] = []
    for i, noi in enumerate(doi_tuong, 1):
        vi_tri.append(len(ra))
        ra += b"%d 0 obj\n" % i + noi + b"\nendobj\n"

    xref = len(ra)
    ra += b"xref\n0 %d\n" % (len(doi_tuong) + 1)
    ra += b"0000000000 65535 f \n"
    for v in vi_tri:
        ra += b"%010d 00000 n \n" % v
    ra += (b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
           % (len(doi_tuong) + 1, so_catalog, xref))

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(ra))
    return path


def lam_pdf_bang(path: Path, bang: list[tuple[str, list[str], list[list[str]]]]) -> Path:
    """Dựng PDF có BẢNG KHUNG THẬT — mỗi phần tử của `bang` là một trang.

    Vì sao phải vẽ khung chứ không chỉ đặt chữ thành cột: `pdfplumber.find_tables()` mặc
    định dò theo **nét vẽ** (`lines`). Một trang chỉ có chữ xếp thẳng hàng thì nó thấy **0
    bảng** — và một bài kiểm dựng trên trang như thế sẽ xanh vì đường dự phòng, không vì
    đường bảng. Nên ô bảng ở đây là `re S` thật: `x y w h re S` vẽ viền một ô.

    Mỗi phần tử: `(tiêu_đề_mục, cột, hàng)`. Tiêu đề mục đặt **phía trên** bảng, vì
    `bang_tu_trang` lấy ngữ cảnh mục từ dòng gần nhất ở trên.
    """
    doi_tuong: list[bytes] = []

    def them(noi_dung: bytes) -> int:
        doi_tuong.append(noi_dung)
        return len(doi_tuong)

    so_catalog, so_pages = 1, 2
    doi_tuong.extend([b"", b""])
    so_font = them(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    so_trang: list[int] = []
    for tieu_de, cot, hang in bang:
        ve: list[str] = ["0.6 w", "0 G"]
        chu: list[str] = []
        x0, y_tren, rong, cao = 56.0, 740.0, 90.0, 20.0
        chu += ["BT", "/F1 11 Tf", f"1 0 0 1 {x0:.1f} 782 Tm",
                f"({_thoat(tieu_de)}) Tj", "ET"]
        day = [cot, *hang]
        for r, dong in enumerate(day):
            for c in range(len(cot)):
                ve.append(f"{x0 + c * rong:.1f} {y_tren - (r + 1) * cao:.1f} "
                          f"{rong:.1f} {cao:.1f} re S")
            for c, o in enumerate(dong):
                if not str(o).strip():
                    continue
                chu += ["BT", "/F1 9 Tf",
                        f"1 0 0 1 {x0 + c * rong + 3:.1f} "
                        f"{y_tren - (r + 1) * cao + 6:.1f} Tm",
                        f"({_thoat(str(o))}) Tj", "ET"]
        luong = "\n".join(ve + chu).encode("latin-1", "replace")
        so_stream = them(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(luong), luong))
        so_trang.append(them(
            b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
            % (so_pages, so_font, so_stream)))

    kids = b" ".join(b"%d 0 R" % n for n in so_trang)
    doi_tuong[so_pages - 1] = (b"<< /Type /Pages /Count %d /Kids [%s] >>"
                               % (len(so_trang), kids))
    doi_tuong[so_catalog - 1] = b"<< /Type /Catalog /Pages %d 0 R >>" % so_pages

    ra = bytearray(b"%PDF-1.4\n")
    vi_tri: list[int] = []
    for i, noi in enumerate(doi_tuong, 1):
        vi_tri.append(len(ra))
        ra += b"%d 0 obj\n" % i + noi + b"\nendobj\n"
    xref = len(ra)
    ra += b"xref\n0 %d\n0000000000 65535 f \n" % (len(doi_tuong) + 1)
    for v in vi_tri:
        ra += b"%010d 00000 n \n" % v
    ra += (b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n"
           % (len(doi_tuong) + 1, so_catalog, xref))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(ra))
    return path


# Datasheet mẫu: đủ thông số để trích Fact và để `fact.compare` có hai vế thật.
DATASHEET_ATMEGA = [
    [
        "ATmega328P  8-bit AVR Microcontroller  DS40002061B",
        "",
        "Features",
        "  Flash memory   32768 B",
        "  SRAM size      2048 B",
        "  EEPROM         1024 B",
        "  Maximum operating frequency  20 MHz",
    ],
    [
        "Electrical Characteristics",
        "",
        "  Supply voltage  VDD  min 1.8 V",
        "  VDD (max)   5.5 V",
        "  VIH   input high voltage   3.0 V",
        "  VOL   output low voltage   0.9 V",
        "  ICC   supply current   0.2 mA",
        "  IOL   40 mA",
        "  Operating temperature   85 °C",
    ],
    [
        "Two-Wire Interface (TWI)",
        "",
        "  Recommended pull-up   4.7 kΩ",
        "  Bus frequency   400 kHz",
    ],
]

DATASHEET_CAM_BIEN_5V = [
    [
        "TMP-5V0 Temperature Sensor  Rev C",
        "",
        "  Supply voltage   5.0 V",
        "  VIH   input high voltage   3.5 V",
        "  VDDIO   maximum   3.6 V",
    ],
]
