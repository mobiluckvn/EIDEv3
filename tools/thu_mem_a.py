#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm MEM-A qua giao diện thật — phong bì kết quả, blob, đồng hồ ngữ cảnh, C1.

    python tools/thu_mem_a.py

Điều bài này đo, nói một câu: **một phiên thật với tệp thật có giữ được cửa sổ không, và
có mất gì không.** Ca đơn vị đã canh từng mảnh; ở đây đo cả đường, với mô hình thật đọc
kết quả đã cắt và phải tự tìm đường đọc tiếp.

Happy: tệp 3 000 dòng · grep 900 kết quả · đồng hồ ngữ cảnh trên thanh trạng thái.
Unhappy: blob đã mất · ref bịa · blob.read làm cửa sau nhét cả tệp · C1 chạy hai lần.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien        # noqa: E402

XANH, HET = "\033[92m", "\033[0m"


def chay(du_an: pathlib.Path) -> int:
    b = Bo()
    g = GiaoDien(du_an)
    print("Mở app…")
    subprocess.run(["open", str(REPO / "ui/EIDEApp/EIDE.app")], check=True)
    # Lần mở đầu sau khi dựng lại, macOS xác thực chữ ký — chờ rộng tay hơn 25 s.
    g.san_sang(60)
    print(f"{XANH}Kênh kiểm thử giao diện đã mở{HET}\n")

    from eide.memory import boc_ket_qua, c1
    from eide.tools import build_registry
    reg = build_registry()
    ctx = _ctx(du_an)

    # ================================================================== HAPPY
    b.phan("A · TỆP 3 000 DÒNG KHÔNG ĐƯỢC NUỐT CỬA SỔ (MEM01)")
    r = reg.run("fs.read", {"path": "drv_i2c.c"}, ctx)
    b.kiem("Đọc được tệp", r.ok, f"{r.data.get('lines_total')} dòng" if r.ok else str(r.error))

    env = boc_ket_qua(tool="fs.read", call_id="c1", ket_qua=r,
                      args={"path": "drv_i2c.c"}, blobs=ctx.history.blobs)
    b.kiem("Phong bì cắt xuống 60 dòng đầu",
           env.truncated and len(env.data["content"].splitlines()) == 60,
           f"{len(env.data['content'].splitlines())} dòng vào ngữ cảnh")
    b.kiem("Giảm ít nhất một bậc độ lớn",
           env.shown_tokens * 10 < env.full_tokens,
           f"{env.full_tokens} → {env.shown_tokens} token")
    b.kiem("Có bảng đề mục để mô hình biết đọc đoạn nào",
           any("i2c_init" in x for x in env.data.get("de_muc", [])),
           "; ".join(env.data.get("de_muc", [])[:3]))
    b.kiem("Phần dư nằm trong blob, NGUYÊN VĂN",
           bool(env.blob_ref)
           and ctx.history.blobs.get(env.blob_ref.split(":")[-1]) is not None,
           env.blob_ref or "không có blob")

    b.buoc("Mô hình đọc lại được phần đã cắt")
    rr = reg.run("blob.read", {"ref": env.blob_ref, "tu": 0, "den": 500}, ctx)
    b.kiem("blob.read trả đúng nguyên văn",
           rr.ok and "drv_i2c.c" in rr.data["noi_dung"],
           rr.data["noi_dung"][:80] if rr.ok else str(rr.error))
    b.kiem("Nói rõ còn bao nhiêu và cách lấy tiếp",
           rr.ok and "Gọi tiếp với tu=" in rr.data["note_vi"],
           rr.data.get("note_vi", "")[:90] if rr.ok else "")

    b.phan("B · TÌM KIẾM 900 KẾT QUẢ (MEM02)")
    r = reg.run("fs.grep", {"pattern": "dòng"}, ctx)
    env = boc_ket_qua(tool="fs.grep", call_id="c2", ket_qua=r, args={},
                      blobs=ctx.history.blobs)
    b.kiem("Chỉ 80 dòng khớp vào ngữ cảnh",
           len(env.data.get("hits", [])) <= 80,
           f"{len(env.data.get('hits', []))} dòng")
    b.kiem("Vẫn ĐẾM đủ tổng — người cần biết còn bao nhiêu",
           env.data.get("count", 0) >= len(env.data.get("hits", [])),
           f"tổng {env.data.get('count')}")

    b.phan("C · ĐỒNG HỒ NGỮ CẢNH TRÊN THANH TRẠNG THÁI (MEM-02)")
    g.go("Dự án này có gì rồi? Đọc tệp drv_i2c.c giúp mình xem nó làm gì.")
    a = g.doi_xong(300)
    nc = a["trang_thai"].get("ngu_canh") or {}
    b.kiem("Thanh trạng thái có đồng hồ ngữ cảnh", bool(nc.get("cua_so")),
           f"{nc.get('tong')}/{nc.get('cua_so')} token · mức {nc.get('muc')}")
    if nc:
        ten = {k["ten"] for k in nc.get("khoi", [])}
        b.kiem("Đủ các khối chính + dự trữ",
               {"constitution", "inventory", "transcript"} <= ten
               and any("dự trữ" in t for t in ten),
               ", ".join(sorted(ten)))
        b.kiem("Không khối nào vượt trần của nó (P8)",
               not [k for k in nc["khoi"] if k.get("vuot")],
               "; ".join(f"{k['ten']}={k['token']}/{k['tran']}"
                         for k in nc["khoi"] if k.get("vuot")) or "không khối nào vượt")
        b.kiem("Dự trữ 20 % được giữ nguyên",
               nc.get("kha_dung", 0) == int(nc["cua_so"] * 0.8),
               f"dùng được {nc.get('kha_dung')} / cửa sổ {nc.get('cua_so')}")

    b.kiem("Tác tử vẫn trả lời được dù kết quả bị cắt",
           len(a["loi_tac_tu_cuoi"]) > 80
           and ("i2c" in a["loi_tac_tu_cuoi"].lower() or "I2C" in a["loi_tac_tu_cuoi"]),
           a["loi_tac_tu_cuoi"][:140])

    # ================================================================== UNHAPPY
    b.phan("D · SÁU ĐƯỜNG HỎNG")

    b.buoc("1. Ref bịa ra")
    r = reg.run("blob.read", {"ref": "blob:sha256:" + "0" * 64}, ctx)
    b.kiem("Từ chối và dặn gọi lại công cụ gốc, không đoán",
           not r.ok and "đoán" in r.error.hint_for_agent,
           r.error.message_vi[:110] if r.error else "lọt!")

    b.buoc("2. blob.read làm cửa sau nhét cả tệp vào ngữ cảnh")
    to = "x" * 200_000
    bam = ctx.history.blobs.put(to)
    r = reg.run("blob.read", {"ref": f"blob:sha256:{bam}"}, ctx)
    b.kiem("Có trần cứng, không cho lấy hết một lần",
           r.ok and len(r.data["noi_dung"]) <= 60_000,
           f"{len(r.data['noi_dung'])} ký tự / tổng {r.data['tong_ky_tu']}" if r.ok else "")
    b.kiem("Vẫn nói rõ còn bao nhiêu",
           r.ok and "Gọi tiếp" in r.data["note_vi"],
           r.data.get("note_vi", "")[:80] if r.ok else "")

    b.buoc("3. Lỗi công cụ KHÔNG bị cắt (§B3)")
    r = reg.run("fs.read", {"path": "khong-co-tep-nay.c"}, ctx)
    env = boc_ket_qua(tool="fs.read", call_id="c9", ket_qua=r, args={},
                      blobs=ctx.history.blobs)
    m = env.to_model()
    b.kiem("Giữ đủ bốn trường để mô hình đổi hướng",
           not env.truncated and m.get("code") == "E1003"
           and m.get("hint_for_agent") and m.get("alternatives"),
           f"{m.get('code')} · {str(m.get('alternatives'))[:60]}")

    b.buoc("4. C1 chạy hai lần liên tiếp")
    ms = _tin_nhan(12)
    c1(ms)
    n = len(ms)
    bc2 = c1(ms)
    b.kiem("Lần hai không stub lại và không mất message nào",
           bc2["stub_qua_han"] == 0 and len(ms) == n,
           f"{n} message, lần hai stub thêm {bc2['stub_qua_han']}")

    b.buoc("5. C1 không được đụng vào kết quả lượt gần nhất")
    ms = _tin_nhan(12)
    c1(ms)
    b.kiem("Kết quả mới nhất còn nguyên văn",
           not ms[-1].get("_stub"),
           "còn nguyên" if not ms[-1].get("_stub") else "đã bị stub — sai")

    b.buoc("6. Thu gọn rồi vẫn phải nói được đường đọc lại")
    stub = next((m for m in ms if m.get("_stub")), None)
    b.kiem("Mỗi stub mang blob_ref và tên công cụ đọc lại",
           stub is not None and "blob.read" in stub["result"]["_da_thu_gon"],
           stub["result"]["_da_thu_gon"][:110] if stub else "không có stub nào")

    return b.tong()


