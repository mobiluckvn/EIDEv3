# -*- coding: utf-8 -*-
"""Thu gọn nhật ký lời gọi mô hình mà KHÔNG cắt nội dung.

Vì sao cần: mỗi lượt gửi lại cả đoạn hội thoại đã có, nên tệp thô phình theo bình phương số
lượt. Phiên sinh viên 450 lời gọi để lại 74 MB; nén gzip thẳng chỉ xuống 26 MB vì cửa sổ nén
32 KB không bắt được những đoạn lặp cách nhau rất xa.

Ba phép thu gọn, không phép nào bỏ dữ liệu:

1. `system` (11 KB) và `cong_cu_thay_duoc` (1,2 KB) giống nhau ở hầu hết lời gọi -> lưu MỘT
   lần vào tệp riêng, mỗi lời gọi giữ một mã băm trỏ tới.
2. `messages` của lời gọi thứ n gần như luôn là phần mở rộng của lời gọi thứ n-1 -> chỉ giữ
   phần ĐUÔI mới, kèm số phần tử chung với lượt trước.
3. Phần `nhan` (mô hình trả về) giữ NGUYÊN VĂN, không chạm.

Dựng lại nguyên trạng: xem `doc_lai()` ở cuối tệp này.

Chạy:
    .venv/bin/python tools/thu_gon_nhat_ky_llm.py <thư mục llm> <thư mục ra>
"""

from __future__ import annotations

import gzip
import hashlib
import json
import pathlib
import sys


def _bam(x: object) -> str:
    return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True)
                          .encode()).hexdigest()[:16]


def thu_gon(vao: pathlib.Path, ra: pathlib.Path) -> dict:
    ra.mkdir(parents=True, exist_ok=True)

    ban_dung: dict[str, object] = {}   # mã băm -> nội dung, lưu một lần
    truoc: list = []                   # messages của lượt trước, để tính phần mới
    so_vao = so_ra = 0

    with gzip.open(ra / "loi-goi-mo-hinh.jsonl.gz", "wt", encoding="utf-8",
                   compresslevel=9) as f:
        for tep in sorted(vao.glob("*.jsonl")):
            for dong in tep.read_text("utf-8", errors="replace").splitlines():
                if not dong.strip():
                    continue
                so_vao += len(dong)
                try:
                    o = json.loads(dong)
                except ValueError:
                    f.write(dong + "\n")   # không đọc được thì giữ nguyên, đừng bỏ
                    continue

                gui = o.get("gui") or {}

                # 1. Lời nhắc hệ thống và danh sách công cụ: lưu một lần
                for khoa in ("system", "cong_cu_thay_duoc"):
                    if khoa in gui:
                        ma = _bam(gui[khoa])
                        ban_dung.setdefault(ma, gui[khoa])
                        gui[khoa] = {"$tro_toi": ma}

                # 2. messages: chỉ giữ phần đuôi mới so với lượt trước
                msgs = gui.get("messages")
                if isinstance(msgs, list):
                    chung = 0
                    for a, b in zip(truoc, msgs):
                        if a != b:
                            break
                        chung += 1
                    gui["messages"] = {"$dung_lai": chung, "$moi": msgs[chung:]}
                    truoc = msgs

                r = json.dumps(o, ensure_ascii=False)
                so_ra += len(r)
                f.write(r + "\n")

    (ra / "ban-dung-mot-lan.json").write_text(
        json.dumps(ban_dung, ensure_ascii=False, indent=1), encoding="utf-8")

    return {"byte_vao": so_vao, "byte_ra": so_ra, "so_ban_dung": len(ban_dung)}


def doc_lai(ra: pathlib.Path):
    """Dựng lại từng lời gọi nguyên trạng. Đây là phép kiểm rằng thu gọn không mất gì."""
    ban_dung = json.loads((ra / "ban-dung-mot-lan.json").read_text("utf-8"))
    truoc: list = []
    with gzip.open(ra / "loi-goi-mo-hinh.jsonl.gz", "rt", encoding="utf-8") as f:
        for dong in f:
            if not dong.strip():
                continue
            o = json.loads(dong)
            gui = o.get("gui") or {}
            for khoa in ("system", "cong_cu_thay_duoc"):
                v = gui.get(khoa)
                if isinstance(v, dict) and "$tro_toi" in v:
                    gui[khoa] = ban_dung[v["$tro_toi"]]
            m = gui.get("messages")
            if isinstance(m, dict) and "$moi" in m:
                day_du = truoc[:m["$dung_lai"]] + m["$moi"]
                gui["messages"] = day_du
                truoc = day_du
            yield o


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    kq = thu_gon(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]))
    print(f"vào {kq['byte_vao']:,} B -> ra {kq['byte_ra']:,} B trước khi nén "
          f"({kq['byte_ra'] / max(kq['byte_vao'], 1):.1%}) · "
          f"{kq['so_ban_dung']} bản dùng một lần")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
