# -*- coding: utf-8 -*-
"""M5-07 — chốt N1 cuối cùng mà MÃ đứng canh, và nó so chuỗi sau khi xoá hết dấu chấm.

`fact.from_doc` là cây cầu duy nhất để một con số trong tài liệu được phép đi vào mã nguồn:
mô hình chọn đoạn và đặt tên khoá, **mã kiểm giá trị có mặt thật trong đoạn ấy**. Kỷ luật đó
là toàn bộ giá trị của công cụ.

Phép kiểm cũ:

    def _chuan(x): return re.sub(r"[\\s.,]", "", x).lower()
    co = _chuan(gt) in _chuan(noi_dung)

Hai chỗ nó nói sai, và cả hai đều nói sai theo chiều **nhận bừa**:

* **Xoá dấu chấm** biến `2.7 V` thành `27v`, nên `gia_tri="27"` đi qua. Một điện áp 2,7 V vào
  kho thành 27 — và nó mang trích dẫn, mang tầng BẠC, trông y như một Fact đọc đúng.
* **Phép CHỨA không có ranh giới** nên `gia_tri="3"` khớp `Table 3`, `180` khớp `1800`, và
  `39` khớp `0.39`.

Đây là ô xanh giả ở đúng chỗ đắt nhất: cửa mà mọi hằng số firmware phải đi qua.
"""

from __future__ import annotations

import pytest

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}

VAN_BAN = "\n".join(
    [f"/* dòng chú thích số {i} */" for i in range(1, 31)]
    + ["VDD 2.7 V nguồn cấp tối thiểu của chip này",
       "Table 3 Electrical characteristics",
       "I2C address 0x27 (39) cho module LCD",
       "#define LED1_PIN                     GPIO_PIN_6",
       "Hệ số hiệu chuẩn 3,55 lấy từ phép đo xuất xưởng",
       "Tần số tối đa 180 MHz ở dải nhiệt độ công nghiệp",
       "Bộ đếm nạp 1800 nhịp mỗi vòng",
       "Sai số cho phép 0.39 phần trăm toàn thang",
       "Thanh ghi TCCR2A nhận 0x27 khi chạy chế độ CTC",
       "Mã lỗi 39, và mã tiếp theo là 40",
       "Dòng tiêu thụ 100 mA ở chế độ chạy",
       "Tần số 180 MHz, điện áp 3.3 V ở dải thương mại"])


@pytest.fixture
def bo(du_an):
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext

    ag = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    ctx = TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                      ids=ag.ids, registry=ag.registry, emit=lambda c: None,
                      history=ag.history, agent=ag, run_id="run-1", project_name="du-an-thu")
    (ag.config.paths.project_root / "bsp.h").write_text(VAN_BAN, "utf-8")
    ag.registry.run("doc.load", {"path": "bsp.h", "doc_id": "BSP-1",
                                 "nguon": "nha_san_xuat", "explain": EX}, ctx)
    return ag, ctx


def _don_vi(ag, ctx, tim: str) -> int:
    """Số thứ tự đơn vị trích dẫn chứa `tim` — lấy qua `doc.read` như tác tử vẫn làm."""
    r = ag.registry.run("doc.read", {"doc_id": "BSP-1", "tim": tim}, ctx)
    assert r.ok and r.data["doan"], (tim, r.data if r.ok else r.error.message_vi)
    return r.data["doan"][0]["so"]


def _ghi(ag, ctx, **kw):
    return ag.registry.run("fact.from_doc", {"doc_id": "BSP-1", **kw}, ctx)


