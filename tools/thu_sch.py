#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm sinh sơ đồ nguyên lý qua giao diện thật — EIDE-SCH-44, ca SCH01–04, 14, 16, 18.

    EIDE_FEATURE_SCHEMATIC=1 python tools/thu_sch.py

**Bộ này cần cờ `features.schematic` BẬT.** Cờ tắt thì `sch.*` không được đăng ký, và bộ sẽ
nói thẳng điều đó rồi dừng — chứ không báo "đạt 0/0".

Điều bộ này canh, một câu: **phép kiểm đẳng cấu phải đi qua hai đường độc lập.** Nếu
`sch.netlist` viết `.net` từ cây rồi so với `flatten(cây)` thì nó so chính mình với chính
mình — luôn đạt, và một phép kiểm luôn đạt tệ hơn không có phép kiểm. Vế thứ hai ở đây là
**đọc lại tệp SKiDL** bằng `ast`, tức đi qua một hiện vật mà mô hình có thể đã sửa.

Happy: soạn tệp SKiDL từ cây · sinh netlist và kiểm khớp · ký hiệu sinh từ Fact có ghi nguồn
· tác tử thật sinh sơ đồ qua hội thoại.

Unhappy (bảy đường): mô hình bịa net trong tệp · tệp lỗi cú pháp · thiếu pinout · cây vi phạm
bất biến · chưa đủ tiền đề · gọi sch.netlist trước sch.compose · đề nghị cài KiCad.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien, PathsThu        # noqa: E402

XANH, DO, HET = "\033[92m", "\033[91m", "\033[0m"
EX = {"summary": "sinh sơ đồ", "why": "để người xem được mạch dưới dạng sơ đồ nguyên lý",
      "sources": [], "diff_prev": "—", "next": "—", "confidence": "VANG"}

CHAN = [("7", "VCC", ""), ("8", "GND", ""), ("27", "PC4", "SDA, ADC4"),
        ("28", "PC5", "SCL, ADC5")]


def _chen_net_bia(nguon: str) -> str:
    """Chèn một net KHÔNG có trong bản đồ vào thân `mach()` — giả lập mô hình sửa tệp.

    Chèn theo CẤU TRÚC (ngay sau dòng `def mach():` và docstring của nó) thay vì theo một
    mốc chuỗi. Lần đầu bộ này dùng mốc `"khoi_board_MOD_MCU(n_3V3)"`, rồi khối có thêm một
    Port nên lời gọi đổi thành hai tham số — mốc không khớp, tệp KHÔNG bị sửa, và ca đo báo
    ĐẠT trong khi nó chẳng kiểm gì. Một ca đo đậu vì không làm gì là ca đo tệ nhất.
    """
    dong = nguon.splitlines()
    for i, l in enumerate(dong):
        if l.startswith("def mach():"):
            j = i + 1
            if j < len(dong) and dong[j].strip().startswith('"""'):
                j += 1
            them = ['    bia = Net("VBUS_BIA")',
                    '    ub_bia = Part("x", "y", ref="U1")',
                    '    bia += ub_bia["7"]']
            return "\n".join(dong[:j] + them + dong[j:]) + "\n"
    raise AssertionError("không tìm thấy def mach() để chèn — tệp không như mong đợi")


def _ctx(du_an):
    from eide import Config
    from eide.config import Features
    from eide.history import History
    from eide.ids import IdGen
    from eide.protocol.ledger import Ledger
    from eide.store import EideMd, Store
    from eide.tools import build_registry

    class C:
        config = Config.for_project(du_an)
        paths = PathsThu(du_an)
        store = Store(paths.store_db)
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-sch")
        # Cờ BẬT tường minh: bộ này đo chính tính năng sau cờ.
        registry = build_registry(Features(schematic=True))
        ids = IdGen(paths.state_dir)
        ledger = Ledger(paths.ledger)
        history = History(paths=paths, store=store, ledger=ledger, ids=ids)
        run_id = "run-thu"
        tai_lieu: dict = {}
        pending_cards: list = []
        loi_nguoi_trong_phien: list = []
        awaiting_human = False
        agent = None
        def emit(self, c): pass
    return C()


