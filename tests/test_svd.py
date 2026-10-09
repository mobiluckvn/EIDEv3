# -*- coding: utf-8 -*-
"""M5-03 — SVD: hệ thống trả HAI CÂU TRẢ LỜI TRÁI NHAU cho cùng một tệp.

`ingest.phan_loai` thấy `<device>` + `peripheral` thì khai `loai="svd"`, mức hỗ trợ **ĐẦY ĐỦ**,
và `doc_duoc=True`. Rồi `doc.load` gọi `_nap_theo_loai`, mà `"svd"` không nằm trong
`_LOAI_VAN_BAN` và cũng không phải Office — nên nó rơi xuống `E1001 "chưa có bộ đọc nạp nó
vào kho"`. Comment ở `tools/knowledge.py` nói *"bốn loại đó có công cụ riêng"*; `grep -rni svd
src/` ra đúng hai chỗ: phép phân loại, và chính câu comment ấy.

Hình dạng này tệ hơn một tính năng thiếu: tác tử hỏi *"tệp này đọc được không"*, nghe **có**,
rồi nạp và nghe **không**. Nó không có cách nào biết câu nào đúng.

Điều bộ này canh, một câu: **một thanh ghi chỉ được vào kho kèm chỗ tra lại nó** — tên ngoại
vi, tên thanh ghi, địa chỉ tính ra từ base + offset, và trích dẫn `<P>.<R>[.<F>]`.
"""

from __future__ import annotations

import pytest

EX = {"summary": "s", "why": "w", "sources": [], "diff_prev": "—", "next": "—",
      "confidence": "BAC"}

# SVD tối giản: một ngoại vi thật, một ngoại vi `derivedFrom`, một cluster, hai kiểu khai bit.
SVD = """<?xml version="1.0" encoding="utf-8"?>
<device schemaVersion="1.1">
  <name>STM32F469</name>
  <peripherals>
    <peripheral>
      <name>USART1</name>
      <description>Universal synchronous asynchronous receiver transmitter</description>
      <baseAddress>0x40011000</baseAddress>
      <registers>
        <register>
          <name>BRR</name>
          <displayName>BRR</displayName>
          <addressOffset>0x08</addressOffset>
          <size>0x20</size>
          <access>read-write</access>
          <resetValue>0x00000000</resetValue>
          <fields>
            <field>
              <name>DIV_Mantissa</name>
              <bitOffset>4</bitOffset>
              <bitWidth>12</bitWidth>
            </field>
            <field>
              <name>DIV_Fraction</name>
              <bitRange>[3:0]</bitRange>
            </field>
          </fields>
        </register>
        <register>
          <name>CR1</name>
          <addressOffset>0x0C</addressOffset>
          <resetValue>0x00000000</resetValue>
        </register>
      </registers>
    </peripheral>
    <peripheral derivedFrom="USART1">
      <name>USART2</name>
      <baseAddress>0x40004400</baseAddress>
    </peripheral>
  </peripherals>
</device>
"""


@pytest.fixture
def bo(du_an):
    from eide import Config
    from eide.llm import ScriptedGateway
    from eide.loop import Agent, TurnContext

    ag = Agent(Config.for_project(du_an), llm=ScriptedGateway([]), project_name="du-an-thu")
    ctx = TurnContext(config=ag.config, store=ag.store, ledger=ag.ledger, eide_md=ag.eide_md,
                      ids=ag.ids, registry=ag.registry, emit=lambda c: None,
                      history=ag.history, agent=ag, run_id="run-1", project_name="du-an-thu")
    return ag, ctx


def _svd(du_an, noi_dung: str = SVD, ten: str = "stm32f469.svd"):
    p = du_an / ten
    p.write_text(noi_dung, "utf-8")
    return p


