# -*- coding: utf-8 -*-
"""Khối "Kiến trúc phần mềm" cho tab Thiết kế (A5.6).

## Vì sao cần tệp này

Tab **Thiết kế** trước đây chỉ biết một loại thiết kế: **mạch**. Ba khối của nó — BOM, Bản đồ
tri thức mạch, Sơ đồ nguyên lý — đều dựng từ CKM. MDD-40 §E7 dòng 405 đòi tab này hiện *"hình
+ danh sách khối"* dựng từ `module_graph`, mà `module_graph` là một nhánh của CKM (§C2).

Hệ quả đo được trên dự án `rtos-ptit`: tác tử phân tích ba phương án kiến trúc, chốt một
phương án qua cổng G-DESIGN, viết 689 dòng nhân RTOS chia làm bốn mô-đun — và tab Thiết kế
**rỗng hoàn toàn**, cả ba khối đều hiện "chưa có gì". Người theo dõi thấy phần phân tích thiết
kế chạy tốt trong hội thoại rồi mở tab ra thì không còn gì.

Thiết kế phần mềm không có nhà. Tệp này dựng cái nhà đó, **không thêm loại hiện vật nào**: mọi
thứ ở đây là phép chiếu từ những thứ đã có trong kho — `option` (phương án), `adr` (quyết
định), `code` (tệp mã) — đúng bất biến I2/I3, giao diện không quyết định gì.

## Sơ đồ có cạnh thật, hoặc không có sơ đồ

Vẽ các mô-đun thành ô rồi **không nối gì** là trang trí giả dạng thiết kế: nhìn như một bản vẽ
kiến trúc nhưng không nói được mô-đun nào dùng mô-đun nào. Nên cạnh ở đây đọc từ `#include` /
`import` **có thật trong tệp**. Không đọc được tệp thì khối nói thẳng là không đọc được và chỉ
liệt kê danh sách — chứ không vẽ một sơ đồ rỗng.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Trần đọc tệp mỗi lần vẽ bề mặt. `paint()` chạy cuối MỖI lượt, nên một vòng lặp đọc không
# chặn trên là một khoản phí trả mãi mãi. Bốn chục tệp đủ cho một sơ đồ người còn đọc được;
# quá số này thì sơ đồ cũng đã thành đám rối.
TRAN_TEP = 40

# Đuôi tệp coi là mã dựng nên sơ đồ. `.h`/`.hpp` giữ lại vì ở C thì quan hệ mô-đun nằm phần
# lớn trong include của header.
DUOI_MA = frozenset({".c", ".h", ".cpp", ".hpp", ".cc", ".py", ".rs", ".go", ".swift", ".ts",
                     ".js", ".java", ".kt"})


def _ten_nut(i: int) -> str:
    """Mã nút cho mermaid — `n0`, `n1`… chứ không lấy tên tệp.

    Tên tệp có dấu chấm và gạch chéo; đưa thẳng vào mermaid thì bộ đọc cắt sai chỗ. Nhãn hiện
    ra vẫn là tên tệp, chỉ mã nút là chữ thuần.
    """
    return f"n{i}"


def _thoat(s: str) -> str:
    """Bỏ ký tự làm hỏng nhãn mermaid. Dấu ngoặc kép đóng nhãn sớm."""
    return str(s).replace('"', "'").replace("[", "(").replace("]", ")")


def _doc_phu_thuoc(goc: Path, duong: list[str]) -> dict[str, list[str]]:
    """Đọc include/import của từng tệp. Tệp nào đọc không được thì vắng mặt, không đoán."""
    from .phan_tich_ma import _phu_thuoc

    ra: dict[str, list[str]] = {}
    for d in duong[:TRAN_TEP]:
        p = (goc / d)
        try:
            if not p.is_file():
                continue
            ra[d] = _phu_thuoc(p.read_text("utf-8", errors="replace"))
        except OSError:
            continue
    return ra


def so_do_mo_dun(goc: str, duong: list[str]) -> tuple[str, int, int]:
    """Sinh mermaid `graph` cho các tệp mã, cạnh đọc từ include thật.

    Trả về (nguồn mermaid, số tệp đọc được, số cạnh). Không đọc được tệp nào, hoặc đọc được
    mà **không có cạnh nào**, thì trả nguồn rỗng — để bên gọi hiện danh sách thay vì vẽ một
    sơ đồ toàn ô rời.
    """
    if not goc or not duong:
        return "", 0, 0
    phu = _doc_phu_thuoc(Path(goc), duong)
    if not phu:
        return "", 0, 0

    # Khớp include về đúng tệp trong dự án: `#include "rtos_types.h"` trỏ tới
    # `firmware/rtos/rtos_types.h`. Khớp theo TÊN TỆP, vì include trong C thường là đường
    # tương đối so với thư mục include chứ không so với gốc dự án.
    theo_ten: dict[str, list[str]] = {}
    for d in duong:
        theo_ten.setdefault(Path(d).name, []).append(d)

    canh: set[tuple[str, str]] = set()
    for d, ds in phu.items():
        for x in ds:
            ten = Path(x).name
            for dich in theo_ten.get(ten, []):
                if dich != d:
                    canh.add((d, dich))
    if not canh:
        return "", len(phu), 0

    # Chỉ giữ tệp có mặt trong ít nhất một cạnh — ô rời không nói gì thêm.
    co_canh = {x for c in canh for x in c}
    giu = [d for d in duong if d in co_canh]
    ma = {d: _ten_nut(i) for i, d in enumerate(giu)}

    # Nhóm theo thư mục: mỗi thư mục một `subgraph`, đó chính là "mô-đun" người đọc thấy.
    nhom: dict[str, list[str]] = {}
    for d in giu:
        nhom.setdefault(str(Path(d).parent), []).append(d)

    dong = ["graph TB"]
    for i, (thu_muc, ts) in enumerate(sorted(nhom.items())):
        nhan = thu_muc if thu_muc not in (".", "") else "gốc dự án"
        if len(nhom) > 1:
            dong.append(f'    subgraph g{i}["{_thoat(nhan)}"]')
            for d in sorted(ts):
                dong.append(f'        {ma[d]}["{_thoat(Path(d).name)}"]')
            dong.append("    end")
        else:
            for d in sorted(ts):
                dong.append(f'    {ma[d]}["{_thoat(Path(d).name)}"]')
    for a, b in sorted(canh):
        dong.append(f"    {ma[a]} --> {ma[b]}")
    return "\n".join(dong), len(phu), len(canh)


def _gach_dau_dong(xs: Any) -> str:
    if isinstance(xs, str):
        xs = [xs] if xs.strip() else []
    return "\n".join(f"- {x}" for x in (xs or []) if str(x).strip())


def muc_kien_truc(store: Any, goc: str = "") -> list[dict[str, str]]:
    """Các mục của khối A5.6. Rỗng nghĩa là chưa có phương án/quyết định nào để chiếu."""
    opts = store.list("option", limit=20)
    adrs = store.list("adr", limit=50)
    if not opts and not adrs:
        return []

    chon = next((o for o in opts if (o.get("canonical") or {}).get("da_chon")), None)
    adr = adrs[-1] if adrs else None
    muc: list[dict[str, str]] = []

    # --- 1. Kiến trúc đã chốt, kèm sơ đồ mô-đun ------------------------------------------
    than: list[str] = []
    if chon:
        c = chon["canonical"]
        than.append(str(c.get("kien_truc") or c.get("ten") or ""))
        than.append(f"\n*Phương án `{chon['id']}` · chốt ở "
                    + (f"`{adr['id']}`*" if adr else "chưa ghi thành ADR*"))
    elif adr:
        than.append(str((adr.get("canonical") or {}).get("boi_canh") or ""))

    files = [f["id"] for f in store.list("code", limit=200)
             if Path(str(f["id"])).suffix.lower() in DUOI_MA]
    mermaid, doc_duoc, so_canh = so_do_mo_dun(goc, files)
    if mermaid:
        than.append(f"\n```mermaid\n{mermaid}\n```")
        than.append(f"\n*Sơ đồ dựng từ {so_canh} quan hệ `#include`/`import` đọc được trong "
                    f"{doc_duoc} tệp — không phải sơ đồ vẽ tay.*")
    elif files:
        # Nói ra vì sao KHÔNG có hình, thay vì để một khoảng trống người tự đoán.
        than.append(f"\n*Chưa vẽ được sơ đồ quan hệ: "
                    + ("đọc được " + str(doc_duoc) + " tệp nhưng không tệp nào "
                       "include/import tệp nào khác trong dự án."
                       if doc_duoc else "không đọc được tệp mã nào trên đĩa.")
                    + " Danh sách mô-đun ở mục dưới.*")
    if any(t.strip() for t in than):
        muc.append({"ten": ("Kiến trúc đã chọn — "
                            + str((chon or {}).get("canonical", {}).get("ten", "")) if chon
                            else "Kiến trúc"),
                    "than": "\n".join(than).strip()})

    # --- 2. Thành phần chính -------------------------------------------------------------
    if chon and chon["canonical"].get("linh_kien_chinh"):
        muc.append({"ten": "Thành phần chính",
                    "than": _gach_dau_dong(chon["canonical"]["linh_kien_chinh"])})

    # --- 3. Rủi ro tác tử đã nêu NGAY KHI chọn -------------------------------------------
    #
    # Đây là thứ dễ mất nhất: rủi ro nói ra lúc chọn, rồi trôi khỏi màn hình, rồi vài tuần sau
    # nó xảy ra và không ai nhớ là đã có người cảnh báo.
    if chon and chon["canonical"].get("rui_ro"):
        muc.append({"ten": "Rủi ro đã nêu khi chọn",
                    "than": _gach_dau_dong(chon["canonical"]["rui_ro"])})

    # --- 4. Các phương án đã loại --------------------------------------------------------
    khac = [o for o in opts if not (o.get("canonical") or {}).get("da_chon")]
    if khac:
        dong = []
        for o in khac:
            c = o["canonical"]
            dong.append(f"**{o['id']} · {c.get('ten', '')}**  \n{c.get('kien_truc', '')}")
            if c.get("do_kho"):
                dong.append(f"- độ khó: {c['do_kho']}")
            if c.get("chi_phi_uoc"):
                dong.append(f"- chi phí ước: {c['chi_phi_uoc']}")
            for r in (c.get("rui_ro") or [])[:3]:
                dong.append(f"- rủi ro: {r}")
            dong.append("")
        muc.append({"ten": f"Đã cân nhắc rồi loại ({len(khac)} phương án)",
                    "than": "\n".join(dong).strip()})

    # --- 5. Hệ quả đã ghi ----------------------------------------------------------------
    if adr and (adr.get("canonical") or {}).get("he_qua"):
        muc.append({"ten": "Chọn cái này thì kéo theo gì",
                    "than": _gach_dau_dong(adr["canonical"]["he_qua"])})

    # --- 6. Mô-đun trên đĩa --------------------------------------------------------------
    if files:
        nhom: dict[str, list[str]] = {}
        for d in files:
            nhom.setdefault(str(Path(d).parent), []).append(d)
        dong = []
        for thu_muc, ts in sorted(nhom.items()):
            dong.append(f"**{thu_muc if thu_muc not in ('.', '') else 'gốc dự án'}**")
            for d in sorted(ts):
                dong.append(f"- `{Path(d).name}`")
            dong.append("")
        muc.append({"ten": f"Mô-đun trên đĩa ({len(files)} tệp mã)",
                    "than": "\n".join(dong).strip()})

    return muc