# ===================================================== dấu chấm KHÔNG được xoá
def test_27_khong_khop_2_7(bo):
    """TC-M5-07-01 — `2.7 V` không phải `27`.

    Phép `_chuan` cũ xoá dấu chấm, nên hai chuỗi ấy bằng nhau. Một điện áp 2,7 V vào kho
    thành 27 — và nó mang trích dẫn, mang tầng BẠC, trông y như một Fact đọc đúng.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "VDD 2.7")

    # Phải NÊU `trich`, không thì ca này xanh vì một lý do khác: `"27"` dài hai ký tự nên luật
    # "số quá ngắn" chặn trước, và phép so dấu chấm không bao giờ được chạy tới. Cùng cái bẫy
    # đã gặp ở TC-M5-05-04 — một ca kiểm đúng đề mà không chạm thứ nó nói nó canh.
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="vdd_min", gia_tri="27",
             trich="VDD 2.7 V nguồn cấp tối thiểu của chip này")
    # E2006 ("giá trị không có trong đoạn"), không phải E2008: đây đúng nghĩa mã cũ, và việc
    # cần làm vẫn như trước. Kế hoạch ghi E2008 cho ca này — xem DEV-357 cho lý do không theo.
    assert not r.ok and r.error.code == "E2006", r
    assert "2.7" in r.error.hint_for_agent, r.error.hint_for_agent
    assert ag.store.query_facts(subject="chip:X") == []

    # Và không nêu `trich` thì chặn vì lý do KHÁC, với mã khác — hai việc cần làm khác nhau.
    r2 = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="vdd_min", gia_tri="27")
    assert not r2.ok and r2.error.code == "E2008", r2
    assert "quá ngắn" in r2.error.message_vi


def test_gia_tri_co_dau_phay_thap_phan_van_nhan(bo):
    """Ca âm của ca trên: `3,55` viết đúng như tài liệu thì phải nhận.

    Chặn quá tay ở đây là bắt tác tử đi `fact.assert_human` — tức gán cho người dùng một câu
    họ chưa nói.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "hiệu chuẩn")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="he_so", gia_tri="3,55",
             trich="Hệ số hiệu chuẩn 3,55 lấy từ phép đo xuất xưởng")
    assert r.ok, getattr(r.error, "message_vi", "")


# ===================================================== ranh giới token
def test_so_ngan_khong_trich_bi_tu_choi(bo):
    """TC-M5-07-02 — `3` khớp `Table 3` ở đúng ranh giới token, nên ranh giới một mình không
    đủ. Một con số một–hai chữ số gần như luôn tìm thấy ở đâu đó trong một đoạn tài liệu;
    bắt nêu CÂU chứa nó là cách duy nhất để lời khai còn nghĩa."""
    ag, ctx = bo
    so = _don_vi(ag, ctx, "Table 3")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="so_bang", gia_tri="3")
    assert not r.ok and r.error.code == "E2008", r
    assert "trich" in r.error.hint_for_agent


def test_so_ngan_CO_trich_thi_nhan(bo):
    """Và có `trich` thì nhận — `trich` là chỗ lời khai của mô hình trở nên kiểm được."""
    ag, ctx = bo
    so = _don_vi(ag, ctx, "Table 3")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="so_bang", gia_tri="3",
             trich="Table 3 Electrical characteristics")
    assert r.ok, getattr(r.error, "message_vi", "")


def test_180_khong_khop_1800(bo):
    """`in` không có ranh giới, nên `180` khớp `1800` — và một tần số 1 800 MHz đọc thành
    180 MHz là một con số *hợp lý hơn* bản thật, tức không ai thấy nó sai."""
    ag, ctx = bo
    so = _don_vi(ag, ctx, "1800 nhịp")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="nhip", gia_tri="180",
             trich="Bộ đếm nạp 1800 nhịp mỗi vòng")
    assert not r.ok and r.error.code == "E2006", r


def test_so_dai_khong_can_trich(bo):
    """`trich` không thành tham số bắt buộc: mọi lời gọi cũ của mô hình phải còn chạy.

    Một con số bốn chữ số trở lên gần như không khớp bừa, nên đòi `trich` ở đó là thêm thủ
    tục mà không thêm phép đo nào.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "1800 nhịp")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="nhip", gia_tri="1800")
    assert r.ok, getattr(r.error, "message_vi", "")


# ===================================================== hex ↔ thập phân
def test_dia_chi_hex_van_nhan(bo):
    """TC-M5-07-03 — tài liệu viết một giá trị ở hai dạng (`0x27 (39)`), và cả hai dạng đều
    là ĐỌC từ đoạn ấy. Phép siết ranh giới không được làm mất tính chất này."""
    ag, ctx = bo
    so = _don_vi(ag, ctx, "I2C address")
    cau = "I2C address 0x27 (39) cho module LCD"
    for gt in ("39", "0x27"):
        r = _ghi(ag, ctx, don_vi=so, thuc_the="mpu:LCD", khoa="dia_chi", gia_tri=gt,
                 trich=cau)
        assert r.ok, (gt, getattr(r.error, "message_vi", ""))
    import json

    f = ag.store.query_facts(subject="mpu:LCD", limit=5)
    src = json.loads(f[0]["source"]) if isinstance(f[0]["source"], str) else f[0]["source"]
    assert src["quote"] == cau, src


def test_hex_cung_phai_dung_ranh_gioi(bo):
    """Nhánh hex dùng CÙNG phép ranh giới, không đi đường riêng: `0x2` không được khớp
    `0x27`."""
    ag, ctx = bo
    so = _don_vi(ag, ctx, "I2C address")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="mpu:LCD", khoa="dia_chi", gia_tri="0x2",
             trich="I2C address 0x27 (39) cho module LCD")
    assert not r.ok and r.error.code == "E2006", r


# ===================================================== giá trị không phải số
def test_gia_tri_dung_van_ghi(bo):
    """TC-M5-07-04 — ca âm quan trọng nhất: một tên ký hiệu (`GPIO_PIN_6`) phải đi qua.

    Phép siết này nhắm vào con số; kêu nhầm ở đây là chặn đúng đường mà công cụ sinh ra để
    mở — và lúc ấy tác tử lại bị chốt hằng số N1 chặn khi ghi mã, đúng chỗ nó đã bị chặn
    trước khi có `fact.from_doc`.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "LED1_PIN")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="led1", gia_tri="GPIO_PIN_6")
    assert r.ok, getattr(r.error, "message_vi", "")