# ========================================================= hai câu trả lời phải thành MỘT
def test_phan_loai_va_doc_load_KHONG_con_noi_nguoc_nhau(bo):
    """TC-M5-03-01 — `phan_loai` nói ĐẦY ĐỦ thì `doc.load` phải nạp được."""
    from eide.knowledge import ingest as I

    ag, ctx = bo
    p = _svd(ag.config.paths.project_root)
    kq = I.phan_loai(p)
    assert kq.loai == "svd" and kq.doc_duoc

    r = ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-F469",
                                     "nguon": "nha_san_xuat", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    # USART1: BRR, CR1 · USART2 (derivedFrom): BRR, CR1 → 4 thanh ghi, và 2 trường bit của
    # BRR được sao sang USART2 nên có 4 trường.
    assert r.data["so_thanh_ghi"] == 4, r.data
    assert r.data["so_truong"] == 4, r.data


def test_doc_load_nap_svd_thanh_fact_co_dia_chi(bo):
    """TC-M5-03-01 (phần Fact) — `dia_chi` phải là base + offset đã tính, dạng hex.

    Không để tác tử tự cộng: một phép cộng hex nhớ trong đầu là đúng kiểu con số mà §C1 đòi
    phải có nguồn, và `0x40011000 + 0x08` sai một chữ số thì firmware ghi vào thanh ghi khác.
    """
    ag, ctx = bo
    _svd(ag.config.paths.project_root)
    ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-F469",
                                 "nguon": "nha_san_xuat", "explain": EX}, ctx)

    d = {x["key"]: x for x in ag.store.query_facts(subject="reg:USART1.BRR", limit=50)}
    assert d["dia_chi"]["value"] == "0x40011008", d["dia_chi"]
    assert d["reset"]["value"] == "0x00000000", d["reset"]
    # `size` và `access` chỉ ghi khi SVD KHAI chúng — không khai thì không bịa mặc định 32 bit.
    assert d["size"]["value"] == "32", d["size"]
    assert d["access"]["value"] == "read-write", d["access"]
    assert "size" not in {x["key"] for x in ag.store.query_facts(subject="reg:USART1.CR1")}


def test_fact_mang_trich_dan_tra_lai_duoc(bo):
    """Một Fact thanh ghi không có `cite` thì không ai mở SVD ra kiểm lại được — và lúc ấy
    nó chỉ là một con số nhớ hộ, đúng thứ N1 tồn tại để ngăn."""
    import json

    ag, ctx = bo
    _svd(ag.config.paths.project_root)
    ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-F469",
                                 "nguon": "nha_san_xuat", "explain": EX}, ctx)
    f = ag.store.query_facts(subject="reg:USART1.BRR", key="dia_chi")[0]
    src = json.loads(f["source"])
    assert src["doc_id"] == "SVD-F469"
    assert src["cite"] == "USART1.BRR", src
    assert "0x40011008" in src["quote"], src
    # Tầng theo NGUỒN, không cứng: nhà sản xuất là BẠC, và chỉ người duyệt mới lên VÀNG (N1).
    assert f["tier"] == "BAC", f["tier"]


def test_derivedFrom_sao_thanh_ghi(bo):
    """TC-M5-03-02 — `derivedFrom` là cách SVD thật mô tả USART2…USART6.

    Không xử lý nó thì mất gần hết thanh ghi của một chip: trên SVD thật của STM32F469,
    phần lớn ngoại vi cùng họ khai bằng một dòng `derivedFrom` và không có `<registers>`.
    """
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root)
    tl = S.doc_svd(p, doc_id="SVD-F469")
    nhan = [t.nhan for t in tl.trang]
    assert "USART2.BRR" in nhan, nhan
    f = S.fact_tu_svd(tl, thuc_the="chip:STM32F469", tier="BAC")
    d = {(x["subject"], x["key"]): x["value"] for x in f}
    assert d[("reg:USART2.BRR", "dia_chi")] == "0x40004408"


