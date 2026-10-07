# ĐANG LÀM — chỗ dừng ngày 07/10/2026

> Tệp này trả lời đúng một câu cho phiên sau: **mở ra là làm tiếp được từ đâu.**
> Trạng thái đầy đủ của 106 việc nằm ở `EIDE_Toi_uu_Agent_2026-10-06.xlsx`,
> sheet **“Tiến độ 07-10-2026”** (cột T–Y của sheet “Danh mục tối ưu” là bằng chứng từng việc).

## Đang ở đâu

| | |
|---|---|
| **Xong** | **14/106** — việc #1 → #14 của Giai đoạn 1, theo đúng thứ tự `#` của kế hoạch |
| **Đang dở** | **#15 M3-13** — nhánh `toi-uu/M3-13`, commit `08788c2`, **chưa gộp `main`** |
| `main` | `4a192bd` — chỉ chứa việc đã qua cổng 4.1 |
| Ca kiểm | 1 610 → **1 732** xanh, 0 đỏ · `swift test` 43 · `kiem_tai_lieu` 0 chỗ lệch |
| Nhật ký | DEV-330 → DEV-343 trong `docs/md/EIDE-DEV-LOG.md` |

## Việc đầu tiên của ngày mai: chốt #15 (M3-13)

Mã đã viết xong và 86 ca trong `tests/test_hdl.py` + `tests/test_dot_bien.py` đã xanh;
“phá lại thì đỏ” đã làm cho **cả 6** chỗ sửa. Còn đúng năm bước cuối của quy trình §3.1:

```bash
git switch toi-uu/M3-13
find src tests -name __pycache__ -type d -exec rm -rf {} +      # bắt buộc, xem DEV-335
.venv/bin/python -m pytest -q -rf            # phải ≥ 1732 + ca mới, không ca cũ nào đỏ
.venv/bin/python tools/kiem_tai_lieu.py      # phải 0 chỗ LỆCH CHẮC CHẮN
```

rồi: ghi **DEV-344** · đánh dấu ☑ dòng 15 bảng mục 5 · commit chốt · `git switch main`
→ `git merge --ff-only toi-uu/M3-13` → `git push origin main`.

Số đo đã có sẵn cho DEV-344, **không cần đo lại**:

* testbench **thật** của bài 3 (lõi RISC-V): `pcpi_dot4` bắt **1/1**, `pcpi_mac` bắt **1/1**
  — phép phá *“đảo điều kiện if”* làm bộ kiểm đỏ. `pcpi_vmini` **chưa đo được**: tb của nó
  cần mô-đun `ram` ngoài phần nó tự `include`.
* một lỗi của chính phép đo, đáng ghi vào DEV-344: dàn dựng đầu tiên của tôi gom RTL + tb
  vào một thư mục, nên `` `include "bai3/rtl/pcpi_mac.v" `` (đường dẫn tính từ gốc dự án)
  đứt và **cả ba** ca báo *“bộ kiểm đang ĐỎ từ trước”* — một kết luận sai về sản phẩm, sinh
  ra từ một dàn dựng sai. Đúng hình dạng việc còn mở trong README §8 về đường dựng bitstream.
* một ca cũ phải nới: `test_do_nhay_di_theo_hien_vat_khong_chi_tra_cho_mo_hinh` chốt cứng
  cả dict `do_nhay`; nay chỉ kiểm `bat`/`tong` **có vào kho** — đúng ý “Bảo vệ hồi quy” của
  nhiệm vụ ghi.

## Sau đó: #16 M3-18

Kiểm ràng buộc chân FPGA (`.cst`) với cổng mô-đun đỉnh và chân của kit — P0 · M, không cờ.
Hết #16 là **xong 4 việc mảng 3** liền nhau; nhớ chạy lại **cổng cuối giai đoạn (§4.2)** khi
hết Giai đoạn 1, không phải sau mỗi việc.

## Hai thứ phải đọc trước khi gõ dòng đầu tiên

1. **Xoá `__pycache__` trước mỗi phép “phá lại thì đỏ”.** Một phép phá dài **đúng bằng** mã
   gốc (`0.6` → `0.0`) làm Python coi `.pyc` cũ là còn hợp lệ, và phép đo chạy **mã khác với
   mã trong tệp**. Mất một lúc mới thấy — xem DEV-335.
2. **Kế hoạch có chỗ sai; đo trước khi tin.** Đã gặp bốn lần trong 14 việc:
   A2.5 đã có chủ (M2-02) · mã lỗi ghi nhầm E6010 (M2-06) · regex PASS/FAIL từ chối oan
   588/846 bản ghi thật (M3-12) · và nhận định “phần dài nằm ở mô tả tham số” chỉ đúng một
   nửa (M1-02, luật cắt 160 ký tự chỉ thu 0,46 %).

## Việc còn MỞ, không thuộc nhiệm vụ nào trong 106

* **Sáu cờ mới đều còn TẮT** — `GON_CONG_CU` · `TRUY_VET` · `REQ_PHU` · `REQ_CHAT_LUONG` ·
  `KE_HOACH_CONG_KIEM` · `ERC_TU_DONG`. Cả sáu đổi thứ Agent **nhìn thấy hoặc đọc mỗi lượt**,
  nên chỉ bộ 76 ca chạy **hai chế độ** mới nói được chúng làm Agent khá hơn hay tệ hơn. Bộ ấy
  tốn tiền mô hình nên §3.0 bắt **hỏi người dùng trước**.
* **`kiem_cap_goi_tra()` chưa thành hàng rào** — soát được mọi phiên đã lưu, nhưng chưa hook
  nào gọi tự động: bắt được chuyện cũ, chưa chặn được chuyện mới.
* **Luật ERC quá áp chưa nổ trên dữ liệu thật** — đường dẫn đã thông ở M3-07, nhưng ba kho có
  Fact điện áp thì không có mô hình mạch, và ngược lại.
* **Lỗi `_go_dau` trong `src/eide/tools/design.py`** — viết `.replace("d", "d")` nên
  `"ổn định"` và `"ON DINH"` không khớp nhau; hàm ấy đang dùng cho một phép kiểm an toàn
  (*người có thật sự chọn không*). Tìm thấy ở M2-03, **chưa sửa** vì ngoài phạm vi.
* **`req-critic`** (bước 4 của M2-03) — kế hoạch ghi “tuỳ chọn, gộp M2-13”. Chưa làm, đúng
  theo kế hoạch.
