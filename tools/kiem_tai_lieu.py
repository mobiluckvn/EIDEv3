#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dò chỗ tài liệu thiết kế nói khác mã.

    .venv/bin/python tools/kiem_tai_lieu.py [--im]

Bốn phép dò, tất cả đều đối chiếu với **mã đang chạy**, không với trí nhớ:

1. **Tên công cụ** tài liệu nhắc tới có trong kho đăng ký không.
2. **Đường dẫn mã** tài liệu trỏ tới có tồn tại không.
3. **Con số đếm được** (số công cụ, số UICommand, số HumanAct, số bề mặt, số subagent, số
   skill, số cổng, số ca đơn vị) — tài liệu ghi bao nhiêu, mã có bao nhiêu.
4. **Mã lỗi** (`E1234`) tài liệu nhắc tới có được sinh ra ở đâu trong mã không.

Vì sao đáng một bộ dò riêng thay vì đọc tay: tài liệu thiết kế của dự án này dài hơn 8000
dòng. Đọc tay thì mỗi lần sửa mã phải đọc lại tất cả, nên thực tế là không ai đọc lại — và
tài liệu trôi khỏi mã một cách lặng lẽ. Một con số sai trong tài liệu thiết kế còn tệ hơn
không có con số: nó **nghe hợp lý**, không ai kiểm, và nó làm mọi con số khác cùng trang mất
giá.

Bộ dò này KHÔNG đọc hiểu nội dung. Nó chỉ bắt được loại lệch **kiểm được bằng máy** — tên,
đường dẫn, con số, mã lỗi. Phần "tài liệu mô tả đúng cách hệ thống hoạt động không" thì vẫn
phải đọc, và nó nói rõ điều đó thay vì để một bảng xanh nói hộ.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

TAI_LIEU = sorted(
    list((REPO / "docs/review-v3/docs/md").glob("*.md"))
    + list((REPO / "docs/md").glob("*.md"))
    + [REPO / "README.md"])

# Tài liệu lịch sử: cố ý nói về bản CŨ, nên lệch với mã hiện tại là ĐÚNG. Không dò tên công
# cụ và đường dẫn ở đây — dò thì sinh ra một đống báo động giả, và một bảng đầy báo động giả
# thì không ai đọc.
LICH_SU = {"EIDE-AAD-33_Kien_truc_Tac_tu_Ky_su_Nhung_v1.0.md",
           "EIDE-AAD-33_v2.0_Kien_truc_Tac_tu_theo_Vong_lap.md",
           "EIDE-AGD-32_Thiet_ke_Tac_tu_Ky_su_Nhung_v1.4.md",
           "EIDE-UIP-34_Giao_thuc_Dieu_khien_Giao_dien_v1.0.md",
           "EIDE-DEV-LOG.md",          # nhật ký: mỗi mục là một lát cắt của quá khứ
           "EIDE-GAP-44_Ra_soat_MEM_ING.md"}

# Tên trông như công cụ nhưng không phải — bỏ qua để khỏi báo động giả.
KHONG_PHAI_CONG_CU = {
    "eide.md", "package.json", "config.load", "self.registry", "ctx.store", "ctx.ledger",
    "ctx.config", "ctx.history", "os.path", "json.dumps", "e.message", "a.b", "x.y",
}


# Dấu hiệu một dòng đang NÓI VỀ một cái tên đã bỏ, chứ không dùng nó.
_KHAI_DA_BO = ("lúc thiết kế", "chưa làm", "không làm", "đã bỏ", "bỏ |", "đổi tên",
               "không có trong kho", "thay bằng", "cố ý không")


def _dem_ma() -> dict[str, int]:
    """Số đếm được từ MÃ — mỗi con số một cách đếm, không cái nào chép của cái nào."""
    from eide import subagent as sa
    from eide.protocol.humanact import HUMAN_ACT_KINDS
    from eide.protocol.uicommand import UI_COMMANDS
    from eide.surfaces import SURFACES

    ts = _tat_ca_cong_cu()
    pol = (REPO / "src/eide/policy/policy.yaml").read_text("utf-8")
    return {
        "công cụ": len(ts),
        "nhóm công cụ": len({t.group for t in ts}),
        "UICommand": len(UI_COMMANDS),
        "HumanAct": len(HUMAN_ACT_KINDS),
        "bề mặt": len(SURFACES),
        "subagent": len(sa.SUBAGENT),
        "skill": len(list((REPO / "src/eide/skills").glob("*.md"))),
        "cổng": len(set(re.findall(r"G-[A-Z]+", pol))),
    }