def test_bitRange(bo):
    """TC-M5-03-03 — SVD thật dùng CẢ HAI lối khai bit. ARM cho phép cả
    `bitOffset`+`bitWidth` lẫn `bitRange` `[msb:lsb]`, và STM32 trộn cả hai trong một tệp."""
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root)
    tl = S.doc_svd(p, doc_id="SVD-F469")
    f = {(x["subject"], x["key"]): x["value"]
         for x in S.fact_tu_svd(tl, thuc_the="chip:STM32F469", tier="BAC")}
    assert f[("field:USART1.BRR.DIV_Mantissa", "bit_offset")] == 4
    assert f[("field:USART1.BRR.DIV_Mantissa", "bit_width")] == 12
    assert f[("field:USART1.BRR.DIV_Fraction", "bit_offset")] == 0
    assert f[("field:USART1.BRR.DIV_Fraction", "bit_width")] == 4


def test_cluster_mot_cap(bo):
    """`<cluster>` gói một nhóm thanh ghi lặp lại và cộng thêm một offset của riêng nó.
    Bỏ qua cluster thì mất thanh ghi; cộng thiếu offset thì ra địa chỉ SAI — và một địa chỉ
    sai tệ hơn một thanh ghi thiếu, vì nó trông như đã có."""
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root, SVD.replace(
        "</registers>",
        """  <cluster>
          <name>GRP</name>
          <addressOffset>0x40</addressOffset>
          <register>
            <name>DR</name>
            <addressOffset>0x04</addressOffset>
          </register>
        </cluster>
      </registers>"""))
    tl = S.doc_svd(p, doc_id="SVD-F469")
    f = {(x["subject"], x["key"]): x["value"]
         for x in S.fact_tu_svd(tl, thuc_the="chip:STM32F469", tier="BAC")}
    assert f[("reg:USART1.GRP.DR", "dia_chi")] == "0x40011044"


def test_xml_hong_noi_ro(bo):
    """TC-M5-03-04 — XML cắt cụt. Hai điều phải cùng đúng: nói rõ vì sao, và **không ghi Fact
    nào**. Ghi một nửa register map rồi báo lỗi là trạng thái tệ nhất — kho có số, không ai
    biết nó thiếu."""
    ag, ctx = bo
    _svd(ag.config.paths.project_root, SVD[:SVD.index("<name>BRR</name>") + 10])
    r = ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-F469",
                                     "nguon": "nha_san_xuat", "explain": EX}, ctx)
    assert not r.ok and r.error.code == "E2007", r
    assert "SVD không đọc được" in r.error.message_vi
    assert ag.store.query_facts(subject="reg:") == []


def test_svd_khong_co_ngoai_vi_nao_thi_noi_RONG_chu_khong_bao_dat(bo):
    """Một SVD hợp lệ về XML mà không có thanh ghi nào là *"đọc được và rỗng"*, không phải
    *"đã nạp register map"*. Im lặng trả 0 thì tác tử đọc thành đã có."""
    ag, ctx = bo
    _svd(ag.config.paths.project_root,
         '<?xml version="1.0"?>\n<device><name>X</name><peripherals>'
         '<peripheral><name>P</name><baseAddress>0x0</baseAddress></peripheral>'
         '</peripherals></device>\n')
    r = ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-X",
                                     "nguon": "nha_san_xuat", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_thanh_ghi"] == 0
    assert "không có thanh ghi nào" in r.data["note_vi"].lower()


def test_xml_thuong_khong_bi_nhan_la_svd(du_an):
    """TC-M5-03-05 — giữ hành vi cũ: XML không có `<peripheral>` vẫn là `xml`."""
    from eide.knowledge import ingest as I

    p = du_an / "cau-hinh.xml"
    p.write_text('<?xml version="1.0"?>\n<root><a>1</a></root>\n', "utf-8")
    assert I.phan_loai(p).loai == "xml"


