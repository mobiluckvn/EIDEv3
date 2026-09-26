#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm cây khối phân cấp qua giao diện thật — EIDE-HIER-45, ca HIER01–04 và 16.

    python tools/thu_hier.py

Câu quan trọng nhất bộ này trả lời: **`flatten(cây)` có bằng netlist phẳng cũ 100 % không?**
Nếu không, mọi tool phẳng (ERC, BOM, sim, target) bắt đầu đọc một mạch khác với mạch người
đã vẽ, và không có bước nào sau đó phát hiện ra.

Happy: dự án phẳng cũ mở lên có cây ngay · dựng cây thật bằng Port · khối con ba tầng ·
tab Thiết kế hiện cây · tác tử thật khai Port qua hội thoại.

Unhappy (bảy đường): nối xuyên cấp · Port lá thừa · cha không tồn tại · tự làm cha mình ·
bus không kể thành viên · cây sâu 6 cấp (cảnh báo, KHÔNG cấm) · hạ lược đồ rồi lên lại.
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

from thu_giao_dien import Bo, GiaoDien, PathsThu        # noqa: E402

XANH, HET = "\033[92m", "\033[0m"
EX = {"summary": "dựng cây khối", "why": "để sơ đồ dựng trên cấu trúc thật",
      "sources": [], "diff_prev": "—", "next": "—", "confidence": "VANG"}

CHAN = [("7", "VCC", ""), ("8", "GND", ""), ("9", "PB6", "XTAL1, TOSC1"),
        ("27", "PC4", "SDA, ADC4"), ("28", "PC5", "SCL, ADC5")]


