#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sơ đồ mermaid phải RA HÌNH, không ra khối mã — đo qua app thật.

    .venv/bin/python tools/thu_so_do.py

Bộ này hỏi bộ dựng của app bằng lệnh `so_do_thu` trên kênh kiểm giao diện: một đoạn markdown
ra những khối gì, khối mermaid có vẽ được không, và **vẽ ra những nhãn nào**.

## Vì sao không bơm một dòng giả vào hội thoại

Cách dễ hơn là thêm một lệnh thử kiểu "hiện câu này như lời tác tử" rồi chụp màn hình. Không
làm, vì I2 nói hội thoại là **hình chiếu của sổ cái** — một móc thử phá bất biến ấy sẽ che lỗi
chứ không tìm ra lỗi. `so_do_thu` chỉ gọi hàm thuần `Markdown.tach` + `DocSoDo`, và đó đúng là
thứ đang cần đo.

## Nguồn của ca kiểm

**Không tự bịa sơ đồ.** Hai tệp thật trong kho:

* `docs/md/EIDE-C4-46_…md` — `graph TB` có `subgraph`, nhãn `<br/>`, biểu tượng;
* `du-lieu/stm32f469-freertos/tai-lieu-kien-truc-c4.md` — `sequenceDiagram` có `autonumber`,
  `actor`, `loop`, `Note over`.