def test_netlist_van_bi_doc_load_tu_choi(bo):
    """Bảo vệ hồi quy của nhiệm vụ: mở đường cho `svd` KHÔNG được mở đường cho ba loại kia.
    Chúng vẫn phải bị từ chối, vì nạp một netlist thành văn bản thô là che mất đường đúng
    bằng một đường tệ hơn."""
    ag, ctx = bo
    p = ag.config.paths.project_root / "mach.net"
    p.write_text("(export (version D)\n (components))\n", "utf-8")
    r = ag.registry.run("doc.load", {"path": "mach.net", "doc_id": "NET-1",
                                     "nguon": "noi_bo", "explain": EX}, ctx)
    assert not r.ok, r


# ================================================================== công cụ reg.lookup
def test_reg_lookup_tim_duoc_thanh_ghi_va_truong(bo):
    """TC-M5-03-04 (phần công cụ) — tra một tên trả về cả thanh ghi lẫn trường bit của nó,
    kèm trích dẫn. Không có công cụ này thì Fact vào kho rồi không ai lấy ra được, và tác tử
    sẽ đi `fs.grep` trong tệp SVD — cùng hình dạng đã đo được với header BSP."""
    ag, ctx = bo
    _svd(ag.config.paths.project_root)
    ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-F469",
                                 "nguon": "nha_san_xuat", "explain": EX}, ctx)

    r = ag.registry.run("reg.lookup", {"ten": "USART1.BRR"}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    ten = {d["ten"] for d in r.data["dong"]}
    assert "reg:USART1.BRR" in ten and "field:USART1.BRR.DIV_Mantissa" in ten, ten
    assert any(d.get("cite") for d in r.data["dong"])


def test_reg_lookup_KHONG_THAY_thi_noi_thang(bo):
    """Rỗng là một câu trả lời, nhưng nó phải nói ra là *chưa nạp SVD nào* chứ không phải
    *không có thanh ghi ấy* — hai câu dẫn tới hai việc khác nhau."""
    ag, ctx = bo
    r = ag.registry.run("reg.lookup", {"ten": "USART9.XYZ"}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["dong"] == []
    assert "chưa nạp" in r.data["note_vi"].lower()


def test_reg_lookup_co_tran_dong(bo):
    """Một ngoại vi thật có hàng chục thanh ghi × hàng chục trường. Trả hết vào transcript là
    tiêu cửa sổ ngữ cảnh cho một phép tra — và phải NÓI RA là đang cắt, không thì 20 dòng đọc
    như toàn bộ."""
    ag, ctx = bo
    # Mỗi thanh ghi phải có HAI Fact (`dia_chi` + `reset`), không thì phép gom theo chủ
    # thể và phép không gom cùng ra 25 dòng — và ca này không phân biệt được hai cái.
    reg = "".join(f"<register><name>R{i:02d}</name>"
                  f"<addressOffset>0x{i * 4:02X}</addressOffset>"
                  f"<resetValue>0x0</resetValue></register>"
                  for i in range(25))
    _svd(ag.config.paths.project_root,
         '<?xml version="1.0"?>\n<device><name>X</name><peripherals><peripheral>'
         '<name>TIM1</name><baseAddress>0x40010000</baseAddress><registers>'
         + reg + "</registers></peripheral></peripherals></device>\n")
    ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-X",
                                 "nguon": "nha_san_xuat", "explain": EX}, ctx)
    r = ag.registry.run("reg.lookup", {"ten": "TIM1"}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert len(r.data["dong"]) == 20, len(r.data["dong"])
    assert r.data["so_khop"] == 25, r.data["so_khop"]
    assert "25" in r.data["note_vi"], r.data["note_vi"]


def test_derivedFrom_KHONG_de_len_thanh_ghi_rieng(bo):
    """`derivedFrom` chỉ dùng khi ngoại vi KHÔNG tự khai thanh ghi.

    SVD thật có ngoại vi vừa `derivedFrom` vừa khai thêm/ghi đè một phần. Lấy thanh ghi của
    ngoại vi gốc trong trường hợp ấy là ghi vào kho một register map KHÔNG phải của nó — và
    nó trông đúng y như một register map thật.
    """
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root, SVD.replace(
        """    <peripheral derivedFrom="USART1">
      <name>USART2</name>
      <baseAddress>0x40004400</baseAddress>
    </peripheral>""",
        """    <peripheral derivedFrom="USART1">
      <name>USART2</name>
      <baseAddress>0x40004400</baseAddress>
      <registers>
        <register><name>RIENG</name><addressOffset>0x20</addressOffset></register>
      </registers>
    </peripheral>"""))
    tl = S.doc_svd(p, doc_id="SVD-F469")
    nhan = [t.nhan for t in tl.trang]
    assert "USART2.RIENG" in nhan, nhan
    assert "USART2.BRR" not in nhan, "thanh ghi của ngoại vi GỐC bị đè lên bản tự khai"


