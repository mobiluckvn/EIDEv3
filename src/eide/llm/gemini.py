# -*- coding: utf-8 -*-
"""Adapter Gemini (google-genai).

Ba thứ phải làm đúng ở đây, vì sai thì cả vòng lặp §B1 hỏng theo:

1. **Dịch công cụ.** Hợp đồng công cụ của EIDE (JSON Schema) → `FunctionDeclaration`.
   Gemini dùng tập con OpenAPI, nên `additionalProperties`, `$schema`… phải bị bỏ.

2. **Dịch thông điệp.** Gemini không có vai trò "tool". Kết quả công cụ đi về dưới
   dạng `Part.from_function_response` mang vai trò "user". Lời gọi công cụ của mô hình
   là `Part.from_function_call` mang vai trò "model". Lịch sử phải giữ đủ cặp
   gọi ↔ trả, nếu không mô hình sẽ gọi lại đúng cái nó vừa gọi.

3. **Tắt tự động gọi hàm.** `automatic_function_calling.disable = True`. SDK có sẵn
   vòng lặp gọi hàm tự động — nhưng vòng lặp đó KHÔNG đi qua hook và lớp cấp quyền của
   ta, nên nó sẽ vượt mặt toàn bộ N1/N5/N8/N9. Phải tắt.

Tất định (§F3): temperature 0 + seed cố định. Gemini không hứa tất định tuyệt đối, nên
bộ đo vẫn chạy mỗi ca 5 lần và chấm theo lần chạy đầy đủ.
"""

from __future__ import annotations

import base64
import random
import time
from typing import Any, Callable

from ..config import ModelConfig
from ..errors import EideError, llm_unavailable, network_down
from .gateway import Response, ToolCall, Usage, declarations_for

# Mã lỗi đáng thử lại: quá tải, hết hạn ngạch tạm thời, lỗi máy chủ.
_RETRY_STATUS = {408, 429, 500, 502, 503, 504}
_SEED = 7          # cố định để hai lần chạy cùng đầu vào có cơ hội giống nhau