Thêm ba ca dựng tay cho những chỗ **phải đỏ**: kiểu chưa vẽ được, nguồn rỗng, và một khối
```bash — thứ không được biến thành sơ đồ.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

from thu_giao_dien import Bo, GiaoDien                                    # noqa: E402

DU_AN = REPO / "du-lieu/thu-so-do"
RA_ANH = REPO / "docs/review-v3/test/ket-qua-so-do"


def _mermaid_dau_tien(tep: pathlib.Path, kieu: str) -> str:
    t = tep.read_text("utf-8")
    for m in re.finditer(r"```mermaid\s*\n(.*?)```", t, re.S):
        if m.group(1).strip().startswith(kieu):
            return "```mermaid\n" + m.group(1).rstrip() + "\n```"
    raise SystemExit(f"không tìm thấy sơ đồ {kieu} trong {tep}")


def chay() -> int:
    from eide.config import load_dotenv

    load_dotenv()
    if DU_AN.exists():
        shutil.rmtree(DU_AN)
    DU_AN.mkdir(parents=True)
    (DU_AN / "ghi-chu.md").write_text("# Ghi chú\n\nDự án để đo bộ vẽ sơ đồ.\n", "utf-8")

    subprocess.run(["pkill", "-f", "EIDE.app/Contents/MacOS/EIDE"], check=False)
    time.sleep(1)
    subprocess.run(["defaults", "write", "vn.mobiluck.eide", "duAnPath",
                    "-string", str(DU_AN)], check=True)
    subprocess.Popen(["open", "-a", str(REPO / "ui/EIDEApp/EIDE.app")])

    g = GiaoDien(DU_AN)
    g.san_sang(40)
    bo = Bo("so-do")

    def thu(md: str) -> dict:
        g._gui({"ui": "so_do_thu", "md": md})
        return g._doi("so_do_thu", 20)

    # ------------------------------------------------------- 1. sơ đồ tuần tự THẬT
    bo.phan("Sơ đồ tuần tự thật của tác tử (stm32f469-freertos)")
    md = _mermaid_dau_tien(
        REPO / "du-lieu/stm32f469-freertos/tai-lieu-kien-truc-c4.md", "sequenceDiagram")
    a = thu(md)
    sd = (a.get("so_do") or [{}])[0]
    bo.kiem("Ra khối `sơ-đồ`, KHÔNG phải `khối-mã`",
            a.get("khoi") == ["sơ-đồ"], str(a.get("khoi")))
    bo.kiem("Vẽ được", sd.get("ve_duoc") is True, sd.get("tom_tat", ""))
    nhan = sd.get("nhan") or []
    bo.kiem("Đọc đủ 7 vai", "7 vai" in sd.get("tom_tat", ""), sd.get("tom_tat", ""))
    bo.kiem("Giữ nhãn tiếng Việt có dấu",
            any("Người dùng" in x for x in nhan), str(nhan[:3]))
    bo.kiem("`loop` thành khối, không thành tin nhắn",
            any(x.startswith("loop ") for x in nhan), str([x for x in nhan if "loop" in x]))
    bo.kiem("`Note over` giữ được và ĐÃ BỎ thẻ `<br/>`",
            any("So khớp vùng nút" in x for x in nhan)
            and not any("<br" in x for x in nhan),
            str([x for x in nhan if "So khớp" in x])[:160])
    bo.kiem("Không nhãn nào còn cú pháp mermaid (`->>`, `[`, `\"`)",
            not any(("->>" in x or "-->>" in x) for x in nhan), str(nhan[:6]))

    g._gui({"ui": "anh_so_do", "md": md, "tep": str(RA_ANH / "tuan-tu.png")})
    g._doi("anh_so_do", 30)

    # ------------------------------------------------------- 2. sơ đồ khối THẬT
    bo.phan("Sơ đồ khối thật (tài liệu C4) — có subgraph")
    md2 = _mermaid_dau_tien(REPO / "docs/md/EIDE-C4-46_Kien_truc_theo_mo_hinh_C4.md", "graph")
    a2 = thu(md2)
    sd2 = (a2.get("so_do") or [{}])[0]
    bo.kiem("Ra khối `sơ-đồ`", a2.get("khoi") == ["sơ-đồ"], str(a2.get("khoi")))
    bo.kiem("Vẽ được", sd2.get("ve_duoc") is True, sd2.get("tom_tat", ""))
    nhan2 = sd2.get("nhan") or []
    bo.kiem("Nhãn nhiều dòng (`<br/>`) đã thành xuống dòng, không còn thẻ",
            not any("<br" in x for x in nhan2), str([x for x in nhan2 if "<br" in x]))
    bo.kiem("Không nhãn nào còn dấu nháy bọc của mermaid",
            not any(x.startswith('"') for x in nhan2), str(nhan2[:4]))

    g._gui({"ui": "anh_so_do", "md": md2, "tep": str(RA_ANH / "so-do-khoi.png")})
    g._doi("anh_so_do", 30)

    # ------------------------------------------------------- 3. sơ đồ lõi tự sinh
    #
    # `ckm.mermaid()` là nguồn sinh sơ đồ CHẮC CHẮN CÒN — nó nằm trong lõi, không phụ thuộc
    # tác tử viết gì. Nếu bộ đọc chỉ hợp với cách viết của mô hình thì ca này sẽ đỏ.
    bo.phan("Sơ đồ do LÕI sinh (`ckm.mermaid`), không phải mô hình viết")
    from eide.knowledge import ckm as K

    ms = [K.Module(ma="MOD-MCU", ten="Vi điều khiển", linh_kien=["STM32F469NIH6"],
                   tin_hieu_vao=["VDD"], tin_hieu_ra=["I2C1"]),
          K.Module(ma="MOD-LCD", ten="Màn hình", linh_kien=["OTM8009A"],
                   tin_hieu_vao=["I2C1"], tin_hieu_ra=[])]
    md3 = "```mermaid\n" + K.mermaid(ms) + "\n```"
    a3 = thu(md3)
    sd3 = (a3.get("so_do") or [{}])[0]
    bo.kiem("Vẽ được sơ đồ của lõi", sd3.get("ve_duoc") is True,
            sd3.get("tom_tat", "") + " | " + md3.replace("\n", " ⏎ ")[:120])
    bo.kiem("Giữ được nhãn tín hiệu trên đường nối",
            any(x == "I2C1" for x in (sd3.get("nhan") or [])), str(sd3.get("nhan")))

    # ------------------------------------------------------- 4. những chỗ PHẢI đỏ
    bo.phan("Biên: chỗ nào bộ vẽ phải nói KHÔNG")
    a4 = thu("```mermaid\ngantt\n  title Lịch\n  section A\n  x :a1, 2026-01-01, 3d\n```")
    sd4 = (a4.get("so_do") or [{}])[0]
    bo.kiem("Kiểu chưa vẽ được thì `ve_duoc = false` (không vẽ bừa)",
            sd4.get("ve_duoc") is False, json.dumps(sd4, ensure_ascii=False)[:160])
    bo.kiem("Và nói đúng TÊN kiểu ấy", sd4.get("kieu") == "gantt", str(sd4.get("kieu")))

    a5 = thu("```bash\ngraph LR\n```")
    bo.kiem("Khối `bash` KHÔNG bị biến thành sơ đồ",
            a5.get("khoi") == ["khối-mã"], str(a5.get("khoi")))

    a6 = thu("```mermaid\n```")
    sd6 = (a6.get("so_do") or [{}])[0]
    bo.kiem("Nguồn rỗng không làm vỡ gì", sd6.get("ve_duoc") is False,
            json.dumps(a6.get("so_do"), ensure_ascii=False)[:120])

    # ------------------------------------------------------- 5. chữ người nhìn thấy
    bo.phan("`chuThuan` — thứ bộ quét giao diện hỏi")
    bo.kiem("Trả NHÃN trong hình, không trả cú pháp mermaid",
            "-->" not in (a2.get("chu_thuan") or "")
            and "sequenceDiagram" not in (a.get("chu_thuan") or ""),
            (a2.get("chu_thuan") or "")[:120])

    print(f"\n  Ảnh sơ đồ: {RA_ANH}")
    return bo.tong()


if __name__ == "__main__":
    raise SystemExit(chay())
