# -*- coding: utf-8 -*-
"""M1-01 — dịch lịch sử nội bộ sang `contents` của Gemini.

Đo hàm thuần `_to_contents`, không gọi mạng và không dựng client: `GeminiGateway.__new__`
cho một đối tượng chưa chạy `__init__`, đủ để gọi một method không đụng `self.client`.

Cái được canh ở đây là hình dạng request: một lượt mô hình có N `function_call` thì gói
kết quả gửi lại phải là MỘT `Content` chứa N `function_response` mang đúng N id — đó là
dạng mà API đọc được. Lịch sử nội bộ trên đĩa không đổi dạng; mọi thứ ở đây chỉ xảy ra
lúc dựng request.
"""


def _gw():
    from eide.llm.gemini import GeminiGateway

    return GeminiGateway.__new__(GeminiGateway)


def _msgs_mo_hinh_hai_goi():
    """Lịch sử ĐÚNG như lõi sinh ra sau một lượt hai lời gọi kèm một lời nhắc chen giữa."""
    return [
        {"role": "user", "text": "đọc hộ hai tệp"},
        {"role": "model", "text": "", "tool_calls": [{"id": "c1", "tool": "fs.read", "args": {}},
                                                     {"id": "c2", "tool": "fs.read", "args": {}}],
         "parts": [{"type": "call", "name": "fs.read", "args": {}, "id": "c1", "sig": None},
                   {"type": "call", "name": "fs.read", "args": {}, "id": "c2", "sig": None}]},
        {"role": "tool", "tool_call_id": "c1", "tool": "fs.read", "result": {"ok": True}},
        {"role": "user", "_he_thong": True, "text": "<system-reminder>nhắc</system-reminder>"},
        {"role": "tool", "tool_call_id": "c2", "tool": "fs.read", "result": {"ok": True}},
    ]


def test_gop_ket_qua_mot_content_co_id():
    """TC-M1-01-04 — hai kết quả thành MỘT Content hai part, mang id c1 và c2."""
    contents = _gw()._to_contents(_msgs_mo_hinh_hai_goi())

    assert [c.role for c in contents] == ["user", "model", "user", "user"], \
        [(c.role, len(c.parts or [])) for c in contents]
    goi = contents[2]
    fr = [p.function_response for p in (goi.parts or []) if p.function_response]
    assert len(fr) == 2, f"phải gộp hai kết quả vào một Content, đang có {len(fr)}"
    assert [f.id for f in fr] == ["c1", "c2"], [f.id for f in fr]
    assert [f.name for f in fr] == ["fs.read", "fs.read"]
    # Lời nhắc chen giữa bị dời xuống SAU nhóm kết quả, không bị mất.
    assert contents[3].parts[0].text == "<system-reminder>nhắc</system-reminder>"


def test_lich_su_dung_san_khong_bi_doi():
    """TC-M1-01-05 — ca âm: lịch sử vốn đã chuẩn thì số Content và thứ tự vai y như trước."""
    msgs = [
        {"role": "user", "text": "đọc hộ một tệp"},
        {"role": "model", "text": "", "tool_calls": [{"id": "c1", "tool": "fs.read", "args": {}}],
         "parts": [{"type": "call", "name": "fs.read", "args": {}, "id": "c1", "sig": None}]},
        {"role": "tool", "tool_call_id": "c1", "tool": "fs.read", "result": {"ok": True}},
        {"role": "user", "text": "cảm ơn"},
    ]
    contents = _gw()._to_contents(msgs)

    assert len(contents) == 4
    assert [c.role for c in contents] == ["user", "model", "user", "user"]
    assert contents[3].parts[0].text == "cảm ơn"
