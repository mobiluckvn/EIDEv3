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


TRAN_TUONG_THUAT = 1500


def tuong_thuat_co_hoc(messages: list[dict[str, Any]]) -> str:
    """Tường thuật phiên trước **bằng mã**, 0 token mô hình — M5-17 phần B.

    Dùng khi phiên trước **chưa chạm ngưỡng nén**, nên không có bản tóm tắt C2 nào. Lúc ấy
    khối resume chỉ nói *"chưa có bản tóm tắt nào"* — đúng, nhưng nó bỏ qua một transcript
    đang nằm sẵn trên đĩa. Phần lớn phiên thật không chạm ngưỡng nén, nên đây là trường hợp
    **thường gặp**, không phải ngoại lệ.

    Ba thứ, và chỉ ba: lời NGƯỜI nói (việc được giao), lời gọi công cụ (việc đã làm), lỗi cuối
    (chỗ đang mắc). Cố ý **không** tóm tắt lời tác tử nói: một bản rút gọn của lời nó tự nói
    là chỗ dễ nhất để một kết luận sai sống thêm một phiên.
    """
    if not messages:
        return ""
    nguoi = [str(m.get("text") or "").strip() for m in messages
             if m.get("role") == "user" and not m.get("_he_thong")]
    goi: list[str] = []
    loi = ""
    for m in messages:
        if m.get("role") != "tool":
            continue
        ten = m.get("tool") or "?"
        env = m.get("envelope") or {}
        kq = m.get("result") or {}
        ma = (kq.get("code") if isinstance(kq, dict) else "") or ""
        dong = str(env.get("summary_line") or "").strip()
        goi.append(f"- `{ten}`" + (f" → {ma}" if ma else " ok")
                   + (f" · {dong[:90]}" if dong else ""))
        if ma:
            loi = f"`{ten}` → {ma}: " + str(
                (kq.get("message_vi") if isinstance(kq, dict) else "") or "")[:160]

    if not nguoi and not goi:
        return ""
    L = ["Phiên trước CHƯA chạm ngưỡng nén nên không có bản tóm tắt. Dưới đây là tường "
         "thuật do MÃ dựng từ transcript phiên ấy — không ai tóm tắt lại, nên nó không "
         "thêm kết luận nào."]
    if nguoi:
        L.append("\n**Người đã nhờ** (3 lời cuối):")
        L += [f"- “{c[:150]}”" for c in nguoi[-3:]]
    if goi:
        L.append(f"\n**Đã gọi** ({len(goi)} lời gọi, hiện 10 cái cuối):")
        L += goi[-10:]
    if loi:
        L.append(f"\n**Lỗi cuối cùng:** {loi}")
    L.append("\nĐây là việc ĐÃ xảy ra, không phải việc cần làm tiếp. Việc tiếp theo do "
             "người dùng giao ở lượt này.")
    chu = "\n".join(L)
    return chu if len(chu) <= TRAN_TUONG_THUAT else chu[:TRAN_TUONG_THUAT] + "\n… (đã cắt)"


def dung_khoi_resume(*, ledger: Any, store: Any, history: Any,
                     tom_tat_truoc: Any = None, phuc_hoi: Any = None,
                     tuong_thuat: str = "", so_su_kien: int = 20) -> str:
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
    elif tuong_thuat:
        # Bản tóm tắt C2 thắng tường thuật cơ học khi có cả hai: nó đã qua vòng kiểm chứng
        # (§6.2), còn tường thuật thì chỉ là một bản kê việc.
        L += ["## Phiên trước tóm lại", tuong_thuat, ""]
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
        # Nói rõ phải làm GÌ với tin này, vì bản thân tin ấy mơ hồ và tốn kém khi hiểu nhầm.
        #
        # Bản cũ chỉ ghi "Lượt run-00N chưa kết thúc." Cộng với lời dặn cuối khối — *"việc dở
        # dang thì nói ra TRƯỚC khi làm"* — tác tử hiểu là phải làm nốt việc cũ, và nó **làm
        # lại đúng việc của lượt trước** thay vì việc vừa được giao. Đo được ngày 01/10/2026
        # trong phiên FPGA: bốn lượt liền lặp lại việc cũ.
        #
        # Và phần lớn trường hợp dòng này còn SAI. `turn.end` được ghi ngay lúc khối resume
        # đang dựng, nên một lượt đã xong vẫn hiện ở đây — một cuộc đua ghi/đọc, không phải
        # một lượt hỏng. Sổ kiểm lại sau đó thấy đủ cả `turn.start` lẫn `turn.end`.
        dang_do.append(
            f"- Lượt {run_cuoi} không thấy bản ghi kết thúc. Thường là tiến trình bị tắt ngay "
            "lúc đang ghi, chứ không phải việc làm dở — nên **đừng tự làm lại việc của lượt "
            "ấy**. Muốn biết nó đã làm tới đâu thì gọi `ledger.query`; nếu thật sự còn dở và "
            "ảnh hưởng tới việc vừa được giao thì **hỏi người dùng**, đừng tự quyết.")

    cho = [e for e in su_kien if e.kind == "gate" and e.data.get("state") == "open"]
    da_tra = {e.data.get("gate_id") for e in su_kien
              if e.kind == "gate" and e.data.get("state") in ("approved", "rejected")}
    # Thẻ mở mà chưa ai trả lời: nói nó HẾT HIỆU LỰC, đừng nói "đang chờ".
    #
    # Khối này chỉ được dựng khi mở lại dự án, tức là tiến trình giữ lời gọi đang treo đã
    # chết. Nói "đang chờ người trả lời" khiến tác tử ngồi đợi một câu trả lời không bao giờ
    # tới, và tệ hơn: khiến nó bảo người dùng đi bấm một cái nút đã không còn tác dụng. Câu
    # đúng là nói cho nó biết phải hỏi lại.
    for g in cho:
        if g.data.get("gate_id") not in da_tra:
            dang_do.append(
                f"- Thẻ cổng {g.data.get('gate')} ({g.data.get('gate_id')}) treo từ phiên "
                "trước và ĐÃ HẾT HIỆU LỰC — lời gọi nó chặn không còn tồn tại. Đừng chờ, "
                "đừng bảo người dùng bấm lại vào nó. Nếu việc ấy vẫn cần thì hỏi lại người "
                "dùng rồi dựng thẻ mới.")

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

    # --- 5. Dùng khối này thế nào.
    #
    # Câu dặn ở đây từng là "tự thuật lại 5–8 câu", và nó CHIẾM CHỖ câu hỏi của người:
    # người hỏi "VDD tối đa bao nhiêu", tác tử trả lời bằng một bản tóm tắt tình trạng
    # dự án. Đo được trên phiên thật. Bối cảnh không bao giờ được thay việc.
    L += ["## Dùng khối này thế nào",
          "Đây là BỐI CẢNH, không phải việc được giao. Làm đúng thứ người dùng vừa hỏi "
          "trước đã.",
          "Chỉ khi họ hỏi “dự án đang thế nào” hoặc chưa giao việc gì cụ thể thì mới "
          "thuật lại 5–8 câu từ khối này.",
          "Nếu có mục nào ở trên ảnh hưởng tới việc họ vừa giao — việc dở dang, thẻ "
          "đang chờ, sổ lệch — thì **nói ra bằng một câu** rồi vẫn làm việc vừa được giao. "
          "Nói ra không có nghĩa là đi làm nốt việc cũ: việc cũ chỉ được làm lại khi người "
          "dùng bảo làm lại.",
          "Không chắc điều gì thì gọi ledger.query, đừng đoán.",
          "</resume>"]
    return "\n".join(L)
