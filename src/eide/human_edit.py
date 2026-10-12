# -*- coding: utf-8 -*-
"""Phân loại sửa của người và hệ quả — EIDE-MDD-40 §E4.1.

| Loại sửa | Nhận biết | Tác tử làm gì |
|---|---|---|
| Nội dung | Diff chạm trường có nghĩa | Nhắc + STALE + đề nghị chạy lại hạ nguồn |
| Quyết định | Diff chạm `choice`/`chosen` | ADR mới; hỏi giữ nhánh cũ hay bỏ |
| Trình bày | Diff chỉ chạm `label`/`order`/`note` | Nhắc ngắn; **không STALE**; học thói quen |
| Bác bỏ | Đánh dấu "không phải lỗi"/"không đúng ý tôi" | Ghi vào EIDE.md §Đừng; không đề xuất lại |
| lock_broken | HumanAct edit có lock_broken | Dừng sửa tệp đó; 3-way merge; trình diff |

Vì sao việc phân loại này đáng có mã riêng: nếu mọi sửa đều gây STALE thì đổi tên một
khối sẽ làm cả chuỗi hạ nguồn sáng đèn cảnh báo. Người sẽ học được rằng băng cảnh báo
không có nghĩa gì, và lần STALE thật sự quan trọng sẽ bị bỏ qua. Ca CX08 đo đúng chỗ đó.

Phần thứ hai của tệp này là **Fact tầng NGƯỜI tự động** (§E4 bước 3, ca CX05):

    "Số mới trong sửa không có nguồn → tạo Fact tầng NGƯỜI với source = human_act"

Người sửa tiêu chí từ "≥ 1 MB/s" thành "≥ 5 MB/s". Con số 5 chưa từng có trong tài
liệu nào. Nhưng nó cũng không phải phỏng đoán của mô hình — **người dùng khẳng định
nó**, và họ là một nguồn có tên. Nên nó thành Fact tầng NGƯỜI: dùng được để so sánh và
sinh mã như VÀNG, nhưng mọi nơi dùng đều ghi "(anh cho, chưa có tài liệu)", và tác tử
nên đề nghị tìm tài liệu để nâng lên VÀNG.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .errors import schema_violation

# Trường chỉ ảnh hưởng tới cách trình bày — sửa chúng không làm hạ nguồn lỗi thời.
TRUONG_TRINH_BAY = frozenset({
    "label", "ten", "tieu_de", "order", "thu_tu", "note", "ghi_chu", "mo_ta_ngan",
    "nhom", "mau", "bi_danh",
})

# Trường mang một quyết định.
TRUONG_QUYET_DINH = frozenset({"chon", "choice", "chosen", "da_chon", "quyet_boi"})

# Số có đơn vị kỹ thuật — ứng viên thành Fact.
_SO_CO_DON_VI = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*"
    r"(ms|µs|us|ns|s|Hz|kHz|MHz|GHz|mV|V|kV|mA|uA|µA|A|mAh|Ah|W|mW|"
    r"kΩ|MΩ|Ω|ohm|uF|µF|nF|pF|mH|uH|dB|dBm|bps|kbps|Mbps|Gbps|B/s|KB/s|MB/s|GB/s|"
    r"KB|MB|GB|TB|°C|%)",
    re.IGNORECASE)


@dataclass(slots=True)
class PhanLoai:
    loai: str                      # noi_dung | quyet_dinh | trinh_bay | bac_bo | lock_broken
    truong_doi: list[str] = field(default_factory=list)
    gay_stale: bool = True
    ly_do: str = ""

    @property
    def mo_ta_vi(self) -> str:
        return {
            "noi_dung": "sửa nội dung",
            "quyet_dinh": "đổi quyết định",
            "trinh_bay": "sửa cách trình bày",
            "bac_bo": "bác bỏ",
            "lock_broken": "sửa tệp tác tử đang giữ",
        }.get(self.loai, self.loai)


def phan_loai(*, truoc: dict[str, Any], sau: dict[str, Any],
              lock_broken: bool = False, bac_bo: bool = False,
              duong_dan_doi: list[str] | None = None) -> PhanLoai:
    """Xếp loại một lần sửa của người theo §E4.1.

    `duong_dan_doi` (EIDE-EDIT-47 DEV-368) — danh sách đường dẫn LỒNG mà người vừa chạm,
    ví dụ `["elements/3/mau", "assert/0/nguong"]`. Có nó thì phép xếp loại nhìn được vào
    bên trong hiện vật; không có nó, mọi sửa sâu đều ra "nội dung" vì **trường cấp một**
    (`elements`, `assert`) đổi.

    Xếp theo ĐOẠN ĐẦU hay đoạn CUỐI? — đoạn **cuối**, cộng với đoạn đầu.
    `elements/3/mau` là sửa màu một nhãn: trình bày. `elements/3/x` là dời nó đi chỗ khác:
    nội dung. Hai đường ấy chung đoạn đầu `elements`, nên chỉ nhìn đoạn đầu thì cả hai
    cùng loại — và một trong hai sẽ bị xếp sai. Tài liệu viết "theo đoạn đầu" và đó là
    chỗ làm khác, có ghi vào DEV-LOG.
    """
    if lock_broken:
        return PhanLoai("lock_broken", ly_do="người sửa tệp tác tử đang giữ soft-lock")
    if bac_bo:
        return PhanLoai("bac_bo", gay_stale=False,
                        ly_do="người bác bỏ một phát hiện hoặc một đề xuất")

    if duong_dan_doi:
        doan = [_doan_co_nghia(d) for d in duong_dan_doi]
        if any(d in TRUONG_QUYET_DINH for d in doan):
            return PhanLoai("quyet_dinh", list(duong_dan_doi),
                            ly_do="chạm trường mang quyết định")
        if all(d in TRUONG_TRINH_BAY for d in doan):
            return PhanLoai("trinh_bay", list(duong_dan_doi), gay_stale=False,
                            ly_do="chỉ chạm trường trình bày")
        return PhanLoai("noi_dung", list(duong_dan_doi), ly_do="chạm trường có nghĩa")

    doi = [k for k in set(truoc) | set(sau) if truoc.get(k) != sau.get(k)]
    if not doi:
        return PhanLoai("trinh_bay", gay_stale=False, ly_do="không có gì đổi")

    if any(k in TRUONG_QUYET_DINH for k in doi):
        return PhanLoai("quyet_dinh", doi, ly_do="chạm trường mang quyết định")

    if all(k in TRUONG_TRINH_BAY for k in doi):
        # CX08 — đổi tên khối không làm mã lỗi thời.
        return PhanLoai("trinh_bay", doi, gay_stale=False,
                        ly_do="chỉ chạm trường trình bày")

    return PhanLoai("noi_dung", doi, ly_do="chạm trường có nghĩa")


def _doan_co_nghia(duong: str) -> str:
    """Đoạn mang nghĩa của một đường dẫn: đoạn CUỐI không phải chỉ số.

    `elements/3/mau` → `mau`; `assert/0` → `assert`; `label` → `label`.
    """
    doan = [d for d in str(duong).split("/") if d and not d.isdigit() and d != "-"]
    return doan[-1] if doan else str(duong)


# =========================================================================== patch
def ap_patch(canonical: dict[str, Any], patch: list[dict[str, Any]]) -> dict[str, Any]:
    """Áp một danh sách phép sửa theo ĐƯỜNG DẪN LỒNG. Trả BẢN SAO — EIDE-EDIT-47 §3.1.

    Đường dẫn là JSON-Pointer rút gọn: `a/b/2/c`, `-` nghĩa là cuối mảng.
    Phép: `set` (mặc định) · `add` · `remove` · `move`.

    Vì sao cần nó, và vì sao nó thay một đống nhánh `if`: đường sửa cũ chỉ thay được
    **trường cấp một**, nên mỗi loại hiện vật có cấu trúc lồng lại phải có một nhánh riêng
    trong `_nguoi_sua` — `symbol` đã có một nhánh như thế, và chú thích của nó nói thẳng
    "nới đường chung ra để chạm tới đây là nới một đường mà mọi tab khác đang dùng". Bảy
    loại hiện vật nữa chờ tới lượt. Một phép áp đường dẫn chung là cách KHÔNG phải viết
    bảy nhánh.

    **Không sửa tại chỗ** (`copy.deepcopy`): người gọi còn giữ bản cũ để so, để ghi
    `noi_dung_truoc`, và để xếp loại sửa. Sửa tại chỗ thì bản "trước" biến thành bản "sau"
    ngay dưới tay họ, và changeset sẽ nói hai bản giống hệt nhau.
    """
    import copy

    ra = copy.deepcopy(canonical)
    for i, p in enumerate(patch or []):
        op = str(p.get("op") or "set")
        duong = str(p.get("path") or "")
        if not duong or ".." in duong:
            raise schema_violation(f"patch[{i}].path",
                                   f"đường dẫn rỗng hoặc có “..”: {duong!r}")
        if op not in ("set", "add", "remove", "move"):
            raise schema_violation(f"patch[{i}].op", f"phép lạ: {op!r}")

        if op == "move":
            gia = _lay(ra, duong, f"patch[{i}].path")
            _xoa(ra, duong, f"patch[{i}].path")
            _dat(ra, str(p.get("to") or ""), gia, f"patch[{i}].to", them=True)
        elif op == "remove":
            _xoa(ra, duong, f"patch[{i}].path")
        else:
            _dat(ra, duong, p.get("value"), f"patch[{i}].path", them=(op == "add"))
    return ra


def doc_duong(canonical: dict[str, Any], duong: str) -> Any:
    """Giá trị đang nằm ở một đường dẫn. Lạc đường thì nổ — người gọi quyết nghĩa của nó."""
    return _lay(canonical, duong, f"path {duong}")


def _tach(duong: str) -> list[str]:
    return [d for d in duong.split("/") if d != ""]


def _di(goc: Any, doan: list[str], o: str) -> Any:
    """Đi tới vật chứa của đoạn cuối. Lạc đường thì NÓI RA ĐƯỜNG NÀO — một lỗi
    "không tìm thấy" không chỉ ra chỗ sai thì người chỉ còn cách thử lại y nguyên."""
    cur = goc
    for k in doan:
        if isinstance(cur, list):
            if not k.lstrip("-").isdigit():
                raise schema_violation(o, f"“{k}” không phải chỉ số của một danh sách")
            try:
                cur = cur[int(k)]
            except IndexError:
                raise schema_violation(o, f"không có phần tử thứ {k}") from None
        elif isinstance(cur, dict):
            if k not in cur:
                raise schema_violation(o, f"không có nhánh “{k}”")
            cur = cur[k]
        else:
            raise schema_violation(o, f"“{k}” đi vào một giá trị không có nhánh con")
    return cur


def _lay(goc: Any, duong: str, o: str) -> Any:
    doan = _tach(duong)
    return _di(goc, doan, o)


def _dat(goc: Any, duong: str, gia: Any, o: str, *, them: bool) -> None:
    doan = _tach(duong)
    if not doan:
        raise schema_violation(o, "đường dẫn rỗng")
    cha = _di(goc, doan[:-1], o)
    cuoi = doan[-1]
    if isinstance(cha, list):
        if cuoi == "-":
            cha.append(gia)
            return
        if not cuoi.lstrip("-").isdigit():
            raise schema_violation(o, f"“{cuoi}” không phải chỉ số của một danh sách")
        k = int(cuoi)
        if them:
            cha.insert(k, gia)
        else:
            try:
                cha[k] = gia
            except IndexError:
                raise schema_violation(o, f"không có phần tử thứ {k}") from None
    elif isinstance(cha, dict):
        if not them and cuoi not in cha:
            raise schema_violation(o, f"không có nhánh “{cuoi}” để sửa")
        cha[cuoi] = gia
    else:
        raise schema_violation(o, "chỗ cần ghi không phải bảng hay danh sách")


def _xoa(goc: Any, duong: str, o: str) -> None:
    doan = _tach(duong)
    if not doan:
        raise schema_violation(o, "đường dẫn rỗng")
    cha = _di(goc, doan[:-1], o)
    cuoi = doan[-1]
    if isinstance(cha, list):
        if not cuoi.lstrip("-").isdigit():
            raise schema_violation(o, f"“{cuoi}” không phải chỉ số của một danh sách")
        try:
            del cha[int(cuoi)]
        except IndexError:
            raise schema_violation(o, f"không có phần tử thứ {cuoi}") from None
    elif isinstance(cha, dict):
        if cuoi not in cha:
            raise schema_violation(o, f"không có nhánh “{cuoi}” để xoá")
        del cha[cuoi]
    else:
        raise schema_violation(o, "chỗ cần xoá không phải bảng hay danh sách")


# =========================================================================== Fact NGƯỜI
@dataclass(slots=True)
class SoMoi:
    gia_tri: str
    don_vi: str
    truong: str
    nguyen_van: str

    @property
    def khoa(self) -> str:
        """Khoá Fact suy từ tên trường — `criteria` → `criteria.nguong`."""
        return f"{self.truong}.{_ten_theo_don_vi(self.don_vi)}"


def so_moi_khong_nguon(*, truoc: dict[str, Any], sau: dict[str, Any],
                       nguon_da_co: str) -> list[SoMoi]:
    """Tìm số có đơn vị VỪA XUẤT HIỆN trong bản sửa mà chưa truy vết được.

    `nguon_da_co` là khối chữ gom từ Fact đã có + EIDE.md — cùng nguồn mà
    constant-guard dùng, để hai lớp không nói hai điều khác nhau về cùng một con số.
    """
    ra: list[SoMoi] = []
    for truong, gia_tri_sau in sau.items():
        if not isinstance(gia_tri_sau, str):
            continue
        cu = str(truoc.get(truong, ""))
        so_cu = {m.group(0) for m in _SO_CO_DON_VI.finditer(cu)}
        for m in _SO_CO_DON_VI.finditer(gia_tri_sau):
            if m.group(0) in so_cu:
                continue                       # số này vốn đã có, không phải cái mới
            so = m.group(1).replace(",", ".")
            if so in nguon_da_co:
                continue                       # đã truy vết được ở đâu đó
            ra.append(SoMoi(gia_tri=m.group(1), don_vi=m.group(2),
                            truong=truong, nguyen_van=m.group(0)))
    return ra


def _ten_theo_don_vi(dv: str) -> str:
    d = dv.lower()
    if d in ("ms", "µs", "us", "ns", "s"):
        return "thoi_gian"
    if d in ("hz", "khz", "mhz", "ghz"):
        return "tan_so"
    if d in ("mv", "v", "kv"):
        return "dien_ap"
    if d in ("ma", "ua", "µa", "a", "mah", "ah"):
        return "dong"
    if d in ("kω", "mω", "ω", "ohm"):
        return "tro_khang"
    if d in ("uf", "µf", "nf", "pf", "mh", "uh"):
        return "linh_kien"
    if d in ("bps", "kbps", "mbps", "gbps", "b/s", "kb/s", "mb/s", "gb/s"):
        return "thong_luong"
    if d in ("kb", "mb", "gb", "tb"):
        return "dung_luong"
    if d == "°c":
        return "nhiet_do"
    if d == "%":
        return "ty_le"
    return "gia_tri"


def tao_fact_nguoi(store: Any, *, hien_vat: str, so: SoMoi, trich_loi: str,
                   human_act_id: str) -> dict[str, Any]:
    """Ghi một Fact tầng NGƯỜI từ con số người vừa nhập.

    `origin=user`, `tier=NGUOI`, `source` mang trích lời họ. §C1 nói tầng NGƯỜI dùng
    được **như VÀNG** cho so sánh và sinh mã — nhưng mọi nơi dùng đều phải ghi
    "(anh cho, chưa có tài liệu)", và tác tử nên đề nghị tìm tài liệu nâng lên VÀNG.
    """
    fid = f"f-nguoi-{abs(hash((hien_vat, so.khoa))) % 10**8}"
    store.put_fact({
        "fact_id": fid,
        "subject": hien_vat,
        "key": so.khoa,
        "value": so.gia_tri,
        "unit": so.don_vi,
        "tier": "NGUOI",
        "origin": "user",
        "source": {"human_act_id": human_act_id, "quote": trich_loi},
        "explain": {
            "summary": f"{so.khoa} = {so.nguyen_van} — anh đặt khi sửa {hien_vat}",
            "why": "Người dùng khẳng định con số này; chưa có tài liệu nào xác thực.",
            "sources": [{"kind": "human_act", "ref": human_act_id, "tier": "NGUOI"}],
            "diff_prev": "bản đầu tiên",
            "next": "Tìm tài liệu để nâng lên tầng VÀNG.",
            "confidence": "NGUOI",
        },
    })
    return {"fact_id": fid, "key": so.khoa, "value": so.nguyen_van}


def loi_nhac_fact_nguoi(ds: list[dict[str, Any]]) -> str:
    """Câu tác tử nói khi vừa ghi Fact tầng NGƯỜI từ sửa của người."""
    if not ds:
        return ""
    muc = ", ".join(f"**{f['key']} = {f['value']}**" for f in ds)
    nhieu = len(ds) > 1
    return (f"Con số {muc} anh vừa đặt chưa có trong tài liệu nào, nên tôi ghi "
            f"{'chúng' if nhieu else 'nó'} ở **tầng NGƯỜI** — dùng được để so sánh và "
            f"sinh mã, nhưng mọi chỗ dùng tôi sẽ ghi rõ *(anh cho, chưa có tài liệu)*. "
            f"Muốn tôi đi tìm tài liệu để nâng lên tầng VÀNG không?")
