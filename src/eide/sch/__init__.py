# -*- coding: utf-8 -*-
"""Sinh sơ đồ nguyên lý KiCad — EIDE-SCH-44, sửa theo EIDE-HIER-45 §7.

Gói này **cách ly**: nó gọi API công khai của cây khối (`knowledge.cay`), kho và policy,
nhưng không có chỗ nào trong mã cũ import vào đây (SCH-44 §2.1 lớp bảo vệ số 1). Cờ
`features.schematic` tắt thì các tool `sch.*` **không được đăng ký** — mô hình không thấy,
không gọi được, và lược đồ tool không tăng một token nào.

Ràng buộc cứng của quyết định 25/09/2026: **máy này KHÔNG cài KiCad.** Không gọi
`kicad-cli`, không đề nghị người dùng cài KiCad ở bất kỳ thông điệp nào (SCH-09 — có chốt
chặn ở hook `Stop`, vì cấm bằng lời trong hiến pháp là cấm không đo được). Thư viện ký hiệu
KiCad chỉ được tải về như **dữ liệu**.
"""

# Hàm tên `tinh_bo_cuc`, KHÔNG phải `bo_cuc`: một hàm trùng tên module của nó sẽ
# che module khi ai đó `from eide.sch import bo_cuc` — và lỗi đó im lặng.
from .bo_cuc import kiem_tieu_chi, tinh_bo_cuc
from .doc_skidl import doc_skidl
from .ghi import doc_lai_duoc, kicad_pro, uuid_theo, viet_kicad_sch
from .netlist import so_dang_cau, viet_net
from .soan import soan_skidl
from .ve_svg import ve

__all__ = ["soan_skidl", "doc_skidl", "so_dang_cau", "viet_net", "tinh_bo_cuc",
           "kiem_tieu_chi", "viet_kicad_sch", "doc_lai_duoc", "uuid_theo",
           "kicad_pro", "ve"]
