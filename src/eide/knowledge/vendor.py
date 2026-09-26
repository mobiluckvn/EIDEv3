# -*- coding: utf-8 -*-
"""Cấu hình vendor và EDA → Fact tầng CẤU HÌNH. EIDE-ING-43 §4.4, §4.5. Bước ING-D.

## Tầng CẤU HÌNH là gì, và vì sao nó phải là một tầng riêng

`.ioc`, `sdkconfig`, `.dts`, `.ld`, `map` nói **dự án đang đặt gì**, không nói **chip
chịu được gì**. Hai câu đó khác nhau về bản chất:

    datasheet:  "FLASH của chip này là 32 KB"      ← giới hạn vật lý
    linker:     "tôi khai FLASH là 64 KB"          ← một lựa chọn, có thể SAI

Nếu nhét cả hai vào cùng một tầng, phép so sánh sẽ lấy con số 64 KB làm sự thật và mọi
tính toán sau đó đúng về số học mà sai về vật lý. Đó là lý do §4.5 nói CẤU HÌNH **không
bao giờ** là vế "giới hạn vật lý" — và cách hiện thực điều đó rất gọn: tầng `CAUHINH`
không nằm trong `TANG_DUNG_DUOC`, nên `fact.compare` tự động từ chối nó.

Giá trị thật của tầng này nằm ở chiều ngược lại: **đối chiếu**. `.ld` khai 64 KB mà chip
có 32 KB là một lỗi im lặng kinh điển — mã biên dịch xong, nạp vào chạy được một lúc rồi
hỏng ở chỗ không ai ngờ. Có hai con số cạnh nhau thì phát hiện được trong một giây.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

TANG_CAU_HINH = "CAUHINH"


@dataclass(slots=True)
class CauHinh:
    """Kết quả đọc một tệp cấu hình."""

    loai: str                                  # ioc | sdkconfig | devicetree | linker | map
    ten_tep: str
    hash: str
    khoa: dict[str, str] = field(default_factory=dict)      # khoá chuẩn → giá trị thô
    tho: dict[str, str] = field(default_factory=dict)       # khoá gốc trong tệp
    canh_bao: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"loai": self.loai, "ten_tep": self.ten_tep, "hash": self.hash,
                "khoa": dict(self.khoa), "so_khoa": len(self.khoa),
                "canh_bao": list(self.canh_bao)}


def _bam(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# =========================================================================== CubeMX .ioc
_IOC_CLOCK = re.compile(r"^RCC\.(\w*SYSCLK\w*|\w*Freq_Value)\s*=\s*(.+)$", re.M)
_IOC_PIN = re.compile(r"^(P[A-Z]\d+)\.Signal\s*=\s*(.+)$", re.M)
_IOC_MCU = re.compile(r"^Mcu\.(Name|UserName|Family)\s*=\s*(.+)$", re.M)


def doc_ioc(path: Path) -> CauHinh:
    chu = path.read_text("utf-8", errors="replace")
    c = CauHinh(loai="ioc", ten_tep=path.name, hash=_bam(path))
    for ten, gt in _IOC_MCU.findall(chu):
        c.khoa[f"config:mcu.{ten.lower()}"] = gt.strip()
    for chan, tin_hieu in _IOC_PIN.findall(chu):
        c.khoa[f"config:pin.{chan}.af"] = tin_hieu.strip()
    for ten, gt in _IOC_CLOCK.findall(chu):
        # CubeMX ghi tần số bằng Hz không có đơn vị — thêm đơn vị vào để không ai
        # phải đoán 72000000 là Hz hay kHz.
        so = gt.strip()
        c.khoa[f"config:clock.{ten.lower()}"] = f"{so} Hz" if so.isdigit() else so
    return c


# =========================================================================== sdkconfig
_KV = re.compile(r"^\s*(CONFIG_[A-Z0-9_]+)\s*=\s*(.+?)\s*$", re.M)
_SDK_QUAN_TAM = {
    "CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ": ("config:cpu.freq", "MHz"),
    "CONFIG_ESPTOOLPY_FLASHSIZE": ("config:flash.size", ""),
    "CONFIG_FREERTOS_HZ": ("config:rtos.tick", "Hz"),
    "CONFIG_PARTITION_TABLE_CUSTOM_FILENAME": ("config:partition.file", ""),
    "CONFIG_ESP32_DEFAULT_CPU_FREQ_MHZ": ("config:cpu.freq", "MHz"),
}


def doc_sdkconfig(path: Path) -> CauHinh:
    chu = path.read_text("utf-8", errors="replace")
    c = CauHinh(loai="sdkconfig", ten_tep=path.name, hash=_bam(path))
    for k, v in _KV.findall(chu):
        v = v.strip().strip('"')
        c.tho[k] = v
        if k in _SDK_QUAN_TAM:
            khoa, dv = _SDK_QUAN_TAM[k]
            c.khoa[khoa] = f"{v} {dv}".strip()
    return c


# =========================================================================== devicetree
_DTS_NODE = re.compile(r"(&?[\w\-]+)\s*\{([^{}]*)\}", re.S)
_DTS_PROP = re.compile(r"^\s*([\w\-]+)\s*=\s*<?\s*([^;>]+?)\s*>?\s*;", re.M)


def doc_dts(path: Path) -> CauHinh:
    """Đọc thuộc tính ở mức nông. Không dựng cây đầy đủ — `dtc` mới làm được thế.

    Nói rõ giới hạn thay vì hứa nhiều hơn khả năng: cấu trúc lồng nhau và `#include`
    của devicetree cần một bộ tiền xử lý thật. Cái ở đây bắt được `clock-frequency`,
    `status`, `reg` ở mức một tầng — đủ để đối chiếu, không đủ để sinh mã.
    """
    chu = path.read_text("utf-8", errors="replace")
    c = CauHinh(loai="devicetree", ten_tep=path.name, hash=_bam(path))
    for node, than in _DTS_NODE.findall(chu):
        ten = node.lstrip("&").split("@")[0]
        for k, v in _DTS_PROP.findall(than):
            gt = v.strip()
            if k == "clock-frequency" and gt.isdigit():
                gt = f"{gt} Hz"
            c.khoa[f"config:{ten}.{k}"] = gt
    if "#include" in chu:
        c.canh_bao.append(
            "Tệp có #include — bản đọc này KHÔNG mở các tệp được include, nên có thể "
            "thiếu thuộc tính. Cần đầy đủ thì phải chạy dtc.")
    return c


# =========================================================================== linker .ld
_LD_MEMORY = re.compile(
    r"(\w+)\s*\(\s*[rwx!ail]+\s*\)\s*:\s*ORIGIN\s*=\s*(\w+)\s*,\s*LENGTH\s*=\s*(\w+)",
    re.I)
_HAU_TO = {"K": 1024, "k": 1024, "M": 1024 ** 2, "m": 1024 ** 2}


def _so_ld(s: str) -> int | None:
    s = s.strip()
    m = re.fullmatch(r"(0[xX][0-9a-fA-F]+|\d+)\s*([KkMm]?)", s)
    if not m:
        return None
    n = int(m.group(1), 16) if m.group(1).lower().startswith("0x") else int(m.group(1))
    return n * _HAU_TO.get(m.group(2), 1)


def doc_ld(path: Path) -> CauHinh:
    chu = path.read_text("utf-8", errors="replace")
    c = CauHinh(loai="linker", ten_tep=path.name, hash=_bam(path))
    for ten, goc, dai in _LD_MEMORY.findall(chu):
        n = _so_ld(dai)
        t = ten.lower()
        if n is not None:
            c.khoa[f"config:{t}.size"] = f"{n} B"
        g = _so_ld(goc)
        if g is not None:
            c.khoa[f"config:{t}.origin"] = f"0x{g:08X}"
    if not c.khoa:
        c.canh_bao.append("Không thấy khối MEMORY{} nào — tệp có thể dùng macro hoặc "
                          "include.")
    return c


# =========================================================================== map file
_MAP_MUC = re.compile(r"^\s*\.(text|data|bss|rodata)\s+0x[0-9a-fA-F]+\s+(0x[0-9a-fA-F]+)",
                      re.M)


def doc_map(path: Path) -> CauHinh:
    chu = path.read_text("utf-8", errors="replace")
    c = CauHinh(loai="map", ten_tep=path.name, hash=_bam(path))
    tong: dict[str, int] = {}
    for muc, co in _MAP_MUC.findall(chu):
        tong[muc] = tong.get(muc, 0) + int(co, 16)
    for muc, n in tong.items():
        c.khoa[f"config:section.{muc}"] = f"{n} B"
    if tong:
        flash = tong.get("text", 0) + tong.get("rodata", 0) + tong.get("data", 0)
        ram = tong.get("bss", 0) + tong.get("data", 0)
        c.khoa["config:flash.used"] = f"{flash} B"
        c.khoa["config:ram.used"] = f"{ram} B"
    return c


_BO_DOC = {"ioc": doc_ioc, "sdkconfig": doc_sdkconfig, "devicetree": doc_dts,
           "linker": doc_ld, "map": doc_map}


def loai_tu_ten(path: Path) -> str:
    duoi = path.suffix.lower()
    if duoi == ".ioc":
        return "ioc"
    if duoi in (".dts", ".dtsi", ".overlay"):
        return "devicetree"
    if duoi == ".ld":
        return "linker"
    if duoi == ".map":
        return "map"
    if path.name.startswith("sdkconfig"):
        return "sdkconfig"
    return ""


def doc_cau_hinh(path: Path) -> tuple[CauHinh | None, str]:
    loai = loai_tu_ten(path)
    if not loai:
        return None, f"{path.name}: chưa có bộ đọc cấu hình cho loại tệp này."
    try:
        return _BO_DOC[loai](path), ""
    except Exception as e:                                   # noqa: BLE001
        return None, f"{path.name}: đọc không được ({e})."


# =========================================================================== → Fact
def fact_cau_hinh(c: CauHinh, khoa: str, gia_tri_tho: str) -> dict[str, Any]:
    """Một dòng cấu hình → một Fact tầng CẤU HÌNH.

    Tầng này **không** nằm trong `TANG_DUNG_DUOC`, nên `fact.compare` tự động từ chối
    dùng nó làm vế giới hạn vật lý. Đó là cách §4.5 được giữ bằng cấu trúc thay vì bằng
    lời dặn: không ai phải nhớ quy tắc, vì phép so sánh không cho lách.
    """
    from .chuan_hoa import chuan_hoa

    g = chuan_hoa(gia_tri_tho)
    fid = "fc-" + hashlib.sha1(f"{khoa}|{c.hash[:8]}".encode()).hexdigest()[:10]
    return {
        "fact_id": fid, "subject": khoa.split(".")[0], "key": khoa,
        "value": g.gia_tri, "unit": g.don_vi,
        "vmin": g.vmin, "vmax": g.vmax, "condition": "",
        "tier": TANG_CAU_HINH, "origin": "config",
        "source": {"file": c.ten_tep, "loai": c.loai, "hash": c.hash[:16],
                   "quote": f"{khoa} = {gia_tri_tho}"},
        "explain": {
            "summary": f"{khoa} = {g.hien_vi() if g.co_so else gia_tri_tho}",
            "why": (f"Đọc từ {c.ten_tep} ({c.loai}). Đây là thứ DỰ ÁN ĐANG ĐẶT, "
                    "không phải giới hạn của chip."),
            "sources": [{"kind": "tool", "ref": f"{c.ten_tep}:{khoa}",
                         "tier": TANG_CAU_HINH}],
            "diff_prev": "bản đầu tiên",
            "next": "Đối chiếu với Fact cùng khoá từ datasheet để phát hiện lệch.",
            "confidence": TANG_CAU_HINH,
        },
    }


# =========================================================================== đối chiếu
# Cặp khoá cấu hình ↔ khoá datasheet. Đây là những chỗ lệch gây lỗi im lặng.
CAP_DOI_CHIEU = [
    ("config:flash.size", "flash.size", "dung lượng FLASH"),
    ("config:ram.size", "ram.size", "dung lượng RAM"),
    ("config:sram.size", "ram.size", "dung lượng RAM"),
    ("config:clock.rcc.sysclkfreq_value", "fmax", "tần số hệ thống"),
    ("config:cpu.freq", "fmax", "tần số CPU"),
    ("config:flash.used", "flash.size", "FLASH đã dùng so với FLASH có"),
    ("config:ram.used", "ram.size", "RAM đã dùng so với RAM có"),
]


def doi_chieu_cau_hinh(facts_cau_hinh: list[dict[str, Any]],
                       facts_tai_lieu: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """So cấu hình với datasheet. `.ld` khai 64 KB mà chip có 32 KB là lỗi im lặng.

    Hai loại kết luận, và chúng khác nhau về mức độ nghiêm trọng:

    - **vượt**: cấu hình đòi nhiều hơn chip có → mạch sẽ hỏng, chỉ là chưa biết khi nào.
    - **dùng hết gần mức**: còn chạy, nhưng hết chỗ để thêm việc — một cảnh báo.
    """
    from .docs import ve_si

    def si(f: dict[str, Any]) -> tuple[float, str] | None:
        v = f.get("value")
        if v is None:
            return None
        try:
            return ve_si(float(v), f.get("unit", ""))
        except (TypeError, ValueError):
            return None

    theo_khoa_ds: dict[str, dict[str, Any]] = {}
    for f in facts_tai_lieu:
        theo_khoa_ds.setdefault(f.get("key", ""), f)

    ra: list[dict[str, Any]] = []
    for f in facts_cau_hinh:
        for khoa_ch, khoa_ds, ten_vi in CAP_DOI_CHIEU:
            if f.get("key") != khoa_ch:
                continue
            ds = theo_khoa_ds.get(khoa_ds)
            if ds is None:
                continue
            a, b = si(f), si(ds)
            if a is None or b is None or a[1] != b[1]:
                continue
            ty_le = a[0] / b[0] if b[0] else 0.0
            if ty_le > 1.0:
                ra.append({
                    "muc": "vuot", "ten_vi": ten_vi,
                    "cau_hinh": {"khoa": khoa_ch, "gia_tri": a[0], "don_vi": a[1],
                                 "nguon": f.get("source")},
                    "tai_lieu": {"khoa": khoa_ds, "gia_tri": b[0], "don_vi": b[1],
                                 "nguon": ds.get("source"), "tang": ds.get("tier")},
                    "message_vi": (
                        f"{ten_vi}: cấu hình đặt {a[0]:g} {a[1]} nhưng tài liệu nói chip "
                        f"chỉ có {b[0]:g} {b[1]}. Đây là lỗi sẽ không lộ ra lúc biên "
                        "dịch — nó lộ ra khi chạy, ở chỗ không ai ngờ."),
                })
            elif ty_le >= 0.9 and khoa_ch.endswith(".used"):
                ra.append({
                    "muc": "gan_het", "ten_vi": ten_vi,
                    "cau_hinh": {"khoa": khoa_ch, "gia_tri": a[0], "don_vi": a[1]},
                    "tai_lieu": {"khoa": khoa_ds, "gia_tri": b[0], "don_vi": b[1]},
                    "message_vi": (f"{ten_vi}: đã dùng {ty_le:.0%}. Còn chạy, nhưng gần "
                                   "hết chỗ để thêm việc."),
                })
    return ra
