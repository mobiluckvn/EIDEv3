# -*- coding: utf-8 -*-
"""Tìm tài liệu nhà sản xuất — SearXNG nếu có, GitHub của hãng nếu không.

MDD-40 §B1 chỉ định SearXNG cho `doc.search_web`. Đo trên máy anh Công ngày 27/09/2026, cách
đó không dùng được và lý do không nằm ở code:

- `www.st.com` bị **chặn ở tầng mạng** (kết nối bị reset ~0,6 s kể cả khi ép đúng IP Akamai),
  trong khi `ti.com`, `github.com`, `example.com` vào bình thường.
- Mọi instance SearXNG công khai thử được đều chặn bằng anti-bot; tự dựng thì cần Docker, máy
  này chưa có.
- DuckDuckGo, Mojeek, Bing đều trả trang xác minh trình duyệt hoặc chỉ dựng kết quả bằng JS.

Còn lại một nguồn vào được **và** do chính hãng viết: tổ chức GitHub của nhà sản xuất. Với
STM32 đó là `STMicroelectronics/STM32Cube*` — trong đó có header BSP của đúng bo (định nghĩa
chân LED, nút, cổng nối tiếp), linker script, và mã khởi động. Đây là hiện vật hãng phát hành,
không phải bài viết trên diễn đàn.

Điểm phải giữ: kết quả luôn nói **nguồn nào trả lời** (`nguon_tim`). Một danh sách ứng viên
không khai nguồn sẽ được người dùng đọc như thể nó từ datasheet, và tầng tin cậy của mọi Fact
về sau treo trên chỗ đó (N1).
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# Tên miền của hãng — dùng để xếp ứng viên SearXNG, không để quyết định tầng tin cậy.
TEN_MIEN_HANG = (
    "st.com", "microchip.com", "ti.com", "nxp.com", "infineon.com", "renesas.com",
    "espressif.com", "nordicsemi.com", "raspberrypi.com", "analog.com", "onsemi.com",
    "rohm.com", "toshiba.com", "silabs.com", "cypress.com", "atmel.com",
)

# Dấu hiệu trong truy vấn → tổ chức GitHub của hãng. Chỉ những tổ chức do hãng tự quản.
# Cố ý KHÔNG có mục "mọi thứ khác → tìm cả GitHub": một repo của người lạ trùng tên chip sẽ
# được trả về trông y như tài liệu hãng, và đó là cách hỏng tệ nhất — sai mà trông đúng.
TO_CHUC_HANG: tuple[tuple[tuple[str, ...], str], ...] = (
    (("stm32", "stm8", "stmicro", "nucleo", "discovery kit", "cubemx", "cubeide"),
     "STMicroelectronics"),
    (("esp32", "esp8266", "esp-idf", "espressif"), "espressif"),
    (("nrf51", "nrf52", "nrf53", "nrf91", "nordic"), "NordicSemiconductor"),
    (("pic32", "atmega", "attiny", "samd", "microchip", "atsam"), "MicrochipTech"),
    (("rp2040", "rp2350", "raspberry pi pico", "picosdk"), "raspberrypi"),
    (("imxrt", "lpc", "kinetis", "mcuxpresso", "nxp"), "nxp-mcuxpresso"),
    (("renesas", "ra4", "ra6"), "renesas"),
)

# Đuôi tệp được coi là TÀI LIỆU tra cứu được. `.h` có mặt vì header BSP/CMSIS của hãng là nơi
# duy nhất ghi bản đồ chân của một bo cụ thể ở dạng máy đọc được.
DUOI_TAI_LIEU = (".pdf", ".h", ".ld", ".md", ".txt", ".ioc", ".csv", ".svd", ".chm", ".html")

# Thư mục càng gần định nghĩa bo thì càng đáng đọc trước.
_THUONG_DUONG_DAN = (("/bsp/", 6), ("/drivers/bsp/", 8), ("/cmsis/device/", 5),
                     ("/include/", 2), ("/doc", 3), ("/projects/", 1))

TRAN_CAY_BYTE = 40 * 1024 * 1024
HAN_CAY_GIAY = 7 * 24 * 3600          # cây tệp của một repo giữ được một tuần


@dataclass(slots=True)
class UngVien:
    url: str
    tieu_de: str
    nha_san_xuat: bool = False
    trich: str = ""
    diem: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"url": self.url, "tieu_de": self.tieu_de,
                "nha_san_xuat": self.nha_san_xuat, "trich": self.trich,
                "diem": round(self.diem, 2)}


@dataclass(slots=True)
class KetQuaTim:
    dat: bool = False
    het_han_muc: bool = False           # thất bại vì HẠN MỨC, không phải vì mất mạng
    nguon_tim: str = ""                 # searxng | github | (rỗng nếu không tìm được)
    truy_van: str = ""
    ung_vien: list[UngVien] = field(default_factory=list)
    vi_sao_khong_dat: str = ""
    ghi_chu: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"dat": self.dat, "het_han_muc": self.het_han_muc,
                "nguon_tim": self.nguon_tim, "truy_van": self.truy_van,
                "so_ket_qua": len(self.ung_vien),
                "ung_vien": [u.to_dict() for u in self.ung_vien],
                "vi_sao_khong_dat": self.vi_sao_khong_dat, "ghi_chu": list(self.ghi_chu)}


# ============================================================================ tiện dụng
_BO_QUA = {"the", "for", "and", "pdf", "datasheet", "manual", "user", "reference",
           "cua", "của", "tai", "tài", "lieu", "liệu", "cho", "board", "kit", "mcu"}


def _tu_khoa(truy_van: str) -> list[str]:
    """Từ khoá có nghĩa trong truy vấn, chữ thường, bỏ từ quá chung.

    Giữ lại cả token có số (`stm32f469`, `f469`, `um2032`) — đó mới là phần định danh, còn
    "datasheet" thì mọi tài liệu đều có.
    """
    tho = [t for t in re.split(r"[^A-Za-z0-9À-ỹ]+", truy_van.lower()) if len(t) >= 3]
    return [t for t in tho if t not in _BO_QUA] or tho


def to_chuc_cho(truy_van: str) -> str:
    """Tổ chức GitHub của hãng suy ra từ truy vấn, rỗng nếu không chắc."""
    t = truy_van.lower()
    for dau_hieu, org in TO_CHUC_HANG:
        if any(d in t for d in dau_hieu):
            return org
    return ""


class HetHanMuc(Exception):
    """GitHub từ chối vì HẾT HẠN MỨC, không phải vì mất mạng.

    Hai thứ này phải khác nhau ở chỗ tác tử đọc: mất mạng thì thử lại ngay được, còn hết hạn
    mức thì thử lại ngay là chắc chắn thất bại lần nữa — và một tác tử được bảo "lỗi mạng" sẽ
    thử lại đúng như thế cho tới khi hết lượt gọi công cụ.
    """

    def __init__(self, con_lai_giay: int, co_token: bool):
        self.con_lai_giay = con_lai_giay
        self.co_token = co_token
        super().__init__(f"hết hạn mức GitHub, còn {con_lai_giay} s")


def _json_url(url: str, *, timeout: float, tran: int = 8 * 1024 * 1024) -> Any:
    import os
    import time as _t
    import urllib.error
    import urllib.request

    dau = {"Accept": "application/vnd.github+json", "User-Agent": "EIDE/3.0"}
    # Không xác thực: 60 lượt/giờ cho cả máy. Một phiên làm việc thật dùng hết trong mươi phút,
    # nên có token thì dùng — nhưng KHÔNG bắt buộc, và không bao giờ ghi token vào kết quả.
    token = os.environ.get("EIDE_GITHUB_TOKEN", "").strip()
    if token:
        dau["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=dau)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310
            b = r.read(tran + 1)
    except urllib.error.HTTPError as e:
        con = e.headers.get("X-RateLimit-Remaining") if e.headers else None
        if e.code in (403, 429) and con is not None and con.strip() == "0":
            reset = int((e.headers.get("X-RateLimit-Reset") or "0") or 0)
            raise HetHanMuc(max(0, reset - int(_t.time())), bool(token)) from e
        raise
    if len(b) > tran:
        raise ValueError(f"phản hồi vượt {tran / 1e6:.0f} MB")
    return json.loads(b.decode("utf-8"))


# ============================================================================ SearXNG
def tim_searxng(url_may_chu: str, truy_van: str, so_luong: int = 8, *,
                timeout: float = 20.0) -> KetQuaTim:
    kq = KetQuaTim(truy_van=truy_van)
    import urllib.parse

    q = urllib.parse.urlencode({"q": truy_van, "format": "json"})
    try:
        data = _json_url(f"{url_may_chu.rstrip('/')}/search?{q}", timeout=timeout)
    except Exception as e:                                    # noqa: BLE001
        kq.vi_sao_khong_dat = f"SearXNG không trả JSON dùng được: {type(e).__name__}: {e}"
        return kq
    if not isinstance(data, dict) or "results" not in data:
        # Instance công khai thường trả trang HTML xác minh trình duyệt cho `format=json`.
        kq.vi_sao_khong_dat = ("Máy chủ SearXNG trả về thứ không phải kết quả tìm kiếm "
                               "(thường là trang xác minh trình duyệt).")
        return kq
    for k in data.get("results", [])[: so_luong * 3]:
        u = str(k.get("url", ""))
        kq.ung_vien.append(UngVien(
            url=u, tieu_de=str(k.get("title", "")),
            nha_san_xuat=any(t in u for t in TEN_MIEN_HANG),
            trich=str(k.get("content") or "")[:150],
            diem=1.0 if any(t in u for t in TEN_MIEN_HANG) else 0.0))
    kq.ung_vien.sort(key=lambda x: -x.diem)
    kq.ung_vien = kq.ung_vien[:so_luong]
    kq.nguon_tim = "searxng"
    kq.dat = bool(kq.ung_vien)
    if not kq.dat:
        kq.vi_sao_khong_dat = "SearXNG trả về 0 kết quả."
    return kq


# ============================================================================ GitHub hãng
def _cay_repo(org: str, repo: str, nhanh: str, cache: Path | None, *,
              timeout: float) -> list[str]:
    """Danh sách đường dẫn tệp trong repo. Có nhớ đệm vì một cây là hơn 10 MB.

    Không nhớ đệm thì mỗi lần tìm kiếm tải lại 13 MB và mất ~33 s — đủ chậm để tác tử bỏ dở
    và đủ tốn để bị giới hạn tần suất của GitHub cắt ngang.
    """
    tep_cache = (cache / f"{org}-{repo}-{nhanh}.json") if cache else None
    if tep_cache and tep_cache.exists() and (time.time() - tep_cache.stat().st_mtime
                                             < HAN_CAY_GIAY):
        try:
            return list(json.loads(tep_cache.read_text("utf-8")))
        except ValueError:
            pass                       # nhớ đệm hỏng thì tải lại, không làm sập việc tìm
    d = _json_url(
        f"https://api.github.com/repos/{org}/{repo}/git/trees/{nhanh}?recursive=1",
        timeout=timeout, tran=TRAN_CAY_BYTE)
    duong = [str(t["path"]) for t in d.get("tree", []) if t.get("type") == "blob"]
    if d.get("truncated"):
        # GitHub cắt cây lớn. Nói ra ở tầng trên, đừng để "không tìm thấy" trông như
        # "không tồn tại".
        duong.append("__CAT_BOT__")
    if tep_cache:
        tep_cache.parent.mkdir(parents=True, exist_ok=True)
        tep_cache.write_text(json.dumps(duong, ensure_ascii=False), "utf-8")
    return duong


def _bien_the(t: str) -> set[str]:
    """Từ khoá và các dạng HỌ của nó.

    Repo của hãng đặt tên theo họ chip, không theo mã đầy đủ: tài liệu của `stm32f469` nằm
    trong `STM32CubeF4`. Tìm thẳng “stm32f469” trong tên repo thì không khớp gì cả — và
    “không khớp” ở đây bị đọc thành “hãng không phát hành tài liệu”, sai hoàn toàn.
    """
    ra: dict[str, float] = {t: 100.0}
    m = re.match(r"^([a-z]{2,}\d{0,2})([a-z])(\d)(\d*)([a-z0-9]*)$", t)  # stm32·f·4·69·i
    if m:
        ho, chu, s1, con, duoi = m.groups()
        if con:
            # ST đặt tên repo/bo theo MÃ ĐẶT HÀNG, bỏ tiền tố "stm" và đôi khi bỏ cả chữ họ:
            # chip `STM32F469I` → repo `32f469idiscovery-bsp`, thư mục
            # `Drivers/BSP/STM32469I-Discovery/`. Không có những biến thể này thì đúng thứ cần
            # tìm không khớp từ khoá nào, còn bo KHÁC tên gần giống (`stm32f4discovery-bsp`,
            # tức F407) lại khớp qua phần họ chung — sai mà trông đúng.
            ra[(ho[3:] if ho.startswith("stm") else ho) + chu + s1 + con + duoi] = 90.0
            ra[chu + s1 + con + duoi] = 85.0                 # f469i
            ra[ho + s1 + con] = 80.0                         # stm32469
            ra[s1 + con] = 70.0                              # 469
        ra[ho + chu + s1] = 40.0                             # stm32f4  — chỉ là HỌ
        ra[chu + s1] = 20.0                                  # f4
        ra[ho] = 10.0                                        # stm32
    return {k: v for k, v in ra.items() if k}


# Tên repo không suy ra được từ mã chip thì khai thẳng ở đây.
BI_DANH_REPO: dict[str, tuple[str, ...]] = {
    "esp32": ("espidf",), "esp8266": ("espidf",), "espidf": ("espidf",),
    "rp2040": ("picosdk",), "rp2350": ("picosdk",),
}


def _diem_mot_tu(t: str, trong: str) -> float:
    """Điểm của MỘT từ khoá trên một chuỗi — lấy biến thể ĐẶC HIỆU NHẤT khớp được.

    Lấy max chứ không cộng dồn: cộng dồn thì một tên chứa cả `stm32`, `stm32f4` và `f4` được
    ba lần điểm cho cùng một sự thật ("thuộc họ F4"), và ba lần điểm ấy đủ để đè một tên khớp
    đúng mã bo. Đo được: với truy vấn "STM32F469I-DISCO", `stm32f4discovery-bsp` (bo F407)
    thắng `32f469idiscovery-bsp` (đúng bo) vì cộng dồn phần họ.
    """
    bt = dict(_bien_the(t))
    for bd in BI_DANH_REPO.get(t, ()):
        bt.setdefault(bd, 95.0)
    return max((w for v, w in bt.items() if v in trong), default=0.0)


def _diem_repo(ten_repo: str, tu: list[str]) -> float:
    n = re.sub(r"[^a-z0-9]", "", ten_repo.lower())
    return sum(_diem_mot_tu(t, n) for t in tu)


def nhanh_mac_dinh(org: str, repo: str, *, cache: Path | None = None,
                   timeout: float = 20.0) -> str:
    """Nhánh mặc định của một repo, hỏi thẳng GitHub. Rỗng nếu không hỏi được.

    Vì sao cần: repo của ST không thống nhất — `stm32f4xx-hal-driver` dùng `master`,
    `stm32-otm8009a` dùng `main`, `32f469idiscovery-bsp` dùng `main`. Đo được trên bo
    STM32F469: tác tử sửa đúng tên repo rồi vẫn trượt vì đoán nhánh là `main`. Bắt nó đoán
    nhánh là lặp lại đúng lỗi "đoán thay vì nhìn", chỉ ở một tầng thấp hơn.
    """
    tep = (cache / f"nhanh-{org}-{repo}.txt") if cache else None
    if tep and tep.exists() and time.time() - tep.stat().st_mtime < HAN_CAY_GIAY:
        cu = tep.read_text("utf-8").strip()
        if cu:
            return cu
    try:
        d = _json_url(f"https://api.github.com/repos/{org}/{repo}", timeout=timeout)
    except Exception:                                         # noqa: BLE001
        return ""
    ra = str((d or {}).get("default_branch") or "")
    if ra and tep:
        tep.parent.mkdir(parents=True, exist_ok=True)
        tep.write_text(ra, "utf-8")
    return ra


def _repo_cua_org(org: str, cache: Path | None, *, timeout: float,
                  tran_trang: int = 4) -> list[tuple[str, str]]:
    """Danh sách repo của một tổ chức, có nhớ đệm. Trả [(tên, nhánh mặc định)]."""
    tep = (cache / f"org-{org}.json") if cache else None

    def tu_cache() -> list[tuple[str, str]]:
        if not tep or not tep.exists():
            return []
        try:
            return [(str(a), str(b)) for a, b in json.loads(tep.read_text("utf-8"))]
        except (ValueError, TypeError):
            return []

    if tep and tep.exists() and time.time() - tep.stat().st_mtime < HAN_CAY_GIAY:
        cu = tu_cache()
        if cu:
            return cu
    ra: list[tuple[str, str]] = []
    try:
        for trang in range(1, tran_trang + 1):
            d = _json_url(f"https://api.github.com/orgs/{org}/repos?per_page=100&page={trang}",
                          timeout=timeout)
            if not isinstance(d, list) or not d:
                break
            ra += [(str(x.get("name") or ""), str(x.get("default_branch") or "main"))
                   for x in d if x.get("name")]
            if len(d) < 100:
                break
    except HetHanMuc:
        # Hết hạn mức mà có nhớ đệm QUÁ HẠN thì dùng nó: một danh sách repo cũ vài ngày vẫn
        # gần đúng, còn không trả gì cả thì tác tử mất hẳn đường tìm tài liệu. Bên gọi nói ra
        # rằng danh sách này cũ.
        cu = tu_cache()
        if cu:
            raise _CacheCu(cu) from None
        raise
    if tep and ra:
        tep.parent.mkdir(parents=True, exist_ok=True)
        tep.write_text(json.dumps(ra, ensure_ascii=False), "utf-8")
    return ra


class _CacheCu(Exception):
    """Mang theo danh sách repo đọc từ nhớ đệm quá hạn, để bên gọi dùng và KHAI RA là cũ."""

    def __init__(self, repos: list[tuple[str, str]]):
        self.repos = repos
        super().__init__("dùng nhớ đệm quá hạn")


def _diem_duong_dan(duong: str, tu: list[str]) -> float:
    """Điểm của một tệp trong repo. Tên tệp nặng hơn đường dẫn chứa nó.

    Dùng cùng phép chấm theo độ đặc hiệu như tên repo: tệp cần tìm ở đây là
    `Drivers/BSP/STM32469I-Discovery/stm32469i_discovery.h`, và nó chỉ khớp truy vấn
    "STM32F469I" qua biến thể bỏ chữ họ (`stm32469`) — khớp thẳng mã đầy đủ thì trượt.
    """
    ten = re.sub(r"[^a-z0-9.]", "", duong.rsplit("/", 1)[-1].lower())
    thap = re.sub(r"[^a-z0-9./]", "", duong.lower())
    diem_ten = sum(_diem_mot_tu(t, ten) for t in tu)
    if diem_ten <= 0:
        return 0.0
    diem = diem_ten + sum(_diem_mot_tu(t, thap) for t in tu) * 0.3
    for mau, cong in _THUONG_DUONG_DAN:
        if mau in duong.lower():
            diem += cong * 10
    if ten.endswith(".pdf"):
        diem += 40
    if ten.endswith(".h"):
        diem += 20
    return diem


def tim_github(truy_van: str, so_luong: int = 8, *, cache: Path | None = None,
               timeout: float = 45.0, so_repo: int = 3) -> KetQuaTim:
    """Tìm tệp tài liệu trong repo của chính hãng trên GitHub."""
    kq = KetQuaTim(truy_van=truy_van)
    org = to_chuc_cho(truy_van)
    if not org:
        kq.vi_sao_khong_dat = (
            "Không nhận ra hãng nào từ truy vấn này, nên không biết tìm trong tổ chức GitHub "
            "nào. Nêu rõ dòng chip (ví dụ “STM32F469”) hoặc nhờ người dùng chỉ đường dẫn tài "
            "liệu.")
        return kq

    tu = _tu_khoa(truy_van)
    import urllib.parse

    try:
        tat_ca = _repo_cua_org(org, cache, timeout=min(timeout, 30))
    except _CacheCu as e:
        tat_ca = e.repos
        kq.ghi_chu.append(
            f"HẾT HẠN MỨC GitHub nên danh sách repo lấy từ nhớ đệm cũ ({len(tat_ca)} repo). "
            "Có thể thiếu repo mới.")
    except HetHanMuc as e:
        kq.het_han_muc = True
        kq.vi_sao_khong_dat = (
            f"HẾT HẠN MỨC GitHub API (không xác thực chỉ được 60 lượt/giờ cho cả máy). "
            f"Hạn mức nạp lại sau {e.con_lai_giay // 60} phút {e.con_lai_giay % 60} giây. "
            + ("Đã dùng EIDE_GITHUB_TOKEN mà vẫn hết — đợi hoặc giảm số lần tìm."
               if e.co_token else
               "Đặt `EIDE_GITHUB_TOKEN` trong .env (token chỉ cần quyền công khai) thì được "
               "5000 lượt/giờ."))
        return kq
    except Exception as e:                                    # noqa: BLE001
        kq.vi_sao_khong_dat = f"Không gọi được API GitHub: {type(e).__name__}: {e}"
        return kq

    xep = sorted(((_diem_repo(t, tu), t, b) for t, b in tat_ca), key=lambda x: -x[0])
    repos = [(t, b) for d, t, b in xep[:so_repo] if d > 0]
    if not repos:
        kq.vi_sao_khong_dat = (
            f"Tổ chức {org} trên GitHub có {len(tat_ca)} repo nhưng không repo nào khớp "
            f"“{' '.join(tu[:4])}”.")
        return kq
    kq.ghi_chu.append("Đã soi repo: " + ", ".join(f"{org}/{t}" for t, _ in repos))

    for repo, nhanh in repos:
        try:
            duong = _cay_repo(org, repo, nhanh, cache, timeout=timeout)
        except HetHanMuc as e:
            kq.het_han_muc = True
            kq.ghi_chu.append(
                f"{org}/{repo}: HẾT HẠN MỨC GitHub khi đọc cây tệp, nạp lại sau "
                f"{e.con_lai_giay // 60} phút.")
            continue
        except Exception as e:                                # noqa: BLE001
            kq.ghi_chu.append(f"{org}/{repo}: không đọc được cây tệp ({type(e).__name__}).")
            continue
        if "__CAT_BOT__" in duong:
            duong.remove("__CAT_BOT__")
            kq.ghi_chu.append(
                f"{org}/{repo}: GitHub CẮT BỚT danh sách tệp — có thể còn tệp khớp mà "
                "không hiện ra ở đây.")
        for d in duong:
            if not d.lower().endswith(DUOI_TAI_LIEU):
                continue
            diem = _diem_duong_dan(d, tu)
            if diem <= 0:
                continue
            kq.ung_vien.append(UngVien(
                url=f"https://raw.githubusercontent.com/{org}/{repo}/{nhanh}/"
                    + urllib.parse.quote(d),
                tieu_de=d.rsplit("/", 1)[-1], nha_san_xuat=True,
                trich=f"{org}/{repo} · {d}", diem=diem))

    kq.ung_vien.sort(key=lambda x: (-x.diem, x.url))
    kq.ung_vien = kq.ung_vien[:so_luong]
    kq.nguon_tim = "github"
    kq.dat = bool(kq.ung_vien)
    if not kq.dat:
        kq.vi_sao_khong_dat = (
            f"Đã soi repo của {org} trên GitHub nhưng không có tệp nào tên khớp "
            f"“{' '.join(tu[:4])}”.")
    else:
        kq.ghi_chu.append(
            "Đây là tệp trong repo GitHub của chính hãng (mã nguồn, header BSP, linker "
            "script) — KHÔNG phải bản PDF datasheet. Dùng được làm nguồn nha_san_xuat, nhưng "
            "khi nhắc tới một con số thì nói rõ nó đọc từ tệp nào, dòng nào.")
    return kq


# ============================================================================ Wikimedia
# Từ khoá báo rằng người dùng đang tìm MỘT TẤM ẢNH, không phải một tài liệu.
_TU_ANH = ("logo", "ảnh", "anh", "hình", "hinh", "image", "icon", "biểu trưng", "bieu trung")

_WM_API = "https://commons.wikimedia.org/w/api.php"


def tim_wikimedia(truy_van: str, so_luong: int = 8, *, timeout: float = 25.0) -> KetQuaTim:
    """Tìm TỆP trên Wikimedia Commons — dùng cho thứ không phải tài liệu chip.

    Vì sao cần backend này: bảng `TO_CHUC_HANG` chỉ biết tìm trong GitHub của các hãng chip.
    Đo trên bo STM32F469 ngày 28/09/2026, tác tử được giao việc tìm **logo của trường PTIT**
    và nhận về `E3001` như thể mất mạng — trong khi máy vẫn vào mạng bình thường, chỉ là EIDE
    không có đường nào tìm một thứ không phải chip.

    Commons có API mở, không anti-bot, và nội dung có giấy phép rõ ràng. Nhưng nó **không
    phải nguồn của hãng**: mọi thứ lấy từ đây ở tầng `ben_thu_ba`, và giấy phép từng tệp là
    việc người dùng phải xem — nói ra cả hai điều đó trong `ghi_chu`.
    """
    kq = KetQuaTim(truy_van=truy_van)
    import urllib.parse
    import urllib.request

    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": truy_van, "gsrnamespace": "6", "gsrlimit": str(max(so_luong * 3, 12)),
        "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata"})
    try:
        req = urllib.request.Request(f"{_WM_API}?{q}", headers={
            # CHỈ ASCII: urllib mã hoá header bằng latin-1, nên một chữ tiếng Việt có dấu
            # trong User-Agent làm cả lời gọi nổ bằng UnicodeEncodeError — một lỗi trông
            # như "không gọi được API" trong khi mạng hoàn toàn bình thường.
            "User-Agent": "EIDE/3.0 (embedded IDE research project)"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            d = json.loads(r.read().decode("utf-8"))
    except Exception as e:                                    # noqa: BLE001
        kq.vi_sao_khong_dat = f"Không gọi được API Wikimedia: {type(e).__name__}: {e}"
        return kq

    trang = ((d.get("query") or {}).get("pages") or {})
    if not trang:
        kq.vi_sao_khong_dat = f"Wikimedia Commons không có tệp nào khớp “{truy_van}”."
        return kq

    muon_anh = any(t in truy_van.lower() for t in _TU_ANH)
    tu = _tu_khoa(truy_van)
    for p in trang.values():
        ii = (p.get("imageinfo") or [{}])[0]
        url = str(ii.get("url") or "")
        if not url:
            continue
        # Bỏ tham số theo dõi mà API gắn vào — tải tệp không cần chúng.
        url = url.split("?", 1)[0]
        mime = str(ii.get("mime") or "")
        tieu_de = str(p.get("title") or "").removeprefix("File:")
        diem = sum(20.0 for t in tu if t in tieu_de.lower())
        if muon_anh:
            # Truy vấn có chữ "logo"/"ảnh" mà kết quả là PDF thì gần như chắc chắn không phải
            # thứ người ta muốn — đẩy xuống cuối thay vì loại hẳn.
            diem += 100.0 if mime.startswith("image/") else -50.0
        kq.ung_vien.append(UngVien(
            url=url, tieu_de=tieu_de, nha_san_xuat=False,
            trich=f"Wikimedia Commons · {mime} · {ii.get('width')}×{ii.get('height')}",
            diem=diem))

    kq.ung_vien.sort(key=lambda x: (-x.diem, x.url))
    kq.ung_vien = kq.ung_vien[:so_luong]
    kq.nguon_tim = "wikimedia"
    kq.dat = bool(kq.ung_vien)
    if kq.dat:
        kq.ghi_chu.append(
            "Nguồn là Wikimedia Commons, KHÔNG phải nhà sản xuất — nạp với "
            "`nguon=\"ben_thu_ba\"`. Mỗi tệp trên Commons có giấy phép riêng; nếu dùng vào "
            "sản phẩm thì nói cho người dùng biết để họ xem giấy phép.")
    return kq


# ============================================================================ điều phối
def tim(truy_van: str, *, url_searxng: str = "", so_luong: int = 8,
        cache: Path | None = None,
        tim_github_fn: Callable[..., KetQuaTim] | None = None,
        tim_searxng_fn: Callable[..., KetQuaTim] | None = None,
        tim_wikimedia_fn: Callable[..., KetQuaTim] | None = None) -> KetQuaTim:
    """SearXNG → GitHub của hãng → Wikimedia. Luôn khai nguồn nào đã trả lời.

    Thứ tự theo độ gần với "tài liệu của hãng": SearXNG có thể trả về đúng trang của hãng;
    GitHub của hãng là hiện vật hãng phát hành; Wikimedia là **bên thứ ba** và chỉ đứng cuối.
    Một truy vấn không phải về chip (ví dụ "logo trường PTIT") sẽ rơi qua hai tầng đầu và
    được tầng cuối trả lời — trước đây nó nhận `E3001` như thể mất mạng.
    """
    g_sx = tim_searxng_fn or tim_searxng
    g_gh = tim_github_fn or tim_github
    g_wm = tim_wikimedia_fn or tim_wikimedia
    ly_do: list[str] = []

    if url_searxng:
        kq = g_sx(url_searxng, truy_van, so_luong)
        if kq.dat:
            return kq
        ly_do.append(f"SearXNG: {kq.vi_sao_khong_dat}")
    else:
        ly_do.append("SearXNG: chưa cấu hình EIDE_SEARXNG_URL.")

    kq = g_gh(truy_van, so_luong, cache=cache)
    if kq.dat:
        kq.ghi_chu.insert(0, ly_do[0] + " → đã chuyển sang GitHub của hãng.")
        return kq
    ly_do.append(f"GitHub: {kq.vi_sao_khong_dat}")
    het = kq.het_han_muc

    kq_wm = g_wm(truy_van, so_luong)
    if kq_wm.dat:
        kq_wm.ghi_chu.insert(0, " ".join(ly_do) + " → đã chuyển sang Wikimedia Commons.")
        return kq_wm
    ly_do.append(f"Wikimedia: {kq_wm.vi_sao_khong_dat}")

    ra = KetQuaTim(truy_van=truy_van, het_han_muc=het)
    ra.vi_sao_khong_dat = " ".join(ly_do)
    ra.ghi_chu = list(kq.ghi_chu) + list(kq_wm.ghi_chu)
    return ra
