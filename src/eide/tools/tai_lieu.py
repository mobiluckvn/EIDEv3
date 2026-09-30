# -*- coding: utf-8 -*-
"""`doc.render` — tác tử làm ra tệp tài liệu `.docx` / `.xlsx` / `.pdf` cho người đọc.

Bảy công cụ `doc.*` có sẵn đều là **đọc** tài liệu người dùng đưa vào. Chiều ngược lại —
tác tử viết ra một tài liệu để gửi đi — trước tệp này không có đường nào: `fs.write` gọi
`write_text`, mà `.docx` là một tệp ZIP.

## Vì sao một công cụ, không phải ba

`doc.to_docx` + `doc.to_xlsx` + `doc.to_pdf` sẽ là ba công cụ mà mỗi cái chỉ đẻ ra được đúng
một hình dạng tài liệu người viết công cụ nghĩ sẵn. Ở đây **hình dạng nằm trong nguồn
Markdown** do tác tử viết, nên một cửa là đủ, và yêu cầu lạ tới đâu cũng diễn đạt được bằng
nguồn.

Yêu cầu vượt quá cả Markdown — mẫu bìa riêng, biểu đồ, trộn nhiều nguồn dữ liệu — thì đường đi
đã có sẵn và **không phải đường này**: `tool.propose` cho tác tử tự viết trình sinh riêng cho
chính nó, có bộ kiểm, có người duyệt.

## Hai chỗ nó nói KHÔNG

* **Nguồn không có bảng mà đòi `.xlsx`** → báo lỗi. Xem `xuat_ban.py`.
* **Không có LibreOffice mà đòi `.pdf`** → báo thiếu kèm cách khác, không vẽ PDF thô sơ.

## Hoàn tác

Nguồn `.md` đi qua `fs.write` nên có changeset và diff đọc được. Tệp render ra là hạng
`dung_lai_duoc`: hoàn tác nó bằng cách xoá đi rồi render lại từ nguồn — chứ **không** giữ bản
sao nhị phân trong kho blob. Giữ một bản sao 200 KB cho mỗi lần render một thứ dựng lại được
trong hai giây là trả giá mà không mua được gì.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import EideError
from .registry import Registry, ToolResult
from .writing import EXPLAIN_SCHEMA, _rel, _sandbox

# Đuôi tệp bắt buộc cho từng định dạng — sai đuôi thì Word/Excel từ chối mở, và người dùng sẽ
# nghĩ tệp hỏng chứ không nghĩ tên sai.
DUOI = {"docx": ".docx", "xlsx": ".xlsx", "pdf": ".pdf", "pptx": ".pptx"}


def register(r: Registry) -> Registry:
    dang_ky(r)
    return r


def dang_ky(r: Registry) -> None:
    @r.tool("doc.render", "Tri thức",
            "Làm ra một tệp tài liệu cho NGƯỜI ĐỌC — Word (.docx), PowerPoint (.pptx), "
            "Excel (.xlsx) hoặc PDF — từ một tệp Markdown bạn đã viết bằng fs.write. Dùng khi "
            "người dùng cần một tệp gửi đi, in ra hoặc nộp, chứ không phải chữ trong khung "
            "chat. Khối ```mermaid trong nguồn được VẼ THÀNH HÌNH trong tệp (sequenceDiagram "
            "và graph/flowchart), không in ra cú pháp. Công thức LaTeX `$…$` giữa dòng, "
            "`$$…$$` nguyên đoạn và khối ```math được đổi sang ký hiệu toán đọc được "
            "(× ≤ ∈ τ Ω…) ở MỌI chỗ — kể cả trong bảng, gạch đầu dòng và trích dẫn. "
            "PowerPoint: mỗi tiêu đề một slide.",
            {"type": "object",
             "properties": {
                 "nguon": {"type": "string",
                           "description": "Đường dẫn tệp .md trong dự án — viết trước bằng "
                                          "fs.write"},
                 "ra": {"type": "string",
                        "description": "Đường dẫn tệp sẽ tạo, kèm đuôi đúng định dạng"},
                 "dinh_dang": {"type": "string", "enum": ["docx", "pptx", "xlsx", "pdf"],
                               "description": "pptx: mỗi tiêu đề một slide; xlsx: cần có "
                                              "bảng Markdown trong nguồn"},
                 "tieu_de": {"type": "string",
                             "description": "Tên in trên trang bìa; bỏ trống nếu nguồn đã có "
                                            "tiêu đề mức 1"},
                 "explain": EXPLAIN_SCHEMA},
             "required": ["nguon", "ra", "dinh_dang", "explain"]},
            risk="R2", gate="G-FILE", writes_artefact=True, needs_explain=True,
            produces=["doc"],
            keywords=["xuất word", "xuất excel", "xuất pdf", "xuất powerpoint", "docx",
                      "xlsx", "pdf", "pptx", "slide", "trình chiếu", "làm tài liệu",
                      "viết báo cáo", "in ra", "nộp", "gửi file", "sơ đồ trong tài liệu"],
            returns_vi="Đường dẫn tệp và SỐ ĐO đọc lại từ chính tệp ấy")
    def doc_render(ctx: Any, nguon: str, ra: str, dinh_dang: str, explain: dict[str, Any],
                   tieu_de: str = ""):
        from ..xuat_ban import render

        p_nguon = _sandbox(ctx, nguon)
        if not p_nguon.is_file():
            return ToolResult(False, error=EideError(
                "E2010", f"Không có tệp nguồn {_rel(ctx, p_nguon)}.",
                hint_for_agent=("Viết nguồn Markdown bằng `fs.write` TRƯỚC, rồi mới render. "
                                "Nguồn nằm trong sổ cái nên người dùng xem được diff và hoàn "
                                "tác được; tệp render ra thì dựng lại từ nguồn bất cứ lúc nào."),
                alternatives=["fs.write", "fs.glob"], blame="agent"))

        p_ra = _sandbox(ctx, ra)
        duoi = DUOI[dinh_dang]
        if p_ra.suffix.lower() != duoi:
            return ToolResult(False, error=EideError(
                "E2011",
                f"Tên tệp ra là {p_ra.name} nhưng định dạng là {dinh_dang} — phải đuôi {duoi}.",
                hint_for_agent=(f"Đổi `ra` thành `{p_ra.with_suffix(duoi).name}`. Sai đuôi thì "
                                "Word/Excel từ chối mở và người dùng sẽ tưởng tệp hỏng chứ "
                                "không tưởng tên sai."),
                blame="agent"))

        try:
            md = p_nguon.read_text("utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return ToolResult(False, error=EideError(
                "E2012", f"Không đọc được {_rel(ctx, p_nguon)}: {e}",
                hint_for_agent="Nguồn phải là tệp văn bản UTF-8.", blame="agent"))

        co_truoc = p_ra.exists()
        kq = render(md, p_ra, dinh_dang, tieu_de=tieu_de, goc_anh=p_nguon.parent)
        if not kq.dat:
            return ToolResult(False, error=EideError(
                "E2013", kq.vi_sao_khong_dat,
                hint_for_agent=("Đây là lời từ chối có chủ ý, không phải sự cố — đọc kỹ rồi "
                                "sửa NGUỒN hoặc đổi định dạng. Đừng gọi lại y nguyên."),
                details={"dinh_dang": dinh_dang, "nguon": _rel(ctx, p_nguon)},
                alternatives=["fs.edit", "doc.render"], blame="agent"))

        rel = _rel(ctx, p_ra)
        # `noi_dung_truoc` bỏ trống: tệp nhị phân không có diff đọc được, và bản cũ dựng lại
        # được từ nguồn. Đường lui vẫn còn — changeset giữ `sha_truoc` của git.
        cs = ctx.history.ghi_tep(
            author=f"agent:{ctx.run_id}", paths=[rel],
            summary=explain.get("summary", f"render {dinh_dang}"), explain=explain,
            run_id=ctx.run_id, loai="doc")
        ctx.mark_agent_wrote(rel)

        return {
            "tep": rel, "dinh_dang": dinh_dang, "nguon": _rel(ctx, p_nguon),
            "changeset": cs.id, "tao_moi": not co_truoc,
            "do_lai": kq.do_lai,
            "duong_day_du": str(p_ra),
            "note_vi": _noi(rel, dinh_dang, kq.do_lai, _rel(ctx, p_nguon), str(p_ra)),
        }


def _noi(tep: str, dinh_dang: str, do_lai: dict[str, Any], nguon: str,
         day_du: str = "") -> str:
    """Câu báo cho người đọc. Nói SỐ ĐO ĐỌC LẠI TỪ TỆP, không nói 'đã ghi xong'.

    `ok` nói về lời gọi, không nói về kết quả: `python-docx` không ném ngoại lệ mới chỉ chứng
    minh thư viện chạy, chưa chứng minh trong tệp có chữ.
    """
    if "khong_doc_lai_duoc" in do_lai:
        return (f"Đã tạo `{tep}` nhưng **mở lại không được**: {do_lai['khong_doc_lai_duoc']}. "
                "Tệp có thể hỏng — thử mở bằng tay trước khi gửi đi.")
    if dinh_dang == "docx":
        do = (f"{do_lai.get('so_doan', 0)} đoạn · {do_lai.get('so_bang', 0)} bảng · "
              f"{do_lai.get('so_ky_tu', 0)} ký tự")
    elif dinh_dang == "pptx":
        do = (f"{do_lai.get('so_slide', 0)} slide · {do_lai.get('so_hinh', 0)} hình · "
              f"{do_lai.get('so_ky_tu', 0)} ký tự")
    elif dinh_dang == "xlsx":
        do = (f"{do_lai.get('so_sheet', 0)} sheet · {do_lai.get('tong_hang', 0)} hàng: "
              + ", ".join(f"{k} ({v['hang']}×{v['cot']})"
                          for k, v in (do_lai.get("sheet") or {}).items()))
    else:
        do = f"{do_lai.get('so_trang', 0)} trang"
    # Lệnh TeX không đổi được thì nói NGAY ĐẦU, cùng chỗ với các cảnh báo khác — người đọc
    # bản in sẽ thấy nguyên cú pháp thô giữa câu, và lúc ấy tệp đã gửi đi rồi.
    sot = do_lai.get("tex_chua_doi_duoc") or []
    canh_bao = ""
    if sot:
        canh_bao = ("\n\n⚠️ **Chưa đổi được " + str(len(sot)) + " lệnh TeX** — "
                    + ", ".join(f"`{x}`" for x in sot[:8])
                    + (" …" if len(sot) > 8 else "")
                    + ". Chúng in ra giấy đúng như đang viết. Viết lại bằng ký hiệu thường "
                      "trong nguồn rồi render lại.")
    # Đường dẫn ĐẦY ĐỦ, không chỉ đường tương đối.
    #
    # Anh Công hỏi ngày 29/09/2026: *"thư mục Agent sinh ra tài liệu nằm ở đâu?"* — tệp nằm
    # trong thư mục dự án, nhưng không chỗ nào nói ra cả đường dẫn, nên người dùng làm ra một
    # tệp rồi đi tìm không thấy. Một tệp không tìm thấy thì cũng bằng chưa làm.
    o_dau = f"\n\nTệp nằm ở: `{day_du}`" if day_du else ""
    return (f"`{tep}` — **{do}** (đếm bằng cách mở lại chính tệp vừa tạo, không phải bằng số "
            f"byte đã ghi).{canh_bao}{o_dau}\n\nNguồn là `{nguon}`: sửa ở đó rồi render lại, "
            "đừng sửa trong Word — bản render là thứ dựng lại được, nguồn mới là thứ giữ "
            "lịch sử.")