class GeminiGateway:
    name = "gemini"

    def __init__(self, cfg: ModelConfig | None = None, *, api_key: str | None = None):
        from google import genai   # nạp trễ: lõi chạy headless không cần SDK nếu offline

        self.cfg = cfg or ModelConfig()
        key = api_key or self.cfg.api_key
        if not key:
            raise EideError(
                "E6003",
                f"Chưa có khoá Gemini. Đặt {self.cfg.api_key_env} trong tệp .env ở gốc dự án.",
                hint_for_agent="",
                alternatives=["Tạo khoá ở https://aistudio.google.com/apikey"],
                blame="user")
        self._genai = genai
        self.client = genai.Client(api_key=key)

    # ------------------------------------------------------------------ gọi
    def stream(self, *, system: str, messages: list[dict[str, Any]],
               tools: list[dict[str, Any]],
               on_text: Callable[[str], None] | None = None,
               model: str | None = None,
               temperature: float | None = None) -> Response:
        from google.genai import types

        # Rang buoc mo hinh duoc canh o DAY, tai diem goi cuoi cung — khong o cho nao khac.
        # Mot subagent hay mot lop tom tat truyen thang `model=` vao van bi chan.
        mdl = ModelConfig.assert_allowed(model or self.cfg.main)
        contents = self._to_contents(messages)
        cfg = types.GenerateContentConfig(
            system_instruction=system,
            temperature=self.cfg.temperature if temperature is None else temperature,
            max_output_tokens=self.cfg.max_output_tokens,
            seed=_SEED,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        decls = declarations_for(tools)
        if decls:
            cfg.tools = [types.Tool(function_declarations=decls)]

        t0 = time.perf_counter()
        last: Exception | None = None
        for attempt in range(1, self.cfg.max_retries + 1):
            try:
                return self._one_call(mdl, contents, cfg, on_text, t0)
            except Exception as e:                       # noqa: BLE001 — phân loại ngay dưới
                status = _status_of(e)
                if status is not None and status not in _RETRY_STATUS:
                    raise self._as_eide_error(e, status)
                last = e
                if attempt < self.cfg.max_retries:
                    # Lùi mũ + nhiễu: nhiều lượt cùng hỏng thì không dội lại cùng lúc.
                    time.sleep(min(8.0, 0.8 * 2 ** (attempt - 1)) * (0.5 + random.random()))
        raise self._as_eide_error(last, _status_of(last), attempts=self.cfg.max_retries)

    def _one_call(self, mdl: str, contents: list[Any], cfg: Any,
                  on_text: Callable[[str], None] | None, t0: float) -> Response:
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        raw: list[dict[str, Any]] = []
        usage = Usage()
        finish = ""

        for chunk in self.client.models.generate_content_stream(
                model=mdl, contents=contents, config=cfg):
            um = getattr(chunk, "usage_metadata", None)
            if um:
                usage = Usage(
                    input_tokens=um.prompt_token_count or 0,
                    output_tokens=um.candidates_token_count or 0,
                    cached_tokens=getattr(um, "cached_content_token_count", 0) or 0,
                    thoughts_tokens=getattr(um, "thoughts_token_count", 0) or 0,
                )
            for cand in (chunk.candidates or []):
                if cand.finish_reason:
                    finish = str(cand.finish_reason)
                for part in ((cand.content.parts if cand.content else None) or []):
                    sig = getattr(part, "thought_signature", None)
                    la_suy_nghi = bool(getattr(part, "thought", False))
                    fc = getattr(part, "function_call", None)

                    if fc and fc.name:
                        calls.append(ToolCall(id=fc.id or f"call-{len(calls) + 1}",
                                              tool=fc.name, args=dict(fc.args or {})))
                        raw.append({"type": "call", "name": fc.name, "args": dict(fc.args or {}),
                                    "id": fc.id, "sig": _b64(sig)})
                    elif part.text is not None:
                        if not la_suy_nghi:
                            # Phần "suy nghĩ" không phải lời nói với người — không stream ra.
                            text_parts.append(part.text)
                            if on_text:
                                on_text(part.text)          # §B1: stream thẳng ra Console
                        raw.append({"type": "text", "text": part.text,
                                    "thought": la_suy_nghi, "sig": _b64(sig)})
                    elif sig:
                        # Phần rỗng chỉ mang chữ ký: vẫn phải giữ để gửi lại nguyên trạng.
                        raw.append({"type": "text", "text": None,
                                    "thought": la_suy_nghi, "sig": _b64(sig)})

        return Response(text="".join(text_parts), tool_calls=calls, usage=usage,
                        finish_reason=finish, model=mdl, parts=raw,
                        elapsed_ms=(time.perf_counter() - t0) * 1000)

    # ------------------------------------------------------------------ dịch
    @staticmethod
    def _gom_ket_qua(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Dời mọi message không phải `tool` ra SAU nhóm kết quả liền sau một lượt mô hình.

        Hàm thuần, chỉ đụng DANH SÁCH gửi đi — transcript trên đĩa không đổi. Lõi đã được
        sửa để không chen lời nhắc vào giữa (M1-01), nhưng một phiên CŨ mở lại vẫn mang
        lịch sử chen giữa, và một request hỏng vì lịch sử cũ thì người dùng không mở lại
        được phiên ấy nữa. Vì vậy chỗ dựng request phải chịu được cả hai dạng.
        """
        ra: list[dict[str, Any]] = []
        i, n = 0, len(messages)
        while i < n:
            m = messages[i]
            ra.append(m)
            if m.get("role") != "model" or not m.get("tool_calls"):
                i += 1
                continue
            ids = {str(c.get("id")) for c in m["tool_calls"]}
            j, tra, chen = i + 1, [], []
            while j < n and messages[j].get("role") != "model":
                if (messages[j].get("role") == "tool"
                        and str(messages[j].get("tool_call_id")) in ids):
                    tra.append(messages[j])
                else:
                    chen.append(messages[j])
                j += 1
            ra.extend(tra)
            ra.extend(chen)
            i = j
        return ra

    def _to_contents(self, messages: list[dict[str, Any]]) -> list[Any]:
        from google.genai import types

        out: list[Any] = []
        cho_phep_id: set[str] = set()      # id đã đi kèm function_call ở lượt mô hình
        nhom: list[Any] = []               # các function_response liền nhau đang gom

        def xa_nhom() -> None:
            if nhom:
                out.append(types.Content(role="user", parts=list(nhom)))
                nhom.clear()

        for m in self._gom_ket_qua(messages):
            role = m.get("role")
            if role == "tool":
                res = m.get("result")
                if not isinstance(res, dict):
                    res = {"result": res}
                # Id chỉ gửi kèm khi lượt mô hình tương ứng cũng đã gửi id ở function_call.
                # Gửi một `function_response.id` không khớp lời gọi nào là tự dựng ra một
                # cặp không tồn tại — tệ hơn là không gửi id.
                cid = str(m.get("tool_call_id") or "")
                fr = types.FunctionResponse(name=m.get("tool", "tool"), response=res)
                if cid in cho_phep_id:
                    fr.id = cid
                nhom.append(types.Part(function_response=fr))
                continue

            xa_nhom()
            if role == "user":
                out.append(types.Content(role="user",
                                         parts=[types.Part.from_text(text=m.get("text", ""))]))
            elif role == "model":
                parts = self._model_parts(m)
                cho_phep_id = {str(p["id"]) for p in (m.get("parts") or [])
                               if p.get("type") == "call" and p.get("id")}
                if parts:
                    out.append(types.Content(role="model", parts=parts))
            else:
                raise ValueError(f"Vai trò thông điệp lạ: {role!r}")
        xa_nhom()
        return out

    @staticmethod
    def _model_parts(m: dict[str, Any]) -> list[Any]:
        """Dựng lại lượt của mô hình.

        Gemini 3.x ĐÒI `thought_signature` đi kèm mỗi `function_call` khi ta gửi lại
        lịch sử. Thiếu nó thì lượt thứ hai — lượt ngay sau khi có kết quả công cụ —
        hỏng 400 INVALID_ARGUMENT, và tác tử không bao giờ đi quá một lời gọi công cụ.
        Đây chính là lỗi đã làm TC003 trượt 0/5 và TC001/TC004/TC005 chập chờn ở lần
        đo đầu (xem DEV-225).

        Vì vậy ở đây ta phát lại ĐÚNG các part đã nhận, kể cả part rỗng chỉ mang chữ ký,
        thay vì dựng lại từ text + tool_calls.
        """
        from google.genai import types

        parts: list[Any] = []
        for p in m.get("parts") or []:
            sig = _unb64(p.get("sig"))
            if p["type"] == "call":
                fc = types.FunctionCall(name=p["name"], args=p.get("args") or {})
                if p.get("id"):
                    fc.id = p["id"]
                parts.append(types.Part(function_call=fc, thought_signature=sig))
            else:
                parts.append(types.Part(text=p.get("text"),
                                        thought=p.get("thought") or None,
                                        thought_signature=sig))
        if parts:
            return parts

        # Không có bản ghi part (cổng kịch bản, hoặc phiên cũ): dựng lại từ dạng trung gian.
        if m.get("text"):
            parts.append(types.Part.from_text(text=m["text"]))
        for c in m.get("tool_calls", []):
            parts.append(types.Part.from_function_call(name=c["tool"], args=c.get("args") or {}))
        return parts

    # ------------------------------------------------------------------ lỗi
    @staticmethod
    def _as_eide_error(e: Exception | None, status: int | None,
                       attempts: int = 1) -> EideError:
        msg = str(e) if e else "không rõ"
        low = msg.lower()
        if status in (401, 403) or "api key" in low or "permission" in low:
            return EideError("E6003",
                             "Khoá Gemini không hợp lệ hoặc không đủ quyền.",
                             hint_for_agent="",
                             alternatives=["Kiểm lại GEMINI_API_KEY trong .env"],
                             blame="user")
        if status is None and any(k in low for k in
                                  ("connection", "timeout", "temporarily", "dns",
                                   "network", "unreachable", "ssl")):
            # UC19/TC072: lỗi MẠNG phải được gọi đúng tên, không đội lốt lỗi khác.
            return network_down("dịch vụ Gemini", msg, state_saved=True)
        return llm_unavailable(msg[:300], attempts)

    def count_tokens(self, text: str) -> int:
        try:
            r = self.client.models.count_tokens(model=self.cfg.main, contents=text)
            return int(r.total_tokens or 0)
        except Exception:
            return int(len(text) / 3.0)      # ước xấp xỉ cho tiếng Việt


def _b64(v: Any) -> str | None:
    """Chữ ký là bytes; sổ cái và bản ghi phát lại là JSON. Base64 nối hai thứ đó."""
    if v is None:
        return None
    return base64.b64encode(v).decode("ascii") if isinstance(v, (bytes, bytearray)) else str(v)


def _unb64(v: Any) -> bytes | None:
    if not v:
        return None
    return base64.b64decode(v) if isinstance(v, str) else v


def _status_of(e: Exception | None) -> int | None:
    for attr in ("code", "status_code", "status"):
        v = getattr(e, attr, None)
        if isinstance(v, int):
            return v
    s = str(e or "")
    for code in _RETRY_STATUS | {400, 401, 403, 404}:
        if f"{code} " in s or f"'code': {code}" in s or f'"code": {code}' in s:
            return code
    return None