def test_dia_chi_luon_du_tam_chu_so_hex(bo):
    """Địa chỉ ghi `0x` + **tám** chữ số, như datasheet viết.

    `0x44` và `0x00000044` là cùng một số mà không cùng một thứ với người đọc: một cái trông
    như offset, một cái trông như địa chỉ tuyệt đối. Tác tử sẽ cộng base vào cái thứ nhất
    lần thứ hai.
    """
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root,
             '<?xml version="1.0"?>\n<device><name>X</name><peripherals><peripheral>'
             '<name>P</name><baseAddress>0x40</baseAddress><registers>'
             '<register><name>R</name><addressOffset>0x4</addressOffset></register>'
             '</registers></peripheral></peripherals></device>\n')
    tl = S.doc_svd(p, doc_id="SVD-X")
    f = {(x["subject"], x["key"]): x["value"]
         for x in S.fact_tu_svd(tl, thuc_the="chip:X", tier="BAC")}
    assert f[("reg:P.R", "dia_chi")] == "0x00000044"


def test_tran_don_vi_cat_thi_NOI_RA(bo, monkeypatch):
    """Trần phải NÓI RA chỗ nó cắt.

    SVD thật của một MCU họ F4 có cỡ 1 500–3 000 thanh ghi và hơn 10 000 trường bit, nên trần
    là cần. Nhưng cắt im lặng thì tác tử tra một thanh ghi ở cuối tệp, nhận "không có", rồi
    kết luận *chip không có thanh ghi ấy* — trong khi câu đúng là *chưa nạp tới*.
    """
    from eide.knowledge import svd as S

    ag, ctx = bo
    monkeypatch.setattr(S, "TRAN_DON_VI", 3)
    reg = "".join(f"<register><name>R{i}</name>"
                  f"<addressOffset>0x{i * 4:02X}</addressOffset></register>"
                  for i in range(10))
    _svd(ag.config.paths.project_root,
         '<?xml version="1.0"?>\n<device><name>X</name><peripherals><peripheral>'
         '<name>TIM1</name><baseAddress>0x40010000</baseAddress><registers>'
         + reg + "</registers></peripheral></peripherals></device>\n")
    r = ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-X",
                                     "nguon": "nha_san_xuat", "explain": EX}, ctx)
    assert r.ok, getattr(r.error, "message_vi", "")
    assert r.data["so_thanh_ghi"] == 3, r.data["so_thanh_ghi"]
    assert r.data.get("da_cat_o_tran") == 3, r.data
    assert "CHƯA được nạp" in r.data["note_vi"], r.data["note_vi"]
    assert "chưa nạp tới" in r.data["note_vi"].lower()