def _tat_ca_cong_cu() -> list:
    """Kể cả công cụ nằm sau CỜ TÍNH NĂNG.

    `sch.*` chỉ được đăng ký khi `EIDE_FEATURE_SCHEMATIC=1`. Dò bằng kho đăng ký mặc định
    thì chín công cụ sơ đồ bị báo là "không tồn tại" — một báo động sai, và một bảng đầy báo
    động sai thì không ai đọc tới dòng thứ ba.
    """
    import os

    from eide.tools import build_registry

    cu = os.environ.get("EIDE_FEATURE_SCHEMATIC")
    os.environ["EIDE_FEATURE_SCHEMATIC"] = "1"
    try:
        r = build_registry()
        return list(r.all() if hasattr(r, "all") else r.tools.values())
    finally:
        if cu is None:
            os.environ.pop("EIDE_FEATURE_SCHEMATIC", None)
        else:
            os.environ["EIDE_FEATURE_SCHEMATIC"] = cu


def _cong_cu_that() -> set[str]:
    return {t.name for t in _tat_ca_cong_cu()}


def _ma_loi_that() -> set[str]:
    ra: set[str] = set()
    for p in (REPO / "src").rglob("*.py"):
        ra |= set(re.findall(r'"(E\d{4})"', p.read_text("utf-8", errors="replace")))
    return ra


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--im", action="store_true", help="chỉ in tổng kết")
    a = ap.parse_args()

    that = _cong_cu_that()
    ma_loi = _ma_loi_that()
    dem = _dem_ma()
    lech: list[tuple[str, str, str]] = []

    bo_qua = 0
    for p in TAI_LIEU:
        t = p.read_text("utf-8", errors="replace")
        ten = p.name
        ngan = str(p.relative_to(REPO))
        # Dòng nào TỰ KHAI rằng cái tên ấy không còn thì không phải một chỗ lệch.
        #
        # Tài liệu thiết kế phải nhắc tên cũ để nói nó đã đổi thành gì — đó là giá trị của
        # bảng ánh xạ, không phải lỗi. Bản đầu của bộ dò báo bảy chỗ như vậy, và bảy báo động
        # giả đủ để người đọc bỏ qua cả bảng.
        dong_cu = {d for d in t.splitlines()
                   if any(k in d.lower() for k in _KHAI_DA_BO)}
        cu_trong_dong = set()
        for d in dong_cu:
            cu_trong_dong |= set(re.findall(r"`([a-z_]+\.[a-z_]+)`", d))
        # Vùng được đánh dấu là LỊCH SỬ: bảng lúc thiết kế phải giữ nguyên làm hồ sơ, nhưng
        # nó nói về một bản cũ nên không phải chỗ lệch. Dấu vùng rõ ràng hơn dấu theo dòng —
        # một cái bảng không có chỗ nào để nhét chữ "lúc thiết kế" vào từng hàng.
        for vung in re.findall(r"<!--\s*lich-su\s*-->(.*?)<!--\s*/lich-su\s*-->", t, re.S):
            cu_trong_dong |= set(re.findall(r"`?([a-z_]+\.[a-z_*\\]+)`?", vung))
        # Bảng ánh xạ "tên cũ → tên nay": chỉ CỘT TRÁI là tên cũ; cột phải là tên hiện tại và
        # PHẢI được kiểm. Đọc theo cấu trúc bảng thay vì đuổi theo cách diễn đạt của cột lý
        # do — đuổi theo từ ngữ là cách chắc chắn để bỏ sót một cách nói mới.
        for vung in re.findall(r"<!--\s*ten-cu\s*-->(.*?)<!--\s*/ten-cu\s*-->", t, re.S):
            for hang in vung.splitlines():
                # Bỏ tiền tố khối trích dẫn trước khi tách cột: `> | a | b |` mà tách thẳng
                # thì cột đầu là dấu `>`, và phép lọc đi tìm tên trong đúng chỗ không có tên.
                hang = hang.lstrip("> ").strip()
                o = [x for x in hang.split("|") if x.strip()]
                if o:
                    cu_trong_dong |= set(re.findall(r"`([a-z_]+\.[a-z_*\\]+)`", o[0]))

        if ten not in LICH_SU:
            # 1. Tên công cụ trong dấu nháy ngược.
            for m in set(re.findall(r"`([a-z_]+\.[a-z_]+)`", t)):
                if m in cu_trong_dong and m not in that:
                    bo_qua += 1
                    continue
                if m in that or m in KHONG_PHAI_CONG_CU:
                    continue
                if m.rsplit(".", 1)[1] in {"py", "md", "c", "h", "json", "yaml", "yml",
                                           "swift", "jsonl", "sqlite", "ino", "bin", "elf",
                                           "hex", "net", "csv", "png", "pdf", "txt", "ld",
                                           "ioc", "dts", "map", "xlsx", "docx", "sh"}:
                    continue
                if m.split(".")[0] in {"fs", "store", "fact", "doc", "ckm", "target", "build",
                                       "sim", "test", "plan", "tool", "memory", "snapshot",
                                       "history", "branch", "ledger", "khoi", "eda", "board",
                                       "passport", "ingest", "blob", "env", "code", "asset",
                                       "diagram", "task", "skill", "ui", "config",
                                       "inventory", "stale", "sch"}:
                    lech.append((ngan, "công cụ không có trong kho đăng ký", m))

            # 2. Đường dẫn mã.
            for m in set(re.findall(r"`((?:src|ui|tools|tests|docs)/[\w./-]+)`", t)):
                if not (REPO / m).exists():
                    lech.append((ngan, "đường dẫn không tồn tại", m))

        # 3. Mã lỗi — dò cả tài liệu lịch sử, vì một mã lỗi biến mất là tin đáng biết.
        for m in set(re.findall(r"`(E\d{4})`", t)):
            if m not in ma_loi:
                lech.append((ngan, "mã lỗi không còn trong mã", m))

    # 4. Con số đếm được — LIỆT KÊ chỗ nói, không tự phán đúng/sai.
    #
    # Bản đầu tự chấm và nó báo sai ngay: "14 công cụ" trong README là số công cụ của MỘT
    # tác tử con, không phải tổng. Một mẫu regex không đọc được ngữ cảnh ấy. Nên phép này
    # chỉ dọn sẵn bàn — nó chỉ ra mọi chỗ tài liệu nêu một con số đếm được, kèm con số mã
    # thật có, rồi để người đọc quyết. Tự phán ở đây là đẻ thêm báo động giả.
    so: list[tuple[str, str, str, int]] = []
    MAU = {"công cụ": r"(\d+)\s*công cụ", "UICommand": r"(\d+)\s*UICommand",
           "HumanAct": r"(\d+)\s*(?:loại\s*)?HumanAct", "bề mặt": r"(\d+)\s*bề mặt",
           "subagent": r"(\d+)\s*(?:subagent|tác tử con)", "skill": r"(\d+)\s*skill",
           "cổng": r"(\d+)\s*cổng(?:\s*duyệt)?"}
    for ten, mau in MAU.items():
        n = dem[ten]
        for p in TAI_LIEU:
            if p.name in LICH_SU:
                continue
            for m in re.finditer(mau, p.read_text("utf-8", errors="replace")):
                if int(m.group(1)) != n:
                    so.append((str(p.relative_to(REPO)), ten, m.group(1), n))

    if not a.im:
        print(f"Số đếm được từ MÃ: " + " · ".join(f"{k} {v}" for k, v in dem.items()))
        print(f"Tài liệu dò: {len(TAI_LIEU)} tệp "
              f"({len([p for p in TAI_LIEU if p.name in LICH_SU])} tệp lịch sử — "
              "chỉ dò mã lỗi)\n")
        for f, loai, gi in sorted(lech):
            print(f"  ✗ {f:58} {loai:38} {gi}")
        if so:
            print("\n  Con số KHÁC với mã — đọc kỹ, có thể đúng (ví dụ số công cụ của MỘT "
                  "tác tử con, không phải tổng):")
            for f, ten, ghi, that_su in sorted(so):
                print(f"  ? {f:58} {'số ' + ten:30} tài liệu {ghi} · mã {that_su}")

    print(f"\nTổng: {len(lech)} chỗ LỆCH CHẮC CHẮN (tên · đường dẫn · mã lỗi) "
          f"· {len(so)} con số cần đọc lại"
          + (f" · {bo_qua} tên cũ được tài liệu TỰ KHAI là đã bỏ (không tính là lệch)"
             if bo_qua else ""))
    print("Bộ dò này KHÔNG đọc hiểu nội dung — nó bắt tên, đường dẫn, con số, mã lỗi. "
          "Phần “tài liệu mô tả ĐÚNG cách hệ thống hoạt động không” vẫn phải đọc.")
    return 1 if lech else 0


if __name__ == "__main__":
    raise SystemExit(main())
