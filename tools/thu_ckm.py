#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm Bản đồ tri thức mạch (CKM) qua giao diện thật — MDD-40 §C2.

    python tools/thu_ckm.py

Vì sao lại chạy qua app thật thay vì chỉ `pytest`: mọi lỗi nặng nhất của các bước trước
đều vô hình với ca đơn vị — một `KeyError` trong hàm dựng `<inventory>` giết cả lượt
trước khi mô hình được gọi; một khối có loại lạ hiện ra thành dòng "giao diện chưa biết
vẽ"; một cảnh báo ghi vào trường không ai dựng thì không ai đọc. Ba thứ đó chỉ lộ ra khi
có một cái màn hình thật.

Happy: dựng bản đồ từ bảng chân → khối → net → gộp · tab Thiết kế hiện đủ bốn bảng ·
tác tử thật tự gán chân qua hội thoại.

Unhappy (tám đường): bịa số chân · chức năng không có trong AF · gán trùng một chân ·
gán lại mà không nói vì sao · chân tầng ĐỒNG · render khi chưa có khối · hai con cùng
loại mà gọi bằng tên chip · hoàn tác rồi bản đồ có lùi theo không.
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
EX = {"summary": "dựng bản đồ mạch", "why": "để sinh sơ đồ từ dữ liệu có nguồn",
      "sources": [], "diff_prev": "—", "next": "—", "confidence": "VANG"}

# Bảng chân thật của ATmega328P (DIP-28), phần liên quan tới I2C và nguồn.
CHAN = [
    ("7", "VCC", ""),
    ("8", "GND", ""),
    ("27", "PC4", "SDA, ADC4"),
    ("28", "PC5", "SCL, ADC5"),
    ("14", "PB0", "ICP1, CLKO"),
]