def test_base_khong_doc_duoc_thi_BO_NGOAI_VI_chu_khong_lay_0(bo):
    """Một `baseAddress` không đọc được phải làm cả ngoại vi bị BỎ, không thành `base = 0`.

    `base = 0` là chỗ sai tệ nhất mà một phép đọc số có thể chọn: mọi địa chỉ của ngoại vi ấy
    thành offset trần, và chúng **trông vẫn như địa chỉ**. Không ai kêu, và firmware ghi vào
    vùng 0x0.
    """
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root,
             '<?xml version="1.0"?>\n<device><name>X</name><peripherals>'
             '<peripheral><name>XAU</name><baseAddress>khong-phai-so</baseAddress>'
             '<registers><register><name>R</name><addressOffset>0x8</addressOffset>'
             "</register></registers></peripheral>"
             '<peripheral><name>TOT</name><baseAddress>0x40000000</baseAddress>'
             '<registers><register><name>R</name><addressOffset>0x8</addressOffset>'
             "</register></registers></peripheral>"
             "</peripherals></device>\n")
    tl = S.doc_svd(p, doc_id="SVD-X")
    nhan = [t.nhan for t in tl.trang]
    assert nhan == ["TOT.R"], nhan
    assert S.dem(tl)[0] == 1


def test_thanh_ghi_thieu_addressOffset_thi_BO(bo):
    """Thiếu `addressOffset` thì bỏ thanh ghi, không lấy `base` làm địa chỉ của nó.

    Cùng hình dạng với ca trên: một địa chỉ bằng base là một địa chỉ **sai mà hợp lệ**. Thiếu
    một thanh ghi thì tác tử đi tra tiếp; có một thanh ghi sai thì nó dùng luôn.
    """
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root,
             '<?xml version="1.0"?>\n<device><name>X</name><peripherals><peripheral>'
             '<name>P</name><baseAddress>0x40000000</baseAddress><registers>'
             "<register><name>THIEU</name></register>"
             '<register><name>CO</name><addressOffset>0x4</addressOffset></register>'
             "</registers></peripheral></peripherals></device>\n")
    tl = S.doc_svd(p, doc_id="SVD-X")
    assert [t.nhan for t in tl.trang] == ["P.CO"], [t.nhan for t in tl.trang]


def test_loi_khai_bit_thu_ba_lsb_msb(bo):
    """ARM cho **ba** lối khai vị trí bit; SVD của Nordic và SiLabs dùng lối `<lsb>/<msb>`.

    Đọc hai lối thôi thì một dòng SVD hợp lệ bị bỏ im lặng — và một trường bit thiếu không
    kêu lên, nó chỉ làm tác tử phải tự nhớ vị trí bit.
    """
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root,
             '<?xml version="1.0"?>\n<device><name>X</name><peripherals><peripheral>'
             '<name>P</name><baseAddress>0x40000000</baseAddress><registers>'
             '<register><name>R</name><addressOffset>0x0</addressOffset><fields>'
             "<field><name>F</name><lsb>2</lsb><msb>5</msb></field>"
             "</fields></register></registers></peripheral></peripherals></device>\n")
    tl = S.doc_svd(p, doc_id="SVD-X")
    f = {(x["subject"], x["key"]): x["value"]
         for x in S.fact_tu_svd(tl, thuc_the="chip:X", tier="BAC")}
    assert f[("field:P.R.F", "bit_offset")] == 2
    assert f[("field:P.R.F", "bit_width")] == 4


def test_dem_tra_HAI_con_so_khac_nhau(bo):
    """`dem()` phải trả hai con số ĐỘC LẬP.

    Ca `test_phan_loai_va_doc_load…` của chính bộ này ra 4 thanh ghi và 4 trường — hai con số
    **bằng nhau**, nên nó xanh cả khi `dem()` trả `(r, r)`. Phép phá chỉ ra đúng điều đó: một
    phép đo mà hai vế tình cờ bằng nhau thì nó không đo được vế nào.
    """
    from eide.knowledge import svd as S

    ag, _ctx = bo
    p = _svd(ag.config.paths.project_root,
             '<?xml version="1.0"?>\n<device><name>X</name><peripherals><peripheral>'
             '<name>P</name><baseAddress>0x40000000</baseAddress><registers>'
             '<register><name>R</name><addressOffset>0x0</addressOffset><fields>'
             "<field><name>A</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth></field>"
             "<field><name>B</name><bitOffset>1</bitOffset><bitWidth>1</bitWidth></field>"
             "<field><name>C</name><bitOffset>2</bitOffset><bitWidth>1</bitWidth></field>"
             "</fields></register></registers></peripheral></peripherals></device>\n")
    tl = S.doc_svd(p, doc_id="SVD-X")
    assert S.dem(tl) == (1, 3), S.dem(tl)


