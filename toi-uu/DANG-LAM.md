# ĐANG LÀM — chỗ dừng ngày 08/10/2026

> Tệp này trả lời đúng một câu cho phiên sau: **mở ra là làm tiếp được từ đâu.**
> Trạng thái đầy đủ của 106 việc nằm ở `EIDE_Toi_uu_Agent_2026-10-06.xlsx`,
> sheet **“Tiến độ 08-10-2026”** (cột Q, T–Y của sheet “Danh mục tối ưu” là bằng chứng từng việc).

## Đang ở đâu

| | |
|---|---|
| **Xong** | **16/106** — việc #1 → #16 của Giai đoạn 1, theo đúng thứ tự `#` của kế hoạch |
| **Đang dở** | **không có.** `main` = `7b5f98d`, đã đẩy. Mọi nhánh `toi-uu/*` đã gộp. |
| Ca kiểm | 1 610 → **1 773** xanh, 0 đỏ · `swift test` 43 · `kiem_tai_lieu` 0 chỗ LỆCH |
| Nhật ký | DEV-330 → **DEV-345** trong `docs/md/EIDE-DEV-LOG.md` |
| Công cụ | 127 → **129** (`hdl.sensitivity`, `hdl.constraints_check`) |

## Việc đầu tiên của phiên sau: #17 M4-01

Máy chấm unit test do EIDE phán (`test.criteria`) — P0 · M, không cờ, không tiền đề.
Mở `KE-HOACH-SUA-VA-KIEM-THU.md`, mục `[M4-01]`, làm đúng quy trình §3.1:

```bash
git switch -c toi-uu/M4-01
# viết TC TRƯỚC, xem chúng ĐỎ trên mã hiện tại
find src tests -name __pycache__ -type d -exec rm -rf {} +      # bắt buộc, xem DEV-335
.venv/bin/python -m pytest -q -rf            # mốc: 1773, không ca cũ nào đỏ
.venv/bin/python tools/kiem_tai_lieu.py      # phải 0 chỗ LỆCH CHẮC CHẮN
```

Hết Giai đoạn 1 mới chạy **cổng cuối giai đoạn (§4.2)**, không phải sau mỗi việc.
Nhớ: công cụ mới nào cũng làm README lệch số công cụ — sửa 4 chỗ (dòng ~43 tổng + số bật
mặc định, dòng bảng nhóm việc, dòng ~1041 phần chưa dùng thật, dòng ~1180 cây mã).

## Bốn thứ phải đọc trước khi gõ dòng đầu tiên

1. **Xoá `__pycache__` trước mỗi phép “phá lại thì đỏ”.** Một phép phá dài **đúng bằng** mã
   gốc (`0.6` → `0.0`) làm Python coi `.pyc` cũ là còn hợp lệ, và phép đo chạy **mã khác với
   mã trong tệp** — DEV-335.
2. **“Phá lại thì đỏ N/N” nói được điều gì chỉ khi tập phép phá không do người đang mong nó
   đẹp chọn ra.** M3-13 khai 6/6; phá bằng tập rộng hơn ra **7/9**. M3-18 ra **18/20** ở lượt
   đầu. Cách dựng tập: đi theo *chỗ mã tháo được*, không theo *chỗ mình biết đã có ca canh*.
   Và mỗi nhánh `if` của một hàm là **một** chỗ, không phải cả hàm là một chỗ.
3. **Kế hoạch có chỗ sai; đo trước khi tin.** Sáu lần trong 16 việc: A2.5 đã có chủ (M2-02) ·
   mã lỗi ghi nhầm E6010 (M2-06) · regex PASS/FAIL từ chối oan 588/846 (M3-12) · “phần dài
   nằm ở mô tả tham số” chỉ đúng một nửa (M1-02) · mã lỗi E4031 đã có chủ ở `loop.py`
   (M3-18) · khoá Fact chân kit kế hoạch ghi `chuc_nang`, mã ghi `ten`/`net`/`af` (M3-18).