def _ctx(du_an):
    """Ngữ cảnh cho phần đo xác định — dùng CHUNG kho, nhưng sổ cái RIÊNG.

    `Ledger` ghi nhớ `seq` và `hash` đầu chuỗi lúc khởi tạo, và docstring của nó nói rõ
    "an toàn với nhiều luồng trong MỘT tiến trình". App đang chạy là một tiến trình khác,
    nên nếu bộ kiểm ghi vào cùng sổ cái thì hai bên cấp `seq` độc lập và chuỗi đứt.

    Lần chạy đầu của bộ này phơi ra đúng điều đó: app phát hiện sổ cái đứt ở dòng 26 và
    dành cả lượt để báo, thay vì làm việc người nhờ. Nó phát hiện ĐÚNG — lỗi ở bộ kiểm.
    Kho hiện vật thì vẫn dùng chung, vì đó chính là thứ tác tử phải thấy.
    """
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
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-ckm")
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

    ctx = _ctx(du_an)
    reg = ctx.registry

    def goi(cong_cu, **kw):
        if "explain" in (reg.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", EX)
        return reg.run(cong_cu, kw, ctx)

    # ================================================================== HAPPY
    b.phan("A · BẢNG CHÂN VÀO BẢN ĐỒ (không có Fact thì không có chân)")

    r = goi("ckm.chip_add", chip="ATmega328P", ref="U1")
    b.kiem("Chưa nạp bảng chân thì chip_add TỪ CHỐI",
           not r.ok and r.error.code == "E8002",
           (r.error.message_vi if not r.ok else "lại nhận!")[:130])
    b.kiem("Lời từ chối nói chính xác chủ đề Fact phải ghi",
           not r.ok and "pin:ATmega328P.<số>" in r.error.hint_for_agent,
           (r.error.hint_for_agent if not r.ok else "")[:150])

    for so, ten, af in CHAN:
        ctx.store.put_fact({"fact_id": f"f-ten-{so}", "subject": f"pin:ATmega328P.{so}",
                            "key": "ten", "value": ten, "tier": "VANG",
                            "origin": "extract",
                            "source": {"doc_id": "DS-328P", "page": 13},
                            "explain": {"summary": f"chân {so} tên {ten}"}})
        if af:
            ctx.store.put_fact({"fact_id": f"f-af-{so}", "subject": f"pin:ATmega328P.{so}",
                                "key": "af", "value": af, "tier": "VANG",
                                "origin": "extract",
                                "source": {"doc_id": "DS-328P", "page": 13},
                                "explain": {"summary": f"AF của chân {so}"}})

    # Ghim hộ chiếu: từ 26/09 `ckm.build` đòi đúng thứ SCH-44 §4 đòi — `passport` — thay vì
    # tự thoả bằng một nút chip. Bộ đo phải đi qua đường thật đó.
    ctx.store.apply(artefact_id="DS-328P", type="doc", op="create", author="human",
                    explain=EX, canonical={"ten": "ATmega328P datasheet", "so_trang": 660})
    goi("passport.pin", chip="ATmega328P", doc_ids=["DS-328P"])

    r = goi("ckm.chip_add", chip="ATmega328P", ref="U1")
    b.kiem("Có Fact rồi thì 5 chân vào bản đồ",
           r.ok and r.data["so_chan_vao_ban_do"] == 5,
           r.data["note_vi"][:130] if r.ok else str(r.error.message_vi)[:130])
    b.kiem("Chip đã ghim hộ chiếu thì bản đồ ghi nhận",
           r.ok and r.data["co_ho_chieu"] is True, r.data.get("ho_chieu", "")[:70])

    b.phan("B · GÁN CHÂN — chân phải có thật, chức năng phải nằm trong AF")
    r = goi("ckm.pinout_set", chip="U1", chan="27", chuc_nang="SDA", net="SDA")
    b.kiem("Gán chân có Fact và AF khớp thì được",
           r.ok and r.data["so_chan_da_gan"] == 1,
           r.data["note_vi"][:120] if r.ok else str(r.error.message_vi)[:120])
    r = goi("ckm.pinout_set", chip="U1", chan="28", chuc_nang="SCL", net="SCL")
    b.kiem("Gán chân thứ hai", r.ok and r.data["so_chan_da_gan"] == 2,
           r.data["note_vi"][:100] if r.ok else str(r.error.message_vi)[:100])

    r = goi("ckm.pinout_set", chip="U1", chan="7", chuc_nang="VCC")
    b.kiem("Chân không có danh sách AF: gán được nhưng nói KHÔNG kiểm được",
           r.ok and any("không kiểm được" in c for c in r.data["canh_bao"]),
           "; ".join(r.data["canh_bao"])[:140] if r.ok else str(r.error.message_vi)[:120])

    b.phan("C · SƠ ĐỒ KHỐI — mã suy ra mũi tên, mã vẽ hình")
    goi("ckm.module_set", ma="MOD-PWR", ten="Nguồn 3V3",
        muc_dich="hạ 5 V xuống 3,3 V cấp cho MCU và cảm biến",
        linh_kien=["U3", "C1", "C2"], tin_hieu_ra=["3V3"])
    r = goi("ckm.module_set", ma="MOD-MCU", ten="Vi điều khiển",
            muc_dich="chạy firmware, làm master I2C", linh_kien=["U1"],
            tin_hieu_vao=["3V3"], tin_hieu_ra=["SDA", "SCL"], rail="3V3")
    b.kiem("Mũi tên 3V3 suy ra từ tên tín hiệu, không do mô hình vẽ",
           r.ok and {"tu": "MOD-PWR", "den": "MOD-MCU", "tin_hieu": "3V3"}
           in r.data["canh_suy_ra"], str(r.data.get("canh_suy_ra"))[:120])

    r = goi("ckm.module_set", ma="MOD-SENSE", ten="Cảm biến nhiệt",
            muc_dich="đo nhiệt độ qua I2C", linh_kien=["U2"],
            tin_hieu_vao=["3V3", "SDA", "SCL", "ALERT"])
    b.kiem("Tín hiệu ALERT chưa ai cấp thì bản đồ TỐ GIÁC",
           r.ok and r.data["tin_hieu_treo"]["vao_khong_ai_cap"] == ["ALERT"],
           str(r.data["tin_hieu_treo"])[:130])

    r = goi("diagram.render")
    b.kiem("Hình mermaid do mã sinh và hiện cả chỗ chưa nối",
           r.ok and "graph LR" in r.data["mermaid"] and "?" in r.data["mermaid"],
           r.data["mermaid"].splitlines()[0] if r.ok else str(r.error.message_vi)[:100])
    lan2 = goi("diagram.render")
    b.kiem("Vẽ hai lần ra đúng một chữ (N3, SCH17)",
           lan2.ok and lan2.data["mermaid"] == r.data["mermaid"], "xác định")

    b.phan("D · NET VÀ GỘP BẢN ĐỒ")
    goi("ckm.net_set", ten="3V3", loai="power", ap_danh_dinh="3,3 V",
        chan=[["U1", "7"], ["U2", "1"]])
    goi("ckm.net_set", ten="GND", loai="ground", chan=[["U1", "8"], ["U2", "2"]])
    r = goi("ckm.net_set", ten="SDA", loai="bus", bus="I2C1",
            chan=[["U1", "27"], ["U2", "5"]])
    b.kiem("Net nối chân của chip trong bản đồ và chân linh kiện ngoài",
           r.ok and r.data["so_chan"] == 2 and any("KHÔNG kiểm được" in c
                                                   for c in r.data["canh_bao"]),
           "; ".join(r.data["canh_bao"])[:140] if r.ok else str(r.error.message_vi)[:120])

    r = goi("ckm.net_set", ten="ALERT", loai="signal", chan=[["U2", "3"]])
    b.kiem("Net một chân bị gọi tên là gần như luôn lỗi vẽ",
           r.ok and any("MỘT chân" in c for c in r.data["canh_bao"]),
           "; ".join(r.data["canh_bao"])[:120] if r.ok else "")

    r = goi("ckm.build")
    b.kiem("Gộp xong: đủ tiền đề sinh sơ đồ",
           r.ok and r.data["du_de_sinh_so_do"] is True,
           r.data["note_vi"][:150] if r.ok else str(r.error.message_vi)[:120])
    d = r.data["cho_dut"] if r.ok else {}
    b.kiem("Chân CHƯA GÁN chỉ đếm chân có bảng chân",
           d.get("so_chan_chua_gan") == 2 and d.get("chan_chua_gan") == ["U1.14", "U1.8"],
           str(d.get("chan_chua_gan"))[:120])
    b.kiem("Chân của linh kiện chưa có datasheet được đếm RIÊNG",
           d.get("so_chan_khong_co_bang_chan") == 4,
           str(d.get("chan_khong_co_bang_chan"))[:120])
    b.kiem("Net một chân bị nêu tên", d.get("net_mot_chan") == ["ALERT"],
           str(d.get("net_mot_chan")))

    b.phan("Đ · TÁC TỬ THẬT LÀM VIỆC TRÊN BẢN ĐỒ")
    g.go("Bản đồ mạch đang có gì rồi? Chân 14 của U1 mình muốn dùng làm ICP1 để bắt "
         "sườn xung. Gán giúp mình, rồi nói còn chỗ nào của mạch chưa nối.")
    a = g.doi_xong(420)
    loi = a["loi_tac_tu_cuoi"]
    gan = ctx.store.get("pinout:U1")
    co14 = any(x["chan"] == "14" for x in (gan["canonical"]["gan"] if gan else []))
    b.kiem("Tác tử gán được chân 14 bằng công cụ, không kể miệng", co14, loi[:160])
    b.kiem("Tác tử nêu được chỗ mạch chưa nối",
           any(t in loi for t in ("ALERT", "chưa nối", "chưa gán")), loi[:200])

    # Phần này phải chạy SAU một lượt thật. Bề mặt được vẽ lại ở cuối mỗi lượt
    # (`Agent.paint`), nên đọc tab ngay sau khi tiến trình kiểm ghi vào kho sẽ thấy màn
    # hình của lượt TRƯỚC — và ca đo sẽ đỏ vì một lý do không phải lỗi sản phẩm.
    b.phan("E · TAB THIẾT KẾ HIỆN ĐƯỢC BẢN ĐỒ")
    g.mo_tab("design")
    a = g.chup("thiet-ke")
    kh = {k["code"]: k for k in a["khoi_tren_tab"]}
    b.kiem("Có bảng sơ đồ khối với đủ ba khối",
           kh.get("A5.1", {}).get("so_hang") == 3,
           "; ".join(f"{k['code']}={k.get('so_hang')}" for k in a["khoi_tren_tab"]))
    b.kiem("Tóm tắt sơ đồ khối nói ra tín hiệu chưa ai cấp",
           "ALERT" in kh.get("A5.1", {}).get("summary", ""),
           kh.get("A5.1", {}).get("summary", "")[:140])
    b.kiem("Có mã mermaid dán được ra ngoài", "A5.1b" in kh,
           kh.get("A5.1b", {}).get("summary", "")[:110])
    # Không kẹp vào một con số: lượt hội thoại ở phần Đ có thể gán thêm chân, và số
    # dòng phụ thuộc mô hình. Cái cần giữ là bảng CÓ và mỗi dòng mang tầng.
    gan = (ctx.store.get("pinout:U1") or {}).get("canonical", {}).get("gan") or []
    b.kiem("Có bảng pinout, mỗi chân mang tầng tin cậy",
           kh.get("A5.2", {}).get("so_hang", 0) >= 3
           and all(x.get("tier") for x in gan),
           f"{kh.get('A5.2', {}).get('so_hang')} dòng · tầng: "
           + ", ".join(f"{x['chan']}={x.get('tier')}" for x in gan))
    b.kiem("Có bảng netlist và nó gọi tên net một chân",
           kh.get("A5.3", {}).get("so_hang") == 4
           and "ALERT" in kh.get("A5.3", {}).get("summary", ""),
           kh.get("A5.3", {}).get("summary", "")[:150])
    b.kiem("Có khối 'bản đồ đủ chưa'", "A5.5" in kh,
           kh.get("A5.5", {}).get("summary", "")[:130])
    b.kiem("Không khối nào thuộc loại giao diện chưa biết vẽ",
           all(k["type"] in ("table", "code", "empty", "kv", "list", "text",
                             "timeline", "changesets", "procedure", "snapshots",
                             "sections", "cay")
               for k in a["khoi_tren_tab"]),
           "; ".join(f"{k['code']}:{k['type']}" for k in a["khoi_tren_tab"]))
    b.kiem("Bảng nào cũng đã qua bộ dựng markdown",
           not any("**" in k.get("chu_da_dung", "") for k in a["khoi_tren_tab"]),
           "sạch")

    # ================================================================== UNHAPPY
    b.phan("F · TÁM ĐƯỜNG HỎNG")

    b.buoc("1. Bịa một số chân")
    r = goi("ckm.pinout_set", chip="U1", chan="35", chuc_nang="GPIO")
    b.kiem("Từ chối, và liệt kê chân CÓ THẬT",
           not r.ok and r.error.code == "E8003" and "27" in r.error.message_vi,
           (r.error.message_vi if not r.ok else "lại nhận!")[:160])

    b.buoc("2. Chức năng không nằm trong AF của chân")
    r = goi("ckm.pinout_set", chip="U1", chan="14", chuc_nang="SDA")
    b.kiem("Từ chối kèm AF thật của chân",
           not r.ok and r.error.code == "E8007" and "ICP1" in r.error.message_vi,
           (r.error.message_vi if not r.ok else "lại nhận!")[:160])

    b.buoc("3. Gán trùng một chân")
    r = goi("ckm.pinout_set", chip="U1", chan="27", chuc_nang="ADC4")
    b.kiem("Từ chối, nói chân đang làm gì và AF nào còn lại",
           not r.ok and r.error.code == "E8004" and r.error.details["gan_truoc"] == "SDA",
           (r.error.message_vi if not r.ok else "lại nhận!")[:150])

    b.buoc("4. Gán lại mà không nói vì sao")
    r = goi("ckm.pinout_set", chip="U1", chan="27", chuc_nang="ADC4", thay_the=True)
    b.kiem("Từ chối vì thiếu lý do — người đọc lịch sử sau này cần nó",
           not r.ok and "vì sao" in r.error.message_vi,
           (r.error.message_vi if not r.ok else "lại nhận!")[:130])

    b.buoc("5. Chân chỉ có ở tầng ĐỒNG")
    ctx.store.put_fact({"fact_id": "f-doan", "subject": "pin:ATmega328P.15",
                        "key": "af", "value": "OC1A?", "tier": "DONG", "origin": "model",
                        "source": {}, "explain": {"summary": "mô hình đoán"}})
    r = goi("ckm.pinout_set", chip="U1", chan="15", chuc_nang="OC1A?")
    b.kiem("Tầng phỏng đoán không được vào bản đồ",
           not r.ok and r.error.code == "E8006",
           (r.error.message_vi if not r.ok else "lại nhận!")[:150])

    b.buoc("6. Vẽ khi chưa có khối nào")
    ctx2 = _ctx(du_an.parent / (du_an.name + "-rong"))
    r = ctx2.registry.run("diagram.render", {}, ctx2)
    b.kiem("Từ chối và nói gọi gì trước",
           not r.ok and r.error.alternatives == ["ckm.module_set"],
           (r.error.hint_for_agent if not r.ok else "lại vẽ!")[:130])

    b.buoc("7. Hai con cùng loại mà gọi bằng tên chip")
    goi("ckm.chip_add", chip="ATmega328P", ref="U4")
    r = goi("ckm.pinout_set", chip="ATmega328P", chan="14", chuc_nang="ICP1")
    b.kiem("HỎI con nào, không đoán hộ",
           not r.ok and r.error.code == "E8008" and r.error.details["ref"] == ["U1", "U4"],
           (r.error.message_vi if not r.ok else "đoán hộ!")[:150])

    b.buoc("8. Hoàn tác một lần gán — bản đồ có lùi theo không")
    r = goi("ckm.pinout_set", chip="U4", chan="28", chuc_nang="SCL")
    truoc = len(ctx.store.ckm_cac_canh(loai="DUOC_GAN"))
    kq = ctx.history.hoan_tac_changeset(r.data["changeset"])
    sau = len(ctx.store.ckm_cac_canh(loai="DUOC_GAN"))
    b.kiem("Hiện vật lùi thì đồ thị lùi theo — không có hai câu trả lời",
           kq.ok and sau == truoc - 1, f"{truoc} → {sau} cạnh ĐƯỢC_GÁN · {kq.message_vi[:80]}")

    print()
    return b.tong()


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    d = (REPO / "du-lieu/thu-nghiem-ckm").resolve()
    for x in (d, d.parent / (d.name + "-rong")):
        if x.exists():
            shutil.rmtree(x)
    d.mkdir(parents=True)
    (d.parent / (d.name + "-rong")).mkdir(parents=True)
    (d / "README.md").write_text("# Bo thu CKM\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
