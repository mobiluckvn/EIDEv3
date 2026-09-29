# -*- coding: utf-8 -*-
"""`du-an.json` — tấm thẻ căn cước của một dự án EIDE, nằm ngay trong thư mục dự án.

## Vì sao cần

Toàn bộ một dự án EIDE nằm trong đúng một thư mục, nên **chép thư mục là chuyển cả dự án**.
Nhưng trước tệp này, người cầm thư mục ấy không có cách nào biết ba điều mà không mở EIDE lên:

* Đây có phải một dự án EIDE không, và của bản nào?
* Nó đang ở đâu — chip gì, bao nhiêu yêu cầu, đã nạp bo chưa?
* Chép đi thì **phải mang theo cái gì**, và cái gì bỏ lại được?

Câu thứ ba là câu đắt nhất. Đo trên `stm32f469-freertos` ngày 29/09/2026: thư mục 14,5 MB,
trong đó `.eide/build/` chiếm **3,0 MB** và `firmware/vendor/` chiếm phần lớn phần còn lại —
cả hai đều **dựng lại được**. Không nói ra thì người ta hoặc chép cả đống, hoặc tệ hơn, lọc
bằng cảm giác và bỏ mất sổ cái.

Tệp này là JSON đọc bằng mắt được, ghi lại mỗi khi mở dự án và cuối mỗi lượt.

## Ba hạng dữ liệu

| Hạng | Nghĩa | Mất thì sao |
|---|---|---|
| `ben` | Bền — không dựng lại được | **Mất là mất hẳn**: sổ cái, kho hiện vật, changeset, blob, EIDE.md, git |
| `dung_lai_duoc` | Dựng lại được từ nguồn | Tốn thời gian, không mất thông tin: `.eide/build/`, thư viện hãng |
| `tam` | Tạm, của phiên chạy | Bỏ được ngay: kênh kiểm giao diện, ảnh chụp nháp |

Phân hạng nằm **trong chính tệp**, không phải trong đầu người viết công cụ sao lưu — để một
lệnh chép về sau đọc được nó thay vì đoán lại.

## Chỗ tệp này KHÔNG làm

Nó **không** là nguồn sự thật. Mọi con số trong đây đều dựng lại được từ sổ cái và kho; nó chỉ
là bản tóm tắt để đọc nhanh. Xoá nó đi thì lần mở sau EIDE ghi lại — nhưng xoá `.eide/` thì
không gì cứu được.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TEN_TEP = "du-an.json"
PHIEN_BAN_LUOC_DO = 1

# Phân hạng từng thứ trong thư mục dự án. Thứ tự có nghĩa: khớp đầu tiên thắng.
#
# `None` ở cột "mô tả" nghĩa là mục ấy có thể không tồn tại — dự án mới chưa có `.git`, chưa
# có `build/`. Không có thì không phải lỗi, chỉ là chưa tới lúc.
HANG: tuple[tuple[str, str, str], ...] = (
    ("EIDE.md", "ben", "Bộ nhớ dài hạn của dự án — người và tác tử cùng sửa"),
    (TEN_TEP, "ben", "Chính tệp này"),
    (".eide/ledger.jsonl", "ben", "Sổ cái append-only, có chuỗi hash"),
    (".eide/store.sqlite", "ben", "Kho hiện vật event-sourced"),
    (".eide/changesets.jsonl", "ben", "Changeset và phép nghịch đảo"),
    (".eide/snapshots.jsonl", "ben", "Bản ưng ý do người đặt tên"),
    (".eide/counters.json", "ben", "Bộ đếm mã: cs- · run- · h- · ses-"),
    (".eide/blobs", "ben", "Bản sao nội dung theo hash — đường lui khi hoàn tác"),
    (".eide/sessions", "ben", "Transcript từng phiên, dùng để khôi phục sau sự cố"),
    (".eide/cong-cu", "ben", "Công cụ tác tử tự viết cho chính nó"),
    (".eide/blocks", "ben", "Thư viện khối riêng của dự án"),
    (".git", "ben", "Lịch sử tệp — mỗi changeset một commit"),
    (".eide/build", "dung_lai_duoc", "Sản phẩm biên dịch (.elf/.bin/.hex/.map)"),
    (".eide/ui-test", "tam", "Kênh kiểm giao diện — chỉ có khi đang chạy bộ đo"),
    (".eide/anh-man-hinh.png", "tam", "Ảnh khung hình vừa đọc từ bo"),
    (".eide/transcripts", "tam", "Thư mục cũ, không còn dùng"),
)


def _co(p: Path) -> int:
    """Kích thước theo byte; thư mục thì cộng dồn. Không có thì 0."""
    if not p.exists():
        return 0
    if p.is_file():
        return p.stat().st_size
    return sum(x.stat().st_size for x in p.rglob("*") if x.is_file())


@dataclass(slots=True)
class ThongTinDuAn:
    goc: Path

    def dung(self, *, ten: str = "", store: Any = None, ledger: Any = None,
             eide_md: Any = None) -> dict[str, Any]:
        """Dựng nội dung tệp. Mọi số đọc từ đĩa hoặc từ kho — không nhận số truyền vào."""
        g = self.goc
        # Liệt kê ĐỦ bảng phân hạng, kể cả mục chưa tồn tại — đánh dấu `co: false`.
        #
        # Bản đầu bỏ qua mục chưa có, và một dự án vừa mở (chưa ghi sổ cái lần nào) sinh ra
        # một `du-an.json` KHÔNG nhắc tới `ledger.jsonl`. Người đọc tệp ấy để biết phải chép
        # gì sẽ không chép nó. Danh sách "phải mang theo" là một HỢP ĐỒNG, không phải ảnh
        # chụp hiện trạng: thiếu một dòng ở đây là mất một thứ ở kia.
        muc: list[dict[str, Any]] = []
        for duong, hang, mo_ta in HANG:
            q = g / duong
            muc.append({"duong": duong, "hang": hang, "co": q.exists(),
                        "byte": _co(q), "mo_ta": mo_ta})

        # Tệp của người dùng: mọi thứ không nằm trong `.eide/`, `.git/` và không phải tệp
        # quản trị. Đây là thứ họ sẽ nhớ ra đầu tiên nếu mất, nên đếm riêng.
        bo_qua = {".eide", ".git"}
        nguoi_byte = nguoi_tep = 0
        for x in g.iterdir():
            if x.name in bo_qua or x.name in {TEN_TEP, "EIDE.md"}:
                continue
            nguoi_byte += _co(x)
            nguoi_tep += 1 if x.is_file() else sum(1 for _ in x.rglob("*") if _.is_file())

        tong = {h: sum(m["byte"] for m in muc if m["hang"] == h)
                for h in ("ben", "dung_lai_duoc", "tam")}

        d: dict[str, Any] = {
            "eide": {
                "luoc_do": PHIEN_BAN_LUOC_DO,
                "ghi_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "ghi_boi": "EIDE v3",
            },
            "du_an": {
                "ten": ten or g.name,
                "thu_muc_luc_ghi": str(g),
            },
            "du_lieu": {
                "muc": muc,
                "tong_byte": {**tong, "tep_cua_nguoi": nguoi_byte},
                "so_tep_cua_nguoi": nguoi_tep,
            },
            "chep_di_the_nao": [
                "Chép CẢ thư mục này là mang cả dự án — không có gì nằm ngoài nó.",
                "Muốn gọn: bỏ mọi mục hạng `dung_lai_duoc` và `tam`. Chúng dựng lại được.",
                "TUYỆT ĐỐI giữ mọi mục hạng `ben`: sổ cái, kho, changeset, blob, EIDE.md, .git.",
                "Không đổi tên thư mục giữa chừng cũng được — dữ liệu không ghim đường dẫn "
                "tuyệt đối; trường `thu_muc_luc_ghi` chỉ để đối chiếu, không ai đọc nó để chạy.",
            ],
        }
        d["du_an"].update(self._tu_kho(store))
        d["lich_su"] = self._tu_so_cai(ledger)
        if eide_md is not None:
            try:
                d["du_an"]["bo_nho_dai_han_dong"] = len(
                    (g / "EIDE.md").read_text("utf-8").splitlines())
            except OSError:
                pass
        return d

    # ---------------------------------------------------------------- nguồn số
    def _tu_kho(self, store: Any) -> dict[str, Any]:
        """Đếm hiện vật theo loại. Đọc thẳng SQLite nếu không có `store` — để một công cụ
        ngoài EIDE cũng dựng lại được tệp này."""
        ra: dict[str, Any] = {}
        db = self.goc / ".eide" / "store.sqlite"
        if not db.exists():
            return ra
        try:
            c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            ra["hien_vat"] = {
                t: n for t, n in c.execute(
                    "select type, count(*) from artefacts where deleted=0 group by type")}
            hc = c.execute(
                "select id from artefacts where type='passport' and deleted=0 limit 1"
            ).fetchone()
            ra["ho_chieu_chip"] = hc[0] if hc else None
            c.close()
        except sqlite3.Error as e:
            ra["kho_loi"] = str(e)
        return ra

    def _tu_so_cai(self, ledger: Any) -> dict[str, Any]:
        p = self.goc / ".eide" / "ledger.jsonl"
        cs = self.goc / ".eide" / "changesets.jsonl"
        ra: dict[str, Any] = {
            "su_kien": sum(1 for _ in p.open("rb")) if p.exists() else 0,
            "changeset": sum(1 for _ in cs.open("rb")) if cs.exists() else 0,
            "phien": sum(1 for _ in (self.goc / ".eide/sessions").iterdir())
            if (self.goc / ".eide/sessions").is_dir() else 0,
        }
        if ledger is not None:
            try:
                ok, vi = ledger.verify()
                ra["so_cai_toan_ven"] = bool(ok)
                ra["so_cai_noi"] = vi
            except Exception as e:                                     # noqa: BLE001
                ra["so_cai_toan_ven"] = None
                ra["so_cai_noi"] = f"chưa kiểm được: {e}"
        return ra

    # ---------------------------------------------------------------- ghi / đọc
    def ghi(self, **kw: Any) -> Path:
        """Ghi `du-an.json`. Không bao giờ làm hỏng lượt chạy: lỗi ghi thì bỏ qua.

        Tệp này là tiện ích đọc nhanh, không phải nguồn sự thật — để nó chặn được một lượt
        làm việc thì cái giá cao hơn cái lợi.
        """
        p = self.goc / TEN_TEP
        try:
            p.write_text(json.dumps(self.dung(**kw), ensure_ascii=False, indent=1) + "\n",
                         "utf-8")
        except OSError:
            pass
        return p

    @staticmethod
    def doc(goc: Path) -> dict[str, Any] | None:
        p = goc / TEN_TEP
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text("utf-8"))
        except (OSError, ValueError):
            return None


def can_chep(goc: Path) -> list[str]:
    """Danh sách đường dẫn PHẢI mang theo khi chép dự án đi nơi khác.

    Dùng cho một lệnh sao lưu, hoặc cho người muốn chép tay mà không phải nhớ.
    """
    return [d for d, h, _ in HANG if h == "ben"] + [
        x.name for x in goc.iterdir()
        if x.name not in {".eide", ".git", TEN_TEP, "EIDE.md"}]


def bo_duoc(goc: Path) -> list[tuple[str, int]]:
    """Đường dẫn bỏ được khi chép, kèm số byte tiết kiệm — để người quyết bằng SỐ."""
    return [(d, _co(goc / d)) for d, h, _ in HANG
            if h in ("dung_lai_duoc", "tam") and (goc / d).exists()]