4. **Phạm vi phép đo sai thì ra một con số *hợp lý* chứ không ra rỗng** — và lúc ấy nó tốn
   nhiều lượt hơn. Hai lần trong M3-18: ghép mọi mạng cổng với mọi `.cst` ra “409 lỗi” trong
   khi số thật là **1**; và phép quét tệp `.cst` thật thu 4 trong 7 tệp mà ca kiểm vẫn xanh.

## Việc còn MỞ, không thuộc nhiệm vụ nào trong 106

* **Sáu cờ mới đều còn TẮT** — `GON_CONG_CU` · `TRUY_VET` · `REQ_PHU` · `REQ_CHAT_LUONG` ·
  `KE_HOACH_CONG_KIEM` · `ERC_TU_DONG`. Cả sáu đổi thứ Agent **nhìn thấy hoặc đọc mỗi lượt**,
  nên chỉ bộ 76 ca chạy **hai chế độ** mới nói được chúng làm Agent khá hơn hay tệ hơn. Bộ ấy
  tốn tiền mô hình nên §3.0 bắt **hỏi người dùng trước**.
* **Hai công cụ mới nhất chưa lượt Agent nào GỌI** — `hdl.sensitivity` và
  `hdl.constraints_check`. Mã của cả hai đã chạy trên hiện vật thật, nhưng đó là tôi gọi hàm,
  không phải tác tử gọi công cụ. README §8 đếm cả hai vào phần chưa dùng thật.
* **`kiem_cap_goi_tra()` chưa thành hàng rào** — soát được mọi phiên đã lưu, nhưng chưa hook
  nào gọi tự động: bắt được chuyện cũ, chưa chặn được chuyện mới.
* **Ba luật kiểm chưa nổ được trên dữ liệu thật vì thiếu dữ liệu, không vì sai:**
  luật ERC quá áp (ba kho có Fact điện áp thì không có mô hình mạch, và ngược lại), rồi
  `chan_lech_kit` và `io_type_lech_bank` của M3-18 — **không kho nào** trong repo có Fact
  `pin:tangnano20k.*` hay khoá `vccio`. Cả ba đã có đường dẫn đo được, chỉ chưa ai nạp dữ liệu.
* **Một bitstream cũ đã dựng với chân đồng hồ do nextpnr tự chọn** — `blinky` của
  `du-lieu/riscv-tn20k-b`: cổng `sys_clk` không có `IO_LOC` ở bất kỳ tệp `.cst` nào, mà
  `blinky.fs` 4,6 MB vẫn dựng ra 01/10/2026. Nó rơi đúng chân 4 nên có thể đã chạy đúng —
  bằng may. Không sửa hiện vật cũ; từ nay `dat_di_day` chặn trước nextpnr. DEV-345 · README §8.
* **Testbench nấc 3c của Bài 3 không dịch nổi từ 02/10/2026** — `tb_pcpi_vmini.v` tạo thực thể
  `bram` với năm cổng `b_*` của **bản hai cổng**, mà `rtl/bram.v` đã đưa về một cổng (có lý do
  ghi sẵn trong tệp: bản hai cổng làm suy luận BSRAM đứt). `bai3/NGOAI-PHAM-VI.md` vẫn ghi
  “độ nhạy 7/7” — con số ấy đúng lúc được viết và hết hiệu lực từ hôm `bram.v` đổi. Bài 3 đã
  ở ngoài đường dựng nên **chưa sửa**. DEV-344.
* **Lỗi `_go_dau` trong `src/eide/tools/design.py`** — viết `.replace("d", "d")` nên
  `"ổn định"` và `"ON DINH"` không khớp nhau; hàm ấy đang dùng cho một phép kiểm an toàn
  (*người có thật sự chọn không*). Tìm thấy ở M2-03, **chưa sửa** vì ngoài phạm vi.
* **Cột “Mã nguồn” của ma trận truy vết trống ở mọi dự án** — nó đọc `hien_thuc_req`, trường
  vừa mới tồn tại nên chưa dự án nào có.
* **`req-critic`** (bước 4 của M2-03) — kế hoạch ghi “tuỳ chọn, gộp M2-13”. Chưa làm, đúng
  theo kế hoạch.