def _ctx(du_an):
    """Sổ cái riêng, kho dùng chung — xem docstring cùng tên trong tools/thu_ckm.py."""
    from eide import Config
    from eide.history import History
    from eide.ids import IdGen
    from eide.protocol.ledger import Ledger
    from eide.store import EideMd, Store
    from eide.tools import build_registry

    class C:
        config = Config.for_project(du_an)
        paths = PathsThu(du_an)
        store = Store(paths.store_db)
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-hier")
        registry = build_registry()
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
    from eide.knowledge import ckm as K

    ctx = _ctx(du_an)
    reg = ctx.registry

    def goi(cong_cu, /, **kw):
        if "explain" in (reg.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", EX)
        return reg.run(cong_cu, kw, ctx)

    # ================================================================== HAPPY
    b.phan("A · DỰ ÁN PHẲNG CŨ MỞ LÊN LÀ CÓ CÂY (HIER01)")

    ctx.store.apply(artefact_id="DS-328P", type="doc", op="create", author="human",
                    explain=EX, canonical={"ten": "ATmega328P datasheet", "so_trang": 660})
    for so, ten, af in CHAN:
        ctx.store.put_fact({"fact_id": f"f-ten-{so}", "subject": f"pin:ATmega328P.{so}",
                            "key": "ten", "value": ten, "tier": "VANG", "origin": "extract",
                            "source": {"doc_id": "DS-328P", "page": 13}, "explain": {}})
        if af:
            ctx.store.put_fact({"fact_id": f"f-af-{so}", "subject": f"pin:ATmega328P.{so}",
                                "key": "af", "value": af, "tier": "VANG",
                                "origin": "extract",
                                "source": {"doc_id": "DS-328P", "page": 13}, "explain": {}})
    goi("passport.pin", chip="ATmega328P", doc_ids=["DS-328P"])
    goi("ckm.chip_add", chip="ATmega328P", ref="U1")
    goi("ckm.module_set", ma="MOD-MCU", ten="Vi điều khiển", muc_dich="chạy firmware",
        linh_kien=["U1"], tin_hieu_vao=["3V3"], tin_hieu_ra=["SDA", "SCL"], rail="3V3")
    goi("ckm.module_set", ma="MOD-PWR", ten="Nguồn 3V3", muc_dich="hạ 5 V xuống 3,3 V",
        linh_kien=["U3"], tin_hieu_ra=["3V3"])
    goi("ckm.net_set", ten="3V3", loai="power", ap_danh_dinh="3,3 V",
        chan=[["U1", "7"], ["U3", "3"]])
    goi("ckm.net_set", ten="GND", loai="ground", chan=[["U1", "8"], ["U3", "2"]])
    goi("ckm.net_set", ten="SDA", loai="bus", bus="I2C1", chan=[["U1", "27"], ["U2", "5"]])

    nl = ctx.store.get(K.MA_NETLIST)["canonical"]
    cu = {n["ten"]: sorted(n.get("chan") or [], key=C._khoa_chan) for n in nl["net"]}
    moi = C.flatten(C.Cay.doc(ctx.store))
    b.kiem("flatten(cây) = netlist phẳng cũ 100 % — câu quan trọng nhất của bước",
           moi == cu, f"cũ {cu} · mới {moi}" if moi != cu else f"{len(moi)} net khớp")

    cay = C.Cay.doc(ctx.store)
    b.kiem("Cây có đúng một gốc và khối cũ thành con của gốc",
           cay.goc == C.GOC and len(cay.khoi_con(C.GOC)) == 2,
           "; ".join(cay.nut[x]["path"] for x in cay.khoi_con(C.GOC)))
    u1 = next(n for n in cay.nut.values() if n["ten"] == "ATmega328P")
    b.kiem("Linh kiện là LÁ, nằm trong khối khai nó (không nằm ở gốc)",
           u1["kind"] == "leaf" and cay.nut[u1["parent_id"]]["path"] == "/board/MOD-MCU",
           f"{u1['path']} trong {cay.nut[u1['parent_id']]['path']}")
    b.kiem("Port của lá sinh từ Fact, đủ 5 chân",
           len(cay.port_cua.get(u1["node_id"], [])) == 5,
           f"{len(cay.port_cua.get(u1['node_id'], []))} Port")
    mcu = next(n for n in cay.nut.values() if n.get("path") == "/board/MOD-MCU")
    ten_port = {cay.port[p]["ten"] for p in cay.port_cua.get(mcu["node_id"], [])}
    b.kiem("Net gốc chạm chân trong khối con → sinh Port 'lên cha' ở biên khối",
           {"3V3", "GND", "SDA"} <= ten_port, ", ".join(sorted(ten_port)))
    b.kiem("Không vi phạm bất biến nào sau di cư",
           C.kiem_bat_bien(cay, chan_theo_fact=K._chan_theo_fact(ctx.store, cay)) == [],
           "sạch")

    b.phan("B · DỰNG CÂY THẬT BẰNG PORT (HIER02)")
    goi("ckm.port_set", khoi="MOD-MCU", ten="VDD", huong="power_in",
        rang_buoc={"v_min": "2,7 V", "v_max": "5,5 V"})
    goi("ckm.port_set", khoi="MOD-MCU", ten="I2C0", huong="bidir", loai="bus",
        members=["SDA", "SCL"])
    r = goi("ckm.port_set", khoi="MOD-PWR", ten="VOUT", huong="power_out",
            rang_buoc={"i_max": "800 mA"})
    b.kiem("Khai Port ở biên khối được, và nói rõ đó là hợp đồng",
           r.ok and "hợp đồng" in r.data["note_vi"],
           r.data["note_vi"][:130] if r.ok else str(r.error.message_vi)[:130])

    r = goi("ckm.module_set", ma="MOD-XTAL", ten="Dao động thạch anh",
            muc_dich="16 MHz cho MCU", linh_kien=["Y1"], cha="MOD-MCU")
    b.kiem("Khối con vào đúng chỗ trong cây",
           r.ok and r.data["duong"] == "/board/MOD-MCU/MOD-XTAL"
           and r.data["kind"] == "subblock",
           r.data.get("duong", "") if r.ok else str(r.error.message_vi)[:120])

    r = goi("ckm.graph")
    b.kiem("Cây hiện được dạng chữ, có đủ ba tầng",
           r.ok and any("/board/MOD-MCU/MOD-XTAL" in d for d in r.data["cay"]),
           " | ".join(d.strip() for d in r.data["cay"][:4]) if r.ok else "")

    b.phan("C · GỘP BẢN ĐỒ CÓ CÂY")
    r = goi("ckm.build")
    b.kiem("Đủ tiền đề (có hộ chiếu, có khối, có net)",
           r.ok and r.data["du_de_sinh_so_do"] is True,
           r.data["note_vi"][:150] if r.ok else str(r.error.message_vi)[:130])
    b.kiem("Hiện vật CKM mang cả cây và netlist phẳng dẫn xuất",
           r.ok and r.data["so_net_phang"] == 3
           and "cay" in ctx.store.get("CKM-1")["canonical"],
           f"{r.data.get('so_net_phang')} net phẳng")
    b.kiem("Không vi phạm bất biến", r.ok and r.data["vi_pham_bat_bien"] == [],
           str(r.data.get("vi_pham_bat_bien"))[:140] if r.ok else "")

    b.phan("D · TÁC TỬ THẬT LÀM VIỆC TRÊN CÂY")
    g.go("Mạch đang chia thành những khối nào? Mình muốn tách phần cảm biến nhiệt ra "
         "thành một khối riêng tên MOD-SENSE, giao tiếp với MCU qua I2C. Làm giúp mình, "
         "rồi nói khối đó có hợp đồng gì với bên ngoài.")
    a = g.doi_xong(420)
    loi = a["loi_tac_tu_cuoi"]
    mg = ctx.store.get(K.MA_DO_THI)
    khoi = {x.get("ma") for x in (mg["canonical"].get("khoi") if mg else [])}
    b.kiem("Tác tử ghi khối mới bằng công cụ, không kể miệng", "MOD-SENSE" in khoi,
           ", ".join(sorted(khoi)))
    sense = next((x for x in (mg["canonical"].get("khoi") or [])
                  if x.get("ma") == "MOD-SENSE"), {})
    b.kiem("Tác tử khai Port cho khối mới (hoặc nói rõ chưa khai)",
           bool(sense.get("port")) or "Port" in loi,
           str([p.get("ten") for p in sense.get("port") or []]) or loi[:140])

    b.phan("Đ · TAB THIẾT KẾ HIỆN CÂY")
    g.mo_tab("design")
    anh = g.chup("thiet-ke")
    kh = {k["code"]: k for k in anh["khoi_tren_tab"]}
    b.kiem("Có khối A5.9 Cây khối phân cấp", "A5.9" in kh,
           "; ".join(sorted(kh)) or "không có khối nào")
    b.kiem("Cây trên tab có đủ nút (gốc + khối + lá)",
           kh.get("A5.9", {}).get("so_hang", 0) >= 5,
           f"{kh.get('A5.9', {}).get('so_hang')} dòng · "
           + kh.get("A5.9", {}).get("summary", "")[:90])
    b.kiem("Không khối nào thuộc loại giao diện chưa biết vẽ",
           all(k["type"] in ("table", "code", "empty", "kv", "list", "text", "timeline",
                             "changesets", "procedure", "snapshots", "sections")
               for k in anh["khoi_tren_tab"]),
           "; ".join(f"{k['code']}:{k['type']}" for k in anh["khoi_tren_tab"]))

    # ================================================================== UNHAPPY
    b.phan("E · BẢY ĐƯỜNG HỎNG")

    b.buoc("1. Nối xuyên cấp (HIER03)")
    ctx.store.ckm_dat_nut(node_id="net:XUYEN", loai="net", ten="XUYEN",
                          canonical={"ten": "XUYEN"})
    ctx.store.ckm_dat_cay("net:XUYEN", parent_id=C.GOC, kind=None, path="/board.XUYEN")
    ctx.store.ckm_noi(net_id="net:XUYEN", port_id=f"port:{u1['path']}.27")
    v = C.kiem_bat_bien(C.Cay.doc(ctx.store))
    x = next((i for i in v if i.ma == C.E_XUYEN_CAP), None)
    b.kiem("Từ chối và gợi ý KHAI PORT, không im lặng nhận",
           x is not None and "Port" in x.goi_y,
           (x.vi if x else "không phát hiện")[:150])
    ctx.store.ckm_xoa_noi(net_id="net:XUYEN")

    b.buoc("2. Port của lá thừa một chân chip KHÔNG có (HIER04)")
    ctx.store.ckm_dat_port(port_id=f"port:{u1['path']}.99", module_id=u1["node_id"],
                           ten="99", huong="passive", chan="99")
    cay2 = C.Cay.doc(ctx.store)
    v = C.kiem_bat_bien(cay2, chan_theo_fact=K._chan_theo_fact(ctx.store, cay2))
    x = next((i for i in v if i.ma == C.E_PORT_LA), None)
    b.kiem("Bắt được, và nói rõ hậu quả là sơ đồ vẽ chân không tồn tại",
           x is not None and "KHÔNG có" in x.vi,
           (x.vi if x else "không phát hiện")[:150])

    b.buoc("3. Khối con khai cha không tồn tại")
    r = goi("ckm.module_set", ma="MOD-X", ten="X", muc_dich="y", cha="KHONG-CO-KHOI-NAY")
    b.kiem("Từ chối và LIỆT KÊ khối đang có",
           not r.ok and "MOD-MCU" in r.error.hint_for_agent,
           (r.error.hint_for_agent if not r.ok else "lại nhận!")[:150])

    b.buoc("4. Khối tự làm cha của chính nó")
    r = goi("ckm.module_set", ma="MOD-MCU", ten="MCU", muc_dich="x", cha="MOD-MCU")
    b.kiem("Từ chối bằng mã bất biến cây E9001",
           not r.ok and r.error.code == C.E_CHU_TRINH,
           (r.error.message_vi if not r.ok else "lại nhận!")[:130])

    b.buoc("5. Port bus không kể thành viên")
    r = goi("ckm.port_set", khoi="MOD-PWR", ten="SPI", huong="bidir", loai="bus")
    b.kiem("Từ chối — hai đầu bus không kể thành viên thì không kiểm khớp được",
           not r.ok and r.error.code == C.E_BUS_LECH,
           (r.error.message_vi if not r.ok else "lại nhận!")[:130])

    b.buoc("6. Cây sâu 6 cấp — CẢNH BÁO, không cấm (HIER11)")
    cha = "MOD-XTAL"
    for i in range(1, 4):
        goi("ckm.module_set", ma=f"MOD-L{i}", ten=f"Tầng {i}", muc_dich="thử độ sâu",
            cha=cha)
        cha = f"MOD-L{i}"
    cay3 = C.Cay.doc(ctx.store)
    cb = C.canh_bao_do_sau(cay3)
    b.kiem("Cảnh báo độ sâu, nhưng cây vẫn HỢP LỆ",
           cb.startswith("Cây sâu") and not [i for i in C.kiem_bat_bien(cay3)
                                             if i.ma == C.E_CHU_TRINH],
           cb[:140])

    b.buoc("7. Hạ lược đồ cây rồi lên lại (HIER-15)")
    ctx.store.ha_cap(2)
    con_fact = len(ctx.store.query_facts(limit=5)) > 0
    con_netlist = ctx.store.get(K.MA_NETLIST) is not None
    ctx.store.nang_cap()
    b.kiem("Gỡ cây KHÔNG làm mất Fact hay netlist phẳng đã vẽ",
           con_fact and con_netlist,
           f"fact còn: {con_fact} · netlist còn: {con_netlist}")
    K.chieu(ctx.store)
    b.kiem("Lên lại thì cây dựng lại đúng như trước",
           C.flatten(C.Cay.doc(ctx.store)) == moi,
           "khớp" if C.flatten(C.Cay.doc(ctx.store)) == moi else "LỆCH")

    print()
    return b.tong()


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    d = (REPO / "du-lieu/thu-nghiem-hier").resolve()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "README.md").write_text("# Bo thu cay khoi\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