def chay(du_an: pathlib.Path) -> int:
    b = Bo()
    g = GiaoDien(du_an)
    print("Mở app…")
    subprocess.run(["open", str(REPO / "ui/EIDEApp/EIDE.app")], check=True)
    g.san_sang(60)
    print(f"{XANH}Kênh kiểm thử giao diện đã mở{HET}\n")

    from eide.knowledge import cay as C
    from eide.sch import doc_skidl

    ctx = _ctx(du_an)
    reg = ctx.registry

    def goi(cong_cu, /, **kw):
        if "explain" in (reg.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", EX)
        return reg.run(cong_cu, kw, ctx)

    # ================================================================== dựng mạch
    b.phan("A · DỰNG MẠCH ĐỦ TIỀN ĐỀ")
    ctx.store.apply(artefact_id="DS-328P", type="doc", op="create", author="human",
                    explain=EX, canonical={"ten": "ATmega328P datasheet"})
    for so, ten, af in CHAN:
        ctx.store.put_fact({"fact_id": f"f-{so}", "subject": f"pin:ATmega328P.{so}",
                            "key": "ten", "value": ten, "tier": "VANG", "origin": "extract",
                            "source": {"doc_id": "DS-328P", "page": 13}, "explain": {}})
        if af:
            ctx.store.put_fact({"fact_id": f"fa-{so}", "subject": f"pin:ATmega328P.{so}",
                                "key": "af", "value": af, "tier": "VANG",
                                "origin": "extract",
                                "source": {"doc_id": "DS-328P", "page": 13}, "explain": {}})
    goi("passport.pin", chip="ATmega328P", doc_ids=["DS-328P"])
    goi("ckm.chip_add", chip="ATmega328P", ref="U1")
    goi("ckm.module_set", ma="MOD-PWR", ten="Nguồn 3V3", muc_dich="hạ 5 V xuống 3,3 V",
        linh_kien=["U3"])
    goi("ckm.module_set", ma="MOD-MCU", ten="Vi điều khiển", muc_dich="chạy firmware",
        linh_kien=["U1"])
    goi("ckm.port_set", khoi="MOD-PWR", ten="VOUT", huong="power_out",
        rang_buoc={"i_max": "800 mA"})
    goi("ckm.port_set", khoi="MOD-MCU", ten="VDD", huong="power_in",
        rang_buoc={"v_min": "2,7 V", "v_max": "5,5 V"})
    goi("ckm.net_set", ten="3V3", loai="power", ap_danh_dinh="3,3 V",
        chan=[["U1", "7"], ["U3", "2"]],
        noi_port=[["MOD-PWR", "VOUT"], ["MOD-MCU", "VDD"]])
    goi("ckm.net_set", ten="GND", loai="ground", chan=[["U1", "8"], ["U3", "1"]])
    r = goi("ckm.build")
    b.kiem("Bản đồ đủ tiền đề để sinh sơ đồ",
           r.ok and r.data["du_de_sinh_so_do"] is True,
           r.data["note_vi"][:140] if r.ok else str(r.error.message_vi)[:130])

    b.phan("B · KÝ HIỆU SINH TỪ FACT, CÓ GHI NGUỒN (SCH03)")
    r = goi("sch.symbols")
    b.kiem("Ký hiệu sinh từ Fact pinout cho mọi linh kiện có chân",
           r.ok and r.data["so_sinh_tu_fact"] >= 1,
           r.data["note_vi"][:150] if r.ok else str(r.error.message_vi)[:140])
    p_sym = du_an / "sch/eide-sinh.kicad_sym"
    noi_dung_sym = p_sym.read_text("utf-8") if p_sym.exists() else ""
    b.kiem("Mỗi ký hiệu ghi rõ LẤY CHÂN TỪ ĐÂU (N1 áp vào ký hiệu)",
           "DS-328P trang 13" in noi_dung_sym,
           [l for l in noi_dung_sym.splitlines() if "Description" in l][:1])
    b.kiem("Kiểu chân suy từ hướng Port, chân chưa rõ thì passive không đoán",
           "(pin power_in line" in noi_dung_sym and "(pin passive line" in noi_dung_sym,
           f"{noi_dung_sym.count('(pin ')} chân trong tệp")

    b.phan("C · SOẠN TỆP SKIDL TỪ CÂY (SCH01, SCH04)")
    r = goi("sch.compose")
    b.kiem("Soạn được, mỗi khối một hàm", r.ok and r.data["so_ham"] >= 3,
           r.data["note_vi"][:150] if r.ok else str(r.error.message_vi)[:140])
    p_py = du_an / "sch/mach_skidl.py"
    ng = p_py.read_text("utf-8") if p_py.exists() else ""
    # KHÔNG kẹp vào chữ ký đầy đủ: khối có thêm Port (GND) là chuyện đúng, và một ca đo
    # đỏ vì lý do đúng sẽ bị sửa cho qua thay vì được đọc.
    ky = [l for l in ng.splitlines() if l.startswith("def khoi_")]
    b.kiem("Khối thành hàm có tham số là Port (HIER-45 §7)",
           any("khoi_board_MOD_MCU(" in l and "VDD" in l for l in ky)
           and any("khoi_board_MOD_PWR(" in l and "VOUT" in l for l in ky), ky)
    b.kiem("Chân dùng đều có trong Fact — không bịa chân",
           'U1["7"]' in ng and 'U1["28"]' not in ng,
           "chân xuất hiện: " + ", ".join(sorted({l.split('U1["')[1].split('"')[0]
                                                  for l in ng.splitlines()
                                                  if 'U1["' in l})))
    lan2 = goi("sch.compose")
    b.kiem("Soạn hai lần ra đúng một tệp (SCH18/N3)",
           lan2.ok and p_py.read_text("utf-8") == ng, "xác định")

    b.phan("D · NETLIST VÀ PHÉP KIỂM ĐẲNG CẤU (SCH02)")
    r = goi("sch.netlist")
    b.kiem("Netlist khớp bản đồ mạch",
           r.ok and r.data["dang_cau"]["dat"] is True,
           r.data["note_vi"][:160] if r.ok else str(r.error.message_vi)[:150])
    b.kiem("Phép kiểm nói rõ nó đi qua ĐƯỜNG NÀO — không tự so với chính mình",
           r.ok and "ĐỌC LẠI" in r.data["note_vi"], "có nói")
    p_net = du_an / "sch/mach.net"
    net_txt = p_net.read_text("utf-8") if p_net.exists() else ""
    b.kiem("Tệp .net đúng dạng KiCad và có đủ linh kiện",
           net_txt.startswith("(export") and '(comp (ref "U1")' in net_txt
           and '(node (ref "U1") (pin "7"))' in net_txt,
           f"{net_txt.count('(comp ')} linh kiện · {net_txt.count('(net ')} net")
    b.kiem("KHÔNG ghi tstamp bịa (KiCad dùng nó để khớp linh kiện khi cập nhật PCB)",
           "tstamp" not in net_txt, "sạch")

    b.phan("Đ · TÁC TỬ THẬT SINH SƠ ĐỒ QUA HỘI THOẠI")
    g.go("Mình muốn có sơ đồ nguyên lý của mạch này. Sinh giúp mình, rồi nói rõ đã kiểm "
         "được những gì và chưa kiểm được gì.")
    a = g.doi_xong(420)
    loi = a["loi_tac_tu_cuoi"]
    b.kiem("Tác tử nói được đã kiểm gì / chưa kiểm được gì",
           any(t in loi.lower() for t in ("netlist", "sơ đồ", "skidl")),
           loi[:200])
    b.kiem("Tác tử KHÔNG đề nghị cài KiCad (SCH09)",
           not any(t in loi.lower() for t in ("cài kicad", "install kicad", "tải kicad",
                                              "kicad-cli")),
           loi[:200])

    # ================================================================== UNHAPPY
    b.phan("E · BẢY ĐƯỜNG HỎNG")

    b.buoc("1. Mô hình BỊA một net trong tệp SKiDL (SCH14)")
    goc = p_py.read_text("utf-8")
    p_py.write_text(_chen_net_bia(goc), "utf-8")
    r = goi("sch.netlist")
    b.kiem("Bị bắt, dừng lại, và KHÔNG khuyên sửa tệp cho khớp",
           not r.ok and r.error.code == "E8001"
           and "VBUS_BIA" in r.error.details.get("net_them", {})
           and "Đừng sửa tệp cho khớp" in r.error.hint_for_agent,
           (r.error.message_vi if not r.ok else "lại nhận!")[:170])

    b.buoc("2. Tệp SKiDL lỗi cú pháp")
    p_py.write_text("def mach(:\n  pass\n", "utf-8")
    r = goi("sch.netlist")
    b.kiem("Nói rõ dòng lỗi và KHÔNG đi tiếp",
           not r.ok and r.error.code == "E8001" and "dòng 1" in r.error.message_vi,
           (r.error.message_vi if not r.ok else "lại nhận!")[:150])
    goi("sch.compose")          # dựng lại tệp sạch

    b.buoc("3. Linh kiện chưa có pinout (SCH03/E8002)")
    ctx.store.apply(artefact_id="ckm:chip:U9", type="ckm", op="create",
                    author=f"agent:{ctx.run_id}", explain=EX,
                    canonical={"chip": "ChipLa", "ref": "U9", "ho_chieu": "", "chan": []})
    from eide.knowledge import ckm as K
    K.chieu(ctx.store)
    r = goi("sch.symbols")
    b.kiem("Từ chối kèm tên linh kiện, không bịa chân",
           not r.ok and r.error.code == "E8002" and "U9" in r.error.message_vi,
           (r.error.message_vi if not r.ok else "lại nhận!")[:150])
    ctx.store.apply(artefact_id="ckm:chip:U9", type="ckm", op="delete",
                    author=f"agent:{ctx.run_id}", explain=EX, canonical={})
    K.chieu(ctx.store)

    b.buoc("4. Cây vi phạm bất biến")
    la = next(n for n in C.Cay.doc(ctx.store).nut.values()
              if n.get("kind") == "leaf" and n["canonical"].get("ref") == "U1")
    ctx.store.ckm_dat_port(port_id=f"port:{la['path']}.99", module_id=la["node_id"],
                           ten="99", huong="passive", chan="99")
    r = goi("sch.compose")
    b.kiem("Từ chối vì sơ đồ sinh ra sẽ là một mạch KHÁC",
           not r.ok and r.error.code == "E8005" and "mạch KHÁC" in r.error.message_vi,
           (r.error.message_vi if not r.ok else "lại nhận!")[:160])
    K.chieu(ctx.store)

    b.buoc("5. Bản đồ chưa đủ tiền đề (R3)")
    ctx2 = _ctx(du_an.parent / (du_an.name + "-rong"))
    r = ctx2.registry.run("sch.compose", {"explain": EX}, ctx2)
    b.kiem("Nói thẳng chưa sinh được, và chỉ về sơ đồ khối đang có (mức R3)",
           not r.ok and "mức R3" in r.error.message_vi
           and "diagram.render" in (r.error.alternatives or []),
           (r.error.message_vi if not r.ok else "lại sinh!")[:160])

    b.buoc("6. Gọi sch.netlist trước sch.compose")
    r = ctx2.registry.run("sch.netlist", {"explain": EX}, ctx2)
    b.kiem("Nói rõ gọi gì trước",
           not r.ok and "sch.compose" in (r.error.alternatives or []),
           (r.error.hint_for_agent if not r.ok else "lại chạy!")[:130])

    b.buoc("7. Đề nghị cài KiCad — chốt chặn ở hook Stop (SCH09)")
    from eide.hooks import HookBus
    from eide.hooks.standard import register_standard_hooks

    class CtxStop:
        assumptions: list = []
        assumptions_stated: list = []
        human_edits: list = []
        said_anything = True
        awaiting_human = False
        loi_da_noi = ["Anh cài KiCad rồi mở tệp sch/mach.net nhé."]

    kq = register_standard_hooks(HookBus()).stop(CtxStop())
    b.kiem("Bị chặn, bắt nói lại, và chỉ đường ĐÚNG (sch.export)",
           kq.another_round and "sch.export" in kq.injection,
           kq.reason_vi)

    print()
    return b.tong()


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    if os.environ.get("EIDE_FEATURE_SCHEMATIC", "") not in ("1", "true", "True"):
        print(f"{DO}Bộ này cần cờ tính năng sơ đồ BẬT.{HET}\n"
              "  EIDE_FEATURE_SCHEMATIC=1 .venv/bin/python tools/thu_sch.py\n\n"
              "Cờ tắt thì sch.* không được đăng ký — chạy tiếp sẽ ra '0/0 đạt', và một bảng "
              "0/0 trông như đã kiểm.")
        return 2
    d = (REPO / "du-lieu/thu-nghiem-sch").resolve()
    for x in (d, d.parent / (d.name + "-rong")):
        if x.exists():
            shutil.rmtree(x)
    d.mkdir(parents=True)
    (d.parent / (d.name + "-rong")).mkdir(parents=True)
    (d / "README.md").write_text("# Bo thu sinh so do\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