# ===================================================== `trich` phải có thật
def test_trich_khong_co_trong_doan(bo):
    """TC-M5-07-05 — `trich` bịa thì từ chối, và nói ra NỘI DUNG THẬT của đoạn.

    Không có phép kiểm này thì `trich` thành một trường tự do: mô hình gõ một câu nghe hợp
    lý, con số nằm trong câu ấy, và cả hai cùng do nó viết ra.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "VDD 2.7")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="vdd_min", gia_tri="2.7",
             trich="VDD 2.7 V theo bảng 12 trang 44")
    assert not r.ok and r.error.code == "E2008", r
    assert "noi_dung" in (r.error.details or {}), r.error.details
    assert "VDD 2.7 V" in r.error.details["noi_dung"]


def test_trich_chi_khac_KHOANG_TRANG_thi_van_nhan(bo):
    """Bộ đọc PDF và bộ đọc Office gộp khoảng trắng khác nhau, nên `trich` chỉ cần khớp sau
    khi gộp khoảng trắng — chặt hơn thế là chặn vì một chi tiết trình bày."""
    ag, ctx = bo
    so = _don_vi(ag, ctx, "LED1_PIN")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="led1", gia_tri="GPIO_PIN_6",
             trich="#define LED1_PIN GPIO_PIN_6")
    assert r.ok, getattr(r.error, "message_vi", "")


# ===================================================== đơn vị đo
def test_don_vi_do_phai_dung_sau_so(bo):
    """`don_vi_do` khai sai thì Fact mang một đơn vị không có trong tài liệu — và `ve_si` sẽ
    quy đổi nó, nên con số trong kho khác con số trên giấy."""
    ag, ctx = bo
    so = _don_vi(ag, ctx, "180 MHz")
    xau = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="fmax", gia_tri="180",
               don_vi_do="kHz", trich="Tần số tối đa 180 MHz ở dải nhiệt độ công nghiệp")
    assert not xau.ok and xau.error.code == "E2008", xau
    tot = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="fmax", gia_tri="180",
               don_vi_do="MHz", trich="Tần số tối đa 180 MHz ở dải nhiệt độ công nghiệp")
    assert tot.ok, getattr(tot.error, "message_vi", "")


# ===================================================== câu trích đã lưu
def test_quote_la_cho_CO_SO_chu_khong_phai_dau_doan(bo):
    """`source.quote` phải là chỗ **có con số**, không phải 200 ký tự đầu đoạn.

    Một đơn vị trích dẫn của tài liệu văn bản dài hàng chục dòng. Lưu 200 ký tự đầu nghĩa là
    người mở Fact ra xem thấy một đoạn **không chứa con số** — và lúc ấy trích dẫn không
    chứng minh gì cả.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "1800 nhịp")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="nhip", gia_tri="1800")
    assert r.ok, getattr(r.error, "message_vi", "")
    import json

    f = ag.store.query_facts(subject="chip:X", key="nhip", limit=5)
    src = json.loads(f[0]["source"]) if isinstance(f[0]["source"], str) else f[0]["source"]
    assert "1800" in src["quote"], src["quote"][:200]


# ============================== bảy chỗ tập phá chỉ ra là ca kiểm CHƯA chạm tới
def test_trich_lech_mot_DAU_CHAM_thi_tu_choi(bo):
    """Phép so `trich` chỉ được gộp khoảng trắng, KHÔNG được xoá dấu chấm.

    Tập phá chỉ ra rằng ca `test_27_khong_khop_2_7` không canh chỗ này: phép xoá dấu chấm
    nằm ở hàm so `trich`, còn phép khớp giá trị đi đường regex riêng. Nới `trich` ra thì câu
    trích thành *gần giống* — và một câu gần giống không chứng minh được con số nào.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "VDD 2.7")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="vdd_min", gia_tri="2.7",
             trich="VDD 27 V nguồn cấp tối thiểu của chip này")
    assert not r.ok and r.error.code == "E2008", r


def test_39_khong_khop_0_39(bo):
    """Ranh giới TRƯỚC: `39` nằm trong `0.39` thì không phải `39`.

    Một sai số 0,39 % đọc thành 39 là con số lớn gấp trăm lần — và nó vào kho mang trích dẫn.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "0.39 phần trăm")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="sai_so", gia_tri="39",
             trich="Sai số cho phép 0.39 phần trăm toàn thang")
    assert not r.ok and r.error.code == "E2006", r