def test_reg_lookup_tran_khong_nang_duoc_qua_tham_so(bo):
    """Trần 20 là trần của **công cụ**, không phải mặc định gợi ý.

    Một tham số `gioi_han` nâng được lên 500 thì trần biến thành một con số trang trí: tác tử
    đang tìm thì sẽ nâng, và cửa sổ ngữ cảnh mất vào một phép tra.
    """
    ag, ctx = bo
    reg = "".join(f"<register><name>R{i:02d}</name>"
                  f"<addressOffset>0x{i * 4:02X}</addressOffset></register>"
                  for i in range(25))
    _svd(ag.config.paths.project_root,
         '<?xml version="1.0"?>\n<device><name>X</name><peripherals><peripheral>'
         '<name>TIM1</name><baseAddress>0x40010000</baseAddress><registers>'
         + reg + "</registers></peripheral></peripherals></device>\n")
    ag.registry.run("doc.load", {"path": "stm32f469.svd", "doc_id": "SVD-X",
                                 "nguon": "nha_san_xuat", "explain": EX}, ctx)
    r = ag.registry.run("reg.lookup", {"ten": "TIM1", "gioi_han": 500}, ctx)
    assert r.ok and len(r.data["dong"]) == 20, len(r.data["dong"])


# ===================================================================== SVD THẬT trên máy
def _svd_that():
    """Tệp SVD thật đầu tiên tìm được trên máy, hoặc None.

    Quét 09/10/2026 trên máy này: **không có tệp `.svd` nào** ngoài các tệp do chính bộ kiểm
    sinh ra trong `tmp`. Nên ca dưới SKIP, và nó skip một cách **nói ra được** — con số
    "nạp được N thanh ghi của một chip thật" chưa có, và ghi vào DEV-LOG đúng như thế thay vì
    dựng một tệp SVD tự viết rồi gọi nó là *thật*.
    """
    from pathlib import Path

    for goc in (Path.home() / "STM32Cube", Path.home() / ".platformio",
                Path("/Applications/STM32CubeIDE.app"),
                Path(__file__).resolve().parents[1] / "tai-lieu-tham-khao"):
        if goc.exists():
            for p in goc.rglob("*.svd"):
                return p
    return None


@pytest.mark.nha_that
@pytest.mark.skipif(_svd_that() is None, reason="máy này không có tệp .svd thật nào")
def test_nap_duoc_SVD_THAT(bo):
    """Một SVD thật có cỡ 1 500–3 000 thanh ghi và hơn 10 000 trường bit, `derivedFrom` khắp
    nơi, và cluster lồng nhau. Bộ đọc chạy đúng trên tệp tự viết chưa nói được gì về nó."""
    from eide.knowledge import svd as S

    p = _svd_that()
    tl = S.doc_svd(p, doc_id="SVD-THAT")
    so_reg, so_field = S.dem(tl)
    assert so_reg > 50, f"{p.name}: chỉ đọc được {so_reg} thanh ghi"
    f = S.fact_tu_svd(tl, thuc_the="chip:that", tier="BAC")
    # Mọi Fact địa chỉ phải là hex tám chữ số — không có cái nào rơi về offset trần.
    dc = [x["value"] for x in f if x["key"] == "dia_chi"]
    assert dc and all(len(v) == 10 and v.startswith("0x") for v in dc), dc[:5]
    print(f"\nSVD thật: {p.name} → {so_reg} thanh ghi · {so_field} trường bit · {len(f)} Fact")
