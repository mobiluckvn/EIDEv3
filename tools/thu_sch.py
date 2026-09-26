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
· bố cục xác định có tiêu chí đo bằng số · ghi .kicad_sch đọc lại được khớp từng ký tự ·
render SVG kiểm chữ không đè · tác tử thật sinh sơ đồ qua hội thoại.

Unhappy (bảy đường): mô hình bịa net trong tệp · tệp lỗi cú pháp · thiếu pinout · cây vi phạm
bất biến · chưa đủ tiền đề · gọi sch.netlist trước sch.compose · đề nghị cài KiCad.

SCH-D thêm: bố cục đo trên TỪNG sheet và đề nghị phân cấp khi mạch lớn (SCH07) · sổ đăng ký
sheet + gói sơ đồ vào bản ưng ý, khôi phục đưa tệp về (SCH-16) · ký hiệu sinh từ Fact CHỜ người
xác nhận, người sửa kiểu chân thành Fact tầng NGƯỜI (SCH-14/15) · khối A5.8 trên tab Thiết kế
với ảnh bấm được, băng chất lượng từng trang, bảng ký hiệu sửa được (SCH-06/07).

HIER-D/SCH-C thêm: sheet phân cấp — mỗi khối một tệp, sheet pin = Port, đọc lại dựng ĐÚNG cây
(HIER13) · cây sâu > 4 cấp TỰ chuyển sang phân cấp (HIER11) · xuất gói mở được ở máy có KiCad
(SCH11) · nạp lại sơ đồ người sửa, phân loại ba loại thay đổi, cấu trúc thì HỎI (SCH10, 12, 13).
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
    # Chạy THẲNG tệp thực thi trong bundle, không qua `open`, để truyền được biến môi trường.
    #
    # `open` không mang biến môi trường của shell sang app, nên lõi mà app sinh ra sẽ đọc
    # `Features.load()` với cờ TẮT và `sch.*` không được đăng ký — phần đo giao diện của bộ này
    # sẽ đỏ vì một lý do không phải lỗi sản phẩm. Cách khác là ghi vào
    # `~/.eide/settings.json`, tức sửa tệp thiết lập của người dùng để chạy một bộ đo: không.
    print("Mở app (cờ schematic BẬT qua biến môi trường)…")
    subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                     env={**os.environ, "EIDE_FEATURE_SCHEMATIC": "1"},
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    g.san_sang(60)
    print(f"{XANH}Kênh kiểm thử giao diện đã mở{HET}\n")

    from eide.knowledge import cay as C
    from eide.knowledge import ckm as K
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

    b.phan("Đ · BỐ CỤC (SCH05–08, SCH17)")
    r = goi("sch.place")
    b.kiem("Bố cục xong, tiêu chí đo bằng SỐ",
           r.ok and r.data["tieu_chi"]["so_ky_hieu"] >= 1,
           r.data["note_vi"][:170] if r.ok else str(r.error.message_vi)[:150])
    tc = r.data["tieu_chi"] if r.ok else {}
    b.kiem("0 ký hiệu chồng nhau · 0 dây cắt thân · đúng lưới 1,27 mm",
           tc.get("cap_chong_nhau") == 0 and tc.get("day_cat_than") == 0
           and not any("lệch lưới" in v for v in tc.get("vi_pham", [])),
           f"chồng {tc.get('cap_chong_nhau')} · cắt thân {tc.get('day_cat_than')} · "
           f"vi phạm: {tc.get('vi_pham')}")
    b.kiem("Mọi ký hiệu nằm trong khổ giấy", tc.get("trong_kho_giay") is True,
           f"khổ {tc.get('kho')}")
    from eide.sch import bo_cuc as BCM
    cay0 = C.Cay.doc(ctx.store)
    nam = [BCM.tinh_bo_cuc(cay0, C.flatten(cay0)).to_dict() for _ in range(5)]
    b.kiem("Chạy 5 lần cùng toạ độ (SCH17)", all(x == nam[0] for x in nam),
           f"{len(nam[0]['o'])} ký hiệu, toạ độ giống hệt 5 lần")
    b.kiem("Tỉ lệ net dùng nhãn được NÓI RA, không lặng lẽ cho qua",
           "ty_le_net_dung_nhan" in tc,
           f"{tc.get('ty_le_net_dung_nhan', 0):.0%} net dùng nhãn")

    b.phan("E · GHI .kicad_sch MỘT TRANG (SCH20, SCH21) VÀ RENDER (SCH06–07)")
    r = goi("sch.write", style="flat")
    b.kiem("Ghi được, và ĐỌC LẠI khớp từng ký tự (round-trip ổn định)",
           r.ok and r.data["round_trip"] is True,
           r.data["note_vi"][:170] if r.ok else str(r.error.message_vi)[:160])
    b.kiem("Ghi một trang mạch CÓ khối thì NÓI RÕ là cây khối không còn trong tệp",
           r.ok and r.data["mat_cay"] is True and "cây khối KHÔNG còn" in r.data["note_vi"],
           r.data["note_vi"][:130] if r.ok else "")
    p_sch = du_an / "sch/mach.kicad_sch"
    txt_sch = p_sch.read_text("utf-8") if p_sch.exists() else ""
    b.kiem("Tệp có đủ ref và có .kicad_pro đi kèm",
           '"U1"' in txt_sch and (du_an / "sch/mach.kicad_pro").exists(),
           f"{txt_sch.count('(symbol (lib_id')} ký hiệu trong tệp")
    from eide.sch import ghi as GHI
    b.kiem("uuid sinh theo REF nên sinh lại KHÔNG mất bố cục người đã sửa (SCH20)",
           GHI.uuid_theo("sym:U1") in txt_sch
           and GHI.uuid_theo("sym:U1") == GHI.uuid_theo("sym:U1"),
           GHI.uuid_theo("sym:U1"))

    r = goi("sch.render")
    b.kiem("Vẽ ra SVG, số ký hiệu khớp số ref",
           r.ok and r.data["so_ky_hieu"] == len(r.data["ref_trong_svg"])
           and r.data["so_ky_hieu"] >= 1,
           r.data["note_vi"][:150] if r.ok else str(r.error.message_vi)[:150])
    svg = (du_an / "sch/mach.svg").read_text("utf-8") if (du_an / "sch/mach.svg").exists() else ""
    b.kiem("SVG có bản đồ ký hiệu → ref để giao diện bấm được",
           'data-ref="U1"' in svg, f"{svg.count('data-ref=')} ký hiệu có data-ref")
    b.kiem("Chữ KHÔNG đè nhau (kiểm bbox)",
           r.ok and r.data["chu_de_nhau"] == [],
           str(r.data.get("chu_de_nhau"))[:150] if r.ok else "")

    b.phan("F · SHEET PHÂN CẤP VÀ VÒNG ĐI–VỀ (HIER11, HIER13)")
    r = goi("sch.write")
    b.kiem("Mặc định auto: mạch CÓ khối thì tự ghi phân cấp, không phải một trang",
           r.ok and r.data.get("style") == "hierarchical",
           r.data["note_vi"][:130] if r.ok else str(r.error.message_vi)[:130])
    r = goi("sch.write", style="hierarchical")
    b.kiem("Mỗi khối một sheet, Port thành sheet pin",
           r.ok and r.data.get("style") == "hierarchical" and r.data["so_sheet"] >= 3,
           r.data["note_vi"][:170] if r.ok else str(r.error.message_vi)[:150])
    b.kiem("Đọc lại gói dựng lại ĐÚNG cây (HIER13)",
           r.ok and r.data["doc_lai_dung_cay"] is True,
           str(r.data.get("so_cay"))[:170] if r.ok else "")
    tep_sheet = sorted(x.name for x in (du_an / "sch").glob("*.kicad_sch"))
    b.kiem("Có tệp sheet riêng cho từng khối, tên theo đường dẫn",
           {"mach.kicad_sch", "mach_MOD-MCU.kicad_sch", "mach_MOD-PWR.kicad_sch"}
           <= set(tep_sheet), ", ".join(tep_sheet))

    for i in range(1, 5):
        goi("ckm.module_set", ma=f"L{i}", ten=f"Tầng {i}", muc_dich="thử độ sâu",
            cha=("MOD-MCU" if i == 1 else f"L{i-1}"))
    r = goi("sch.write", style="flat")
    b.kiem("Cây sâu hơn 4 cấp thì TỰ chuyển sang phân cấp (HIER11)",
           r.ok and r.data.get("style") == "hierarchical"
           and "TỰ chuyển sang phân cấp" in r.data["note_vi"],
           r.data["note_vi"][:180] if r.ok else str(r.error.message_vi)[:150])

    r = goi("sch.render")
    b.kiem("Vẽ MỌI sheet — gốc phân cấp chỉ có hộp sheet nên vẽ riêng nó là ảnh rỗng",
           r.ok and len(r.data["tep"]) >= 3 and r.data["so_ky_hieu"] >= 1
           and r.data["so_sheet"] >= 1,
           r.data["note_vi"][:160] if r.ok else str(r.error.message_vi)[:150])

    b.phan("G · XUẤT GÓI VÀ NẠP LẠI (SCH10–13)")
    r = goi("sch.export")
    b.kiem("Gói có đủ tệp và tệp hướng dẫn nói rõ máy này KHÔNG cài KiCad (SCH11)",
           r.ok and (du_an / "sch/goi/DOC-TRUOC-KHI-MO.md").exists()
           and "không cài KiCad" in r.data["note_vi"],
           ", ".join(r.data["tep"][:6]) if r.ok else str(r.error.message_vi)[:140])

    r = goi("sch.import")
    b.kiem("Nạp lại khi chưa ai sửa gì: KHÔNG có thay đổi, KHÔNG đánh STALE (SCH10)",
           r.ok and r.data["so_thay_doi"] == 0 and r.data["can_hoi"] is False,
           r.data["note_vi"][:160] if r.ok else str(r.error.message_vi)[:150])

    # Người sửa GIÁ TRỊ một linh kiện trong KiCad.
    p_mcu = du_an / "sch/mach_MOD-MCU.kicad_sch"
    assert p_mcu.exists(), sorted(x.name for x in (du_an / "sch").glob("*.kicad_sch"))
    txt = p_mcu.read_text("utf-8")
    p_mcu.write_text(txt.replace('(property "Value" "ATmega328P"',
                                 '(property "Value" "ATmega328PB"'), "utf-8")
    r = goi("sch.import")
    gia = r.data["theo_loai"]["gia_tri"] if r.ok else []
    b.kiem("Đổi GIÁ TRỊ linh kiện: vào loại giá trị, KHÔNG phải hỏi",
           r.ok and len(gia) >= 1 and r.data["can_hoi"] is False,
           (gia[0]["vi"] if gia else r.data.get("note_vi", ""))[:150])
    p_mcu.write_text(txt, "utf-8")

    # Người THÊM một linh kiện trong KiCad — đây là thay đổi CẤU TRÚC.
    them = ('  (symbol (lib_id "Device:R") (at 100 100 0) (unit 1)\n'
            '    (in_bom yes) (on_board yes) (dnp no)\n'
            '    (uuid 11111111-2222-4333-8444-555555555555)\n'
            '    (property "Reference" "R99" (at 100 98 0)\n'
            '      (effects (font (size 1.27 1.27)))\n'
            "    )\n"
            '    (property "Value" "4k7" (at 100 102 0)\n'
            '      (effects (font (size 1.27 1.27)))\n'
            "    )\n"
            "  )\n")
    p_mcu.write_text(txt.rstrip()[:-1] + them + ")\n", "utf-8")
    truoc_khoi = ctx.store.get(K.MA_DO_THI)["canonical"]["khoi"]
    r = goi("sch.import")
    ct = r.data["theo_loai"]["cau_truc"] if r.ok else []
    b.kiem("Thêm linh kiện = CẤU TRÚC → tạo thẻ hỏi (SCH12, SCH13)",
           r.ok and r.data["can_hoi"] is True and any("R99" in x["vi"] for x in ct),
           (ct[0]["vi"] if ct else "không phát hiện")[:150])
    b.kiem("Thẻ hỏi nêu HAI lựa chọn, mỗi cái nói hậu quả, và nói rõ KHÔNG chọn hộ",
           r.ok and r.data["the_hoi"] and len(r.data["the_hoi"]["lua_chon"]) == 2
           and all(x["hau_qua"] for x in r.data["the_hoi"]["lua_chon"])
           and "không chọn hộ" in r.data["the_hoi"]["khong_tu_chon"],
           str([x["nhan"] for x in r.data["the_hoi"]["lua_chon"]]) if r.ok else "")
    b.kiem("KHÔNG tự ghi đè bản đồ mạch — đó là cả nội dung của SCH13",
           ctx.store.get(K.MA_DO_THI)["canonical"]["khoi"] == truoc_khoi,
           "bản đồ giữ nguyên")
    p_mcu.write_text(txt, "utf-8")

    b.phan("H · BỐ CỤC TỪNG SHEET, SỔ SHEET, BẢN ƯNG Ý (SCH07, SCH-16)")
    r = goi("sch.place")
    b.kiem("Bố cục đo tiêu chí trên TỪNG trang, không chỉ trên tổng thể (SCH07)",
           r.ok and r.data["so_sheet"] >= 3
           and sum(t["so_ky_hieu"] for t in r.data["tieu_chi_sheet"].values())
               == r.data["so_ky_hieu"],
           f"{r.data['so_sheet']} trang · chưa đạt: {r.data['sheet_chua_dat']}"
           if r.ok else str(r.error.message_vi)[:150])
    b.kiem("Lý do đề nghị/không đề nghị phân cấp đều là SỐ đo được",
           r.ok and isinstance(r.data["de_nghi_phan_cap"]["nen_phan_cap"], bool)
           and r.data["de_nghi_phan_cap"]["vi"],
           r.data["de_nghi_phan_cap"]["vi"][:160] if r.ok else "")

    r = goi("sch.write", style="hierarchical")
    ds_sheet = ctx.store.sch_cac_sheet()
    b.kiem("Mỗi sheet một dòng trong sổ đăng ký, kèm băm bố cục và phiên bản thư viện",
           r.ok and len(ds_sheet) == r.data["so_sheet_ghi_so"]
           and all(x["layout_hash"] and x["lib_versions"] for x in ds_sheet),
           f"{len(ds_sheet)} dòng · {ds_sheet[0]['layout_hash'][:12]}…" if ds_sheet else "")

    goi("sch.render")
    snap = ctx.history.tao_snapshot(ten="co-so-do", ghi_chu="thử SCH-16", boi="human")
    sd = snap.contents["so_do"]
    b.kiem("Bản ưng ý gói cả NỘI DUNG tệp sơ đồ, không chỉ tên tệp (SCH-16)",
           sd["so_sheet"] >= 3 and all(x["co_tep"] and x["blob"] for x in sd["sheet"])
           and any(k["tep"].endswith(".kicad_sym") for k in sd["kem"]),
           f"{sd['so_sheet']} sheet + {len(sd['kem'])} tệp kèm · lib {sd['lib_versions']}")

    p_mot = du_an / sd["sheet"][0]["tep"]
    that = p_mot.read_text("utf-8")
    p_mot.write_text("(kicad_sch HỎNG)\n", "utf-8")
    kq = ctx.history.khoi_phuc_snapshot(snap.id, by="human")
    b.kiem("Khôi phục bản ưng ý đưa tệp sơ đồ về đúng nội dung lúc đó",
           kq.ok and p_mot.read_text("utf-8") == that
           and "tệp sơ đồ về đúng nội dung" in kq.message_vi,
           kq.message_vi[:170])

    b.phan("I · KÝ HIỆU CHỜ NGƯỜI XÁC NHẬN (SCH-14, SCH-15)")
    r = goi("sch.symbols")
    b.kiem("Ký hiệu sinh từ Fact thì CHỜ người xem, và công cụ nói ra",
           r.ok and r.data["cho_xac_nhan"] and "CHỜ người xác nhận" in r.data["note_vi"],
           str(r.data.get("cho_xac_nhan"))[:120] if r.ok else "")
    r = goi("sch.write", style="hierarchical")
    b.kiem("Ghi tệp vẫn nói rõ còn ký hiệu chưa ai xác nhận (N6 áp vào kiểu chân)",
           r.ok and r.data["cho_xac_nhan_ky_hieu"] and "chưa ai xác nhận" in r.data["note_vi"],
           r.data["note_vi"][:150] if r.ok else "")
    r = goi("sch.symbol_confirm", ref="U1", trich_loi="")
    b.kiem("Tác tử KHÔNG xác nhận hộ người dùng được",
           not r.ok and r.error.code == "E8009"
           and "Đừng tự xác nhận hộ" in r.error.hint_for_agent,
           (r.error.message_vi if not r.ok else "lại ghi!")[:150])

    # Người bấm sửa kiểu chân TRÊN GIAO DIỆN — đi qua cùng công cụ đó.
    g.mo_tab("design")
    g.sua("symbol", "U1", {"chan": "7=power_in"}, "v1",
          "tôi tra datasheet rồi, chân 7 là VCC nên phải là power_in")
    g.doi_xong(240)
    f = [x for x in ctx.store.query_facts(subject="pin:ATmega328P.7", limit=10)
         if x["key"] == "kieu_chan"]
    b.kiem("Người sửa kiểu chân trên giao diện → Fact tầng NGƯỜI có trích lời",
           bool(f) and f[0]["tier"] == "NGUOI" and f[0]["value"] == "power_in",
           str(f[0])[:170] if f else "không có Fact nào")

    b.phan("Đ2 · KHỐI A5.8 TRÊN TAB THIẾT KẾ (SCH-06, SCH-07)")
    goi("sch.render")
    g.ve_lai()                      # bộ đo ghi thẳng vào kho ⇒ phải xin app vẽ lại (0 token)
    g.mo_tab("design")
    a5 = {k["code"]: k for k in g.chup("a58")["khoi_tren_tab"]}
    b.kiem("Có khối ảnh sơ đồ, nhiều trang, ký hiệu bấm được",
           a5.get("A5.8", {}).get("type") == "svg"
           and a5["A5.8"]["so_trang_svg"] >= 3 and a5["A5.8"]["so_ref_bam_duoc"] >= 1,
           str({k: v for k, v in a5.get("A5.8", {}).items()
                if k in ("type", "so_trang_svg", "so_ref_bam_duoc")}))
    b.kiem("Khối ảnh mang đủ sáu trường giải thích (N8)",
           a5.get("A5.8", {}).get("explain_du_6_truong") is True,
           f"co_explain={a5.get('A5.8', {}).get('co_explain')}")
    b.kiem("Băng chất lượng bố cục có một dòng mỗi trang",
           a5.get("A5.8b", {}).get("so_hang", 0) >= 4,
           f"{a5.get('A5.8b', {}).get('so_hang')} dòng")
    b.kiem("Bảng ký hiệu sửa được, và ô sửa nhắm vào KÝ HIỆU chứ không phải yêu cầu",
           a5.get("A5.8c", {}).get("cot_sua_loai") == "symbol"
           and a5["A5.8c"]["so_hang"] >= 1,
           str(a5.get("A5.8c", {}).get("cot_sua_loai")))
    b.kiem("Khối mức render nói rõ máy này không cài KiCad, và không đề nghị cài",
           "KHÔNG cài KiCad" in a5.get("A5.8d", {}).get("summary", "")
           and "hãy cài" not in a5.get("A5.8d", {}).get("summary", ""),
           a5.get("A5.8d", {}).get("summary", "")[:130])
    # Hỏi CHÍNH giao diện, không hỏi một danh sách loại khối viết ở đây: `ve_duoc` do nhánh
    # "chưa biết vẽ" của bộ vẽ Swift tự ghi vào khi nó chạy. Bản trước so với một danh sách
    # trong bộ đo, tức chỉ kiểm rằng BỘ ĐO biết loại khối đó.
    kh_all = g.chup("loai-khoi")["khoi_tren_tab"]
    b.kiem("Giao diện vẽ được MỌI khối — chính bộ vẽ Swift khai, không phải bộ đo đoán",
           all(k.get("ve_duoc") is True for k in kh_all),
           "; ".join(f"{k['code']}:{k['type']}" for k in kh_all if not k.get("ve_duoc"))
           or f"{len(kh_all)} khối, loại: "
              + ", ".join(sorted({k["type"] for k in kh_all})))

    b.phan("K · TÁC TỬ THẬT SINH SƠ ĐỒ QUA HỘI THOẠI")
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
    b.phan("L · MƯỜI ĐƯỜNG HỎNG")

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

    b.buoc("7. Xếp bố cục khi netlist CHƯA kiểm")
    r = ctx2.registry.run("sch.place", {"explain": EX}, ctx2)
    b.kiem("Từ chối — xếp đẹp một mạch chưa kiểm là xếp đẹp một mạch có thể sai",
           not r.ok and "mạch sai" in r.error.message_vi,
           (r.error.message_vi if not r.ok else "lại xếp!")[:140])

    b.buoc("8. Ghi .kicad_sch khi chưa có bố cục")
    r = ctx2.registry.run("sch.write", {"explain": EX}, ctx2)
    b.kiem("Nói rõ gọi sch.place trước",
           not r.ok and r.error.alternatives == ["sch.place"],
           (r.error.message_vi if not r.ok else "lại ghi!")[:120])

    b.buoc("9. Render khi chưa có tệp — suy giảm R3")
    r = ctx2.registry.run("sch.render", {"explain": EX}, ctx2)
    b.kiem("Nói thẳng chưa có gì để vẽ, và chỉ về sơ đồ khối",
           not r.ok and "mức R3" in r.error.message_vi
           and "diagram.render" in (r.error.alternatives or []),
           (r.error.message_vi if not r.ok else "lại vẽ!")[:150])

    b.buoc("10. Đề nghị cài KiCad — chốt chặn ở hook Stop (SCH09)")
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
