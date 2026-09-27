#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kiểm G6 — build/sim/test, tiêu chí nêu trước, subagent và verifier — qua GIAO DIỆN THẬT.

    .venv/bin/python tools/thu_g6.py

Điều bộ này canh, một câu: **thứ dễ nói dối nhất phải không nói dối được.**

Một công cụ biên dịch có thể "đạt" mà không sinh ra tệp; một mô phỏng có thể in ra một bản
báo cáo đẹp mà chẳng đo gì; một tiêu chí có thể được nới ra vừa khít với kết quả; một tác tử
con có thể nộp một đoạn văn trôi chảy thay cho bằng chứng. Bốn kiểu đậu giả đó đều trông hợp
lý trên màn hình, và chỉ vỡ ra khi người dùng nạp firmware vào bo thật.

Ca đo gốc: TC015–028 (biên dịch, mô phỏng, toolchain, map), TC052 (unit test + độ phủ),
TC019/TC020/TC022 (phần không mô phỏng được, treo, sửa tiêu chí để ép đạt).
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
EX = {"summary": "kiểm G6", "why": "để đo nền biên dịch – mô phỏng", "sources": [],
      "diff_prev": "—", "next": "—", "confidence": "VANG"}

# Firmware tí hon nhưng THẬT: biên dịch được cho ATmega328P, và có một hằng chiếm chỗ đo được.
FW = """#include <avr/io.h>

/* `volatile` + có người đọc: nếu không, -Os bỏ hẳn bảng và bản đồ bộ nhớ không thấy nó —
   khi đó ca đo đang đo một firmware khác với firmware nó nghĩ. */
volatile char bang_tra[256] = {0};

int main(void) {
    DDRB |= (1 << PB5);
    for (;;) {
        PORTB ^= bang_tra[TCNT0 & 0xFF];
    }
}
"""

# Mô phỏng: chỉ ĐO và in số. Không tự kết luận — đó là việc của tiêu chí.
SIM = """#include <stdio.h>
#include "../firmware/control.h"

int main(void) {
    double goc = 3.0;
    for (int i = 0; i < 100; ++i) {
        goc = buoc_mo_phong(goc);
    }
    printf("{\\"do\\": {\\"A1\\": 3.0, \\"A2\\": %.3f}}\\n", goc);
    return 0;
}
"""

CONTROL_H = """#ifndef CONTROL_H
#define CONTROL_H
double buoc_mo_phong(double goc);
#endif
"""

CONTROL_C = """#include "control.h"

/* Logic thuần: không đụng thanh ghi, nên mô phỏng chạy được chính mã này. */
double buoc_mo_phong(double goc) {
    return goc * 0.95;
}
"""

TEST = """#include <stdio.h>
#include "../firmware/control.h"

int main(void) {
    double g = buoc_mo_phong(10.0);
    int ok = (g < 10.0);
    printf("{\\"ca\\": [{\\"ten\\": \\"giam_dan\\", \\"dat\\": %s, \\"vi\\": \\"%.3f\\"}]}\\n",
           ok ? "true" : "false", g);
    return 0;
}
"""

SIM_TREO = """#include <stdio.h>
int main(void) { volatile int co = 0; while (!co) { } printf("{}\\n"); return 0; }
"""


