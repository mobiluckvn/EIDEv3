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

HIER-B thêm: ERC bốn ràng buộc báo theo path (HIER06–08) · STALE theo cây, nội bộ KHÔNG lan
sang anh em (HIER05) · lớp giải thích khối bảy câu (HIER14) · cây trên tab Thiết kế có tô
nút (HIER15).
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
           kh.get("A5.9", {}).get("so_nut_cay", 0) >= 5,
           f"{kh.get('A5.9', {}).get('so_nut_cay')} nút · sâu "
           f"{kh.get('A5.9', {}).get('sau_nhat')} · "
           + kh.get("A5.9", {}).get("summary", "")[:80])
    b.kiem("Không khối nào thuộc loại giao diện chưa biết vẽ",
           all(k["type"] in ("table", "code", "empty", "kv", "list", "text", "timeline",
                             "changesets", "procedure", "snapshots", "sections", "cay")
               for k in anh["khoi_tren_tab"]),
           "; ".join(f"{k['code']}:{k['type']}" for k in anh["khoi_tren_tab"]))

    b.phan("E · ERC THEO CÂY (HIER06–08)")
    # Kiểm TRƯỚC khi nạp Fact: đường "chưa đủ dữ kiện" là ca quan trọng nhất của ERC, và nó
    # chỉ đo được khi Fact còn thiếu. Nạp Fact rồi mới kiểm thì mất hẳn đường đó.
    r0 = goi("board.check")
    thieu0 = r0.data["ket_qua"]["chua_du_du_kien"] if r0.ok else []
    b.kiem("Thiếu Fact thì nói CHƯA ĐỦ DỮ KIỆN, không gọi là đạt (N6)",
           bool(thieu0) and "CHƯA ĐỦ DỮ KIỆN" in r0.data["note_vi"],
           (thieu0[0]["vi"] if thieu0 else "không có chỗ nào chưa đủ")[:150])

    # Nạp Fact cho bốn ràng buộc §4.2. Con số thật: AMS1117 800 mA, ATmega328P 12 mA,
    # TMP102 85 µA ở 0x48.
    ctx.store.put_fact({"fact_id": "f-ldo-i", "subject": "leaf:U3", "key": "iout_max",
                        "value": 0.8, "unit": "A", "tier": "VANG", "origin": "extract",
                        "source": {"doc_id": "DS-AMS1117", "page": 4}, "explain": {}})
    ctx.store.put_fact({"fact_id": "f-mcu-i", "subject": "leaf:U1", "key": "i_max",
                        "value": 0.012, "unit": "A", "tier": "VANG", "origin": "extract",
                        "source": {"doc_id": "DS-328P", "page": 316}, "explain": {}})
    ctx.store.put_fact({"fact_id": "f-t-i", "subject": "leaf:U2", "key": "i_max",
                        "value": 0.000085, "unit": "A", "tier": "VANG", "origin": "extract",
                        "source": {"doc_id": "DS-TMP102", "page": 5}, "explain": {}})
    ctx.store.put_fact({"fact_id": "f-t-a", "subject": "leaf:U2", "key": "i2c.addr",
                        "value": "0x48", "tier": "VANG", "origin": "extract",
                        "source": {"doc_id": "DS-TMP102", "page": 9}, "explain": {}})

    r = goi("board.check")
    b.kiem("ERC chạy và mọi phát hiện nói rõ Ở KHỐI NÀO (HIER-17)",
           r.ok and r.data["so_phat_hien"] > 0
           and all(x["path"] for v in r.data["ket_qua"].values() for x in v),
           r.data["note_vi"][:170] if r.ok else str(r.error.message_vi)[:130])

    goi("ckm.net_set", ten="3V3", loai="power", ap_danh_dinh="3,3 V",
        chan=[["U1", "7"], ["U3", "3"]], noi_port=[["MOD-PWR", "VOUT"],
                                                  ["MOD-MCU", "VDD"]])
    r = goi("board.check")
    dong = [x for v in r.data["ket_qua"].values() for x in v
            if x["luat"] == "ngan_sach_dong"]
    b.kiem("Ngân sách dòng cộng được theo cây và nói còn dư bao nhiêu",
           any(x["ket_luan"] == "dat" and "còn dư" in x["vi"] for x in dong),
           (dong[0]["vi"] if dong else "không xét được")[:170])

    # Hai con TMP102 cùng 0x48 trên một bus — bus vẫn ACK, số của con nào thì không ai biết.
    ctx.store.put_fact({"fact_id": "f-t2-a", "subject": "leaf:U5", "key": "i2c.addr",
                        "value": "0x48", "tier": "VANG", "origin": "extract",
                        "source": {"doc_id": "DS-TMP102", "page": 9}, "explain": {}})
    goi("ckm.net_set", ten="SDA", loai="bus", bus="I2C1",
        chan=[["U1", "27"], ["U2", "5"], ["U5", "5"]])
    r = goi("board.check")
    trung = [x for v in r.data["ket_qua"].values() for x in v
             if x["luat"] == "trung_dia_chi"]
    b.kiem("Hai con cùng địa chỉ I2C bị phát hiện, kèm khối (HIER08)",
           any(x["ket_luan"] == "khong_dat" and "U2" in x["vi"] and "U5" in x["vi"]
               for x in trung),
           (trung[0]["vi"] if trung else "không phát hiện")[:170])
    pu = [x for v in r.data["ket_qua"].values() for x in v if x["luat"] == "pull_up"]
    b.kiem("Bus I2C thiếu pull-up bị gọi tên, có cách sửa",
           any(x["ket_luan"] == "khong_dat" and "open-drain" in x["vi"] for x in pu),
           (pu[0]["cach_sua"] if pu else "không xét")[:150])

    b.phan("F · STALE THEO CÂY (HIER05, HIER06) VÀ GIẢI THÍCH KHỐI (HIER14)")
    r = goi("ckm.port_set", khoi="MOD-MCU", ten="VDD", huong="bidir",
            rang_buoc={"ghi_chu": "đổi hướng để thử lan STALE"})
    nut = (ctx.store.get(K.MA_DO_THI)["canonical"].get("stale_nut") or {})
    b.kiem("Đổi Port lan tới cha và khối cùng nối net (bảng §6 dòng 2)",
           "/board/MOD-MCU" in nut and "/board" in nut and "/board/MOD-PWR" in nut,
           ", ".join(sorted(nut)) or "không lan gì")
    lan_noi_bo = C.lan_stale(C.Cay.doc(ctx.store), loai="noi_bo",
                             muc_tieu="/board/MOD-SENSE", ly_do="cs-thu")
    b.kiem("Sửa nội bộ khối KHÔNG lan sang anh em; cha chỉ nhận cờ thông tin",
           "/board/MOD-MCU" not in lan_noi_bo.stale
           and "/board" in lan_noi_bo.chi_bao_tin
           and "/board" not in lan_noi_bo.stale,
           f"stale: {sorted(lan_noi_bo.stale)} · thông tin: {sorted(lan_noi_bo.chi_bao_tin)}")

    r = goi("stale.accept", id="/board/MOD-MCU", why="anh chấp nhận, sửa ở đợt sau")
    canon = ctx.store.get(K.MA_DO_THI)["canonical"]
    b.kiem("Chấp nhận STALE cho một nút, và lý do được GIỮ chứ không xoá trắng",
           r.ok and "/board/MOD-MCU" not in (canon.get("stale_nut") or {})
           and "anh chấp nhận" in (canon.get("stale_da_chap_nhan") or {})
                                  .get("/board/MOD-MCU", ""),
           str(canon.get("stale_da_chap_nhan", {}))[:140])

    from eide.knowledge import erc as ERC
    ex = ERC.explain_khoi(C.Cay.doc(ctx.store), "/board/MOD-MCU")
    b.kiem("Lớp giải thích khối có hai câu do MÃ dựng: giao tiếp gì · gồm gì (HIER14)",
           "VDD" in ex["giao_tiep"] and "U1" in ex["gom"],
           f"giao tiếp: {ex['giao_tiep'][:60]} · gồm: {ex['gom'][:60]}")

    b.phan("G · TÁC TỬ BÁO ERC, VÀ TAB TÔ ĐÚNG NÚT (HIER15)")
    # Lượt này cần thiết về mặt KỸ THUẬT: bề mặt chỉ được vẽ lại ở cuối mỗi lượt, nên muốn
    # thấy STALE theo nút và bảng ERC trên tab thì phải có một lượt nữa sau khi chúng sinh.
    g.go("Kiểm mạch giúp mình xem có vấn đề gì không, và nói rõ vấn đề ở khối nào.")
    a2 = g.doi_xong(420)
    loi2 = a2["loi_tac_tu_cuoi"]
    b.kiem("Tác tử nêu được vấn đề và nói ở KHỐI nào",
           any(t in loi2 for t in ("MOD-SENSE", "MOD-MCU", "/board")) 
           and any(t in loi2.lower() for t in ("địa chỉ", "pull-up", "0x48")),
           loi2[:200])

    g.mo_tab("design")
    anh2 = g.chup("thiet-ke-2")
    kh2 = {k["code"]: k for k in anh2["khoi_tren_tab"]}
    cay_kh = kh2.get("A5.9", {})
    b.kiem("Cây tô đúng nút cần cập nhật, và tách khỏi nút 'con đã đổi' (§6)",
           bool(cay_kh.get("nut_can_cap_nhat")),
           f"cần cập nhật: {cay_kh.get('nut_can_cap_nhat')} · "
           f"con đã đổi: {cay_kh.get('nut_con_da_doi')}")
    b.kiem("Tab có bảng ERC theo khối", "A5.9c" in kh2,
           kh2.get("A5.9c", {}).get("summary", "")[:150])
    b.kiem("Bảng ERC không gọi 'chưa đủ dữ kiện' là 'đạt'",
           "chưa đủ dữ kiện" in kh2.get("A5.9c", {}).get("chu_da_dung", "").lower()
           or "chưa đủ dữ kiện" in kh2.get("A5.9c", {}).get("summary", "").lower(),
           kh2.get("A5.9c", {}).get("summary", "")[:150])

    # ================================================================== UNHAPPY
    b.phan("H · BẢY ĐƯỜNG HỎNG")

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
    # So với ảnh NGAY TRƯỚC khi hạ, không với ảnh đầu bộ: giữa hai mốc đó bộ đo đã thêm
    # khối, net và Port, nên flatten khác đi là đúng. So sai mốc thì ca đo đỏ vì một lý do
    # không phải lỗi sản phẩm.
    truoc_ha = C.flatten(C.Cay.doc(ctx.store))
    ctx.store.ha_cap(2)
    con_fact = len(ctx.store.query_facts(limit=5)) > 0
    con_netlist = ctx.store.get(K.MA_NETLIST) is not None
    ctx.store.nang_cap()
    b.kiem("Gỡ cây KHÔNG làm mất Fact hay netlist phẳng đã vẽ",
           con_fact and con_netlist,
           f"fact còn: {con_fact} · netlist còn: {con_netlist}")
    K.chieu(ctx.store)
    sau_len = C.flatten(C.Cay.doc(ctx.store))
    b.kiem("Lên lại thì cây dựng lại đúng như trước khi hạ",
           sau_len == truoc_ha,
           f"{len(truoc_ha)} net → {len(sau_len)} net"
           + ("" if sau_len == truoc_ha else " · LỆCH"))

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
