# -*- coding: utf-8 -*-
"""Mở lại dự án — EIDE-MEM-42 §7.5. Năm bước.

Bằng chứng đo của tài liệu là TC065: `previous_session.summary = null`. Bản v1.x sinh
một trường `summary` riêng, và khi nó rỗng thì mô hình mở lại dự án mà **không biết là
mình không biết** — nó kể tiếp như thể vẫn nhớ.

Cách chữa ở đây là bỏ hẳn trường đó: không có một chỗ nào để null. Khối `<resume>` được
dựng **bằng mã** từ những thứ có thật trên đĩa — sổ cái, kho, EIDE.md, bản tóm tắt phiên
trước — và mô hình tự thuật lại 5–8 câu từ đó. Không có gì thì khối nói "không có gì",
và đó là một câu trả lời đúng.

Bước 3 (kiểm toàn vẹn) có một quy tắc đáng nói: lệch thì **dùng sổ cái làm chuẩn** và
báo người, chứ không im lặng chọn bên nào. Sổ cái là thứ duy nhất chỉ ghi thêm.
"""

from __future__ import annotations

from typing import Any


def dung_khoi_resume(*, ledger: Any, store: Any, history: Any,
                     tom_tat_truoc: Any = None, phuc_hoi: Any = None,
                     so_su_kien: int = 20) -> str:
    """Khối `<resume>` cho lượt đầu tiên của một phiên mở lại."""
    su_kien = list(ledger.read())
    if not su_kien:
        return ""                     # dự án mới tinh — không có gì để thuật lại

    L = ["<resume>",
         "Đây là lần mở lại dự án. Những gì dưới đây do mã dựng từ sổ cái và kho, "
         "không phải do bạn nhớ.",
         ""]

    # --- 1. Bản tóm tắt phiên trước.
    if tom_tat_truoc is not None:
        L += ["## Phiên trước tóm lại", tom_tat_truoc.van_ban(), ""]
    else:
        L += ["## Phiên trước tóm lại",
              "Chưa có bản tóm tắt nào — phiên trước chưa chạm ngưỡng nén.", ""]

    # --- 2. Sổ cái: việc dở, thẻ chờ, sửa của người chưa nhắc, thao tác không lùi được.
    L.append("## Đang dở dang")
    dang_do: list[str] = []

    run_cuoi = None
    da_xong: set[str] = set()
    for ev in su_kien:
        if ev.kind == "turn.start":
            run_cuoi = ev.data.get("run_id")
        elif ev.kind == "turn.end":
            da_xong.add(ev.data.get("run_id"))
    if run_cuoi and run_cuoi not in da_xong:
        dang_do.append(f"- Lượt {run_cuoi} chưa kết thúc.")

    cho = [e for e in su_kien if e.kind == "gate" and e.data.get("state") == "open"]
    da_tra = {e.data.get("gate_id") for e in su_kien
              if e.kind == "gate" and e.data.get("state") in ("approved", "rejected")}
    for g in cho:
        if g.data.get("gate_id") not in da_tra:
            dang_do.append(f"- Thẻ cổng {g.data.get('gate')} "
                           f"({g.data.get('gate_id')}) đang chờ người trả lời.")

    if history is not None:
        chua_nhac = history.log.human_unacknowledged()
        for cs in chua_nhac[:5]:
            hv = ", ".join(t.artefact_id for t in cs.touches)
            dang_do.append(f"- Người đã sửa {hv} ({cs.id}) mà bạn chưa nhắc tới.")

    khong_lui = [e for e in su_kien
                 if e.kind == "changeset" and e.data.get("reversible") is False]
    if khong_lui:
        c = khong_lui[-1]
        dang_do.append(f"- Thao tác KHÔNG hoàn tác được gần nhất: {c.data.get('summary')} "
                       f"({c.data.get('id')}). Nó đã xảy ra thật.")

    if phuc_hoi is not None and getattr(phuc_hoi, "goi_dang_do", None):
        for g in phuc_hoi.goi_dang_do:
            if g["co_tac_dung_phu"]:
                dang_do.append(f"- {g['tool']} đã bắt đầu mà không có kết quả — "
                               "KHÔNG chạy lại, hỏi người dùng.")

    L += dang_do or ["- Không có việc nào dở dang."]
    L.append("")

    # --- 3. Bản ưng ý gần nhất và khoảng cách.
    if history is not None:
        try:
            ds = history.danh_sach_snapshot()
        except Exception:                                        # noqa: BLE001
            ds = []
        L.append("## Mốc quay về gần nhất")
        if ds:
            s = ds[-1]
            L.append(f"- “{s.get('name') or s.get('ten') or s['id']}” ({s['id']}), "
                     f"cách đây {s.get('khoang_cach', 0)} thay đổi.")
        else:
            L.append("- Chưa ghi bản ưng ý nào. Sau một mốc đáng nhớ hãy ĐỀ XUẤT ghi.")
        L.append("")

    # --- 4. Kiểm toàn vẹn. Lệch thì sổ cái là chuẩn, và phải NÓI RA.
    L.append("## Toàn vẹn")
    ok_l, vi_l = ledger.verify()
    L.append(f"- Sổ cái: {vi_l}")
    if history is not None:
        try:
            ok_c, vi_c = history.log.verify()
            L.append(f"- Sổ changeset: {vi_c}")
            if not ok_c:
                L.append("- **Lệch.** Lấy sổ cái làm chuẩn và báo người dùng trước khi "
                         "làm bất cứ việc gì ghi vào kho.")
        except Exception:                                        # noqa: BLE001
            pass
    if not ok_l:
        L.append("- **Sổ cái lệch.** Báo người dùng; chuyển sang chỉ đọc.")
    L.append("")

    # --- 5. Việc của mô hình ở lượt này.
    L += ["## Việc của bạn ngay bây giờ",
          "Tự thuật lại 5–8 câu: dự án đang ở đâu, đã quyết những gì, việc tiếp theo là "
          "gì. Chỉ dùng thông tin trong khối này và <inventory>. Không chắc thì gọi "
          "ledger.query, đừng đoán.",
          "</resume>"]
    return "\n".join(L)