def _ctx(du_an: pathlib.Path):
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
        eide_md = EideMd.load(config.paths.eide_md, create_name="thu-g6")
        registry = build_registry(Features())
        ids = IdGen(paths.state_dir)
        ledger = Ledger(paths.ledger)
        history = History(paths=paths, store=store, ledger=ledger, ids=ids)
        run_id = "run-g6"
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
    subprocess.Popen([str(REPO / "ui/EIDEApp/EIDE.app/Contents/MacOS/EIDE")],
                     env={**os.environ}, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    g.san_sang(90)
    print(f"{XANH}Kênh kiểm thử giao diện đã mở{HET}\n")

    ctx = _ctx(du_an)
    reg = ctx.registry

    def goi(cong_cu, /, **kw):
        if "explain" in (reg.get(cong_cu).params.get("properties") or {}):
            kw.setdefault("explain", EX)
        return reg.run(cong_cu, kw, ctx)

    # ================================================================ A · môi trường
    b.phan("A · MÔI TRƯỜNG (TC018)")
    r = goi("env.check", isa="avr8")
    b.kiem("Liệt kê công cụ CÓ và THIẾU, mỗi cái nói để làm gì",
           r.ok and len(r.data["cong_cu"]) >= 4
           and all(c["de_lam_gi"] for c in r.data["cong_cu"]),
           f"{r.data['so_co']} có / {r.data['so_thieu']} thiếu" if r.ok else "")
    b.kiem("KHÔNG tự tuyên bố “sẵn sàng biên dịch”",
           r.ok and "sẵn sàng" not in r.data["note_vi"].lower(),
           r.data["note_vi"][:130] if r.ok else "")
    r = goi("env.check", isa="armv7-m")
    b.kiem("Kiến trúc lạ thì nói thẳng, không chọn một kiến trúc gần giống",
           r.ok and r.data["isa_chua_biet"] and "gần giống" in r.data["note_vi"],
           r.data["note_vi"][:150] if r.ok else "")
    r = goi("tool.install", cong_cu="rm -rf /", isa="avr8")
    b.kiem("Lệnh cài KHÔNG do mô hình soạn — chỉ cài thứ có trong bảng",
           not r.ok and r.error.code == "E4005"
           and "đừng soạn lệnh shell" in r.error.hint_for_agent,
           (r.error.message_vi if not r.ok else "lại cài!")[:130])

    # ================================================================ B · biên dịch
    b.phan("B · BIÊN DỊCH VÀ BẢN ĐỒ BỘ NHỚ (TC015, TC017, TC021)")
    (du_an / "firmware").mkdir(parents=True, exist_ok=True)
    (du_an / "firmware/firmware.ino").write_text(FW, "utf-8")
    for fid, k, v in (("f-flash", "flash.size", 32768), ("f-ram", "ram.size", 2048)):
        ctx.store.put_fact({"fact_id": fid, "subject": "chip:ATmega328P", "key": k,
                            "value": v, "unit": "B", "tier": "BAC", "origin": "extract",
                            "source": {"doc_id": "DS"}, "explain": {}})
    r = goi("build.compile")
    b.kiem("Biên dịch bằng chuỗi công cụ THẬT và có tệp ảnh trên đĩa",
           r.ok and r.data["dat"] and r.data["tep_ra"],
           f"{r.data['cong_cu']} → {r.data['tep_ra']}" if r.ok else
           str(r.error.message_vi)[:150])
    b.kiem("Nói tỉ lệ Flash/SRAM so với ngân sách lấy từ Fact",
           r.ok and r.data["ty_le_flash"] is not None and r.data["vua_chip"] is True,
           f"Flash {r.data['flash']}/{r.data['flash_toi_da']} B" if r.ok else "")

    (du_an / "firmware/firmware.ino").write_text(
        "#include <avr/io.h>\nint main(void){ ham_khong_co(); }\n", "utf-8")
    r = goi("build.compile")
    b.kiem("Lỗi biên dịch trả về TỪNG DÒNG có toạ độ để sửa đúng chỗ (TC017)",
           not r.ok and r.error.details.get("loi")
           and r.error.details["loi"][0]["dong"] == 2,
           str(r.error.details["loi"][0] if not r.ok else "")[:140])
    (du_an / "firmware/firmware.ino").write_text(FW, "utf-8")
    goi("build.compile")

    r = goi("build.map")
    b.kiem("Bản đồ bộ nhớ nói CÁI GÌ chiếm chỗ, không chỉ chiếm bao nhiêu (TC021)",
           r.ok and r.data["section"] and r.data["symbol"]
           and any(s["ten"] == "bang_tra" for s in r.data["symbol"]),
           ", ".join(f"{s['ten']}={s['byte']}" for s in r.data["symbol"][:3])
           if r.ok else str(r.error.message_vi)[:130])

    # ================================================================ C · tiêu chí
    b.phan("C · TIÊU CHÍ NÊU TRƯỚC (TC016, TC019, TC022)")
    (du_an / "firmware/control.h").write_text(CONTROL_H, "utf-8")
    (du_an / "firmware/control.c").write_text(CONTROL_C, "utf-8")
    (du_an / "sim").mkdir(exist_ok=True)
    (du_an / "sim/plant.c").write_text(SIM, "utf-8")

    r = goi("sim.run")
    b.kiem("Chạy mô phỏng khi CHƯA có tiêu chí thì bị từ chối",
           not r.ok and r.error.code == "E4008"
           and "vừa khít với kết quả" in r.error.hint_for_agent,
           (r.error.message_vi if not r.ok else "lại chạy!")[:130])

    AS = [{"ma": "A1", "mo_ta": "Góc nghiêng lớn nhất", "phep_so": "<=", "nguong": 15.0,
           "don_vi": "°", "do_req": "REQ-BAL-01", "nguon_nguong": "§13.4 tài liệu"},
          {"ma": "A2", "mo_ta": "Góc ở cuối", "phep_so": "<=", "nguong": 2.0,
           "don_vi": "°", "do_req": "REQ-BAL-01", "nguon_nguong": "§13.4 tài liệu"}]
    r = goi("sim.criteria", ma="sim-01", ten="Cân bằng", **{"assert": AS},
            khong_mo_phong_duoc=[{"gi": "WS2812", "vi_sao": "không mô hình 800 kHz",
                                  "cach_bu": "đo bằng oscilloscope"}])
    b.kiem("Ghi tiêu chí được, nhưng CHƯA xác nhận thì nói rõ",
           r.ok and r.data["da_xac_nhan"] is False and "CHƯA có xác nhận" in r.data["note_vi"],
           r.data["note_vi"][:140] if r.ok else "")
    r = goi("sim.run")
    b.kiem("Tiêu chí chưa ai xác nhận thì KHÔNG chạy mô phỏng",
           not r.ok and r.error.code == "E4009"
           and "Đừng tự xác nhận hộ" in r.error.hint_for_agent,
           (r.error.message_vi if not r.ok else "lại chạy!")[:130])

    goi("sim.criteria", ma="sim-01", ten="Cân bằng", **{"assert": AS},
        khong_mo_phong_duoc=[{"gi": "WS2812", "vi_sao": "không mô hình 800 kHz",
                              "cach_bu": "đo bằng oscilloscope"}],
        trich_loi="đúng rồi, 15 độ và 2 độ")
    r = goi("sim.run")
    b.kiem("Chạy được, và kết luận do SO SỐ ĐO với ngưỡng",
           r.ok and r.data["dat"] is True and r.data["xet"]["dem"]["dat"] == 2,
           r.data["note_vi"][:150] if r.ok else str(r.error.message_vi)[:150])
    b.kiem("Kết quả LUÔN kèm phần không mô phỏng được (TC019)",
           r.ok and "KHÔNG mô phỏng được" in r.data["note_vi"]
           and "WS2812" in r.data["note_vi"],
           r.data["note_vi"][-180:] if r.ok else "")

    # Bỏ mất danh sách "không mô phỏng được" thì công cụ phải NÓI RA.
    r = goi("sim.criteria", ma="sim-01", **{"assert": AS}, trich_loi="thử bỏ đi")
    b.kiem("Bỏ mất phần “không mô phỏng được” thì CẢNH BÁO, không im lặng",
           r.ok and r.data["mat_khong_mo_phong_duoc"]
           and "BỎ MẤT" in r.data["note_vi"],
           r.data["note_vi"][:150] if r.ok else "")

    # Số đo thiếu → CHƯA ĐỦ DỮ KIỆN, không phải đạt.
    goi("sim.criteria", ma="sim-01", khong_mo_phong_duoc=[
            {"gi": "WS2812", "vi_sao": "không mô hình 800 kHz",
             "cach_bu": "đo bằng oscilloscope"}], **{"assert": AS + [
        {"ma": "A9", "mo_ta": "Thứ chương trình không đo", "phep_so": "<=", "nguong": 1,
         "nguon_nguong": "thử"}]}, trich_loi="thêm một tiêu chí nữa")
    r = goi("sim.run")
    b.kiem("Thiếu số đo là CHƯA ĐỦ DỮ KIỆN, không phải đạt (N6)",
           r.ok and r.data["dat"] is False
           and r.data["xet"]["dem"]["chua_do_duoc"] == 1,
           r.data["note_vi"][:150] if r.ok else "")

    # ================================================================ D · treo
    b.phan("D · MÔ PHỎNG TREO (TC020)")
    (du_an / "sim/plant.c").write_text(SIM_TREO, "utf-8")
    goi("sim.criteria", ma="sim-01", **{"assert": AS}, timeout_s=3,
        khong_mo_phong_duoc=[{"gi": "WS2812", "vi_sao": "không mô hình 800 kHz",
                              "cach_bu": "đo bằng oscilloscope"}],
        trich_loi="giữ nguyên tiêu chí")
    r = goi("sim.run")
    b.kiem("Quá thời gian chờ thì DỪNG và chỉ chỗ tìm vòng chờ",
           not r.ok and r.error.code == "E4010"
           and "vòng chờ cờ không bao giờ bật" in r.error.hint_for_agent,
           (r.error.message_vi if not r.ok else "chạy xong?!")[:140])
    (du_an / "sim/plant.c").write_text(SIM, "utf-8")

    # ================================================================ Đ · unit test
    b.phan("Đ · UNIT TEST TRÊN MÁY CHỦ (TC052)")
    r = goi("test.run")
    b.kiem("Chưa có test thì nói thẳng, không coi im lặng là đạt",
           not r.ok and r.error.code == "E4011"
           and "đừng coi im lặng là đạt" in r.error.hint_for_agent,
           (r.error.message_vi if not r.ok else "")[:130])
    (du_an / "test").mkdir(exist_ok=True)
    (du_an / "test/test_control.c").write_text(TEST, "utf-8")
    r = goi("test.run")
    b.kiem("Đếm được ca đạt/hỏng từ dữ liệu, không từ lời văn",
           r.ok and r.data["so_ca"] == 1 and r.data["so_dat"] == 1,
           r.data["note_vi"][:150] if r.ok else str(r.error.message_vi)[:130])
    b.kiem("Độ phủ: đo được thì nói số, không đo được thì nói vì sao",
           r.ok and (r.data["do_phu"].get("do_duoc") is True
                     or bool(r.data["do_phu"].get("vi_sao"))),
           str(r.data["do_phu"])[:140] if r.ok else "")

    # ================================================================ E · subagent
    b.phan("E · SUBAGENT VÀ VERIFIER (§B5, N6)")
    from eide import subagent as SA

    b.kiem("Sáu tác tử con, mỗi cái một tập công cụ riêng",
           len(SA.SUBAGENT) == 6
           and all(d.cong_cu for d in SA.SUBAGENT.values()),
           ", ".join(SA.SUBAGENT))
    ghi = {"fs.write", "fs.edit", "build.compile", "sim.run", "sim.criteria", "test.run"}
    b.kiem("Verifier CHỈ có công cụ đọc — ghi được thì nó sửa được cho đạt",
           not (set(SA.SUBAGENT["verifier"].cong_cu) & ghi),
           ", ".join(SA.SUBAGENT["verifier"].cong_cu[:6]))
    b.kiem("Verifier KHÔNG thấy đề bài, chỉ thấy báo cáo và bằng chứng",
           SA.SUBAGENT["verifier"].doc_duoc_viec is False, "doc_duoc_viec = False")

    bc = SA.doc_bao_cao('{"tom_tat":"xong","da_lam":["a"],"bang_chung":[],'
                        '"chua_lam":[],"ket_luan":"dat","do_tin":"BAC"}',
                        subagent="firmware")
    b.kiem("Tuyên ĐẠT mà không bằng chứng nào thì báo cáo KHÔNG hợp lệ",
           not bc.hop_le and "KHÔNG có bằng chứng" in bc.loi_luoc_do[0],
           "; ".join(bc.loi_luoc_do))
    bc2 = SA.doc_bao_cao('{"tom_tat":"biên dịch sạch","da_lam":["a"],'
                         '"bang_chung":[{"kind":"file","ref":"x.hex"}],"chua_lam":[],'
                         '"ket_luan":"dat","do_tin":"BAC"}', subagent="firmware")
    b.kiem("firmware/sim tuyên ĐẠT thì PHẢI qua verifier",
           SA.can_goi_verifier(bc2) is True
           and SA.can_goi_verifier(SA.doc_bao_cao(
               '{"tom_tat":"x","da_lam":[],"bang_chung":[{"ref":"a"}],"chua_lam":[],'
               '"ket_luan":"dat","do_tin":"BAC"}', subagent="design-review")) is False,
           "firmware: có · design-review: không")
    kc = SA.doc_bao_cao('{"tom_tat":"không có tệp ảnh nào","da_lam":[],'
                        '"bang_chung":[{"ref":".eide/build"}],"chua_lam":[],'
                        '"ket_luan":"khong_dat","do_tin":"BAC"}', subagent="verifier")
    gop = SA.gop_kiem_chung(bc2, kc)
    b.kiem("Verifier bác thì kết luận bị HẠ, và lý do được giữ lại",
           gop.ket_luan == "khong_dat"
           and any("Verifier bác" in x for x in gop.chua_lam),
           "; ".join(gop.chua_lam)[:140])

    # ================================================================ G · skill
    b.phan("G · SKILL NẠP THEO NGỮ CẢNH (§B5)")
    r = goi("skill.load")
    b.kiem("Có skill, và skill nào cũng nói KHI NÀO dùng",
           r.ok and r.data["so_skill"] >= 5
           and all(s["khi_nao"] for s in r.data["skill"]),
           ", ".join(s["ten"] for s in r.data["skill"]))
    r = goi("skill.load", ten="sim-criteria-first")
    b.kiem("Nạp được nội dung đầy đủ",
           r.ok and "Nêu tiêu chí trước" in r.data["noi_dung"],
           r.data["khi_nao"][:120] if r.ok else "")
    from eide.context.assemble import build_skills_hint
    from eide.skills import goi_y_cho_ngu_canh
    ds = goi_y_cho_ngu_canh()
    b.kiem("Gợi ý ĐÚNG lúc: câu về mô phỏng thì gợi ý sim-criteria-first",
           "sim-criteria-first" in build_skills_hint(ds, "chạy mô phỏng giúp mình", 300),
           "khớp từ khoá")
    b.kiem("Câu không liên quan thì KHÔNG gợi ý gì",
           build_skills_hint(ds, "hôm nay trời đẹp", 300) == "",
           "gợi ý sai chỗ dạy người ta bỏ qua gợi ý")

    # ================================================================ H · bề mặt
    b.phan("H · BỀ MẶT (E2 dòng 337–338)")
    g.ve_lai()
    g.mo_tab("simulation")
    time.sleep(1.0)
    a = g.chup("mo-phong")
    kh = {k["code"]: k for k in a["khoi_tren_tab"]}
    ma = [k["code"] for k in a["khoi_tren_tab"]]
    b.kiem("Tab Mô phỏng hiện TIÊU CHÍ trước, KẾT QUẢ sau",
           "criteria:sim-01" in ma and "sim_result:can-bang" in ma
           and ma.index("criteria:sim-01") < ma.index("sim_result:can-bang"),
           " → ".join(ma))
    b.kiem("Bảng tiêu chí sửa được ngưỡng ngay trên đó",
           kh.get("criteria:sim-01", {}).get("cot_sua_loai") == "criteria",
           str(kh.get("criteria:sim-01", {}).get("cot_sua_loai")))
    b.kiem("Phần KHÔNG mô phỏng được có khối riêng",
           any(c.endswith(":khong-mo-phong") for c in ma),
           [c for c in ma if "khong-mo-phong" in c] or "không có")

    g.mo_tab("code")
    time.sleep(1.0)
    a = g.chup("ma-nguon")
    ma = [k["code"] for k in a["khoi_tren_tab"]]
    b.kiem("Tab Mã nguồn hiện kết quả biên dịch và bản đồ bộ nhớ",
           "build:firmware" in ma and "analysis:build-map" in ma, " · ".join(ma))
    b.kiem("Giao diện vẽ được mọi khối trên hai tab này",
           all(k.get("ve_duoc") is not False for k in a["khoi_tren_tab"]),
           "; ".join(k["code"] for k in a["khoi_tren_tab"]
                     if k.get("ve_duoc") is False) or "sạch")

    print()
    return b.tong()


def main() -> int:
    from eide.config import load_dotenv
    load_dotenv()
    d = (REPO / "du-lieu/thu-nghiem-g6").resolve()
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / "README.md").write_text("# Bo thu G6\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(d)], check=True)
    return chay(d)


if __name__ == "__main__":
    raise SystemExit(main())