def test_so_theo_sau_dau_phay_van_nhan(bo):
    """Ranh giới SAU chỉ chặn dấu chấm/phẩy **mở đầu phần thập phân**.

    `Mã lỗi 39, và…` phải còn khớp được `39` — chặn cả dấu phẩy ngắt câu là chặn một cách
    viết rất thường gặp, và lúc ấy tác tử phải đi `fact.assert_human`.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "Mã lỗi 39")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="ma_loi", gia_tri="39",
             trich="Mã lỗi 39, và mã tiếp theo là 40")
    assert r.ok, getattr(r.error, "message_vi", "")


def test_hex_sang_THAP_PHAN_khi_doan_CHI_co_mot_dang(bo):
    """Nhánh hex phải nổ thật: đoạn chỉ viết `0x27`, tác tử khai `39`.

    Ca `test_dia_chi_hex_van_nhan` KHÔNG canh được chuyện này — câu trích của nó có cả hai
    dạng, nên phép khớp trần đã tìm thấy và nhánh hex chưa bao giờ chạy tới.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "TCCR2A")
    cau = "Thanh ghi TCCR2A nhận 0x27 khi chạy chế độ CTC"
    assert "39" not in cau
    r = _ghi(ag, ctx, don_vi=so, thuc_the="reg:TCCR2A", khoa="gia_tri", gia_tri="39",
             trich=cau)
    assert r.ok, getattr(r.error, "message_vi", "")


def test_don_vi_do_o_CHO_KHAC_trong_cau_khong_tinh(bo):
    """Đơn vị phải đứng NGAY SAU số, không phải xuất hiện đâu đó trong câu.

    `Tần số 180 MHz, điện áp 3.3 V` có cả `MHz` lẫn `V`. Một phép "có mặt trong câu" sẽ nhận
    `don_vi_do="V"` cho giá trị `180` — và Fact ấy nói 180 V.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "dải thương mại")
    cau = "Tần số 180 MHz, điện áp 3.3 V ở dải thương mại"
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="fmax2", gia_tri="180",
             don_vi_do="V", trich=cau)
    assert not r.ok and r.error.code == "E2008", r
    tot = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="fmax2", gia_tri="180",
               don_vi_do="MHz", trich=cau)
    assert tot.ok, getattr(tot.error, "message_vi", "")


def test_don_vi_do_phai_khop_CA_TOKEN(bo):
    """`m` không phải `mA`. Thiếu ranh giới cuối thì một tiền tố đơn vị khớp cả đơn vị khác,
    và `ve_si` quy đổi theo cái tác tử khai — nên con số trong kho khác con số trên giấy."""
    ag, ctx = bo
    so = _don_vi(ag, ctx, "100 mA")
    cau = "Dòng tiêu thụ 100 mA ở chế độ chạy"
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="icc2", gia_tri="100",
             don_vi_do="m", trich=cau)
    assert not r.ok and r.error.code == "E2008", r
    tot = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="icc2", gia_tri="100",
               don_vi_do="mA", trich=cau)
    assert tot.ok, getattr(tot.error, "message_vi", "")


def test_quote_du_rong_de_NGUOI_doc_duoc(bo):
    """Cửa sổ quanh chỗ khớp phải đủ rộng để câu còn nghĩa.

    Một `quote` chỉ gồm con số và hai ký tự hai bên thì đúng về kỹ thuật và vô dụng với người
    mở Fact ra xem — mà *"người mở ra xem lại được"* là toàn bộ điểm của N1.
    """
    ag, ctx = bo
    so = _don_vi(ag, ctx, "1800 nhịp")
    r = _ghi(ag, ctx, don_vi=so, thuc_the="chip:X", khoa="nhip2", gia_tri="1800")
    assert r.ok, getattr(r.error, "message_vi", "")
    import json

    f = ag.store.query_facts(subject="chip:X", key="nhip2", limit=5)
    src = json.loads(f[0]["source"]) if isinstance(f[0]["source"], str) else f[0]["source"]
    assert "Bộ đếm nạp 1800 nhịp" in src["quote"], src["quote"]