def _tin_nhan(n_luot: int) -> list[dict]:
    ms: list[dict] = []
    for l in range(n_luot):
        ms.append({"role": "user", "text": f"việc thứ {l}"})
        ms.append({"role": "tool", "tool_call_id": f"c{l}", "tool": "fs.read",
                   "result": {"ok": True, "data": {"path": f"f{l}.c", "bytes": 100,
                                                   "content": "nội dung " * 200}},
                   "envelope": {"summary_line": f"fs.read f{l}.c",
                                "blob_ref": f"blob:sha256:{l:064d}"}})
    return ms


def _ctx(du_an):
    from eide import Config
    from eide.history import History
    from eide.ids import IdGen
    from eide.protocol.ledger import Ledger
    from eide.store import EideMd, Store
    from eide.tools import build_registry

    class C:
        config = Config.for_project(du_an)
        store = Store(config.paths.store_db)
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-mem-a")
        registry = build_registry()
        ids = IdGen(config.paths.state_dir)
        history = History(paths=config.paths, store=store,
                          ledger=Ledger(config.paths.ledger), ids=ids)
        run_id = "run-thu"
        tai_lieu: dict = {}
        pending_cards: list = []
        loi_nguoi_trong_phien: list = []
        awaiting_human = False
        def emit(self, c): pass
    return C()


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    d = (REPO / "du-lieu/thu-nghiem-mem-a").resolve()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)

    # Tệp 3 000 dòng có hàm và hằng số thật, để bảng đề mục có cái để bắt.
    dong = ["#include <stdint.h>", "#define I2C_TIMEOUT_MS 50", ""]
    dong += ["static int i2c_init(void) {", "    return 0;", "}", ""]
    dong += ["void i2c_write(uint8_t addr, uint8_t reg) {"]
    dong += [f"    // dòng đệm thứ {i} của trình điều khiển I2C" for i in range(2980)]
    dong += ["}", ""]
    dong += ["int i2c_read(uint8_t addr) {", "    return -1;", "}"]
    (d / "drv_i2c.c").write_text("\n".join(dong) + "\n", "utf-8")
    (d / "ghi-chu.md").write_text("# Trình điều khiển I2C\n\nCho cảm biến nhiệt.\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
