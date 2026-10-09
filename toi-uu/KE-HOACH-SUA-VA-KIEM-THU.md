# KẾ HOẠCH SỬA VÀ KIỂM THỬ — TỐI ƯU TÁC TỬ (AGENT) EIDE v3

> **Dành cho Claude Code.** Tệp này là đặc tả triển khai cho 106 nhiệm vụ rút ra từ đợt rà soát ngày 06/10/2026
> (tệp Excel cùng thư mục: `EIDE_Toi_uu_Agent_2026-10-06.xlsx`). Mỗi nhiệm vụ có: mục tiêu, hiện trạng đã kiểm lại
> trong mã, các bước sửa, phạm vi cấm, **test case viết trước**, test bảo vệ hồi quy, tiêu chí xong và cách hoàn tác.
> Mục tiêu duy nhất: **sản phẩm chỉ tốt lên, không ca nào đang xanh bị đỏ, không hành vi nào đang đúng bị đổi ngoài ý muốn.**

**Trạng thái của các test case:** test case trong tệp được viết bằng cách đọc mã và test hiện có, **chưa chạy lần nào**
(môi trường soạn không chạy được `.venv` của máy). Vì vậy bước 3 của quy trình (mục 3) bắt buộc: viết test, chạy, xác nhận
ĐỎ đúng lý do. Nếu test xanh ngay trên mã cũ hoặc đỏ vì lý do khác (sai fixture, sai tên hàm) thì sửa test cho đúng
**ý định** ghi ở cột "Cho trước → Khi → Thì", rồi mới sửa mã sản phẩm.

---

## 1. Cách dùng tệp này

1. Đọc hết mục 1–4 một lần (khoảng 200 dòng) trước khi làm nhiệm vụ đầu tiên.
2. Mỗi lần làm, chọn nhiệm vụ đầu tiên chưa xong trong bảng **mục 5** (theo cột `#`), rồi mở chi tiết:
   `grep -n "TASK M1-01" toi-uu/KE-HOACH-SUA-VA-KIEM-THU.md` và đọc từ dòng đó tới dòng `<!-- TASK` kế tiếp.
3. **Một nhiệm vụ = một nhánh git = một hoặc vài commit nhỏ.** Không gộp hai nhiệm vụ vào một commit, trừ khi chi tiết
   nhiệm vụ ghi rõ "Gộp với … làm cùng đợt".
4. Hiện trạng trong từng nhiệm vụ ghi số dòng tại ngày 06/10/2026. **Luôn mở lại mã trước khi sửa**: số dòng có thể đã lệch;
   nếu mã đã khác hẳn mô tả (ai đó đã sửa) thì dừng nhiệm vụ đó, ghi lý do vào DEV-LOG và báo người dùng.
5. Gặp điều mơ hồ mà quyết định sai thì khó lùi (đổi lược đồ SQLite, đổi giao thức UI, đổi `policy.yaml`) → hỏi người dùng,
   không tự quyết.

## 2. Nguyên tắc bất biến — không làm hỏng sản phẩm

| # | Nguyên tắc | Vì sao |
|---|---|---|
| N-1 | **Đo mốc trước, so sau.** Không sửa dòng nào trước khi có mốc ở mục 3.0. | Không có mốc thì không chứng minh được "không tụt". |
| N-2 | **Test viết trước, phải ĐỎ trên mã cũ, đỏ đúng lý do.** | Test xanh trên mã cũ là test vô dụng (DEV-LOG đã ghi ba lần mắc). |
| N-3 | **"Phá lại thì đỏ"**: sửa xong, tạm hoàn nguyên đúng chỗ sửa, chạy test mới, xác nhận ĐỎ, rồi trả lại. | Chứng minh test canh đúng chỗ đã sửa, không canh chỗ khác. |
| N-4 | **Đổi hành vi tác tử → sau cờ `Features`, mặc định TẮT.** Đổi hành vi gồm: prompt/hiến pháp, danh sách công cụ hiển thị, temperature/thinking, định tuyến, hook mới chèn lời nhắc, vòng lặp tự gọi LLM thêm. | Hành vi mô hình chỉ đo được bằng eval; cờ cho phép bật/tắt mà không revert. |
| N-5 | **Sửa lỗi thuần không cần cờ** (ô xanh giả, đi vòng hàng rào, mất dữ liệu), nhưng bắt buộc có test hồi quy. | Lỗi thì phải hết, không để tuỳ chọn. |
| N-6 | **Không sửa ngoài "Tệp chạm tới"**, trừ khi bắt buộc; nếu phải sửa thêm, ghi rõ trong DEV-LOG. | Giữ diff nhỏ, dễ review, dễ revert. |
| N-7 | **Không đổi dữ liệu người dùng trên đĩa**: transcript cũ, `.eide/`, `du-lieu/`, EIDE.md của dự án thật. Chuẩn hoá thì làm lúc đọc. | Phiên cũ phải mở lại được. |
| N-8 | **Không đổi chữ ký công khai** (tên công cụ, tham số bắt buộc, mã lỗi đang có, dạng UICommand) trừ khi nhiệm vụ ghi rõ. Thêm tham số thì tuỳ chọn, có mặc định giữ hành vi cũ. | Mô hình và giao diện Swift đang dựa vào chúng. |
| N-9 | **Không nới luật an toàn**: `policy.yaml`, cổng G-*, constant_guard, kiểm `fs.write` đọc-trước-khi-đè chỉ được chặt hơn, không lỏng hơn. | An toàn là thứ không đánh đổi lấy tốc độ. |
| N-10 | **Phụ thuộc mới** (`pdfplumber`, `lizard`, embedding…) chỉ là tuỳ chọn: thiếu thì nói rõ và rơi về đường cũ, không lỗi cứng. Thêm vào `pyproject.toml` mục tuỳ chọn, hỏi người dùng trước khi cài. | Giữ nguyên quyết định "thiếu công cụ thì sản phẩm nói rõ". |
| N-11 | **Mã lỗi mới chỉ lấy từ bảng mục 6**; công cụ mới đăng ký `core=False`, mô tả ≤ 400 ký tự. | Tránh trùng mã; không làm phình lược đồ công cụ. |
| N-12 | **Chỉ một model** (`gemini-3.8-flash`, `config.ALLOWED_MODELS`). Mọi ý "model khác" đã đổi thành "cùng model, prompt/nhiệt độ/mức nghĩ khác". | Quyết định chủ sản phẩm 25/09/2026. |
| N-13 | **Ghi DEV-LOG** (`docs/md/EIDE-DEV-LOG.md`) một mục mỗi nhiệm vụ: đã đổi gì, số ca trước/sau, kết quả "phá lại thì đỏ", số đo nếu có. | Giữ thói quen ghi sổ của dự án. |

## 3. Quy trình cho MỖI nhiệm vụ

### 3.0. Đo mốc (làm một lần trước nhiệm vụ đầu tiên, và lại sau mỗi giai đoạn)

```bash
git status                                  # cây sạch, hoặc ghi rõ thay đổi đang có
git switch -c toi-uu/moc && git switch -    # đánh dấu điểm xuất phát
mkdir -p ket-qua-do/moc
.venv/bin/python -m pytest -q 2>&1 | tail -5 | tee ket-qua-do/moc/pytest.txt   # ghi số ca xanh/đỏ/bỏ qua
.venv/bin/python tools/kiem_tai_lieu.py   | tee ket-qua-do/moc/kiem_tai_lieu.txt
.venv/bin/python tools/kiem_tra_day_du.py --nhanh | tee ket-qua-do/moc/day_du.txt
(cd ui/EIDEApp && swift test 2>&1 | tail -3) | tee ket-qua-do/moc/swift.txt
```

Nếu mốc đã có ca đỏ thì **ghi lại danh sách ca đỏ** (`pytest -q -rf`). Đó là "đỏ có sẵn", không được đổ cho nhiệm vụ sau,
và cũng không được tự ý sửa ngoài kế hoạch. `ket-qua-do/` đã nằm trong `.gitignore`.

Các bộ tốn tiền mô hình (`tools/chay_kich_ban.py --lan 5`, `tools/chay_usecase.py`, `tools/thu_giao_dien.py`) **không** chạy
mỗi nhiệm vụ. Chỉ chạy ở cổng bật cờ (4.3) và cuối mỗi giai đoạn, sau khi hỏi người dùng.

### 3.1. Mười bước cho một nhiệm vụ

1. `git switch -c toi-uu/<Mx-yy>` từ nhánh chính mới nhất.
2. Đọc chi tiết nhiệm vụ, mở lại mọi vị trí trong "Hiện trạng" để xác nhận còn đúng.
3. **Viết các test case** trong bảng của nhiệm vụ (đúng tên tệp/hàm nếu hợp lý). Chạy riêng → xác nhận **ĐỎ đúng lý do**.
   Ghi kết quả đỏ (tên ca + dòng assert) vào ghi chú tạm.
4. Nếu có cờ: thêm trường cờ vào `Features` + tên vào `ten_co()` trước, kèm ca "cờ TẮT thì hành vi y như cũ".
5. Sửa mã theo "Thay đổi cần làm", tôn trọng "Không được làm".
6. Chạy test mới → XANH.
7. **Phá lại thì đỏ** cho từng ca mới (git stash phần sửa sản phẩm, hoặc hoàn nguyên tay đúng dòng) → ĐỎ → trả lại.
8. Chạy "Bảo vệ hồi quy" của nhiệm vụ, rồi **toàn bộ** `pytest -q`. Số ca xanh phải ≥ mốc + số ca mới; không ca cũ nào chuyển đỏ.
   Nếu nhiệm vụ đụng tài liệu hoặc tên công cụ/mã lỗi: chạy thêm `tools/kiem_tai_lieu.py` (0 chỗ lệch). Đụng `ui/`: `swift test`.
9. Ghi DEV-LOG; tự soát diff (`git diff --stat`) chỉ chạm các tệp được phép.
10. Commit (thông điệp: `[Mx-yy] <tên nhiệm vụ>` + một dòng "trước X ca / sau Y ca"), đánh dấu ☑ ở bảng mục 5.

### 3.2. Khi gặp sự cố

- **Ca cũ chuyển đỏ** → dừng. Hoặc là test cũ đang khoá đúng hành vi sai (một số nhiệm vụ đã nói trước, ví dụ M4-09 sửa
  `test_da_goi_verifier_roi_thi_thoi`), khi đó sửa test cũ **và ghi lý do vào DEV-LOG**; hoặc là sửa đã làm hỏng thứ khác, khi đó
  sửa lại mã. Không bao giờ xoá hay `skip` một ca cũ để cho xanh.
- **Không viết được test đỏ** cho một lỗi được mô tả → lỗi có thể không còn (hoặc mô tả sai). Ghi "ĐÃ KIỂM LẠI: không tái hiện"
  vào DEV-LOG, đánh dấu nhiệm vụ "Không làm", sang nhiệm vụ kế.
- **Cần công cụ hệ thống chưa có** (iverilog, sby, cppcheck, clang/libFuzzer…) → test phần thuần Python bằng log mẫu/monkeypatch
  (mẫu `_lenh_gia`, `H._tim_lenh` trong tests/test_hdl.py), ca chạy công cụ thật đánh `skipif(not shutil.which(...))`.

## 4. Cổng chất lượng

### 4.1. Cổng gộp một nhiệm vụ (bắt buộc)

- [ ] Mọi TC của nhiệm vụ xanh và đã qua "phá lại thì đỏ".
- [ ] `pytest -q` toàn bộ: không ca cũ nào đỏ; tổng xanh ≥ mốc.
- [ ] `tools/kiem_tai_lieu.py` 0 chỗ lệch (nếu đụng tên công cụ, mã lỗi, đường dẫn trong tài liệu).
- [ ] Không chạm tệp ngoài phạm vi; không đổi dữ liệu người dùng; không nới luật an toàn.
- [ ] Hành vi tác tử đổi thì đã nằm sau cờ TẮT.
- [ ] DEV-LOG có mục mới.

### 4.2. Cổng cuối giai đoạn

- [ ] Chạy lại toàn bộ mục 3.0 và so với mốc: Python, Swift, `kiem_tra_day_du --nhanh`, `kiem_tai_lieu`.
- [ ] Chạy các bộ "đường hỏng cố ý" liên quan mảng đã sửa (`tools/thu_g3.py` … `tools/thu_g6.py`, `thu_ckm.py`, `thu_hier.py`,
      `EIDE_FEATURE_SCHEMATIC=1 tools/thu_sch.py`) → không tụt.
- [ ] Hỏi người dùng có chạy bộ tốn tiền (`chay_kich_ban.py --lan 5`, `chay_usecase.py`, `thu_giao_dien.py`) không; nếu chạy, so với
      kết quả cũ trong `docs/review-v3/test/` → pass-rate không giảm.

### 4.3. Cổng bật cờ (đổi mặc định một cờ từ TẮT sang BẬT)

Chỉ đổi mặc định khi **cả bốn** đúng, và đổi bằng một commit riêng (dễ revert):

1. Bộ eval phát lại (khi M4-21 xong) xanh với cờ BẬT.
2. Bộ kịch bản `tools/chay_kich_ban.py --bo tests/kich_ban/tc001_007.yaml --lan 5` và bộ 76 ca: pass-rate với cờ BẬT **≥** cờ TẮT
   (chạy cả hai chế độ bằng `EIDE_FEATURE_<TEN>=0/1`, so bằng `tools/so_ket_qua.py`).
3. Chỉ số chi phí (khi M1-20 xong): token đầu vào trung vị mỗi lượt không tăng quá 15 %, số lượt chạm trần 40 lời gọi không tăng.
4. Người dùng đồng ý.

## Mức độ ưu tiên và công sức

P0 = vá ngay (lỗi nền, đi vòng an toàn, ô xanh giả) · P1 = tăng rõ độ thông minh/độ phủ kiểm thử · P2 = nên làm · P3 = có thì tốt.
Công sức: S ≤ 2 ngày · M ≈ 3–7 ngày · L ≈ 2–4 tuần · XL > 1 tháng (một người quen mã). Giai đoạn 1 có 32 nhiệm vụ.

**Lời khuyên thứ tự:** làm sớm M1-20 (bảng chỉ số từ ledger) và M5-21/M4-20 (eval) dù không phải P0. Không có thước đo thì
mọi nhiệm vụ "đổi hành vi" sau này không qua được cổng 4.3.

## 5. Thứ tự triển khai (bảng điều khiển)

Làm theo đúng thứ tự `#`. Cột **Tiền đề** là phụ thuộc cứng; tiền đề nằm ở giai đoạn sau đã được **kéo lên** (ghi ở cột Ghi chú). Đánh dấu tiến độ bằng cách sửa ô Trạng thái trong tệp này hoặc trong sheet *Danh mục tối ưu* của tệp Excel cùng thư mục.


### Giai đoạn 1 — Làm ngay: vá lỗi nền và ô xanh giả (P0, công sức S/M)

| # | Mã | Nhiệm vụ | Ưu tiên | Công sức | Tiền đề | Cờ tính năng | Ghi chú | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| 1 | [M1-01](#m1-01) | Bảo đảm toàn vẹn cặp function_call ↔ function_response | P0 | M | — | — | xong 06/10/2026 · DEV-330 · 1610→1615 ca | ☑ |
| 2 | [M1-02](#m1-02) | Đưa lược đồ công cụ hiển thị về trong ngân sách | P0 | M | — | GON_CONG_CU | xong 06/10/2026 · DEV-331 · 25 869→4 475 token · cờ vẫn TẮT | ☑ |
| 3 | [M1-03](#m1-03) | Tác tử con phải đi qua hook, policy và khoá plan mode | P0 | M | — | — | xong 06/10/2026 · DEV-332 · 1 822 lời gọi từng đi vòng | ☑ |
| 4 | [M2-01](#m2-01) | Truy vết khai báo: `deps.upstream` thật cho REQ → thiết kế → mã → test | P0 | M | — | TRUY_VET | xong 06/10/2026 · DEV-333 · STALE 9→3 | ☑ |
| 5 | [M2-02](#m2-02) | Khối "Ma trận truy vết" trên tab A2 và hook Stop "REQ chưa ai đo" | P0 | S | M2-01 | REQ_PHU | xong 07/10/2026 · DEV-334 · khối là A2.2 (A2.5 đã có chủ) | ☑ |
| 6 | [M2-03](#m2-03) | Kiểm chất lượng yêu cầu: tiêu chí đo được, từ mơ hồ, trùng lặp | P0 | M | — | REQ_CHAT_LUONG | xong 07/10/2026 · DEV-335 · req-critic chưa làm (chờ M2-13) | ☑ |
| 7 | [M2-06](#m2-06) | Bước kế hoạch có cổng kiểm (`kiem`) và mã REQ; `step_done` đối chiếu sổ cái | P0 | M | — | KE_HOACH_CONG_KIEM | xong 07/10/2026 · DEV-336 · sẽ chặn 19/26 lần trong phiên thật | ☑ |
| 8 | [M2-08](#m2-08) | `phan_tich_ma`: nhận ISR/handler và không nuốt hàm kế tiếp | P0 | S | — | — | xong 07/10/2026 · DEV-337 · +28 hàm trước đây vô hình | ☑ |
| 9 | [M3-01](#m3-01) | ERC luật quá áp trên net (5 V vào chân 3,3 V) | P0 | S | — | — | xong 07/10/2026 · DEV-338 · chưa nổ trên dữ liệu thật tới khi M3-07 xong | ☑ |
| 10 | [M3-03](#m3-03) | ERC theo kiểu chân (ma trận điện thay KiCad ERC) | P0 | M | — | — | xong 07/10/2026 · DEV-339 · 8 phát hiện trên 5 mạch thật | ☑ |
| 11 | [M3-04](#m3-04) | ERC tranh chấp nguồn và ngắn mạch rail–GND | P0 | S | — | — | xong 07/10/2026 · DEV-340 · 0 trên mạch thật, đã cấy lỗi để chứng minh luật sống | ☑ |
| 12 | [M3-07](#m3-07) | Nối Fact datasheet ↔ khoá/chủ thể ERC, và báo độ phủ ERC | P0 | S | — | — | xong 07/10/2026 · DEV-341 · Fact tới được ERC 5→17 | ☑ |
| 13 | [M3-10](#m3-10) | Vòng sinh → ERC → sửa có trần cho bản đồ mạch (hook `erc_delta`) | P0 | M | M3-03, M3-04, M3-07 | ERC_TU_DONG | xong 07/10/2026 · DEV-342 · ERC 7,6 ms trên mạch 187 nút | ☑ |
| 14 | [M3-12](#m3-12) | Mô phỏng HDL: đọc PASS/FAIL chặt, chỉ từ log chạy, tính cả mã thoát và `$fatal` | P0 | S | — | — | xong 07/10/2026 · DEV-343 · regex kế hoạch từ chối oan 588/846, đã nới | ☑ |
| 15 | [M3-13](#m3-13) | `hdl.sensitivity`: đo độ nhạy testbench Verilog bằng đột biến thật | P0 | M | M3-12 | — | xong 08/10/2026 · DEV-344 · 1732→1744 ca · đo thật: `tb_pcpi_dot4` 1/1, `tb_pcpi_mac` 1/1, `tb_pcpi_vmini` không dịch nổi từ 02/10 | ☑ |
| 16 | [M3-18](#m3-18) | Kiểm ràng buộc chân FPGA (`.cst`) với cổng mô-đun đỉnh và chân của kit | P0 | M | — | — | xong 08/10/2026 · DEV-345 · 1744→1773 ca · trên 6 cặp thật: 1 chỗ CHẶN (`blinky` của riscv-tn20k-b dựng bitstream với chân đồng hồ nextpnr tự chọn) | ☑ |
| 17 | [M4-01](#m4-01) | Máy chấm unit test do EIDE phán (`test.criteria`) | P0 | M | — | — | xong 08/10/2026 · DEV-346 · 1773→1791 ca · phá lại 24/24 (lượt đầu 17/24) · thêm E4023 cho đường unit test, và chế độ phải hiện ở tab A8 chứ không chỉ ở note_vi | ☑ |
| 18 | [M4-02](#m4-02) | Cổng G-QUAL khi sửa/xoá tệp test sau kết quả đỏ + sửa `criteria.has_result` | P0 | M | — | SIM_RUNNER_GIOI_HAN — TẮT | xong 08/10/2026 · DEV-347 · 1791→1816 ca · phá lại 27/27 (lượt đầu 22/27) · phát hiện: một luật trỏ tới nhóm dữ kiện chưa khai thì DỪNG CẢ LƯỢT, và `criteria` cũng chưa bao giờ có trong danh sách ấy | ☑ |
| 19 | [M4-05](#m4-05) | Đột biến không biên dịch được không được tính là "bắt được" | P1 | S | — | — | xong 08/10/2026 · DEV-348 · 1816→1835 ca · phá lại 22/22 (lượt đầu 15/20) · tìm thêm BA lỗi thật trên cùng đường đo: test.sensitivity ĐỔ trên mọi tệp firmware thật (≥10 chú thích), mo_phong chạy lại sim.vvp cũ khi biên dịch đổ, và loi_nguoi_doc khen khi chưa đo được gì | ☑ |
| 20 | [M4-19](#m4-19) | Đột biến trên bản sao, không ghi đè tệp sản phẩm của người dùng | P2 | S | — | — | xong 08/10/2026 · DEV-349 · 1835→1846 ca · phá lại 13/13 (lượt đầu 7/13) · đo trên 3 dự án thật TẠI CHỖ: 50/50 tệp firmware giữ nguyên sha256 VÀ mtime, kết luận giống hệt lượt đột biến tại chỗ của M4-05 | ☑ |
| 21 | [M4-04](#m4-04) | Đột biến chi tiết từng vị trí + điểm đột biến (mutation score) | P1 | M | M4-05, M4-19 | — | xong 09/10/2026 · DEV-350 · 1846→1862 ca · phá lại 22/22 (lượt đầu 15/22) · TÁI HIỆN được ca DANH-GIA §2.2 bằng máy (0xFFFFFFFD dòng 147 → mutant SỐNG) · phép đo mới TREO 10 phút trên tệp thật đầu tiên, đã sửa | ☑ |
| 22 | [M4-06](#m4-06) | Vòng tự nâng test khi đột biến sống (Evaluator–Optimizer) | P0 | M | M4-04, M4-05 | TEST_HARDEN — TẮT | xong 09/10/2026 · DEV-351 · 1862→1878 ca · phá lại 22/22 (lượt đầu 18/22) · **một tiêu chí CHƯA đạt**: "mutation score tăng sau harden" cần lời gọi mô hình (§3.0 bắt hỏi trước), và dự án mẫu không có chỗ để đo | ☑ |
| 23 | [M4-07](#m4-07) | Verifier nhận gói bằng chứng do EIDE dựng từ sổ cái, không nhận đề bài tác tử chính tự viết | P0 | M | — | VERIFIER_GOI_BANG_CHUNG | DEV-352 · một tiêu chí còn mở (cần M4-22) | ☑ |
| 24 | [M4-09](#m4-09) | Stop hook không được coi `task.run` với subagent khác là "đã kiểm chứng" | P0 | S | — | — | DEV-353 | ☑ |
| 25 | [M4-11](#m4-11) | Hồi quy tự động sau khi sửa mã + STALE chính xác theo tệp | P0 | M | M2-01 | HOI_QUY_NEN | DEV-354 | ☑ |
| 26 | [M2-09](#m2-09) | Phân tích tĩnh chiều sâu: call graph, ngăn xếp, luật ngữ cảnh ISR (`code.static`) | P1 | L | M2-08 | — | kéo lên từ GĐ3 vì là tiền đề của M4-13 | ☐ |
| 27 | [M4-13](#m4-13) | Kiểm "nối" tĩnh sau biên dịch (vector table, hàm không ai gọi, return hằng) | P0 | M | M2-09 | KIEM_NOI |  | ☐ |
| 28 | [M5-03](#m5-03) | Bộ đọc SVD: nạp register map thành Fact `reg:`/`field:` + `reg.lookup` | P0 | M | — | — | DEV-355 | ☑ |
| 29 | [M5-05](#m5-05) | Kiểm thứ nguyên đơn vị + thống nhất khoá khoảng hợp lý + kiểm cả đường bảng | P0 | S | — | — | DEV-356 | ☑ |
| 30 | [M5-07](#m5-07) | `fact.from_doc`: kiểm giá trị theo ranh giới token và câu trích nguyên văn | P0 | S | — | — |  | ☐ |
| 31 | [M5-13](#m5-13) | Chính sách phong bì cho `doc.read`/`fact.query`/`fact.extract`; sửa `_cat_chung` cắt phần tử dài | P0 | S | — | — |  | ☐ |
| 32 | [M5-17](#m5-17) | Resume nạp lại bản tóm tắt C2 từ sổ cái; tường thuật cơ học phiên trước | P0 | S | — | RESUME_TUONG_THUAT |  | ☐ |

### Giai đoạn 2 — Ngắn hạn: P0 công sức lớn và P1 công sức nhỏ

| # | Mã | Nhiệm vụ | Ưu tiên | Công sức | Tiền đề | Cờ tính năng | Ghi chú | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| 33 | [M5-01](#m5-01) | Chỉ mục tìm kiếm tài liệu BM25 (FTS5) lưu bền + công cụ `doc.search` | P0 | L | — | DOC_EMBED |  | ☐ |
| 34 | [M5-04](#m5-04) | Trích bảng có cấu trúc từ PDF datasheet (hàng bảng + ngữ cảnh mục) | P0 | L | M5-05 | PDF_BANG |  | ☐ |
| 35 | [M1-05](#m1-05) | Ngân sách, cắt kết quả và lượt buộc nộp cho tác tử con | P1 | M | M1-03 | SUBAGENT_NOP | kéo lên từ GĐ3 vì là tiền đề của M1-07 | ☐ |
| 36 | [M1-06](#m1-06) | Thi hành tính độc lập của verifier | P1 | S | — | — |  | ☐ |
| 37 | [M1-07](#m1-07) | Báo cáo subagent nộp bằng lời gọi công cụ có lược đồ | P1 | S | M1-05 | BAO_CAO_CONG_CU |  | ☐ |
| 38 | [M1-08](#m1-08) | Định tuyến mức suy nghĩ và chế độ gọi công cụ theo loại bước | P1 | S | — | DINH_TUYEN_NGHI |  | ☐ |
| 39 | [M1-20](#m1-20) | Bảng chỉ số lượt/phiên từ ledger và cổng hồi quy | P1 | M | — | — | kéo lên từ GĐ3 vì là tiền đề của M1-09 | ☐ |
| 40 | [M1-09](#m1-09) | Thí nghiệm A/B nhiệt độ cho Gemini 3.x | P1 | S | M1-20 | NHIET_MAC_DINH_1 |  | ☐ |
| 41 | [M1-10](#m1-10) | Xử lý finish_reason và chống lặp chữ khi retry | P1 | S | M1-08 | XU_LY_KET_THUC |  | ☐ |
| 42 | [M1-11](#m1-11) | Trần token mỗi lượt và cửa sổ làm việc thực | P1 | S | — | TRAN_TOKEN |  | ☐ |
| 43 | [M1-15](#m1-15) | Lõi tự chạy verifier khi trả lượt có việc chưa kiểm | P1 | S | M1-03, M1-06 | TU_KIEM_BANG_MA |  | ☐ |
| 44 | [M1-17](#m1-17) | Chống lời gọi trùng y hệt và leo thang khi quay vòng | P1 | S | M1-08 | CHONG_LAP |  | ☐ |
| 45 | [M2-05](#m2-05) | `option_create` nói ra REQ lạ và REQ chưa xét | P1 | S | — | — |  | ☐ |
| 46 | [M2-11](#m2-11) | `code.analyze`: loại thư mục thư viện, một lượt regex mỗi tệp, có trần | P1 | S | — | — |  | ☐ |
| 47 | [M2-13](#m2-13) | Subagent `sw-design-review` và checklist rà thiết kế phần mềm trước G-DESIGN | P1 | S | — | RA_SOAT_PHAN_MEM |  | ☐ |
| 48 | [M2-14](#m2-14) | Subagent `firmware`: "xong" phải gồm test, có vòng tự sửa có trần | P1 | S | M1-03 | FIRMWARE_KIEM |  | ☐ |
| 49 | [M3-02](#m3-02) | ERC mức logic hai chiều (VOL ≤ VIL) và VIH dạng tỉ lệ ×VDD | P1 | S | M3-01 | — |  | ☐ |
| 50 | [M3-06](#m3-06) | Pull-up I2C: không đếm điện trở nối tiếp, kiểm Rmin/Rmax | P1 | S | M3-01 | — |  | ☐ |
| 51 | [M4-17](#m4-17) | Đo được độ phủ C trên macOS (xcrun llvm-cov), có gcov, có dòng chưa phủ | P1 | S | — | — |  | ☐ |
| 52 | [M4-18](#m4-18) | Mở khoá công cụ kiểm thử theo giai đoạn | P1 | S | — | MO_KHOA_KIEM_THU |  | ☐ |
| 53 | [M5-10](#m5-10) | Tra Fact theo id chính xác; `fact.query` trả tổng thật và sắp theo tầng | P1 | S | — | — |  | ☐ |
| 54 | [M5-16](#m5-16) | `EideMd.render` giữ §Đừng/§Người vừa sửa/§Quyết định khi vượt ngân sách | P1 | S | — | — |  | ☐ |

### Giai đoạn 3 — Trung hạn: P1 công sức M/L

| # | Mã | Nhiệm vụ | Ưu tiên | Công sức | Tiền đề | Cờ tính năng | Ghi chú | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| 55 | [M1-04](#m1-04) | Chạy song song các lời gọi chỉ-đọc trong cùng một batch | P1 | M | M1-01, M1-03 | SONG_SONG_DOC |  | ☐ |
| 56 | [M1-12](#m1-12) | Chỉ gửi khối nhắc của lượt mới nhất và giữ prefix ổn định cho cache | P1 | M | — | NHAC_MOT_BAN |  | ☐ |
| 57 | [M1-13](#m1-13) | Replanner: `plan.revise`, tiêu chí xong và phụ thuộc giữa các bước | P1 | L | — | REPLAN |  | ☐ |
| 58 | [M1-14](#m1-14) | Reflexion: chưng cất bài học từ thất bại vào EIDE.md | P1 | M | — | BAI_HOC |  | ☐ |
| 59 | [M2-04](#m2-04) | Phương án kiến trúc có rubric và điểm; công cụ `design.explore` (ToT + phản biện) | P1 | M | — | — |  | ☐ |
| 60 | [M2-10](#m2-10) | REQ ràng buộc (CR) có luật máy; kiểm ngay khi ghi tệp `.c` | P1 | M | M2-09 | LUAT_RANG_BUOC |  | ☐ |
| 61 | [M2-15](#m2-15) | `doc.check_sync`: kiểm tài liệu của DỰ ÁN NGƯỜI DÙNG còn khớp mã và Fact | P1 | M | M2-01 | — |  | ☐ |
| 62 | [M2-18](#m2-18) | Bộ chấm định lượng chất lượng phân tích–thiết kế trên KHO hiện vật | P1 | M | — | — |  | ☐ |
| 63 | [M3-08](#m3-08) | Tính toán kỹ thuật bằng mã: mở rộng `CONG_THUC` + công cụ `calc.eval` | P1 | M | — | — |  | ☐ |
| 64 | [M3-05](#m3-05) | Luật miền: decoupling, boot/reset, LED hạn dòng, nhiệt LDO | P1 | M | M3-01, M3-08 | ERC_LUAT_MIEN |  | ☐ |
| 65 | [M3-09](#m3-09) | Trích datasheet dự phòng bằng LLM có kiểm bám nguyên văn + `part.select` | P1 | L | M3-07 | DATASHEET_LLM |  | ☐ |
| 66 | [M3-14](#m3-14) | Đối chiếu số bằng mã (`hdl.compare`) và khung testbench tự kiểm (`hdl.tb_scaffold`) | P1 | L | M3-12, M3-08 | — |  | ☐ |
| 67 | [M3-15](#m3-15) | Kiểm hình thức bằng SymbiYosys (`hdl.formal`) và bật `--assert` cho Verilator | P1 | M | — | — |  | ☐ |
| 68 | [M3-20](#m3-20) | `hdl.flow`: luồng lint → sim → độ nhạy → kiểm chân → synth → pnr → bitstream có cổng bằng mã | P1 | M | M3-12, M3-13, M3-18 | — |  | ☐ |
| 69 | [M4-03](#m4-03) | Công cụ sinh test biên / fuzz / property (`test.generate`) | P1 | L | M4-01, M4-17 | — |  | ☐ |
| 70 | [M4-08](#m4-08) | Verifier chạy lại phép đo và soi STALE (cùng model, cấu hình riêng) | P1 | M | M4-07 | VERIFIER_CHAY_LAI |  | ☐ |
| 71 | [M4-10](#m4-10) | Verifier bác thì có vòng sửa có trần (Evaluator–Optimizer + bài học) | P1 | M | M4-09 | SUA_SAU_KIEM |  | ☐ |
| 72 | [M4-12](#m4-12) | Kiểm tiêu chí có khả năng ĐỎ (`sim.criteria_check`) | P1 | M | M4-04, M4-19 | — |  | ☐ |
| 73 | [M4-14](#m4-14) | HIL có tiêu chí và máy chấm log UART (`hil.criteria` + `hil.run`) | P1 | L | M4-01 | — |  | ☐ |
| 74 | [M4-16](#m4-16) | HDL: khớp PASS/FAIL chặt, độ nhạy do EIDE đo, coverage Verilator | P1 | M | — | — |  | ☐ |
| 75 | [M4-20](#m4-20) | Chấm eval theo chủ đề và theo hiện vật, chạy k lần cho ca kỹ thuật | P1 | M | — | — |  | ☐ |
| 76 | [M4-21](#m4-21) | Theo dõi eval qua phiên bản + băng phát lại 0 token + CI | P1 | M | M4-20 | — |  | ☐ |
| 77 | [M5-02](#m5-02) | Vòng Agentic RAG `kb.ask` + kiểm câu trả lời bám trích dẫn bằng mã | P1 | M | M5-01 | AGENTIC_RAG |  | ☐ |
| 78 | [M5-06](#m5-06) | Chuẩn hoá giá trị tương đối theo nguồn ("0.7 × VDD", "VDD + 0.3") | P1 | M | M5-05, M5-04, M5-04 | — |  | ☐ |
| 79 | [M5-08](#m5-08) | Vòng đời phiên bản Fact: thay thế khi nạp bản tài liệu mới + `fact.supersede` | P1 | M | M5-10 | — |  | ☐ |
| 80 | [M5-09](#m5-09) | Luật so sánh kiểm thứ nguyên + điều kiện; đối chiếu chéo theo điều kiện | P1 | M | M5-05 | — |  | ☐ |
| 81 | [M5-11](#m5-11) | Mở rộng CKM: ngoại vi–thanh ghi–AF–clock + truy vấn đường đi `ckm.path` | P1 | L | M5-03, M5-04 | — |  | ☐ |
| 82 | [M5-14](#m5-14) | Bộ nhớ bài học kỹ thuật (lesson) có bằng chứng, hết hạn, tra theo mã lỗi | P1 | M | — | BAI_HOC |  | ☐ |
| 83 | [M5-18](#m5-18) | Phiếu kiểm C2 không lộ đáp án; sinh câu hỏi từ đoạn bị nén; đo tỉ lệ phủ | P1 | M | — | NEN_KIEM_PHU |  | ☐ |
| 84 | [M5-19](#m5-19) | Lược đồ tóm tắt C2 thêm `rang_buoc`/`so_lieu_then_chot`; kiểm trần bằng mã; PreCompact chèn mã còn thiếu | P1 | M | M5-18 | NEN_RANG_BUOC |  | ☐ |
| 85 | [M5-21](#m5-21) | Bộ eval vàng cho trích xuất, tìm kiếm, nén và resume | P1 | M | — | — |  | ☐ |

### Giai đoạn 4 — Có thì tốt: P2/P3

| # | Mã | Nhiệm vụ | Ưu tiên | Công sức | Tiền đề | Cờ tính năng | Ghi chú | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| 86 | [M1-16](#m1-16) | Phản biện tự động cho quyết định kiến trúc (option/ADR) | P2 | M | M1-03, M1-07 | PHAN_BIEN |  | ☐ |
| 87 | [M1-18](#m1-18) | tool.search chuẩn hoá dấu tiếng Việt và chỉ mở khoá công cụ đủ điểm | P2 | S | — | TIM_CONG_CU_GON |  | ☐ |
| 88 | [M1-19](#m1-19) | Kiểm kiểu, enum và lược đồ lồng nhau cho tham số công cụ | P2 | S | — | — |  | ☐ |
| 89 | [M1-21](#m1-21) | Công cụ phân tích Python dùng một lần trong sandbox chỉ-đọc | P2 | L | M1-03 | PY_PHAN_TICH |  | ☐ |
| 90 | [M1-22](#m1-22) | Lỗi điều kiện policy không được làm sập cả lượt | P2 | S | M1-01 | — |  | ☐ |
| 91 | [M2-07](#m2-07) | Bước thất bại và `plan.revise` (Replanner) có trần | P2 | M | M2-06 | — |  | ☐ |
| 92 | [M2-12](#m2-12) | Sơ đồ mô-đun: khớp include theo đường dẫn, kiểm phân tầng | P2 | M | M2-06 | — |  | ☐ |
| 93 | [M2-17](#m2-17) | CodeAct chỉ-đọc: công cụ `analysis.py` chạy Python trong tiến trình con có giới hạn | P2 | M | — | — |  | ☐ |
| 94 | [M2-19](#m2-19) | REQ: kiểm câu trích có trong sổ cái và bám nguồn (cảnh báo, hạ tầng tin cậy) | P2 | S | — | REQ_BAM_NGUON |  | ☐ |
| 95 | [M3-11](#m3-11) | Footprint trong netlist và đối chiếu footprint BOM ↔ sơ đồ | P2 | M | — | — |  | ☐ |
| 96 | [M3-16](#m3-16) | Tách tệp RTL/testbench khi lint và synth; chặn latch và đa nguồn lái | P2 | S | — | — |  | ☐ |
| 97 | [M3-17](#m3-17) | Định thời: đích theo từng đồng hồ và báo cáo đường găng | P2 | M | — | — |  | ☐ |
| 98 | [M3-19](#m3-19) | Bản đồ địa chỉ dùng chung RTL ↔ linker ↔ firmware | P2 | M | — | — |  | ☐ |
| 99 | [M3-21](#m3-21) | HDL: trả lỗi gốc kèm mã nguồn, và bài học theo chữ ký lỗi (Reflexion) | P2 | M | — | BAI_HOC_HDL |  | ☐ |
| 100 | [M4-15](#m4-15) | Đo đại lượng thời gian thực trên bo và đối chiếu với mô phỏng (`target.measure`) | P2 | M | M4-14 | — |  | ☐ |
| 101 | [M4-22](#m4-22) | Bộ ca gài lỗi để đo verifier và năng lực tự kiểm | P2 | L | M4-21, M4-09 | — |  | ☐ |
| 102 | [M5-12](#m5-12) | Nạp PDF scan/lai bằng OCR từng trang (`doc.load ocr=true`) | P2 | M | — | OCR_NAP |  | ☐ |
| 103 | [M5-15](#m5-15) | EIDE.md: dấu ngày, điều kiện huỷ cho Giả định, gợi ý trùng/mâu thuẫn khi ghi | P2 | M | — | EIDE_MD_KIEM |  | ☐ |
| 104 | [M5-20](#m5-20) | C1 stub theo lần "được nhắc" gần nhất; gộp trùng cho `doc.read`/`store.get`/`fact.query` | P2 | S | — | C1_THEO_NHAC |  | ☐ |
| 105 | [M2-16](#m2-16) | Bộ vẽ hỗ trợ `stateDiagram-v2` và kiểm máy trạng thái | P3 | M | — | — |  | ☐ |
| 106 | [M3-22](#m3-22) | Khép vòng số đo mạch thật với ERC (dòng đo so với ngân sách) | P3 | S | M3-07 | — |  | ☐ |

## 6. Mã lỗi mới — bảng cấp phát duy nhất

Các mã dưới đây CHƯA tồn tại trong `src/eide` (đã grep ngày 06/10/2026). Mỗi mã chỉ thuộc một nhiệm vụ; mã trùng giữa các mảng đã được cấp lại (E5012, E5013, E5014, E6012, E4034). Trước khi thêm một mã, chạy `grep -rn '"<MÃ>"' src/eide` để chắc chưa ai dùng; nếu đã có (do nhiệm vụ khác làm trước) thì lấy mã trống kế tiếp CÙNG nhóm và sửa lại bảng này.

| Mã | Nhiệm vụ | Nhóm |
|---|---|---|
| E2007 | M5-03 | tri thức/Fact |
| E2008 | M5-07 | tri thức/Fact |
| E2009 | M5-08 | tri thức/Fact |
| E4024 | M4-01 | cổng/kiểm/sandbox |
| E4025 | M4-03 | cổng/kiểm/sandbox |
| E4026 | M4-15 | cổng/kiểm/sandbox |
| E4031 | M1-01 | cổng/kiểm/sandbox |
| E4032 | M1-03 | cổng/kiểm/sandbox |
| E4033 | M1-22 | cổng/kiểm/sandbox |
| E4034 | M2-17 | cổng/kiểm/sandbox |
| E5011 | M1-17 | tham số/dữ liệu |
| E5012 | M2-04 | tham số/dữ liệu |
| E5013 | M3-08 | tham số/dữ liệu |
| E6010 | M1-10 | vòng lặp/kế hoạch |
| E6011 | M2-07 | vòng lặp/kế hoạch |
| E6012 | M2-06 | vòng lặp/kế hoạch |

## 7. Cờ tính năng mới (mặc định TẮT)

Thêm trường `bool = False` vào `eide.config.Features` và thêm tên (chữ thường, bỏ tiền tố) vào `ten_co()`. Bật thử bằng biến môi trường `EIDE_FEATURE_<TEN>=1`. Chỉ đổi mặc định sang BẬT khi qua **cổng bật cờ** ở mục 4.3. Cờ dùng chung nhiều nhiệm vụ là cố ý.

| Cờ | Nhiệm vụ | Tên trường trong `Features` |
|---|---|---|
| `EIDE_FEATURE_AGENTIC_RAG` | M5-02 | `agentic_rag` |
| `EIDE_FEATURE_BAI_HOC` | M1-14, M5-14 | `bai_hoc` |
| `EIDE_FEATURE_BAI_HOC_HDL` | M3-21 | `bai_hoc_hdl` |
| `EIDE_FEATURE_BAO_CAO_CONG_CU` | M1-07 | `bao_cao_cong_cu` |
| `EIDE_FEATURE_C1_THEO_NHAC` | M5-20 | `c1_theo_nhac` |
| `EIDE_FEATURE_CHONG_LAP` | M1-17 | `chong_lap` |
| `EIDE_FEATURE_DATASHEET_LLM` | M3-09 | `datasheet_llm` |
| `EIDE_FEATURE_DINH_TUYEN_NGHI` | M1-08 | `dinh_tuyen_nghi` |
| `EIDE_FEATURE_DOC_EMBED` | M5-01 | `doc_embed` |
| `EIDE_FEATURE_EIDE_MD_KIEM` | M5-15 | `eide_md_kiem` |
| `EIDE_FEATURE_ERC_LUAT_MIEN` | M3-05 | `erc_luat_mien` |
| `EIDE_FEATURE_ERC_TU_DONG` | M3-10 | `erc_tu_dong` |
| `EIDE_FEATURE_FIRMWARE_KIEM` | M2-14 | `firmware_kiem` |
| `EIDE_FEATURE_GON_CONG_CU` | M1-02 | `gon_cong_cu` |
| `EIDE_FEATURE_HOI_QUY_NEN` | M4-11 | `hoi_quy_nen` |
| `EIDE_FEATURE_KE_HOACH_CONG_KIEM` | M2-06 | `ke_hoach_cong_kiem` |
| `EIDE_FEATURE_KIEM_NOI` | M4-13 | `kiem_noi` |
| `EIDE_FEATURE_LUAT_RANG_BUOC` | M2-10 | `luat_rang_buoc` |
| `EIDE_FEATURE_MO_KHOA_KIEM_THU` | M4-18 | `mo_khoa_kiem_thu` |
| `EIDE_FEATURE_NEN_KIEM_PHU` | M5-18 | `nen_kiem_phu` |
| `EIDE_FEATURE_NEN_RANG_BUOC` | M5-19 | `nen_rang_buoc` |
| `EIDE_FEATURE_NHAC_MOT_BAN` | M1-12 | `nhac_mot_ban` |
| `EIDE_FEATURE_NHIET_MAC_DINH_1` | M1-09 | `nhiet_mac_dinh_1` |
| `EIDE_FEATURE_OCR_NAP` | M5-12 | `ocr_nap` |
| `EIDE_FEATURE_PDF_BANG` | M5-04 | `pdf_bang` |
| `EIDE_FEATURE_PHAN_BIEN` | M1-16 | `phan_bien` |
| `EIDE_FEATURE_PY_PHAN_TICH` | M1-21 | `py_phan_tich` |
| `EIDE_FEATURE_RA_SOAT_PHAN_MEM` | M2-13 | `ra_soat_phan_mem` |
| `EIDE_FEATURE_REPLAN` | M1-13 | `replan` |
| `EIDE_FEATURE_REQ_BAM_NGUON` | M2-19 | `req_bam_nguon` |
| `EIDE_FEATURE_REQ_CHAT_LUONG` | M2-03 | `req_chat_luong` |
| `EIDE_FEATURE_REQ_PHU` | M2-02 | `req_phu` |
| `EIDE_FEATURE_RESUME_TUONG_THUAT` | M5-17 | `resume_tuong_thuat` |
| `EIDE_FEATURE_SIM_RUNNER_GIOI_HAN` | M4-02 | `sim_runner_gioi_han` |
| `EIDE_FEATURE_SONG_SONG_DOC` | M1-04 | `song_song_doc` |
| `EIDE_FEATURE_SUA_SAU_KIEM` | M4-10 | `sua_sau_kiem` |
| `EIDE_FEATURE_SUBAGENT_NOP` | M1-05 | `subagent_nop` |
| `EIDE_FEATURE_TEST_HARDEN` | M4-06 | `test_harden` |
| `EIDE_FEATURE_TIM_CONG_CU_GON` | M1-18 | `tim_cong_cu_gon` |
| `EIDE_FEATURE_TRAN_TOKEN` | M1-11 | `tran_token` |
| `EIDE_FEATURE_TRUY_VET` | M2-01 | `truy_vet` |
| `EIDE_FEATURE_TU_KIEM_BANG_MA` | M1-15 | `tu_kiem_bang_ma` |
| `EIDE_FEATURE_VERIFIER_CHAY_LAI` | M4-08 | `verifier_chay_lai` |
| `EIDE_FEATURE_VERIFIER_GOI_BANG_CHUNG` | M4-07 | `verifier_goi_bang_chung` |
| `EIDE_FEATURE_XU_LY_KET_THUC` | M1-10 | `xu_ly_ket_thuc` |

## 8. Ghi chú hạ tầng test theo mảng

Do người rà soát từng mảng ghi lại khi đọc mã; dùng để viết test đúng fixture. Câu nào nói về mã lỗi thì bảng ở mục 6 là bản chuẩn.

### 8.1. Mảng 1 — Lõi tác tử

Ghi chú chung cho mọi nhiệm vụ trong tệp này:
- Chạy test: `.venv/bin/python -m pytest -q` (testpaths=tests, pythonpath=src). Fixture có sẵn trong `tests/conftest.py`: `du_an`, `cfg`, `make_agent(script)`, `chay(act, script)`, `_nha_rieng` (tự động).
- `ScriptedGateway(script)` (src/eide/llm/offline.py): mỗi phần tử là Response, dict, hoặc hàm(messages)->Response. Muốn soi đúng thứ đã gửi cho mô hình thì dùng phần tử dạng hàm và chép `list(messages)` ra ngoài. `.calls` chỉ ghi tên tool và số message.
- Văn hoá "phá lại thì đỏ" bắt buộc với mọi TC mới.

### 8.2. Mảng 2 — Phân tích & thiết kế phần mềm

Nguồn: `m2.json` (19 phát hiện, theo thứ tự M2-01 … M2-19). Mọi tên hàm, tệp, dòng dưới đây
`"E[0-9]{4}"` trong src/eide) gồm E4001–E4023, E4030, E5001–E5010, E5999, E6001–E6009…; các

Cờ tính năng mới (thêm trường vào `eide.config.Features` và thêm tên vào `ten_co()`, mặc định
`False`): `truy_vet`, `req_phu`, `req_chat_luong`, `kham_pha_thiet_ke`, `ke_hoach_cong_kiem`,
`ke_hoach_sua`, `luat_rang_buoc`, `ra_soat_phan_mem`, `firmware_kiem`, `phan_tich_py`,
`req_bam_nguon`. Công cụ có cờ khai `feature="<ten>"` trên `ToolSpec`
(registry.py:65), y như `tools/sch.py` khai `feature="schematic"`. Test bật cờ bằng
`build_registry(Features(<ten>=True))` hoặc `monkeypatch.setenv("EIDE_FEATURE_<TEN>", "1")`
(mẫu: tests/test_sch0.py:84–128).

### 8.3. Mảng 3 — Mạch, ERC, HDL/FPGA

Ghi chú chung cho mọi nhiệm vụ trong tệp này:
- Gốc mã: `src/eide/`. Chạy test: `.venv/bin/python -m pytest -q` (pyproject: testpaths=tests, pythonpath=src).
- Dàn dựng ERC dùng sẵn trong `tests/test_erc.py`: các hàm `_nut`, `_port`, `_fact`, `_tim` và fixture `bo`. Fixture này dựng một bo có LDO U3 (Port lá `2` power_out), MCU U1, cảm biến U2 TMP102, điện trở kéo lên R1 chỉ nối chân `1` vào `net:/board/sense.SDA_I`, và net `net:/board.3V3` có `canonical.ap_danh_dinh = "3,3 V"`.
- Gọi công cụ trong test theo mẫu `test_board_check_noi_ro_CHUA_DU_DU_KIEN_khong_goi_la_dat`: dựng `TurnContext(...)` rồi gọi `a.registry.run(ten, kw, ctx)`. Gọi hook theo mẫu `a.hooks.post_tool_use(call, res, ctx)` / `a.hooks.stop(ctx)` (xem `loop.py:829`, `:881`, `:534`).
- Test HDL dùng các hằng `BLINKY`, `CST`, `TB_PASS`, `TB_FAIL`, `TB_IM_LANG`, các hàm `_du_an(tmp_path, **tep)`, `_lenh_gia(tmp_path, than)` và các dấu `can_iv` / `CO_YOSYS` / `CO_PNR` trong `tests/test_hdl.py`. Để giả công cụ thì monkeypatch `H._tim_lenh`.
- Thêm cờ tính năng: thêm trường vào `eide.config.Features` (config.py:297) và thêm tên vào `ten_co()` (config.py:334). Công cụ gắn cờ bằng `feature="<ten>"` khi đăng ký (registry.py:101 `_co_bat`). Hook đọc cờ qua `ctx.config.features.bat("<ten>")`.

### 8.4. Mảng 4 — Kiểm thử & kiểm chứng

Ghi chú chung cho mọi nhiệm vụ dưới đây:
- Gốc mã `EIDE_v3/`; chạy test bằng `.venv/bin/python -m pytest -q`. `tests/test_xay_dung.py` có `pytestmark = pytest.mark.nha_that` (dùng `$HOME` thật vì có chuỗi công cụ). Vì vậy test MỚI không cần toolchain nhúng nên đặt ở tệp mới (không có nha_that). Ca cần `cc` thì dùng `skipif(not shutil.which("cc") …)` như `co_cc` trong test_xay_dung.
- **ĐÃ KIỂM LẠI** — `config.ModelConfig` + `ALLOWED_MODELS = frozenset({"gemini-3.8-flash"})` (config.py:40, 186-219): chủ sản phẩm chốt 25/09/2026 chỉ dùng MỘT model, và `GeminiGateway.stream` gọi `assert_allowed` ở điểm gọi cuối. Mọi đề xuất "model khác" trong m4.json (M4-08, M4-12, M4-21) được hạ xuống "cùng model, prompt/nhiệt độ riêng". Tham số `model=`/`temperature=` của `stream()` có sẵn cả ở `ScriptedGateway`.

### 8.5. Mảng 5 — Tri thức, RAG & bộ nhớ

Nguồn: `m5.json` (21 phát hiện, M5-01…M5-21 theo đúng thứ tự trong tệp). Mã đã được đọc lại trên
`$HOME/mnt/EIDE_v3` ngày 06/10/2026. Các điều chỉnh sau khi kiểm lại được ghi rõ trong từng nhiệm vụ ở dòng
"ĐÃ KIỂM LẠI".

Quy ước chung cho mọi nhiệm vụ:
- Helper gọi công cụ trong test: dùng lại mẫu `_ctx(agent)` và `_ex()` trong `tests/test_doc_van_ban.py`
  (`agent.registry.run("doc.load", {...}, _ctx(agent))`).
- PDF thử: `tests/lam_pdf.py::lam_pdf(path, [[dòng,...], ...])` (không thêm phụ thuộc). Tài liệu dựng tay:
  `docs_mod.TaiLieu(doc_id=..., ten=..., duong_dan=..., hash="0"*64, so_trang=1, trang=[docs_mod.Trang(1, "...")])`.
  Mỗi nhiệm vụ dùng mã nào thì ghi ở đây để không trùng: M5-03 dùng E2007, M5-07 dùng E2008,
- Cờ mới thêm vào `eide/config.py::Features` (trường bool mặc định `False` + tên trong `ten_co()`).
  Công cụ chỉ chạy khi có cờ thì khai `feature="<ten>"` trong `@r.tool(...)` (xem `Registry.add`/`_co_bat`).
- Lược đồ SQLite: migration tiếp theo là **v5** (`store/db.py::MIGRATIONS`, hiện `SCHEMA_VERSION=4`). Nhiệm vụ nào
  cũng thêm bảng thì gộp chung vào v5 nếu làm cùng đợt, không thì v6. Mẫu test migration: `tests/test_sch0.py`.


## 9. Nhiệm vụ chi tiết (theo thứ tự triển khai)

Mỗi nhiệm vụ mở đầu bằng dòng `<!-- TASK Mx-yy -->` để tìm nhanh: `grep -n "TASK M3-12" toi-uu/KE-HOACH-SUA-VA-KIEM-THU.md`.


---

## Giai đoạn 1 — Làm ngay: vá lỗi nền và ô xanh giả (P0, công sức S/M)

<!-- TASK M1-01 -->
<a id="m1-01"></a>
### [M1-01] Bảo đảm toàn vẹn cặp function_call ↔ function_response — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #1

**Mục tiêu:** mọi lượt model có N lời gọi công cụ thì theo sau đúng N kết quả cùng id, liền nhau và không có message nào chen giữa, kể cả khi bật thẻ cổng giữa batch hay khi duyệt cổng.
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** Không. Phải xong trước M1-04.
**Tệp chạm tới:** src/eide/loop.py, src/eide/llm/gemini.py, tests/test_loop.py, tests/test_tu_phat_hien_sai.py, tests/test_gemini_lich_su.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- loop.py:695-699 — `for call in rsp.tool_calls: self._one_tool(...); if ctx.awaiting_human: return`. Lời gọi bật cổng thì các lời gọi sau nó trong cùng batch không có message `role=tool` nào.
- loop.py:900-913 — khi `khong_noi_gi` đúng, `self.messages.append({"role":"user","_he_thong":True,...nhac_nho})` chạy TRƯỚC `self.messages.append({"role":"tool",...})` của chính lời gọi đó.
- loop.py:1441-1446 (`_resolve_gate`) — thêm reminder user rồi `{"role":"tool","tool_call_id": call.get("id", gid)}`. Đây là kết quả THỨ HAI cho cùng call id, vì kết quả E4030/E4003 (`gate_pending`) đã nằm sẵn trong transcript.
- gemini.py:143-163 (`_to_contents`) — mỗi message tool thành một `types.Content(role="user")` riêng, dùng `Part.from_function_response(name=..., response=...)` không có `id`. Bản SDK 2.25.0 trong .venv có `types.FunctionResponse(id=..., name=..., response=...)`.

**Thay đổi cần làm:**
1. loop.py `_tool_loop`: khi `ctx.awaiting_human` bật ở lời gọi thứ k, với mỗi lời gọi k+1..n gọi `_tool_error(call, EideError("E4031", "Chưa chạy: lời gọi trước trong cùng lượt đang chờ người duyệt cổng.", hint_for_agent="Đợi người duyệt; đừng gọi lại.", blame="system"), ctx, as_incident=False)`.
2. loop.py `_one_tool`: gom lời nhắc `nhac_nho` vào danh sách tạm `ctx._nhac_sau_batch` và chỉ append chúng SAU KHI mọi kết quả của batch đã vào transcript (cùng chỗ đang append `_nhac_neu_dang_quay_vong`).
3. loop.py `_resolve_gate`: không thêm một message tool thứ hai. Tìm message tool cũ có `tool_call_id == call["id"]` và thay `result` bằng `res.to_model()` (thêm khoá `_da_duyet_sau: gid`), rồi gọi `self.transcript.thay_toan_bo(list(self.messages))`. Reminder "ĐÃ DUYỆT" giữ nguyên nội dung và đặt SAU kết quả.
4. gemini.py: thêm hàm thuần `_gom_ket_qua(messages) -> list[dict]` để gộp các message tool liền nhau thành một nhóm. `_to_contents` sinh MỘT `Content(role="user", parts=[Part(function_response=FunctionResponse(id=m["tool_call_id"], name=..., response=...)), ...])`. Message user chen giữa lượt model và nhóm kết quả thì dời xuống sau nhóm. Chỉ làm lúc dựng request, KHÔNG sửa transcript trên đĩa.

**Không được làm (giới hạn phạm vi):**
- Không đổi dạng message nội bộ (`role/tool_call_id/tool/result`) và không sửa transcript cũ đã lưu.
- Không đổi nội dung các lời nhắc hiện có (test_loop.py::test_duyet_cong_chan_loi_goi_thi_PHAI_noi_ra kiểm chữ).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-01-01 | Tích hợp (ScriptedGateway) | tests/test_loop.py::test_cong_giua_batch_van_tra_du_ket_qua | Response có 2 lời gọi `[ToolCall("c1","target.flash",{"explain":ex}), ToolCall("c2","fs.read",{"path":"main.c"})]` → `chay` → mỗi id c1 và c2 có đúng một message `role=tool`; c2 mang `code == "E4031"`. |
| TC-M1-01-02 | Tích hợp | tests/test_tu_phat_hien_sai.py::test_nhac_rong_KHONG_chen_giua_goi_va_ket_qua | Dùng `_agent_voi_cong_cu_rong` như ca `test_LOI_that_su_nhac...` → sau message model chứa c1, message kế tiếp là `role=tool` với `tool_call_id=="c1"`; lời nhắc "vừa trả về **thành công**" đứng sau nó. |
| TC-M1-01-03 | Tích hợp | tests/test_loop.py::test_duyet_cong_KHONG_sinh_ket_qua_thu_hai | Kịch bản như `test_duyet_cong_chan_loi_goi_thi_PHAI_noi_ra` → sau `decide approved` → đúng 1 message tool có `tool_call_id=="c1"` và `result` của nó không còn mã E4030/E4003. |
| TC-M1-01-04 | Đơn vị | tests/test_gemini_lich_su.py::test_gop_ket_qua_mot_content_co_id | `gw = GeminiGateway.__new__(GeminiGateway)`; messages: user, model(2 call c1,c2 + parts), tool c1, user(_he_thong), tool c2 → `gw._to_contents(msgs)` → contents[2] có 2 part function_response với id c1,c2; message user nằm ở contents[3]. |
| TC-M1-01-05 | Ca âm | tests/test_gemini_lich_su.py::test_lich_su_dung_san_khong_bi_doi | Lịch sử đã chuẩn (1 call, 1 kết quả, rồi user) → `_to_contents` → số Content và thứ tự vai trò y như trước. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_tu_phat_hien_sai.py tests/test_mem_b.py tests/test_mem_c.py tests/test_mo_lai_du_an.py`
- Thẻ cổng vẫn dừng lượt (I6); lời nhắc ĐÃ DUYỆT/TỪ CHỐI giữ nguyên chữ; phục hồi phiên đỏ (`_doc_phien_do`) vẫn đếm đúng lời gọi dở.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Thêm hàm kiểm bất biến `kiem_cap_goi_tra(messages)` dùng trong test và chạy được trên transcript thật để soát.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit; không có dữ liệu trên đĩa bị đổi dạng.

<!-- TASK M1-02 -->
<a id="m1-02"></a>
### [M1-02] Đưa lược đồ công cụ hiển thị về trong ngân sách — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #2

**Mục tiêu:** số token lược đồ công cụ gửi mỗi lời gọi được đo, có trần, và khi bật cờ thì giảm từ khoảng 26k xuống ≤ 6k token.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_GON_CONG_CU`, mặc định TẮT). Phần đo và ghi sổ là hạ tầng, chạy cả khi cờ tắt.
**Phụ thuộc:** Không. Liên quan M4-18, không viết lại phần trùng.
**Tệp chạm tới:** src/eide/config.py, src/eide/tools/registry.py, src/eide/loop.py, src/eide/context/assemble.py, tests/test_policy_tools.py, tests/test_gon_cong_cu.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- Đo bằng `build_registry()` (cờ schematic tắt): 118 công cụ, 73 `core=True`, `json.dumps(declarations)` ≈ 77.600 ký tự ≈ 26k token.
- ĐÃ KIỂM LẠI, chỉnh lại nhận định: phần dài KHÔNG nằm ở `summary_vi` (target.flash chỉ 194 ký tự) mà ở mô tả TRONG `params` (declaration của target.flash dài 2.937 ký tự, store.procedure_set 2.505, tool.propose 2.309).
- config.py:137 — `ContextBudget.tool_schema = 4000` không được đọc ở đâu (grep chỉ ra đúng một dòng).
- registry.py:139-144 — `visible()` = core hoặc `_unlocked`. `_unlocked` chỉ được `add` (registry.search, loop._mo_khoa_theo_ngu_canh, hooks.standard), không bao giờ gỡ.

**Thay đổi cần làm:**
1. registry.py: thêm `Registry.token_luoc_do() -> int` = `approx_tokens(json.dumps(self.declarations(), ensure_ascii=False))`.
2. loop.py `_tool_loop`: ghi `tool_schema_tokens` vào ledger `llm_call` (hạ tầng đo, luôn bật).
3. config.py `Features`: thêm `gon_cong_cu: bool = False` và tên vào `ten_co()`.
4. Khi cờ bật: (a) `ToolSpec.declaration()` cắt mô tả từng tham số còn ≤ 160 ký tự (giữ nguyên bản đầy đủ trong `spec.params` cho tool.search và lỗi); (b) `visible()` chỉ trả tập `CORE_GON` (khoảng 18 tên: fs.read/glob/grep/stat/write/edit, store.get/list, fact.query, inventory.get, ask_user, tool.search, plan.enter, memory.note, ledger.query, build.compile, task.run, skill.load) cộng `_unlocked`; (c) `_unlocked` theo LRU: công cụ không được gọi trong 3 lượt thì gỡ, trừ khi đang có kế hoạch nêu nó; (d) declarations sắp theo tên để prefix ổn định.
5. Vượt `context_budget.tool_schema` thì ghi `note` vào ledger (không chặn).

**Không được làm (giới hạn phạm vi):**
- Không đổi `ToolSpec.core` của từng công cụ trong các tệp tools/*.py; tập gọn chỉ áp khi cờ bật.
- Không đổi hợp đồng `registry.run` (mọi công cụ vẫn gọi được, kể cả khi đang ẩn: lỗi E5004 hiện có vẫn gợi ý tool.search).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-02-01 | Đơn vị | tests/test_gon_cong_cu.py::test_co_ham_do_token_luoc_do | `build_registry()` → `reg.token_luoc_do()` → trả int > 0 và bằng approx của declarations. |
| TC-M1-02-02 | Đơn vị (cờ BẬT) | tests/test_gon_cong_cu.py::test_bat_co_thi_luoc_do_duoi_6000 | monkeypatch `EIDE_FEATURE_GON_CONG_CU=1`, `build_registry(Features.load())` → `token_luoc_do() <= 6000` và các công cụ trong `CORE_GON` vẫn có mặt. |
| TC-M1-02-03 | Ca âm (cờ TẮT) | tests/test_gon_cong_cu.py::test_tat_co_thi_danh_sach_y_nhu_cu | Cờ tắt → tập tên `visible()` đúng bằng tập `core=True` hiện nay (73 tên, so với ảnh chụp lưu trong test). |
| TC-M1-02-04 | Tích hợp (ScriptedGateway) | tests/test_gon_cong_cu.py::test_ledger_ghi_token_luoc_do | Một lượt có 1 lời gọi → ledger `llm_call` có khoá `tool_schema_tokens`. |
| TC-M1-02-05 | Tích hợp (cờ BẬT) | tests/test_gon_cong_cu.py::test_lru_go_cong_cu_khong_dung | Mở khoá `ledger.verify` bằng search, chạy 3 lượt không gọi nó → lượt 4 không còn `ledger.verify` trong `agent.llm.calls[-1]["tools"]`. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_policy_tools.py tests/test_loop.py tests/test_ke_hoach.py tests/test_chia_viec_lon.py tests/test_nang_luc.py tests/test_duong_dan_toi_cong_cu.py`
- `test_tool_search_mo_khoa`, `test_moi_cong_cu_co_hop_dong_du` giữ nguyên; các ca "mở khoá plan.* / skill.load / task.run" vẫn đúng.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: token lược đồ / lời gọi ≤ 6k khi bật cờ; pass rate 76 TC (chay_usecase) không tụt thì mới đề nghị bật mặc định.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ `EIDE_FEATURE_GON_CONG_CU`; revert commit nếu cần gỡ phần đo.

<!-- TASK M1-03 -->
<a id="m1-03"></a>
### [M1-03] Tác tử con phải đi qua hook, policy và khoá plan mode — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #3

**Mục tiêu:** mọi lời gọi công cụ của subagent đi đúng chuỗi plan-lock → pre_tool_use → policy.decide → run → post_tool_use như tác tử chính.
**Loại:** Sửa lỗi thuần (đi vòng hàng rào)
**Phụ thuộc:** Không. Phải xong trước M2-14 và M1-05.
**Tệp chạm tới:** src/eide/loop.py, src/eide/subagent.py, tests/test_subagent.py

**Hiện trạng (đã kiểm lại trong mã):**
- subagent.py:292-316 (`chay`) — `r = registry.run(call.tool, call.args, ctx)`, không gọi `hooks.pre_tool_use`, `policy.decide`, `_khoa_khi_soan_ke_hoach` hay `hooks.post_tool_use`.
- subagent.py SUBAGENT["firmware"].cong_cu có fs.write, fs.edit, build.compile; "sim-runner" có fs.write, sim.criteria.
- policy.yaml có `POL-N1-constant-guard` (deny khi `constant_guard.unsourced > 0`), `POL-N8-explain`, `POL-MEM-eide-md-qua-tool`. Các luật này chỉ nổ khi đi qua `Agent._one_tool` (loop.py:812-917).
- hooks/standard.py `_DEFINE` bắt `#define X 1234`, nên `#define BAUD 115200` không có nguồn sẽ bị deny ở tác tử chính.

**Thay đổi cần làm:**
1. loop.py: tách phần kiểm từ `_one_tool` ra method `Agent.kiem_va_chay(call, ctx, *, che_do="chinh"|"con") -> tuple[ToolResult, dict|None]`, trả (kết quả, perm). Thứ tự giữ nguyên: `_khoa_khi_soan_ke_hoach` → `hooks.pre_tool_use` → `policy.decide` → `registry.run` → `hooks.post_tool_use`.
2. Khi `che_do="con"` và policy trả "ask": KHÔNG dựng thẻ, trả `EideError("E4032", "Thao tác cần người duyệt — tác tử con không được tự mở cổng.", hint_for_agent="Ghi việc này vào chua_lam rồi nộp báo cáo.", blame="agent")`.
3. subagent.chay: nếu `getattr(ctx, "agent", None)` có `kiem_va_chay` thì dùng nó; nếu không (ctx giả trong test cũ) thì giữ `registry.run` và ghi `ghi_so("subagent_tool", {..., "khong_qua_hang_rao": True})`.
4. `_one_tool` gọi lại `kiem_va_chay` để không có hai bản logic.

**Không được làm (giới hạn phạm vi):**
- Không đổi thứ tự ba lớp, không đổi chữ ký `subagent.chay(...)`.
- Không cho subagent dựng thẻ cổng hay đụng `pending_cards`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-03-01 | Tích hợp (ScriptedGateway) | tests/test_subagent.py::test_firmware_KHONG_ghi_duoc_hang_so_khong_nguon | Kịch bản: firmware gọi `fs.write {"path":"blink.c","content":"#define BAUD 115200\n","explain":_EX}`, rồi nộp `_bc(ket_luan="chua_du_du_kien", bang_chung=[])` → `SA.chay(..., ctx=_ctx(agent), ma="firmware")` → `blink.c` KHÔNG tồn tại; ledger có dòng hook policy với rule `POL-N1-constant-guard`. |
| TC-M1-03-02 | Tích hợp | tests/test_subagent.py::test_subagent_bi_khoa_khi_dang_soan_ke_hoach | Có `plan:current` ở trạng thái `dang_soan` (gọi `plan.enter` trước) → firmware gọi fs.write tệp mới → kết quả công cụ có code `E6005`, tệp không tồn tại. |
| TC-M1-03-03 | Tích hợp | tests/test_subagent.py::test_subagent_gap_cong_thi_E4032_khong_dung_the | Thêm tạm "target.flash" vào tập công cụ subagent "hardware" (monkeypatch `SA.SUBAGENT["hardware"].cong_cu`) → gọi target.flash → kết quả `E4032`, `agent.pending_cards` rỗng. |
| TC-M1-03-04 | Ca âm | tests/test_subagent.py::test_firmware_ghi_hop_le_van_ghi_duoc | fs.write `blink.c` nội dung không có hằng số (`int main(void){return 0;}`) → tệp được tạo, kết quả ok. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_loop.py tests/test_ke_hoach.py tests/test_policy_tools.py tests/test_tu_phat_hien_sai.py`
- `test_subagent_KHONG_dung_duoc_cong_cu_ngoai_tap_cua_no` vẫn trả E5006 trước mọi hook.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ledger: mọi `subagent_tool` có dòng `hook policy` đi kèm (soát bằng một phiên thật).
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M2-01 -->
<a id="m2-01"></a>
### [M2-01] Truy vết khai báo: `deps.upstream` thật cho REQ → thiết kế → mã → test — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #4

**Mục tiêu:** hiện vật khai mình dựng từ REQ nào thì STALE chỉ lan tới đúng nó, và có hàm dựng ma trận truy vết; hiện nay `deps.upstream` luôn rỗng nên đường khai báo không bao giờ chạy.
**Loại:** Phần nền là Sửa lỗi thuần. Phần mở tham số mới trên lược đồ công cụ là Đổi hành vi (cờ `EIDE_FEATURE_TRUY_VET`, mặc định TẮT).
**Phụ thuộc:** Không. Là tiền đề của M2-02, M2-15 và M4-11.
**Tệp chạm tới:** src/eide/history.py, src/eide/store/db.py, src/eide/deps.py, src/eide/tools/writing.py, src/eide/tools/design.py, src/eide/tools/xay_dung.py, src/eide/config.py, tests/test_truy_vet.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- deps.py:52–79 `ha_nguon_cua`: đọc `(a.get("deps") or {}).get("upstream")` rồi CỘNG thêm toàn bộ hiện vật cùng loại theo `HA_NGUON` (req → option, adr, block_diagram, code, criteria, findings, note).
- history.py:109 `ghi_kho(...)` không có tham số `deps`; history.py:142 `ghi_tep(...)` cũng không có. Cả hai gọi `self.store.apply(...)` mà không truyền `deps`.
- store/db.py:392 `apply(..., deps=None, ...)` ghi `"deps": deps or {}`, và câu upsert (db.py:424) có `deps=excluded.deps`. Nghĩa là MỖI lần ghi lại sẽ xoá deps cũ.
- Grep `deps=` trong src/eide: không có lời gọi nào ngoài db.py, nên upstream luôn rỗng.
- Hai chỗ đã sẵn liên kết REQ trong canonical nhưng chưa thành deps: tieu_chi.py:41 có `do_req` ở từng assert; design.py `option_create` có `dap_ung_req`.

**Thay đổi cần làm:**
1. `History.ghi_kho(..., deps: dict | None = None)` và `History.ghi_tep(..., deps: dict | None = None)` truyền thẳng xuống `store.apply`.
2. `Store.apply`: khi `deps is None` và hiện vật đã có thì GIỮ deps cũ (đọc từ hàng hiện có); chỉ ghi đè khi truyền dict, kể cả `{}`.
3. `deps.ha_nguon_cua`: hiện vật `a` khai `upstream` có ít nhất một id cùng LOẠI với `goc` (ví dụ có mã req) thì đường theo loại BỎ QUA `a`; `a` chỉ bị lan khi `goc["id"] in upstream`. Hiện vật không khai gì thì giữ nguyên đường theo loại.
4. Viết `deps.ma_tran_truy_vet(store) -> list[dict]`: mỗi REQ một dòng `{req, option:[], adr:[], code:[], criteria:[], ket_qua:[]}`, dựng từ `deps.upstream`, `option.canonical.dap_ung_req` và `criteria.canonical.assert[*].do_req`.
5. Tự ghi upstream, không cần cờ: `option_create` ghi `deps={"upstream": dap_ung_req}`; `sim.criteria` ghi upstream là tập `do_req` khác rỗng.
6. Sau cờ `truy_vet`: thêm tham số tuỳ chọn `hien_thuc_req: list[str]` vào lược đồ `fs.write` và `fs.edit`. Lược đồ chỉ có trường này khi cờ bật (dựng `params` theo `ctx`/features lúc đăng ký). Giá trị truyền xuống `ghi_tep(deps=...)`.

**Không được làm (giới hạn phạm vi):**
- Không bỏ đường lan theo loại: hiện vật không khai upstream vẫn lan như cũ.
- Không đổi chữ ký `danh_dau_stale`, không đổi bảng `HA_NGUON`, không viết migration lại dữ liệu cũ trên đĩa.
- Không đổi `KHONG_STALE`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-01-01 | Đơn vị | tests/test_truy_vet.py::test_ghi_kho_luu_deps_upstream | fixture `bo` (chép từ test_quy_trinh_lap_trinh.py) → `ag.history.ghi_kho(..., deps={"upstream":["FR-01"]})` → `ag.store.get(id)["deps"]["upstream"] == ["FR-01"]` (mã cũ: TypeError) |
| TC-M2-01-02 | Đơn vị | …::test_ghi_lai_khong_xoa_deps_cu | hiện vật có upstream → ghi_kho lần 2 không truyền deps → upstream vẫn còn |
| TC-M2-01-03 | Tích hợp | …::test_sua_FR02_khong_stale_tieu_chi_chi_do_FR01 | FR-01, FR-02 và `sim.criteria` có assert `do_req="FR-01"` → `store.req_update(FR-02)` → criteria KHÔNG có trong `stale_marked`; sửa FR-01 thì có |
| TC-M2-01-04 | Ca âm | …::test_tep_ma_khong_khai_REQ_van_stale_theo_loai | tệp code không khai upstream → sửa REQ → tệp vẫn STALE (giữ hành vi CX06) |
| TC-M2-01-05 | Đơn vị | …::test_ma_tran_truy_vet_tung_REQ | 2 REQ, 1 option `dap_ung_req=["FR-01"]` → `ma_tran_truy_vet` cho FR-01.option==["PA-A"], FR-02.option==[] |
| TC-M2-01-06 | Cờ TẮT | …::test_co_tat_luoc_do_fs_write_khong_co_hien_thuc_req | `build_registry(Features())` → `"hien_thuc_req" not in get("fs.write").params["properties"]` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_cx_cong_tac.py tests/test_ai_quyet.py tests/test_snapshot.py tests/test_xay_dung.py tests/test_quy_trinh_lap_trinh.py`
- CX06 (test_cx_cong_tac.py:76) phải vẫn ra STALE đúng `["drv_eth.c"]`; snapshot vẫn chép `deps` (snapshot.py:177).

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC (ví dụ bỏ bước 2 thì TC-02 đỏ, bỏ bước 3 thì TC-03 đỏ).
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Đo trên kịch bản 3 REQ + 3 tệp khai đúng: số hiện vật STALE khi sửa 1 REQ giảm từ "tất cả" xuống "đúng phần khai".
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit; riêng tham số lược đồ thì tắt cờ `truy_vet`.

<!-- TASK M2-02 -->
<a id="m2-02"></a>
### [M2-02] Khối "Ma trận truy vết" trên tab A2 và hook Stop "REQ chưa ai đo" — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #5

**Mục tiêu:** người dùng thấy ngay REQ nào chưa có thiết kế, mã hay test; và tác tử bị nhắc trước khi báo xong khi còn REQ mồ côi.
**Loại:** Khối giao diện là Sửa lỗi thuần (chỉ trình bày). Hook là Đổi hành vi (cờ `EIDE_FEATURE_REQ_PHU`, mặc định TẮT).
**Phụ thuộc:** M2-01 (cần `ma_tran_truy_vet`).
**Tệp chạm tới:** src/eide/surfaces.py, src/eide/hooks/standard.py, src/eide/config.py, tests/test_phan_tich_thiet_ke_len_tab.py, tests/test_req_phu.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- surfaces.py:129 `requirements(store, inv, ledger=None)` dựng các khối A2.1 (REQ), A2.3 (phương án), A2.4 (ADR). Không có khối gộp phủ yêu cầu.
- surfaces.py:1334: bảng tiêu chí đã hiện `"— chưa gắn REQ —"` cho từng assert, nhưng không có cái nhìn theo REQ.
- hooks/standard.py:557 `kiem_viec_chua_ai_kiem` đòi gọi verifier; verifier có `doc_duoc_viec=False` (subagent.py:150), tức không xét phủ yêu cầu. Hook này hoãn khi kế hoạch còn bước chưa xong (dùng `_ke_hoach_dang_chay`).

**Thay đổi cần làm:**
1. Thêm khối `block("A2.5", "Ma trận truy vết", "table", ...)` trong `requirements()`, chỉ khi có REQ. Các cột: Mã · Phương án · Mã nguồn · Tiêu chí/Test · Tình trạng (chưa thiết kế / chưa hiện thực / chưa kiểm / đủ). `summary` dạng "N/M REQ có ít nhất một phép đo".
2. Thêm hook `@bus.on_stop def req_chua_phu(ctx)`: chỉ chạy khi `ctx.config.features.bat("req_phu")` (đọc bằng getattr phòng thủ, vì `_Ctx` trong test không có `config`), ctx có `store`, `da_ghi_gi_do` là True, và không có kế hoạch dở (dùng lại `_ke_hoach_dang_chay`).
3. Nếu có REQ loại FR/NFR mà cột Tiêu chí/Test rỗng thì trả `StopResult(another_round=True, fired=["req_chua_phu"], injection=...)`. Lời nhắc liệt kê tối đa 8 REQ và cho hai lối: viết `sim.criteria`/test, hoặc nói rõ là ngoài phạm vi lượt này.
4. Chỉ nổ MỘT lần mỗi lượt (cờ `ctx.da_nhac_req_phu`).

**Không được làm (giới hạn phạm vi):**
- Không sửa `kiem_viec_chua_ai_kiem` và verifier; không đổi thứ tự hook có sẵn.
- Không chặn trả lượt. Hook chỉ nhắc một vòng.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-02-01 | Đơn vị | tests/test_phan_tich_thiet_ke_len_tab.py::test_A2_5_ma_tran_hien_REQ_chua_kiem | `KhoGia(req=[FR-01, FR-02], criteria=[assert do_req FR-01])` → `S.requirements(kho, None)` → có khối A2.5, dòng FR-02 ghi "chưa kiểm" |
| TC-M2-02-02 | Ca âm | …::test_khong_co_REQ_thi_khong_co_A2_5 | kho rỗng → không có mã khối "A2.5" (chống khối rỗng giả) |
| TC-M2-02-03 | Đơn vị | tests/test_req_phu.py::test_hook_nhac_REQ_mo_coi_khi_co_bat | `_Ctx` như test_hoi_xong_thi_lam.py, thêm `store` thật có FR-02 mồ côi và `config.features.req_phu=True` → `stop(ctx).another_round` và "FR-02" có trong injection |
| TC-M2-02-04 | Cờ TẮT | …::test_co_tat_hook_im | như trên nhưng cờ tắt → `"req_chua_phu" not in r.fired` |
| TC-M2-02-05 | Ca âm | …::test_dang_giua_ke_hoach_thi_hoan | kế hoạch còn bước chưa xong → hook không nổ |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_phan_tich_thiet_ke_len_tab.py tests/test_hoi_xong_thi_lam.py tests/test_cx_cong_tac.py tests/test_ke_hoach.py`
- CX07 (Stop bắt thêm một vòng) giữ đúng số vòng khi cờ tắt.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ".
- [ ] Toàn bộ `pytest -q` xanh.
- [ ] Chạy lại 76 ca với cờ bật: không tụt so với cờ tắt thì mới đề xuất bật mặc định.
- [ ] Ghi DEV-LOG; nếu đổi giao diện thì thêm kiểu khối vào `test_giao_dien_biet_ve_kieu_khoi_moi`.

**Hoàn tác:** tắt cờ `req_phu`; khối A2.5 thì revert commit.

<!-- TASK M2-03 -->
<a id="m2-03"></a>
### [M2-03] Kiểm chất lượng yêu cầu: tiêu chí đo được, từ mơ hồ, trùng lặp — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #6

**Mục tiêu:** `store.req_create`/`store.req_update` trả cảnh báo có cấu trúc khi REQ thiếu tiêu chí đo được, chứa từ mơ hồ, hoặc trùng ý với REQ đã có.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_REQ_CHAT_LUONG`, mặc định TẮT). Module thuần thì luôn có.
**Phụ thuộc:** Không. Phần subagent `req-critic` (bước 4) gộp với M2-13 nếu làm chung khung subagent.
**Tệp chạm tới:** src/eide/yeu_cau.py (mới), src/eide/tools/writing.py, src/eide/config.py, tests/test_yeu_cau.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- writing.py:165–197 `store_req_create`: `required` gồm id, loai, text, source_quote, explain; `criteria` mặc định `""`; không có phép kiểm nào khác.
- writing.py:199–227 `store_req_update`: cũng không kiểm.
- Grep `mơ hồ|mâu thuẫn|EARS|INVEST` trong src/eide: không có bộ kiểm yêu cầu. tools/bo_usecase.py TC004/TC005 chỉ chấm bằng dấu hiệu bề mặt.

**Thay đổi cần làm:**
1. `src/eide/yeu_cau.py`, toàn hàm thuần:
   - `kiem_tieu_chi(s) -> list[str]`: rỗng, hoặc không có số kèm đơn vị/phép so (regex: `(≤|≥|<=|>=|<|>|=)?\s*\d+([.,]\d+)?\s*[A-Za-zµ%°/]+`) thì cảnh báo "tiêu chí chưa đo được".
   - `TU_MO_HO` gồm nhanh, ổn định, thông minh, dễ dùng, tốt, mượt, nhiều, ít, tối ưu, thân thiện. `tu_mo_ho(text) -> list[str]` so sau khi bỏ dấu (tái dùng cách `_go_dau` ở design.py).
   - `trung_lap(text, ds_req) -> list[str]`: Jaccard token (bỏ dấu, bỏ từ ≤2 ký tự) ≥ 0,6 thì trả mã REQ.
2. Khi cờ bật, `store_req_create` và `store_req_update` thêm vào kết quả `"canh_bao_chat_luong": [...]`, và nối một câu vào `note_vi` chỉ đường `ask_user` để làm rõ. KHÔNG chặn ghi.
3. Khi cờ tắt: kết quả giống hệt hiện nay (không có khoá mới).
4. (Tuỳ chọn, gộp M2-13) subagent `req-critic` chỉ đọc, `toi_da_goi=8`, chấm theo rubric ISO 29148 và trả câu hỏi làm rõ.

**Không được làm (giới hạn phạm vi):**
- Không biến `criteria` thành bắt buộc trong lược đồ; không đổi thông điệp của luật N7 (test_policy_tools.py:30).
- Không tự sửa text REQ hộ người dùng.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-03-01 | Đơn vị | tests/test_yeu_cau.py::test_tieu_chi_khong_so_thi_canh_bao | `kiem_tieu_chi("chạy nhanh")` khác rỗng; `kiem_tieu_chi("≥ 5 MB/s")` == [] (mã cũ: ImportError) |
| TC-M2-03-02 | Đơn vị | …::test_tu_mo_ho_bo_dau | `tu_mo_ho("Hệ thống phải ON DINH")` chứa "ổn định" |
| TC-M2-03-03 | Đơn vị | …::test_trung_lap | FR-01 "Nhận tệp phim qua LAN" so với "nhận tệp phim qua mạng LAN" → ["FR-01"] |
| TC-M2-03-04 | Tích hợp | …::test_req_create_co_bat_tra_canh_bao | fixture `bo` với `Features(req_chat_luong=True)` → req_create không criteria → có "canh_bao_chat_luong", REQ vẫn được ghi |
| TC-M2-03-05 | Cờ TẮT | …::test_co_tat_ket_qua_y_cu | cờ tắt → `"canh_bao_chat_luong" not in ra` |
| TC-M2-03-06 | Ca âm | …::test_REQ_tot_khong_bi_keu | "Tốc độ chép ≥ 5 MB/s qua LAN 100 Mbps" kèm criteria đo được → danh sách cảnh báo rỗng |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_cx_cong_tac.py tests/test_policy_tools.py tests/test_duong_dan_toi_cong_cu.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Bật cờ, chạy TC004/TC005: số câu hỏi làm rõ tăng, các ca khác không tụt.
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ `req_chat_luong`.

<!-- TASK M2-06 -->
<a id="m2-06"></a>
### [M2-06] Bước kế hoạch có cổng kiểm (`kiem`) và mã REQ; `step_done` đối chiếu sổ cái — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #7

**Mục tiêu:** bước kế hoạch sinh mã chỉ được đánh dấu xong khi công cụ kiểm đã khai (build/test/sim/lint) đã chạy thành công SAU lần ghi của bước đó.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_KE_HOACH_CONG_KIEM`, mặc định TẮT).
**Phụ thuộc:** Gộp với M1-13 (cùng chạm ke_hoach.py). M2-07 làm sau.
**Tệp chạm tới:** src/eide/ke_hoach.py, src/eide/tools/ke_hoach.py, src/eide/config.py, tests/test_ke_hoach_cong_kiem.py (mới).

**ĐÃ KIỂM LẠI:** JSON đề xuất mã lỗi E6006, nhưng E6006 đã được dùng. Đổi sang **E6012**.

**Hiện trạng (đã kiểm lại trong mã):**
- ke_hoach.py `Buoc` có viec, cong_cu, hien_vat, cong, chi_phi, ghi_chu, xong. Không có trường kiểm, không có trường REQ.
- ke_hoach.py `thieu_phan_tich`: cấu trúc mã chỉ được kiểm bằng tìm từ khoá `_TU_CAU_TRUC` ("module", "api", "thư mục"…) trong viec/ghi_chu/hien_vat.
- tools/ke_hoach.py:28 `_SCHEMA_BUOC` gồm 6 trường; `plan_exit` (dòng 230) chạy `kiem_ke_hoach` → E6003, `thieu_phan_tich` → E6009.
- tools/ke_hoach.py:330 `plan_step_done(ctx, so, hien_vat)` chỉ kiểm `_hien_vat_co_that` → E6004.
- hooks/standard.py:303 `ledger_and_lint` ghi `tool_result {tool, ok}` vào sổ cái theo thứ tự, nên có đủ dữ liệu để đối chiếu thứ tự ghi và kiểm.

**Thay đổi cần làm:**
1. `Buoc` thêm `kiem: str = ""` và `req: list[str]` (field default_factory). `to_dict`/`from_dict` đọc và ghi hai trường này (kế hoạch cũ trên đĩa không có thì nhận giá trị mặc định).
2. `_SCHEMA_BUOC` thêm `kiem` (enum: build.compile, test.run, sim.run, hdl.lint, code.analyze, khong) và `req`. Khi cờ tắt, lược đồ giữ nguyên.
3. Khi cờ bật, `kiem_ke_hoach`: bước có `_la_ma(b)` mà `kiem` rỗng thì là lỗi "bước X sinh mã mà không nói kiểm bằng gì"; `kiem="khong"` thì bắt buộc có `ghi_chu`.
4. Khi cờ bật, `plan_step_done`: bước có `kiem` thuộc danh sách công cụ thì duyệt `ctx.ledger.read()`. Phải có `tool_result{tool==kiem, ok==True}` nằm SAU `tool_result` ghi gần nhất của bước. Không có thì trả `E6012`, kèm hint "chạy <kiem> rồi đánh dấu lại".

**Không được làm (giới hạn phạm vi):**
- Không đổi E6003, E6004, E6009 và thông điệp của chúng.
- Không ép `kiem` cho bước thuần tài liệu (không phải `_la_ma`).
- Không đọc lại toàn bộ sổ cái mỗi lần vẽ bề mặt.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-06-01 | Đơn vị | tests/test_ke_hoach_cong_kiem.py::test_buoc_sinh_ma_thieu_kiem_thi_loi | cờ bật, `KeHoach` có bước fs.write `src/a.c` không `kiem` → `kiem_ke_hoach` có lỗi chứa "kiểm bằng gì" |
| TC-M2-06-02 | Tích hợp | …::test_step_done_chua_build_thi_E6010 | fixture `bo` + cờ bật; kế hoạch hợp lệ có kiem=build.compile; fs.write rồi step_done → `E6012` |
| TC-M2-06-03 | Tích hợp | …::test_step_done_sau_build_ok_thi_qua | ledger có `tool_result build.compile ok=True` sau lần ghi → step_done thành công |
| TC-M2-06-04 | Cờ TẮT | …::test_co_tat_step_done_nhu_cu | cờ tắt → step_done chỉ kiểm hiện vật như hiện nay |
| TC-M2-06-05 | Ca âm | …::test_buoc_tai_lieu_khong_bi_doi_kiem | bước fs.write `tai-lieu/1.md` → không lỗi |
| TC-M2-06-06 | Ca biên | …::test_ke_hoach_cu_tren_dia_khong_co_truong_kiem | `KeHoach.from_dict` của dict thiếu kiem/req → không lỗi, `kiem==""` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ke_hoach.py tests/test_quy_trinh_lap_trinh.py tests/test_chia_viec_lon.py tests/test_phan_tich_thiet_ke_len_tab.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Eval 76 ca với cờ bật không tụt; đo số lỗi build bắt được tại bước.
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ `ke_hoach_cong_kiem`.

<!-- TASK M2-08 -->
<a id="m2-08"></a>
### [M2-08] `phan_tich_ma`: nhận ISR/handler và không nuốt hàm kế tiếp — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #8

**Mục tiêu:** `code.analyze` liệt kê được `ISR(...)`, `*_IRQHandler`, hàm có `__attribute__((interrupt))`, và không còn bỏ sót hàm vì regex tham lam.
**Loại:** Sửa lỗi thuần.
**Phụ thuộc:** Không. Là tiền đề của M2-09.
**Tệp chạm tới:** src/eide/phan_tich_ma.py, tests/test_phan_tich_ma.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- phan_tich_ma.py:33–41, `_HAM[".c"] = r"^[A-Za-z_][\w \*]*\s+\**(\w+)\s*\([^;]*\)\s*\{"`: bắt buộc có kiểu trước tên hàm.
- ĐÃ ĐO LẠI trên `du-lieu/robot-tu-can-bang/firmware/timer.c`: kết quả chỉ có `timer_init, timer_get_ms, timer_check_control_flag, timer_get_deadline_miss`. Thiếu `ISR(TIMER0_COMPA_vect)` và `ISR(TIMER2_COMPA_vect)` (dòng 31, 45).
- ĐÃ ĐO LẠI, phát hiện thêm so với JSON: với đoạn `static void phu(void) { }` + `void __attribute__((interrupt)) TIM2_IRQHandler(void) { }` + `void SysTick_Handler(void)\n{\n}`, regex chỉ ra `['phu']`. Lý do: `[^;]*` tham lam vượt qua nhiều hàm không có dấu `;`, nuốt luôn các hàm phía sau.
- `TepMa.ky_hieu: list[str]` được `dung_tai_lieu` và `code_analyze` (xay_dung.py:309) dùng làm khoá của `ai_dung`.

**Thay đổi cần làm:**
1. Đổi `[^;]*` thành `[^;{}()]*(?:\([^;{}]*\))?[^;{}()]*` (giới hạn trong một danh sách tham số, không vượt `{`/`}`), hoặc đơn giản hơn là `\([^;{}]*\)`.
2. Thêm mẫu `_ISR = re.compile(r"^\s*ISR\s*\(\s*(\w+)", re.M)`, mẫu `__attribute__\s*\(\(\s*(?:interrupt|signal)[^)]*\)\)\s*(\w+)`, và nhận mọi tên khớp `\w+_(IRQ)?Handler` là ISR.
3. Thêm hàm `phan_loai(p, chu) -> dict[str, str]` (tên → "ham" | "isr" | "static"). GIỮ `_ky_hieu` trả `list[str]` như cũ, có thêm tên ISR, để không vỡ `ai_dung`.
4. `dung_tai_lieu`: thêm cột hoặc dòng "Ngắt (ISR): …" khi có ISR.

**Không được làm (giới hạn phạm vi):**
- Không đổi kiểu `TepMa.ky_hieu`; không đổi khoá trả về của `code.analyze`.
- Không thêm phụ thuộc tree-sitter ở nhiệm vụ này (để lại M2-09).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-08-01 | Đơn vị | tests/test_phan_tich_ma.py::test_ISR_macro_AVR_duoc_nhan | `_ky_hieu(Path("t.c"), "ISR(TIMER0_COMPA_vect) {\n x++;\n}\n")` chứa "TIMER0_COMPA_vect" |
| TC-M2-08-02 | Đơn vị | …::test_khong_nuot_ham_ke_tiep | đoạn 3 hàm thân rỗng nêu trên → đủ 3 tên `phu, TIM2_IRQHandler, SysTick_Handler` |
| TC-M2-08-03 | Đơn vị | …::test_phan_loai_isr | `phan_loai` cho SysTick_Handler → "isr", phu → "static" |
| TC-M2-08-04 | Tích hợp | …::test_code_analyze_tai_lieu_co_muc_ISR | fixture `bo`, tệp có ISR → tài liệu có chuỗi "ISR" và tên vector |
| TC-M2-08-05 | Ca âm | …::test_loi_goi_ham_trong_than_khong_thanh_dinh_nghia | `int main(void){ foo(1); return 0; }` → chỉ có "main", không có "foo" |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_quy_trinh_lap_trinh.py tests/test_phan_tich_thiet_ke_len_tab.py`
- `test_code_analyze_tra_loi_cau_AI_DANG_DUNG` vẫn thấy `app.c`.

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ" (trả lại regex cũ thì TC-01, TC-02 đỏ).
- [ ] `pytest -q` xanh.
- [ ] Trên firmware robot: số ISR nhận ra = 3 (timer.c ×2, uart.c ×1).
- [ ] DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-01 -->
<a id="m3-01"></a>
### [M3-01] ERC luật quá áp trên net (5 V vào chân 3,3 V) — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #9

**Mục tiêu:** `board.check` / `ERC.erc()` tự báo **blocker** khi một net mang điện áp vượt mức chịu tối đa của một chân nối vào nó, không cần tác tử tự nhớ gọi `fact.compare`.
**Loại:** Sửa lỗi thuần (bổ sung luật kiểm bằng mã)
**Phụ thuộc:** Không. Nên làm cùng M3-07, vì M3-07 sửa cách tra chủ thể `chip:X`.
**Tệp chạm tới:** `src/eide/knowledge/erc.py`, `tests/test_erc.py`

**Hiện trạng (đã kiểm lại trong mã):**
- erc.py:40 `KHOA["v_max"] = ("v_max","vdd.max","vin.max","ap_toi_da")` đã có bí danh, nhưng không hàm nào gọi `tf.tra(..., "v_max")`.
- erc.py:136 `erc()` chỉ gọi 4 luật: `ngan_sach_dong`, `muc_logic_tren_net`, `trung_dia_chi_bus`, `pull_up_bus`.
- compare.py:211 `qua_ap(ap_cap, chiu_toi_da)` đã viết sẵn kết luận, câu chữ và chặn vế ĐỒNG (`_chan_dong`, tầng hợp lệ là `VANG/BAC/NGUOI`).
- Điện áp rail đã có trong mô hình: `ckm.net_set(ap_danh_dinh=...)` (tools/ckm.py:500) ghi `canonical.ap_danh_dinh` cho net, ví dụ fixture `bo` có `"3,3 V"`.

**Thay đổi cần làm:**
1. Thêm `"vddio_max": ("vddio.max","vddio_max")` và `"v_tolerant": ("v_tolerant","ft","five_volt_tolerant")` vào `KHOA`.
2. Viết `qua_ap_tren_net(cay, tf, phang, thuoc) -> list[PhatHien]`. Với mỗi net điện:
   - Vế cấp = điện áp rail lấy từ `canonical.ap_danh_dinh` của net thành viên. Phân tích bằng `knowledge.chuan_hoa.chuan_hoa` và dựng một "Fact giả" `{key:"ap_danh_dinh", value, unit:"V", tier:"NGUOI", subject:"net:<path>", source:{"human_act_id":"ckm.net_set"}}`.
   - Nếu không có rail thì lấy `voh` lớn nhất của một chân trên net (tầng hợp lệ).
   - Vế chịu = `tf.tra(ct, "v_max")`, nếu không có thì `vddio_max` của từng chân lá (chủ thể `pin:REF.N` trước, rồi `chu_the_la`).
   - Chân có `v_tolerant` mang giá trị truthy thì bỏ qua.
   - Gọi `CP.qua_ap(cap, chiu)`; `chua_kiem_chung` thì đổi thành `chua_du_du_kien`. Path là khối cha của lá vi phạm (`_path_cua_ref`).
3. Gọi luật mới trong `erc()`, sau `muc_logic_tren_net`. Bỏ qua net đất (`_la_dat`).
4. Không sinh phát hiện `dat` cho chân không có Fact `v_max`, để không làm nhiễu bảng (giữ `test_board_check..._dat == []`).

**Không được làm (giới hạn phạm vi):**
- Không đổi chữ ký `erc(store)`, `PhatHien`, `CP.qua_ap`.
- Không suy `v_max` từ tên chip hay tri thức chung. Thiếu Fact thì im lặng hoặc trả `chua_du_du_kien`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-01-01 | Đơn vị | tests/test_erc.py::test_qua_ap_rail_5V_vao_chan_3V6_bi_chan | `bo`; đặt lại `net:/board.3V3` với `ap_danh_dinh="5 V"` (gọi `bo.ckm_dat_nut`); `_fact(bo,"leaf:U2","vdd.max",3.6,unit="V")` → `E.erc(bo)` → có `_tim(ds,"qua_ap","khong_dat")`, `muc=="blocker"`, `"U2"` trong `vi`, `path.startswith("/board/sense")` |
| TC-M3-01-02 | Ca âm | tests/test_erc.py::test_qua_ap_trong_gioi_han_khong_bao | rail 3,3 V, `vdd.max=5.5 V` cho U2 → không có `qua_ap/khong_dat` |
| TC-M3-01-03 | Ca biên | tests/test_erc.py::test_qua_ap_ve_DONG_thi_chua_du_du_kien | rail 5 V, `vdd.max=3.6` tier `DONG` → chỉ có `qua_ap` với `ket_luan=="chua_du_du_kien"` |
| TC-M3-01-04 | Đơn vị | tests/test_erc.py::test_qua_ap_tin_hieu_voh_vuot_vmax_chan_thu | `_fact(bo,"pin:U1.27","voh",4.8,unit="V")`, `_fact(bo,"pin:U2.5","v_max",3.6,unit="V")` → blocker trên net SDA |
| TC-M3-01-05 | Ca âm | tests/test_erc.py::test_qua_ap_chan_chiu_5V_khong_bao | như TC-01, thêm `_fact(bo,"pin:U2.1","v_tolerant","1")` → không blocker |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py tests/test_sch_a.py tests/test_ckm*.py`
- `test_board_check_noi_ro_CHUA_DU_DU_KIEN_khong_goi_la_dat` vẫn có `ket_qua["dat"] == []`. `test_HIER17_moi_phat_hien_noi_ro_o_khoi_nao` vẫn đúng: mọi phát hiện có `path`.

**Tiêu chí xong:**
- [ ] 5 TC xanh; đã "phá lại thì đỏ" (bỏ lời gọi luật trong `erc()` thì TC-01/04 đỏ).
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit; luật là hàm độc lập, bỏ một dòng gọi trong `erc()` là tắt.

<!-- TASK M3-03 -->
<a id="m3-03"></a>
### [M3-03] ERC theo kiểu chân (ma trận điện thay KiCad ERC) — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #10

**Mục tiêu:** EIDE tự bắt được output nối output, power_out nối power_out, net nguồn không ai cấp và net một chân mà không cần KiCad.
**Loại:** Sửa lỗi thuần (luật mới bằng mã)
**Phụ thuộc:** Không. M3-04 dùng chung bộ đếm "ai cấp".
**Tệp chạm tới:** `src/eide/knowledge/erc_kieu_chan.py` (mới), `src/eide/knowledge/erc.py`, `tests/test_erc.py`

**Hiện trạng (đã kiểm lại trong mã):**
- sch/kyhieu.py:27 `KIEU_CHAN` ánh xạ hướng Port sang kiểu chân KiCad. tools/sch.py:11 ghi "máy này KHÔNG cài KiCad". Không có ma trận nội bộ.
- knowledge/ckm.py:563 `cho_dut` có `net_mot_chan`, nhưng chỉ là một dòng chữ trong `ckm.build` (tools/ckm.py:916), không phải `PhatHien`.
- knowledge/cay.py:697 `_huong_theo_ten`: Port lá sinh khi di cư lấy `power_in` cho cả chân VCC lẫn GND, còn lại là `passive`. Hướng thật chỉ có khi người khai qua `ckm.port_set`.

**Thay đổi cần làm:**
1. Tạo `erc_kieu_chan.py` với `kiem_kieu_chan(cay, tf, phang, thuoc) -> list[PhatHien]`. Đi qua `cay.noi` theo từng net điện (nhóm bằng `thuoc`) và chỉ xét Port của LÁ (`cay.nut[p["module_id"]]["kind"] == "leaf"`).
2. Luật dùng `huong` của Port lá:
   - `out`+`out`: luật `xung_dau_ra`, blocker.
   - `power_out`+`out`: blocker.
   - Net `loai` power/rail không có Port lá `power_out` nào và không lá nào có Fact `iout_max`: luật `nguon_khong_cap`, `canh_bao`/major. Bỏ qua nếu net có `canonical.pwr_flag` truthy. Bỏ qua net đất (dùng lại `erc._la_dat`).
   - Net có đúng 1 chân lá: luật `net_mot_chan`, `canh_bao`/minor.
   - `in` không có `out`/`bidir`/`power_out` nào trên net, và net không phải nguồn: luật `dau_vao_treo`, minor.
   - `passive` không tham gia xung đột.
3. Ưu tiên kiểu chân người đã xác nhận nếu có: đọc `symbol_map:mach` (`MA_SYMBOL` trong tools/sch.py). Không có thì dùng `huong` Port.
4. Không sinh phát hiện `dat`. Gọi `kiem_kieu_chan` trong `erc()` sau 4 luật cũ.

**Không được làm (giới hạn phạm vi):**
- Không đổi `_huong_theo_ten` hay hướng Port đã lưu.
- Không coi `passive` là xung đột (tránh báo nhầm hàng loạt trên mạch di cư).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-03-01 | Đơn vị | tests/test_erc.py::test_hai_dau_ra_noi_chung_bi_chan | `bo` + lá Q1, Q2 trong `/board/mcu`, mỗi lá một Port `huong="out"` nối vào net mới `net:/board/mcu.X` → `_tim(ds,"xung_dau_ra","khong_dat")` có, blocker, `vi` nêu Q1 và Q2 |
| TC-M3-03-02 | Ca âm | tests/test_erc.py::test_bo_mau_khong_co_xung_dot_kieu_chan | `bo` nguyên → không có phát hiện `khong_dat` nào của các luật mới (U3 power_out cấp 3V3) |
| TC-M3-03-03 | Đơn vị | tests/test_erc.py::test_net_nguon_khong_ai_cap_thi_canh_bao | thêm net `5V` `loai=power` chỉ có Port power_in của U1 → `nguon_khong_cap` `canh_bao` |
| TC-M3-03-04 | Ca âm | tests/test_erc.py::test_net_GND_khong_doi_nguon_cap | net `GND` `loai=gnd`, chân power_in → không có `nguon_khong_cap` |
| TC-M3-03-05 | Đơn vị | tests/test_erc.py::test_net_mot_chan_la_phat_hien_erc | net chỉ nối 1 Port lá → `net_mot_chan` có `path` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py tests/test_sch_a.py tests/test_sch0.py tests/test_ckm*.py tests/test_khoi.py`
- `board.check` trên mạch chỉ có khối PWR (test hiện có) vẫn có `ket_qua["dat"] == []` và vẫn nói "CHƯA ĐỦ DỮ KIỆN".

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ (tắt lời gọi `kiem_kieu_chan`).
- [ ] `pytest -q` xanh, ≥ mốc. Chạy `tools/thu_sch.py` (cờ schematic bật): số phát hiện mới trên mạch mẫu được ghi vào DEV-LOG, kèm lý do nếu có báo nhầm.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert; hoặc bỏ dòng gọi trong `erc()`.

<!-- TASK M3-04 -->
<a id="m3-04"></a>
### [M3-04] ERC tranh chấp nguồn và ngắn mạch rail–GND — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #11

**Mục tiêu:** Hai bộ cấp trên một rail, hoặc một rail bị nối vào GND, bị báo blocker thay vì bị bỏ qua lặng lẽ.
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** Không. Có thể làm cùng M3-03.
**Tệp chạm tới:** `src/eide/knowledge/erc.py`, `tests/test_erc.py`

**Hiện trạng (đã kiểm lại trong mã):**
- erc.py `_hai_ve_dong`: `if f_cap is not None or p["huong"] == "power_out": ... cap = {...}` chỉ giữ MỘT bộ cấp (tầng tin nhất) và bỏ các bộ khác mà không báo gì.
- erc.py `_nhom_nguon` loại cả nhóm nếu `_la_dat(cay, v)`: chỉ cần MỘT net thành viên có `loai=="gnd"` hoặc tên GND/VSS là cả nhóm (kể cả nhóm mang tên +3V3) bị bỏ khỏi mọi phép kiểm.
- Fixture `bo`: trên net 3V3 có hai Port power_out, của lá U3 và của khối `/board/pwr` (Port `VOUT`). Port khối là đường đi qua cấp, không phải bộ cấp thứ hai.

**Thay đổi cần làm:**
1. Thêm `tranh_chap_nguon(cay, tf, thuoc)`: với mỗi nhóm nguồn, đếm các LÁ khác nhau có Port `power_out` hoặc có Fact `iout_max`. Từ 2 lá trở lên, và không net thành viên nào có `canonical.or_ing` truthy, thì blocker `tranh_chap_nguon` kèm `bang_chung` của từng bộ cấp. Port của khối không được đếm.
2. Thêm `chap_nguon(cay, thuoc)`: một nhóm điện có cả net `loai` thuộc {power, rail} lẫn net `loai=="gnd"` (hoặc tên đúng GND/VSS/AGND/DGND), thì blocker `chap_nguon`. `vi` nêu tên hai net và path của từng net.
3. Gọi cả hai trong `erc()`.

**Không được làm (giới hạn phạm vi):**
- Không đổi kết quả `ngan_sach_dong` cho nhóm chỉ có một bộ cấp (các test HIER07 hiện có phải giữ nguyên).
- Không đếm Port khối.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-04-01 | Đơn vị | tests/test_erc.py::test_hai_LDO_cung_rail_bi_chan | thêm lá U7 trong `/board/pwr`, Port `huong="power_out"` nối `net:/board/pwr.VOUT_I` → `_tim(ds,"tranh_chap_nguon","khong_dat")` có, nêu U3 và U7 |
| TC-M3-04-02 | Ca âm | tests/test_erc.py::test_port_khoi_power_out_khong_tinh_la_bo_cap_thu_hai | `bo` nguyên → không có `tranh_chap_nguon` |
| TC-M3-04-03 | Đơn vị | tests/test_erc.py::test_rail_noi_vao_GND_bi_chan | thêm net `net:/board/mcu.GND_I` `loai=gnd`, rồi nối nó vào Port `/board/mcu.VDD` (cùng nhóm 3V3) → `chap_nguon` blocker |
| TC-M3-04-04 | Ca biên | tests/test_erc.py::test_or_ing_khai_ro_thi_khong_bao | như TC-01 nhưng net 3V3 có `canonical.or_ing=True` → không blocker |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py`
- Các test `test_HIER07_*` và `test_khoi_cap_nhan_ra_bang_FACT_du_Port_chua_biet_huong` giữ nguyên.

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-07 -->
<a id="m3-07"></a>
### [M3-07] Nối Fact datasheet ↔ khoá/chủ thể ERC, và báo độ phủ ERC — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #12

**Mục tiêu:** Fact do `fact.extract` ghi (chủ thể `chip:X@ver`, khoá `icc.typ`) được ERC nhìn thấy, và mọi kết quả ERC nói rõ bao nhiêu luật thực sự đã kết luận.
**Loại:** Sửa lỗi thuần (ô xanh giả "ERC 0 lỗi chặn")
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/knowledge/erc.py`, `src/eide/knowledge/docs.py`, `src/eide/tools/ckm.py` (board.check), `src/eide/tools/sch.py` (sch.netlist), `tests/test_erc.py`, `tests/test_tri_thuc.py`, `tests/test_sch_a.py`

**Hiện trạng (đã kiểm lại trong mã):**
- ĐÃ KIỂM LẠI, phát hiện thêm: `fact.extract` ghi `subject = thuc_the` (docs.py:637), và mô tả công cụ khuyên dạng `chip:ATmega328P@1.0.0` (test_tri_thuc.py:120 dùng `chip:ATmega328P`). Nhưng `chu_the_la` (erc.py) chỉ tra `leaf:U1`, `U1`, `ATmega328P`, và `TraFact.tra` khớp chuỗi tuyệt đối. Vì vậy Fact trích từ datasheet không bao giờ tới được ERC.
- docs.py:357: dòng ICC sinh khoá `icc.typ`, mà bí danh `i_max` (erc.py:40) không có `icc.typ`. Chế độ bảng (docs.py:517) thì sinh `icc.max` đúng.
- Không có mẫu trích cho `iout_max` hay `i2c.addr`.
- tools/sch.py:216 `nang = [x for x in ph if x.ket_luan == "khong_dat"]`: chỉ trả lỗi chặn; `chua_du_du_kien` bị ẩn.

**Thay đổi cần làm:**
1. `TraFact.__init__`: ngoài khoá gốc, nếu `subject` có dạng `chip:<ten>[@ver]` thì đánh chỉ mục thêm dưới `<ten>` (bỏ tiền tố và phiên bản). Ưu tiên vẫn theo thứ tự trong `chu_the_la`.
2. Thêm `icc.typ` vào bí danh `i_max`. Khi Fact dùng có khoá `.typ`, `_hai_ve_dong` ghi vào `bang_chung` cờ `"dung_typ_thay_max": True` và câu "con số danh định, không phải tối đa".
3. docs.py `_MAU_THONG_SO`: thêm `(r"\bI\s*OUT\b|\boutput\s+current\b", "iout.max")` và `(r"\b(I2C|slave)\s+address\b", "i2c.addr")`. Thêm khoảng `PHAM_VI_HOP_LY["iout.max"]=(1e-3, 50)`. Địa chỉ dạng nhị phân 7 bit thì đọc thành hex.
4. Thêm hàm `do_phu(ds) -> dict` trong erc.py: `{luat: {"dat":n,"khong_dat":n,"canh_bao":n,"chua_du":n}}`, kèm `fact_con_thieu` (gom từ `cach_sua` của các phát hiện `chua_du_du_kien`). `board.check` và `sch.netlist` trả thêm khoá `do_phu`. `sch.netlist` thêm câu "N luật chưa đủ dữ kiện" vào `note_vi` khi có.

**Không được làm (giới hạn phạm vi):**
- Không đổi khoá trả về hiện có (`erc_loi_chan`, `ket_qua`, `so_phat_hien`). Chỉ THÊM khoá mới.
- Không tự gán Fact `chip:X` cho một lá khác tên chip.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-07-01 | Đơn vị | tests/test_erc.py::test_fact_chu_the_chip_co_phien_ban_duoc_ERC_thay | `_fact(bo,"chip:AMS1117@1.0.0","iout_max",0.8,unit="A")` + i_max cho U1, U2 → `ngan_sach_dong` `dat` |
| TC-M3-07-02 | Đơn vị | tests/test_erc.py::test_icc_typ_duoc_cong_va_noi_ro_la_typ | U1 chỉ có `icc.typ` → cộng được; `bang_chung` có `dung_typ_thay_max` |
| TC-M3-07-03 | Đơn vị | tests/test_tri_thuc.py::test_trich_IOUT_va_dia_chi_i2c | PDF qua `lam_pdf` có "Output Current IOUT 1 A" và "I2C address 0x48" → ứng viên `iout.max`=1 A, `i2c.addr`="0x48" |
| TC-M3-07-04 | Tích hợp | tests/test_erc.py::test_board_check_tra_do_phu | dựng như `test_board_check_noi_ro_CHUA_DU...` → `r.data["do_phu"]["ngan_sach_dong"]["chua_du"] >= 1` |
| TC-M3-07-05 | Ca âm | tests/test_erc.py::test_chip_khac_ten_khong_bi_gan_nham | `chip:LM1117@1` iout_max, lá U3 tên AMS1117 → vẫn `chua_du_du_kien` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py tests/test_tri_thuc.py tests/test_sch_a.py tests/test_ing_c.py`
- `test_khoa_fact_co_bi_danh` và `test_netlist_kiem_bang_cach_DOC_LAI_tep` giữ nguyên.

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc. Đo trên 3 mạch mẫu: tỉ lệ `chua_du_du_kien` trước và sau, ghi vào DEV-LOG.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-10 -->
<a id="m3-10"></a>
### [M3-10] Vòng sinh → ERC → sửa có trần cho bản đồ mạch (hook `erc_delta`) — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #13

**Mục tiêu:** Sau mỗi lần sửa bản đồ mạch, tác tử thấy ngay lỗi chặn MỚI do chính nó gây ra; lượt không kết thúc khi còn lỗi chặn mới chưa nhắc tới; vòng sửa cho cùng một lỗi có trần 3.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_ERC_TU_DONG`, mặc định TẮT)
**Phụ thuộc:** M3-03, M3-04, M3-07 (để ERC có thứ đáng báo).
**Tệp chạm tới:** `src/eide/hooks/standard.py`, `src/eide/config.py`, `src/eide/knowledge/erc.py`, `tests/test_erc_tu_dong.py` (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- hooks/standard.py:303 `ledger_and_lint` (on_post_tool) chỉ ghi sổ và bắt kết quả rỗng; không có hook nào chạy ERC.
- ERC chỉ chạy khi gọi `board.check` (tools/ckm.py:766), trong `ckm.build` (:883) và trong `sch.netlist` (tools/sch.py:213).
- ĐÃ KIỂM LẠI, phát hiện cũ SAI một phần: JSON ghi "_GHI_CHAC_CHAN không có ckm.* nên verifier không bị nhắc". Thực tế `kiem_chung._la_ghi` (kiem_chung.py:~70) còn coi mọi công cụ `writes_artefact=True` là ghi, và `ckm.chip_add/module_set/port_set/pinout_set/net_set/from_pinout/import_netlist/build` đều có `writes_artefact=True` (tools/ckm.py:169–862). Phần đó BỎ, không làm.
- sch.compose sinh SKiDL tất định từ cây (sch/soan.py:45), nên vòng sửa thật nằm ở các công cụ `ckm.*`.

**Thay đổi cần làm:**
1. Cờ `erc_tu_dong` trong `Features`.
2. Hook `@bus.on_post_tool erc_delta(call, result, ctx)`. Khi cờ bật, công cụ thuộc `ckm.*` / `khoi.place` / `khoi.upgrade` và `result.ok`:
   - Chạy `ERC.erc(ctx.store)` và lấy tập khoá `(luat, path, vi[:60])` có `ket_luan=="khong_dat"` hoặc `muc in {"blocker","major"}`.
   - So với `ctx.erc_truoc` (thuộc tính mới, mặc định `None` thì coi là tập rỗng ở lần đầu của lượt).
   - Gắn vào `result.data["erc_moi"]` tối đa 3 phát hiện mới, kèm `note_vi` một câu. Cập nhật `ctx.erc_truoc`.
   - Đếm `ctx.erc_lan_sua[(luat,path)] += 1` khi phát hiện đó còn sau một lần ghi.
3. Hook `@bus.on_stop erc_chua_xu`: cờ bật và còn phát hiện mới chưa có trong `ctx.loi_da_noi` (khớp theo `luat` hoặc `path`) thì `StopResult(another_round=True, injection=...)`. Nếu một khoá có `erc_lan_sua >= 3` thì injection yêu cầu gọi `ask_user` thay vì sửa tiếp.
4. Chi phí: ERC là mã thuần. Đo thời gian, và bỏ qua hook nếu cây có trên 2000 nút (ghi `note_vi`).

**Không được làm (giới hạn phạm vi):**
- Không tự sửa bản đồ.
- Không chạy ERC sau công cụ chỉ-đọc.
- Không đổi `kiem_chung.py`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-10-01 | Tích hợp | tests/test_erc_tu_dong.py::test_net_set_gay_loi_chan_thi_ket_qua_co_erc_moi | cờ bật (monkeypatch env); tạo khối và net gây `trung_dia_chi` hoặc `xung_dau_ra`; gọi `registry.run("ckm.net_set")` rồi `a.hooks.post_tool_use(call,res,ctx)` → `res.data["erc_moi"]` có 1 phần tử |
| TC-M3-10-02 | Ca âm | tests/test_erc_tu_dong.py::test_loi_cu_khong_bao_lai | gọi `ckm.net_set` lần hai (không đổi gì) → `erc_moi` rỗng hoặc không có khoá |
| TC-M3-10-03 | Tích hợp (ScriptedGateway) | tests/test_erc_tu_dong.py::test_stop_cho_them_vong_khi_con_loi_moi_chua_nhac | kịch bản: gọi `ckm.net_set` gây lỗi rồi trả lời "xong" không nhắc lỗi → có đúng 1 vòng thêm với injection chứa tên luật; kịch bản hết thì dừng tự nhiên |
| TC-M3-10-04 | Ca biên | tests/test_erc_tu_dong.py::test_sua_3_lan_cung_loi_thi_doi_ask_user | đặt `ctx.erc_lan_sua[k]=3` → injection chứa "ask_user" |
| TC-M3-10-05 | Cờ TẮT | tests/test_erc_tu_dong.py::test_co_tat_hook_khong_cham_ket_qua | cờ tắt → `"erc_moi" not in res.data`, `stop` không cho thêm vòng |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py tests/test_loop.py tests/test_tu_phat_hien_sai.py tests/test_hooks*.py`

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc. Trước khi bật mặc định: eval 76 ca và phát lại không tụt; đo số blocker còn lại lúc kết lượt.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** tắt cờ.

<!-- TASK M3-12 -->
<a id="m3-12"></a>
### [M3-12] Mô phỏng HDL: đọc PASS/FAIL chặt, chỉ từ log chạy, tính cả mã thoát và `$fatal` — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #14

**Mục tiêu:** `hdl.sim` không còn báo PASS giả (chữ "BYPASS", tên tệp có "pass", log biên dịch) và không bỏ sót `$fatal`, assertion hay mã thoát khác 0.
**Loại:** Sửa lỗi thuần (ô xanh giả)
**Phụ thuộc:** Liên quan M4-16 (khung chung chống ô xanh giả). Nhiệm vụ này chỉ sửa phần HDL, không làm lại phần chung.
**Tệp chạm tới:** `src/eide/build/hdl.py`, `tests/test_hdl.py`

**Hiện trạng (đã kiểm lại trong mã):**
- hdl.py:466–470: `kq.nguyen_van = (kq.nguyen_van + "\n" + kq2.nguyen_van)`, tức log biên dịch iverilog/verilator cộng log chạy vvp/sim. `kq.ma_thoat = kq2.ma_thoat`.
- hdl.py:496–498: `tren = kq.nguyen_van.upper(); co_pass, co_fail = "PASS" in tren, "FAIL" in tren; kq.dat = co_pass and not co_fail`. Dò chuỗi con, không xét `ma_thoat`, không xét FATAL/ERROR/assertion.
- `kq2.vi_sao_khong_dat` (ví dụ quá hạn) không được chép sang `kq`.

**Thay đổi cần làm:**
1. Thêm hàm thuần `doc_ket_qua_tb(log_chay: str, ma_thoat: int|None) -> dict` trả `{pass_fail, so_pass, so_fail, ly_do}`:
   - Dòng PASS/FAIL hợp lệ: `^\s*(?:TEST\s+\S+\s+)?(PASS|FAIL)\b`, không phân biệt hoa thường, so khớp theo từng dòng.
   - Dấu hỏng: `^\s*(FATAL|ERROR)\b|%Error|Assertion failed|\$fatal`.
   - `dat` = so_pass ≥ 1, so_fail = 0, không có dấu hỏng, và `ma_thoat == 0`.
2. `mo_phong` chỉ gọi hàm này trên `kq2.nguyen_van` (log chạy) và `kq2.ma_thoat`. Nếu `kq2.vi_sao_khong_dat` có giá trị thì chép sang. Thêm `so_ca_pass` và `so_ca_fail` vào `KetQuaHdl` cùng `to_dict()`.
3. Câu `vi_sao_khong_dat` mới cho ca "PASS nhưng mã thoát ≠ 0" và ca "có FATAL/assertion".

**Không được làm (giới hạn phạm vi):**
- Không đổi giao thức tối thiểu: testbench chỉ in một dòng `PASS` vẫn đạt (`TB_PASS`).
- Không đổi khoá `pass_fail` hay `dat` trong `to_dict()`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-12-01 | Đơn vị (không cần iverilog) | tests/test_hdl.py::test_sim_BYPASS_khong_phai_PASS | monkeypatch `H._tim_lenh`: `iverilog` giả là script `: > "$3"` (tạo tệp `-o`), `vvp` giả in "bypass mode on" rồi thoát 0 → `not kq.dat`, `pass_fail==""` |
| TC-M3-12-02 | Đơn vị | tests/test_hdl.py::test_sim_PASS_nhung_ma_thoat_1_thi_khong_dat | `vvp` giả in "PASS", thoát 1 → `not kq.dat`, `vi_sao_khong_dat` có "mã thoát" |
| TC-M3-12-03 | Đơn vị | tests/test_hdl.py::test_sim_PASS_roi_FATAL_thi_khong_dat | `vvp` giả in "PASS\nFATAL: assertion" thoát 0 → không đạt |
| TC-M3-12-04 | Đơn vị | tests/test_hdl.py::test_sim_ten_tep_pass_trong_log_bien_dich_khong_tinh | `iverilog` giả in "warning: pass_through.v:3" và tạo tệp; `vvp` không in gì → không đạt |
| TC-M3-12-05 | Hồi quy | tests/test_hdl.py::test_sim_doc_PASS_tu_testbench, test_sim_in_FAIL_thi_KHONG_dat (đã có, `can_iv`) | vẫn xanh |
| TC-M3-12-06 | Đơn vị | tests/test_hdl.py::test_doc_ket_qua_tb_dem_ca | log "TEST a PASS\nTEST b PASS" → `so_pass==2` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py tests/test_hdl_cay.py`
- `test_sim_khong_in_gi_thi_KHONG_dat`: chữ "testbench" vẫn có trong lý do.

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ (khôi phục `"PASS" in tren` thì TC-01/04 đỏ).
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-13 -->
<a id="m3-13"></a>
### [M3-13] `hdl.sensitivity`: đo độ nhạy testbench Verilog bằng đột biến thật — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #15

**Mục tiêu:** Độ nhạy của testbench HDL được ĐO bằng mã và lưu vào `build:hdl:sim`, thay cho con số tác tử tự khai qua tham số `do_nhay`.
**Loại:** Công cụ mới (`core=False`) + sửa lỗi thuần (đánh dấu con số tự khai)
**Phụ thuộc:** M3-12 (đọc PASS/FAIL đúng là điều kiện để đo). Liên quan M4-16: phần chung về đột biến không làm lại.
**Tệp chạm tới:** `src/eide/build/dot_bien.py`, `src/eide/tools/hdl.py`, `tests/test_dot_bien.py`, `tests/test_hdl.py`

**Hiện trạng (đã kiểm lại trong mã):**
- tools/hdl.py:123 tham số `do_nhay {bat, tong}` do tác tử tự điền; `hdl_sim` chép thẳng vào `kq.do_nhay`.
- build/dot_bien.py:44 `_PHEP` là các phép kiểu C. `dot_bien_van_ban(ma, phep)` và `do_do_nhay(nguon, chay, toi_da_phep=3)` (:77) dùng `_PHEP` cố định. `_BO_QUA` bỏ qua chuỗi, chú thích và `#include`.
- tools/xay_dung.py:738 `test.sensitivity` chỉ lấy `firmware/*.c` và chạy test C.
- `do_do_nhay` ghi đè tệp rồi trả lại trong `finally` (dot_bien.py: `p.write_text(goc)`), nên dùng được cho `.v`.

**Thay đổi cần làm:**
1. `dot_bien_van_ban(ma, phep=0, bang=_PHEP)` và `do_do_nhay(..., bang=_PHEP)`: thêm tham số bảng phép, mặc định giữ nguyên.
2. Thêm `PHEP_VERILOG`:
   - đảo điều kiện `if (X)` thành `if (!(X))`;
   - đổi ` & ` thành ` | `;
   - đổi hằng `\d+'d\d+` (+1);
   - đổi `posedge` thành `negedge`;
   - đổi `==` thành `!=`.
   Vùng bỏ qua thêm `$display(...)`, chuỗi và `//`.
3. `H.do_do_nhay_hdl(goc, rtl: list[Path], tb_dir, dinh, bo_may)`: `chay(p)` = `mo_phong(...)` trên thư mục gồm RTL đã đột biến; trả `(kq.dat, kq.nguyen_van)`.
4. Công cụ `hdl.sensitivity(nguon_rtl: list[str], tb: str, dinh: str, bo_may="iverilog")` (R1, `core=False`, mô tả ≤ 400 ký tự): ghi `do_nhay={"bat": so_thay, "tong": so_thay+so_khong_thay, "do_bang": "ma"}` vào `build:hdl:sim` (dùng `_ghi_kho`).
5. Trong `hdl.sim`: khi tác tử tự điền `do_nhay`, lưu kèm `"do_bang": "tu_khai"`. Khối hiển thị A8.0 (surfaces.py:555) ghi "tự khai" nếu `do_bang != "ma"`.

**Không được làm (giới hạn phạm vi):**
- Không đổi kết quả `test.sensitivity` cho C (giữ `_PHEP` mặc định).
- Không để tệp RTL ở trạng thái đột biến khi có ngoại lệ.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-13-01 | Đơn vị | tests/test_dot_bien.py::test_phep_verilog_dao_if_khong_dung_display | `if (a) $display("if (x)");` → chỉ đảo `if (a)`, chuỗi giữ nguyên |
| TC-M3-13-02 | Đơn vị | tests/test_dot_bien.py::test_bang_mac_dinh_y_nhu_cu | `dot_bien_van_ban(ma_c, 1)` cho kết quả như trước khi sửa |
| TC-M3-13-03 | Tích hợp (`can_iv`) | tests/test_hdl.py::test_hdl_sensitivity_bo_kiem_that_bat_duoc | RTL bộ đếm + tb kiểm giá trị cụ thể → `so_thay==1` |
| TC-M3-13-04 | Ca âm (`can_iv`) | tests/test_hdl.py::test_hdl_sensitivity_tb_chi_in_PASS_thi_khong_thay | tb in PASS vô điều kiện → `so_khong_thay==1` |
| TC-M3-13-05 | Đơn vị | tests/test_hdl.py::test_do_nhay_tu_khai_duoc_danh_dau | `hdl.sim` với `do_nhay` tự điền → kho có `do_bang=="tu_khai"` |
| TC-M3-13-06 | Ca biên | tests/test_dot_bien.py::test_tra_tep_ve_nguyen_ven_khi_chay_nem_loi | `chay` ném lỗi → tệp `.v` giống hệt ban đầu |

**Ba TC thêm khi chốt** (phép phá rộng hơn tìm ra hai chỗ **không có ca nào canh** — xem
DEV-344; TC-06 cũng nằm ở tệp khác tên khác so với bảng trên, vì vòng đột biến là của
`dot_bien`, không phải của `hdl`):

| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-13-07 | Đơn vị | tests/test_hdl.py::test_A8_do_nhay_do_bang_ma_noi_dung_mau_so_la_TEP | `do_bang=="ma"` → nhãn A8.0 nói "tệp RTL", KHÔNG nói "phép phá mã" |
| TC-M3-13-08 | Tích hợp (`can_iv`) | tests/test_hdl.py::test_hdl_sensitivity_dung_bang_VERILOG_khong_phai_bang_C | RTL chỉ phá được bằng `posedge` → `so_thay==1` **và** lý do là phép đổi sườn |
| TC-M3-13-09 | Ca âm (`can_iv`) | tests/test_hdl.py::test_hdl_sensitivity_tu_choi_khi_bo_kiem_DO_tu_truoc | tb in `FAIL` ngay → công cụ trả `ok=False` mã `E4030`, **và kho không bị ghi** |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_dot_bien.py tests/test_hdl.py tests/test_xay_dung*.py`
- `test_do_nhay_di_theo_hien_vat_khong_chi_tra_cho_mo_hinh` giữ nguyên (vẫn lưu `bat`/`tong`).
  **Đã phải nới**: ca này chốt cứng cả dict `do_nhay` nên thêm khoá `do_bang` là đỏ; nay nó
  kiểm `bat`/`tong` có vào kho, không so cả dict.

**Tiêu chí xong:**
- [x] TC xanh, phá lại thì đỏ. — 9 chỗ sửa, **9/9 đỏ** (lượt đầu 7/9, xem DEV-344)
- [x] `pytest -q` xanh, ≥ mốc. — 1732 → **1744 xanh, 0 đỏ**
- [x] Ghi DEV-LOG. — **DEV-344**

**Hoàn tác:** revert commit.

<!-- TASK M3-18 -->
<a id="m3-18"></a>
### [M3-18] Kiểm ràng buộc chân FPGA (`.cst`) với cổng mô-đun đỉnh và chân của kit — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #16

**Mục tiêu:** Trước khi đặt-đi dây, mọi cổng của mô-đun đỉnh đều có `IO_LOC`; không có ràng buộc thừa hay trùng chân; chân được đối chiếu với Fact chân của kit; lệch thì không đi tiếp.
**Loại:** Sửa lỗi thuần (bitstream "đạt" nhưng sai chân) + công cụ mới (`core=False`)
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/knowledge/cst.py` (mới), `src/eide/build/hdl.py`, `src/eide/tools/hdl.py`, `tests/test_cst.py` (mới), `tests/test_hdl.py`

**Hiện trạng (đã kiểm lại trong mã):**
- hdl.py:556 `dat_di_day` chỉ kiểm `cst.exists()`. grep `IO_LOC|doc_cst` trong `src/` không ra gì.
- Hằng `CST` trong tests/test_hdl.py có `IO_LOC "clk" 4;`, `IO_PORT "clk" IO_TYPE=LVCMOS33 …`, `IO_LOC "led[0]" 15;` … `led[5]` 20.
- Tệp JSON yosys `.eide/hdl/<dinh>.json` có `modules[<dinh>].ports` (tên, hướng, `bits`).

**Thay đổi cần làm:**
1. `cst.doc_cst(chu) -> dict`: `{"loc": {ten: chan}, "io": {ten: {IO_TYPE,...}}, "loi_cu_phap": [dong]}`. Tên dạng `led[0]` được giữ nguyên.
2. `cst.cong_tu_json(json_path, dinh) -> list[str]`: tách bus thành `ten[i]` theo `bits` (bus 1 bit giữ tên trần).
3. `cst.kiem(cst, cong, fact_chan_kit: dict[str, dict]) -> list[dict]` sinh các phát hiện:
   - `thieu_rang_buoc`: cổng không có `IO_LOC`, blocker.
   - `rang_buoc_thua`: IO_LOC cho tên không phải cổng, major.
   - `trung_chan`: hai tên cùng một chân, blocker.
   - `chan_lech_kit`: Fact `pin:<kit>.<so>` có `chuc_nang` (vd LED0) mà tên cổng gán vào nó không khớp mẫu khai báo, major kèm trích dẫn.
   - `io_type_lech_bank`: Fact `bank.<n>.vccio` khác điện áp ngầm của IO_TYPE, blocker.
4. `dat_di_day` gọi `cst.kiem` trước nextpnr. Có blocker thì trả không đạt với `vi_sao_khong_dat` liệt kê. Thêm tham số `bo_qua_kiem_cst=False` (dành cho test cũ và trường hợp đặc biệt).
5. Công cụ `hdl.constraints_check(dinh, cst, bo_kit)` (R1, `core=False`) chạy riêng phần kiểm; Fact kit tra bằng `ctx.store.query_facts(subject=f"pin:{bo_kit}.")`.

**Không được làm (giới hạn phạm vi):**
- Không tự sửa tệp `.cst`.
- Không bịa bản đồ chân kit: thiếu Fact thì bỏ phần đối chiếu kit và ghi "chưa có Fact chân kit".

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-18-01 | Đơn vị | tests/test_cst.py::test_doc_cst_mau | `doc_cst(CST)` → `loc["led[5]"]=="20"`, `io["clk"]["IO_TYPE"]=="LVCMOS33"` |
| TC-M3-18-02 | Đơn vị | tests/test_cst.py::test_cong_thieu_rang_buoc_bi_chan | cổng `clk, led[0..5], uart_tx`, CST mẫu → `thieu_rang_buoc` cho `uart_tx` |
| TC-M3-18-03 | Đơn vị | tests/test_cst.py::test_trung_chan_bi_chan | thêm `IO_LOC "x" 15;` và `x` là cổng → `trung_chan` |
| TC-M3-18-04 | Ca âm | tests/test_cst.py::test_cst_khop_khong_bao | cổng đúng như CST mẫu, không có Fact kit → không có blocker |
| TC-M3-18-05 | Tích hợp | tests/test_hdl.py::test_pnr_tu_choi_khi_cst_thieu_cong | JSON giả có cổng `uart_tx`, `_tim_lenh` giả → `dat_di_day` không đạt trước khi gọi nextpnr; lý do nêu `uart_tx` |

**Mười một TC thêm khi làm** (phép phá rộng tìm ra hai chỗ không ai canh; và phần "chạy trên
hiện vật thật" không có trong bảng kế hoạch — xem DEV-345):

| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-18-06 | Đơn vị | tests/test_cst.py::test_rang_buoc_thua_bi_bao_major | ràng buộc cho tên không phải cổng → `major`, KHÔNG chặn |
| TC-M3-18-07 | Đơn vị | tests/test_cst.py::test_cong_tu_json_tach_bus | JSON có `led` 6 bit → `led[0]`…`led[5]` |
| TC-M3-18-08 | Ca biên | tests/test_cst.py::test_cong_tu_json_khong_co_mo_dun_dinh | thiếu mô-đun đỉnh → ném `KeyError`, KHÔNG trả rỗng |
| TC-M3-18-09 | Đơn vị | tests/test_cst.py::test_doc_cst_noi_ra_dong_khong_doc_duoc | 2 dòng sai cú pháp → cả 2 vào `loi_cu_phap` |
| TC-M3-18-10 | Đơn vị | tests/test_cst.py::test_doc_cst_bo_qua_chu_thich | `IO_LOC` nằm sau `//` không được tính là còn hiệu lực |
| TC-M3-18-11 | Đơn vị | tests/test_cst.py::test_chan_lech_kit_bao_major_kem_trich_dan + `test_chan_khop_fact_kit_thi_im` | Fact nói chân 15 là LED0 mà gán `clk` → `chan_lech_kit` kèm Fact |
| TC-M3-18-12 | Đơn vị | tests/test_cst.py::test_io_type_lech_bank_bi_chan + `test_io_type_khop_bank_thi_im` | `LVCMOS18` trên bank 3,3 V → blocker |
| TC-M3-18-13 | **Hiện vật thật** | tests/test_cst.py::test_doc_duoc_moi_cst_that_trong_repo | cả 7 tệp `.cst` thật trong repo → đọc hết, 0 dòng sai cú pháp (bản đầu của phép quét chỉ thu 4/7 — xem DEV-345) |
| TC-M3-18-14 | **Hiện vật thật** | tests/test_cst.py::test_cst_that_khop_cong_cua_soc_top_that | `soc_top` thật + `.cst` thật → 0 blocker, đúng 2 ràng buộc thừa |
| TC-M3-18-15 | Ca biên | tests/test_hdl.py::test_pnr_tu_choi_khi_mang_cong_khong_doc_duoc | JSON hỏng → không đạt, KHÔNG gọi nextpnr |
| TC-M3-18-16 | Ca biên | tests/test_hdl.py::test_pnr_tu_choi_khi_mang_cong_khong_co_mo_dun_dinh | mạng cổng có mô-đun KHÁC → không đạt, nêu cả tên đang có |
| TC-M3-18-17 | Tích hợp | tests/test_hdl.py::test_constraints_check_* (4 ca) | công cụ qua sổ: báo cổng thiếu · từ chối `E4033` · ca âm nói ra đã bỏ phần kit · **Fact trong kho tới được luật** |
| TC-M3-18-18 | Cửa thoát | tests/test_hdl.py::test_pnr_bo_qua_kiem_cst_khi_duoc_yeu_cau | `bo_qua_kiem_cst=True` → có gọi nextpnr; mặc định vẫn `False` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py tests/test_cst.py`
- `test_pnr_bao_fmax_va_muc_dung_that` và `test_duong_fpga_di_het_voi_tep_that` (cổng `blinky` khớp CST mẫu) giữ nguyên. **Đã kiểm: cả hai vẫn xanh, không phải nới gì.**

**Lệch khỏi kế hoạch (đo rồi mới thấy):**
- Mã lỗi `E4033`, **không** `E4031`: `loop.py:1085` đã dùng `E4031` cho "chưa chạy, vì chờ cổng".
- Khoá Fact chân kit: kế hoạch ghi `chuc_nang`, mã đang ghi `ten`/`net`/`af`. Nhận cả ba.
- `chan_lech_kit` và `io_type_lech_bank` **chưa có dữ liệu để nổ**: không kho nào trong repo có
  Fact `pin:tangnano20k.*` hay khoá `vccio`. Có ca kiểm, có đường dẫn đã đo — nhưng hôm nay
  chỉ 3 trong 5 luật kết luận được gì trên dữ liệu thật.

**Tiêu chí xong:**
- [x] TC xanh, phá lại thì đỏ. — 20 chỗ phá, **20/20 đỏ** (lượt đầu 18/20, xem DEV-345)
- [x] `pytest -q` xanh, ≥ mốc. — 1744 → **1773 xanh, 0 đỏ** (+29 ca)
- [x] Ghi DEV-LOG. — **DEV-345**

**Hoàn tác:** revert; hoặc `bo_qua_kiem_cst=True`.

<!-- TASK M4-01 -->
<a id="m4-01"></a>
### [M4-01] Máy chấm unit test do EIDE phán (`test.criteria`) — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #17

**Mục tiêu:** Ca unit test có thể được EIDE phán bằng ngưỡng nêu trước (giống `sim.run`) thay vì chương trình test tự in `dat:true`.
**Loại:** Công cụ mới
**Phụ thuộc:** Không
**Tệp chạm tới:** src/eide/build/mo_phong.py, src/eide/build/tieu_chi.py (dùng lại, không đổi ngữ nghĩa), src/eide/tools/xay_dung.py, tests/test_test_tieu_chi.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- build/mo_phong.py:438-446 `chay_test` — `kq.so_dat = sum(1 for x in kq.ca if x.get("dat") is True)`: tệp test tự khai đạt.
- build/tieu_chi.py:294 `xet_ket_qua(tc, do)` — máy phán theo `Assert` đang chỉ dùng cho sim.run (tools/xay_dung.py:~660).
- tools/xay_dung.py:802-886 `test_run` không đọc tiêu chí nào; `MA_TEST = "sim_result:unit-test"`.

**Thay đổi cần làm:**
1. Công cụ `test.criteria` (core=False, risk R2, writes_artefact, needs_explain, produces ["criteria"]), lược đồ giống `sim.criteria` nhưng ghi hiện vật `criteria:unit-<ma>` (mặc định `unit-01`), dùng lại `TieuChi`/`Assert`. Mô tả ≤400 ký tự.
2. `chay_test(..., tieu_chi: TieuChi | None = None)`: khi có tiêu chí VÀ dòng JSON cuối có khoá `do` thì gọi `xet_ket_qua(tieu_chi, do)`, lấy `ca` từ `xet["dong"]` (ten=ma, dat=ket_luan=="dat", vi=vi), và gắn `che_do="eide_phan"`. Không có tiêu chí thì giữ nguyên cách cũ, gắn `che_do="tu_khai"`.
3. `test_run(..., ma_tieu_chi: str = "")`: nếu nêu mã mà hiện vật chưa có hoặc chưa xác nhận thì trả E4008/E4009 (dùng lại mã của sim.run). Có tiêu chí mà test vẫn in `ca` (tự khai) thì trả E4024 "test in tự khai trong khi đã có tiêu chí", kèm khuôn `{"do":{...}}`.
4. `note_vi` của test.run nói rõ chế độ: "EIDE phán theo tiêu chí unit-01" hoặc "test TỰ KHAI đạt — độ tin DONG".

**Không được làm (giới hạn phạm vi):**
- Không đổi `KHUON_RA` cũ, không bắt buộc tiêu chí cho test.run (tương thích ngược với ~6 ca trong test_xay_dung).
- Không sửa `xet_ket_qua`/`Assert.xet`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-01-01 | Đơn vị (skipif không có cc) | tests/test_test_tieu_chi.py::test_chay_test_co_tieu_chi_thi_EIDE_phan | TieuChi T1 "<=255"; test in `{"do":{"T1":300}}` → chay_test(tieu_chi=tc) → so_hong==1, che_do=="eide_phan", vi chứa "300" |
| TC-M4-01-02 | Ca âm | …::test_tu_khai_dat_nhung_co_tieu_chi_thi_tu_choi | criteria:unit-01 đã xác nhận; test in `{"ca":[{"ten":"a","dat":true}]}`; gọi test.run(ma_tieu_chi="unit-01") → not ok, code E4024 |
| TC-M4-01-03 | Tích hợp registry | …::test_test_criteria_chua_xac_nhan_thi_test_run_tu_choi | test.criteria không có trich_loi → test.run(ma_tieu_chi="unit-01") → E4009 |
| TC-M4-01-04 | Ca âm "không kêu nhầm" | …::test_khong_neu_tieu_chi_thi_hanh_vi_y_cu | Không có tiêu chí; test in `ca` dat true → ok, so_dat==1, che_do=="tu_khai" |
| TC-M4-01-05 | Lược đồ | …::test_test_criteria_dang_ky_core_false_mo_ta_ngan | build_registry().get("test.criteria") → core False, len(summary_vi)≤400 |

**Mười ba TC thêm khi làm** (phép phá dựng từ `git diff` tìm ra bảy chỗ không ai canh — xem
DEV-346; tất cả nằm trong `tests/test_test_tieu_chi.py`):

| Mã TC | Loại | Tên ca | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-01-06 | Ca biên | test_tieu_chi_KHONG_CO_ASSERT_nao_thi_noi_ra_chu_khong_bao_0_ca | tiêu chí rỗng assert → nói "chưa có assert nào", KHÔNG báo "0 ca" |
| TC-M4-01-07 | Ca âm | test_co_tieu_chi_ma_test_khong_in_so_do_thi_CHUA_DO_DUOC | có tiêu chí, `do` rỗng → chưa-đo-được, KHÔNG lùi về đếm `ca` |
| TC-M4-01-08 | Sở cứ | test_hien_vat_mang_theo_MA_TIEU_CHI_da_phan | hiện vật mang `ma_tieu_chi` + `so_do`, không chỉ mang chữ "đã phán" |
| TC-M4-01-09 | Sở cứ | test_E4024_tu_choi_TRUOC_khi_ghi_kho | từ chối E4024 → `sim_result:unit-test` KHÔNG tồn tại |
| TC-M4-01-10 | Ca âm | test_so_do_khong_khop_MOT_ma_assert_nao_thi_tu_choi_E4023 | tiêu chí đòi T1, test đo X9 → E4023 "KHÔNG phải sản phẩm sai" |
| TC-M4-01-11 | Đơn vị | test_assert_thieu_mo_ta_thi_tu_choi_E4007 | thiếu `ma` hoặc `mo_ta` → E4007; canh hộ cả `sim.criteria` (helper dùng chung) |
| TC-M4-01-12 | **Bề mặt** | test_tab_A8_dong_KET_LUAN_noi_ra_con_so_la_TU_KHAI | dòng *Kết luận* của khối A8.1 nói "TỰ KHAI", và có dòng "Độ tin … ĐỎ" |
| TC-M4-01-13 | **Bề mặt** | test_tab_A8_dong_KET_LUAN_noi_ra_con_so_do_EIDE_phan | dòng *Kết luận* nói "EIDE phán" + mã tiêu chí; KHÔNG dán cảnh báo độ tin |
| TC-M4-01-14 | **Bề mặt** | test_tab_A8_tieu_chi_unit_khong_bi_goi_la_tieu_chi_mo_phong | `criteria:unit-01` hiện là "Tiêu chí unit test", không hứa chặn mô phỏng |
| TC-M4-01-15 | Tương thích | test_test_run_khong_neu_tieu_chi_thi_note_noi_la_TU_KHAI | không nêu mã → vẫn chạy, `note_vi` nói "TỰ KHAI" |
| TC-M4-01-16 | Tích hợp | test_test_run_co_tieu_chi_thi_EIDE_phan_va_note_noi_ro_che_do | đường đầy đủ qua công cụ → `che_do="eide_phan"`, note nêu mã tiêu chí |
| TC-M4-01-17 | Ca âm | test_neu_ma_tieu_chi_chua_he_co_thi_tu_choi_E4008 | mã chưa tồn tại → E4008, `alternatives` có `test.criteria` |
| TC-M4-01-18 | An toàn kho | test_test_criteria_khong_the_de_len_tieu_chi_cua_sim | `test.criteria(ma="sim-01")` KHÔNG ghi đè `criteria:sim-01` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_xay_dung.py tests/test_dot_bien.py tests/test_policy_tools.py`
- test_test_run_dem_duoc_CA_DAT_va_CA_HONG, test_test_run_KHONG_in_JSON_thi_khong_ket_luan (E4014) giữ nguyên.
  **Đã kiểm: không ca cũ nào phải nới.** Sáu ca `test.run` cũ đi đường không-tiêu-chí.

**Lệch khỏi kế hoạch (đo rồi mới thấy):**
- Thêm cổng **E4023** cho đường unit test (kế hoạch chỉ nêu E4008/E4009/E4024). Cùng cái bẫy
  DEV-336 ở `sim.run`, và ở đây dễ trúng hơn vì `nguon` bỏ trống lấy MỌI tệp `test/*.c`.
- E4024 phải từ chối **trước** khi ghi kho, không thì hiện vật giữ `che_do="eide_phan"` cho
  một lượt tự khai.
- Phải sửa cả `surfaces.py` (ngoài danh sách "tệp chạm tới"): `test.run` ghi vào loại
  `sim_result` nên nó hiện ở khối của `sim.run`, và dòng *Kết luận* ở đó nói "theo đúng tiêu
  chí mà chương trình mô phỏng tự kiểm" cho **mọi** lượt. Chế độ chỉ nằm ở `note_vi` thì
  không tới người đọc.
- Phần kiểm assert tách thành `_kiem_assert` dùng chung với `sim.criteria` — một bản sao thứ
  hai sẽ lệch.

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ" từng TC. — 24 chỗ phá, **24/24 đỏ** (lượt đầu 17/24)
- [x] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc. — 1773 → **1791 xanh, 0 đỏ**
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md. — **DEV-346**

**Hoàn tác:** revert commit (công cụ mới core=False, không ai gọi tới khi tool.search).

<!-- TASK M4-02 -->
<a id="m4-02"></a>
### [M4-02] Cổng G-QUAL khi sửa/xoá tệp test sau kết quả đỏ + sửa `criteria.has_result` — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #18

**Mục tiêu:** Sửa yếu tệp test/testbench sau khi đã có kết quả ĐỎ phải đi qua thẻ người, và `has_result` đúng với mọi mã tiêu chí.
**Loại:** Sửa lỗi thuần (đi vòng hàng rào N6/TC022) — riêng phần siết công cụ của sim-runner đặt sau cờ `EIDE_FEATURE_SIM_RUNNER_GIOI_HAN`, mặc định TẮT
**Phụ thuộc:** Không (M4-01 làm trước thì kiểm thêm criteria:unit-*)
**Tệp chạm tới:** src/eide/hooks/standard.py, src/eide/policy/policy.yaml, src/eide/subagent.py, src/eide/config.py (cờ), tests/test_test_bi_sua_yeu.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- hooks/standard.py:185-222 `doi_tieu_chi` — chỉ xét `sim.criteria`; dòng 216 `co_kq = ctx.store.get("sim_result:can-bang") is not None` cứng mã hiện vật.
- policy.yaml POL-QUAL-criteria-change / POL-N6-doi-tieu-chi chỉ có `tool: "sim.criteria"`; POL-FILE-overwrite-human cho `fs.write|fs.edit` chỉ xét sửa của người.
- subagent.py:106 sim-runner có `fs.write` trong `cong_cu`.

**Thay đổi cần làm:**
1. `doi_tieu_chi`: thay dòng 216 bằng tra các `sim_result` có `canonical.ma_tieu_chi == ma` (dùng `ctx.store.list("sim_result")`), fallback `sim_result:can-bang` khi `ma=="sim-01"`.
2. Hook pre_tool mới `sua_test_sau_do` cho `fs.write|fs.edit`: đường dẫn khớp `test/**`, `tests/**`, `sim/**`, `*_tb.v`, `tb_*.v` VÀ có hiện vật kết quả `dat=False` (MA_TEST, MA_SIM, `build:hdl:sim`). Đếm số ca/assert trước–sau (đếm `"dat"`, `"ma"` trong JSON in ra, `$display("FAIL`, `assert`) trên nội dung cũ trên đĩa và nội dung mới (`content`, hoặc áp `old`→`new` với fs.edit), rồi phát facts `test.weakened` (bool) và `test.doi_gi` ("3 ca → 1 ca", "xoá FAIL dòng 42").
3. policy.yaml: thêm `POL-N6-sua-test` với tool `fs.write|fs.edit`, when `test.weakened`, action ask, gate G-QUAL, never_auto, principle N6, ca_do [TC022].
4. Cờ `sim_runner_gioi_han` trong `Features` (+`ten_co()`): bật thì `subagent.chay` từ chối `fs.write` của sim-runner ngoài `sim/` (E5006, kèm lời chỉ dẫn).

**Không được làm (giới hạn phạm vi):**
- Không chặn tạo tệp test MỚI (chưa có kết quả thì không có gì để ép).
- Không đổi khoá facts cũ `criteria.*`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-02-01 | Đơn vị hook | tests/test_test_bi_sua_yeu.py::test_has_result_theo_ma_tieu_chi | criteria:sim-ntc + sim_result có ma_tieu_chi="sim-ntc" (không có can-bang) → pre_tool_use sim.criteria(ma="sim-ntc", đổi ngưỡng) → facts["criteria.has_result"] is True |
| TC-M4-02-02 | Đơn vị hook | …::test_xoa_ca_test_sau_ket_qua_do_thi_weakened | MA_TEST dat=False; test/t.c in 3 ca; fs.write nội dung chỉ 1 ca → facts["test.weakened"] True, "3" và "1" trong test.doi_gi |
| TC-M4-02-03 | Tích hợp policy | …::test_policy_hoi_G_QUAL_khi_test_bi_sua_yeu | như 02 → policy.decide trả ask với gate G-QUAL (dùng cách gọi policy như tests/test_policy_tools.py) |
| TC-M4-02-04 | Ca âm | …::test_tao_test_moi_hoac_chua_co_ket_qua_thi_KHONG_keu | không có MA_TEST, hoặc MA_TEST dat=True → test.weakened False |
| TC-M4-02-05 | Cờ TẮT | …::test_co_tat_sim_runner_van_ghi_duoc_ngoai_sim | EIDE_FEATURE_SIM_RUNNER_GIOI_HAN chưa đặt; ScriptedGateway sim-runner gọi fs.write test/x.c → không có E5006 |

**Mười hai TC thêm khi làm** (phép phá dựng từ `git diff` tìm ra bốn chỗ không ai canh — xem
DEV-347; tất cả nằm trong `tests/test_test_bi_sua_yeu.py`):

| Mã TC | Loại | Tên ca | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-02-06 | Ca âm | test_has_result_khong_keu_cho_tieu_chi_KHAC | kết quả của `sim-ntc` KHÔNG làm `sim-01` thành có-kết-quả |
| TC-M4-02-07 | Tương thích | test_has_result_giu_duong_cu_cho_can_bang | `sim_result:can-bang` không khai `ma_tieu_chi` vẫn tính cho `sim-01` |
| TC-M4-02-08 | Cửa sau | test_has_result_cho_ca_tieu_chi_UNIT_TEST | `criteria:unit-*` (M4-01) cũng qua cổng N6 |
| TC-M4-02-09 | Quy ước khoá | test_has_result_ep_tien_to_unit_khi_tac_tu_chi_gui_so | `ma="01"` → hook tra `criteria:unit-01`, không tra `criteria:01` |
| TC-M4-02-10 | Cửa sau | test_fs_edit_xoa_dong_FAIL_cung_tinh_la_weakened | `fs.edit` phải được áp `old`→`new` rồi mới đếm |
| TC-M4-02-11 | Ca âm | test_them_ca_test_thi_KHONG_keu | 1 ca → 3 ca sau kết quả đỏ → KHÔNG hỏi |
| TC-M4-02-12 | Ca âm | test_so_cho_canh_KHONG_DOI_thi_khong_keu | đổi tên ca, số chỗ canh không đổi → KHÔNG hỏi |
| TC-M4-02-13 | **FPGA** | test_testbench_NGOAI_thu_muc_test_cung_duoc_canh | `rtl/tb_dem.v` cũng là tệp đo (dự án FPGA đặt tb cạnh RTL) |
| TC-M4-02-14 | Ca âm | test_ket_qua_DAT_thi_sua_test_khong_phai_hoi | kết quả đang XANH → sửa tệp test là việc thường |
| TC-M4-02-15 | Ca biên | test_tep_test_CHUA_CO_tren_dia_thi_khong_keu | tạo tệp test MỚI → không hỏi, và hook KHÔNG nổ |
| TC-M4-02-16 | **Luật** | test_policy_hoi_G_QUAL_khi_doi_nguong_UNIT_TEST | `test.criteria` + has_result → ask G-QUAL never_auto |
| TC-M4-02-17 | **Luật** | test_luat_moi_KHONG_lam_do_ca_luot_khi_hook_im | 4 công cụ, `pre` không có nhóm `test`/`criteria` → KHÔNG ném ValueError |
| TC-M4-02-18 | Cờ BẬT | test_co_BAT_thi_sim_runner_khong_ghi_duoc_ngoai_sim | ghi `test/` bị chặn, ghi `sim/` vẫn qua |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_xay_dung.py tests/test_policy_tools.py tests/test_subagent.py tests/test_s0.py`
- test_doi_NGUONG_khi_da_co_ket_qua_thi_hook_bao_cho_cong_G_QUAL và test_them_assert_MOI_cung_tinh_la_doi giữ nguyên.
  **Đã kiểm: cả hai vẫn xanh, không phải nới.**

**Lệch khỏi kế hoạch (đo rồi mới thấy):**
- Phải sửa cả `src/eide/policy/engine.py` (ngoài danh sách "tệp chạm tới"): `_env` có một
  danh sách "nhóm dữ kiện phải luôn tồn tại", và thiếu nhóm trong đó thì luật mới **dừng cả
  lượt** bằng `ValueError`, không phải "không nổ". Nhóm `criteria` cũng chưa bao giờ có trong
  danh sách ấy — hàng rào N6 cũ đang dựa vào thói quen tốt của một hook, không dựa vào một
  bảo đảm.
- `POL-QUAL-criteria-change` cũng phải liệt `test.criteria` (kế hoạch chỉ nêu
  `POL-N6-doi-tieu-chi`).
- Phép đo là *"yếu đi bao nhiêu"*, nên phải có thêm nhánh **số chỗ canh không đổi thì im** —
  kế hoạch không nêu, và không có nó thì mọi lần sửa chữ trong tệp test đều dựng một thẻ.

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ" từng TC. — 27 chỗ phá, **27/27 đỏ** (lượt đầu 22/27)
- [x] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc. — 1791 → **1816 xanh, 0 đỏ**
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md. — **DEV-347**

**Hoàn tác:** revert commit; riêng phần sim-runner thì tắt cờ.

<!-- TASK M4-05 -->
<a id="m4-05"></a>
### [M4-05] Đột biến không biên dịch được không được tính là "bắt được" — P1 · S

**Giai đoạn:** GĐ1 · thứ tự #19 (kéo lên từ GĐ2 vì là tiền đề của M4-06)

**Mục tiêu:** Một mutant làm lỗi biên dịch được xếp `khong_hop_le` (stillborn), không làm tệp thành `thay`.
**Loại:** Sửa lỗi thuần (ô xanh giả trong phép đo)
**Phụ thuộc:** Không
**Tệp chạm tới:** src/eide/build/dot_bien.py, tests/test_dot_bien.py

**Hiện trạng (đã kiểm lại trong mã):**
- dot_bien.py:145-153 — `dat, _ = chay(p)` bỏ log; `if not dat: thay_doi = True`, nên lỗi biên dịch cũng thành "thay".
- dot_bien.py:174 `_khong_dich_duoc(log)` chỉ được gọi ở bước nạp mã gốc (dòng 123).
- tools/xay_dung.py:783-790 `_chay` trả `(False, loi_bien_dich[-800:])` khi không biên dịch được, nên log có sẵn để phân biệt.

**Thay đổi cần làm:**
1. Trong vòng đột biến: `dat, log = chay(p)`; nếu `not dat and _khong_dich_duoc(log)` thì ghi_chu "… → mutant không dịch được (bỏ qua)", tăng biến đếm `khong_hop_le`, rồi `continue` sang phép kế.
2. Thêm `ra["so_mutant_khong_hop_le"]`. Tệp mà mọi phép đều stillborn thì trạng thái `chua_do_duoc` với lý do "mọi đột biến đều làm hỏng biên dịch".
3. Cẩn thận: `_DAU_HIEU_KHAC` có `"error:"`, nên `vi_sao_khong_dat` của ca test hỏng chứa chữ "error:" sẽ bị nhận nhầm. Chỉ coi là stillborn khi `_chay` báo không chạy được. Cách làm: `_chay` trả thêm cờ qua tuple 3 phần tử, hoặc gắn tiền tố `"[BIEN_DICH] "` vào log và chỉ kiểm tiền tố đó. Giữ tương thích hàm `chay` 2 phần tử trong test cũ.

**Không được làm (giới hạn phạm vi):**
- Không đổi chữ ký `do_do_nhay(nguon, chay, toi_da_phep)`.
- Không đổi phân loại `khong_nap_duoc` ở bước nạp mã gốc.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-05-01 | Đơn vị | tests/test_dot_bien.py::test_mutant_khong_dich_duoc_KHONG_tinh_la_thay | chay giả: mã gốc → (True,""); mã khác gốc → (False,"[BIEN_DICH] error: bit-field width") → trạng thái ≠ "thay", so_mutant_khong_hop_le ≥1 |
| TC-M4-05-02 | Ca âm | …::test_ca_test_hong_co_chu_error_van_la_thay | mutant → (False, "TC-01: error: mong 1 nhan 0") không tiền tố → vẫn "thay" |
| TC-M4-05-03 | Ca biên | …::test_moi_phep_deu_stillborn_thi_chua_do_duoc | mọi mutant trả lỗi biên dịch → "chua_do_duoc" |
| TC-M4-05-04 | Hồi quy | …::test_bo_kiem_that_thi_ra_thay (có sẵn) | giữ xanh |

**Mười lăm TC thêm khi làm** (ba lỗi nữa chỉ lộ ra khi CHẠY phép đo trên dữ liệu thật, và phép
phá tìm ra năm chỗ không ai canh — xem DEV-348; tất cả trong `tests/test_dot_bien.py`):

| Mã TC | Loại | Tên ca | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-05-05 | Ca biên | test_tien_to_BIEN_DICH_khong_doi_phan_loai_o_buoc_NAP | bước nạp giữ nguyên `khong_nap_duoc`, chưa đếm mutant |
| TC-M4-05-06 | Lược đồ | test_so_mutant_khong_hop_le_co_mat_ca_khi_bang_khong | khoá luôn có trong kết quả, kể cả khi 0 |
| TC-M4-05-07 | Người đọc | test_loi_nguoi_doc_NOI_RA_co_mutant_stillborn | đoạn cho người nói ra số mutant bị bỏ |
| TC-M4-05-08 | **Lỗi 4** | test_loi_nguoi_doc_khong_khen_khi_chua_do_duoc_tep_nao | `so_thay == 0` → "CHƯA ĐO ĐƯỢC", không "phá tệp nào cũng có ca đỏ" |
| TC-M4-05-09 | **Lỗi 2** | test_tep_co_HON_MUOI_chu_thich_van_dot_bien_duoc | tệp ≥10 chú thích → không `IndexError`, chú thích về nguyên vẹn |
| TC-M4-05-10 | Ca âm | test_chu_thich_khong_bi_dot_bien_ke_ca_khi_co_so_dai | số trong chú thích vẫn không bị đổi |
| TC-M4-05-11 | Đơn vị | test_ma_cho_giu_di_va_ve_khong_lech | `_ma_cho`/`_so_cho` song ánh trên 2000 giá trị |
| TC-M4-05-12 | **Lỗi 3** | test_mo_phong_KHONG_chay_lai_tep_sim_cu_khi_bien_dich_do | dịch đổ → `dat=False`, `pass_fail=""`, không đọc PASS của lượt trước |
| TC-M4-05-13 | Luật chung | test_ket_qua_chay_gan_tien_to_khi_co_loi_bien_dich | có `loi_bien_dich` → có tiền tố |
| TC-M4-05-14 | Luật chung | test_ket_qua_chay_KHONG_gan_tien_to_khi_QUA_HAN | quá hạn → KHÔNG tiền tố (mutant treo ≠ mutant không dịch được) |
| TC-M4-05-15 | Luật chung | test_ket_qua_chay_dat_thi_khong_bao_gio_gan_tien_to | đạt → không tiền tố |
| TC-M4-05-16 | **Đường thật** | test_test_sensitivity_dem_duoc_mutant_stillborn | công cụ THẬT trên `cc` thật → `so_mutant_khong_hop_le ≥ 1` |
| TC-M4-05-17 | **Đường thật** | test_do_do_nhay_hdl_dem_stillborn_tren_duong_THAT | `do_do_nhay_hdl` thật + bảng bơm vào → stillborn 1, `so_thay` 0 |
| TC-M4-05-18 | **Đường thật** | test_hdl_do_do_nhay_dem_duoc_mutant_stillborn | mutant DỊCH ĐƯỢC thì KHÔNG bị đếm là stillborn |
| TC-M4-05-19 | Báo lại | test_cong_cu_hdl_sensitivity_MANG_THEO_so_mutant_stillborn | công cụ mang con số ra cả ba chỗ: kết quả · kho · `note_vi` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_dot_bien.py`
- Bốn trạng thái cũ và ca "trả tệp về nguyên vẹn" giữ nguyên. **Đã kiểm: không phải nới ca nào.**

**Lệch khỏi kế hoạch (đo rồi mới thấy):**
- Phải sửa cả `src/eide/build/hdl.py`, `src/eide/tools/xay_dung.py`, `src/eide/tools/hdl.py`
  (kế hoạch chỉ ghi `dot_bien.py` + tests). Lý do: luật "khai lỗi biên dịch" phải do hàm
  `chay` phát ra, nên hai đường đo thật đều phải sửa — thiếu chúng thì cơ chế có sẵn mà không
  lượt đo nào đi qua nó.
- `mo_phong` phải gọi `_don_tep_ra(anh)` — không thì mutant hỏng cú pháp ở đường HDL **không
  bao giờ** trả `False` để mà phân loại. Tức Lỗi 3 là **tiền đề** của chính nhiệm vụ này.
- Mã chỗ giữ của `dot_bien_van_ban` phải đổi từ chữ số sang chữ hoa, không thì phép đo ĐỔ trên
  mọi tệp firmware thật.
- `do_do_nhay_hdl` nhận thêm tham số `bang` — năm phép `PHEP_VERILOG` đều hợp lệ về cú pháp
  nên không dựng nổi ca kiểm cho nhánh stillborn của đường HDL qua bảng mặc định.
- Luật gắn tiền tố gom về `dot_bien.ket_qua_chay` thay vì viết hai lần trong hai closure.

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ" từng TC. — 22 chỗ phá, **22/22 đỏ** (lượt đầu 15/20)
- [x] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc. — 1816 → **1835 xanh, 0 đỏ**
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md. — **DEV-348**

**Hoàn tác:** revert commit.

<!-- TASK M4-19 -->
<a id="m4-19"></a>
### [M4-19] Đột biến trên bản sao, không ghi đè tệp sản phẩm của người dùng — P2 · S

**Giai đoạn:** GĐ1 · thứ tự #20 (kéo lên từ GĐ4 vì là tiền đề của M4-04)

**Mục tiêu:** Đo độ nhạy không bao giờ ghi vào tệp gốc của dự án, kể cả khi tiến trình bị giết giữa chừng.
**Loại:** Sửa lỗi thuần (nguy cơ mất/hỏng dữ liệu)
**Phụ thuộc:** Không (M4-04, M4-12, M4-16 dựa trên nhiệm vụ này)
**Tệp chạm tới:** src/eide/build/dot_bien.py, src/eide/build/mo_phong.py, src/eide/tools/xay_dung.py, tests/test_dot_bien.py

**Hiện trạng (đã kiểm lại trong mã):**
- dot_bien.py:145-149 `p.write_text(moi_ma) … finally: p.write_text(goc)`: ghi đè tệp thật; chỉ an toàn với ngoại lệ Python (test_tra_tep_ve_nguyen_ven_ke_ca_khi_chay_no).
- mo_phong.py:369 `chay_test(goc, nguon, thu_muc_build, giay_toi_da, do_phu)`: không có tham số cờ biên dịch thêm (`-I`).

**Thay đổi cần làm:**
1. `chay_test(..., them_co: list[str] | None = None)` chèn vào lệnh biên dịch (sau `-DEIDE_TEST=1`).
2. `do_do_nhay(..., thu_muc_tam: Path | None = None)`: có `thu_muc_tam` thì với mỗi tệp `p` sao chép ra `thu_muc_tam/<p.name>`, đột biến bản sao, và gọi `chay(ban_sao)`. Tệp gốc chỉ được ĐỌC.
3. `test_sensitivity._chay(them)`: biên dịch `tep_test + [them]` với `them_co=["-I", str(p_goc.parent)]` để `#include "x.h"` tương đối vẫn tìm thấy. Truyền `thu_muc_tam = goc/".eide"/"mutate"/run_id`.
4. Giữ đường cũ (không có thu_muc_tam) cho tương thích test cũ, nhưng test.sensitivity luôn dùng đường mới.

**Không được làm (giới hạn phạm vi):**
- Không đổi phân loại bốn trạng thái.
- Không ghi `.eide/mutate` vào changeset/history.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-19-01 | Đơn vị | tests/test_dot_bien.py::test_tep_goc_KHONG_bi_ghi_trong_luc_do | chay giả kiểm `p_goc.read_text()==goc` ở MỌI lần gọi, thu_muc_tam=tmp → không lần nào sai |
| TC-M4-19-02 | Đơn vị | …::test_chay_nhan_ban_sao_khong_phai_tep_goc | chay ghi lại đối số → mọi đường dẫn mutant nằm dưới thu_muc_tam |
| TC-M4-19-03 | Tích hợp (skipif không có cc) | …::test_sensitivity_include_tuong_doi_van_dich_duoc | firmware/pid.c `#include "pid.h"` + test → test.sensitivity không ra khong_nap_duoc vì thiếu header |
| TC-M4-19-04 | Ca biên | …::test_mtime_tep_goc_khong_doi | mtime trước = sau khi test.sensitivity chạy |

**Bảy TC thêm khi làm** (phép phá tìm ra năm chỗ không ai canh — xem DEV-349; tất cả trong
`tests/test_dot_bien.py`):

| Mã TC | Loại | Tên ca | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-19-05 | Tương thích | test_khong_co_thu_muc_tam_thi_duong_cu_giu_nguyen | không nêu `thu_muc_tam` → vẫn đột biến tại chỗ như trước |
| TC-M4-19-06 | Dọn rác | test_ban_sao_bi_DON_sau_khi_do | hết lượt đo → thư mục tạm KHÔNG còn tồn tại |
| TC-M4-19-07 | **Bước nạp** | test_buoc_NAP_dich_dung_noi_dung_tep_goc_tren_ban_sao | bản sao mang đúng nội dung gốc → `khong_nap_duoc` vẫn phát hiện được |
| TC-M4-19-08 | **Đụng tên** | test_hai_tep_CUNG_TEN_khac_thu_muc_khong_pha_ban_sao_cua_nhau | `d1/dem.c` + `d2/dem.c` → hai bản sao riêng |
| TC-M4-19-09 | Dọn rác | test_ban_sao_cua_tep_TRUOC_da_bi_don_khi_do_tep_SAU | đang đo tệp 2 thì bản sao tệp 1 đã biến mất |
| TC-M4-19-10 | **Cờ dịch** | test_duong_tim_header_khong_che_header_HE_THONG | `firmware/stdio.h` giả → KHÔNG che `<stdio.h>` hệ thống |
| TC-M4-19-11 | Song song | test_thu_muc_tam_LONG_theo_run_id | đường thư mục tạm có `run_id` trong đó |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_dot_bien.py tests/test_xay_dung.py`
  **Đã kiểm: không phải nới ca nào.** Ca `test_tra_tep_ve_nguyen_ven_ke_ca_khi_chay_no` đi
  đường cũ (không `thu_muc_tam`) và giữ nguyên.

**Lệch khỏi kế hoạch (đo rồi mới thấy):**
- Cờ dịch là **`-iquote`**, không phải `-I` như bước 3 ghi. `-I` đổi đường tìm cho cả
  `#include <...>`, nên `du-lieu/rtos-sinhvien/firmware/stdio.h` (header giả của bo) che bản
  hệ thống và **11 trong 12** tệp bị xếp là `khong_nap_duoc`.
- Đường tìm header gắn cho **cả hai** lượt, không chỉ lượt có tệp sản phẩm: với `-iquote` thì
  nhánh ấy không đổi hành vi, và một nhánh `if` không đổi hành vi là một nhánh không ca kiểm
  nào canh được.
- `hdl.sensitivity` **không** dùng được `thu_muc_tam`: `chay` của nó bỏ qua đối số và dịch lại
  cả thư mục nguồn, nên bật lên là phá bản sao mà biên dịch bản gốc — mọi tệp RTL bị kết luận
  là *bộ kiểm không canh tới*. Điều kiện ấy ghi vào docstring của `do_do_nhay`.
- Dọn thư mục tạm **hai bậc**: `do_do_nhay` dọn thư mục nó được giao, công cụ dọn vỏ
  `.eide/mutate`. Thiếu bậc hai thì mỗi `run_id` để lại một thư mục rỗng.

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ" từng TC. — 13 chỗ phá, **13/13 đỏ** (lượt đầu 7/13)
- [x] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc. — 1835 → **1846 xanh, 0 đỏ**
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md. — **DEV-349**

**Hoàn tác:** revert commit.

<!-- TASK M4-04 -->
<a id="m4-04"></a>
### [M4-04] Đột biến chi tiết từng vị trí + điểm đột biến (mutation score) — P1 · M

**Giai đoạn:** GĐ1 · thứ tự #21 (kéo lên từ GĐ3 vì là tiền đề của M4-06)

**Mục tiêu:** `test.sensitivity` đo được từng dòng mà bộ kiểm không canh, kèm mutation score, thay vì một câu trả lời nhị phân theo tệp.
**Loại:** Công cụ mới (tham số mới `muc` cho công cụ có sẵn, mặc định giữ hành vi cũ)
**Phụ thuộc:** M4-05 (stillborn phải đúng trước), M4-19 (đột biến trên bản sao)
**Tệp chạm tới:** src/eide/build/dot_bien.py, src/eide/tools/xay_dung.py, tests/test_dot_bien.py

**Hiện trạng (đã kiểm lại trong mã):**
- dot_bien.py:62-74 `dot_bien_van_ban` dùng `re.subn(mau, thay, than)`: thay MỌI chỗ khớp cùng lúc.
- dot_bien.py:44-53 `_PHEP` có 4 phép; hằng hex bị loại bởi `(?<![\w.])` (ví dụ `0xFFFFFFFD`).
- dot_bien.py:141-153 dừng ở phép đầu tiên làm đỏ; trả `thay/khong_thay/khong_nap_duoc/chua_do_duoc`.

**Thay đổi cần làm:**
1. `liet_ke_dot_bien(ma) -> list[DotBien(phep, vi_tri, dong, truoc, sau)]` dùng `re.finditer` trên phần thân đã che chuỗi/chú thích (dùng lại `_BO_QUA`); `ap_mot(ma, db)` chỉ đổi MỘT chỗ.
2. Thêm phép: hex `0x[0-9A-Fa-f]+`→`0x0`; `&&`↔`||`; `>=`→`>`; `return <biểu thức>;`→`return 0;`; xoá một câu lệnh gọi hàm đứng riêng (`^\s*\w+\(.*\);$`→`;`).
3. `do_do_nhay(..., muc="tep"|"chi_tiet", toi_da_moi_tep=30, seed=0)`: chế độ chi tiết lấy mẫu tất định, trả `diem = killed/(total-stillborn)` cùng danh sách `song: [{tep, dong, phep, truoc, sau}]` (≤20).
4. `test.sensitivity` thêm `muc` (enum, mặc định "tep"), và ghi hiện vật `sim_result:test-sensitivity` (dùng chung với M4-06).

**Không được làm (giới hạn phạm vi):**
- Không đổi giá trị trả về của chế độ "tep" (mọi ca hiện có của test_dot_bien phải xanh nguyên).
- Không đổi thứ tự `_PHEP` cũ (test dùng chỉ số 0..3).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-04-01 | Đơn vị | tests/test_dot_bien.py::test_liet_ke_moi_vi_tri_rieng | `a==b; c==d;` → liet_ke_dot_bien có 2 mục phép "==", ap_mot chỉ đổi 1 chỗ |
| TC-M4-04-02 | Đơn vị | …::test_dot_bien_hang_hex | `return 0xFFFFFFFD;` → có đột biến hex sang 0x0 |
| TC-M4-04-03 | Đơn vị (fake chay) | …::test_chi_tiet_tinh_diem_va_liet_ke_dot_bien_song | bộ kiểm giả chỉ canh hằng 480, mã có 480 và `x==y` → diem<1, `song` chứa dòng có "==" |
| TC-M4-04-04 | Ca âm | …::test_che_do_tep_giu_nguyen_ket_qua | gọi không có `muc` → khoá trả về y như cũ (không có "diem") |
| TC-M4-04-05 | Ca biên | …::test_lay_mau_tat_dinh_theo_seed | 100 vị trí, toi_da=10, seed=0 hai lần → cùng danh sách |

**Mười một TC thêm khi làm** (phép phá tìm ra bảy chỗ không ai canh, và ba lỗi của chính phép
đo — xem DEV-350; tất cả trong `tests/test_dot_bien.py`):

| Mã TC | Loại | Tên ca | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-04-06 | Lược đồ | test_phep_moi_khong_doi_chi_so_cua_bon_phep_cu | bốn phép cũ giữ đúng chỉ số 0..3 |
| TC-M4-04-07 | Mẫu số | test_chi_tiet_KHONG_tinh_stillborn_vao_mau_so | `diem = bắt/(thử − stillborn)`, mutant stillborn không vào `song` |
| TC-M4-04-08 | Ca biên | test_chi_tiet_khong_co_mutant_nao_thi_diem_la_None | không phá được chỗ nào → `None`, KHÔNG `0.0` |
| TC-M4-04-09 | **Hiện vật thật** | test_tai_hien_DANH_GIA_2_2_mutant_EXC_RETURN_phai_SONG | `control_rtos.c` thật: bảng cũ 0 đột biến · bảng mới dòng 147 · mutant SỐNG |
| TC-M4-04-10 | **Chi phí** | test_liet_ke_khong_dung_ca_tep_cho_moi_cho_khop | 8 000 chỗ khớp kèm chú thích → liệt kê dưới 5 s (nhanh 0,04 s · chậm ≈21 s) |
| TC-M4-04-11 | Toạ độ | test_so_dong_dung_khi_co_CHU_THICH_NHIEU_DONG | chú thích ba dòng → số dòng vẫn là số dòng người mở tệp thấy |
| TC-M4-04-12 | Phép mới | test_phep_doi_gia_tri_tra_ve | `return x*3;` → `return 0;`, và KHÔNG chạm `return 0;` sẵn có |
| TC-M4-04-13 | Ca âm | test_bo_muc_dot_bien_KHONG_doi_gi | `0x0` gặp phép hex → bỏ, không vào mẫu số |
| TC-M4-04-14 | Ca âm | test_muc_la_thi_NEM_LOI_chu_khong_im_lang_chay_nhu_tep | `muc="chitiet"` → `ValueError`, không im lặng chạy chế độ tệp |
| TC-M4-04-15 | Tích hợp | test_cong_cu_truyen_muc_xuong_VA_ghi_hien_vat | công cụ truyền `muc` xuống VÀ ghi `sim_result:test-sensitivity` |
| TC-M4-04-16 | **Plan mode** | test_mien_khoa_plan_mode_la_CO_CHU_Y_va_co_ly_do | miễn khoá nằm trong `KHONG_KHOA`, và luật chung KHÔNG bị nới |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_dot_bien.py tests/test_xay_dung.py`
  **Đã kiểm: chế độ "tep" giữ nguyên từng khoá trả về**, và bốn ca gọi `test.sensitivity` phải
  thêm `explain` — xem phần lệch dưới đây.

**Lệch khỏi kế hoạch (đo rồi mới thấy):**
- Phải sửa cả `src/eide/ke_hoach.py` (ngoài danh sách "tệp chạm tới"). Khai `writes_artefact`
  là plan mode khoá công cụ — luật ấy lấy từ **hợp đồng** của công cụ, không từ danh sách tên.
  Cách giải là dùng `KHONG_KHOA`, cùng lý do với `memory.note`: khoá một phép ĐO trong lúc
  soạn kế hoạch là cấm tác tử biết bộ kiểm hiện tại canh được những gì.
- `test.sensitivity` phải đòi `explain`: N8 không có ngoại lệ, và sổ công cụ chặn đúng chỗ ấy.
  Bốn lời gọi trong ca kiểm phải sửa theo. Vẫn R1 và vẫn không khoá.
- `liet_ke_dot_bien` **không được dựng cả tệp cho mỗi chỗ khớp**: trên `logo_ptit.c` thật
  (720 KB, 57 600 chỗ khớp) đó là ≈41 GB việc chuỗi — lượt chạy đầu TREO 10 phút. Phải liệt kê
  rẻ, lấy mẫu trước, và tra số dòng qua một **bản đồ đoạn**.
- Bỏ bước sắp xếp TRƯỚC khi lấy mẫu: nó không đổi gì đo được (tính tất định đến từ `seed`).

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ" từng TC. — 22 chỗ phá, **22/22 đỏ** (lượt đầu 15/22)
- [x] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc. — 1846 → **1862 xanh, 0 đỏ**
- [x] Chỉ số: tái hiện ca DANH-GIA §2.2 → **ĐẠT** — bảng cũ 0 đột biến cho hằng hex; bảng mới
  tìm đúng dòng 147 của `control_rtos.c` thật; áp vào, bộ kiểm vẫn XANH ⇒ mutant **SỐNG**.
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md. — **DEV-350**

**Hoàn tác:** revert commit; chế độ mặc định không đổi.

<!-- TASK M4-06 -->
<a id="m4-06"></a>
### [M4-06] Vòng tự nâng test khi đột biến sống (Evaluator–Optimizer) — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #22

**Mục tiêu:** Sau khi test.run xanh, EIDE chủ động đo độ nhạy và (khi bật cờ) chạy một vòng có trần để thêm ca giết các mutant còn sống.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_TEST_HARDEN`, mặc định TẮT)
**Phụ thuộc:** M4-04, M4-05; liên quan M1-06 (tổ chức subagent) — không viết lại phần định nghĩa subagent chung của M1-06
**Tệp chạm tới:** src/eide/config.py, src/eide/hooks/standard.py, src/eide/tools/xay_dung.py, src/eide/subagent.py, tests/test_test_harden.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- tools/xay_dung.py:738 `test.sensitivity` có `core=False`; mô tả dặn "Gọi nó SAU khi test.run xanh" nhưng không cơ chế nào ép.
- Kết quả test.sensitivity chỉ được trả về, không `store.apply` (ghi chú trong tools/hdl.py hdl_sim xác nhận).
- `grep sensitivity` trong hooks/loop: không có chỗ nào gọi.

**Thay đổi cần làm:**
1. Cờ `test_harden` trong `Features` + `ten_co()`.
2. Luôn làm (sửa lỗi, không cần cờ): test.sensitivity ghi hiện vật `sim_result:test-sensitivity` với `deps.upstream` gồm tệp test và tệp sản phẩm.
3. Stop hook `test_xanh_chua_do_nhay` (khi cờ bật): có MA_TEST dat=True với `updated_at` mới hơn hiện vật độ nhạy (hoặc chưa có hiện vật độ nhạy) thì mở khoá `test.sensitivity` (như dòng 590-592 với task.run), `another_round=True`, mỗi lượt một lần.
4. Công cụ `test.harden(max_vong=3, toi_da_goi=15)` (core=False): với mỗi mutant sống (từ M4-04), gọi `SA.chay(ma="test-writer")` (subagent mới, công cụ: fs.read, fs.glob, fs.write giới hạn test/**, test.run). Ca mới phải XANH trên mã gốc và ĐỎ trên mutant (EIDE tự kiểm hai lần chạy), sai thì loại ca. Trần vòng/lời gọi cứng.

**Không được làm (giới hạn phạm vi):**
- Không cho test-writer ghi ngoài test/**; không sửa mã sản phẩm.
- Cờ TẮT thì không có hook mới, không có công cụ mới hiển thị.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-06-01 | Đơn vị | tests/test_test_harden.py::test_sensitivity_ghi_hien_vat | test giả xanh + sản phẩm (skipif không có cc) → test.sensitivity → store.get("sim_result:test-sensitivity") không None |
| TC-M4-06-02 | Đơn vị hook | …::test_hook_bat_khi_test_xanh_chua_do_nhay | cờ bật (monkeypatch env), MA_TEST dat True, không có hiện vật độ nhạy → another_round True, "test.sensitivity" trong registry._unlocked |
| TC-M4-06-03 | Cờ TẮT | …::test_co_tat_thi_hook_im | như 02 nhưng cờ tắt → another_round False |
| TC-M4-06-04 | Tích hợp (ScriptedGateway) | …::test_harden_loai_ca_khong_do_tren_mutant | test-writer viết ca luôn xanh → ca bị loại, báo "không giết được mutant" |
| TC-M4-06-05 | Ca biên | …::test_harden_dung_o_tran_vong | 5 mutant, max_vong=1 → chỉ 1 vòng, ScriptedGateway không bị gọi quá số kịch bản (không có E6004) |

**Mười một TC thêm khi làm** (phép phá tìm ra bốn chỗ không ai canh, và hai hàng rào có sẵn chỉ
ra hai ràng buộc thật — xem DEV-351; tất cả trong `tests/test_test_harden.py`):

| Mã TC | Loại | Tên ca | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-06-06 | Lỗi thời | test_hien_vat_do_nhay_co_DEPS_UPSTREAM | hiện vật khai `deps.upstream` gồm tệp test VÀ tệp sản phẩm |
| TC-M4-06-07 | **Mốc** | test_hien_vat_do_nhay_mang_PHIEN_BAN_cua_hien_vat_test | ghi `version_test`, KHÔNG dựa vào `updated_at` |
| TC-M4-06-08 | Hook | test_hook_IM_khi_da_do_nhay_SAU_khi_test_xanh | đã đo rồi thì im |
| TC-M4-06-09 | Hook | test_hook_NHAC_LAI_khi_test_chay_lai_sau_lan_do | test chạy lại sau lần đo → nhắc lại |
| TC-M4-06-10 | Hook | test_hook_IM_khi_test_DO | test còn ĐỎ thì không nhắc đo độ nhạy |
| TC-M4-06-11 | Hook | test_hook_moi_luot_chi_nhac_MOT_lan | nhắc hai lượt liền là cách một lời nhắc thành tiếng ồn |
| TC-M4-06-12 | Cờ | test_cong_cu_harden_chi_co_khi_CO_BAT | cờ TẮT → KHÔNG đăng ký, không chỉ bị giấu |
| TC-M4-06-13 | An toàn | test_subagent_test_writer_KHONG_ghi_duoc_ngoai_test | không `fs.edit`, không `build.compile`, không chạm bo |
| TC-M4-06-14 | **Phép nhận** | test_harden_loai_ca_DO_NGAY_tren_ma_that | ca ĐỎ sẵn trên mã thật cũng bị LOẠI, và bộ kiểm được TRẢ LẠI |
| TC-M4-06-15 | Trần | test_harden_dung_o_TRAN_LOI_GOI_du_con_mutant | `toi_da_goi` là trần thứ hai, độc lập với `max_vong` |
| TC-M4-06-16 | **Bộ dò** | test_bo_do_tai_lieu_dem_ca_cong_cu_sau_CO_KHAC_schematic | `kiem_tai_lieu` đếm công cụ sau MỌI cờ, không chỉ `schematic` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_dot_bien.py tests/test_tu_phat_hien_sai.py tests/test_subagent.py tests/test_loop.py`
  **Hai ca `sch` phải siết** (không phải nới): chúng đòi `bo_qua_vi_co` **chỉ** chứa `sch.*`,
  đúng khi `schematic` là cờ duy nhất gate công cụ và nói quá khi có hai.

**Lệch khỏi kế hoạch (đo rồi mới thấy):**
- Phải sửa cả `tools/kiem_tai_lieu.py` (ngoài danh sách "tệp chạm tới"): `_tat_ca_cong_cu` tự
  khai *"kể cả công cụ nằm sau cờ tính năng"* mà chỉ bật một cờ theo TÊN, nên `test.harden` bị
  báo thành "không tồn tại". Nay lấy danh sách từ `Features.ten_co()`.
- Hook so **phiên bản**, không so `updated_at`: độ phân giải thô làm hai lần ghi trong cùng một
  giây bằng nhau, và phép so "mới hơn" im lặng sai. Nên `test.sensitivity` ghi kèm `version_test`.
- Ca mới phải thêm **vào tệp test đang có**, không tạo tệp mới: `chay_test` dịch mọi tệp trong
  `test/` cùng nhau, nên tệp thứ hai có `main()` làm trùng ký hiệu. Kiểm trên dữ liệu thật: cả
  bốn dự án có `test/` đều đúng một tệp.
- Lời giao việc phải nói ra hợp đồng của `fs.write`: nó không ghi đè tệp mà lượt này chưa đọc
  (E4020, có từ 30/09/2026).
- Ca bị loại phải được **trả lại**: một ca xanh mãi mãi ở lại trong `test/` còn tệ hơn không
  thêm gì.

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ" từng TC. — 22 chỗ phá, **22/22 đỏ** (lượt đầu 18/22)
- [x] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc. — 1862 → **1878 xanh, 0 đỏ**
- [ ] **CHƯA ĐẠT** — Chỉ số: mutation score trên dự án mẫu tăng sau harden. Đo "trước" đã có
  (`du-lieu/rtos-sinhvien`, `logo_ptit.c`: điểm **0,0** · 30 mutant · 20 sống · 18 s), nhưng
  phần "sau" cần **lời gọi mô hình** và §3.0 bắt hỏi người dùng trước. Và kể cả có hỏi, dự án
  ấy **không có chỗ để đo**: tệp duy nhất đáng nâng (`control_rtos.c`) là `khong_nap_duoc` vì
  tệp test `#include` chính tệp `.c` đó; sáu tệp còn lại là bitmap. Cờ giữ **TẮT**.
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md. — **DEV-351**

**Hoàn tác:** tắt cờ; revert commit cho phần ghi hiện vật.

<!-- TASK M4-07 -->
<a id="m4-07"></a>
### [M4-07] Verifier nhận gói bằng chứng do EIDE dựng từ sổ cái, không nhận đề bài tác tử chính tự viết — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #23

**Mục tiêu:** Khi tác tử chính gọi `task.run(subagent="verifier")`, đầu vào của verifier do mã dựng từ sổ cái/kho, nên verifier không thấy lập luận của tác tử.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_VERIFIER_GOI_BANG_CHUNG`, mặc định TẮT)
**Phụ thuộc:** Gộp với M1-06 (cùng chạm subagent/task.run): làm sau hoặc cùng PR, không viết lại phần chung
**Tệp chạm tới:** src/eide/subagent.py, src/eide/tools/dieu_phoi.py, src/eide/config.py, tests/test_subagent.py

**Hiện trạng (đã kiểm lại trong mã):**
- tools/dieu_phoi.py:45-86 `task_run(ctx, explain, subagent, viec)` truyền nguyên `viec` cho `SA.chay`; chỉ đường tự động (`can_goi_verifier`) dùng `SA.viec_cho_verifier(bc)` (subagent.py:240).
- hooks/standard.py:597-610 bảo tác tử chính tự gọi verifier và tự soạn việc.
- `DinhNghia.doc_duoc_viec=False` (subagent.py:46,150) nhưng KHÔNG được đọc ở đâu trong `chay`.

**Thay đổi cần làm:**
1. `subagent.goi_bang_chung_tu_so_cai(ledger, store, history, toi_da_ky_tu=6000) -> str`: đọc ngược sổ cái tới lần verifier gần nhất (tái dùng logic `kiem_chung.co_viec_chua_kiem`). Liệt kê changeset (id, tệp), hiện vật có `writes_artefact` (id, version, stale, `dat` nếu có), kết quả build/test/sim gần nhất.
2. `loc_claim(viec) -> str`: giữ ≤300 ký tự, bỏ câu chứa "vì", "chắc chắn", "đã kiểm", "đã xác nhận", "nên".
3. Khi cờ bật và `dn.doc_duoc_viec is False`: `task_run` gửi `"CLAIM: …\n\nBẰNG CHỨNG (dữ liệu):\n…"` thay cho `viec`; ghi sổ `subagent_input` dạng `{"che_do": "goi_bang_chung", "so_ky_tu": n}`.

**Không được làm (giới hạn phạm vi):**
- Không đổi đường tự động SubagentStop (đã dùng viec_cho_verifier).
- Không đổi lược đồ báo cáo `TRUONG_BAO_CAO`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-07-01 | Tích hợp (ScriptedGateway) | tests/test_subagent.py::test_verifier_KHONG_thay_lap_luan_tac_tu_chinh | cờ bật; viec="Đã xong vì chắc chắn PID đúng, kiểm a.c" → messages[0] gửi verifier không chứa "chắc chắn" (đọc qua hàm script nhận messages) |
| TC-M4-07-02 | Tích hợp | …::test_goi_bang_chung_co_changeset_tu_so_cai | fs.write a.c qua registry trước → nội dung gửi verifier chứa "a.c" và mã changeset |
| TC-M4-07-03 | Đơn vị | …::test_loc_claim_cat_300_va_bo_lap_luan | chuỗi 1000 ký tự có "vì" → ≤300, không có "vì" |
| TC-M4-07-04 | Cờ TẮT | …::test_co_tat_viec_di_nguyen_van | cờ tắt → messages[0]["text"] == viec |
| TC-M4-07-05 | Ca âm | …::test_subagent_khac_khong_bi_doi_viec | cờ bật, subagent="firmware" → viec nguyên văn |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_tu_phat_hien_sai.py`
- test_verifier_KHONG_thay_de_bai_chi_thay_bao_cao, test_task_run_tu_goi_verifier_khi_firmware_tuyen_dat giữ nguyên.

**Ca kiểm THÊM (ngoài bảng trên) — đã viết và đã đỏ trước khi sửa:**
| Mã TC | Tệp test | Nó canh gì |
|---|---|---|
| TC-M4-07-06 | …::test_loc_claim_bo_dung_nam_dau_hieu | năm dấu hiệu, mỗi dấu hiệu một câu; câu dữ kiện phải còn |
| TC-M4-07-07 | …::test_loc_claim_khong_con_cau_nao_thi_noi_RO | lọc sạch thì nói ra, đừng gửi chuỗi trắng |
| TC-M4-07-08 | …::test_goi_bang_chung_noi_version_va_STALE_cua_hien_vat | gói nói phiên bản và cờ STALE, không chỉ nói tên |
| TC-M4-07-09 | …::test_goi_bang_chung_DUNG_o_lan_verifier_gan_nhat | gói dừng ở ĐÚNG mốc mà `co_viec_chua_kiem` dùng |
| TC-M4-07-10 | …::test_goi_bang_chung_co_tran_ky_tu | 200 changeset không được thành 200 KB |
| TC-M4-07-11 | …::test_goi_bang_chung_noi_ket_qua_build_test_sim_gan_nhat | khối C có `dat` của build và của test |
| TC-M4-07-12 | …::test_so_cai_ghi_lai_che_do_dau_vao_cua_subagent | sổ cái ghi `subagent_input`, và `so_ky_tu` đếm chuỗi THẬT gửi đi |
| TC-M4-07-13 | …::test_duong_TU_DONG_khong_bi_doi | giới hạn phạm vi: đường SubagentStop vẫn gửi `BÁO CÁO`, không gửi `BẰNG CHỨNG` |
| TC-M4-07-14 | …::test_MOI_co_khai_trong_dataclass_deu_co_trong_ten_co | `ten_co()` so TẬP HỢP với `dataclasses.fields`, và mọi cờ nạp được qua biến môi trường |
| TC-M4-07-15 | …::test_loc_claim_bo_PHAN_QUYET_trich_san | dấu hiệu thứ sáu (phán quyết trích sẵn), và một quan sát thì KHÔNG bị bỏ |
| TC-M4-07-16 | …::test_goi_bang_chung_noi_PHIEN_BAN_TAI_LUC_DOI_khi_co_so_changeset | tham số `history` cho `(create→v1)`, không trang trí |
| TC-M4-07-17 | …::test_goi_bang_chung_co_KHOI_B_doc_lai_hien_vat_bi_cham | khối B đọc lại từ KHO (v, STALE), khác khối A nhắc lại lời sổ cái |
| TC-M4-07-18 | …::test_goi_bang_chung_NOI_RA_khi_khong_co_changeset_nao | không có changeset thì NÓI RA, đừng im |

**Phá lại thì đỏ:** 36 phép phá dựng từ `git diff`, **34/36 ở lượt đầu**. Hai chỗ LỌT đều ở
cùng một hình dạng DEV-344 — *ca kiểm xanh vì MỘT DÒNG KHÁC*:

* **khối B biến mất mà bộ kiểm vẫn xanh**, vì ca kiểm của khối A đã thấy `a.c` qua dòng
  changeset. Hai khối nói hai câu khác nhau: A nói *"cs-3 chạm a.c"* (chuyện đã xảy ra), B nói
  *"a.c trong kho hiện là v1 và đang STALE"* (chuyện ĐANG đúng) — và chỉ câu thứ hai trả lời
  được "bằng chứng này còn giá trị không". Nay có ca đọc riêng khối B và chắc `c.c` KHÔNG nằm
  trong khối C.
* **nhánh "không có changeset nào" im lặng cũng xanh.** Im và "không có gì để kiểm" trông
  giống nhau với người đọc, mà hai điều ấy khác hẳn.

Sau khi thêm hai ca: **36/36**.

**Lệch khỏi kế hoạch:**
1. **Thêm dấu hiệu thứ SÁU vào `loc_claim`,** vì một phép đo. Năm dấu hiệu kế hoạch nêu chỉ bỏ
   được **11/1 706 câu** trên **323 đề bài verifier THẬT** trong sổ cái 42 dự án. Chỗ rò thật
   không phải chữ "vì" — tác tử chính **trích sẵn phán quyết**: `kết quả 'dat: false'`,
   `(dat=true, chip GW2A)`. Thêm `dat:`/`dat=`/`pass_fail`/`chay_duoc=`/`không đạt`/`đã đạt`:
   **95/1 706 câu, chạm 88/323 đề bài, 0/323 bị lọc thành trắng**. KHÔNG nhận `thành công` (lên
   123 câu) vì *"lệnh chạy thành công, mã thoát 0"* là một quan sát — bỏ nó là lấy mất dữ kiện.
2. **Sửa `Features.ten_co()`** — không có trong "tệp chạm tới" của kế hoạch ngoài `config.py`.
   Cờ `verifier_goi_bang_chung` khai đúng trường mà `Features.load()` vẫn trả `False`:
   `ten_co()` là danh sách gõ tay, và `load()`/`to_dict()`/`kiem_tai_lieu.py` đều vòng qua nó.
   Nay lấy từ `dataclasses.fields(Features)`. Đây là sửa lỗi thuần, **không sau cờ**.
3. **`history` và `registry` là tham số tuỳ chọn** (kế hoạch ghi `history` bắt buộc). Gói dựng
   được mà không có chúng — đo trên 5 bản xuất `docs/*/ho-so-tac-tu` vốn không có tệp kho.
4. **Ranh giới từ của `vì`/`nên` không đo được chênh lệch nào**: trên 1 706 câu thật, phép
   `\bvì\b` và phép chuỗi con `"vì" in` kết luận **giống nhau 1 706/1 706**. Giữ dạng ranh giới
   từ (rẻ, và an toàn hơn khi thêm dấu hiệu sau), nhưng **không có ca kiểm nào tuyên nó quan
   trọng** — vì số đo nói nó không.

**Đo trên dữ liệu thật (không phải trên ca kiểm):**
- Sổ cái 42 dự án: **327 lời gọi `task.run` có `viec`**, **323** trong đó là `verifier` —
  đường này là đường chính của cả lớp kiểm chứng, không phải một đường lý thuyết.
- **209/323** đề bài dài hơn trần 300 ký tự.
- `goi_bang_chung_tu_so_cai` dựng được gói **CÓ NỘI DUNG trên 29/42 dự án**, **0 lần đổ**.
  `du-lieu/robot-canbang` đụng **đúng trần 6 000 ký tự** — trần nổ trên dữ liệu có thật.
- Tham số `history` làm gói `rtos-sinhvien` dài **2 142 → 2 322 ký tự**, mỗi dòng thêm
  `(update→v24)`: phiên bản **tại lúc đổi**, số mà sổ cái một mình không ghi.

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [x] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa (1 878 → 1 896).
- [ ] **CHƯA ĐẠT** — Chỉ số: trên bộ ca gài lỗi (M4-22), tỉ lệ verifier bác đúng không giảm
      khi bật cờ. **M4-22 chưa làm** (nó ở nhiệm vụ sau), và phép đo ấy cần lời gọi mô hình
      thật — §3.0 bắt hỏi người dùng trước. Nên cờ `VERIFIER_GOI_BANG_CHUNG` giữ **TẮT**.
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md (DEV-352).

**Hoàn tác:** tắt cờ.

<!-- TASK M4-09 -->
<a id="m4-09"></a>
### [M4-09] Stop hook không được coi `task.run` với subagent khác là "đã kiểm chứng" — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #24

**Mục tiêu:** Chỉ một lần chạy verifier thật mới tắt yêu cầu kiểm chứng ở cuối lượt.
**Loại:** Sửa lỗi thuần (đi vòng hàng rào N6)
**Phụ thuộc:** Không
**Tệp chạm tới:** src/eide/hooks/standard.py, src/eide/loop.py (đọc), tests/test_tu_phat_hien_sai.py

**Hiện trạng (đã kiểm lại trong mã):**
- hooks/standard.py:562-563 `if "task.run" in (getattr(ctx, "cong_cu_da_goi", []) or []): return StopResult(fired=["tu_kiem_da_chay"])`.
- loop.py:816 `ctx.cong_cu_da_goi.append(call.tool)` chỉ ghi TÊN, không ghi args.
- loop.py:891-893 và kiem_chung.py:44 đã đọc `args.subagent == "verifier"` (nhất quán), riêng hook này thì không.
- Test có sẵn tests/test_tu_phat_hien_sai.py::test_da_goi_verifier_roi_thi_thoi dùng `_Ctx(["đã xong"], cong_cu=["fs.write","task.run"])` với sổ cái RỖNG và da_ghi=True. Ca này đang khoá đúng hành vi lỗi.

**Thay đổi cần làm:**
1. Thêm trường `da_goi_verifier: bool = False` vào TurnContext (loop.py:~89-92); đặt True ở loop.py:891 cùng chỗ `self.ghi_chua_kiem = False`.
2. Hook: thay dòng 562 bằng `if getattr(ctx, "da_goi_verifier", False): return StopResult(fired=["tu_kiem_da_chay"])`. Phần còn lại vẫn dựa `co_viec_chua_kiem` (đọc args từ sổ cái).
3. Cập nhật test_da_goi_verifier_roi_thi_thoi: dựng `_Ctx(..., so=_So([("fs.write",{}),("task.run",{"subagent":"verifier"})]), da_ghi=False)` hoặc đặt `ctx.da_goi_verifier=True`. Ghi chú trong docstring lý do đổi.

**Không được làm (giới hạn phạm vi):**
- Không đổi điều kiện hoãn khi đang theo kế hoạch (dòng 571-573).
- Không đổi lời nhắc injection.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-09-01 | Đơn vị hook | tests/test_tu_phat_hien_sai.py::test_task_run_subagent_KHAC_khong_tat_hook | `_Ctx(["đã xong"], cong_cu=["fs.write","task.run"], chua_kiem=True)` (sổ cái fs.write + build.compile, không verifier) → another_round True |
| TC-M4-09-02 | Tích hợp (make_agent) | …::test_LOI_task_run_firmware_khong_dat_co_da_goi_verifier | ScriptedGateway: fs.write rồi task.run(subagent="firmware"), firmware trả báo cáo không dat → ctx.da_goi_verifier False |
| TC-M4-09-03 | Ca âm | …::test_verifier_that_thi_hook_im | ctx.da_goi_verifier=True → another_round False, fired chứa "tu_kiem_da_chay" |
| TC-M4-09-04 | Hồi quy | …::test_task_run_voi_subagent_KHAC_khong_tinh_la_da_kiem (có sẵn) | vẫn xanh |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_tu_phat_hien_sai.py tests/test_loop.py tests/test_subagent.py tests/test_ke_hoach.py`

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ" từng TC (khôi phục dòng cũ thì TC-01 đỏ). Tập phá
      dựng từ `git diff`: **10/12**; hai chỗ LỌT đã kiểm lại là **không đổi hành vi** (DEV-353).
- [x] Toàn bộ `pytest -q` xanh: 1 896 → **1 901**, 0 đỏ.
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md — DEV-353.

**Hoàn tác:** revert commit.

<!-- TASK M4-11 -->
<a id="m4-11"></a>
### [M4-11] Hồi quy tự động sau khi sửa mã + STALE chính xác theo tệp — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #25

**Mục tiêu:** Sửa một tệp firmware chỉ làm lỗi thời những kết quả test/sim dùng tệp đó, các bộ test bị ảnh hưởng tự chạy lại nhẹ, và không được tuyên xong khi còn kết quả STALE.
**Loại:** STALE theo tệp + chặn tuyên xong khi STALE = Sửa lỗi thuần; tự chạy test sau ghi + tiêm kết quả = Đổi hành vi (cờ `EIDE_FEATURE_HOI_QUY_NEN`, mặc định TẮT)
**Phụ thuộc:** M2-01 (phải xong trước, theo danh sách liên quan)
**Tệp chạm tới:** src/eide/deps.py, src/eide/tools/xay_dung.py, src/eide/loop.py, src/eide/hooks/standard.py, src/eide/config.py, tests/test_hoi_quy.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- history.py:217 `deps.danh_dau_stale(store, thuong_nguon=paths, …)`, và deps.py:37 `"code": ("build","sim_result","target")`: sửa BẤT KỲ tệp mã nào cũng đánh STALE mọi sim_result.
- store/db.py:433 `mark_stale` chỉ đánh dấu, "không tự chạy lại".
- `KetQuaTest.tep_nguon` / `KetQuaMoPhong.tep_nguon` đã có trong canonical (mo_phong.py:256, 353).

**Thay đổi cần làm:**
1. test.run/sim.run ghi thêm `deps.upstream = tep_nguon` (đường dẫn tương đối) vào hiện vật.
2. `deps.ha_nguon_cua`: với loại đích `sim_result` mà hiện vật có `deps.upstream` thì CHỈ lấy khi `artefact_id in upstream`, không lấy theo loại (giữ đường theo loại cho hiện vật chưa có upstream, để tương thích dữ liệu cũ).
3. Stop hook `ket_qua_stale` (không cờ): lượt có tuyên (said_anything) mà MA_TEST/MA_SIM `stale=True` và lượt đó có ghi mã thì another_round một lần, injection "kết quả … lỗi thời vì <stale_reason> — chạy lại trước khi báo".
4. Cờ bật: trong loop.py ngay sau khối `khong_noi_gi` (~dòng 897-908), nếu tool là fs.write/fs.edit vào `firmware/**` và có MA_TEST với tệp đó trong upstream, gọi `MP.chay_test` (trần 20 s, 1 lần/lượt), rồi append message `_he_thong` "hồi quy: x/y ca".

**Không được làm (giới hạn phạm vi):**
- Không xoá hay tự sửa hiện vật STALE; không đổi `KHONG_STALE`.
- Không chạy sim.run tự động (có thể lâu).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-11-01 | Đơn vị | tests/test_hoi_quy.py::test_sua_tep_khong_lien_quan_khong_stale | sim_result A upstream ["firmware/pid.c"]; history.ghi_tep("firmware/ui.c") → A không stale |
| TC-M4-11-02 | Đơn vị | …::test_sua_tep_lien_quan_thi_stale | ghi_tep("firmware/pid.c") → A stale |
| TC-M4-11-03 | Ca âm tương thích | …::test_hien_vat_cu_khong_upstream_van_stale_theo_loai | sim_result không có deps → vẫn stale như cũ |
| TC-M4-11-04 | Đơn vị hook | …::test_tuyen_xong_khi_MA_TEST_stale_thi_bat_lai | MA_TEST stale, da_ghi_gi_do True, said_anything → another_round True |
| TC-M4-11-05 | Cờ TẮT | …::test_co_tat_khong_tu_chay_test | ScriptedGateway fs.write firmware/pid.c → không có message "hồi quy:" |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_xay_dung.py tests/test_snapshot.py tests/test_tu_phat_hien_sai.py tests/test_loop.py`
- test_nguoi_sua_NGUONG_tren_bang_thi_ket_qua_cu_thanh_LOI_THOI giữ nguyên.

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ": **31/34** (lượt đầu 24/32). Ba chỗ LỌT còn lại đã
      kiểm lại là **không đổi hành vi** — xem DEV-354.
- [x] Toàn bộ `pytest -q` xanh: 1 901 → **1 929**, 0 đỏ.
- [ ] **CHƯA ĐẠT** — *"số lần tuyên xong với kết quả STALE = 0"* cần **phát lại** phiên mẫu với
      hook mới (sổ cái không ghi trạng thái kho tại thời điểm ấy), tức lời gọi mô hình thật, mà
      §3.0 bắt hỏi người dùng trước. Thay vào đó đã đo trên **9 kho thật**: bán kính STALE của
      kết quả test/sim khi sửa một tệp mã **107 → 49 lần** (58/107 là cáo buộc oan).
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md — DEV-354.

**Hoàn tác:** tắt cờ cho phần tự chạy; revert commit cho phần STALE và hook.

<!-- TASK M2-09 -->
<a id="m2-09"></a>
### [M2-09] Phân tích tĩnh chiều sâu: call graph, ngăn xếp, luật ngữ cảnh ISR (`code.static`) — P1 · L

**Giai đoạn:** GĐ1 · thứ tự #26 (kéo lên từ GĐ3 vì là tiền đề của M4-13)

**Mục tiêu:** có công cụ trả dữ kiện máy đo về đồ thị gọi hàm, ngăn xếp tối đa theo chuỗi gọi từ main và từng ISR, và vi phạm cơ bản trong ngữ cảnh ngắt.
**Loại:** Công cụ mới (`code.static`, `core=False`, R1). Không cần cờ vì chỉ đọc và chỉ hiện khi gọi `tool.search`.
**Phụ thuộc:** M2-08. Là tiền đề của M2-10 và M4-13.
**Tệp chạm tới:** src/eide/build/phan_tich_tinh.py (mới), src/eide/tools/xay_dung.py, tests/test_phan_tich_tinh.py (mới), tests/du-lieu-chung/phan_tich_tinh/ (mẫu .su/.ci).

**Hiện trạng (đã kiểm lại trong mã):**
- phan_tich_ma.py docstring: "Không phân tích ngữ nghĩa, không dựng đồ thị gọi hàm đúng nghĩa".
- toolchain.py:434 (avr-gcc) và toolchain.py:732, 777 (arm, rv32): có `-Wall -Wextra`; không có `-fstack-usage`, `-fcallgraph-info`, `-fanalyzer`. Không có cppcheck hay lizard ở đâu trong src/eide.
- xay_dung.py:438 `build.map` là mẫu công cụ đọc kết quả biên dịch rồi ghi artefact `analysis` (KHONG_STALE).

**Thay đổi cần làm:**
1. `phan_tich_tinh.py` gồm các hàm THUẦN để test được mà không cần trình biên dịch:
   - `doc_su(text) -> dict[ham, (byte, kieu)]` (định dạng GCC: `file.c:12:6:ham\t48\tstatic`);
   - `doc_ci(text) -> dict[ham, set[ham_goi]]` (VCG của `-fcallgraph-info`, các dòng `edge: { sourcename: … targetname: … }`);
   - `ngan_xep_toi_da(su, cg, goc) -> (byte, chuoi)` duyệt DFS, gặp đệ quy thì đánh dấu "không chặn trên được";
   - `luat_isr(nguon_c, cg, isr) -> list[ViPham]`: trong tập hàm reachable từ ISR, báo `float`/`double`, toán tử `/` `%` trên biến (không phải hằng), gọi `_delay_ms|_delay_us|printf|malloc`; báo biến toàn cục được ghi ở cả ISR lẫn main mà không có `volatile`.
2. `chay_phan_tich(goc, cc, nguon, isa)`: biên dịch lại vào `.eide/build/tinh/` với `-fstack-usage -fcallgraph-info=su -c`, gọi các hàm trên; cppcheck và lizard chỉ chạy nếu `shutil.which` thấy; thiếu thì ghi "không chạy được: thiếu …".
3. Công cụ `code.static(nguon?, explain)`: ghi artefact `analysis` id `analysis:static`. Kết quả gọn: tối đa 20 phát hiện, mỗi cái có `tep:dong`, và ngân sách stack so với `_han_muc(ctx, ...)` như `build_map`.
4. `code.analyze` (xay_dung.py `code_analyze`): nếu đã có `analysis:static` mới hơn tệp thì đính tóm tắt vào phần DỮ KIỆN.

**Không được làm (giới hạn phạm vi):**
- Không đổi cờ biên dịch của `build.compile` (ảnh nạp chip phải giữ nguyên).
- Không chạy addon MISRA có bản quyền; không chặn ghi tệp dựa trên kết quả này.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-09-01 | Đơn vị | tests/test_phan_tich_tinh.py::test_doc_su | chuỗi 3 dòng .su → dict đúng byte (mã cũ: ImportError) |
| TC-M2-09-02 | Đơn vị | …::test_ngan_xep_theo_chuoi_goi | main(16) → a(32) → b(48) → kết quả 96 và chuỗi ["main","a","b"] |
| TC-M2-09-03 | Ca biên | …::test_de_quy_thi_noi_khong_chan_duoc | a gọi a → cờ `de_quy=True` |
| TC-M2-09-04 | Đơn vị | …::test_luat_isr_bat_phep_chia_va_delay | ISR gọi f; f có `x / y` và `_delay_ms(1)` → 2 vi phạm có số dòng |
| TC-M2-09-05 | Ca âm | …::test_isr_sach_khong_keu | ISR chỉ `dem++` (`dem` là volatile) và `x >> 2` → 0 vi phạm |
| TC-M2-09-06 | Tích hợp | …::test_thieu_trinh_bien_dich_thi_noi_ro | `which` trả None → kết quả có "không chạy được", `ok` vẫn True, không đạt giả |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_xay_dung.py tests/test_quy_trinh_lap_trinh.py tests/test_arm_bien_dich.py tests/test_tai_lieu_khop_ma.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh. Ca cần avr-gcc thật thì đánh `@pytest.mark.nha_that`.
- [ ] Trên firmware robot: ước lượng stack được đối chiếu với đo stack-painting, ghi con số vào DEV-LOG.
- [ ] DEV-LOG.

**Hoàn tác:** revert commit (công cụ `core=False` nên không ảnh hưởng lược đồ mặc định).

<!-- TASK M4-13 -->
<a id="m4-13"></a>
### [M4-13] Kiểm "nối" tĩnh sau biên dịch (vector table, hàm không ai gọi, return hằng) — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #27

**Mục tiêu:** Ngay sau `build.compile` thành công, EIDE liệt kê ISR đang trỏ Default_Handler dù có handler cùng tên, hàm người viết bị linker loại vì không ai gọi, và hàm chỉ trả hằng.
**Loại:** Công cụ mới (`build.wiring`, core=False) + thêm cảnh báo vào kết quả build.compile sau cờ `EIDE_FEATURE_KIEM_NOI`, mặc định TẮT
**Phụ thuộc:** M2-09 (phải xong trước theo danh sách liên quan)
**Tệp chạm tới:** src/eide/build/kiem_noi.py (mới), src/eide/tools/xay_dung.py, src/eide/config.py, tests/test_kiem_noi.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- tools/xay_dung.py:40-55 `_tep_khong_vao_anh` chỉ kiểm tệp .c không có trong lệnh dịch.
- build.map đọc section/symbol (`TC.doc_map`, xay_dung.py:~472).
- target.debug có cảnh báo "hàm chỉ trả về một hằng số" nhưng chỉ khi chạy trên chip (tools/mach_that.py:651-668).
- DANH-GIA §3.1: 7 lần "cơ chế có sẵn, đường dẫn tới nó đứt", gồm SysTick → Default_Handler và PendSV.

**Thay đổi cần làm:**
1. `kiem_noi.doc_vector(elf) -> list[(chi_so, dia_chi, ten)]`: đọc section `.isr_vector` bằng `arm-none-eabi-objdump -s -j .isr_vector` + `nm`; ten từ `addr2line`/`nm`.
2. `kiem_noi.isr_bi_bo_quen(vector, nm_symbols)`: ô trỏ `Default_Handler` mà trong mã người dùng có định nghĩa mạnh tên `<X>_Handler` (khác địa chỉ).
3. `kiem_noi.ham_bi_loai(log_link)`: biên dịch thêm `-Wl,--print-gc-sections` và phân tích dòng "removing unused section '.text.<ham>'" cho hàm trong tệp người dùng (bỏ vendor/).
4. Công cụ `build.wiring` (R1, core=False) trả ba danh sách. Cờ bật thì build.compile gọi nó và nối vào note_vi.
5. AVR/RISC-V: bỏ qua bước vector, nói rõ "chưa hỗ trợ kiến trúc này".

**Không được làm (giới hạn phạm vi):**
- Không làm build.compile thất bại vì cảnh báo nối.
- Không quét `vendor/`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-13-01 | Đơn vị | tests/test_kiem_noi.py::test_isr_tro_default_handler_bi_bat | vector giả [(15, 0x800, "Default_Handler")], symbols có "SysTick_Handler"@0x900 → báo SysTick |
| TC-M4-13-02 | Ca âm | …::test_isr_noi_dung_khong_keu | vector ô 15 trỏ SysTick_Handler → [] |
| TC-M4-13-03 | Đơn vị | …::test_doc_log_gc_sections | log có "removing unused section '.text.rtos_idle' in file 'firmware/rtos.o'" → ["rtos_idle"] |
| TC-M4-13-04 | Tích hợp (nha_that, skipif không có arm-none-eabi-gcc) | …::test_build_wiring_tren_elf_that | dự án STM32 tối thiểu có SysTick_Handler weak bị ghi đè sai tên → báo |
| TC-M4-13-05 | Cờ TẮT | …::test_co_tat_note_build_compile_y_cu | monkeypatch build → note_vi không chứa "nối" |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_xay_dung.py tests/test_arm_bien_dich.py tests/test_bien_dich_rv32.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: tái hiện ≥3/7 ca của DANH-GIA §3.1 bắt được ở bước build.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ; revert commit.

<!-- TASK M5-03 -->
<a id="m5-03"></a>
### [M5-03] Bộ đọc SVD: nạp register map thành Fact `reg:`/`field:` + `reg.lookup` — P0 · M

**Giai đoạn:** GĐ1 · thứ tự #28

**Mục tiêu:** tệp SVD được `doc.load` nạp thành Fact thanh ghi/trường bit có trích dẫn `peripheral.register.field`, thay vì bị từ chối dù `phan_loai` báo "đầy đủ".
**Loại:** Sửa lỗi thuần (hai câu trả lời mâu thuẫn) + Công cụ mới `reg.lookup` (`core=False`).
**Phụ thuộc:** Không. (M5-11 dùng kết quả này.)
**Tệp chạm tới:** `src/eide/knowledge/svd.py` (mới), `src/eide/tools/knowledge.py`, `tests/test_svd.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `knowledge/ingest.py:324-326`: XML có `<device` + `peripheral` thì trả `ra("svd", ..., DAY_DU, ...)`.
- `tools/knowledge.py:28-30`: comment nói "svd có công cụ riêng", nhưng `grep -rni svd src/` chỉ ra ingest.py và comment đó. Không có bộ đọc.
- `tools/knowledge.py:95-136` `_nap_theo_loai`: `svd` không thuộc `_LOAI_VAN_BAN` và không thuộc nhánh Office nên rơi vào `E1001 "chưa có bộ đọc"`.

**Thay đổi cần làm:**
1. `svd.py::doc_svd(path) -> TaiLieu` dùng `xml.etree.ElementTree` (không thêm phụ thuộc): duyệt `device/peripherals/peripheral` (xử lý `derivedFrom` bằng cách sao thanh ghi của ngoại vi gốc), `registers/register` (cả `cluster` một cấp), `fields/field` (`bitOffset`/`bitWidth` hoặc `bitRange` `[msb:lsb]`).
   Mỗi thanh ghi là một `Trang(so=i, chu="<P>.<R> @0x… reset=0x… …", nhan="<P>.<R>")`. `loai="svd"`, `don_vi_trich_dan="thanh ghi"`.
2. `svd.py::fact_tu_svd(tl, *, thuc_the, tier) -> list[dict]`: Fact `reg:<P>.<R>` với khoá `dia_chi` (base+offset, chuỗi hex), `reset`, `size`, `access`; Fact `field:<P>.<R>.<F>` với `bit_offset`, `bit_width`.
   `source={"doc_id","version","page":so,"cite":"<P>.<R>[.<F>]","quote":...}`. Dùng `fact_id` băm giống `docs.fact_tu_ung_vien`.
3. `_nap_theo_loai`: thêm nhánh `loai=="svd"`. `doc.load` với SVD tự ghi Fact (tầng theo `tang_mac_dinh(nguon)`, nhà sản xuất là BAC) và trả `so_thanh_ghi`, `so_truong`.
   XML hỏng thì `E2007` "SVD không đọc được: <lý do>".
4. Tool `reg.lookup(ten)` (R1, `core=False`): tìm `reg:%ten%` hoặc `field:%ten%`, trả tối đa 20 dòng gọn.

**Không được làm (giới hạn phạm vi):**
- Không tự gán tầng VANG (vẫn theo luật N1: người duyệt mới lên VANG). Không đụng ATDF/EDC ở nhiệm vụ này.
- Không nạp SVD như văn bản thô qua `nap_van_ban`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-03-01 | Tích hợp (registry) | tests/test_svd.py::test_doc_load_nap_svd | SVD tối giản (1 ngoại vi USART1 base 0x40011000, thanh ghi BRR offset 0x08 reset 0x0, field DIV_Mantissa bitOffset 4 width 12) → `doc.load` `ok`; `fact.query(subject="reg:USART1.BRR")` có `dia_chi=="0x40011008"` |
| TC-M5-03-02 | Đơn vị | tests/test_svd.py::test_derivedFrom_sao_thanh_ghi | USART2 `derivedFrom="USART1"` base 0x40004400 → có `reg:USART2.BRR` với `dia_chi=="0x40004408"` |
| TC-M5-03-03 | Đơn vị | tests/test_svd.py::test_bitRange | field `<bitRange>[15:4]</bitRange>` → `bit_offset==4`, `bit_width==12` |
| TC-M5-03-04 | Ca âm | tests/test_svd.py::test_xml_hong_noi_ro | SVD cắt cụt giữa thẻ → `not ok`, `code=="E2007"`, không ghi Fact nào |
| TC-M5-03-05 | Ca âm | tests/test_svd.py::test_xml_thuong_khong_bi_nhan_la_svd | XML không có `<peripheral>` → `phan_loai(...).loai=="xml"` (giữ hành vi cũ) |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_tri_thuc.py tests/test_ingest_v3.py tests/test_doc_van_ban.py`
- Netlist/schematic/eagle vẫn bị `doc.load` từ chối như cũ (`test_netlist_khong_bi_nap_thanh_van_ban_tho`).

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ": **34/34** (lượt đầu 28/34 — sáu chỗ LỌT đều là lỗ
      THẬT, không chỗ nào vô hiệu; hai trong sáu xanh vì dàn dựng làm hai vế trùng nhau).
- [x] Toàn bộ `pytest -q` xanh: 1 942 → **1 950**, 1 skip, 0 đỏ.
- [ ] **CHƯA ĐẠT** — quét cả máy 09/10/2026 **không có tệp `.svd` thật nào**. Ca
      `test_nap_duoc_SVD_THAT` đã viết, đánh `nha_that` + `skipif`, dò bốn chỗ hay có và SKIP.
      Không tự viết một SVD lớn rồi gọi nó là *thật*.
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md — DEV-355.

**Hoàn tác:** revert commit (Fact đã nạp có thể xoá theo `source.doc_id`).

<!-- TASK M5-05 -->
<a id="m5-05"></a>
### [M5-05] Kiểm thứ nguyên đơn vị + thống nhất khoá khoảng hợp lý + kiểm cả đường bảng — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #29

**Mục tiêu:** Fact sai thứ nguyên (vdd = 25 °C) và giá trị vô lý của tần số/nhiệt độ bị chặn ở cả đường dòng chữ lẫn đường hàng bảng.
**Loại:** Sửa lỗi thuần.
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/knowledge/docs.py`, `tests/test_doc_van_ban.py`, `tests/test_don_vi_fact.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `docs.py:356,362`: mẫu sinh khoá `"fmax"` và `"ta.max"`. `docs.py:437-447` `PHAM_VI_HOP_LY` khai `"f.max"`, `"temp.min"`, `"temp.max"`, nên hai khoá kia không bao giờ được kiểm khoảng.
- `docs.py:507-514` `hop_ly`: chỉ so độ lớn sau `ve_don_vi_co_ban`, không kiểm đơn vị. `hop_ly("vdd.max", 25, "°C")` trả `True`.
- `docs.py:526-593` `_tu_hang_bang`: không gọi `hop_ly`.
- `tools/xay_dung.py:925-944` cũng đọc `PHAM_VI_HOP_LY` (theo khoá `flash.size`/`ram.size`), nên đổi tên khoá phải giữ các khoá này.

**Thay đổi cần làm:**
1. Thêm `THU_NGUYEN_KHOA: dict[str,str]` theo TIỀN TỐ khoá (phần trước dấu chấm cuối): `vdd,vih,vil,voh,vol,vddio → "V"`, `icc,iol,ioh → "A"`, `fmax,i2c.fmax,spi.fmax → "Hz"`, `ta → "°C"`, `flash,ram,sram,eeprom → "B"`, `i2c.pullup → "Ω"`.
2. `hop_ly`: lấy `ve_si(gia_tri, don_vi)[1]`. Khoá có thứ nguyên khai báo mà đơn vị cơ bản khác thì `False` (cho phép đơn vị rỗng với khoá `B` để giữ ca `flash.size 32768` không đơn vị).
3. `PHAM_VI_HOP_LY`: thêm `"fmax": (1_000, 2e9)`, `"ta.min"`/`"ta.max": (-100, 200)`. GIỮ các khoá cũ `f.max`, `temp.*` (test cũ và xay_dung dùng).
4. `_tu_hang_bang`: trước khi `ra.append`, gọi `hop_ly(f"{khoa_goc}.{ht}", v, g.don_vi)`; sai thì bỏ.

**Không được làm (giới hạn phạm vi):**
- Không đổi tên khoá mà bộ trích sinh ra (Fact cũ trong kho người dùng phải còn khớp).
- Không đổi `ve_don_vi_co_ban` (xay_dung phụ thuộc ngữ nghĩa KB=1024 của nó).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-05-01 | Đơn vị | tests/test_don_vi_fact.py::test_sai_thu_nguyen_bi_loai | `hop_ly("vdd.max", 25, "°C") is False`; `hop_ly("icc.typ", 3.3, "V") is False` |
| TC-M5-05-02 | Đơn vị | tests/test_don_vi_fact.py::test_khoa_fmax_ta_co_khoang | `hop_ly("fmax", 20, "GHz") is False`; `hop_ly("ta.max", 900, "°C") is False` |
| TC-M5-05-03 | Đơn vị | tests/test_don_vi_fact.py::test_dong_co_dieu_kien_nhiet_do | `TaiLieu` 1 trang "VDD (max) 3.6 V at TA = 25 °C" → `trich_fact_ung_vien` cho đúng 1 Fact `vdd.max` với `don_vi=="V"` |
| TC-M5-05-04 | Đơn vị | tests/test_don_vi_fact.py::test_hang_bang_cung_bi_kiem | `Trang(1,"…", o=["VDD","25","°C"], cot=["Parameter","Max","Unit"])` → `_tu_hang_bang` trả rỗng |
| TC-M5-05-05 | Ca âm | tests/test_don_vi_fact.py::test_gia_tri_dung_khong_bi_loai | `hop_ly("vdd.max",5.5,"V")`, `hop_ly("fmax",20,"MHz")`, `hop_ly("flash.size",32768,"")`, `hop_ly("i2c.pullup.typ",4.7,"kΩ")` đều `True` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_doc_van_ban.py tests/test_tri_thuc.py tests/test_office.py tests/test_chuan_hoa.py tests/test_ing_c.py`
- `test_pham_vi_hop_ly` (mọi tham số cũ, kể cả `temp.max 85 °C` là True) và `test_han_muc_*` trong test_doc_van_ban giữ nguyên.

**Tiêu chí xong:**
- [x] Các TC mới xanh; đã "phá lại thì đỏ": **23/24** (lượt đầu 17/21). Hai chỗ LỌT là lỗ THẬT
      → thành hai phần sửa thêm; hai chỗ còn lại đã kiểm lại là **không đổi hành vi** (DEV-356).
- [x] Toàn bộ `pytest -q` xanh: 1 976 → **1 980**, 0 đỏ.
- [x] Ghi một mục vào docs/md/EIDE-DEV-LOG.md — DEV-356.

> **TC-M5-05-04 của bảng trên XANH SẴN vì một lý do khác.** Hàng `o=["VDD","25","°C"]` trả rỗng
> trên mã chưa sửa, nhưng không vì phép kiểm đơn vị nào: `"VDD"` trơn không khớp mẫu nào trong
> `_MAU_THONG_SO`. Ca kiểm thật dùng `VDD (max)` / `Supply voltage`.

**Hoàn tác:** revert commit.

<!-- TASK M5-07 -->
<a id="m5-07"></a>
### [M5-07] `fact.from_doc`: kiểm giá trị theo ranh giới token và câu trích nguyên văn — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #30

**Mục tiêu:** `fact.from_doc` chỉ nhận một giá trị khi nó đứng NGUYÊN VĂN, đúng ranh giới token, trong câu được trích, nên "27" không còn khớp "2.7 V" và "3" không còn khớp "Table 3".
**Loại:** Sửa lỗi thuần (ô xanh giả ở chốt N1).
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/tools/knowledge.py`, `tests/test_fact_from_doc.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `tools/knowledge.py:913-929`: `_chuan(x) = re.sub(r"[\s.,]", "", x).lower()`, rồi `co = _chuan(gt) in _chuan(noi_dung)`, với `noi_dung = t.chu + " ".join(t.o)` (cả đơn vị/trang).
  Nhánh hex dùng cùng phép chứa. Không kiểm `don_vi_do`, không kiểm nhãn khoá.
- Quote lưu là `noi_dung[:200]` (đầu trang, không phải chỗ có số).

**Thay đổi cần làm:**
1. Thêm tham số tuỳ chọn `trich: str` (mô tả: "câu nguyên văn ≤200 ký tự chứa con số"). Có `trich`: phải có trong `noi_dung` sau khi chỉ gộp khoảng trắng; nếu không thì `E2008`.
2. So khớp giá trị bằng regex ranh giới: `(?<![\w.,])` + `re.escape(gt)` + `(?![\w]|[.,]\d)` trên `trich` (hoặc trên `noi_dung` khi không có `trich`). KHÔNG xoá dấu chấm/phẩy.
   Nhánh hex/thập phân giữ nguyên ý (39 ↔ 0x27) nhưng dùng cùng ranh giới.
3. Giá trị ngắn (`len(gt.strip()) <= 2`) mà KHÔNG có `trich` thì từ chối `E2008` với `hint_for_agent` "số quá ngắn, hãy truyền `trich`".
4. Có `don_vi_do` thì đơn vị phải xuất hiện ngay sau số (cho phép một khoảng trắng) trong vùng khớp.
5. Ghi `source.quote = trich` nếu có, nếu không thì 200 ký tự quanh vị trí khớp.

**Không được làm (giới hạn phạm vi):**
- Không biến `trich` thành tham số bắt buộc (tránh làm vỡ lời gọi cũ của mô hình). Không đổi `fact_id`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-07-01 | Tích hợp (registry) | tests/test_fact_from_doc.py::test_27_khong_khop_2_7 | Tài liệu văn bản (nạp bằng `doc.load` như test_doc_van_ban) có dòng "VDD 2.7 V" → `fact.from_doc(gia_tri="27")` → `not ok`, `code=="E2008"` |
| TC-M5-07-02 | Tích hợp | tests/test_fact_from_doc.py::test_so_ngan_khong_trich_bi_tu_choi | Đơn vị có "Table 3 ..." → `gia_tri="3"` không có `trich` → `E2008` |
| TC-M5-07-03 | Tích hợp | tests/test_fact_from_doc.py::test_dia_chi_hex_van_nhan | Dòng "I2C address 0x27 (39)" → `gia_tri="39"`, `trich="I2C address 0x27 (39)"` → `ok`, quote đúng câu đó |
| TC-M5-07-04 | Ca âm | tests/test_fact_from_doc.py::test_gia_tri_dung_van_ghi | Dòng "#define LED1_PIN GPIO_PIN_6" (HEADER của test_doc_van_ban) → `gia_tri="GPIO_PIN_6"` → `ok` (không kêu nhầm) |
| TC-M5-07-05 | Ca biên | tests/test_fact_from_doc.py::test_trich_khong_co_trong_doan | `trich` bịa → `E2008`, `details` có `noi_dung` thật |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_doc_van_ban.py tests/test_ke_hoach.py tests/test_tri_thuc.py`
- Các test đang gọi `fact.from_doc` (grep `fact.from_doc` trong tests: test_ke_hoach.py) giữ xanh.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M5-13 -->
<a id="m5-13"></a>
### [M5-13] Chính sách phong bì cho `doc.read`/`fact.query`/`fact.extract`; sửa `_cat_chung` cắt phần tử dài — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #31

**Mục tiêu:** một lời gọi `doc.read` hoặc `fact.query` rộng không còn đưa khoảng 20k token vào ngữ cảnh; phần dư vẫn đọc lại được qua blob.
**Loại:** Sửa lỗi thuần (kết quả tool quá dài; trần chung bị lách vì không cắt phần tử).
**Phụ thuộc:** Không. Đổi khoá `"rag.ask"` → `"doc.search"` thuộc M5-01, không làm ở đây.
**Tệp chạm tới:** `src/eide/memory/envelope.py`, `tests/test_mem_a.py`.

**Hiện trạng (đã kiểm lại trong mã):**
- `envelope.py:254-268` `CHINH_SACH`: không có `doc.read`, `fact.query`, `fact.extract`.
- `envelope.py:331-343` `_cat_chung`: dict thì đệ quy cho giá trị > 500 token; list thì chỉ `d[:30]`, KHÔNG cắt từng phần tử.
- `tools/knowledge.py:441-448` `doc_read`: mặc định 40 đoạn, mỗi `chu[:2000]` + `o[:20]`. Ra trần chung: 30 đoạn × 2000 ký tự ≈ 60k ký tự ≈ 20k token (`KY_TU_MOI_TOKEN=3.0`).

**Thay đổi cần làm:**
1. `_cs_doc_read(d, args)`: giữ tối đa 8 đoạn. Mỗi `chu` cắt còn 600 ký tự quanh lần khớp đầu của `args.get("tim")` (cửa sổ ±300; không có `tim` thì 600 ký tự đầu); `o` tối đa 10.
   Trả `so_tra_ve`, giữ `so_khop`, thêm `note_vi` "còn N đoạn — gọi lại với `tu`=<so tiếp> hoặc blob.read". Dòng tóm tắt: `doc.read <doc_id>: <so_khop> khớp, hiện <k>`.
2. `_cs_fact(d, args)` cho `fact.query`/`fact.extract`: list `facts`/`fact` tối đa 30 phần tử, mỗi phần tử bỏ trường `explain` (chuỗi JSON dài) và cắt `source` còn `doc_id/page/cite`.
3. `_cat_chung`: với list, ngoài `d[:30]` còn gọi đệ quy `_cat_chung` cho phần tử có `uoc_token > 500`.

**Không được làm (giới hạn phạm vi):**
- Không đổi dữ liệu thô ghi vào blob (phải giữ nguyên văn để `blob.read`). Không cắt kết quả lỗi.
- Không đổi chính sách `fs.read`/`fs.grep` hiện có.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-13-01 | Đơn vị | tests/test_mem_a.py::test_doc_read_40_doan_khong_nuot_ngu_canh | `d={"doc_id":"DS","so_khop":40,"doan":[{"so":i,"chu":"x"*2000,"o":[],"cot":[]} for i in range(40)]}` → `boc_ket_qua(tool="doc.read", ..., blobs=KhoBlob())` → `env.shown_tokens <= 2500` và `env.blob_ref` |
| TC-M5-13-02 | Đơn vị | tests/test_mem_a.py::test_doc_read_cat_quanh_tu_khoa | Đoạn dài 5000 ký tự có "throttle" ở vị trí 4000, `args={"tim":"throttle"}` → `chu` hiển thị chứa "throttle" |
| TC-M5-13-03 | Đơn vị | tests/test_mem_a.py::test_fact_query_bo_explain | 100 Fact có `explain` 1 KB → hiển thị ≤ 30 Fact, không có khoá `explain` |
| TC-M5-13-04 | Đơn vị | tests/test_mem_a.py::test_cat_chung_cat_phan_tu_dai | Tool lạ trả `{"ds":["y"*20000]*5}` → `env.shown_tokens < 4000` |
| TC-M5-13-05 | Ca âm | tests/test_mem_a.py::test_doc_read_ngan_di_nguyen | 2 đoạn × 100 ký tự → `env.truncated is False`, dữ liệu y nguyên |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_a.py tests/test_mem_b.py tests/test_doc_van_ban.py tests/test_loop.py`
- `test_cong_cu_khong_co_chinh_sach_van_co_tran_chung`, `test_loi_KHONG_bi_cat`, `test_tep_ngan_di_qua_nguyen_ven_khong_boc_giay` giữ xanh.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M5-17 -->
<a id="m5-17"></a>
### [M5-17] Resume nạp lại bản tóm tắt C2 từ sổ cái; tường thuật cơ học phiên trước — P0 · S

**Giai đoạn:** GĐ1 · thứ tự #32

**Mục tiêu:** mở lại dự án sau một lần nén C2 thì khối `<resume>` chứa đúng bản tóm tắt đó; phiên chưa nén thì có tường thuật cơ học (0 token) về yêu cầu, lời gọi và lỗi cuối.
**Loại:** Phần A: Sửa lỗi thuần (bản tóm tắt bị mất). Phần B: Đổi hành vi (cờ `EIDE_FEATURE_RESUME_TUONG_THUAT`, mặc định TẮT).
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/memory/nen.py`, `src/eide/memory/resume.py`, `src/eide/memory/summary.py`, `src/eide/loop.py`, `src/eide/config.py`, `tests/test_mem_c.py`.

**Hiện trạng (đã kiểm lại trong mã):**
- `memory/nen.py:125-135` `BoNen.__init__`: `self.tom_tat_hien_tai = None`; chỉ gán ở `nen.py:432` khi nén thành công TRONG tiến trình.
- `memory/nen.py:433-437`: bản tóm tắt được ghi vào sổ cái: `ledger.append("compact", {"buoc": "ok", ..., "tom_tat": tt.to_dict()})`.
- `loop.py:211-226`: tiến trình mới tạo `session_id` mới, `BoNen` mới; `loop.py:499-505` dựng resume với `tom_tat_truoc=self.bo_nen.tom_tat_hien_tai` (luôn None).
- `resume.py:34-41` khi None in "Chưa có bản tóm tắt nào". `tests/test_mem_c.py:274-279` chỉ khẳng định chuỗi đó.
- ĐÃ KIỂM LẠI: phát hiện gốc đề xuất thêm "trạng thái kế hoạch" vào resume. **Bỏ phần này**, vì kế hoạch `plan:current` đã hiện ở `<pending>` mỗi lượt (`tools/ke_hoach.py:10, 575-580` `ke_hoach_dang_chay`).

**Thay đổi cần làm:**
1. (A) `summary.BanTomTat.tu_dict(d) -> BanTomTat` (đảo `to_dict`: `covers` list → tuple).
2. (A) `nen.tom_tat_cuoi_tu_so_cai(ledger) -> BanTomTat | None`: duyệt ngược `ledger.read()`, sự kiện `kind=="compact"` có `buoc=="ok"` và `tom_tat`. Gặp `buoc=="huy"` mới hơn thì trả None (người đã huỷ nén).
   `BoNen.__init__` gán `self.tom_tat_hien_tai = tom_tat_cuoi_tu_so_cai(ledger)` (bọc try/except: sổ hỏng không được làm chết khởi động).
3. (B) `resume.tuong_thuat_co_hoc(transcript_truoc) -> str` (khi cờ bật và không có bản tóm tắt): 3 lời người cuối (≤150 ký tự mỗi lời), 10 lời gọi tool cuối (tên, ok/mã lỗi, `envelope.summary_line`), lỗi cuối. Trần 1 500 ký tự.
   `loop.py` truyền transcript phiên trước (`self.phien.gan_nhat(tru=self.session_id)`) vào `dung_khoi_resume(..., tuong_thuat=...)`.

**Không được làm (giới hạn phạm vi):**
- Không nạp lại transcript cũ vào `messages`. Không sửa transcript cũ trên đĩa. Không đổi các mục khác của khối resume.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-17-01 | Tích hợp (ScriptedGateway) | tests/test_mem_c.py::test_MEM17_mo_lai_sau_C2_co_tom_tat | `bo_nen([_rsp_tom_tat(muc_tieu="bộ thu video qua Ethernet")])`, `bn.nen(_messages(20))` `ok` → agent THỨ HAI `make_agent([])` cùng cfg → `dung_khoi_resume(..., tom_tat_truoc=agent2.bo_nen.tom_tat_hien_tai)` chứa "bộ thu video qua Ethernet" và KHÔNG chứa "Chưa có bản tóm tắt" |
| TC-M5-17-02 | Đơn vị | tests/test_mem_c.py::test_tu_dict_dao_to_dict | `BanTomTat.tu_dict(tt.to_dict()).muc == tt.muc` và `covers` là tuple |
| TC-M5-17-03 | Ca âm | tests/test_mem_c.py::test_da_huy_nen_thi_khong_nap_lai | Nén ok rồi `bn.huy_nen(ms)` → agent mới có `tom_tat_hien_tai is None` |
| TC-M5-17-04 | Ca âm | tests/test_mem_c.py::test_khoi_resume_dung_bang_MA_khong_co_cho_nao_de_null | (test cũ, phiên chưa nén) vẫn có "Chưa có bản tóm tắt nào" |
| TC-M5-17-05 | Cờ / tích hợp | tests/test_mem_c.py::test_tuong_thuat_co_hoc_khi_co_bat | Cờ bật; agent 1 chạy một lượt có tool lỗi; agent 2 mở lại → resume có tên tool đó và mã lỗi. Cờ tắt → không có mục tường thuật |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_c.py tests/test_mem_b.py tests/test_mem_d.py tests/test_loop.py`
- `test_MEM17_agent_tiem_khoi_resume_DUNG_MOT_LAN`, `test_MEM17_khoi_resume_KHONG_duoc_chiem_cho_cau_hoi_cua_nguoi` giữ xanh.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC (TC-01 đỏ khi bỏ bước 2).
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit (A); tắt cờ `EIDE_FEATURE_RESUME_TUONG_THUAT` (B).


---

## Giai đoạn 2 — Ngắn hạn: P0 công sức lớn và P1 công sức nhỏ

<!-- TASK M5-01 -->
<a id="m5-01"></a>
### [M5-01] Chỉ mục tìm kiếm tài liệu BM25 (FTS5) lưu bền + công cụ `doc.search` — P0 · L

**Giai đoạn:** GĐ2 · thứ tự #33

**Mục tiêu:** tác tử tìm được đoạn liên quan trên NHIỀU tài liệu đã nạp, có xếp hạng, không cần từ khoá trùng nguyên văn, và mở lại dự án không phải phân tích lại PDF.
**Loại:** Công cụ mới (`doc.search`, `core=False`) + hạ tầng lưu trữ. Phần embedding/lai để giai đoạn 2, sau cờ `EIDE_FEATURE_DOC_EMBED` (mặc định TẮT).
**Phụ thuộc:** Không. (M5-02, M5-13 phụ thuộc nhiệm vụ này.)
**Tệp chạm tới:** `src/eide/store/db.py`, `src/eide/knowledge/chi_muc.py` (mới), `src/eide/tools/knowledge.py`, `src/eide/memory/envelope.py`, `tests/test_chi_muc.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `tools/knowledge.py:385-455` `doc_read`: lọc `tk in t.chu.lower()` trên MỘT `doc_id`, không xếp hạng; `core=False`.
- `grep -i "fts5|bm25|embedd|rerank"` trong `src/` không ra kết quả nào. GAP-44:89 ghi "Không có RAG"; MEM-42 §348 yêu cầu lai.
- `tools/knowledge.py:137-205` `_lay_tai_lieu`: mở lại dự án thì gọi lại `_nap_theo_loai` (chạy pypdf lại toàn bộ).
- `memory/envelope.py:263` đã có chính sách cho `"rag.ask"`, một tool không tồn tại.

**Thay đổi cần làm:**
1. Migration v5: `CREATE TABLE IF NOT EXISTS doc_chunks(doc_id TEXT, so INTEGER, nhan TEXT, loai_bang TEXT, chu TEXT, hash TEXT, PRIMARY KEY(doc_id, so))`
   và `CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts USING fts5(chu, doc_id UNINDEXED, so UNINDEXED, tokenize='unicode61 remove_diacritics 2')`. `down` chỉ DROP hai bảng này.
   Nếu SQLite không có FTS5 (bắt `sqlite3.OperationalError`) thì chỉ tạo `doc_chunks` và đặt cờ `Store.co_fts=False`.
2. `knowledge/chi_muc.py`: `ghi_chi_muc(store, tl: TaiLieu)` xoá rồi ghi lại các chunk của `tl.doc_id` (mỗi `Trang` là một chunk; ô bảng nối bằng " | " vào `chu`).
   `tim(store, truy_van, *, doc_ids=None, k=8) -> list[dict]` dùng `bm25(doc_fts)`. Mở rộng truy vấn bằng bảng `DONG_NGHIA` (VDD↔VCC↔"supply voltage", "start-up"↔startup↔"startup time", tSU↔setup).
   Không có FTS5 thì xếp hạng bằng số từ khoá khớp (dự phòng).
3. `doc.load` gọi `ghi_chi_muc` sau khi ghi kho thành công. Lỗi chỉ mục thì phát `notice` cảnh báo, không làm hỏng `doc.load`.
4. Công cụ `doc.search` (`core=False`, risk R1, mô tả ≤ 400 ký tự): tham số `truy_van` (bắt buộc), `doc_ids`, `k` (mặc định 8, tối đa 20).
   Trả `{"ket_qua":[{doc_id, so, trich_dan, diem, doan(≤600 ký tự quanh từ khớp)}], "so_tai_lieu_da_tim": n}`.
   Kho chưa có tài liệu nào thì trả lỗi `E2004` kèm `alternatives=["doc.load","doc.search_web"]`.
5. `envelope.py`: đổi khoá `"rag.ask"` thành `"doc.search"`.

**Không được làm (giới hạn phạm vi):**
- Không đổi chữ ký hay hành vi `doc.read` (test cũ phụ thuộc). Không đưa `doc.search` vào core ở nhiệm vụ này.
- Không thêm phụ thuộc embedding ở giai đoạn này. Không chỉ mục tệp ngoài kho (`.eide/`, transcript).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-01-01 | Đơn vị | tests/test_chi_muc.py::test_tim_xep_hang_va_dong_nghia | 2 tài liệu dựng bằng `lam_pdf` (ATmega + cảm biến 5V); `ghi_chi_muc` cả hai → `tim(store,"VCC supply")` → kết quả đầu là trang có "Supply voltage" và có `doc_id` của cả hai tài liệu |
| TC-M5-01-02 | Tích hợp (registry) | tests/test_chi_muc.py::test_doc_search_qua_cong_cu | `make_agent([])`, `doc.load` hai tài liệu → `registry.run("doc.search", {"truy_van":"pull-up"})` → `ok`, `ket_qua[0]["trich_dan"]=="trang 3"` |
| TC-M5-01-03 | Tích hợp | tests/test_chi_muc.py::test_chi_muc_song_qua_mo_lai | Nạp tài liệu, tạo agent MỚI bằng `make_agent` lần hai cùng `cfg` → `doc.search` vẫn ra kết quả mà không gọi `docs_mod.nap_tai_lieu` (monkeypatch để nổ nếu bị gọi) |
| TC-M5-01-04 | Ca âm | tests/test_chi_muc.py::test_kho_rong_thi_noi_ro | Không nạp gì → `doc.search` → `not ok`, `code=="E2004"`, có `doc.load` trong `alternatives` |
| TC-M5-01-05 | Lược đồ | tests/test_chi_muc.py::test_luoc_do_va_core_false | `registry.get("doc.search").core is False`, `len(summary_vi)<=400`; `Store.nang_cap()` lên 5 rồi `ha_cap(4)` thì không còn bảng `doc_chunks` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_doc_van_ban.py tests/test_office.py tests/test_tri_thuc.py tests/test_sch0.py tests/test_mem_a.py`
- `doc.read` trả đúng định dạng cũ; `doc.load` trả đúng các khoá cũ; migration v1→v4 không đổi.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] recall@5 trên bộ vàng của M5-21 được ghi lại (mốc cho giai đoạn embedding).
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit; `Store.ha_cap(4)` gỡ bảng (không chạm dữ liệu cũ).

<!-- TASK M5-04 -->
<a id="m5-04"></a>
### [M5-04] Trích bảng có cấu trúc từ PDF datasheet (hàng bảng + ngữ cảnh mục) — P0 · L

**Giai đoạn:** GĐ2 · thứ tự #34

**Mục tiêu:** PDF có bảng thông số, pinout hoặc register map được đọc thành `Trang` dạng hàng bảng (`o`/`cot`/`loai_bang`), để `_tu_hang_bang` và `trich_chan_ung_vien` chạy được trên PDF như trên Office.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_PDF_BANG`, mặc định TẮT; nó đổi tập Fact tác tử nhìn thấy) + phụ thuộc tuỳ chọn `pdfplumber` (MIT).
**Phụ thuộc:** M5-05 (phải có kiểm thứ nguyên trong `_tu_hang_bang` trước khi mở thêm nguồn hàng bảng).
**Tệp chạm tới:** `src/eide/knowledge/docs.py`, `src/eide/knowledge/bang_pdf.py` (mới), `pyproject.toml`, `tests/lam_pdf.py`, `tests/test_bang_pdf.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `docs.py:160-187` `nap_tai_lieu`: `Trang(i+1, p.extract_text())`. Không bao giờ đặt `o`/`cot`.
- `docs.py:372-421`: PDF đi đường theo dòng (18 regex `_MAU_THONG_SO`, mọi "số+đơn vị" trên dòng).
- `.venv` hiện chỉ có `pypdf`; không có `pdfplumber`/`pymupdf`/`numpy`.

**Thay đổi cần làm:**
1. `pyproject.toml`: thêm `pdfplumber>=0.11` vào `[project.optional-dependencies] pdf = [...]` (TUỲ CHỌN; thiếu thì giữ đường cũ, kèm `notice` một lần).
2. `bang_pdf.py::bang_tu_trang(path, so_trang) -> list[Trang]`: `pdfplumber` `page.find_tables()`. Dòng đầu là `cot`, mỗi hàng sau là một `Trang(so=<trang>, chu=" | ".join(o), o=o, cot=cot, nhan=f"trang {n} > {tieu_de_muc} > Bảng {k} hàng {r}", loai_bang=...)`.
   `loai_bang` suy từ tiêu đề cột: có Min/Typ/Max/Unit thì `"thong_so"`; có Pin + Function/Direction thì `"chan"`; có Offset/Address + Reset thì `"thanh_ghi"`.
   `tieu_de_muc` là dòng chữ đậm hoặc in hoa gần nhất phía trên bảng khớp `(absolute maximum|electrical characteristics|recommended operating|pin (description|configuration)|register map)`.
3. Trong `nap_tai_lieu`, khi cờ bật và có pdfplumber: giữ `Trang` trang-chữ cũ **và** nối thêm các `Trang` hàng bảng với `so` = 10000·trang + chỉ số (không trùng số trang). `trich_dan` dùng `nhan`.
4. `_tu_hang_bang`: nếu `nhan` chứa "absolute maximum" thì hậu tố khoá là `abs_max` (ví dụ `vdd.abs_max`) thay vì `max`. Thêm `"vdd.abs_max"` vào `KHOA_CHUAN`.
5. `tests/lam_pdf.py`: thêm `lam_pdf_bang(path, tieu_de, cot, hang)` vẽ khung bảng bằng toán tử `re S` và đặt chữ từng ô bằng `Tm` theo toạ độ (không thêm phụ thuộc).

**Không được làm (giới hạn phạm vi):**
- Không bỏ đường theo dòng (dự phòng khi không có bảng/không có thư viện). Không dùng pymupdf (AGPL).
- Không đổi `so` của các trang chữ cũ (trích dẫn "trang N" cũ phải giữ nguyên).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-04-01 | Tích hợp | tests/test_bang_pdf.py::test_bang_thong_so_doc_theo_cot | `pytest.importorskip("pdfplumber")`; cờ bật; PDF bảng "Electrical characteristics" cột Parameter/Min/Typ/Max/Unit, hàng "VDD | 1.8 | | 5.5 | V" → `trich_fact_ung_vien` có `vdd.min=1.8 V` và `vdd.max=5.5 V`, `trich_doan` trỏ "Bảng 1 hàng 1" |
| TC-M5-04-02 | Tích hợp | tests/test_bang_pdf.py::test_abs_max_khac_operating | Hai bảng: Absolute Maximum (VDD max 4.0 V), Recommended (VDD max 3.6 V) → có `vdd.abs_max=4.0` và `vdd.max=3.6`; `doi_chieu_cheo` KHÔNG báo lệch cho `vdd.max` |
| TC-M5-04-03 | Tích hợp | tests/test_bang_pdf.py::test_pinout_pdf | Bảng Pin/Function/Direction → `fact.extract_pinout` trên PDF `ok`, `so_chan>=2` |
| TC-M5-04-04 | Cờ TẮT | tests/test_bang_pdf.py::test_co_tat_y_nhu_cu | Cờ tắt → `nap_tai_lieu(ds_atmega)` cho đúng `so_trang==3` và không `Trang` nào có `o` |
| TC-M5-04-05 | Ca âm | tests/test_bang_pdf.py::test_thieu_thu_vien_khong_sap | monkeypatch import pdfplumber nổ `ImportError`, cờ bật → nạp vẫn `ok` theo đường cũ |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_tri_thuc.py tests/test_ingest_v3.py tests/test_office.py tests/test_ing_c.py tests/test_doc_van_ban.py`
- `test_TC008_trich_fact_co_so_trang_va_trich_doan` vẫn xanh với `ds_atmega`.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Precision/recall trích Fact trên bộ vàng M5-21 khi cờ bật tốt hơn khi tắt (ghi số).
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ `EIDE_FEATURE_PDF_BANG`; revert commit.

<!-- TASK M1-05 -->
<a id="m1-05"></a>
### [M1-05] Ngân sách, cắt kết quả và lượt buộc nộp cho tác tử con — P1 · M

**Giai đoạn:** GĐ2 · thứ tự #35 (kéo lên từ GĐ3 vì là tiền đề của M1-07)

**Mục tiêu:** subagent bị giới hạn theo số lời gọi và giây, kết quả công cụ bị cắt như tác tử chính, token được tính vào chi phí lượt, và luôn có một lượt cuối buộc nộp báo cáo.
**Loại:** Sửa lỗi thuần (ngân sách, kế toán) + Đổi hành vi cho lượt buộc nộp (cờ `EIDE_FEATURE_SUBAGENT_NOP`, mặc định TẮT). `task.run_many` để sau, xem mục cuối.
**Phụ thuộc:** M1-03.
**Tệp chạm tới:** src/eide/subagent.py, src/eide/config.py, tests/test_subagent.py

**Hiện trạng (đã kiểm lại trong mã):**
- subagent.py:292 — `for _ in range(dn.toi_da_goi)` đếm VÒNG LLM. `bc.so_goi` đếm lời gọi công cụ, nên một vòng có 5 call vẫn tính là 1 vòng.
- subagent.py:309-316 — `kq = r.to_model()` đi nguyên văn vào `tin`, không qua `memory.boc_ket_qua` (trần 4.000 token, memory/envelope.py:275).
- Lời gọi LLM của subagent không gọi `agent._usage_add` và không ghi ledger `llm_call`. Không kiểm `ctx.budget_left()`.
- Hết vòng thì `doc_bao_cao(chu_cuoi)` → thường E5007 "hết N lời gọi mà chưa nộp báo cáo".

**Thay đổi cần làm:**
1. Đổi vòng thành `while bc.so_goi < dn.toi_da_goi and vong < dn.toi_da_goi + 2`, kèm `tran_giay = min(90, ctx.budget_left()[1])` nếu ctx có `budget_left`.
2. Mỗi lần `llm.stream` xong: nếu `ctx.agent` có `_usage_add` thì gọi `ctx.agent._usage_add(rsp.usage, ctx)`; ghi `ghi_so("llm_call", {"subagent": ma, "usage": rsp.usage.to_dict()})`.
3. Bọc kết quả bằng `boc_ket_qua(tool=..., call_id=..., ket_qua=r, args=..., blobs=ctx.history.blobs)` khi `ctx.history` có. Đưa `env.to_model()` vào `tin`.
4. Khi cờ `subagent_nop` bật và báo cáo chưa hợp lệ lúc hết ngân sách: gọi thêm 1 lần `llm.stream(..., tools=[])` với message "NỘP BÁO CÁO JSON ngay; phần chưa làm ghi vào chua_lam."
5. `task.run_many` KHÔNG nằm trong nhiệm vụ này. Ghi vào DEV-LOG thành việc tiếp theo sau khi M1-04 ổn định.

**Không được làm (giới hạn phạm vi):**
- Không đổi `TRUONG_BAO_CAO`, `KET_LUAN`, `toi_da_goi` mặc định của từng subagent.
- Không đổi cách verifier được gọi tự động.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-05-01 | Tích hợp (ScriptedGateway) | tests/test_subagent.py::test_ngan_sach_tinh_theo_loi_goi_khong_theo_vong | verifier (toi_da_goi=10); mỗi Response có 4 call fs.glob → `bc.so_goi <= 10 + 3` (dừng ngay khi vượt), không phải 40. |
| TC-M1-05-02 | Tích hợp | tests/test_subagent.py::test_ket_qua_lon_bi_cat_trong_subagent | Tệp 300 KB trong du_an; subagent fs.read nó → message tool trong `llm.calls`/messages có trường `_cat` (envelope cắt). Chụp messages bằng phần tử kịch bản dạng hàm. |
| TC-M1-05-03 | Tích hợp | tests/test_subagent.py::test_token_subagent_vao_chi_phi_luot | ctx từ `_ctx(agent)` có `usage_luot=None`; Response có `usage=Usage(100,10)` → sau chay, `ctx.usage_luot.input_tokens == 100`. |
| TC-M1-05-04 | Cờ BẬT | tests/test_subagent.py::test_het_ngan_sach_thi_co_luot_buoc_nop | Kịch bản 10 Response gọi tool rồi 1 Response `_bc(...)` → báo cáo hợp lệ; lời gọi cuối có `tools == []`. |
| TC-M1-05-05 | Cờ TẮT | tests/test_subagent.py::test_tat_co_thi_khong_them_luot_nop | Như TC-04 nhưng cờ tắt → E5007 như cũ, đúng `toi_da_goi` vòng tool. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_tu_phat_hien_sai.py tests/test_loop.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: tỉ lệ E5007 / task.run trên phát lại giảm.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit (phần kế toán); tắt cờ (phần lượt nộp).

<!-- TASK M1-06 -->
<a id="m1-06"></a>
### [M1-06] Thi hành tính độc lập của verifier — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #36

**Mục tiêu:** khi tác tử chính gọi `task.run(subagent="verifier")`, đề cho verifier được dựng bằng mã từ danh sách bằng chứng, không nhận văn xuôi tự do chứa kỳ vọng.
**Loại:** Sửa lỗi thuần (cờ `doc_duoc_viec` được khai mà không thi hành). Phần "2 verifier / nhiệt độ khác" là Đổi hành vi, để cho M4-07/M4-08.
**Phụ thuộc:** Gộp với M4-07, M4-08: nhiệm vụ này chỉ làm phần thi hành `doc_duoc_viec`. Debate/2 verifier không viết lại ở đây.
**Tệp chạm tới:** src/eide/tools/dieu_phoi.py, src/eide/subagent.py, src/eide/hooks/standard.py, tests/test_subagent.py

**Hiện trạng (đã kiểm lại trong mã):**
- subagent.py:46 — `doc_duoc_viec: bool = True`; verifier đặt `False` (dòng 150). Grep cho thấy cờ chỉ xuất hiện ở khai báo và `to_dict`; tests/test_subagent.py::test_verifier_KHONG_thay_de_bai_chi_thay_bao_cao chỉ kiểm giá trị cờ.
- tools/dieu_phoi.py `task_run` — `SA.chay(..., viec=viec)` chuyển nguyên văn `viec` do tác tử chính viết, kể cả khi `subagent == "verifier"`.
- hooks/standard.py:557-612 — lời nhắc bảo gọi `task.run(subagent="verifier", …)` và "đưa cho nó bằng chứng, không đưa kết luận". Đây chỉ là lời khuyên.

**Thay đổi cần làm:**
1. Lược đồ `task.run`: thêm tham số tuỳ chọn `bang_chung: array of {kind, ref, khang_dinh}`.
2. Trong `task_run`: nếu `dn.doc_duoc_viec is False` thì bắt buộc có `bang_chung` (thiếu thì lỗi `E5001` với hint "verifier chỉ nhận danh sách bằng chứng"). Dựng `viec` bằng `SA.viec_cho_verifier(BaoCao(subagent="chinh", bang_chung=..., tom_tat="", ket_luan="dat"))` và BỎ QUA `viec` tự do (ghi `viec_bi_bo_qua` vào ledger).
3. Thêm hàm `SA.loc_ket_luan(chu)` bỏ các cụm kết luận ("đã đạt", "thành công", "chạy đúng", "xong") khỏi trường `khang_dinh`, giữ phần mô tả.
4. Sửa câu nhắc trong `kiem_viec_chua_ai_kiem` thành `task.run(subagent="verifier", bang_chung=[…])`.

**Không được làm (giới hạn phạm vi):**
- Không đổi đường SubagentStop (firmware/sim tuyên đạt → verifier), vốn đã đúng.
- Không đổi tập công cụ của verifier.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-06-01 | Tích hợp (ScriptedGateway) | tests/test_subagent.py::test_verifier_KHONG_nhan_viec_tu_do | Kịch bản hàm chép messages; `registry.run("task.run", {"subagent":"verifier","viec":"Code đã chạy đúng, kiểm giúp","bang_chung":[{"kind":"file","ref":"main.c","khang_dinh":"có hàm main"}],"explain":_EX}, ctx)` → message user đầu tiên gửi verifier KHÔNG chứa "đã chạy đúng" và có chứa "main.c". |
| TC-M1-06-02 | Ca âm | tests/test_subagent.py::test_verifier_thieu_bang_chung_thi_tu_choi | Gọi verifier chỉ với `viec` → `r.ok is False`, code E5001, hint nhắc `bang_chung`. |
| TC-M1-06-03 | Ca âm | tests/test_subagent.py::test_subagent_khac_van_nhan_viec_tu_do | design-review với `viec="rà soát"` → message gửi đi chứa đúng "rà soát" (không bị đổi). |
| TC-M1-06-04 | Đơn vị | tests/test_subagent.py::test_loc_ket_luan_bo_cum_ky_vong | `SA.loc_ket_luan("biên dịch thành công, đã đạt")` → không còn "thành công"/"đã đạt". |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_tu_phat_hien_sai.py`
- `test_LOI_bat_tat_co_khi_verifier_chay`: cờ `ghi_chua_kiem` tắt khi verifier chạy.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M1-07 -->
<a id="m1-07"></a>
### [M1-07] Báo cáo subagent nộp bằng lời gọi công cụ có lược đồ — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #37

**Mục tiêu:** subagent nộp báo cáo qua một "công cụ nộp" có lược đồ, không còn hỏng vì JSON xuống dòng hay bọc trong ```json```.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_BAO_CAO_CONG_CU`, mặc định TẮT). Riêng phần sửa parser là Sửa lỗi thuần.
**Phụ thuộc:** M1-05 (lượt buộc nộp dùng chung).
**Tệp chạm tới:** src/eide/subagent.py, src/eide/config.py, tests/test_subagent.py

**Hiện trạng (đã kiểm lại trong mã):**
- subagent.py `doc_bao_cao` — `dong = [d for d in chu.splitlines() if d.strip().startswith("{")]`, rồi `json.loads(dong[-1])`. JSON in nhiều dòng (`indent=1`) hay bọc ```json``` đều cho lỗi "dòng JSON không hợp lệ".
- `_CHUNG` đòi "MỘT dòng JSON duy nhất". `chay` không khai công cụ nộp nào.

**Thay đổi cần làm:**
1. Sửa lỗi thuần: `doc_bao_cao` tìm khối `{...}` cân ngoặc CUỐI CÙNG trong văn bản (bỏ hàng rào ```), rồi mới `json.loads`. Hành vi với một dòng JSON giữ nguyên.
2. Cờ `bao_cao_cong_cu`: thêm khai báo ảo `{"name":"bao_cao.nop","description":"Nộp báo cáo cuối…","parameters":{6 trường, ket_luan enum KET_LUAN, do_tin enum}}` vào `khai` (không đăng ký vào Registry). Trong `chay`, call tên `bao_cao.nop` thì lấy `call.args` làm báo cáo (chạy qua cùng phép kiểm `doc_bao_cao` trên `json.dumps(args)`) rồi dừng vòng.
3. Cập nhật `_CHUNG` (chỉ khi cờ bật) thành "kết thúc bằng lời gọi `bao_cao.nop`".

**Không được làm (giới hạn phạm vi):**
- Không đăng ký `bao_cao.nop` vào Registry chung (tác tử chính không được thấy).
- Không nới luật "đạt mà không có bằng chứng là không hợp lệ".

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-07-01 | Đơn vị | tests/test_subagent.py::test_bao_cao_JSON_nhieu_dong_van_doc_duoc | `SA.doc_bao_cao("Báo cáo:\n" + json.dumps(d, indent=1), subagent="firmware")` → `hop_le is True`. |
| TC-M1-07-02 | Đơn vị | tests/test_subagent.py::test_bao_cao_trong_hang_rao_json | Văn bản "```json\n{...}\n```" → hợp lệ. |
| TC-M1-07-03 | Ca âm | tests/test_subagent.py::test_van_xuoi_khong_JSON_van_khong_hop_le | Câu "Tôi đã kiểm hết rồi {không phải json}" → không hợp lệ (không được kêu nhầm là hợp lệ). |
| TC-M1-07-04 | Tích hợp (cờ BẬT) | tests/test_subagent.py::test_nop_bang_cong_cu_bao_cao_nop | Response gọi `bao_cao.nop` với 6 trường → `bc.hop_le`, `bc.ket_luan` đúng; `llm.calls[0]["tools"]` chứa "bao_cao.nop". |
| TC-M1-07-05 | Cờ TẮT | tests/test_subagent.py::test_tat_co_khong_khai_bao_cao_nop | Cờ tắt → "bao_cao.nop" không có trong `llm.calls[0]["tools"]`. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py`
- Bốn ca lược đồ hiện có (`test_bao_cao_khong_co_JSON...`, `test_thieu_truong...`, `test_tuyen_DAT_ma_khong_co_bang_chung...`, `test_ket_luan_la_ba_gia_tri_dong`) giữ nguyên.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ; revert phần parser nếu cần.

<!-- TASK M1-08 -->
<a id="m1-08"></a>
### [M1-08] Định tuyến mức suy nghĩ và chế độ gọi công cụ theo loại bước — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #38

**Mục tiêu:** mỗi lời gọi LLM mang một mức suy nghĩ (thinking level) và chế độ tool (AUTO/NONE) do bộ định tuyến xác định (0 token) chọn, không đổi model.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_DINH_TUYEN_NGHI`, mặc định TẮT)
**Phụ thuộc:** Không. M1-10 dùng `che_do_tool="NONE"`.
**Tệp chạm tới:** src/eide/llm/gateway.py, src/eide/llm/gemini.py, src/eide/llm/offline.py, src/eide/loop.py, src/eide/config.py, tests/test_dinh_tuyen_nghi.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- config.py:40 — `ALLOWED_MODELS = frozenset({"gemini-3.8-flash"})`; assert_allowed cưỡng chế, nên không định tuyến model được.
- gemini.py:67-75 — `GenerateContentConfig(system_instruction, temperature, max_output_tokens, seed, automatic_function_calling)`: không có `thinking_config`, không có `tool_config`.
- SDK google-genai 2.25.0 trong .venv có `types.ThinkingConfig(thinking_level=ThinkingLevel.MINIMAL|LOW|MEDIUM|HIGH)` và `types.ToolConfig(function_calling_config=FunctionCallingConfig(mode=AUTO|ANY|NONE))`. Lưu ý từ docstring SDK: từ Gemini 3.5 trở đi, `thinking_budget` bị bỏ, phải dùng `thinking_level`.
- offline.py:54 — `ScriptedGateway.stream(..., model=None, temperature=None)` có chữ ký cố định, nên thêm kwarg mới phải sửa cả ở đây.

**Thay đổi cần làm:**
1. gateway.py `LLMGateway.stream`: thêm `muc_nghi: str | None = None` ("thap"|"vua"|"cao") và `che_do_tool: str | None = None` ("AUTO"|"NONE"). ScriptedGateway và RecordingGateway nhận và ghi hai giá trị này vào `.calls[i]`.
2. gemini.py: ánh xạ thap→LOW, vua→MEDIUM, cao→HIGH vào `types.ThinkingConfig(thinking_level=...)`; `che_do_tool="NONE"` → `tool_config=ToolConfig(function_calling_config=FunctionCallingConfig(mode="NONE"))`.
3. loop.py: hàm thuần `chon_muc_nghi(ctx, vong) -> str`: plan đang `dang_soan`, vòng đầu sau câu người, sau ≥2 lỗi cùng mã → "cao"; vòng ngay sau batch chỉ-đọc toàn ok → "thap"; còn lại → "vua". Chỉ truyền khi cờ bật. Ghi `muc_nghi` vào ledger `llm_call`.
4. subagent verifier/design-review: "cao"; memory/nen.py giữ nguyên (không truyền).

**Không được làm (giới hạn phạm vi):**
- Không đổi `ALLOWED_MODELS`, không thêm model.
- Không đặt `thinking_budget` (SDK báo không hỗ trợ cho Gemini ≥3.5).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-08-01 | Đơn vị | tests/test_dinh_tuyen_nghi.py::test_scripted_nhan_muc_nghi | `ScriptedGateway([Response(text="x")]).stream(system="", messages=[], tools=[], muc_nghi="cao")` → không lỗi, `.calls[0]["muc_nghi"] == "cao"`. |
| TC-M1-08-02 | Đơn vị | tests/test_dinh_tuyen_nghi.py::test_chon_muc_nghi_xac_dinh | ctx giả: vòng 0 → "cao"; sau batch chỉ fs.read ok → "thap"; 2 lỗi E1003 liền → "cao". |
| TC-M1-08-03 | Đơn vị | tests/test_dinh_tuyen_nghi.py::test_gemini_dung_thinking_level | monkeypatch `gw._one_call` để bắt `cfg`; `GeminiGateway.__new__` + gán `cfg=ModelConfig()`, `_genai` → `stream(..., muc_nghi="thap")` → `cfg.thinking_config.thinking_level == LOW`. |
| TC-M1-08-04 | Tích hợp (cờ BẬT) | tests/test_dinh_tuyen_nghi.py::test_ledger_ghi_muc_nghi | Lượt 2 vòng → ledger `llm_call` có `muc_nghi` ở cả hai. |
| TC-M1-08-05 | Cờ TẮT | tests/test_dinh_tuyen_nghi.py::test_tat_co_khong_truyen_muc_nghi | `.calls[i]["muc_nghi"] is None` ở mọi lời gọi. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_config_model.py tests/test_mem_c.py tests/test_subagent.py`
- Cổng giả trong test_mem_c.py (`def stream(self, *, system, messages, tools, **kw)`) phải vẫn chạy, nên kwarg mới bắt buộc có mặc định.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: thoughts_tokens / lượt giảm, pass 76 TC không tụt, thì mới bật mặc định.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ.

<!-- TASK M1-20 -->
<a id="m1-20"></a>
### [M1-20] Bảng chỉ số lượt/phiên từ ledger và cổng hồi quy — P1 · M

**Giai đoạn:** GĐ2 · thứ tự #39 (kéo lên từ GĐ3 vì là tiền đề của M1-09)

**Mục tiêu:** có mô-đun tính chỉ số chuẩn từ ledger (lời gọi/lượt, cache ratio, quay vòng, cổng, verifier, finish_reason) và một lệnh CI so với mốc cơ sở.
**Loại:** Hạ tầng test/đo
**Phụ thuộc:** Không. Gộp với M4-20, M4-21: nhiệm vụ này làm phần chỉ số tính từ ledger (`eide/do_luong.py`); eval quỹ đạo và CI thuộc M4-20/M4-21.
**Tệp chạm tới:** src/eide/do_luong.py (mới), src/eide/loop.py (thêm trường ledger), tools/so_ket_qua.py (tham khảo), tests/test_do_luong.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- loop.py:678-681 — ledger `llm_call` có run_id, model, usage (in/out/cached/thoughts), tool_calls, elapsed_ms; KHÔNG có finish_reason, temperature, subagent.
- Ledger có `turn.start/turn.end` (report cost), `tool_use`, `tool_result`, `hook` (policy, Stop, ket_qua_rong), `gate`, `incident`, `subagent_stop`.
- tools/theo_doi.py dịch ledger sang chữ ("cơ chế nào đã nổ"); tools/chay_usecase.py chấm 76 TC theo "có dấu hiệu"; không có mô-đun chỉ số dùng được trong pytest/CI.

**Thay đổi cần làm:**
1. `do_luong.py`: `chi_so_luot(events) -> list[dict]` và `chi_so_phien(events) -> dict` gồm: n_llm, n_tool, ty_le_chi_doc, cached/input, thoughts/out, so_nhac_quay_vong (đếm message `_he_thong` hoặc hook), so_het_ngan_sach (notice E6002 trong ledger nếu có, hoặc report), cong_mo/duyet/bac, verifier dat/khong_dat/chua_du, phan_bo_finish_reason, token lược đồ (nếu M1-02 đã ghi).
2. loop.py: ghi thêm `finish_reason` vào `llm_call` (nếu M1-10 chưa làm) và `hook` loại `quay_vong` khi `_nhac_neu_dang_quay_vong` trả chữ.
3. CLI `python -m eide.do_luong <du_an> [--so-voi moc.json]`: in JSON; mã thoát 1 nếu pass hoặc chỉ số tụt quá ngưỡng (token/lượt +15 %, so_nhac_quay_vong +20 %).

**Không được làm (giới hạn phạm vi):**
- Không đổi định dạng các sự kiện ledger hiện có (chỉ thêm khoá). Không làm LLM-giám khảo ở đây.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-20-01 | Đơn vị | tests/test_do_luong.py::test_chi_so_phien_tu_ledger_gia | Danh sách sự kiện giả (2 llm_call usage in=100 cached=50, 3 tool_use) → `cached_ty_le == 0.5`, `n_tool == 3`. |
| TC-M1-20-02 | Tích hợp (ScriptedGateway) | tests/test_do_luong.py::test_chi_so_tu_luot_that | Một lượt kịch bản 2 vòng → `chi_so_phien(agent.ledger.read())["n_llm"] == 2`. |
| TC-M1-20-03 | Tích hợp | tests/test_do_luong.py::test_quay_vong_duoc_dem | Kịch bản như `test_tac_tu_TIM_MAI_ma_khong_lam_thi_loi_NHAC` → `so_nhac_quay_vong >= 1`. |
| TC-M1-20-04 | Ca âm | tests/test_do_luong.py::test_ledger_rong_khong_no | `chi_so_phien([])` → dict với các số bằng 0, không chia cho 0. |
| TC-M1-20-05 | Đơn vị | tests/test_do_luong.py::test_so_voi_moc_bao_tut | Mốc token/lượt 1000, hiện tại 1200 → hàm so trả `tut=True`. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_ledger_protocol.py tests/test_bo_do_phien.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Đã chạy trên ít nhất một dự án phiên thật và lưu `moc.json` làm mốc cơ sở.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit (mô-đun độc lập).

<!-- TASK M1-09 -->
<a id="m1-09"></a>
### [M1-09] Thí nghiệm A/B nhiệt độ cho Gemini 3.x — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #40

**Mục tiêu:** nhiệt độ của tác tử chính và subagent cấu hình được qua cờ, và có số đo A/B trên bộ 76 ca trước khi đổi mặc định.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_NHIET_MAC_DINH_1`, mặc định TẮT) + Hạ tầng đo
**Phụ thuộc:** M1-20 (bảng chỉ số) nên có trước để đọc kết quả.
**Tệp chạm tới:** src/eide/config.py, src/eide/loop.py, src/eide/subagent.py, tests/test_config_model.py

**Hiện trạng (đã kiểm lại trong mã):**
- config.py:198 — `temperature: float = 0.0`; gemini.py:70 dùng `self.cfg.temperature` khi `temperature is None`; `_SEED = 7`.
- loop.py:665 và subagent.py:293 không truyền `temperature`, nên luôn dùng 0.
- Mã ghi nhận ca quay vòng (loop.py:544-547: ledger.query 21 lần; docstring nang_luc.py: fs.read 28 lần).
- CHƯA KIỂM được trong container: khuyến nghị "Gemini 3 nên để temperature 1.0" là tài liệu công khai của Google cho dòng Gemini 3, chưa xác minh riêng cho 3.8-flash. Vì vậy nhiệm vụ này là THÍ NGHIỆM, không phải đổi thẳng.

**Thay đổi cần làm:**
1. `Features.nhiet_mac_dinh_1: bool = False`. Khi bật: `ModelConfig.temperature = 1.0` cho main và subagent. Các lời gọi trích xuất (memory/nen.py, fact.extract nếu có gọi LLM) truyền `temperature=0.0` tường minh.
2. Thêm biến môi trường `EIDE_NHIET_DO` (float, kẹp trong [0, 2]) để chạy quét 0 / 0.7 / 1.0 bằng tools/chay_usecase.py mà không sửa mã.
3. Ghi `temperature` vào ledger `llm_call`.
4. Viết kết quả A/B (pass rate, số lần nhắc quay vòng / 100 lượt, số lời gọi / lượt) vào DEV-LOG.

**Không được làm (giới hạn phạm vi):**
- Không đổi mặc định 0.0 khi chưa có số đo. Không bỏ seed trong nhiệm vụ này.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-09-01 | Đơn vị (cờ BẬT) | tests/test_config_model.py::test_co_nhiet_1_thi_temperature_1 | monkeypatch `EIDE_FEATURE_NHIET_MAC_DINH_1=1` → `Config.for_project(tmp).model.temperature == 1.0`. |
| TC-M1-09-02 | Cờ TẮT | tests/test_config_model.py::test_mac_dinh_van_la_0 | Không đặt biến → `== 0.0`. |
| TC-M1-09-03 | Ca biên | tests/test_config_model.py::test_bien_nhiet_do_bi_kep | `EIDE_NHIET_DO=5` → 2.0; `EIDE_NHIET_DO=abc` → giữ mặc định. |
| TC-M1-09-04 | Tích hợp (ScriptedGateway) | tests/test_loop.py::test_ledger_ghi_temperature | Một lượt → ledger `llm_call` có khoá `temperature`. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_config_model.py tests/test_loop.py tests/test_mem_c.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: bảng A/B 76 ca × 5 lần cho 0 / 0.7 / 1.0 đã ghi DEV-LOG; chỉ đề nghị bật khi pass không tụt và số lần nhắc quay vòng giảm.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ, bỏ biến môi trường.

<!-- TASK M1-10 -->
<a id="m1-10"></a>
### [M1-10] Xử lý finish_reason và chống lặp chữ khi retry — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #41

**Mục tiêu:** câu trả lời bị cắt vì MAX_TOKENS hay lời gọi hàm hỏng được xử lý có chủ đích; retry không stream lặp chữ ra Console; retry không vượt trần giây của lượt.
**Loại:** Sửa lỗi thuần (ghi finish_reason, chống lặp chữ, deadline) + Đổi hành vi cho vòng "viết tiếp" (cờ `EIDE_FEATURE_XU_LY_KET_THUC`, mặc định TẮT)
**Phụ thuộc:** M1-08 (dùng `che_do_tool`), không bắt buộc.
**Tệp chạm tới:** src/eide/llm/gemini.py, src/eide/loop.py, src/eide/config.py, tests/test_loop.py, tests/test_gemini_lich_su.py

**Hiện trạng (đã kiểm lại trong mã):**
- gemini.py:113-114 — `finish = str(cand.finish_reason)`. Với enum SDK, chuỗi có thể có dạng "FinishReason.MAX_TOKENS", nên cần chuẩn hoá bằng `.name`/`.value`.
- loop.py — không có dòng nào đọc `rsp.finish_reason` (grep). Ledger `llm_call` (loop.py:678) cũng không ghi nó.
- gemini.py:81-92 — retry bọc cả `_one_call`; `on_text(part.text)` (dòng 130) đã emit trước khi hỏng thì lần thử lại emit lại từ đầu. `time.sleep` tới 8 s mà không biết deadline.
- `max_output_tokens = 8192` (config.py:199).

**Thay đổi cần làm:**
1. gemini.py: chuẩn hoá `finish = getattr(cand.finish_reason, "name", str(cand.finish_reason))`.
2. gemini.py `stream`: theo dõi `da_phat_chu`. Nếu lỗi xảy ra sau khi đã phát chữ thì KHÔNG retry, ném `EideError("E6010", "Mô hình ngắt giữa câu trả lời.", details={"partial": True}, blame="system")`.
3. `stream` nhận `deadline: float | None` (perf_counter tuyệt đối); không ngủ quá deadline. loop truyền `time.perf_counter() + ctx.budget_left()[1]`.
4. loop.py: ghi `finish_reason` vào ledger `llm_call`. Khi cờ bật: finish "MAX_TOKENS" và không có tool_calls → append `_he_thong` "Câu trả lời bị cắt — viết tiếp từ chỗ dừng, phần dài thì ghi ra tệp bằng fs.write" rồi lặp, tối đa 1 lần mỗi lượt. "MALFORMED_FUNCTION_CALL" → nhắc lại tên và lược đồ tool liên quan, tối đa 1 lần. "SAFETY" hay "PROHIBITED_CONTENT" → console_post nói thật, không lặp.

**Không được làm (giới hạn phạm vi):**
- Không đổi `max_output_tokens`. Không đổi phân loại lỗi E6003/network_down hiện có.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-10-01 | Tích hợp (ScriptedGateway) | tests/test_loop.py::test_ledger_ghi_finish_reason | `Response(text="a", finish_reason="MAX_TOKENS")` → ledger `llm_call` có `finish_reason == "MAX_TOKENS"`. |
| TC-M1-10-02 | Tích hợp (cờ BẬT) | tests/test_loop.py::test_bi_cat_MAX_TOKENS_thi_viet_tiep_mot_lan | Kịch bản [`Response(text="phần 1", finish_reason="MAX_TOKENS")`, `Response(text="phần 2", finish_reason="MAX_TOKENS")`, `Response(text="xong")`] → đúng 2 lời gọi LLM (chỉ 1 vòng viết tiếp mỗi lượt); có message `_he_thong` chứa "bị cắt". |
| TC-M1-10-03 | Cờ TẮT | tests/test_loop.py::test_tat_co_MAX_TOKENS_ket_thuc_nhu_cu | Cùng kịch bản → 1 lời gọi LLM (cộng vòng Stop nếu chưa nói gì: Response có text nên không). |
| TC-M1-10-04 | Đơn vị | tests/test_gemini_lich_su.py::test_khong_retry_khi_da_phat_chu | `GeminiGateway.__new__`; giả `client.models.generate_content_stream` sinh 1 chunk text rồi raise lỗi 503 → `on_text` được gọi đúng 1 lần; ném E6010. |
| TC-M1-10-05 | Ca âm | tests/test_gemini_lich_su.py::test_loi_truoc_khi_phat_chu_van_retry | Lần 1 raise 503 ngay, lần 2 trả chữ → thành công, `on_text` 1 lần (monkeypatch `time.sleep`). |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_config_model.py tests/test_mem_c.py`
- `test_su_co_mo_hinh_khong_mat_viec` giữ nguyên.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: phân bố finish_reason trên phiên thật có trong bảng M1-20.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ; revert commit cho phần sửa lỗi.

<!-- TASK M1-11 -->
<a id="m1-11"></a>
### [M1-11] Trần token mỗi lượt và cửa sổ làm việc thực — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #42

**Mục tiêu:** lượt có trần token đầu vào cộng dồn, và áp lực ngữ cảnh được đo bằng usage thật trên một "cửa sổ làm việc" cấu hình được, thay cho 1M.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_TRAN_TOKEN`, mặc định TẮT). Phần đo áp lực bằng usage thật là sửa lỗi ước lượng, cũng để sau cờ vì nó đổi thời điểm nén.
**Phụ thuộc:** Liên quan M1-12 (bỏ reminder cũ làm giảm áp lực).
**Tệp chạm tới:** src/eide/config.py, src/eide/loop.py, src/eide/errors.py (nếu cần hàm mới), tests/test_loop.py, tests/test_mem_a.py

**Hiện trạng (đã kiểm lại trong mã):**
- config.py:50-60 `Budget` — chỉ có `max_tool_calls=40`, `max_seconds=300`, `compact_at`, `max_ask_rounds`.
- config.py:200 — `context_window = 1_000_000`; ngưỡng C1..C4 = 0,60/0,70/0,85/0,95.
- loop.py:1502-1504 `_context_pressure` — `asm.total_tokens + sum(len(str(m)) // 3 for m in self.messages)`. `str(m)` gồm cả `parts` (base64 `sig`) và `envelope`.
- `ctx.usage_luot` (Usage) đã được cộng dồn tại `_usage_add`.

**Thay đổi cần làm:**
1. `Budget.max_tokens_luot: int = 600_000` (biến `EIDE_TRAN_TOKEN_LUOT`, cùng kiểu `_so` trong `__post_init__`). Khi cờ bật, `_tool_loop` kiểm `ctx.usage_luot.input_tokens >= max_tokens_luot` trước mỗi lời gọi; hết thì gọi `budget_exhausted("token", lim)` và đi đúng nhánh nói-ra như hết lời gọi (`_cau_het_ngan_sach`).
2. `ModelConfig.cua_so_lam_viec: int = 200_000` (biến `EIDE_CUA_SO_LAM_VIEC`).
3. Khi cờ bật, `_context_pressure` = (usage.input_tokens của phản hồi gần nhất + ước lượng các message thêm sau đó, bỏ khoá `parts`/`envelope`) / `cua_so_lam_viec`.
4. Hàm thuần `uoc_message(m) -> int` bỏ `parts` và `envelope`, để test được.

**Không được làm (giới hạn phạm vi):**
- Không đổi ngưỡng C1..C4 (test_mem_a.py:163-167 kiểm).
- Không đổi `max_tool_calls`/`max_seconds` mặc định.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-11-01 | Đơn vị | tests/test_mem_a.py::test_uoc_message_bo_chu_ky | Message model có `parts` với `sig` dài 20.000 ký tự → `uoc_message(m)` < 100. |
| TC-M1-11-02 | Tích hợp (cờ BẬT) | tests/test_loop.py::test_het_tran_token_thi_dung_va_noi_ra | `max_tokens_luot=1000`; mỗi Response có `usage=Usage(800,10)` và một tool call → dừng sau lời gọi LLM thứ 2, có console_post chứa "hết token". |
| TC-M1-11-03 | Cờ TẮT | tests/test_loop.py::test_tat_co_khong_co_tran_token | Cùng kịch bản 3 vòng → chạy đủ 3 vòng. |
| TC-M1-11-04 | Ca biên | tests/test_loop.py::test_ap_luc_dung_usage_that | Cờ bật, Response `usage.input_tokens=150_000`, `cua_so_lam_viec=200_000` → `_context_pressure` ≈ 0,75 (±0,05) → `muc_nen` trả "C2". |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_mem_a.py tests/test_mem_b.py tests/test_mem_c.py tests/test_mem_d.py tests/test_thanh_trang_thai_va_doi_du_an.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: sai số giữa ước lượng và usage thật < 20 % trên phiên phát lại.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ.

<!-- TASK M1-15 -->
<a id="m1-15"></a>
### [M1-15] Lõi tự chạy verifier khi trả lượt có việc chưa kiểm — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #43

**Mục tiêu:** khi điều kiện "có việc đã ghi mà chưa ai kiểm" đúng, vòng lặp tự chạy verifier bằng mã thay vì chỉ nhắc mô hình, và các lời nhắc Stop được xếp ưu tiên.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_TU_KIEM_BANG_MA`, mặc định TẮT)
**Phụ thuộc:** M1-03, M1-06. Gộp với M4-10 (vòng sửa sau khi verifier bác): cùng chạm hook Stop, làm cùng đợt.
**Tệp chạm tới:** src/eide/hooks/standard.py, src/eide/hooks/base.py, src/eide/loop.py, tests/test_tu_phat_hien_sai.py

**Hiện trạng (đã kiểm lại trong mã):**
- hooks/standard.py:557-612 `kiem_viec_chua_ai_kiem` — mở khoá `task.run` và trả `StopResult(another_round=True, injection=...)` bảo mô hình gọi verifier.
- loop.py:530-543 — chỉ cho đúng 1 vòng thêm; `HookBus.stop` (hooks/base.py) nối mọi injection bằng "\n".
- kiem_chung.py `co_viec_chua_kiem(ledger, registry)` trả `(chua, dau_vet)`.
- subagent.py `viec_cho_verifier(bc)` dựng đề từ BaoCao.

**Thay đổi cần làm:**
1. `StopResult` thêm `tu_chay_verifier: bool = False` và `bang_chung: list[dict]`. Khi cờ bật, `kiem_viec_chua_ai_kiem` đặt hai trường này (bằng chứng dựng từ `dau_vet` và các changeset của lượt) thay vì bảo mô hình tự gọi.
2. loop.py `_run`: sau `hooks.stop`, nếu `stop.tu_chay_verifier` thì gọi `SA.chay(ma="verifier", viec=SA.viec_cho_verifier(...))` qua `kiem_va_chay` (M1-03). Append kết quả thành message `_he_thong` có cấu trúc ("Verifier độc lập kết luận: …"), đặt `self.ghi_chua_kiem = False`, rồi cho mô hình 1 vòng để trình bày.
3. `HookBus.stop`: thêm `uu_tien` cho mỗi hook (human_edits=1, verifier=2, assumptions=3, hoi_xong=4, các hook khác=5). Injection chỉ gộp 2 cái ưu tiên cao nhất; các cái còn lại ghi ledger `hook` với `bi_hoan`.

**Không được làm (giới hạn phạm vi):**
- Không bỏ điều kiện "đang giữa kế hoạch thì hoãn" (`_ke_hoach_dang_chay`).
- Không tăng số vòng thêm quá 1.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-15-01 | Tích hợp (cờ BẬT) | tests/test_tu_phat_hien_sai.py::test_co_viec_ghi_thi_LOI_tu_chay_verifier | Kịch bản: fs.write tệp mới, trả lời "xong", rồi Response báo cáo verifier, rồi Response trình bày → ledger có `subagent_tool`/`subagent_stop` với `subagent=="verifier"` mà mô hình KHÔNG hề gọi task.run; `agent.ghi_chua_kiem is False`. |
| TC-M1-15-02 | Cờ TẮT | tests/test_tu_phat_hien_sai.py::test_tat_co_van_chi_nhac | Cùng việc ghi → có lời nhắc chứa "task.run(subagent=" như hiện nay, không có subagent_stop. |
| TC-M1-15-03 | Ca âm | tests/test_tu_phat_hien_sai.py::test_luot_chi_doc_khong_tu_chay_verifier | Lượt chỉ fs.read → không có subagent nào chạy (kịch bản dư sẽ nổ E6004 nếu có). |
| TC-M1-15-04 | Đơn vị | tests/test_tu_phat_hien_sai.py::test_stop_chi_gop_hai_nhac_uu_tien_cao | Bus giả có 4 hook cùng nổ → `injection` chứa đúng 2 khối (human_edits, verifier). |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_tu_phat_hien_sai.py tests/test_loop.py tests/test_hoi_xong_thi_lam.py tests/test_cx_cong_tac.py tests/test_subagent.py`
- `test_dang_giua_ke_hoach_thi_HOAN_kiem_chung`, `test_chi_bat_MOT_LAN_moi_luot` giữ nguyên.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: tỉ lệ đợt việc có ghi mà có verifier chạy ≈ 100 % khi bật cờ.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ.

<!-- TASK M1-17 -->
<a id="m1-17"></a>
### [M1-17] Chống lời gọi trùng y hệt và leo thang khi quay vòng — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #44

**Mục tiêu:** lời gọi chỉ-đọc trùng y hệt (cùng tool và args, nội dung không đổi) không chạy lại; lỗi lặp cùng mã được nhắc riêng; sau lần nhắc đầu mà vẫn cày thì vòng kế buộc trả lời.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_CHONG_LAP`, mặc định TẮT)
**Phụ thuộc:** M1-08 (dùng `che_do_tool="NONE"` cho bước leo thang). Nếu chưa có thì bước leo thang chỉ chèn lời nhắc.
**Tệp chạm tới:** src/eide/loop.py, src/eide/config.py, tests/test_loop.py

**Hiện trạng (đã kiểm lại trong mã):**
- loop.py:548-618 `_nhac_neu_dang_quay_vong` — đếm theo tên (≥6) và tổng chỉ-đọc (≥10), mỗi loại nhắc 1 lần, chỉ khi `not ctx.da_ghi_gi_do`. Không có khoá theo args, không đếm theo mã lỗi, không leo thang.
- memory/compact.py:65 `_khoa_doc(m)` đã có khoá đọc (tool, path) để dedup lúc nén. Dùng lại ý tưởng này.
- tests/test_loop.py::test_ngan_sach_tool_cat_dung_cho gọi `fs.glob {"pattern":"*"}` 60 lần y hệt, nên stub vẫn phải tính vào `tool_calls_used`.

**Thay đổi cần làm:**
1. `TurnContext.da_goi_hash: dict[str, int]` (hash → chỉ số message kết quả).
2. Khi cờ bật, trong `_one_tool` trước `registry.run`: nếu tool ∈ `_CONG_CU_DOC` và `hash(tool, json.dumps(args, sort_keys=True), mtime nếu có path)` đã gặp thì không chạy, trả kết quả `{"ok": False, "code": "E5011", "message_vi": "Lời gọi y hệt #k, kết quả đã có trong ngữ cảnh.", ...}`. Vẫn `tool_calls_used += 1`.
3. Đếm `(tool, error.code)`: lần thứ 2 thì nhắc 1 lần, kèm `hint_for_agent` của lỗi.
4. Leo thang: đã nhắc quay vòng mà còn thêm ≥5 lời gọi chỉ-đọc thì vòng LLM kế đặt `che_do_tool="NONE"` (hoặc chèn lời nhắc "trả lời ngay bằng dữ kiện đang có" nếu M1-08 chưa xong).

**Không được làm (giới hạn phạm vi):**
- Không đổi ngưỡng 6/10 và chữ lời nhắc hiện có (test_loop.py kiểm "chưa ghi được gì", "Dừng tìm lại").
- Không áp cho công cụ ghi hay build.compile.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-17-01 | Tích hợp (cờ BẬT) | tests/test_loop.py::test_doc_trung_y_het_khong_chay_lai | 2 vòng `fs.read {"path":"main.c"}` → kết quả thứ 2 có code E5011; ledger `tool_result` chỉ có 1 lần chạy fs.read thật. |
| TC-M1-17-02 | Ca âm (cờ BẬT) | tests/test_loop.py::test_doc_lai_sau_khi_tep_doi_thi_chay_that | fs.read main.c, fs.write main.c (đã đọc), fs.read main.c → lần đọc thứ 2 chạy thật (mtime đổi). |
| TC-M1-17-03 | Tích hợp (cờ BẬT) | tests/test_loop.py::test_loi_cung_ma_lap_lai_thi_nhac_rieng | 2 lần fs.read tệp không có (E1003, hai đường dẫn khác nhau) → có 1 message `_he_thong` chứa "E1003". |
| TC-M1-17-04 | Cờ TẮT | tests/test_loop.py::test_tat_co_doc_trung_van_chay | Như TC-01, cờ tắt → cả hai lần đều ok. |
| TC-M1-17-05 | Hồi quy | tests/test_loop.py::test_ngan_sach_tool_cat_dung_cho (có sẵn) | Chạy thêm với cờ BẬT → vẫn E6002 và `tool_calls <= 5`. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_tu_phat_hien_sai.py tests/test_mem_b.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: số lời gọi trùng / lượt và tỉ lệ lượt hết 40 lời gọi giảm trên phát lại.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ.

<!-- TASK M2-05 -->
<a id="m2-05"></a>
### [M2-05] `option_create` nói ra REQ lạ và REQ chưa xét — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #45

**Mục tiêu:** ghi phương án mà tham chiếu REQ không có trong kho, hoặc bỏ sót REQ đang có, thì kết quả nói rõ, giống `ckm.module_set` đã làm.
**Loại:** Sửa lỗi thuần (đưa `option_create` về cùng chuẩn với `ckm.module_set`, ckm.py:286).
**Phụ thuộc:** Không.
**Tệp chạm tới:** src/eide/tools/design.py, src/eide/surfaces.py, tests/test_phuong_an_req.py (mới).

**ĐÃ KIỂM LẠI:** JSON đề xuất "có REQ lạ thì trả lỗi E5005". Đọc lại ckm.py:286–299 thì thấy chuẩn hiện có của dự án là KHÔNG chặn: chỉ trả `req_khong_co_trong_kho` kèm câu trong `note_vi` "đừng tự tạo, hỏi người dùng…". Chặn sẽ lệch chuẩn và có thể làm đỏ test_ai_quyet.py (`_dung_phuong_an` không khai REQ). Nhiệm vụ được chỉnh thành chỉ báo, không chặn.

**Hiện trạng (đã kiểm lại trong mã):**
- design.py `option_create`: ghi `dap_ung_req or []` và `khong_dap_ung or []` vào canonical, không kiểm gì. Kết quả trả về chỉ có `{id, changeset, note_vi}`.
- ckm.py:286: `req_la = [rq for rq in m.dap_ung_req if ctx.store.get(rq) is None]`, trả về trong khoá `req_khong_co_trong_kho`.

**Thay đổi cần làm:**
1. Trong `option_create`: `req_la` = các mã trong `dap_ung_req ∪ khong_dap_ung` mà `ctx.store.get(x) is None`; `chua_xet` = {id REQ trong kho} − dap_ung − khong_dap_ung. Chỉ tính `chua_xet` khi kho có ít nhất 1 REQ.
2. Trả thêm hai khoá `req_khong_co_trong_kho` và `req_chua_xet`; nối vào `note_vi` hai câu tương ứng (theo giọng của ckm.py:297).
3. surfaces.py bảng A2.3: thêm cột "Chưa xét", tính lúc vẽ (không lưu vào canonical).

**Không được làm (giới hạn phạm vi):**
- Không trả `ToolResult(False)`; không đổi lược đồ `option_create`.
- Không tự tạo REQ.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-05-01 | Đơn vị | tests/test_phuong_an_req.py::test_REQ_la_duoc_bao | fixture như test_ai_quyet.py `_ctx`; kho có FR-01 → option `dap_ung_req=["FR-09"]` → `ra["req_khong_co_trong_kho"]==["FR-09"]`, `r.ok` |
| TC-M2-05-02 | Đơn vị | …::test_REQ_chua_xet_duoc_bao | kho FR-01, FR-02 → option `dap_ung_req=["FR-01"]` → `req_chua_xet==["FR-02"]` |
| TC-M2-05-03 | Ca âm | …::test_phu_du_thi_khong_keu | `dap_ung=[FR-01]`, `khong_dap_ung=[FR-02]` → cả hai danh sách rỗng, `note_vi` không có "chưa xét" |
| TC-M2-05-04 | Ca âm | …::test_kho_chua_co_REQ_khong_keu_chua_xet | kho không có REQ → `req_chua_xet == []` |
| TC-M2-05-05 | Đơn vị | tests/test_phan_tich_thiet_ke_len_tab.py::test_A2_3_cot_chua_xet | KhoGia req + option → có cột "Chưa xét" ghi FR-02 |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ai_quyet.py tests/test_phan_tich_thiet_ke_len_tab.py tests/test_quy_trinh_lap_trinh.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M2-11 -->
<a id="m2-11"></a>
### [M2-11] `code.analyze`: loại thư mục thư viện, một lượt regex mỗi tệp, có trần — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #46

**Mục tiêu:** quét ngược nhanh trên dự án STM32 có HAL, danh sách "chỗ phải xem lại" không bị ngập, và nói rõ khi bị cắt.
**Loại:** Sửa lỗi thuần (hiệu năng và độ dài kết quả).
**Phụ thuộc:** Không (có thể làm cùng M2-08 vì cùng tệp).
**Tệp chạm tới:** src/eide/phan_tich_ma.py, src/eide/tools/xay_dung.py, tests/test_phan_tich_ma.py.

**Hiện trạng (đã kiểm lại trong mã):**
- phan_tich_ma.py:45 `BO_QUA = (".eide", ".git", "node_modules", "__pycache__", "vendor", "build", ".venv")`.
- phan_tich_ma.py:82–106 `quet`: `for q in sorted(goc.rglob("*"))`, và với mỗi tệp `for k, tm in can.items(): re.search(r"\b"+re.escape(k)+r"\b", chu)`. Độ phức tạp O(tệp × ký hiệu), không có trần.
- `.h` nằm trong `_HAM`, nên header chứa prototype cũng bị tính là "ai đang dùng".

**Thay đổi cần làm:**
1. Mở rộng `BO_QUA` thêm "Drivers", "Middlewares", "CMSIS", "third_party". Thêm tham số `bo_qua_them: tuple = ()` cho `quet`.
2. Gộp mọi ký hiệu thành một regex `\b(?:a|b|c)\b`, chạy `finditer` mỗi tệp một lần, gom tên khớp.
3. Thêm hằng `TRAN_TEP_QUET = 2000` và `TRAN_GIAY = 10.0`; quá trần thì dừng và trả cờ. `quet` trả thêm thông tin qua thuộc tính module hoặc một đối tượng kết quả mới `KetQuaQuet(tep: list[TepMa], da_cat: bool, so_tep_da_quet: int)`. Giữ `quet()` cũ trả `list[TepMa]` và thêm `quet_day_du()` cho đường mới.
4. Tách `ai_dung` thành nơi gọi `.c` và nơi khai báo `.h`; trong tài liệu, mục "khai báo" in riêng và không tính vào `cho_phai_xem_lai`.
5. `code_analyze` nói "đã dừng ở N tệp" khi `da_cat`.

**Không được làm (giới hạn phạm vi):**
- Không đổi chữ ký `quet(goc, tep)`; không đổi khoá kết quả hiện có của `code.analyze`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-11-01 | Đơn vị | tests/test_phan_tich_ma.py::test_bo_qua_Drivers | `Drivers/hal.c` gọi ký hiệu → không có trong `ai_dung` |
| TC-M2-11-02 | Đơn vị | …::test_tran_tep_bao_da_cat | monkeypatch `TRAN_TEP_QUET=3`, 10 tệp → `quet_day_du(...).da_cat is True` |
| TC-M2-11-03 | Đơn vị | …::test_header_khong_tinh_la_cho_phai_xem_lai | `hal.h` khai prototype, `app.c` gọi → `cho_phai_xem_lai == ["app.c"]` |
| TC-M2-11-04 | Ca âm | …::test_ket_qua_giong_cu_tren_du_an_nho | kịch bản `test_code_analyze_tra_loi_cau_AI_DANG_DUNG` → vẫn có "app.c" |
| TC-M2-11-05 | Đo | …::test_mot_luot_regex_moi_tep | monkeypatch `re.search` đếm lời gọi → 0 (đã chuyển sang regex gộp) |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_quy_trinh_lap_trinh.py tests/test_phan_tich_thiet_ke_len_tab.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Đo thời gian `code.analyze` trên dự án F469: ghi trước/sau vào DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M2-13 -->
<a id="m2-13"></a>
### [M2-13] Subagent `sw-design-review` và checklist rà thiết kế phần mềm trước G-DESIGN — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #47

**Mục tiêu:** trước khi chốt phương án cho việc tạo mới, có một góc nhìn phản biện độc lập về kiến trúc phần mềm, và kết quả hiện trên thẻ G-DESIGN.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_RA_SOAT_PHAN_MEM`, mặc định TẮT). Định nghĩa subagent và skill mới thì luôn có.
**Phụ thuộc:** Gộp với M1-16 và M2-04. Khung "phản biện + trọng tài" chỉ làm một lần; nếu M1-16 đã dựng thì nhiệm vụ này chỉ thêm định nghĩa + checklist + điểm móc.
**Tệp chạm tới:** src/eide/subagent.py, src/eide/skills/sw-design-review-checklist.md (mới), src/eide/hooks/standard.py, src/eide/config.py, tests/test_subagent.py.

**Hiện trạng (đã kiểm lại trong mã):**
- subagent.py:82–91: `design-review` chỉ dành cho mạch (công cụ ckm.graph, board.check, eda.*; prompt nói "đường dẫn khối/net").
- skills/design-review-checklist.md: 6 mục, toàn về mạch (net hở, pull-up, mức logic…).
- policy.yaml:211 `POL-DESIGN-choose`: `store.option_choose|board.freeze` → ask, gate G-DESIGN.

**Thay đổi cần làm:**
1. Thêm `SUBAGENT["sw-design-review"] = DinhNghia(ma="sw-design-review", ten="Rà soát thiết kế phần mềm", cong_cu=("store.get","store.list","fs.read","fs.glob","fs.grep","build.map","code.analyze"), toi_da_goi=10, system=_CHUNG + ...)`. Prompt liệt kê 7 mục: phân tầng/hướng phụ thuộc; ngân sách thời gian ISR / vòng điều khiển / nền; tài nguyên chia sẻ và khoá; trạng thái lỗi và phục hồi; Flash/RAM; khả năng kiểm thử; REQ không phương án nào đáp ứng. (`code.analyze` có `writes_artefact`, nên nếu muốn giữ chỉ-đọc thì thay bằng `code.static` của M2-09.)
2. Viết skill `sw-design-review-checklist.md` theo định dạng của design-review-checklist.md (`tu_khoa:`, `khi_nao:`).
3. Khi cờ bật, hook pre_tool_use cho `store.option_choose`: nếu kho có ≥2 option và chưa có báo cáo rà soát trong lượt, gọi `subagent.chay(ma="sw-design-review", ...)` một lần rồi đính `tom_tat` + các phát hiện vào `call` để thẻ G-DESIGN hiện. Trần 1 lần mỗi lượt.

**Không được làm (giới hạn phạm vi):**
- Không sửa `design-review` (mạch). Không chặn `option_choose` dựa trên kết quả rà soát.
- Không cho subagent mới công cụ ghi.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-13-01 | Đơn vị | tests/test_subagent.py::test_sw_design_review_ton_tai_va_chi_doc | `SUBAGENT["sw-design-review"]` có; mọi công cụ trong `cong_cu` đều không `writes_artefact` (tra build_registry) |
| TC-M2-13-02 | Đơn vị | …::test_skill_sw_review_tim_duoc | `tim_skill("rà soát kiến trúc phần mềm")` chứa "sw-design-review-checklist" |
| TC-M2-13-03 | Tích hợp (ScriptedGateway) | …::test_option_choose_co_bat_goi_ra_soat_mot_lan | cờ bật, 2 option, kịch bản: báo cáo JSON của subagent rồi phản hồi chính → sổ cái có `sw-design-review` đúng 1 lần |
| TC-M2-13-04 | Cờ TẮT | …::test_co_tat_khong_goi_ra_soat | cờ tắt → không có lời gọi subagent; `test_cau_CO_CHON_thi_van_chot_duoc` vẫn xanh |
| TC-M2-13-05 | Ca âm | …::test_mot_phuong_an_khong_ra_soat | kho chỉ 1 option → không gọi subagent |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_ai_quyet.py tests/test_policy_tools.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Eval 76 ca với cờ bật không tụt; ghi số token thêm mỗi lần chốt.
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ.

<!-- TASK M2-14 -->
<a id="m2-14"></a>
### [M2-14] Subagent `firmware`: "xong" phải gồm test, có vòng tự sửa có trần — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #48

**Mục tiêu:** worker firmware chỉ tuyên `dat` khi build có ảnh, test trên máy chủ (nếu có) không hỏng và không thêm cảnh báo mới; tự sửa tối đa 3 vòng.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_FIRMWARE_KIEM`, mặc định TẮT).
**Phụ thuộc:** M1-03 phải xong trước (theo brief; liên quan ngân sách lời gọi của subagent, VIEC-CHO-LAM mục 6).
**Tệp chạm tới:** src/eide/subagent.py, src/eide/config.py, tests/test_subagent.py.

**Hiện trạng (đã kiểm lại trong mã):**
- subagent.py:92–102 `firmware`: `cong_cu` gồm fs.read, fs.write, fs.edit, fs.glob, fs.grep, fs.stat, build.compile, build.map, env.check, fact.query, doc.read, memory.read, store.get. Không có test.run, test.sensitivity.
- Prompt: "`ket_luan: dat` chỉ khi build.compile trả về có tệp ảnh"; `toi_da_goi` mặc định 12.
- subagent.py:269 `chay`: `dn = SUBAGENT.get(ma)` là hằng module, không xét cờ.
- subagent.py:164 `CAN_KIEM_CHUNG = ("firmware", "sim-runner")`: verifier vẫn chạy sau.

**Thay đổi cần làm:**
1. Thêm hàm `lay_dinh_nghia(ma, features) -> DinhNghia | None`: với `firmware` khi cờ `firmware_kiem` bật thì trả bản sao (`dataclasses.replace`) có thêm `test.run`, `test.sensitivity` vào `cong_cu`, `toi_da_goi=18`, và prompt thêm điều kiện (b) test.run không ca hỏng nếu có test/, (c) không có cảnh báo -Wall mới.
2. `chay` dùng `lay_dinh_nghia(ma, getattr(ctx.config, "features", None))` thay cho `SUBAGENT.get(ma)`.
3. Trong `chay`: đếm số lần `build.compile`/`test.run` trả `ok=False` liên tiếp; ≥3 thì chèn một tin `user` "Đã 3 vòng sửa không qua — nộp báo cáo `chua_dat` kèm lỗi cuối". Chỉ áp cho firmware khi cờ bật.

**Không được làm (giới hạn phạm vi):**
- Không đổi `SUBAGENT["firmware"]` gốc (cờ tắt thì y hệt); không đổi verifier.
- Không đổi `TRUONG_BAO_CAO`/`KET_LUAN`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-14-01 | Đơn vị | tests/test_subagent.py::test_firmware_co_bat_co_test_run | `lay_dinh_nghia("firmware", Features(firmware_kiem=True)).cong_cu` chứa "test.run" (mã cũ: ImportError) |
| TC-M2-14-02 | Cờ TẮT | …::test_firmware_co_tat_y_cu | `lay_dinh_nghia("firmware", Features()) == SUBAGENT["firmware"]` |
| TC-M2-14-03 | Tích hợp (ScriptedGateway) | …::test_ba_vong_build_hong_thi_bi_nhac_nop_bao_cao | kịch bản 3 lần gọi build.compile (monkeypatch trả ok=False) → tin thứ 4 gửi LLM chứa "3 vòng" |
| TC-M2-14-04 | Ca âm | …::test_build_hong_mot_lan_khong_nhac | 1 lần hỏng rồi qua → không có lời nhắc |
| TC-M2-14-05 | Hồi quy | …::test_task_run_tu_goi_verifier_khi_firmware_tuyen_dat | ca có sẵn (test_subagent.py:121) vẫn xanh khi cờ bật |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_quy_trinh_lap_trinh.py tests/test_dot_bien.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Đo tỉ lệ verifier trả `khong_dat` sau firmware, cờ bật so với tắt.
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ `firmware_kiem`.

<!-- TASK M3-02 -->
<a id="m3-02"></a>
### [M3-02] ERC mức logic hai chiều (VOL ≤ VIL) và VIH dạng tỉ lệ ×VDD — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #49

**Mục tiêu:** Luật mức logic kiểm cả mức thấp và lề nhiễu, và đọc đúng VIH/VIL ghi dạng `0.7×VDD` thay vì đọc nhầm thành 0,7 V hoặc bỏ qua.
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** M3-01. Dùng chung cách lấy rail từ `ap_danh_dinh`.
**Tệp chạm tới:** `src/eide/knowledge/erc.py`, `src/eide/knowledge/compare.py`, `src/eide/knowledge/docs.py`, `tests/test_erc.py`, `tests/test_tri_thuc.py`

**Hiện trạng (đã kiểm lại trong mã):**
- erc.py:343 `muc_logic_tren_net` chỉ tra `voh` và `vih`. compare.py:192 `muc_logic` chỉ so `voh >= vih`.
- docs.py:349, 351 trích được `vil.max` và `vol.max`, nhưng `KHOA` (erc.py:40) không có hai khoá này, nên ERC không bao giờ thấy chúng.
- docs.py:405 `_SO_DON_VI` bắt "số + đơn vị". Chuỗi "0.7 VCC" bị bắt thành 0,7 V; `hop_ly("vih.min", 0.7, "V")` vẫn qua vì `PHAM_VI_HOP_LY` là 0,3–60 (docs.py:443).

**Thay đổi cần làm:**
1. Thêm `"vol": ("vol","vol.max","v_ol")` và `"vil": ("vil","vil.max","v_il")` vào `KHOA`.
2. Thêm hàm `muc_logic_thap(ra, vao)` trong compare.py, cùng khuôn với `muc_logic` (dùng `_chan_dong`): VOL ≤ VIL thì đạt, ngược lại blocker. Thêm `"muc_logic_thap"` vào `LUAT` và `MO_TA_LUAT`.
3. Trong `muc_logic_tren_net`: với mỗi cặp phát–thu đã có, nếu có `vol` và `vil` thì thêm phát hiện `muc_logic_thap`. Khi cả hai chiều đạt nhưng lề `NM_H` hoặc `NM_L` < 0,2 V thì thêm `canh_bao` mức minor, luật `le_nhieu`.
4. Trong docs.py: trước khi bắt `_SO_DON_VI` trên một dòng VIH/VIL, dò mẫu `r"(0[.,]\d+)\s*[x×*·]\s*V\s*(DD|CC)(IO)?"`. Gặp thì tạo ứng viên với `don_vi="xVDD"`, giá trị là tỉ lệ, và không tạo ứng viên volt từ cùng con số đó.
5. Trong ERC: Fact có `unit == "xVDD"` thì nhân với rail của chân (lấy rail của net nguồn nối chân `power_in` cùng lá, theo M3-01). Không có rail thì trả `chua_du_du_kien` và ghi "VIH dạng tỉ lệ, chưa biết VDD".

**Không được làm (giới hạn phạm vi):**
- Không đổi khoá đang trích (`vih.min`, `vil.max`…) và không đổi chữ ký `trich_fact_ung_vien`.
- Không đổi câu chữ của phát hiện `muc_logic` cũ (test hiện có so chuỗi "SDA", "U1.27").

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-02-01 | Đơn vị | tests/test_erc.py::test_muc_thap_VOL_lon_hon_VIL_bi_chan | `_fact pin:U1.27 vol 0.9 V`, `pin:U2.5 vil 0.6 V` → `_tim(ds,"muc_logic_thap","khong_dat")` có, blocker |
| TC-M3-02-02 | Ca âm | tests/test_erc.py::test_muc_thap_tuong_thich_thi_dat | vol 0.4, vil 0.9 → không có `khong_dat` của `muc_logic_thap` |
| TC-M3-02-03 | Đơn vị | tests/test_erc.py::test_le_nhieu_hep_thi_canh_bao | voh 2.2/vih 2.1, vol 0.4/vil 0.9 → có `le_nhieu` `canh_bao` |
| TC-M3-02-04 | Đơn vị | tests/test_tri_thuc.py::test_VIH_dang_ti_le_VDD_khong_doc_thanh_volt | PDF (dùng `lam_pdf`) có dòng "VIH Input High Voltage 0.7 × VCC" → ứng viên `vih.min` có `don_vi=="xVDD"`, không có ứng viên 0,7 V |
| TC-M3-02-05 | Tích hợp | tests/test_erc.py::test_VIH_ti_le_nhan_voi_rail | `pin:U2.5 vih 0.7 unit xVDD`, rail 3V3, `pin:U1.27 voh 2.0` → khong_dat (2,0 < 2,31) |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py tests/test_tri_thuc.py tests/test_ing_c.py tests/test_doc_van_ban.py`
- `test_muc_logic_khong_tuong_thich_bi_chan`, `test_muc_logic_tuong_thich_thi_dat`, `test_TC008_trich_fact_co_so_trang_va_trich_doan` giữ nguyên.

**Tiêu chí xong:**
- [ ] TC xanh, đã phá lại thì đỏ từng TC.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-06 -->
<a id="m3-06"></a>
### [M3-06] Pull-up I2C: không đếm điện trở nối tiếp, kiểm Rmin/Rmax — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #50

**Mục tiêu:** Chỉ điện trở có đầu kia lên rail nguồn mới được tính là pull-up, và R quá nhỏ (vượt IOL 3 mA) hay quá lớn (rise time) đều bị báo.
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** M3-01 (đọc rail `ap_danh_dinh`).
**Tệp chạm tới:** `src/eide/knowledge/erc.py`, `src/eide/knowledge/compare.py`, `tests/test_erc.py`

**Hiện trạng (đã kiểm lại trong mã):**
- erc.py:454 `r = sorted({c.partition(".")[0] for c in chan if ...upper().startswith("R")})`: mọi lá ref R* có một chân trên net SDA/SCL đều được đếm là pull-up.
- compare.py:264 `pull_up`: chỉ cảnh báo khi `r > rmax*2`, không bao giờ kiểm R quá nhỏ.
- Fixture `bo`: R1 chỉ nối chân `1` vào SDA, chân kia không nối gì. Test `test_mot_cum_pull_up_thi_dat` cần R1 vẫn được đếm.

**Thay đổi cần làm:**
1. Trong `pull_up_bus`, với mỗi R trên net bus, tìm net điện của chân còn lại (duyệt `phang` tìm `REF.x` với x khác chân trên bus):
   - Chân kia nằm trên net nguồn (nhóm có `loai` power/rail): pull-up.
   - Chân kia nằm trên net tín hiệu khác: điện trở nối tiếp, KHÔNG đếm. Ghi vào `bang_chung` "R? nối tiếp".
   - Chân kia không nối gì: vẫn đếm (giữ tương thích), thêm câu "chưa biết đầu kia của R1 nối đâu".
2. Khi có đúng một cụm và biết rail + giá trị R (`canonical.gia_tri` của lá, chuẩn hoá bằng `chuan_hoa`): tính `Rmin=(Vdd−0,4)/0,003` bằng mã. Nếu R < Rmin thì `canh_bao` major, câu nêu hai số. Nếu có Fact `cb` (điện dung bus) thì tính `Rmax=tr/(0,8473·Cb)` với tr=1000 ns (chế độ chuẩn, ghi rõ giả định).
3. Hai R trên cùng bus thì báo giá trị song song tương đương bên cạnh câu "gấp đôi" hiện có.

**Không được làm (giới hạn phạm vi):**
- Không đổi câu chữ đang được test so: "R1 ở /board/sense", "gấp đôi", "tìm cả tuần", "open-drain", "4,7 kΩ".

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-06-01 | Đơn vị | tests/test_erc.py::test_dien_tro_noi_tiep_khong_tinh_la_pull_up | xoá nối R1; thêm R5 (33R) với chân 1 trên SDA, chân 2 trên net tín hiệu `SDA_MCU` → `pull_up/khong_dat` (thiếu pull-up) |
| TC-M3-06-02 | Ca âm | tests/test_erc.py::test_pull_up_noi_tiep_cung_bus_khong_bao_hai_cum | giữ R1, thêm R5 nối tiếp như trên → KHÔNG có `canh_bao` "hai cụm" |
| TC-M3-06-03 | Đơn vị | tests/test_erc.py::test_pull_up_qua_nho_vuot_IOL | R1 `gia_tri="470"`, chân 2 nối 3V3 → `canh_bao` có "1,0 kΩ" hoặc Rmin |
| TC-M3-06-04 | Hồi quy | tests/test_erc.py::test_mot_cum_pull_up_thi_dat (đã có) | vẫn xanh: R1 chân kia không nối gì vẫn được đếm |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py`
- Các test pull-up và `test_HIER17_moi_phat_hien_noi_ro_o_khoi_nao` giữ nguyên.

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M4-17 -->
<a id="m4-17"></a>
### [M4-17] Đo được độ phủ C trên macOS (xcrun llvm-cov), có gcov, có dòng chưa phủ — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #51

**Mục tiêu:** `test.run` đo được độ phủ trên macOS mặc định (Xcode CLT) và trên gcc, kèm % nhánh/hàm theo tệp sản phẩm và danh sách dòng chưa phủ.
**Loại:** Sửa lỗi thuần (cột độ phủ gần như luôn "chưa đo được") + mở rộng dữ liệu trả về
**Phụ thuộc:** Không
**Tệp chạm tới:** src/eide/build/mo_phong.py, tests/test_do_phu.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- mo_phong.py:457-461 `_do_phu`: `pd = which("llvm-profdata") or which("xcrun")` nhưng `cov = shutil.which("llvm-cov")`. Trên macOS không có llvm-cov trong PATH thì trả `do_duoc False`.
- mo_phong.py:396 `co_phu` bật cho tên kết thúc "cc" (gồm gcc), rồi gcc hỏng `-fprofile-instr-generate` và rơi về không đo (406-409); không có nhánh gcov.
- mo_phong.py:469-474 chỉ đọc dòng TOTAL, lấy `ty[1]` (cột %).

**Thay đổi cần làm:**
1. `_lenh_llvm(ten)`: `which(ten)` hoặc `["xcrun", ten]` khi có xcrun. Dùng cho cả profdata và cov.
2. Nhánh gcc: nhận gcc thật (`cc --version` chứa "gcc"/"Free Software"), dùng `--coverage`, chạy `gcov -b -j <tệp.gcda>` và đọc JSON.
3. `llvm-cov export -format=text -summary-only` → % dòng/nhánh/hàm theo từng tệp; lọc bỏ tệp test (`tep_test`), giữ tệp sản phẩm. `llvm-cov show -show-line-counts` → `dong_chua_phu: [{tep, dong}]` (≤30).
4. Giữ khoá cũ `do_phu.dong` (chuỗi %) để test cũ và bề mặt không vỡ.

**Không được làm (giới hạn phạm vi):**
- Không làm test.run thất bại vì không đo được phủ.
- Không cài llvm.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-17-01 | Đơn vị (monkeypatch shutil.which) | tests/test_do_phu.py::test_khong_co_llvm_cov_nhung_co_xcrun_thi_dung_xcrun | which("llvm-cov") None, which("xcrun") "/usr/bin/xcrun" → lệnh cov bắt đầu bằng ["xcrun","llvm-cov"] |
| TC-M4-17-02 | Đơn vị | …::test_doc_export_theo_tep_bo_tep_test | JSON export mẫu có test/t.c và firmware/pid.c → chỉ còn pid.c |
| TC-M4-17-03 | Tích hợp (skipif không có clang/xcrun) | …::test_test_run_tren_macos_do_duoc_phu | test.run dự án mẫu → do_phu.do_duoc True, có "dong_chua_phu" |
| TC-M4-17-04 | Ca âm | …::test_khong_co_cong_cu_nao_thi_noi_ro | which trả None hết → do_duoc False, vi_sao không rỗng |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_xay_dung.py tests/test_dot_bien.py`
- test_do_phu_khong_do_duoc_thi_NOI_RA_chu_khong_bo_cot giữ nguyên.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: trên máy macOS của dự án, test.run báo do_duoc True.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M4-18 -->
<a id="m4-18"></a>
### [M4-18] Mở khoá công cụ kiểm thử theo giai đoạn — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #52

**Mục tiêu:** Khi tác tử vừa ghi mã firmware/test/HDL, các công cụ kiểm thử tương ứng tự hiện trong danh sách nó nhìn thấy, không phải chờ `tool.search`.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_MO_KHOA_KIEM_THU`, mặc định TẮT)
**Phụ thuộc:** Gộp với M1-02 (cùng chạm cơ chế hiển thị công cụ): dùng chung hàm mở khoá của M1-02 nếu có
**Tệp chạm tới:** src/eide/loop.py, src/eide/subagent.py, src/eide/config.py, tests/test_mo_khoa_kiem_thu.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- tools/registry.py:97 `_unlocked`; 139-141 `visible()` = core hoặc trong `_unlocked`.
- test.run/test.sensitivity (xay_dung.py:738, 802), hdl.sim (tools/hdl.py:111), task.run (dieu_phoi.py:42) đều có `core=False`.
- Tiền lệ: hooks/standard.py:590-592 tự `_unlocked.add("task.run")`.
- subagent.py:106 sim-runner không có test.sensitivity.

**Thay đổi cần làm:**
1. Cờ `mo_khoa_kiem_thu`.
2. loop.py ngay sau khối `da_ghi_gi_do` (~885-888): cờ bật thì ghi vào `firmware/**|test/**|tests/**` → `_unlocked |= {"test.run","test.sensitivity"}`; ghi `*.v|*.sv` → `{"hdl.sim","hdl.lint"}`. Ghi sổ `hook: mo_khoa_kiem_thu`.
3. Thêm `test.sensitivity` vào `SUBAGENT["sim-runner"].cong_cu` (luôn làm, vì sim-runner chỉ dùng qua task.run).

**Không được làm (giới hạn phạm vi):**
- Không đổi `core` của công cụ nào.
- Không mở khoá công cụ R3 (target.*).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-18-01 | Tích hợp (make_agent) | tests/test_mo_khoa_kiem_thu.py::test_ghi_firmware_thi_test_run_hien | cờ bật; ScriptedGateway fs.write firmware/pid.c rồi text → lần gọi LLM thứ 2 có "test.run" trong `llm.calls[1]["tools"]` |
| TC-M4-18-02 | Cờ TẮT | …::test_co_tat_khong_mo_khoa | như trên, cờ tắt → không có "test.run" |
| TC-M4-18-03 | Ca âm | …::test_ghi_tai_lieu_khong_mo_khoa | cờ bật, fs.write docs/a.md → không có "test.run" |
| TC-M4-18-04 | Đơn vị | …::test_sim_runner_co_test_sensitivity | "test.sensitivity" in SA.SUBAGENT["sim-runner"].cong_cu |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_chon_chuoi_cong_cu.py tests/test_subagent.py tests/test_policy_tools.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: tỉ lệ phiên có ghi mã mà gọi test.run tăng; bật mặc định chỉ khi 76 ca không tụt.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ; revert phần sim-runner.

<!-- TASK M5-10 -->
<a id="m5-10"></a>
### [M5-10] Tra Fact theo id chính xác; `fact.query` trả tổng thật và sắp theo tầng — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #53

**Mục tiêu:** `fact.review`/`fact.compare` tìm đúng Fact theo khoá chính dù kho có trên 1000 Fact, và `fact.query` báo đúng tổng số khớp, sắp theo tầng, có lựa chọn khớp chủ thể chính xác.
**Loại:** Sửa lỗi thuần.
**Phụ thuộc:** Không. (M5-08 phụ thuộc nhiệm vụ này.)
**Tệp chạm tới:** `src/eide/store/db.py`, `src/eide/tools/knowledge.py`, `src/eide/tools/builtin.py`, `tests/test_fact_query.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `tools/knowledge.py:974-976` (`fact_review`): `[f for f in ctx.store.query_facts(limit=1000) if f["fact_id"] == fid]`. `tools/knowledge.py:1012` (`fact_compare`): `{f["fact_id"]: f for f in ctx.store.query_facts(limit=1000)}`.
- `store/db.py:496-511` `query_facts`: `subject LIKE %x%`, không `ORDER BY`, `LIMIT 100` mặc định. `dem_fact` có sẵn (`db.py:513`) nhưng `fact.query` (`builtin.py:250`) trả `count=len(rows)`.

**Thay đổi cần làm:**
1. `Store.get_fact(fact_id) -> dict | None` (SELECT theo PRIMARY KEY, kể cả Fact đã bị thay, kèm trường `superseded_by`).
2. `fact_review`, `fact_compare` dùng `get_fact`. `fact_review` báo `khong_thay=[...]` cho id không có, thay vì im lặng.
3. `query_facts(..., chinh_xac: bool=False)`: `True` thì `subject = ? OR subject LIKE ? || '@%'`. Thêm `ORDER BY CASE tier WHEN 'VANG' THEN 0 WHEN 'BAC' THEN 1 WHEN 'NGUOI' THEN 2 ELSE 9 END, key`.
4. `fact.query`: thêm tham số `chinh_xac` (mặc định False, giữ hành vi), trả `count` = `dem_fact(...)`, `so_tra_ve=len(rows)`, và `bi_cat` khi `count > so_tra_ve`.

**Không được làm (giới hạn phạm vi):**
- Không đổi mặc định LIKE của `query_facts` (ckm, assemble, xay_dung phụ thuộc). Không đổi định dạng bản ghi Fact trả về.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-10-01 | Tích hợp (registry) | tests/test_fact_query.py::test_review_tim_duoc_fact_thu_1001 | `put_fact` 1001 Fact (fact_id `f-0000`…`f-1000`) → `fact.review(fact_ids=["f-1000"], xac_nhan=True)` → `da_doi==1` |
| TC-M5-10-02 | Tích hợp | tests/test_fact_query.py::test_compare_tim_duoc_fact_thu_1001 | Như trên, `fact.compare(luat="qua_ap", fact_a="f-1000", fact_b="f-0001")` → `ok` |
| TC-M5-10-03 | Tích hợp | tests/test_fact_query.py::test_query_bao_tong_that | 150 Fact cùng subject → `fact.query(subject=...)` → `count==150`, `so_tra_ve==100`, `bi_cat is True` |
| TC-M5-10-04 | Đơn vị | tests/test_fact_query.py::test_chinh_xac_khong_tron_chip | Fact cho `chip:STM32F407` và `chip:STM32F469@1.0.0` → `query_facts(subject="chip:STM32F469", chinh_xac=True)` chỉ ra F469 |
| TC-M5-10-05 | Ca âm | tests/test_fact_query.py::test_mac_dinh_van_LIKE | Không truyền `chinh_xac` → `query_facts(subject="STM32F4")` vẫn ra cả hai (giữ hành vi cũ) |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ckm.py tests/test_ing_d.py tests/test_tri_thuc.py tests/test_doc_van_ban.py tests/test_cay.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M5-16 -->
<a id="m5-16"></a>
### [M5-16] `EideMd.render` giữ §Đừng/§Người vừa sửa/§Quyết định khi vượt ngân sách — P1 · S

**Giai đoạn:** GĐ2 · thứ tự #54

**Mục tiêu:** khi EIDE.md dài quá ngân sách, bản đưa vào ngữ cảnh vẫn chứa nguyên mục §Đừng và §Người vừa sửa, đúng như docstring hứa, thay vì cắt chúng trước tiên.
**Loại:** Sửa lỗi thuần (mã trái docstring; mất ranh giới người đặt).
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/store/eide_md.py`, `tests/test_eide_md_render.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `eide_md.py:22-24` `SECTIONS = [..., "Quy ước", "Đừng", "Người vừa sửa"]`: hai mục quan trọng nằm cuối.
- `eide_md.py:229-242` `render(budget_chars=12000)`: docstring nói "giữ nguyên mục, chỉ cắt thân mục dài nhất"; mã là `text[:keep] + "…bị cắt bớt…"`, tức cắt đuôi.
- `context/assemble.py:251` gọi `eide_md.render(budget_chars(b.eide_md))` với `Budget.eide_md=3000` (`config.py:138`).

**Thay đổi cần làm:**
1. Viết lại `render`: `UU_TIEN = ["Đừng", "Người vừa sửa", "Quyết định", "Quy ước", "Giả định", "Chip & phần cứng", "Mục tiêu"]` (mục ngoài danh sách xếp cuối).
   Lấy đủ các mục bắt buộc (3 mục đầu). Nếu riêng chúng đã vượt ngân sách thì giữ §Đừng nguyên vẹn và cắt các mục còn lại theo dòng MỚI NHẤT (dòng cuối).
   Mục bị cắt giữ N dòng cuối kèm dòng `_(còn k dòng — memory.read section="<mục>")_`.
2. Thứ tự HIỂN THỊ vẫn theo `SECTIONS` (mô hình đã quen); chỉ thứ tự CẤP NGÂN SÁCH theo `UU_TIEN`.
3. Sửa docstring cho khớp.

**Không được làm (giới hạn phạm vi):**
- Không đổi `save()` hay nội dung tệp trên đĩa. Không đổi `TRAN_TOKEN`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-16-01 | Đơn vị | tests/test_eide_md_render.py::test_dung_khong_bao_gio_bi_cat | `EideMd.load(tmp/"EIDE.md", create_name="x")`; §Mục tiêu 15 000 ký tự; §Đừng "- Đừng dùng HAL" → `render(12000)` chứa "Đừng dùng HAL" và `len(...) <= 12000` |
| TC-M5-16-02 | Đơn vị | tests/test_eide_md_render.py::test_nguoi_vua_sua_con_nguyen | Như trên với §Người vừa sửa 3 dòng → cả 3 dòng có trong render |
| TC-M5-16-03 | Đơn vị | tests/test_eide_md_render.py::test_muc_bi_cat_co_duong_doc_lai | §Quy ước 400 dòng → render có `memory.read section="Quy ước"` và dòng CUỐI cùng của mục |
| TC-M5-16-04 | Ca âm | tests/test_eide_md_render.py::test_ngan_thi_y_nguyen | Tệp nhỏ → `render()` bằng đúng chuỗi ghép theo `SECTIONS` như hiện tại |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_b.py tests/test_mem_d.py tests/test_mem_a.py tests/test_loop.py`
- `test_hien_phap_khong_duoc_phinh_qua_tran` (test_mem_a) giữ xanh.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.


---

## Giai đoạn 3 — Trung hạn: P1 công sức M/L

<!-- TASK M1-04 -->
<a id="m1-04"></a>
### [M1-04] Chạy song song các lời gọi chỉ-đọc trong cùng một batch — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #55

**Mục tiêu:** khi mô hình phát nhiều lời gọi R1 chỉ-đọc trong một phản hồi, chúng chạy đồng thời mà thứ tự kết quả và ledger vẫn tất định.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_SONG_SONG_DOC`, mặc định TẮT)
**Phụ thuộc:** M1-01 (bắt buộc), M1-03 (để dùng chung `kiem_va_chay`).
**Tệp chạm tới:** src/eide/config.py, src/eide/loop.py, src/eide/context/constitution.md, tests/test_song_song_doc.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- loop.py:695-699 — `for call in rsp.tool_calls: self._one_tool(call, ctx)`: tuần tự hoàn toàn.
- loop.py:550-556 — `_CONG_CU_DOC` liệt kê công cụ chỉ-đọc (fs.read/glob/grep/stat, fact.query, store.get/list, ledger.query…).
- tools/builtin.py `fs_read` ghi `ctx.mark_agent_read` (set), nên cần khoá khi chạy đồng thời.

**Thay đổi cần làm:**
1. `Features.song_song_doc: bool = False` + `ten_co()`.
2. `_tool_loop`: khi cờ bật, pha A chạy TUẦN TỰ plan-lock + pre + policy cho mọi call. Pha B chạy đồng thời bằng `ThreadPoolExecutor(max_workers=4)` các call có perm allow, `spec.risk == "R1"`, `not spec.writes_artefact` và `call.tool in _CONG_CU_DOC`. Pha C chạy tuần tự các call còn lại theo thứ tự mô hình phát.
3. Append kết quả vào `self.messages` và ledger theo ĐÚNG thứ tự call gốc, không theo thứ tự xong. Mỗi call vẫn `tool_calls_used += 1`.
4. Thêm `threading.Lock` cho `ctx.da_doc` và `ledger.append` khi gọi từ luồng phụ.
5. Hiến pháp §Cách làm việc (chỉ khi cờ bật, qua một khối `<s0_notes>` thay vì sửa tệp cố định): "Cần đọc nhiều thứ độc lập thì phát nhiều lời gọi trong MỘT lượt."

**Không được làm (giới hạn phạm vi):**
- Không chạy song song công cụ ghi, R2 trở lên, công cụ tự viết (`.eide/cong-cu`) hay `task.run`.
- Không đổi số đếm ngân sách.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-04-01 | Tích hợp (cờ BẬT) | tests/test_song_song_doc.py::test_ba_lan_doc_chay_dong_thoi | Đăng ký công cụ thử `thu.cham` (R1, ngủ 0,3 s) và thêm vào `_CONG_CU_DOC` bằng monkeypatch; 1 Response có 3 call → tổng thời gian lượt < 0,6 s. |
| TC-M1-04-02 | Tích hợp (cờ BẬT) | tests/test_song_song_doc.py::test_thu_tu_ket_qua_theo_thu_tu_goi | Công cụ ngủ ngược thời gian (call đầu ngủ lâu nhất) → các message tool trong transcript có thứ tự c1,c2,c3. |
| TC-M1-04-03 | Ca âm (cờ BẬT) | tests/test_song_song_doc.py::test_cong_cu_ghi_khong_bao_gio_song_song | Batch [fs.read, fs.write, fs.read] → fs.write chạy sau cả hai fs.read đã xong (đo bằng dấu thời gian ghi trong công cụ giả). |
| TC-M1-04-04 | Cờ TẮT | tests/test_song_song_doc.py::test_tat_co_thi_tuan_tu_nhu_cu | Như TC-01 nhưng cờ tắt → tổng ≥ 0,9 s. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_tu_phat_hien_sai.py tests/test_mem_b.py`
- Đếm ngân sách (`test_ngan_sach_tool_cat_dung_cho`) và nhắc quay vòng giữ nguyên.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: thời gian trung vị / lượt trên kịch bản phiên (tools/phien_stm32.py hoặc phát lại) giảm; pass 76 TC không tụt.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ.

<!-- TASK M1-12 -->
<a id="m1-12"></a>
### [M1-12] Chỉ gửi khối nhắc của lượt mới nhất và giữ prefix ổn định cho cache — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #56

**Mục tiêu:** mỗi lời gọi LLM chỉ mang một bản `<system-reminder>` (của message người mới nhất), các bản cũ không còn nằm trong ngữ cảnh gửi đi, và thứ tự khai báo công cụ ổn định.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_NHAC_MOT_BAN`, mặc định TẮT). Explicit cache (`client.caches`) KHÔNG nằm trong nhiệm vụ này.
**Phụ thuộc:** Không. Liên quan M1-11 (bỏ reminder cũ làm giảm áp lực ngữ cảnh).
**Tệp chạm tới:** src/eide/loop.py, src/eide/tools/registry.py, src/eide/config.py, tests/test_loop.py

**Hiện trạng (đã kiểm lại trong mã):**
- loop.py:527-528 — `self.messages.append({"role":"user","_kind":act.kind,"text": self._user_block(...)})`.
- loop.py:1497-1500 `_user_block` — `asm.reminder + "\n\n" + body`: reminder bị nối cứng vào text và lưu vĩnh viễn trong transcript.
- context/assemble.py:271 — reminder gồm eide_md, inventory, facts, human_edits, pending, skills_hint, s0_notes.
- memory/compact.py `c1` — chỉ stub kết quả công cụ (`_la_tool`), không động tới reminder trong message user.
- registry.py `visible()` giữ thứ tự đăng ký; công cụ mở khoá chen vào giữa tuỳ vị trí đăng ký.

**Thay đổi cần làm:**
1. Khi cờ bật: message user lưu `text = body` và `_reminder = asm.reminder`.
2. loop.py: hàm `_ban_gui(messages) -> list[dict]` trả bản sao nông. Message user MỚI NHẤT có `_reminder` thì `text = _reminder + "\n\n" + text`; các message cũ gửi `text` gốc. `_tool_loop` truyền `messages=self._ban_gui(self.messages)` vào `llm.stream`.
3. Message cũ (không có `_reminder`, đã nối sẵn) giữ nguyên, không sửa transcript cũ.
4. registry.py `declarations()`: sắp core theo tên trước, các công cụ mở khoá theo tên sau (chỉ khi cờ bật).

**Không được làm (giới hạn phạm vi):**
- Không sửa transcript cũ trên đĩa; không đổi dạng `text` của message `_he_thong`.
- Không làm explicit cache (cần đo chi phí lưu trữ riêng).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-12-01 | Tích hợp (cờ BẬT) | tests/test_loop.py::test_chi_mot_ban_nhac_trong_ban_gui | Hai lượt `say` liên tiếp, kịch bản hàm chép messages → ở lời gọi của lượt 2, số lần xuất hiện "<inventory" trong text các message user là 1. |
| TC-M1-12-02 | Tích hợp (cờ BẬT) | tests/test_loop.py::test_transcript_luu_text_goc | Sau một lượt → message user có `text == "câu người gõ"` và có khoá `_reminder` khác rỗng. |
| TC-M1-12-03 | Cờ TẮT | tests/test_loop.py::test_tat_co_van_noi_nhac_nhu_cu | Cờ tắt → text message user bắt đầu bằng "<system-reminder>". |
| TC-M1-12-04 | Đơn vị (cờ BẬT) | tests/test_loop.py::test_thu_tu_khai_bao_on_dinh | Mở khoá `ledger.verify` → danh sách tên trong declarations vẫn có phần core giống hệt trước khi mở, và ledger.verify nằm sau phần core. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_mem_a.py tests/test_mem_b.py tests/test_mem_c.py tests/test_mem_d.py tests/test_subagent.py tests/test_ke_hoach.py`
- Các ca kiểm pending/skills-hint (test_ke_hoach.py::test_pending_LIET_KE_cac_buoc..., test_subagent.py::test_skill_hint_vao_duoc_ngu_canh_that) phải xanh ở cả hai trạng thái cờ. Nếu các ca này đọc `messages[-1]["text"]` thì sửa test để đọc qua `_ban_gui`.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: cached_tokens/input_tokens tăng và token trung bình / lời gọi ở lượt ≥5 giảm trên phiên phát lại.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ (message mới có `_reminder` vẫn đọc được khi cờ tắt: thêm nhánh ghép lại).

<!-- TASK M1-13 -->
<a id="m1-13"></a>
### [M1-13] Replanner: `plan.revise`, tiêu chí xong và phụ thuộc giữa các bước — P1 · L

**Giai đoạn:** GĐ3 · thứ tự #57

**Mục tiêu:** kế hoạch đã duyệt sửa được tại chỗ (giữ bước đã xong). Mỗi bước có thể khai tiêu chí xong kiểm được bằng máy và các bước phụ thuộc. Hook Stop gợi ý `plan.revise` khi một bước hỏng lặp lại.
**Loại:** Công cụ mới (`plan.revise`, core=False) + Đổi hành vi cho lời nhắc replan (cờ `EIDE_FEATURE_REPLAN`, mặc định TẮT)
**Phụ thuộc:** Không. Gộp với M2-06 (cổng kiểm từng bước) và M2-07 (trạng thái bước thất bại, trần sửa): làm chung một đợt vì cùng chạm `ke_hoach.py`; `plan.revise` chỉ định nghĩa MỘT lần ở đây.
**Tệp chạm tới:** src/eide/ke_hoach.py, src/eide/tools/ke_hoach.py, src/eide/hooks/standard.py, src/eide/loop.py (`_CONG_CU_KHI_CO_KE_HOACH`), tests/test_ke_hoach.py

**Hiện trạng (đã kiểm lại trong mã):**
- ke_hoach.py `Buoc` — chỉ có viec, cong_cu, hien_vat, cong, chi_phi, ghi_chu, xong; không có phụ thuộc hay tiêu chí xong.
- tools/ke_hoach.py có plan.enter/exit/step_done/merge/cancel; không có revise. `plan.enter` khi đang có kế hoạch dở thì cất kế hoạch cũ (`_cat_di`).
- ke_hoach.py:289 `doi_chieu` — chỉ so TÊN công cụ đã gọi với `b.cong_cu`.
- loop.py `_CONG_CU_KHI_CO_KE_HOACH = ("plan.step_done","plan.merge","plan.cancel")`.

**Thay đổi cần làm:**
1. `Buoc`: thêm `phu_thuoc: list[int] = []`, `tieu_chi_xong: str = ""`; `from_dict` tương thích ngược (thiếu thì mặc định); `kiem_ke_hoach` báo lỗi nếu `phu_thuoc` trỏ số không có hoặc trỏ tới chính nó hay về sau.
2. `plan.revise(thay: list[{so?, viec, cong_cu, hien_vat, ...}], vi_sao)`: chỉ sửa hoặc chèn bước CHƯA xong; bước đã xong giữ nguyên. Chạy lại `kiem_ke_hoach` và `la_viec_lon`. Nếu `la_viec_lon` đổi từ False→True hoặc thêm bước có `gate` thì trả `trang_thai="cho_duyet"` và đi qua G-SCOPE như plan.exit; nếu không thì giữ `da_duyet`. Ghi changeset (dùng `_ghi`). Mô tả ≤ 400 ký tự.
3. Thêm "plan.revise" vào `_CONG_CU_KHI_CO_KE_HOACH` và `KHONG_KHOA`.
4. Cờ `replan`: hook Stop mới `goi_y_sua_ke_hoach`. Khi có kế hoạch `da_duyet` và trong lượt có ≥2 kết quả lỗi cùng `(tool, code)` cho một công cụ nằm trong kế hoạch, chèn lời nhắc gọi `plan.revise` (không bắt thêm vòng).

**Không được làm (giới hạn phạm vi):**
- Không đổi luồng plan.enter/exit/G-SCOPE hiện có; không để `plan.revise` xoá bước đã xong.
- Không tự chạy `tieu_chi_xong` trong nhiệm vụ này (chỉ lưu và hiện ở `<pending>`).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-13-01 | Lược đồ | tests/test_ke_hoach.py::test_plan_revise_dang_ky_dung_hop_dong | `reg.get("plan.revise")` tồn tại, `core is False`, mô tả ≤ 400 ký tự, `required` gồm "thay","vi_sao". |
| TC-M1-13-02 | Hành vi | tests/test_ke_hoach.py::test_revise_giu_buoc_da_xong | Kế hoạch 3 bước đã duyệt, bước 1 xong → revise sửa bước 2, chèn bước 4 → bước 1 vẫn `xong=True`, tổng 4 bước, trạng thái `da_duyet`. |
| TC-M1-13-03 | Hành vi | tests/test_ke_hoach.py::test_revise_them_buoc_qua_cong_thi_phai_duyet_lai | Thêm bước `target.flash` → trạng thái `cho_duyet`, có thẻ G-SCOPE. |
| TC-M1-13-04 | Lỗi | tests/test_ke_hoach.py::test_phu_thuoc_vong_bi_chan | `kiem_ke_hoach` với bước 2 `phu_thuoc=[3]` → có lỗi nhắc "phụ thuộc". |
| TC-M1-13-05 | Ca âm | tests/test_ke_hoach.py::test_ke_hoach_cu_khong_co_truong_moi_van_doc_duoc | `KeHoach.from_dict` từ dict không có `phu_thuoc`/`tieu_chi_xong` → không lỗi, mặc định rỗng. |
| TC-M1-13-06 | Cờ TẮT | tests/test_ke_hoach.py::test_tat_co_khong_nhac_revise | Hai lỗi cùng mã trong lượt có kế hoạch → không có lời nhắc chứa "plan.revise". |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ke_hoach.py tests/test_chia_viec_lon.py tests/test_tu_phat_hien_sai.py tests/test_loop.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: tỉ lệ kế hoạch bị cancel giảm trên phiên phát lại (tools/thu_chia_viec_lon.py).
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ; công cụ core=False nên không hiện nếu không mở khoá; revert nếu cần.

<!-- TASK M1-14 -->
<a id="m1-14"></a>
### [M1-14] Reflexion: chưng cất bài học từ thất bại vào EIDE.md — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #58

**Mục tiêu:** khi lượt có thất bại đặc trưng, lõi ghi một "bài học" có cấu trúc vào mục mới "Bài học" của EIDE.md, và các lượt sau nạp lại những bài học khớp ngữ cảnh.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_BAI_HOC`, mặc định TẮT)
**Phụ thuộc:** Không. Gộp với M5-14 (kho lưu và tra bài học) và M3-21 (chữ ký lỗi HDL): M1-14 lo hook chưng cất bài học ở vòng lặp, M5-14 lo kho `lesson`; làm M5-14 trước hoặc cùng đợt.
**Tệp chạm tới:** src/eide/store/eide_md.py, src/eide/tools/writing.py (enum memory.note), src/eide/loop.py, src/eide/context/assemble.py, src/eide/bai_hoc.py (mới), tests/test_bai_hoc.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- store/eide_md.py:23-24 — `SECTIONS = ["Mục tiêu","Chip & phần cứng","Quyết định","Giả định","Quy ước","Đừng","Người vừa sửa"]`; `CHI_NGUOI_GHI = {"Đừng"}`.
- tools/writing.py:229-241 — `memory.note` có enum mục cố định; không có "Bài học".
- Ledger đã có `incident` (E_PHIEN_DO, E_VERSION_CONFLICT, lỗi LLM), `budget_exhausted` (notice E6002), hook quay vòng chỉ ghi vào messages (`_he_thong`). Không có chỗ nào tổng hợp thành bài học.

**Thay đổi cần làm:**
1. `SECTIONS` thêm "Bài học" (tác tử được ghi), trần 15 dòng: dòng thứ 16 đẩy dòng cũ nhất ra.
2. Mô-đun `bai_hoc.py`: `phat_hien_that_bai(ctx, ledger_run) -> list[dict]` (thuần, 0 token) nhận 4 dấu hiệu: hết ngân sách; hook quay vòng nổ; verifier `khong_dat`; ≥3 lỗi cùng `(tool, code)`. `dung_bai_hoc(dau_hieu) -> str` dùng mẫu XÁC ĐỊNH cho từng loại, dạng "Khi <tình huống>: <làm gì lần sau> [run-xx]". Không gọi LLM trong nhiệm vụ này.
3. loop.py `turn` (khối finally, khi cờ bật): ghi bài học qua `eide_md.append_line("Bài học", ..., boi=run_id)` và tạo changeset như memory.note.
4. assemble.py: khối `<bai_hoc>` ≤ 300 token, chọn dòng có từ khoá trùng câu người dùng (dùng `normalize_vi` của hooks/s0.py).

**Không được làm (giới hạn phạm vi):**
- Không ghi vào "Đừng"; không gọi LLM để chưng cất (để việc sau, cần đo).
- Không đổi trần 3.000 token của eide_md.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-14-01 | Đơn vị | tests/test_bai_hoc.py::test_phat_hien_het_ngan_sach | ctx có `tool_calls_used == max_tool_calls` → `phat_hien_that_bai` trả 1 dấu hiệu loại "het_ngan_sach". |
| TC-M1-14-02 | Tích hợp (cờ BẬT) | tests/test_bai_hoc.py::test_het_ngan_sach_thi_ghi_bai_hoc | Kịch bản như `test_ngan_sach_tool_cat_dung_cho` (max 5) → EIDE.md có mục "Bài học" với 1 dòng chứa run_id. |
| TC-M1-14-03 | Tích hợp (cờ BẬT) | tests/test_bai_hoc.py::test_bai_hoc_vao_ngu_canh_lan_sau | EIDE.md có sẵn dòng bài học chứa "addr2line"; lượt mới câu "pc = 0x0800 thuộc hàm nào, addr2line" → reminder có `<bai_hoc>` chứa dòng đó. |
| TC-M1-14-04 | Ca âm | tests/test_bai_hoc.py::test_luot_thanh_cong_khong_ghi_gi | Lượt 1 lời gọi ok rồi trả lời → mục "Bài học" không có dòng mới. |
| TC-M1-14-05 | Cờ TẮT | tests/test_bai_hoc.py::test_tat_co_khong_ghi_bai_hoc | Như TC-02 nhưng cờ tắt → EIDE.md không đổi mục "Bài học". |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_a.py tests/test_mem_d.py tests/test_loop.py tests/test_mo_lai_du_an.py`
- `memory.note` vẫn từ chối mục "Đừng".

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: tỉ lệ tái phát cùng loại thất bại giữa các phiên giảm (đo bằng M1-20).
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ; người dùng xoá mục "Bài học" bằng tay hoặc memory.forget.

<!-- TASK M2-04 -->
<a id="m2-04"></a>
### [M2-04] Phương án kiến trúc có rubric và điểm; công cụ `design.explore` (ToT + phản biện) — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #59

**Mục tiêu:** phương án có cột điểm theo ràng buộc như §E2 đòi; tác tử có cách sinh nhiều phương án độc lập rồi chấm theo rubric.
**Loại:** Trường dữ liệu và cột bảng là Sửa lỗi thuần (§E2 chưa hiện thực). `design.explore` là Công cụ mới, `core=False`, `feature="kham_pha_thiet_ke"`.
**Phụ thuộc:** Gộp với M1-16 và M2-13 (cùng khung "phản biện"). Nếu M1-16 đã dựng subagent phản biện chung thì dùng lại, không viết lại.
**Tệp chạm tới:** src/eide/tools/design.py, src/eide/surfaces.py, src/eide/subagent.py, src/eide/config.py, tests/test_kham_pha_thiet_ke.py (mới), tests/test_phan_tich_thiet_ke_len_tab.py.

**Hiện trạng (đã kiểm lại trong mã):**
- design.py docstring (đầu tệp): "§E2 đòi bảng so sánh cạnh nhau có cột điểm theo ràng buộc".
- design.py `option_create`: lược đồ có ten, kien_truc, linh_kien_chinh, chi_phi_uoc, do_kho (enum), rui_ro, dap_ung_req, khong_dap_ung, explain. Không có trường điểm.
- design.py `option_choose`: không kiểm số phương án; test_ai_quyet.py dựng 2 phương án.
- surfaces.py:170–185, bảng A2.3 có 9 cột, không có cột điểm.

**Thay đổi cần làm:**
1. `option_create` nhận thêm `diem: object` dạng `{<mã REQ hoặc ràng buộc>: {"diem": 0..5, "ly_do": str}}`, kiểm `0 ≤ diem ≤ 5`; ngoài khoảng thì trả lỗi `E5012`.
2. Thêm artefact `rubric` qua công cụ `store.rubric_set` (`core=False`): `tieu_chi: [{ma, trong_so, nguon}]`. Hàm thuần `diem_trong_so(option, rubric) -> float`.
3. Bảng A2.3 thêm cột "Điểm (trọng số)", chỉ khi có rubric; chưa có rubric thì cột ghi "— chưa có rubric —".
4. `option_choose` thêm `note_vi` cảnh báo (không chặn) khi kho chỉ có 1 phương án, hoặc khi chọn phương án không có điểm cao nhất mà `he_qua` rỗng.
5. `design.explore(van_de, so_huong<=3)`: chạy `subagent.chay` N lần với `ma="architect"` (định nghĩa mới, chỉ đọc, `toi_da_goi=10`), mỗi lần một vai (thời gian thực, chi phí, bảo trì); rồi 1 lần `ma="design-critic"` chấm theo rubric. Kết quả trả về là đề xuất; tác tử vẫn phải gọi `option_create` để ghi.

**Không được làm (giới hạn phạm vi):**
- Không đổi `_kiem_nguoi_that_su_chon`, không đổi E5006–E5009.
- `design.explore` không tự ghi kho và không tự gọi `option_choose`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-04-01 | Đơn vị | tests/test_kham_pha_thiet_ke.py::test_diem_trong_so | rubric {FR-01:2, NFR-01:1}, điểm {5, 2} → 4.0 (mã cũ: ImportError) |
| TC-M2-04-02 | Ca biên | …::test_diem_ngoai_khoang_bi_tu_choi | `option_create(diem={"FR-01":{"diem":7}})` → `E5012` |
| TC-M2-04-03 | Đơn vị | tests/test_phan_tich_thiet_ke_len_tab.py::test_A2_3_co_cot_diem_khi_co_rubric | KhoGia option + rubric → "Điểm (trọng số)" có trong columns |
| TC-M2-04-04 | Tích hợp (ScriptedGateway) | …::test_explore_chay_N_architect_va_1_critic | `Features(kham_pha_thiet_ke=True)`, kịch bản 4 báo cáo JSON hợp lệ → `len(llm.calls)==4`, kết quả có 3 đề xuất có điểm |
| TC-M2-04-05 | Cờ TẮT | …::test_co_tat_khong_dang_ky_explore | `build_registry(Features())` → `get("design.explore") is None` |
| TC-M2-04-06 | Ca âm | …::test_choose_hai_phuong_an_khong_canh_bao_thua | 2 phương án, chọn cái điểm cao nhất → note không chứa "chỉ có 1 phương án" |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ai_quyet.py tests/test_phan_tich_thiet_ke_len_tab.py tests/test_subagent.py tests/test_tai_lieu_khop_ma.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh; `tools/kiem_tai_lieu.py` xanh (mã lỗi mới E5012 phải có trong tài liệu nếu được nhắc tới).
- [ ] Đo token mỗi lần `design.explore` (ghi sổ qua `ghi_so`).
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ; trường `diem` là tuỳ chọn nên dữ liệu cũ vẫn đọc được.

<!-- TASK M2-10 -->
<a id="m2-10"></a>
### [M2-10] REQ ràng buộc (CR) có luật máy; kiểm ngay khi ghi tệp `.c` — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #60

**Mục tiêu:** các điều cấm kiểu "không chia trong ISR 50 kHz", "không `_delay_ms` trong vòng lặp chính" thành REQ có `luat_may`, và vi phạm được báo ngay sau `fs.write`/`fs.edit`.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_LUAT_RANG_BUOC`, mặc định TẮT).
**Phụ thuộc:** M2-09 (dùng `luat_isr`, `doc_ci`). Liên quan M4-13.
**Tệp chạm tới:** src/eide/tools/writing.py, src/eide/rules/req_rules.py (mới), src/eide/hooks/standard.py, src/eide/config.py, tests/test_luat_rang_buoc.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- tools/sinh_yeu_cau_robot.py:353–390: "1.4. Bốn điều cấm" chỉ là văn xuôi gõ cứng vào .docx (Cấm 1: số thực/phép chia trong ngắt 50 kHz; Cấm 2: hàm chờ chặn; Cấm 3: WS2812; Cấm 4: tắt động cơ bằng chân EN).
- writing.py:174 `loai` enum chỉ có ["FR", "NFR", "UR"].
- hooks/standard.py:303 `ledger_and_lint` là hook post_tool_use chung, có thể gắn note vào `result.data`.
- Thư mục src/eide/rules/ đã có (ls src/eide).

**Thay đổi cần làm:**
1. Khi cờ bật, enum `loai` thêm "CR". Thêm tham số tuỳ chọn `luat_may: {pham_vi: "isr:<vector>"|"isr:*"|"main_loop"|"*", cam_ky_hieu: [..], cam_toan_tu: ["/","%"], cam_kieu: ["float","double"]}`; ghi vào canonical.
2. `req_rules.py`: `kiem(store, goc, tep_c) -> list[{req, tep, dong, vi_sao}]` dùng lại `phan_tich_tinh.luat_isr` (phạm vi isr) và quét thân `main` + hàm gọi từ main bằng cùng bộ luật (phạm vi main_loop).
3. Hook `@bus.post_tool_use`: khi cờ bật và tool là fs.write/fs.edit, đuôi .c/.h, và kho có REQ loại CR, chạy `kiem` rồi nối vào `result.data["note_vi"]` câu "Vi phạm CR-xx tại tệp:dòng…" và đặt `data["vi_pham_rang_buoc"]`. Không đổi `ok`.
4. Có danh sách ngoại lệ `cho_phep: ["x / 2^n"]`: phép chia cho hằng là lũy thừa 2 thì bỏ qua.

**Không được làm (giới hạn phạm vi):**
- Không chặn ghi tệp; không sửa tools/sinh_yeu_cau_robot.py ở nhiệm vụ này.
- Không chạy trình biên dịch trong hook (chỉ phân tích văn bản/AST nhẹ), để giữ độ trễ < 200 ms.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-10-01 | Đơn vị | tests/test_luat_rang_buoc.py::test_CR_cam_chia_trong_isr | CR `pham_vi="isr:*"`, `cam_toan_tu=["/"]`; tệp có `ISR(T0){ a = b / c; }` → 1 vi phạm, dòng đúng |
| TC-M2-10-02 | Ca âm | …::test_chia_hang_luy_thua_2_khong_keu | `a = b / 4;` → 0 vi phạm |
| TC-M2-10-03 | Tích hợp | …::test_fs_write_tra_note_vi_pham | fixture `bo` + cờ bật + CR trong kho → fs.write tệp vi phạm → `ra["vi_pham_rang_buoc"]` khác rỗng, `ok` vẫn True |
| TC-M2-10-04 | Cờ TẮT | …::test_co_tat_khong_co_loai_CR | cờ tắt → enum loai không có "CR"; fs.write không có khoá `vi_pham_rang_buoc` |
| TC-M2-10-05 | Ca âm | …::test_delay_ngoai_main_loop_khong_keu | `_delay_ms` trong hàm init gọi trước vòng while → không vi phạm `main_loop` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_cx_cong_tac.py tests/test_quy_trinh_lap_trinh.py tests/test_policy_tools.py`
- `constant_guard` (test_cx_cong_tac.py:383) không đổi.

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Trên firmware robot với 4 CR: 0 vi phạm trên mã đã chạy được, 1 vi phạm khi cố ý chèn `float` vào ISR.
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ `luat_rang_buoc`.

<!-- TASK M2-15 -->
<a id="m2-15"></a>
### [M2-15] `doc.check_sync`: kiểm tài liệu của DỰ ÁN NGƯỜI DÙNG còn khớp mã và Fact — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #61

**Mục tiêu:** tác tử kiểm được một tệp `.md` của dự án: hằng số, thanh ghi, đường dẫn nêu trong tài liệu có còn khớp mã/Fact không; và tài liệu bị STALE khi tệp mã nó trích bị sửa.
**Loại:** Công cụ mới (`doc.check_sync`, `core=False`, R1). Phần STALE tài liệu dùng hạ tầng của M2-01.
**Phụ thuộc:** M2-01.
**Tệp chạm tới:** src/eide/knowledge/dong_bo_tai_lieu.py (mới), src/eide/tools/tai_lieu.py, src/eide/tools/writing.py, tests/test_dong_bo_tai_lieu.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- tools/kiem_tai_lieu.py (262 dòng, các hàm `_dem_ma`, `_cong_cu_that`, `_ma_loi_that`, `main`) chỉ kiểm docs/md của CHÍNH EIDE; được gọi trong tests/test_tai_lieu_khop_ma.py.
- tools/sinh_yeu_cau_robot.py gõ cứng nội dung (ví dụ bảng thanh ghi có "TWBR", "12" ở dòng 727) dù docstring ghi "Mọi con số lấy thẳng từ mã".
- tools/tai_lieu.py chỉ có `doc.render` (ghi ra docx/pptx/xlsx/pdf); không có công cụ đối chiếu.

**Thay đổi cần làm:**
1. `dong_bo_tai_lieu.py`, hàm thuần:
   - `trich_khang_dinh(md) -> list[{ten, gia_tri, dong}]` từ hàng bảng Markdown có 2+ cột dạng `| TÊN | GIÁ TRỊ |`, từ `TÊN = GIÁ_TRỊ` trong khối code, và đường dẫn trong backtick có đuôi mã;
   - `tra_ma(goc, ten) -> list[(tep, dong, gia_tri)]` qua regex `#define TEN X`, `TEN = X;`, `const … TEN = X`;
   - `doi_chieu(...) -> list[{ten, tai_lieu, ma, tep_dong, loai: lech|khong_thay}]`.
2. Công cụ `doc.check_sync(nguon)`: trả tối đa 30 dòng lệch, kèm tổng; ghi artefact `analysis` id `analysis:sync:<nguon>`.
3. Khi `fs.write` ghi `.md` có trích đường dẫn tệp mã có thật thì ghi `deps.upstream` các tệp đó (qua `ghi_tep(deps=...)` của M2-01), để sửa mã thì tài liệu được đánh STALE.

**Không được làm (giới hạn phạm vi):**
- Không sửa tools/kiem_tai_lieu.py và test của nó. Không tự sửa tài liệu.
- Không phân tích văn xuôi tự do (chỉ bảng, khối code, backtick).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-15-01 | Đơn vị | tests/test_dong_bo_tai_lieu.py::test_bang_lech_hang_so | md `\| TWBR \| 12 \|`, mã `TWBR = 72;` → 1 dòng `lech` (mã cũ: ImportError) |
| TC-M2-15-02 | Ca âm | …::test_khop_thi_khong_keu | `TWBR = 12;` → 0 dòng lệch |
| TC-M2-15-03 | Đơn vị | …::test_duong_dan_khong_ton_tai | md nhắc `` `firmware/control.c` `` mà không có tệp → `khong_thay` |
| TC-M2-15-04 | Tích hợp | …::test_sua_ma_thi_tai_lieu_stale | (sau M2-01) fs.write `tai-lieu/tk.md` trích `main.c` → fs.edit `main.c` → `tai-lieu/tk.md` nằm trong `stale_marked` |
| TC-M2-15-05 | Đơn vị lược đồ | …::test_cong_cu_core_false_mo_ta_ngan | `get("doc.check_sync").core is False` và `len(summary_vi) <= 400` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_tai_lieu_khop_ma.py tests/test_xuat_ban.py tests/test_cong_thuc_ra_tai_lieu.py tests/test_them_tai_lieu.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Chạy trên docs/robot-tu-can-bang/*.md (nếu có bản md) và ghi số chỗ lệch vào DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M2-18 -->
<a id="m2-18"></a>
### [M2-18] Bộ chấm định lượng chất lượng phân tích–thiết kế trên KHO hiện vật — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #62

**Mục tiêu:** sau mỗi phiên usecase có số đo khách quan về REQ, phương án, ADR, kế hoạch, truy vết, thay cho chỉ chấm dấu hiệu bề mặt trong lời đáp.
**Loại:** Hạ tầng test/đo.
**Phụ thuộc:** Dùng được ngay. Các chỉ số truy vết và cổng kiểm đầy đủ hơn sau M2-01 và M2-06.
**Tệp chạm tới:** tools/cham_thiet_ke.py (mới), tools/chay_usecase.py, tests/test_cham_thiet_ke.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- tools/bo_usecase.py:1–25: chấm bằng `dau_hieu`/`cam`/`cong_cu`; docstring tự nói "Ô xanh ở đây nghĩa là có dấu hiệu… không phải đã làm đúng".
- tools/chay_usecase.py:55 `cham(tc, loi, cc)`; kết quả ghi `docs/review-v3/test/ket-qua-chay-lai/ket-qua.jsonl` (dòng 36–37), mỗi ca một dự án tại `du-lieu/usecase`.

**Thay đổi cần làm:**
1. `tools/cham_thiet_ke.py`: hàm `cham_kho(store) -> dict` (hàm thuần, nhận store hoặc đối tượng có `.list(type, limit)`), gồm:
   - `ty_le_req_co_tieu_chi_do_duoc` (dùng `yeu_cau.kiem_tieu_chi` nếu có M2-03, nếu không thì regex số + đơn vị);
   - `ty_le_req_duoc_option_xet`;
   - `so_option_moi_adr`;
   - `ty_le_adr_co_he_qua`;
   - `ty_le_buoc_sinh_ma_co_kiem` (đọc `plan:current`);
   - `do_phu_truy_vet` (từ `deps.ma_tran_truy_vet` nếu có);
   - `ty_le_assert_gan_req`.
2. `main(du_an)` in JSON; `chay_usecase.py` gọi `cham_kho` sau mỗi nhóm UC và ghi thêm trường `cham_kho` vào dòng JSONL (không đổi các trường cũ).
3. README ngắn ở đầu tệp nói rõ: đây là chỉ số hình dạng kho, không phải độ đúng kỹ thuật.

**Không được làm (giới hạn phạm vi):**
- Không đổi `cham()` hay nhãn đạt/không của 76 ca. Không gọi LLM-as-judge ở đợt này (để nhiệm vụ sau, có nhãn người).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-18-01 | Đơn vị | tests/test_cham_thiet_ke.py::test_ty_le_req_co_tieu_chi | KhoGia (chép từ test_phan_tich_thiet_ke_len_tab.py) 2 REQ, 1 có "≥ 5 MB/s" → 0.5 (mã cũ: ImportError) |
| TC-M2-18-02 | Đơn vị | …::test_so_option_moi_adr | ADR `phuong_an_xet=[PA-A,PA-B]` → 2.0 |
| TC-M2-18-03 | Ca biên | …::test_kho_rong_khong_chia_cho_0 | kho rỗng → mọi tỉ lệ là None, không ném lỗi |
| TC-M2-18-04 | Đơn vị | …::test_assert_gan_req | criteria 3 assert, 1 có do_req → 1/3 |
| TC-M2-18-05 | Ca âm | …::test_khong_dung_den_LLM | monkeypatch `eide.llm` ném lỗi khi import → `cham_kho` vẫn chạy |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_bo_do_phien.py tests/test_tai_lieu_khop_ma.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Chạy một lượt UC01 và ghi mốc chỉ số ban đầu vào DEV-LOG (làm đường gốc cho M2-01…M2-06).

**Hoàn tác:** revert commit (chỉ thêm trường JSONL).

<!-- TASK M3-08 -->
<a id="m3-08"></a>
### [M3-08] Tính toán kỹ thuật bằng mã: mở rộng `CONG_THUC` + công cụ `calc.eval` — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #63

**Mục tiêu:** Mọi con số điện tử dẫn xuất (R LED, chia áp, công suất, RC, tụ thạch anh, sai số baud) được tính bằng mã, có công thức, tham số và nguồn, thay vì để LLM nhẩm.
**Loại:** Công cụ mới (`core=False`)
**Phụ thuộc:** Gộp với M1-21 / M2-17. Nếu M1-21 dựng sandbox chạy mã (CodeAct) chung thì `calc.eval` dùng lại phần phân tích biểu thức an toàn đó; nhiệm vụ này chỉ thêm lớp riêng của mạch (đơn vị, Fact, `GiaTriDanXuat`).
**Tệp chạm tới:** `src/eide/knowledge/khoi_thu_vien.py`, `src/eide/knowledge/cong_thuc_mach.py` (mới), `src/eide/tools/khoi.py` (đăng ký công cụ), `tests/test_khoi.py`, `tests/test_calc.py` (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- khoi_thu_vien.py:56–81 `CONG_THUC` là danh sách đóng, không dùng `eval`, chỉ có 3 phép: `chia_ap_r2`, `tu_loc`, `pull_up`. Chỉ `dat_khoi` dùng (qua `khoi.place`).
- `GiaTriDanXuat` (khoi_thu_vien.py:86) đã mang công thức, tham số, nguồn và tier "VANG".
- Danh sách công cụ đăng ký không có công cụ tính hay chạy mã nào.

**Thay đổi cần làm:**
1. Thêm vào `CONG_THUC`: `led_r(vcc, vf, i_led)`=(vcc−vf)/i_led; `chia_ap_vout(vin, r1, r2)`; `cong_suat_r(i, r)`=i²r; `nhiet_ldo(vin, vout, i)`=(vin−vout)·i; `rc_tan_so(r, c)`=1/(2πrc); `tu_tai_thach_anh(cl, cstray)`=2(cl−cstray); `sai_so_baud(f_clk, baud, ubrr)`. Mỗi hàm ném `ValueError` có câu tiếng Việt khi miền vô nghĩa.
2. Công cụ `calc.eval(cong_thuc: str, tham_so: dict[str, str|number])`, R1, `core=False`, mô tả ≤ 400 ký tự:
   - Chỉ nhận tên trong `CONG_THUC` (không nhận biểu thức tự do ở bản này).
   - Giá trị tham số có thể là `"3,3 V"`, chuẩn hoá bằng `chuan_hoa`, hoặc `"fact:<fact_id>"`: tra `ctx.store`, lấy giá trị/đơn vị, ghi nguồn.
   - Trả `GiaTriDanXuat.to_dict()` + `cau_vi()`. Tier của kết quả là tier THẤP NHẤT trong các Fact tham số (dùng `ckm.thu_tu_tang`); không có Fact thì "NGUOI" nếu số do tác tử đưa và ghi "(số tác tử đưa vào)".
3. Lỗi: tên công thức lạ thì `E5013` kèm danh sách tên hợp lệ; tham số thiếu hoặc sai đơn vị thì `E5013` kèm tên tham số.

**Không được làm (giới hạn phạm vi):**
- Không dùng `eval`/`exec` trên chuỗi của mô hình.
- Không đổi chữ ký `dat_khoi` hay `GiaTriDanXuat`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-08-01 | Đơn vị | tests/test_calc.py::test_led_r_tinh_dung_va_mang_cong_thuc | `CONG_THUC["led_r"]` với 5 V, 2 V, 10 mA → 300 Ω; `cong_thuc` chứa "Vf" |
| TC-M3-08-02 | Tích hợp | tests/test_calc.py::test_calc_eval_qua_registry_lay_fact_lam_nguon | store có Fact `vf` tier BAC; `registry.run("calc.eval",{"cong_thuc":"led_r","tham_so":{"vcc":"5 V","vf":"fact:f-vf","i_led":"10 mA"}})` → ok; `tier=="BAC"`; `nguon["vf"]` chứa id Fact |
| TC-M3-08-03 | Ca âm | tests/test_calc.py::test_calc_eval_ten_la_thi_E5011 | `cong_thuc="__import__"` → không ok, `code=="E5013"` |
| TC-M3-08-04 | Lược đồ | tests/test_calc.py::test_calc_eval_dang_ky_core_false_mo_ta_ngan | `spec.core is False`, `len(spec.description) <= 400` |
| TC-M3-08-05 | Ca biên | tests/test_calc.py::test_led_r_vf_lon_hon_vcc_bao_loi | vf > vcc → `ValueError` có câu tiếng Việt |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_khoi.py tests/test_calc.py tests/test_registry*.py`
- 3 công thức cũ cho kết quả y hệt.

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit (công cụ `core=False`, không ảnh hưởng lược đồ mặc định).

<!-- TASK M3-05 -->
<a id="m3-05"></a>
### [M3-05] Luật miền: decoupling, boot/reset, LED hạn dòng, nhiệt LDO — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #64

**Mục tiêu:** ERC bắt bốn lỗi bo hay gặp (thiếu tụ decoupling, chân boot/reset thả nổi, LED không có điện trở, LDO quá nhiệt), mỗi phát hiện có path và công thức tính bằng mã.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_ERC_LUAT_MIEN`, mặc định TẮT). Lý do dùng cờ: các luật mềm dễ nhiễu và làm dài kết quả `board.check` mà tác tử đọc.
**Phụ thuộc:** M3-01 (đọc rail), M3-08 (nên dùng `CONG_THUC` mới cho LED và nhiệt).
**Tệp chạm tới:** `src/eide/knowledge/erc_mien.py` (mới), `src/eide/knowledge/erc.py`, `src/eide/config.py`, `src/eide/knowledge/docs.py`, `src/eide/skills/design-review-checklist.md`, `tests/test_erc.py`

**Hiện trạng (đã kiểm lại trong mã):**
- erc.py:136 không có luật nào về tụ, boot/reset, LED hay nhiệt.
- build/mach_that.py:103 chỉ nhắc BOOT0/NRST trong danh sách kiểm tra khi dò bo, không có ở mức sơ đồ.
- skills/design-review-checklist.md liệt kê đúng 6 mục mà ERC đã có.

**Thay đổi cần làm:**
1. Thêm `erc_luat_mien: bool = False` vào `Features` và tên `"erc_luat_mien"` vào `ten_co()`. `erc(store)` nhận thêm tham số tuỳ chọn `features=None`; `board.check` truyền `ctx.config.features`. Cờ tắt thì không chạy luật miền.
2. `erc_mien.decoupling`: mỗi lá có Port `power_in` trên rail (không phải GND) phải có ít nhất một lá ref `C*` mà một chân nằm trên rail đó và chân kia nằm trên nhóm GND, trong cùng khối hoặc khối cha. Thiếu thì major.
3. `erc_mien.boot_reset`: chân có Fact `role` thuộc {boot, reset, strap, en} phải nằm trên net có điện trở hoặc nút (ref `R*`/`SW*`) nối tới rail hoặc GND. Thiếu thì major. Thêm mẫu trích `role` trong docs.py cho các tên chân BOOT0/NRST/RESET/EN/IO0 là KHÔNG cần thiết; người khai `role` qua `fact.assert_human` là đủ.
4. `erc_mien.led_han_dong`: lá ref `D*`/`LED*` có Fact `vf` mà net của nó nối thẳng vào chân GPIO (không qua `R*`) thì blocker. Có R thì tính I=(Vrail−Vf)/R bằng mã (giá trị R lấy từ `canonical.gia_tri`, chuẩn hoá bằng `chuan_hoa`), so với Fact `if_max` của LED và `ioh.max` của chân GPIO.
5. `erc_mien.nhiet_ldo`: LDO (lá có `iout_max`) với Fact `pd_max` hoặc `theta_ja`: P=(Vin−Vout)·ΣI (ΣI lấy từ `ngan_sach_dong`). Vượt thì blocker, thiếu dữ kiện thì `chua_du_du_kien`.
6. Cập nhật checklist skill: liệt kê đúng danh sách luật thật (đọc `LUAT_ERC` mới, một tuple tên luật trong erc.py).

**Không được làm (giới hạn phạm vi):**
- Không đổi kết quả `erc()` khi cờ TẮT.
- Không bịa Vf, Pd hay θJA. Thiếu thì `chua_du_du_kien`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-05-01 | Đơn vị | tests/test_erc.py::test_thieu_tu_decoupling_cho_U1 | `bo` + net GND, cờ bật (monkeypatch env `EIDE_FEATURE_ERC_LUAT_MIEN=1`, `Features.load()`) → `decoupling` major cho U1 và U2 |
| TC-M3-05-02 | Ca âm | tests/test_erc.py::test_co_tu_100nF_thi_khong_bao_decoupling | thêm C1 chân 1 ở 3V3 trong `/board/mcu`, chân 2 ở GND → không báo cho U1 |
| TC-M3-05-03 | Đơn vị | tests/test_erc.py::test_LED_noi_thang_GPIO_bi_chan | D1 có `vf=2.0 V` nối thẳng U1.27 → blocker `led_han_dong` |
| TC-M3-05-04 | Đơn vị | tests/test_erc.py::test_LDO_qua_nhiet | Vin=12 V (net vào), Vout 3,3 V, ΣI=0,2 A, `pd_max=1 W` → blocker; `vi` có "1,74 W" |
| TC-M3-05-05 | Cờ TẮT | tests/test_erc.py::test_luat_mien_tat_thi_erc_y_nhu_cu | cờ tắt → `{x.luat for x in E.erc(bo)}` không chứa luật miền nào |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py tests/test_khoi.py tests/test_skills*.py`
- Mọi test ERC cũ không đặt cờ phải giữ nguyên.

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc. Trước khi bật cờ mặc định: chạy bộ eval 76 ca, không tụt.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** tắt cờ (mặc định đã tắt); revert nếu cần.

<!-- TASK M3-09 -->
<a id="m3-09"></a>
### [M3-09] Trích datasheet dự phòng bằng LLM có kiểm bám nguyên văn + `part.select` — P1 · L

**Giai đoạn:** GĐ3 · thứ tự #65

**Mục tiêu:** Khi regex không trích được khoá mà ERC cần, tác tử có đường trích bằng LLM, trong đó mã kiểm trích đoạn có thật trên trang; và có công cụ chọn linh kiện theo ràng buộc tính bằng mã.
**Loại:** Công cụ mới, sau cờ `EIDE_FEATURE_DATASHEET_LLM` (mặc định TẮT), vì công cụ tự gọi LLM thêm.
**Phụ thuộc:** M3-07 (khoá và chủ thể đã nối với ERC).
**Tệp chạm tới:** `src/eide/knowledge/docs.py`, `src/eide/knowledge/chon_linh_kien.py` (mới), `src/eide/tools/knowledge.py`, `src/eide/config.py`, `tests/test_tri_thuc_llm.py` (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- tools/knowledge.py:751 `fact.extract`: chỉ dùng `docs.trich_fact_ung_vien` (regex dòng và hàng bảng). Trích không được thì `note_vi` bảo dừng.
- Danh sách công cụ không có công cụ chọn hoặc so linh kiện; `doc.search_web` và `doc.fetch` có sẵn.

**Thay đổi cần làm:**
1. Cờ `datasheet_llm` trong `Features`.
2. `fact.extract_llm(doc_id, thuc_the, khoa: list[str])` (R2, `core=False`, `feature="datasheet_llm"`):
   - Định vị trang bằng từ khoá (tái dùng `_MAU_THONG_SO` + bảng đồng nghĩa mới `DONG_NGHIA = {"icc": ["idd","supply current","operating current"], ...}`).
   - Gửi tối đa 3 trang cho LLM qua `ctx` gateway, yêu cầu JSON `{khoa, gia_tri, don_vi, dieu_kien, trich_nguyen_van, trang}`.
   - Hàm `kiem_bam(tl, uv) -> bool` bằng mã: `trich_nguyen_van` phải có nguyên chuỗi (sau chuẩn hoá khoảng trắng) trong `tl.trang[trang-1].chu`, và chuỗi số `gia_tri` phải nằm trong trích đoạn. Trượt thì loại và đếm `bi_loai`.
   - Fact giữ tầng BẠC (hoặc thấp hơn theo `tang_mac_dinh`) với `origin="extract_llm"`.
3. `part.select(yeu_cau: list[{khoa, phep, gia_tri, don_vi}], ung_vien_doc_ids: list[str])` (R1, `core=False`, cùng cờ): đọc Fact của từng ứng viên, so bằng mã (`>=`, `<=`, `==`), xếp hạng theo số ràng buộc đạt, trả bảng có trích dẫn. Không tự chọn; `note_vi` yêu cầu hỏi người (`ask_user`).

**Không được làm (giới hạn phạm vi):**
- Không đổi `fact.extract` hiện có.
- Không ghi Fact VÀNG từ LLM.
- Không gọi web khi chưa qua cổng G-DATA hiện có.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-09-01 | Đơn vị | tests/test_tri_thuc_llm.py::test_kiem_bam_loai_trich_doan_khong_co_tren_trang | `TaiLieu` từ `lam_pdf`; ứng viên có `trich_nguyen_van` bịa → `kiem_bam` False |
| TC-M3-09-02 | Tích hợp (ScriptedGateway) | tests/test_tri_thuc_llm.py::test_extract_llm_giu_fact_bam_nguon | cờ bật; LLM kịch bản trả 2 Fact, một đúng trích đoạn và một bịa → kho có 1 Fact tầng BAC, `bi_loai==1` |
| TC-M3-09-03 | Đơn vị | tests/test_tri_thuc_llm.py::test_part_select_xep_hang_bang_ma | 2 ứng viên (iout 0,8 A và 1,5 A), yêu cầu iout ≥ 1 A → ứng viên 2 đứng đầu; có `trich_dan` |
| TC-M3-09-04 | Cờ TẮT | tests/test_tri_thuc_llm.py::test_co_tat_thi_cong_cu_khong_dang_ky | `build_registry` với Features mặc định → `registry.get("fact.extract_llm") is None` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_tri_thuc.py tests/test_ing_c.py tests/test_tri_thuc_llm.py`

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ (bỏ `kiem_bam` thì TC-02 đỏ).
- [ ] `pytest -q` xanh, ≥ mốc. Đo recall khoá ERC trên ≥ 5 datasheet mẫu trước và sau, ghi vào DEV-LOG.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** tắt cờ (mặc định tắt); revert.

<!-- TASK M3-14 -->
<a id="m3-14"></a>
### [M3-14] Đối chiếu số bằng mã (`hdl.compare`) và khung testbench tự kiểm (`hdl.tb_scaffold`) — P1 · L

**Giai đoạn:** GĐ3 · thứ tự #66

**Mục tiêu:** Tiêu chí kiểu "mô phỏng và đo trên bo chênh ≤ 1 %" được kiểm bằng mã, tái lập được; và tác tử có khung testbench tự kiểm đọc vector từ mô hình tham chiếu thay vì viết tay từ đầu.
**Loại:** Công cụ mới (`core=False`)
**Phụ thuộc:** M3-12 (giao thức PASS/FAIL), M3-08 (nếu dùng chung phần phân tích số).
**Tệp chạm tới:** `src/eide/build/hdl_doi_chieu.py` (mới), `src/eide/tools/hdl.py`, `tests/test_hdl_doi_chieu.py` (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- tools/phien_fpga_bo_that.py:289: bước 4 giao bằng câu "So results/board.csv với results/all.csv… Báo mình từng dòng chênh bao nhiêu", để LLM tự đọc và tự tính.
- Không có công cụ sinh testbench. `hdl_cay.py` chỉ đọc quan hệ gọi mô-đun, không đọc cổng.
- `sim.criteria` có cho firmware; HDL chưa có tiêu chí số.

**Thay đổi cần làm:**
1. `hdl_doi_chieu.so_csv(a: Path, b: Path, khoa: list[str], cot: list[str], nguong_tuong_doi: float) -> dict`: khớp dòng theo khoá; với mỗi cột tính `|a−b|/|b|`; trả `dong_vuot`, `so_dong`, `lech_lon_nhat`, `thieu_o_a`, `thieu_o_b`. Đọc bằng `csv`, không pandas.
2. Công cụ `hdl.compare(a, b, khoa, cot, nguong=0.01)` (R1, `core=False`): ghi kết quả vào `build:hdl:compare`; `dat` = không dòng nào vượt và không thiếu dòng.
3. `hdl_doi_chieu.khung_tb(dinh: str, cong: list[{ten, huong, rong}], tep_vector: str) -> str`: sinh testbench Verilog có clock/reset, `$readmemh` nạp vector, so đầu ra với kỳ vọng, in `TEST <i> FAIL ...` khi lệch, `PASS` ở cuối, và `$finish`. Lấy cổng từ JSON yosys (`modules[dinh].ports`) bằng `yosys -p "read_verilog -sv ...; hierarchy -top X; write_json -"`. Thiếu yosys thì `_thieu`.
4. Công cụ `hdl.tb_scaffold(nguon, dinh, tep_vector)` (R2, `writes_artefact=True`, `core=False`): ghi `sim/tb_<dinh>.v` qua `ctx.history.ghi_tep` (changeset).

**Không được làm (giới hạn phạm vi):**
- Không tự sinh vector kỳ vọng bằng LLM. Vector phải do mô hình tham chiếu (mã Python của người dùng hoặc của tác tử, có trong dự án) sinh ra.
- Không ghi đè testbench người đã sửa (G-FILE hiện có).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-14-01 | Đơn vị | tests/test_hdl_doi_chieu.py::test_so_csv_bao_dong_vuot_1_phan_tram | 2 CSV, một dòng lệch 2 % → `dong_vuot` có dòng đó, `lech_lon_nhat≈0.02` |
| TC-M3-14-02 | Ca âm | tests/test_hdl_doi_chieu.py::test_so_csv_lech_0_5_phan_tram_dat | lệch 0,5 % → `dat` True |
| TC-M3-14-03 | Ca biên | tests/test_hdl_doi_chieu.py::test_thieu_dong_thi_khong_dat | b thiếu 1 khoá → `thieu_o_b` khác rỗng, `dat` False |
| TC-M3-14-04 | Đơn vị | tests/test_hdl_doi_chieu.py::test_khung_tb_co_PASS_FAIL_va_finish | `khung_tb("dem",[...],"v.hex")` → chuỗi có `$readmemh`, `FAIL`, `PASS`, `$finish` |
| TC-M3-14-05 | Tích hợp (`can_iv`) | tests/test_hdl_doi_chieu.py::test_khung_tb_chay_duoc_voi_mo_phong | RTL đơn giản + vector đúng → `H.mo_phong(...).dat`; sửa một vector cho sai → không đạt |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py tests/test_hdl_doi_chieu.py`

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-15 -->
<a id="m3-15"></a>
### [M3-15] Kiểm hình thức bằng SymbiYosys (`hdl.formal`) và bật `--assert` cho Verilator — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #67

**Mục tiêu:** Assertion trong RTL được chứng minh hoặc bị bác bỏ kèm phản ví dụ, thay vì bị bỏ qua.
**Loại:** Công cụ mới (`core=False`) + sửa lỗi thuần (`--assert`)
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/build/hdl.py`, `src/eide/tools/hdl.py`, `src/eide/deps.py` hoặc `tools/env.check` (khai công cụ tuỳ chọn), `tests/test_hdl.py`

**Hiện trạng (đã kiểm lại trong mã):**
- build/hdl.py chỉ có `lint`, `mo_phong`, `tong_hop`, `dat_di_day`, `dong_goi`. grep `sby|symbiyosys|formal` trong `src/` không ra gì.
- hdl.py:478 lệnh verilator `--binary -j 0 -Wno-fatal ...` không có `--assert`, nên `assert property` bị bỏ qua khi mô phỏng.
- hdl_cay.py:_TU_KHOA đã biết `assert/assume/cover/restrict`.

**Thay đổi cần làm:**
1. Thêm `"formal": 900` vào `HAN_GIAY`.
2. `H.kiem_hinh_thuc(goc, nguon, dinh, che_do="bmc", do_sau=20) -> KetQuaHdl`:
   - Sinh `.eide/hdl/formal/<dinh>.sby` gồm `[options] mode/depth`, `[engines] smtbmc`, `[script] read -formal ...; prep -top`, `[files]`.
   - Chạy `sby -f`; đọc dòng cuối `DONE (PASS|FAIL…)` thành `dat`.
   - Khi FAIL: tìm `engine_*/trace*.vcd` và trích tối đa 10 chu kỳ cuối của các tín hiệu xuất hiện trong thông điệp `Assert failed in <mod>: <file>:<dong>`. Trả `phan_vi_du={tep, dong, vcd}`.
   - Không có thông điệp DONE thì không đạt và nói rõ.
3. Thiếu `sby` thì `_thieu("sby", "kiểm hình thức")`.
4. Công cụ `hdl.formal(nguon, dinh, che_do="bmc"|"prove", do_sau=20)` (R1, `core=False`).
5. Thêm `--assert` vào lệnh verilator trong `mo_phong`.

**Không được làm (giới hạn phạm vi):**
- Không coi "không có assertion nào" là PASS: không thấy `assert`, `assume` hay `cover` trong nguồn thì từ chối và nói rõ.
- Không đổi lệnh iverilog.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-15-01 | Đơn vị (giả công cụ) | tests/test_hdl.py::test_formal_doc_DONE_PASS | `sby` giả (script) in "SBY ... DONE (PASS, rc=0)" → `kq.dat` |
| TC-M3-15-02 | Đơn vị | tests/test_hdl.py::test_formal_FAIL_tra_phan_vi_du | `sby` giả in "Assert failed in dem: dem.v:12" + "DONE (FAIL, rc=2)" và tạo `engine_0/trace.vcd` → không đạt, `phan_vi_du["dong"]==12` |
| TC-M3-15-03 | Ca âm | tests/test_hdl.py::test_formal_khong_co_assert_thi_tu_choi | RTL `BLINKY` → không đạt, lý do có "assert" |
| TC-M3-15-04 | Đơn vị | tests/test_hdl.py::test_verilator_sim_co_co_assert | monkeypatch `_chay` để ghi lại `lenh`; `mo_phong(bo_may="verilator")` → `"--assert" in lenh` |
| TC-M3-15-05 | Đơn vị | tests/test_hdl.py::test_formal_thieu_sby_noi_cach_cai | `_tim_lenh` trả "" → lý do có "sby" và "G-TOOL" |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py tests/test_bien_dich_rv32.py`
- `test_cong_cu_hdl_da_dang_ky`: cập nhật danh sách nếu test đếm đúng số công cụ (đọc test trước khi sửa).

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-20 -->
<a id="m3-20"></a>
### [M3-20] `hdl.flow`: luồng lint → sim → độ nhạy → kiểm chân → synth → pnr → bitstream có cổng bằng mã — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #68

**Mục tiêu:** Một lời gọi chạy các chặng HDL theo đúng thứ tự, có cổng giữa chặng bằng mã, dừng ở chặng trượt đầu tiên và trả kết quả gọn; người dùng không phải chia đề bằng script bên ngoài.
**Loại:** Công cụ mới (`core=False`)
**Phụ thuộc:** M3-12, M3-13, M3-18 (các cổng). Có thể làm trước với cổng tuỳ chọn và bật dần.
**Tệp chạm tới:** `src/eide/build/hdl_luong.py` (mới), `src/eide/tools/hdl.py`, `tests/test_hdl_luong.py` (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- tools/hdl.py đăng ký 5 công cụ rời (`hdl.lint`, `hdl.sim`, `hdl.synth`, `hdl.pnr`, `hdl.bitstream`); tác tử tự xâu chuỗi chúng qua vòng ReAct.
- tools/phien_fpga_bo_that.py:10–20 ghi lại: "đề dài có bảng và sáu mục thì nó đọc rồi dừng… nên câu trong tệp này ngắn, mỗi câu đúng một việc"; hạn lượt phải nâng lên `EIDE_TRAN_GIAY_LUOT=3600`, `EIDE_TRAN_LOI_GOI_LUOT=220`.

**Thay đổi cần làm:**
1. `hdl_luong.chay_luong(goc, rtl, tb, dinh, dinh_tb, cst, dich_mhz, den="bitstream", nguong_do_nhay=None, nguong_lut=0.85, bo_kit="tangnano20k") -> dict`. Gọi lần lượt các hàm đã có trong `build/hdl.py`, không gọi qua registry. Cổng:
   - lint: `dat`.
   - sim: `dat` (sau M3-12).
   - độ nhạy: chỉ khi có `nguong_do_nhay`.
   - kiểm chân: `cst.kiem` không có blocker (sau M3-18).
   - synth: `dat`.
   - pnr: `dat` và `ty_le` LUT ≤ `nguong_lut`.
   - bitstream: `dat`.
2. Trả `{"chang_cuoi_dat", "dung_o", "ly_do", "loi": [≤5, có toạ độ], "ket_qua_tung_chang": {chang: to_dict rút gọn}}`. Mỗi chặng vẫn ghi `build:hdl:<chang>` như các công cụ rời (dùng lại `_ghi_kho`).
3. Công cụ `hdl.flow(...)` (R2, `core=False`, `writes_artefact=True`), mô tả ≤ 400 ký tự, nói rõ "dừng ở chặng trượt đầu tiên; sửa rồi gọi lại".
4. Hạn tổng: tổng `HAN_GIAY` của các chặng chạy, cộng kiểm `ctx` còn ngân sách thời gian lượt (đọc như cách loop dùng `max_seconds`). Không đủ thì dừng trước chặng dài và nói rõ.

**Không được làm (giới hạn phạm vi):**
- Không xoá hay đổi 5 công cụ rời.
- Không tự sửa RTL.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-20-01 | Đơn vị | tests/test_hdl_luong.py::test_dung_o_chang_truot_dau_tien | monkeypatch `H.lint` trả `dat=True`, `H.mo_phong` trả `dat=False` → `dung_o=="mo_phong"`; `H.tong_hop` KHÔNG được gọi (đếm số lần gọi) |
| TC-M3-20-02 | Đơn vị | tests/test_hdl_luong.py::test_lut_vuot_nguong_thi_dung | pnr giả `dung["LUT4"]["ty_le"]=0.9` → `dung_o=="dat_di_day"`, lý do có "85" |
| TC-M3-20-03 | Đơn vị | tests/test_hdl_luong.py::test_den_synth_thi_khong_chay_pnr | `den="tong_hop"` → không gọi `dat_di_day` |
| TC-M3-20-04 | Tích hợp (`CO_YOSYS and CO_PNR and CO_PACK`) | tests/test_hdl_luong.py::test_luong_blinky_toi_bitstream | `_du_an` + `TB_PASS` → `chang_cuoi_dat=="dong_goi"` |
| TC-M3-20-05 | Lược đồ | tests/test_hdl_luong.py::test_hdl_flow_core_false_mo_ta_ngan | `core is False`, mô tả ≤ 400 |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py tests/test_hdl_luong.py`

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc. Đo số lời gọi từ RTL tới bitstream trên `tools/phien_fpga.py` trước và sau.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M4-03 -->
<a id="m4-03"></a>
### [M4-03] Công cụ sinh test biên / fuzz / property (`test.generate`) — P1 · L

**Giai đoạn:** GĐ3 · thứ tự #69

**Mục tiêu:** Tác tử có một công cụ sinh khung test biên, harness libFuzzer và property cho hàm logic C thuần, đầu ra theo khuôn `{"do":…}` để EIDE phán.
**Loại:** Công cụ mới
**Phụ thuộc:** M4-01 (khuôn `do` + tiêu chí unit), M4-17 (coverage để chọn đích, tuỳ chọn)
**Tệp chạm tới:** src/eide/build/sinh_test.py (mới), src/eide/tools/xay_dung.py, tests/test_sinh_test.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- tools/xay_dung.py chỉ có `test.run` (802) và `test.sensitivity` (738); không công cụ nào sinh test.
- `phan_tich_ma.quet(goc, [tệp])` (dùng ở code.analyze, xay_dung.py:~285) có trả ký hiệu; cần kiểm nó có chữ ký tham số chưa trước khi dựa vào.
- `_logic_dich_duoc_tren_may(goc)` (xay_dung.py:961) đã lọc được tệp logic không kéo header bo.

**Thay đổi cần làm:**
1. build/sinh_test.py: `bang_bien(kieu_c: str) -> list[str]` (uint8_t: 0,1,254,255; int16_t: -32768,-1,0,1,32767; float: 0, -0.0, 1e-30, 1e30, NAN); `sinh_khung_bien(ham, tham_so, ma_assert)` sinh tệp C in `{"do":{...}}`; `sinh_harness_fuzz(ham, tham_so)` sinh `LLVMFuzzerTestOneInput`; `sinh_property(ham, bat_bien_c, n=1000, seed=1)`.
2. Công cụ `test.generate(tep, ham, kieu=["bien"|"fuzz"|"property"], bat_bien="")` (core=False, R2, writes_artefact, needs_explain): chỉ nhận tệp nằm trong `_logic_dich_duoc_tren_may`, ghi ra `test/gen_<ham>_<kieu>.c` qua `ctx.history.ghi_tep` (có changeset). Fuzz: biên dịch `-fsanitize=fuzzer,address,undefined`, chạy `-max_total_time=` (mặc định 30, trần 120); thiếu libFuzzer thì E4025 kèm lý do.
3. Ca sinh tự động mang `nguon=sinh` trong tên ca.

**Không được làm (giới hạn phạm vi):**
- Không tự gọi test.generate từ hook (đó là M4-06).
- Không sinh test cho tệp kéo header bo.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-03-01 | Đơn vị | tests/test_sinh_test.py::test_bang_bien_uint8_co_0_va_255 | bang_bien("uint8_t") → chứa "0" và "255" |
| TC-M4-03-02 | Tích hợp (skipif không có cc) | …::test_khung_bien_bat_duoc_tran_so | firmware/logic.c `uint8_t cong(uint8_t a,uint8_t b){return a+b;}` → test.generate(kieu="bien") + test.run → có ca không đạt với 255+1 |
| TC-M4-03-03 | Ca âm | …::test_tep_keo_header_bo_thi_tu_choi | firmware/x.c `#include "stm32f4xx.h"` → not ok, hint nói "header của bo" |
| TC-M4-03-04 | Ca biên | …::test_fuzz_khong_co_libfuzzer_thi_noi_ro | monkeypatch trình biên dịch trả lỗi `-fsanitize=fuzzer` → E4025, không trả ok |
| TC-M4-03-05 | Lược đồ | …::test_test_generate_core_false | core False, summary ≤400 |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_xay_dung.py tests/test_dot_bien.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: trên dự án mẫu robot, ít nhất 1 lỗi biên được test sinh bắt mà test viết tay không bắt.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit (công cụ độc lập).

<!-- TASK M4-08 -->
<a id="m4-08"></a>
### [M4-08] Verifier chạy lại phép đo và soi STALE (cùng model, cấu hình riêng) — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #70

**Mục tiêu:** Verifier có thể CHẠY LẠI test/sim/đối chiếu Flash vào hiện vật riêng, và tự hạ kết luận khi bằng chứng đã STALE.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_VERIFIER_CHAY_LAI`, mặc định TẮT)
**Phụ thuộc:** M4-07; Gộp với M1-06
**Tệp chạm tới:** src/eide/subagent.py, src/eide/tools/xay_dung.py, src/eide/tools/dieu_phoi.py, src/eide/config.py, tests/test_subagent.py

**ĐÃ KIỂM LẠI:** phát hiện gốc đề xuất "model khác họ/cỡ" là KHÔNG làm được: `ALLOWED_MODELS` chỉ có `gemini-3.8-flash` (config.py:40) theo quyết định chủ sản phẩm, và `GeminiGateway.stream` chặn ở điểm gọi (llm/gemini.py:~64). Phần model hạ xuống: dùng `temperature=0.0` riêng cho verifier qua tham số `stream(temperature=…)` sẵn có. `ModelConfig.subagent` (config.py:196) hiện không ai đọc: nối vào `stream(model=cfg.model.subagent)` để tôn trọng cấu hình (vẫn cùng một model).

**Hiện trạng (đã kiểm lại trong mã):**
- subagent.py:148-149 verifier chỉ có công cụ đọc; subagent.py:293 `llm.stream(system=…, messages=…, tools=…)` không truyền model/temperature.
- `store.get` trả `stale`/`stale_reason` (store/db.py:842).

**Thay đổi cần làm:**
1. `chay`: truyền `model=ctx.config.model.subagent`, và `temperature=0.0` khi `ma=="verifier"`.
2. Cờ bật: thêm `test.run`, `sim.run`, `target.verify` vào tập verifier, nhưng `sim.run`/`test.run` gọi từ verifier phải ghi vào `sim_result:verify-<ma>` thay cho MA_SIM/MA_TEST. Cách làm: thêm tham số ẩn `_ma_hien_vat` mà chỉ subagent.chay đặt (lọc khỏi lược đồ hiển thị).
3. `gop_kiem_chung`: bằng chứng `ref` là hiện vật có `stale=True` thì hạ `chua_du_du_kien` với lý do "bằng chứng STALE".
4. Kết luận `dat` của verifier khi báo cáo gốc có test/sim mà không có bằng chứng `kind="rerun"` thì hạ `chua_du_du_kien` (chỉ khi cờ bật).

**Không được làm (giới hạn phạm vi):**
- Không thêm model nào vào ALLOWED_MODELS.
- Verifier không được ghi đè MA_SIM/MA_TEST/MA_NAP; không được có fs.write.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-08-01 | Đơn vị | tests/test_subagent.py::test_bang_chung_STALE_thi_ha_ket_luan | hiện vật x stale; bc dat với bang_chung ref x; kc dat → gop_kiem_chung → "chua_du_du_kien" |
| TC-M4-08-02 | Tích hợp (ScriptedGateway) | …::test_verifier_co_test_run_khi_bat_co | cờ bật → llm.calls[0]["tools"] chứa "test.run", không chứa "fs.write" |
| TC-M4-08-03 | Tích hợp | …::test_verifier_chay_lai_khong_ghi_de_MA_TEST | MA_TEST version v; verifier gọi test.run → MA_TEST vẫn version v; có sim_result:verify-* |
| TC-M4-08-04 | Cờ TẮT | …::test_co_tat_tap_cong_cu_verifier_y_cu | tools == danh sách cũ |
| TC-M4-08-05 | Ca âm | …::test_bang_chung_khong_stale_khong_bi_ha | hiện vật không stale → ket_luan giữ "dat" |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_xay_dung.py tests/test_config_model.py`
- test_verifier_chi_co_cong_cu_DOC phải được cập nhật có điều kiện theo cờ (cờ tắt vẫn đúng như cũ).

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ; phần STALE và model/temperature revert commit.

<!-- TASK M4-10 -->
<a id="m4-10"></a>
### [M4-10] Verifier bác thì có vòng sửa có trần (Evaluator–Optimizer + bài học) — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #71

**Mục tiêu:** Khi verifier trả `khong_dat` có mục cụ thể, tác tử được cho tối đa N vòng sửa và verifier kiểm lại trước khi trả lượt cho người.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_SUA_SAU_KIEM`, mặc định TẮT)
**Phụ thuộc:** M4-09; Gộp với M1-15 (cùng chạm hook Stop); phần lưu bài học dùng kho `lesson` của M5-14/M1-14, không viết riêng
**Tệp chạm tới:** src/eide/hooks/standard.py, src/eide/loop.py, src/eide/config.py, tests/test_sua_sau_kiem.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- subagent.py:252-265 `gop_kiem_chung` hạ kết luận và ghi `chua_lam`, rồi dừng.
- hooks/standard.py:574 `ctx.da_tu_kiem = True`: hook chỉ nổ một lần mỗi lượt; injection chỉ dặn "NÓI RA điều đó".
- Kết quả task.run verifier nằm trong `res.data["ket_luan"]` tại loop.py:891.

**Thay đổi cần làm:**
1. Cờ `sua_sau_kiem` + tham số `Budget.max_vong_sua_sau_kiem = 2`.
2. loop.py:891: khi verifier `ket_luan == "khong_dat"`, lưu `ctx.phat_hien_verifier = res.data["chua_lam"] + bang_chung không khớp` và tăng `ctx.vong_sua`.
3. Stop hook mới `sua_theo_verifier` (cờ bật): có phát hiện và `vong_sua < max` thì `another_round=True`, injection là checklist; đặt lại `ctx.da_tu_kiem=False` để hook kiểm chứng nổ lại sau khi sửa. Hết trần thì injection "báo người dùng danh sách còn lại".
4. Ghi sổ `hook: sua_theo_verifier {vong, so_muc}`.

**Không được làm (giới hạn phạm vi):**
- Không vượt `max_tool_calls`/`max_seconds` hiện có; vòng sửa tính vào cùng ngân sách.
- Không tự sửa khi verifier trả `chua_du_du_kien` (thiếu dữ kiện thì không có gì để sửa).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-10-01 | Tích hợp (ScriptedGateway) | tests/test_sua_sau_kiem.py::test_verifier_bac_thi_co_them_vong_sua | cờ bật; kịch bản fs.write → task.run verifier (khong_dat) → fs.edit → task.run verifier (dat) → text → có đúng 2 lần verifier trong sổ cái |
| TC-M4-10-02 | Ca biên | …::test_dung_o_tran_vong | verifier luôn khong_dat, max=2 → tối đa 3 lần verifier, lượt kết thúc không có E6004 |
| TC-M4-10-03 | Cờ TẮT | …::test_co_tat_hanh_vi_y_cu | cờ tắt → 1 lần verifier, rồi kết thúc |
| TC-M4-10-04 | Ca âm | …::test_chua_du_du_kien_khong_kich_hoat_sua | verifier chua_du_du_kien → không có vòng sửa |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_tu_phat_hien_sai.py tests/test_loop.py tests/test_subagent.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: tỉ lệ khong_dat→dat sau ≤2 vòng trên bộ M4-22; chỉ bật mặc định khi 76 ca / phát lại không tụt.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ.

<!-- TASK M4-12 -->
<a id="m4-12"></a>
### [M4-12] Kiểm tiêu chí có khả năng ĐỎ (`sim.criteria_check`) — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #72

**Mục tiêu:** Trước khi người xác nhận tiêu chí, EIDE chỉ ra assert nào không bao giờ đổi kết luận khi mã sản phẩm bị phá, và REQ nào chưa có assert.
**Loại:** Công cụ mới
**Phụ thuộc:** M4-04, M4-19
**Tệp chạm tới:** src/eide/tools/xay_dung.py, src/eide/build/tieu_chi.py (hàm mới, không đổi hàm cũ), tests/test_kiem_tieu_chi.py (mới)

**ĐÃ KIỂM LẠI:** phần "criteria-critic model khác" hạ xuống: dùng cùng model (ALLOWED_MODELS chỉ có một), với system prompt riêng và temperature 0.

**Hiện trạng (đã kiểm lại trong mã):**
- tools/xay_dung.py `sim_criteria` (~524-596) kiểm khuôn: ma/mo_ta, phep_so ∈ PHEP_SO, cảnh báo thiếu `nguon_nguong`, mất `khong_mo_phong_duoc`; không có phép thử khả năng đỏ.
- DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md §4: tiêu chí "mọi ô ok=1" làm 24/96 ô không thể báo sai.

**Thay đổi cần làm:**
1. `tieu_chi.assert_khong_doi(tc, ket_qua_goc: dict, ket_qua_dot_bien: list[dict]) -> list[str]`: assert có kết luận giống hệt nhau qua mọi lần chạy đột biến.
2. Công cụ `sim.criteria_check(ma_tieu_chi="sim-01", toi_da_dot_bien=8)` (core=False, R1): chạy sim gốc, rồi chạy sim với K mutant (từng mutant một, trên bản sao của M4-19) của tệp `firmware/control*.c` (hoặc `nguon`), và liệt kê assert không đổi. Đối chiếu `do_req` với REQ trong kho (`store.list("req")`) để liệt kê REQ chưa có assert.
3. Tuỳ chọn khi có llm: subagent `criteria-critic` (công cụ: store.get, store.list, fact.query) trả danh sách nghi vấn. Không có llm thì nói "chưa có phần phản biện".
4. Không ghi đè tiêu chí; chỉ ghi hiện vật `analysis:criteria-check:<ma>`.

**Không được làm (giới hạn phạm vi):**
- Không tự sửa ngưỡng; không tự xác nhận.
- Không chặn sim.run (đây là thông tin cho người).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-12-01 | Đơn vị | tests/test_kiem_tieu_chi.py::test_assert_tu_so_chinh_no_bi_bat | kết quả gốc A1=1, mọi mutant A1=1 với ngưỡng "==1" → ["A1"] |
| TC-M4-12-02 | Ca âm | …::test_assert_doi_khi_dot_bien_khong_bi_keu | A1 đổi từ 3 thành 99999 ở một mutant → [] |
| TC-M4-12-03 | Tích hợp (skipif không có cc) | …::test_criteria_check_tren_du_an_mau | sim in A1 cố định, A2 tính từ control.c → báo A1, không báo A2 |
| TC-M4-12-04 | Đơn vị | …::test_REQ_khong_co_assert_duoc_liet_ke | req REQ-1, REQ-2; tiêu chí chỉ do_req REQ-1 → liệt kê REQ-2 |
| TC-M4-12-05 | Lược đồ | …::test_cong_cu_core_false_R1 | core False, risk R1 |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_xay_dung.py tests/test_sim_lech_tieu_chi.py tests/test_dot_bien.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M4-14 -->
<a id="m4-14"></a>
### [M4-14] HIL có tiêu chí và máy chấm log UART (`hil.criteria` + `hil.run`) — P1 · L

**Giai đoạn:** GĐ3 · thứ tự #73

**Mục tiêu:** Log UART từ bo thật được EIDE chấm bằng assert nêu trước, lặp N lần, có kiểm mốc thời gian nạp/đọc.
**Loại:** Công cụ mới
**Phụ thuộc:** M4-01 (dùng chung khuôn tiêu chí)
**Tệp chạm tới:** src/eide/build/hil.py (mới), src/eide/tools/mach_that.py, src/eide/policy/policy.yaml, tests/test_hil.py (mới)

**ĐÃ KIỂM LẠI:** phát hiện gốc nói "không xả bộ đệm cũ, không gắn mốc với lần nạp". Chỉ đúng một phần. `build/mach_that.py:747 bat_log_quanh_viec` (DEV-331) mở cổng TRƯỚC khi nạp và có `_vet()` vét byte tồn, và `target.flash` dùng nó (tools/mach_that.py:386). Riêng `target.log` (880-940) thì vẫn đọc thô qua `doc_log` (build/mach_that.py:2015), không xả và không mốc. Điểm còn thiếu thật: không có assert/máy chấm và không lặp N lần.

**Hiện trạng (đã kiểm lại trong mã):**
- tools/mach_that.py:880 `target.log` → `MT.doc_log(cong, baud, giay)`, ghi `target:log` 8000 ký tự cuối, kết luận do mô hình đọc.
- BAO-CAO-TONG: TC053 "Cần thiết bị — HIL lặp 20 lần".

**Thay đổi cần làm:**
1. build/hil.py: `trich_so_do(chu, asserts) -> dict` với assert kiểu `{ma, regex, nhom:int, phep_so, nguong}` hoặc `{ma, dem_dong: regex, phep_so, nguong}`; dùng lại `tieu_chi.xet_ket_qua`.
2. `hil.criteria` (giống sim.criteria, hiện vật `criteria:hil-<ma>`, cần trich_loi).
3. `hil.run(ma_tieu_chi, lan=1..20, giay=…)` (core=False, R3): mỗi lần gọi đường nạp có sẵn (dùng `bat_log_quanh_viec` + reset), xả cổng tới khi im ≥300 ms, đọc, chấm. Ghi `sim_result:hil-<ma>` gồm `lan`, `so_dat`, `ty_le`, `t_nap`, `t_doc`; `t_doc < t_nap` thì lần đó `chua_do_duoc`.
4. policy: `POL-HIL-run` ask G-FLASH MỘT lần cho cả loạt (summary nêu số lần nạp).

**Không được làm (giới hạn phạm vi):**
- Không đổi hành vi target.log / target.flash hiện có.
- Không chạy khi chưa có tiêu chí đã xác nhận (E4008/E4009).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-14-01 | Đơn vị | tests/test_hil.py::test_trich_so_do_theo_regex | chu "tick=1003\n" và assert regex `tick=(\d+)` "trong_khoang 990–1010" → dat |
| TC-M4-14-02 | Ca âm | …::test_log_khong_khop_regex_la_chua_do_duoc | chu "" → ket_luan chua_do_duoc, dat False |
| TC-M4-14-03 | Đơn vị (monkeypatch nạp/đọc) | …::test_doc_truoc_khi_nap_thi_tu_choi_lan_do | t_doc < t_nap → lần đó chua_do_duoc |
| TC-M4-14-04 | Tích hợp (monkeypatch) | …::test_lap_N_lan_tinh_ty_le | 5 lần, 1 lần log hỏng → so_dat 4, ty_le 0.8 |
| TC-M4-14-05 | Lược đồ/policy | …::test_hil_run_core_false_va_qua_cong | core False; policy.decide → ask |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mach_that.py tests/test_hdl.py tests/test_nap_avr.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: TC053 chuyển từ "Cần thiết bị" sang đo được trên STM32F469I-DISCO.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit (công cụ độc lập).

<!-- TASK M4-16 -->
<a id="m4-16"></a>
### [M4-16] HDL: khớp PASS/FAIL chặt, độ nhạy do EIDE đo, coverage Verilator — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #74

**Mục tiêu:** `hdl.sim` không nhận "BYPASS"/"PASSED" làm PASS, độ nhạy HDL là số EIDE đo được (không phải tác tử tự điền), và có % coverage khi dùng Verilator.
**Loại:** Sửa lỗi thuần (khớp chuỗi con, độ nhạy tự khai) + Công cụ mới (`hdl.sensitivity`)
**Phụ thuộc:** Gộp với M3-12 và M3-13 (mảng 3 chạm cùng tools/hdl.py, build/hdl.py): làm sau hoặc cùng PR, không viết lại phần trùng
**Tệp chạm tới:** src/eide/build/hdl.py, src/eide/tools/hdl.py, src/eide/build/dot_bien.py (phép Verilog), tests/test_hdl.py

**Hiện trạng (đã kiểm lại trong mã):**
- build/hdl.py:496-498 `tren = kq.nguyen_van.upper(); co_pass, co_fail = "PASS" in tren, "FAIL" in tren`: khớp chuỗi con, kể cả "BYPASS", "PASSED", "FAILSAFE".
- tools/hdl.py:~121-160 tham số `do_nhay {bat,tong}` do tác tử tự điền và được ghi thẳng vào hiện vật (`kq.do_nhay = …`).
- Không có cờ `--coverage` trong đường Verilator.

**Thay đổi cần làm:**
1. Khớp theo dòng: `re.search(r"^\s*(?:\[[^\]]*\]\s*)?(PASS|FAIL)\b", dong, re.M)` trên nguyên văn, không `.upper()` cả khối (chấp nhận "PASS", "FAIL:", "FAIL ca 3").
2. Bỏ tham số `do_nhay` khỏi lược đồ hdl.sim (giữ đọc trường cũ trong hiện vật để bề mặt surfaces.py:539 vẫn hiện). Thêm công cụ `hdl.sensitivity(nguon, dinh, toi_da=10)` (core=False, R1): phép RTL `==`↔`!=`, `&`↔`|`, hằng `N'dX`/`N'hX`→0, đảo `posedge rst`↔`negedge rst`. Chạy `H.mo_phong` trên bản sao, tính `{bat,tong}` và ghi vào hiện vật `build:hdl:sim`.
3. `bo_may="verilator"`: thêm `--coverage`, chạy `verilator_coverage --annotate` và báo `% line/toggle` vào `kq.do_phu`.

**Không được làm (giới hạn phạm vi):**
- Không đổi cách tính `dat` = có PASS và không có FAIL (chỉ đổi cách khớp).
- Không đột biến tệp testbench.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-16-01 | Đơn vị (can_iv) | tests/test_hdl.py::test_BYPASS_khong_phai_PASS | testbench chỉ in "bypass enabled" → not kq.dat |
| TC-M4-16-02 | Đơn vị (can_iv) | …::test_FAILSAFE_khong_phai_FAIL | in "failsafe on\nPASS" → kq.dat |
| TC-M4-16-03 | Lược đồ | …::test_hdl_sim_khong_con_nhan_do_nhay_tu_khai | registry.get("hdl.sim").params không có "do_nhay"; có "hdl.sensitivity" core False |
| TC-M4-16-04 | Tích hợp (can_iv) | …::test_hdl_sensitivity_do_that | thiết kế cộng + testbench kiểm tổng → bat ≥1, ghi vào build:hdl:sim |
| TC-M4-16-05 | Hồi quy | …::test_sim_doc_PASS_tu_testbench, test_sim_in_FAIL_thi_KHONG_dat (có sẵn) | giữ xanh |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py tests/test_hdl_cay.py tests/test_dot_bien.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M4-20 -->
<a id="m4-20"></a>
### [M4-20] Chấm eval theo chủ đề và theo hiện vật, chạy k lần cho ca kỹ thuật — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #75

**Mục tiêu:** Máy chấm 76 ca không còn cộng các từ đồng nghĩa của cùng một chủ đề, có loại kiểm theo hiện vật/sổ cái, và báo pass@1/pass^k.
**Loại:** Hạ tầng test/đo
**Phụ thuộc:** Gộp với M1-20 và M4-21 (cùng hạ tầng eval); làm trước M4-21
**Tệp chạm tới:** tools/chay_usecase.py, tools/bo_usecase.py, tools/chay_kich_ban.py, tests/test_may_cham_eval.py (mới)

**ĐÃ KIỂM LẠI:** "LLM-judge model khác" hạ xuống cùng model (ALLOWED_MODELS), system prompt riêng, temperature 0, và phải hiệu chuẩn với `docs/review-v3/test/ket-qua-chay-lai/doc-tay.json`.

**Hiện trạng (đã kiểm lại trong mã):**
- tools/chay_usecase.py:93-99 `dau_hieu_bat_ky` là danh sách phẳng; `thay = [d for d in bk if khong_dau(d) in l]`, đếm từng từ.
- tools/bo_usecase.py:55-57 TC001 gộp "fat32","exfat","ntfs","hệ thống tệp" vào cùng danh sách với "dung lượng"… và `so_dau_hieu=3`. Kết quả thật: "4/3 dấu hiệu: fat32, exfat, ntfs, dung lượng" (3/4 cùng một chủ đề).
- tests/kich_ban/tc001_007.yaml đã có `phai_hoi.chu_de` theo chủ đề; chay_kich_ban chạy `--lan 5`.

**Thay đổi cần làm:**
1. `cham()`: nhận `dau_hieu_bat_ky` dạng dict `{chu_de: [cụm…]}`, mỗi chủ đề tính tối đa 1. Danh sách phẳng giữ nguyên ngữ nghĩa cũ (tương thích).
2. Chuyển TC001 (và các ca có cụm đồng nghĩa) trong bo_usecase sang dạng dict.
3. Loại kiểm mới, đọc từ kho/sổ cái của dự án ca: `hien_vat: {id, dat: true, khong_stale: true}`, `thu_tu_cong_cu: ["sim.criteria","sim.run"]`.
4. Tham số `--lan k` cho chay_usecase; ghi `pass_at_1` và `pass_hat_k` (đạt cả k lần).
5. Tuỳ chọn `--judge`: chấm ngữ nghĩa bằng rubric, ghi điểm kèm trích dẫn; báo độ đồng thuận với doc-tay.json.

**Không được làm (giới hạn phạm vi):**
- Không đổi nhãn `ngoai_pham_vi/can_nguoi/can_thiet_bi`.
- Không xoá kết quả cũ trong ket-qua.jsonl.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-20-01 | Đơn vị (nạp tools/chay_usecase.py qua importlib.util.spec_from_file_location) | tests/test_may_cham_eval.py::test_dong_nghia_cung_chu_de_chi_tinh_mot | dau_hieu_bat_ky={"dinh_dang":["fat32","exfat","ntfs"],"dung_luong":["dung lượng"]}, so 3; lời "fat32 exfat ntfs dung lượng" → "khong_dat" |
| TC-M4-20-02 | Ca âm tương thích | …::test_danh_sach_phang_giu_ngu_nghia_cu | danh sách phẳng như cũ → vẫn "dat" |
| TC-M4-20-03 | Đơn vị | …::test_kiem_thu_tu_cong_cu | cc=[sim.run, sim.criteria] với thu_tu yêu cầu criteria trước → khong_dat |
| TC-M4-20-04 | Đơn vị | …::test_pass_hat_k | 3 lần [dat, khong_dat, dat] → pass_at_1 = 2/3, pass_hat_k False |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/` (bộ eval chưa có test riêng; chạy `python tools/bao_cao_tong.py` để chắc không sót mã TC).

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: độ đồng thuận máy chấm với doc-tay.json được báo ra (mốc ban đầu).
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M4-21 -->
<a id="m4-21"></a>
### [M4-21] Theo dõi eval qua phiên bản + băng phát lại 0 token + CI — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #76

**Mục tiêu:** Mỗi lần chạy eval ghi token/chi phí/model/git sha; có 20–30 ca vàng phát lại bằng ReplayGateway trong pytest; có CI chạy pytest và eval phát lại.
**Loại:** Hạ tầng test/đo
**Phụ thuộc:** M4-20; Gộp với M1-20 (không viết lại phần chung)
**Tệp chạm tới:** tools/chay_usecase.py, tools/eval_lich_su.py (mới), tests/test_eval_phat_lai.py (mới), tests/du-lieu-chung/bang-ghi/ (mới), .github/workflows/test.yml (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- Khoá bản ghi trong ket-qua.jsonl: `cho, cong_cu, giay, goi, loai, loi_dap, ma, ma_loi, nhan, nhap, so_loi_cong_cu, ten, uc, vi_sao`; không có token/model/sha.
- llm/__init__.py:12-22 `make_gateway(replay=…, record=…)`; llm/offline.py:141 `ReplayGateway`. `grep` trong tests/ và tools/: không chỗ nào dùng ReplayGateway; thư mục `ket-qua-do/ban-ghi` không tồn tại.
- Không có `.github/`; pytest chỉ chạy tay.

**Thay đổi cần làm:**
1. chay_usecase: ghi thêm `token_vao`, `token_ra`, `so_goi_llm`, `model` (cfg.model.main), `git_sha` (`git rev-parse --short HEAD`), `prompt_hash` (sha256 của system prompt đã dựng).
2. tools/eval_lich_su.py: gộp nhiều tệp kết quả thành `ket-qua-do/lich-su.jsonl` và in bảng pass-rate/token theo git_sha; mã thoát 1 khi pass-rate giảm so với mốc (dùng lại logic so của so_ket_qua.py).
3. Cờ `--ghi-bang` dùng `make_gateway(record=…)` cho các ca chọn; lưu vào tests/du-lieu-chung/bang-ghi/<TC>.jsonl.
4. tests/test_eval_phat_lai.py: tham số hoá theo các tệp băng, chạy Agent với `ReplayGateway`, chấm bằng `cham()`; nhãn phải khớp nhãn khi ghi.
5. .github/workflows/test.yml: Python 3.11, `pip install -e .[dev]`, `pytest -q -m "not nha_that"`.

**Không được làm (giới hạn phạm vi):**
- Không đưa GEMINI_API_KEY vào CI; CI chỉ chạy phát lại.
- Không chạy ca nha_that trên CI.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-21-01 | Tích hợp (ReplayGateway) | tests/test_eval_phat_lai.py::test_phat_lai_ca_vang | băng TC004 → nhãn == nhãn khi ghi |
| TC-M4-21-02 | Đơn vị | tests/test_eval_lich_su.py::test_pass_rate_giam_thi_ma_thoat_1 | hai tệp kết quả, B kém A một ca → mã thoát 1 |
| TC-M4-21-03 | Ca âm | …::test_giong_het_thi_ma_thoat_0 | A==B → 0 |
| TC-M4-21-04 | Đơn vị | …::test_ban_ghi_co_du_khoa_moi | bản ghi giả từ chay_usecase → có token_vao, model, git_sha |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q` toàn bộ; `python tools/so_ket_qua.py` vẫn chạy như cũ.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC (sửa prompt trong băng → TC-01 đỏ).
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: ≥20 ca vàng có băng; CI xanh.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit; xoá workflow.

<!-- TASK M5-02 -->
<a id="m5-02"></a>
### [M5-02] Vòng Agentic RAG `kb.ask` + kiểm câu trả lời bám trích dẫn bằng mã — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #77

**Mục tiêu:** câu hỏi tri thức đi qua bộ định tuyến nguồn, bước chấm liên quan, bước viết lại truy vấn có trần, và mọi con số trong câu trả lời được MÃ kiểm có nằm trong đoạn được trích hay không.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_AGENTIC_RAG`, mặc định TẮT) + Công cụ mới `kb.ask` (`core=False`, `feature="agentic_rag"`).
**Phụ thuộc:** M5-01 (cần `chi_muc.tim`). Nên làm sau M5-05 (đơn vị chuẩn) để kiểm số chính xác.
**Tệp chạm tới:** `src/eide/knowledge/kb_ask.py` (mới), `src/eide/tools/knowledge.py`, `src/eide/config.py`, `tests/test_kb_ask.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- Các nguồn là tool rời: `fact.query` (`tools/builtin.py:237`), `doc.read` (`tools/knowledge.py:385`), `ckm.graph` (`tools/ckm.py:813`), `doc.search_web` (`tools/knowledge.py:1076`). Không có bộ định tuyến.
- `doc.read` rỗng thì chỉ trả `E2004` "thử từ khoá khác" (`tools/knowledge.py:427-439`). Không có bước viết lại truy vấn.
- Không có hàm nào kiểm số trong văn bản trả lời cuối có bám nguồn hay không. N1 chỉ chặn ở cửa ghi Fact/hằng số.

**Thay đổi cần làm:**
1. `kb_ask.py::kiem_bam_nguon(tra_loi: str, doan: dict[str,str]) -> list[dict]` (hàm THUẦN, 0 token): tách các cụm `[cite:<doc_id>#<so>]`;
   với mỗi câu có số + đơn vị (dùng `docs._SO_DON_VI`), kiểm số đó có trong đoạn được cite của câu (so sau `ve_si`, dung sai 1e-9).
   Trả danh sách vi phạm `{cau, so, cite, ly_do}`. Câu có số mà không có cite cũng là vi phạm.
2. `dinh_tuyen(cau_hoi, store) -> list[str]` theo luật (thuần): có `chip:`/tên chip và khoá chuẩn của `KHOA_CHUAN` thì `fact`; có mẫu tên thanh ghi `[A-Z]{2,}\d*_[A-Z]+` thì `reg` (khi M5-03 xong); luôn có `doc` nếu có chỉ mục; kho rỗng thì `web_goi_y`.
3. Tool `kb.ask(cau_hoi)`: định tuyến → lấy ứng viên → một lời gọi LLM chấm liên quan qua tool schema `cham_lien_quan{ids:[...]}` → nếu 0 đoạn liên quan thì một lời gọi viết lại truy vấn (tối đa **2 vòng**) → trả các đoạn liên quan kèm cite cùng hướng dẫn "trả lời kèm [cite:…]".
   Hook post-answer (chỉ khi cờ bật): chạy `kiem_bam_nguon` trên câu trả lời cuối của lượt; có vi phạm thì bơm một vòng sửa (dùng cơ chế Stop-hook một vòng sẵn có), tối đa 1 vòng.
4. Trần cứng: tối đa 3 lời gọi LLM trong `kb.ask`; hết trần thì trả những gì đang có kèm `bi_cat_tran=True`.

**Không được làm (giới hạn phạm vi):**
- Không đổi hiến pháp hay prompt mặc định khi cờ TẮT. Không tự gọi `doc.search_web` (tool R3 có cổng G-DATA), chỉ gợi ý.
- Không chặn câu trả lời; chỉ bơm tối đa một vòng sửa.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-02-01 | Đơn vị | tests/test_kb_ask.py::test_so_khong_bam_nguon_bi_bat | Đoạn `{"DS#2":"VDD (max) 5.5 V"}`, câu trả lời "VDD tối đa 6.0 V [cite:DS#2]" → `kiem_bam_nguon` trả 1 vi phạm với `so==6.0` |
| TC-M5-02-02 | Ca âm | tests/test_kb_ask.py::test_so_dung_va_doi_don_vi_khong_keu_nham | Đoạn "4.7 kΩ", câu "pull-up 4700 Ω [cite:DS#3]" → 0 vi phạm |
| TC-M5-02-03 | Tích hợp (ScriptedGateway) | tests/test_kb_ask.py::test_viet_lai_truy_van_co_tran | Cờ bật qua `monkeypatch.setenv("EIDE_FEATURE_AGENTIC_RAG","1")`; kịch bản: chấm liên quan trả `ids=[]` ba lần → `kb.ask` dừng sau 2 vòng viết lại; `len(agent.llm.calls)<=3`, kết quả có `bi_cat_tran` |
| TC-M5-02-04 | Cờ TẮT | tests/test_kb_ask.py::test_co_tat_khong_dang_ky | Không đặt env → `registry.get("kb.ask") is None` và `"kb.ask" in registry.bo_qua_vi_co` |
| TC-M5-02-05 | Đơn vị | tests/test_kb_ask.py::test_dinh_tuyen | "VDD max của chip:ATmega328P" → `"fact"` đứng đầu; kho rỗng → `["web_goi_y"]` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_loop.py tests/test_subagent.py tests/test_tri_thuc.py tests/test_chi_muc.py`
- Bộ eval 76 ca / phát lại không tụt khi cờ TẮT (không đổi gì); đo lại khi cờ BẬT trước khi đề nghị bật mặc định.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Citation precision trên bộ vàng M5-21 khi cờ bật ≥ khi cờ tắt.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ `EIDE_FEATURE_AGENTIC_RAG`; revert commit.

<!-- TASK M5-06 -->
<a id="m5-06"></a>
### [M5-06] Chuẩn hoá giá trị tương đối theo nguồn ("0.7 × VDD", "VDD + 0.3") — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #78

**Mục tiêu:** VIH/VIL viết dạng tương đối được giữ thành Fact có biểu thức, và luật `muc_logic` giải được biểu thức khi có Fact VDD, thay vì bỏ hoặc đọc sai thành "0.7 V".
**Loại:** Sửa lỗi thuần (trích thiếu hoặc sai).
**Phụ thuộc:** M5-05. ĐÃ KIỂM LẠI: phần "khoá theo mục (abs_max vs operating)" của phát hiện gốc cần ngữ cảnh mục, mà ngữ cảnh mục chỉ có sau M5-04, nên đã chuyển sang M5-04 (bước 4). Nhiệm vụ này chỉ còn giá trị tương đối.
**Tệp chạm tới:** `src/eide/knowledge/chuan_hoa.py`, `src/eide/knowledge/docs.py`, `src/eide/knowledge/compare.py`, `tests/test_chuan_hoa.py`, `tests/test_tri_thuc.py`.

**Hiện trạng (đã kiểm lại trong mã):**
- `chuan_hoa.py:161` `chuan_hoa(chu, don_vi_cot, ngu_canh)`: xử lý 4R7/3V3/100n, N/A/TBD, điều kiện "@ …"; không có nhánh `× VDD` hay `VDD ±`.
- `docs.py:365-369` `_SO_DON_VI` đòi số phải kèm đơn vị; dòng "VIH 0.7 × VDD" không có đơn vị sau "0.7", nên VIH bị bỏ hẳn (hoặc lấy nhầm số khác có đơn vị trên cùng dòng).
- `compare.py:192-208` `muc_logic` dùng `_so(f)` = `float(value)`; `value=None` thì ra `nan` và so sánh luôn sai.

**Thay đổi cần làm:**
1. `chuan_hoa.py`: thêm regex `_TUONG_DOI = r"(?P<he>\d+(?:[.,]\d+)?)\s*[x×*·]\s*(?P<ref>V\s*DD(?:IO)?|V\s*CC)"` và `r"(?P<ref>V\s*DD(?:IO)?|V\s*CC)\s*(?P<dau>[+-])\s*(?P<cong>\d+(?:[.,]\d+)?)\s*V?"`.
   `GiaTri` thêm trường `tuong_doi: dict | None = None` (`{"he_so":0.7,"tham_chieu":"VDD","cong":0.0}`), `co_so=True`, `don_vi="V"`.
2. `docs.FactUngVien` thêm `bieu_thuc: str = ""`; `fact_tu_ung_vien` ghi `value=None`, `vtyp="0.7*VDD"` (dạng chuỗi), `condition` giữ nguyên.
   Đường dòng chữ: nếu dòng khớp khoá `vih|vil` và `_TUONG_DOI` thì sinh ứng viên tương đối.
3. `compare.py`: `giai_tuong_doi(f, vdd: float) -> float | None`. Trong `muc_logic(ra, vao)`: nếu `vao` là tương đối thì tìm VDD từ `vao.get("_vdd")` (người gọi truyền), không có thì trả `chua_kiem_chung` kèm lý do "cần Fact VDD của bên thu".
   `tools/knowledge.py::fact_compare` thêm tham số tuỳ chọn `fact_vdd` để truyền VDD.

**Không được làm (giới hạn phạm vi):**
- Không tự lấy VDD "đoán" từ kho; phải do người gọi chỉ rõ `fact_vdd`. Không đổi lược đồ bảng `facts` (dùng cột `vtyp` sẵn có).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-06-01 | Đơn vị | tests/test_chuan_hoa.py::test_tuong_doi_nhan | `chuan_hoa("0.7 × VDD").tuong_doi == {"he_so":0.7,"tham_chieu":"VDD","cong":0.0}` |
| TC-M5-06-02 | Đơn vị | tests/test_chuan_hoa.py::test_tuong_doi_cong | `chuan_hoa("VDD + 0.3 V").tuong_doi["cong"] == 0.3` |
| TC-M5-06-03 | Đơn vị | tests/test_tri_thuc.py::test_vih_tuong_doi_duoc_trich | Trang "VIH  input high  0.7 × VDD" → ứng viên `vih.min` có `bieu_thuc=="0.7*VDD"` (không phải `gia_tri==0.7` đơn vị V) |
| TC-M5-06-04 | Đơn vị | tests/test_tri_thuc.py::test_muc_logic_giai_tuong_doi | VOH 3.0 V, VIH 0.7×VDD, VDD 5.0 V → `khong_dat` (3.0 < 3.5) |
| TC-M5-06-05 | Ca âm | tests/test_tri_thuc.py::test_tuong_doi_thieu_vdd_khong_ket_luan | Không có VDD → `chua_kiem_chung`, không phải `dat` |
| TC-M5-06-06 | Ca âm | tests/test_chuan_hoa.py::test_so_thuong_khong_bi_doc_thanh_tuong_doi | `chuan_hoa("3.3 V").tuong_doi is None` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_chuan_hoa.py tests/test_tri_thuc.py tests/test_ing_c.py tests/test_office.py`
- 8 luật so sánh cũ cho đúng kết quả cũ với Fact tuyệt đối.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M5-08 -->
<a id="m5-08"></a>
### [M5-08] Vòng đời phiên bản Fact: thay thế khi nạp bản tài liệu mới + `fact.supersede` — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #79

**Mục tiêu:** khi một tài liệu được nạp lại với nội dung mới, các Fact của bản cũ bị đánh dấu thay thế sau khi người duyệt, và `fact.cross_check` có đường đóng mâu thuẫn, thay vì Fact cũ sống mãi.
**Loại:** Công cụ mới (`fact.supersede`, R2, `core=False`) + Sửa lỗi thuần (cột `superseded_by` có mà không ai ghi).
**Phụ thuộc:** M5-10 (cần `Store.get_fact`).
**Tệp chạm tới:** `src/eide/store/db.py`, `src/eide/tools/knowledge.py`, `src/eide/knowledge/compare.py`, `tests/test_fact_phien_ban.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `store/db.py:80` có `supersedes`, `superseded_by`; `query_facts` (`db.py:496-511`) lọc `superseded_by IS NULL`. `grep superseded_by src/` chỉ ra db.py: không ai ghi.
- `docs.py:627-631`: `fact_id` băm `doc.hash[:8]`, nên bản mới sinh Fact mới bên cạnh Fact cũ.
- `tools/knowledge.py:289-383` `doc_load` luôn `op="create"` khi ghi `doc`, không so với bản cũ cùng `doc_id`.

**Thay đổi cần làm:**
1. `Store.supersede_fact(cu: str, moi: str, ly_do: str)`: `UPDATE facts SET superseded_by=? WHERE fact_id=?` và `supersedes=?` cho bản mới, trong một giao dịch.
2. `doc.load`: nếu `ctx.store.get(doc_id)` đã có và `hash` khác thì ghi `op="update"`, trả thêm `ban_cu_hash` và `note_vi` "chạy fact.extract lại rồi fact.cross_check để chọn bản".
3. `doi_chieu_cheo`: khi các bản cùng `(subject,key)` đến từ cùng `doc_id` nhưng khác `source.version`/hash thì gắn `"cung_tai_lieu_khac_ban": True` và đề xuất bản mới.
4. Tool `fact.supersede(fact_cu, fact_moi, ly_do)` (R2): cả hai phải tồn tại (dùng `get_fact`), không thì `E2009`; ghi sổ cái `note` `{"supersede":..}`.
5. Không xoá Fact cũ; `fact.query` mặc định đã ẩn Fact bị thay.

**Không được làm (giới hạn phạm vi):**
- Không tự thay thế mà không có người duyệt (giữ tinh thần `can_nguoi_chon`). Không đổi công thức `fact_id`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-08-01 | Đơn vị | tests/test_fact_phien_ban.py::test_supersede_an_fact_cu | `put_fact` A (vdd.max 5.5) và B (5.0) → `supersede_fact("A","B","errata")` → `query_facts(key="vdd.max")` chỉ còn B; B có `supersedes=="A"` |
| TC-M5-08-02 | Tích hợp (registry) | tests/test_fact_phien_ban.py::test_cong_cu_supersede | `fact.supersede` qua registry → `ok`; sổ cái có note `supersede` |
| TC-M5-08-03 | Ca âm | tests/test_fact_phien_ban.py::test_id_khong_ton_tai | `fact_moi="f-khong-co"` → `code=="E2009"`, không đổi gì trong kho |
| TC-M5-08-04 | Tích hợp | tests/test_fact_phien_ban.py::test_nap_lai_ban_moi_bao_ban_cu | Nạp tệp văn bản `doc_id="DS"`, sửa tệp, `doc.load` lại → `ok`, có `ban_cu_hash` |
| TC-M5-08-05 | Ca âm | tests/test_fact_phien_ban.py::test_nap_lai_cung_noi_dung_khong_bao | Nạp lại y nguyên → không có `ban_cu_hash` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ing_c.py tests/test_tri_thuc.py tests/test_doc_van_ban.py tests/test_ing_d.py`
- `test_tep_doi_sau_khi_nap_thi_bao_E2005...` vẫn E2005 khi ĐỌC (chưa nạp lại).

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit; `UPDATE facts SET superseded_by=NULL, supersedes=NULL` nếu cần gỡ dữ liệu.

<!-- TASK M5-09 -->
<a id="m5-09"></a>
### [M5-09] Luật so sánh kiểm thứ nguyên + điều kiện; đối chiếu chéo theo điều kiện — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #80

**Mục tiêu:** `so_sanh` không kết luận khi hai vế khác thứ nguyên, cảnh báo khi điều kiện đo khác nhau, và `doi_chieu_cheo` không báo mâu thuẫn giả giữa các điều kiện khác nhau.
**Loại:** Sửa lỗi thuần.
**Phụ thuộc:** M5-05 (bảng thứ nguyên dùng chung).
**Tệp chạm tới:** `src/eide/knowledge/compare.py`, `tests/test_tri_thuc.py`, `tests/test_ing_c.py`.

**Hiện trạng (đã kiểm lại trong mã):**
- `compare.py:82-130` `doi_chieu_cheo`: nhóm `(subject, key)`, bỏ qua `condition`.
- `compare.py:169-174` `_so` trả `(si, don_vi_co_ban)` nhưng `muc_logic`/`qua_ap` (`192-226`) bỏ phần đơn vị (`voh, _ = _so(ra)`).
- `compare.py:367` `so_sanh(ten_luat, a, b)` là điểm vào chung.

**Thay đổi cần làm:**
1. Trong `so_sanh` (sau `_chan_dong`): nếu cả hai vế có `unit` và `_so(a)[1] != _so(b)[1]` thì trả `KetQuaSoSanh(luat, "chua_kiem_chung", "info", chua_kiem_chung=True, giai_thich="Hai vế khác thứ nguyên (V vs A)…")`.
   Ngoại lệ: luật `trung_af` (so chuỗi chức năng, không có đơn vị).
2. `_dieu_kien(f) -> dict` dùng `chuan_hoa.tach_dieu_kien(f.get("condition") or "")`. Nếu hai vế cùng có một khoá điều kiện (vdd, ta, iol…) với giá trị khác nhau thì kết luận giữ nguyên nhưng `muc` tối thiểu `minor` và thêm câu "khác điều kiện: …" vào `giai_thich`.
3. `muc_logic` thêm `bien_nhieu = voh - vih` vào `giai_thich`; `dat` mà biên < 0.2 V thì `ket_luan="canh_bao"`, `muc="minor"`.
4. `doi_chieu_cheo`: khoá nhóm thành `(subject, key, _chuan_dk(condition))`.

**Không được làm (giới hạn phạm vi):**
- Không đổi tên luật hay chữ ký `so_sanh`. Không đổi luật N2 (vế ĐỒNG).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-09-01 | Đơn vị | tests/test_tri_thuc.py::test_khac_thu_nguyen_khong_ket_luan | `so_sanh("muc_logic", _f("voh.min",3.3,"V"), _f("vih.min",25,"mA"))` → `chua_kiem_chung` |
| TC-M5-09-02 | Đơn vị | tests/test_tri_thuc.py::test_khac_dieu_kien_canh_bao | VOH 3.3 V cond "VDD=3.3V", VIH 2.0 V cond "VDD=5V" → `giai_thich` chứa "khác điều kiện" |
| TC-M5-09-03 | Đơn vị | tests/test_tri_thuc.py::test_bien_nhieu_mong | VOH 3.0 V, VIH 2.9 V → `ket_luan=="canh_bao"` |
| TC-M5-09-04 | Đơn vị | tests/test_ing_c.py::test_dieu_kien_khac_khong_phai_mau_thuan | Hai Fact `vol.max` 0.4 V (IOL=4mA) và 0.9 V (IOL=20mA) → `doi_chieu_cheo(...) == []` |
| TC-M5-09-05 | Ca âm | tests/test_tri_thuc.py::test_TC013_muc_logic_khong_tuong_thich | (test cũ) vẫn `khong_dat`/`blocker` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_tri_thuc.py tests/test_ing_c.py tests/test_ing_d.py tests/test_erc.py`
- `test_so_sanh_doi_don_vi_truoc_khi_ket_luan` (5000 mV vs 5 V) vẫn xanh.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M5-11 -->
<a id="m5-11"></a>
### [M5-11] Mở rộng CKM: ngoại vi–thanh ghi–AF–clock + truy vấn đường đi `ckm.path` — P1 · L

**Giai đoạn:** GĐ3 · thứ tự #81

**Mục tiêu:** câu hỏi nhiều bước (chân → chức năng thay thế → ngoại vi → bit bật clock) trả lời được bằng một lời gọi có trích dẫn từng cạnh.
**Loại:** Công cụ mới (`ckm.path`, `core=False`) + mở rộng từ vựng đồ thị (cộng thêm).
**Phụ thuộc:** M5-03 (nguồn thanh ghi từ SVD). Bảng AF từ PDF cần M5-04; trước đó chỉ lấy AF từ Fact `pin:` đã có.
**Tệp chạm tới:** `src/eide/knowledge/ckm.py`, `src/eide/tools/ckm.py`, `src/eide/store/db.py` (chỉ thêm hàm truy vấn), `tests/test_ckm_path.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `ckm.py:39-42`: `LOAI_NUT=("chip","pin","net","module","bus","rail","rang_buoc","tai_lieu","fact","chuc_nang","linh_kien")`, `LOAI_CANH=("CO_CHAN","NOI","DUOC_GAN","GOM","THUC_HIEN","CAP","AP_LEN","SINH","THAY_THE")`. Danh sách đóng, kiểm bằng `_hop_le_loai` (`ckm.py:356`).
- `tools/ckm.py:813-854` `ckm.graph`: đếm hoặc liệt kê theo loại/chip; không có truy vấn đường đi.
- `store/db.py:592` `ckm_cac_canh(loai, tu, den)` là truy vấn một bước.

**Thay đổi cần làm:**
1. Thêm vào `LOAI_NUT`: `"ngoai_vi","thanh_ghi","truong_bit","clock"`; vào `LOAI_CANH`: `"CO_AF"` (pin→chuc_nang), `"THUOC"` (chuc_nang→ngoai_vi), `"CO_THANH_GHI"` (ngoai_vi→thanh_ghi), `"CO_TRUONG"` (thanh_ghi→truong_bit), `"BAT_CLOCK"` (ngoai_vi→truong_bit).
2. `ckm.chieu_svd(store)`: từ Fact `reg:`/`field:` tạo nút và cạnh `CO_THANH_GHI`/`CO_TRUONG`; cạnh `BAT_CLOCK` khi tên trường RCC khớp `<NGOAI_VI>EN` (USART1EN → ngoai_vi:USART1).
   Gọi trong `chieu()` khi có Fact `reg:`.
3. `Store.ckm_duong_di(tu, den, *, loai_canh=None, sau_toi_da=4) -> list[list[dict]]`: BFS bằng `WITH RECURSIVE` trên `ckm_edges`, trả tối đa 5 đường.
4. Tool `ckm.path(tu, den, sau_toi_da=4)` (R1, `core=False`, mô tả ≤ 400 ký tự): trả các đường kèm `nguon` của từng nút (Fact/trích dẫn). Không có đường thì `E2003` kèm gợi ý nạp SVD/bảng AF.

**Không được làm (giới hạn phạm vi):**
- Không đổi chỉ mục `ux_ckm_duoc_gan` hay ngữ nghĩa `DUOC_GAN`. Không thêm bảng mới (dùng `ckm_nodes/ckm_edges`).
- Không sinh cạnh từ tri thức chung của mô hình (chỉ từ Fact tầng ≥ NGUOI).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-11-01 | Đơn vị | tests/test_ckm_path.py::test_loai_moi_hop_le | `ckm_dat_nut(loai="thanh_ghi", ...)` không nổ (hiện `_hop_le_loai` từ chối) |
| TC-M5-11-02 | Đơn vị | tests/test_ckm_path.py::test_duong_di_ba_buoc | Nút pin:U1.PA9 →CO_AF→ chuc_nang:USART1_TX →THUOC→ ngoai_vi:USART1 →BAT_CLOCK→ truong_bit:RCC.APB2ENR.USART1EN → `ckm_duong_di("pin:U1.PA9","truong_bit:RCC.APB2ENR.USART1EN")` có 1 đường dài 3 cạnh |
| TC-M5-11-03 | Tích hợp (registry) | tests/test_ckm_path.py::test_chieu_svd_sinh_bat_clock | Nạp SVD tối giản (RCC.APB2ENR.USART1EN + USART1) qua `doc.load` → `ckm.build` → `ckm.path` từ `ngoai_vi:USART1` tới trường đó `ok` |
| TC-M5-11-04 | Ca âm | tests/test_ckm_path.py::test_khong_co_duong_thi_noi_ro | Hai nút rời → `E2003`, không bịa đường |
| TC-M5-11-05 | Ca biên | tests/test_ckm_path.py::test_tran_do_sau | Chuỗi 6 cạnh, `sau_toi_da=4` → không trả đường nào, không treo |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ckm.py tests/test_cay.py tests/test_khoi.py tests/test_sch0.py tests/test_sch_a.py`
- `ckm.graph` trả đúng khoá cũ; Mermaid sinh ra không đổi khi không có nút loại mới.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit (nút/cạnh mới chỉ cộng thêm, xoá theo `loai`).

<!-- TASK M5-14 -->
<a id="m5-14"></a>
### [M5-14] Bộ nhớ bài học kỹ thuật (lesson) có bằng chứng, hết hạn, tra theo mã lỗi — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #82

**Mục tiêu:** tác tử lưu được bài học "lỗi X do Y, sửa bằng Z" kèm bằng chứng và được nhắc lại bằng MÃ khi gặp lại đúng mã lỗi/công cụ, qua phiên và (khi người duyệt) qua dự án.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_BAI_HOC`, mặc định TẮT) + Công cụ mới `memory.lesson` (`core=False`, `feature="bai_hoc"`).
**Phụ thuộc:** **Gộp với M1-14 và M3-21.** Nhiệm vụ này chỉ phụ trách LƯU TRỮ + TRUY XUẤT bài học (hiện vật `lesson`, tool ghi, chèn khi gặp lỗi). Phần hook tự sinh bài học sau chuỗi lỗi→sửa thuộc M1-14/M3-21 (dùng `ghi_bai_hoc()` của nhiệm vụ này). Làm M5-14 trước hoặc cùng lúc.
**Tệp chạm tới:** `src/eide/memory/bai_hoc.py` (mới), `src/eide/tools/writing.py`, `src/eide/store/db.py` (`ARTEFACT_TYPES`), `src/eide/loop.py` (chỗ `_tool_error`), `src/eide/config.py`, `tests/test_bai_hoc.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `tools/writing.py:229-276` `memory.note`: `section` enum chỉ có Mục tiêu/Chip & phần cứng/Quyết định/Giả định/Quy ước/Đừng.
- `memory/nguoi_dung.py:28-35` `CHU_DE`: 6 chủ đề sở thích, không có bài học kỹ thuật.
- `memory/summary.py:36` mục `loi_da_gap` chỉ sống trong bản tóm tắt C2.
- `loop.py:919-925` `_tool_error` ghi `tool_result` và message lỗi; không tra gì thêm. `grep -i "bai_hoc|lesson|reflex" src/` chỉ ra comment.

**Thay đổi cần làm:**
1. `ARTEFACT_TYPES` thêm `"lesson"`. `bai_hoc.py::BaiHoc` dataclass: `trigger={"tool","ma_loi","chip","tu_khoa":[...]}`, `trieu_chung`, `nguyen_nhan`, `cach_sua`, `bang_chung=[run_id|changeset]`, `do_tin` (0–1), `so_lan_ap_dung`, `verified_at`, `het_han_sau_ngay` (mặc định 180).
2. `ghi_bai_hoc(ctx, bh) -> Changeset` ghi qua `ctx.history.ghi_kho(type="lesson", ...)` (có explain, theo N8). Trùng (cùng `tool`+`ma_loi`+`nguyen_nhan` chuẩn hoá) thì cập nhật `so_lan_ap_dung`, không tạo bản mới.
3. `tra_bai_hoc(store, *, tool, ma_loi, chip="") -> list[BaiHoc]`: lọc theo trigger, bỏ bản hết hạn, sắp theo `do_tin*so_lan_ap_dung`, tối đa 3.
4. Khi cờ bật: trong `_tool_error`, gắn vào `result` của lỗi trường `bai_hoc_lien_quan` (≤ 3 dòng, mỗi dòng ≤ 200 ký tự). Cờ tắt thì không đổi gì.
5. Tool `memory.lesson` (R2, `writes_artefact=True`, `needs_explain=True`): `bang_chung` bắt buộc khác rỗng; rỗng thì `E4004` như `remember_user`. Kho xuyên dự án để giai đoạn sau, chỉ sau thẻ người duyệt (không làm ở đây).

**Không được làm (giới hạn phạm vi):**
- Không ghi bài học vào EIDE.md (tránh phình trần 3000 token). Không tự ghi xuyên dự án.
- Không chèn bài học vào mọi lượt; chỉ khi lỗi khớp trigger.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-14-01 | Đơn vị | tests/test_bai_hoc.py::test_ghi_va_tra_theo_ma_loi | Ghi bài học trigger `{"tool":"code.vendor_fetch","ma_loi":"E3001"}` → `tra_bai_hoc(tool="code.vendor_fetch", ma_loi="E3001")` có 1 kết quả |
| TC-M5-14-02 | Đơn vị | tests/test_bai_hoc.py::test_trung_thi_tang_dem | Ghi cùng bài học 2 lần → 1 hiện vật, `so_lan_ap_dung==2` |
| TC-M5-14-03 | Đơn vị | tests/test_bai_hoc.py::test_het_han_bi_bo | `verified_at` cách 200 ngày, `het_han_sau_ngay=180` → không được trả |
| TC-M5-14-04 | Tích hợp (ScriptedGateway) | tests/test_bai_hoc.py::test_loi_khop_thi_kem_bai_hoc | Cờ bật; kịch bản gọi một tool nổ mã lỗi đã có bài học → message tool trong `agent.messages` có `bai_hoc_lien_quan` |
| TC-M5-14-05 | Cờ TẮT | tests/test_bai_hoc.py::test_co_tat_y_nhu_cu | Cờ tắt, cùng kịch bản → không có `bai_hoc_lien_quan`; `registry.get("memory.lesson") is None` |
| TC-M5-14-06 | Ca âm | tests/test_bai_hoc.py::test_khong_bang_chung_bi_tu_choi | Cờ bật, `memory.lesson` với `bang_chung=[]` → `E4004` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_a.py tests/test_mem_b.py tests/test_mem_c.py tests/test_mem_d.py tests/test_loop.py`
- Bộ eval 76 ca / phát lại không tụt khi cờ TẮT.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ `EIDE_FEATURE_BAI_HOC`; revert commit.

<!-- TASK M5-18 -->
<a id="m5-18"></a>
### [M5-18] Phiếu kiểm C2 không lộ đáp án; sinh câu hỏi từ đoạn bị nén; đo tỉ lệ phủ — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #83

**Mục tiêu:** phép kiểm sau nén đo được mất mát thật: không câu nào chứa sẵn đáp án, câu hỏi lấy từ số/id/ràng buộc của chính đoạn bị nén, và tỉ lệ phủ tất định được ghi vào sổ cái.
**Loại:** Phần A: Sửa lỗi thuần (câu hỏi lộ đáp án, ô xanh giả). Phần B: Hạ tầng đo (`ty_le_phu` chỉ ghi, không chặn). Phần C: Đổi hành vi (chặn nén theo phủ, cờ `EIDE_FEATURE_NEN_KIEM_PHU`, mặc định TẮT).
**Phụ thuộc:** Không. Làm trước M5-19 (M5-19 dùng `ty_le_phu`).
**Tệp chạm tới:** `src/eide/memory/summary.py`, `src/eide/memory/nen.py`, `src/eide/memory/don_dep.py` (`do_luong`), `src/eide/config.py`, `tests/test_mem_c.py`.

**Hiện trạng (đã kiểm lại trong mã):**
- `summary.py:150-160` `lam_phieu_kiem`: câu ADR `hoi=f"Quyết định {ma} là quyết định về việc gì? Nêu mã của nó."`, `dap_an=ma`, nên `CauKiem.dung` luôn đạt. Ledger `changeset.touches` là list mã hiện vật (`history.py:236`).
- `summary.py:161-167` câu cổng: đáp án "duyệt"/"từ chối" (50 % đoán trúng). `summary.py:186-196` câu bù: từ đầu tiên dài ≥5 chữ của lời người đầu phiên.
- `nen.py:258` `phieu = sm.lam_phieu_kiem(self.ledger, self.store)`, sinh TRƯỚC khi chia đoạn, không dựa vào `doan`.

**Thay đổi cần làm:**
1. (A) `lam_phieu_kiem`: bỏ câu nào có `_chuan(dap_an) in _chuan(hoi)`. Câu ADR đổi thành hỏi nội dung `summary` của changeset (đáp án là một từ khoá ≥5 chữ của summary, không xuất hiện trong câu hỏi). Bỏ câu cổng đúng/sai.
2. (B) `phieu_tu_doan(doan) -> list[CauKiem]` (thuần): rút (a) số + đơn vị trong lời người (`docs._SO_DON_VI`), (b) mã `ADR-|FR-|NFR-|f-[0-9a-f]{10}` và đường dẫn trong `tep_dang_sua`, (c) câu của người chứa "không được|đừng|phải|luôn|tối đa|tối thiểu".
   Câu hỏi che đáp án (thay đáp án bằng "___"). `nen()` gộp: tối đa 3 câu từ sổ cái + 5 câu từ đoạn.
3. (B) `ty_le_phu(doan, tt, store, eide_md) -> float`: tỉ lệ phần tử (a)(b) có trong `tt.van_ban()` hoặc trong kho/EIDE.md. Ghi vào sự kiện `compact` `buoc=="ok"` và `kiem_truot`; `do_luong` báo trung bình.
4. (C) Khi cờ bật: `ty_le_phu < 0.9` thì coi như kiểm trượt (đi nhánh tăng K hiện có).

**Không được làm (giới hạn phạm vi):**
- Không đổi luật "câu hỏi không công bằng thì bỏ" (`nen.py:350-381`). Không tăng số lời gọi LLM (vẫn một lời gọi kiểm cho cả phiếu).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-18-01 | Đơn vị | tests/test_mem_c.py::test_phieu_khong_lo_dap_an | `agent.ledger.append("changeset", {"id":"cs-1","author":"agent:run-1","touches":["ADR-03"],"summary":"chọn giao thức MTP để truyền tệp"})` → mọi câu trong `lam_phieu_kiem` có `_chuan(dap_an) not in _chuan(hoi)` |
| TC-M5-18-02 | Đơn vị | tests/test_mem_c.py::test_phieu_tu_doan_lay_rang_buoc | `doan` có lời người "dòng PWM tối đa 2 A, đừng dùng HAL" → `phieu_tu_doan` có câu với `dap_an` "2 A" và câu với `dap_an` chứa "HAL" |
| TC-M5-18-03 | Đơn vị | tests/test_mem_c.py::test_ty_le_phu | `doan` chứa "ADR-07" và "2 A"; `tt` chỉ chứa "ADR-07" → `ty_le_phu == 0.5` |
| TC-M5-18-04 | Tích hợp (ScriptedGateway) | tests/test_mem_c.py::test_ty_le_phu_vao_so_cai | `bn.nen` ok → sự kiện `compact` `buoc=="ok"` có khoá `ty_le_phu` |
| TC-M5-18-05 | Cờ TẮT | tests/test_mem_c.py::test_co_tat_phu_thap_van_nhan | Cờ tắt, `ty_le_phu` thấp, trả lời kiểm đúng → `kq.ok` (như cũ). Cờ bật → `not kq.ok` |
| TC-M5-18-06 | Ca âm | tests/test_mem_c.py::test_phieu_kiem_sinh_tu_SO_CAI_khong_tu_mo_hinh | (test cũ) vẫn có phiếu khác rỗng |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_c.py tests/test_mem_d.py tests/test_mem_b.py`
- Mọi test `test_MEM08_*` giữ xanh (luật huỷ nén, tăng K, câu không công bằng).

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] `memory.metrics` hiển thị `ty_le_phu` trung bình.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit; tắt cờ `EIDE_FEATURE_NEN_KIEM_PHU`.

<!-- TASK M5-19 -->
<a id="m5-19"></a>
### [M5-19] Lược đồ tóm tắt C2 thêm `rang_buoc`/`so_lieu_then_chot`; kiểm trần bằng mã; PreCompact chèn mã còn thiếu — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #84

**Mục tiêu:** ràng buộc người nói giữa chừng, số then chốt và các mã ADR/FR chưa vào kho không bị mất khi nén, và trần token mỗi mục được MÃ kiểm.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_NEN_RANG_BUOC`, mặc định TẮT; đổi prompt và lược đồ tool tóm tắt).
**Phụ thuộc:** M5-18 (dùng `ty_le_phu` để đo trước/sau).
**Tệp chạm tới:** `src/eide/memory/summary.py`, `src/eide/memory/nen.py`, `src/eide/config.py`, `tests/test_mem_c.py`.

**Hiện trạng (đã kiểm lại trong mã):**
- `summary.py:27-38` `MUC`: 10 mục, không có ràng buộc hay số then chốt. `summary.py:42` `MUC_KHONG_DUOC_BO` có 3 mục.
- `summary.py:56-58`: trần (`tran`) chỉ nằm trong `description` của lược đồ; không mã nào kiểm.
- `summary.py:236-240` `prompt_tom_tat`: mỗi message `str(chu)[:1500]`.
- `nen.py:87-112` `pre_compact` trả `chua_co_trong_M2`; `nen.py:276` chỉ gán `kq.rut_vao_m2` và ghi sổ, không ai dùng (grep `rut_vao_m2` chỉ ra nen.py).

**Thay đổi cần làm:**
1. Khi cờ bật: `MUC` thêm `("rang_buoc", "[{noi_dung, nguon_luot}] — lời người: không được/phải/tối đa…", 150)` và `("so_lieu_then_chot", "[{gia_tri, don_vi, fact_id|nguon}]", 150)`; cả hai vào `MUC_KHONG_DUOC_BO`.
   Viết thành hàm `muc_hien_hanh(features)` để cờ tắt thì lược đồ y như cũ (`test_luoc_do_du_MUOI_muc...` vẫn đúng).
2. `BanTomTat.vuot_tran() -> list[str]` (dùng `envelope.uoc_token`). Vượt thì gọi lại tóm tắt MỘT lần kèm câu "rút gọn các mục: …"; vẫn vượt thì nhận và ghi `vuot_tran` vào sổ.
3. `prompt_tom_tat`: thay `[:1500]` bằng: với message tool có `envelope.summary_line` thì dùng dòng đó cộng mọi số + đơn vị và mã (regex) rút từ toàn văn; message người/mô hình giữ tối đa 3000 ký tự.
4. Sau bước tóm tắt: nếu `pre["chua_co_trong_M2"]` khác rỗng mà mã đó không có trong `tt.van_ban()` thì nối vào `quyet_dinh` dòng "chưa ghi kho: ADR-07, …" (bằng mã, không gọi LLM).

**Không được làm (giới hạn phạm vi):**
- Không đổi tên/thứ tự 10 mục cũ. Không ghi gì vào kho từ `pre_compact` (giữ luật "kho chỉ nhận qua changeset").

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-19-01 | Đơn vị | tests/test_mem_c.py::test_co_bat_luoc_do_co_rang_buoc | Cờ bật → `luoc_do_tom_tat()` có `rang_buoc`, `so_lieu_then_chot` trong `required` |
| TC-M5-19-02 | Đơn vị | tests/test_mem_c.py::test_so_sau_ky_tu_1500_khong_mat | Message tool dài 5000 ký tự, "IOL 25 mA" ở vị trí 4000 → `prompt_tom_tat([...])` chứa "25 mA" |
| TC-M5-19-03 | Tích hợp (ScriptedGateway) | tests/test_mem_c.py::test_ma_chua_vao_kho_duoc_chen | Cờ bật; `ms[2]["text"]="chốt ADR-07 dùng MTP"`; tóm tắt trả `quyet_dinh="—"` → `ms[0]["text"]` chứa "ADR-07" |
| TC-M5-19-04 | Tích hợp | tests/test_mem_c.py::test_vuot_tran_goi_lai_mot_lan | `muc_tieu` dài 2000 token → đúng 2 lời gọi tóm tắt trong `agent.llm.calls` |
| TC-M5-19-05 | Cờ TẮT | tests/test_mem_c.py::test_luoc_do_du_MUOI_muc_va_moi_muc_bat_buoc | (test cũ) cờ tắt vẫn đúng 10 mục |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_c.py tests/test_mem_d.py`
- Luật tombstone (`test_MEM13_*`) và "nén mà phình thì không nhận" giữ xanh.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] `ty_le_phu` (M5-18) trung bình trên eval_nho (M5-21) khi cờ bật ≥ khi cờ tắt.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ `EIDE_FEATURE_NEN_RANG_BUOC`; revert commit.

<!-- TASK M5-21 -->
<a id="m5-21"></a>
### [M5-21] Bộ eval vàng cho trích xuất, tìm kiếm, nén và resume — P1 · M

**Giai đoạn:** GĐ3 · thứ tự #85

**Mục tiêu:** có số đo chất lượng (precision/recall trích Fact, recall@5/MRR, citation precision, `ty_le_phu`, pass@1 làm tiếp) để M5-01…M5-20 chứng minh "tốt lên" bằng số.
**Loại:** Hạ tầng test/đo.
**Phụ thuộc:** Không (nên làm SỚM; các nhiệm vụ khác dùng làm mốc). Phần đo tìm kiếm chạy khi M5-01 xong; phần `ty_le_phu` khi M5-18 xong.
**Tệp chạm tới:** `tests/eval_tri_thuc/` (mới: `vang_*.yaml`, `test_eval_tri_thuc.py`), `tools/eval_tri_thuc.py` (mới), `tests/lam_pdf.py` (dùng lại).

**Hiện trạng (đã kiểm lại trong mã):**
- `tests/test_tri_thuc.py`, `test_doc_van_ban.py`, `test_ing_*.py`, `test_mem_*.py`: khoảng 350 test hợp đồng hành vi, dữ liệu tổng hợp (`lam_pdf.DATASHEET_ATMEGA` 3 trang).
- Không có bộ vàng, không có script đo chất lượng. Lỗi lệch khoá `fmax`/`f.max` (M5-05) và resume rỗng (M5-17) lọt qua vì test chỉ khẳng định hình dạng.

**Thay đổi cần làm:**
1. `tests/eval_tri_thuc/vang_tong_hop.yaml`: 3 "datasheet" dựng bằng `lam_pdf` (mở rộng từ `DATASHEET_ATMEGA`, `DATASHEET_CAM_BIEN_5V`, thêm một bảng điều kiện nhiệt độ/abs-max). Mỗi cái có ≥ 15 Fact đúng (khoá, giá trị, đơn vị, trang) và ≥ 3 "bẫy" (số điều kiện, địa chỉ) không được trích.
2. `tools/eval_tri_thuc.py`: `cham_trich(vang) -> {"precision","recall","bay_lot"}`; `cham_tim(vang, ham_tim) -> {"recall@5","mrr"}` (bỏ qua nếu chưa có `chi_muc`); `cham_bam_nguon(...)` (khi có M5-02). In bảng và ghi JSON vào `.eide/eval/` (không commit).
3. `tests/eval_tri_thuc/test_eval_tri_thuc.py`: chạy trong `pytest -q` mặc định với ngưỡng SÀN (đặt bằng số đo hiện tại trừ 0.02), để hồi quy chất lượng làm đỏ CI. Datasheet thật (ATmega328P/STM32F469/ESP32) đánh dấu `@pytest.mark.nha_that`.
4. `eval_nho`: 3 phiên ghi sẵn (`ReplayGateway` trong `llm/offline.py`) có ràng buộc gài ("đừng dùng HAL", "dòng tối đa 2 A"), đo `ty_le_phu` sau C2 và pass@1 của câu hỏi "làm tiếp" sau resume.

**Không được làm (giới hạn phạm vi):**
- Không gọi mạng hay LLM thật trong `pytest -q` mặc định. Không commit PDF có bản quyền (chỉ đường dẫn + `nha_that`).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-21-01 | Đo | tests/eval_tri_thuc/test_eval_tri_thuc.py::test_bay_dieu_kien_khong_lot | Bẫy "VDD (max) 3.6 V at TA = 25 °C" → `bay_lot == 0` (ĐỎ trên mã hiện tại cho tới khi M5-05 xong; đánh `xfail(strict=True)` kèm mã M5-05 cho tới lúc đó) |
| TC-M5-21-02 | Đo | tests/eval_tri_thuc/test_eval_tri_thuc.py::test_san_recall_trich | `recall >= SAN_RECALL` (mốc đo lần đầu) |
| TC-M5-21-03 | Đo | tests/eval_tri_thuc/test_eval_tri_thuc.py::test_resume_sau_C2 | `eval_nho` phiên 1 → resume chứa ràng buộc gài (ĐỎ cho tới M5-17; `xfail(strict=True)`) |
| TC-M5-21-04 | Ca âm | tests/eval_tri_thuc/test_eval_tri_thuc.py::test_vang_hop_le | Mọi Fact vàng có trang tồn tại trong PDF dựng ra, có đơn vị thuộc `_HE_SO` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q` toàn bộ (bộ eval thêm vào không được làm chậm quá 5 s).

**Tiêu chí xong:**
- [ ] Các TC mới chạy; `xfail(strict=True)` chuyển thành xanh đúng lúc nhiệm vụ tương ứng xong (strict bảo đảm phải gỡ xfail).
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Số đo mốc ghi trong DEV-LOG.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** xoá thư mục `tests/eval_tri_thuc/` và `tools/eval_tri_thuc.py`.


---

## Giai đoạn 4 — Có thì tốt: P2/P3

<!-- TASK M1-16 -->
<a id="m1-16"></a>
### [M1-16] Phản biện tự động cho quyết định kiến trúc (option/ADR) — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #86

**Mục tiêu:** mỗi lần chốt phương án hoặc ghi ADR, một subagent phản biện chỉ-đọc chấm theo rubric cố định, và thẻ duyệt hiện cả quan điểm phản biện.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_PHAN_BIEN`, mặc định TẮT)
**Phụ thuộc:** M1-03, M1-07. Gộp với M2-04 và M2-13: khung 'phản biện + trọng tài' dựng MỘT lần ở đây, hai nhiệm vụ kia chỉ thêm định nghĩa/điểm móc.
**Tệp chạm tới:** src/eide/subagent.py, src/eide/hooks/standard.py, src/eide/config.py, tests/test_subagent.py, tests/test_phan_bien.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- ke_hoach.py `thieu_phan_tich` — đòi bước `store.option_create`/`store.option_choose`/`store.adr_create` cho kế hoạch viết mã mới.
- subagent.py — có "design-review" (soi bản đồ mạch) và "code-analyst"; không có vai phản biện kiến trúc. Không hook nào chạy sau `store.option_choose`.

**Thay đổi cần làm:**
1. `SUBAGENT["phan-bien"]`: công cụ chỉ-đọc (fact.query, store.get, store.list, fs.read, fs.glob, ledger.query), `toi_da_goi=8`. System prompt: tìm lý do phương án hỏng theo 5 tiêu chí (tài nguyên chip, thời gian thực, khả năng test, rủi ro người, phụ thuộc ngoài), mỗi tiêu chí 0–2 điểm, phải dẫn Fact.
2. Hook post_tool_use `phan_bien_kien_truc` (cờ bật, tool ∈ {store.option_choose, store.adr_create}, kết quả ok): chạy subagent qua `kiem_va_chay`, lưu kết quả vào `ctx.phan_bien[artefact_id]` và append message `_he_thong` tóm tắt (điểm, phản chứng).
3. Điểm < 6/10 hoặc có phản chứng dẫn Fact VÀNG/BẠC: lời nhắc yêu cầu tác tử trình cả hai quan điểm cho người dùng. Không tự sửa, không vòng lại quá 1 lần.

**Không được làm (giới hạn phạm vi):**
- Không chặn `store.option_choose` (chỉ thêm thông tin). Không cho phan-bien công cụ ghi.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-16-01 | Đơn vị | tests/test_subagent.py::test_phan_bien_chi_co_cong_cu_doc | `SA.SUBAGENT["phan-bien"].cong_cu` không giao với tập ghi (như `test_verifier_chi_co_cong_cu_DOC`). |
| TC-M1-16-02 | Tích hợp (cờ BẬT) | tests/test_phan_bien.py::test_chot_phuong_an_thi_co_phan_bien | Tạo option qua store.option_create, gọi store.option_choose; kịch bản có báo cáo phan-bien → ledger `subagent_stop` với `subagent=="phan-bien"`; messages có `_he_thong` chứa "phản biện". |
| TC-M1-16-03 | Ca âm | tests/test_phan_bien.py::test_ghi_REQ_khong_goi_phan_bien | `store.req_create` → không có subagent chạy. |
| TC-M1-16-04 | Cờ TẮT | tests/test_phan_bien.py::test_tat_co_khong_phan_bien | Như TC-02, cờ tắt → không có subagent_stop. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_ke_hoach.py tests/test_phan_tich_thiet_ke_len_tab.py tests/test_ai_quyet.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ.

<!-- TASK M1-18 -->
<a id="m1-18"></a>
### [M1-18] tool.search chuẩn hoá dấu tiếng Việt và chỉ mở khoá công cụ đủ điểm — P2 · S

**Giai đoạn:** GĐ4 · thứ tự #87

**Mục tiêu:** câu tìm không dấu vẫn tìm đúng công cụ; mỗi lần tìm mở khoá tối đa 3 công cụ đạt ngưỡng, kèm lý do khớp.
**Loại:** Sửa lỗi thuần (chuẩn hoá dấu) + Đổi hành vi (giới hạn số mở khoá, cờ `EIDE_FEATURE_TIM_CONG_CU_GON`, mặc định TẮT)
**Phụ thuộc:** Liên quan M1-02 (cùng giảm lược đồ).
**Tệp chạm tới:** src/eide/tools/registry.py, src/eide/tools/builtin.py, tests/test_policy_tools.py

**Hiện trạng (đã kiểm lại trong mã):**
- registry.py:146-170 `search` — so `q in t.name.lower()`, `q in t.summary_vi.lower()`, keywords, từng từ; không bỏ dấu. Mở khoá `scored[:8]`.
- Đã chạy thử: `search("kiem toan ven so cai")` KHÔNG trả `ledger.verify` (trả branch.create, code.vendor_list…), trong khi `search("kiểm toàn vẹn sổ cái")` trả nó đầu tiên. `search("xuất ra tệp powerpoint")` mở khoá đủ 8 công cụ.
- hooks/s0.py có `normalize_vi(s)` (bỏ dấu, thay đ→d, hạ chữ).

**Thay đổi cần làm:**
1. Sửa lỗi thuần: trong `search`, chuẩn hoá cả `q` và các trường (`name`, `summary_vi`, `keywords`) bằng `normalize_vi` trước khi so. Dời `normalize_vi` sang mô-đun tiện ích dùng chung (vd. `eide/chu.py`) và để hooks/s0.py import lại, không nhân bản.
2. Cờ bật: chỉ mở khoá kết quả có điểm ≥ 5 và tối đa 3; mỗi mục trả thêm `ly_do_khop` (trường nào khớp).
3. Ghi ledger `tool_search` gồm truy vấn và danh sách tên trả về (luôn bật).

**Không được làm (giới hạn phạm vi):**
- Không đổi hành vi `normalize_vi` (test_s0.py phụ thuộc).
- Không đổi chữ ký `search(query, limit=8)`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-18-01 | Đơn vị | tests/test_policy_tools.py::test_tool_search_khong_dau_van_tim_thay | `build_registry().search("kiem toan ven so cai")` → "ledger.verify" nằm trong 3 kết quả đầu. |
| TC-M1-18-02 | Đơn vị (cờ BẬT) | tests/test_policy_tools.py::test_tool_search_mo_toi_da_ba | `search("xuất ra tệp powerpoint")` → `len(reg._unlocked) <= 3`; mỗi mục có `ly_do_khop`. |
| TC-M1-18-03 | Cờ TẮT | tests/test_policy_tools.py::test_tool_search_tat_co_mo_nhu_cu | Cùng truy vấn → mở khoá tới 8 như hiện nay. |
| TC-M1-18-04 | Ca âm | tests/test_policy_tools.py::test_tool_search_vo_nghia_khong_mo_gi | Cờ bật, `search("zzqx")` → `_unlocked` rỗng. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_policy_tools.py tests/test_s0.py tests/test_nang_luc.py tests/test_duong_dan_toi_cong_cu.py tests/test_sch0.py`
- `test_tool_search_mo_khoa` giữ nguyên.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ; revert phần chuẩn hoá.

<!-- TASK M1-19 -->
<a id="m1-19"></a>
### [M1-19] Kiểm kiểu, enum và lược đồ lồng nhau cho tham số công cụ — P2 · S

**Giai đoạn:** GĐ4 · thứ tự #88

**Mục tiêu:** tham số sai kiểu hoặc sai enum bị chặn trước khi vào thân công cụ, với lỗi E5001 chỉ rõ đường dẫn trường, không còn rơi vào E5999 "không phải lỗi tham số".
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** Không.
**Tệp chạm tới:** src/eide/tools/registry.py, tests/test_policy_tools.py

**Hiện trạng (đã kiểm lại trong mã):**
- registry.py:219-232 `_validate_args` — chỉ kiểm `required` và trường lạ.
- registry.py `run` — `except Exception` → E5999 "Đây là lỗi bên trong công cụ, không phải lỗi tham số của bạn".
- tools/builtin.py `fs_read` — `start = max(0, (offset or 1) - 1)`, nên `offset="abc"` gây TypeError, thành E5999.
- `errors.schema_violation(what, why)` trả E5001 (test `test_thieu_tham_so_bat_buoc` kiểm code E5001).

**Thay đổi cần làm:**
1. `_validate_args`: kiểm đệ quy `type` (string/integer/number/boolean/array/object, không phân biệt hoa thường), `enum`, `items`, `properties` lồng và `required` lồng, `minimum`/`maximum`. Ép kiểu an toàn: chuỗi số nguyên "3" → 3 cho trường integer, "true"/"false" cho boolean; ghi đè vào `args` (bản sao). Lỗi trả `schema_violation(f"tham số của {spec.name}", f"{duong_dan}: cần {kieu}, nhận {repr(gia_tri)[:40]}")`.
2. `run`: `TypeError` phát sinh ngay khi gọi `spec.fn(ctx=ctx, **args)` (sai tên hoặc số tham số) đổi thành E5001; lỗi khác giữ E5999.

**Không được làm (giới hạn phạm vi):**
- Không thêm phụ thuộc `jsonschema` (giữ triết lý không thêm phụ thuộc như config.load_dotenv).
- Không đổi lược đồ của bất kỳ công cụ nào.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-19-01 | Đơn vị | tests/test_policy_tools.py::test_sai_kieu_tham_so_la_E5001 | `reg.run("fs.read", {"path":"main.c","offset":"abc"}, ctx)` → code E5001, message chứa "offset". |
| TC-M1-19-02 | Đơn vị | tests/test_policy_tools.py::test_ep_kieu_chuoi_so_nguyen | `{"path":"main.c","offset":"1","limit":"1"}` → ok, `lines_shown == [1,1]`. |
| TC-M1-19-03 | Đơn vị | tests/test_policy_tools.py::test_sai_enum_bi_chan | `memory.note` với `section="Linh tinh"` → E5001 chứa "section". |
| TC-M1-19-04 | Ca âm | tests/test_policy_tools.py::test_tham_so_dung_khong_bi_keu_nham | Mọi ví dụ hợp lệ hiện có (fs.read main.c, fs.glob "*.c", fact.query {}) → ok. |
| TC-M1-19-05 | Hồi quy | tests/test_policy_tools.py::test_moi_cong_cu_luoc_do_tu_kiem_duoc | Với mọi spec trong `reg.all()`, `_validate_args(spec, {})` không ném exception Python (chỉ trả None hoặc EideError). |

**Bảo vệ hồi quy (phải vẫn XANH):**
- Toàn bộ `.venv/bin/python -m pytest -q` (đụng mọi công cụ). Đặc biệt test_policy_tools.py, test_ke_hoach.py (lược đồ `buoc` lồng), test_subagent.py, test_ckm.py, test_sch_a.py.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M1-21 -->
<a id="m1-21"></a>
### [M1-21] Công cụ phân tích Python dùng một lần trong sandbox chỉ-đọc — P2 · L

**Giai đoạn:** GĐ4 · thứ tự #89

**Mục tiêu:** tác tử chạy được một đoạn Python ngắn (chỉ đọc dự án, không mạng, có trần thời gian và đầu ra) để trả lời câu hỏi phân tích thay cho hàng chục lời gọi fs.*.
**Loại:** Công cụ mới (`py.phan_tich`, core=False, R1) + Đổi hành vi về khả dụng (cờ `EIDE_FEATURE_PY_PHAN_TICH`, mặc định TẮT; tắt thì không đăng ký)
**Phụ thuộc:** M1-03 (đi qua hàng rào). Liên quan M2-17, M3-08. Kiểm trùng với các công cụ chạy lệnh của mảng build/HDL trước khi làm.
**Tệp chạm tới:** src/eide/tools/phan_tich_py.py (mới), src/eide/tools/builtin.py (register), src/eide/config.py, src/eide/loop.py (`_CONG_CU_DOC`), tests/test_py_phan_tich.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- nang_luc.py + tools/nang_luc.py — `tool.propose`/`tool.reload` cho công cụ LÂU DÀI (thẻ hiện mã nguồn, test xanh, `.eide/cong-cu`).
- Không có công cụ chạy mã tạm (grep `@r.tool("shell|cmd|python|exec|script|run` không có). Có `env.check`, `test.run`, `test.sensitivity` cho việc riêng.
- Đo trong docstring nang_luc.py: 580/1078 lời gọi (54 %) là fs.read/grep/glob.

**Thay đổi cần làm:**
1. `Features.py_phan_tich` + `ten_co()`; `ToolSpec(feature="py_phan_tich")` để tắt là không đăng ký (cơ chế `Registry._co_bat`).
2. Công cụ `py.phan_tich(ma: str, tep: list[str] = [])`: chạy `sys.executable -I -c <bộ bọc>` trong tiến trình con. `cwd` là thư mục tạm; danh sách `tep` (phải qua `_sandbox`) được chép vào đó chỉ-đọc. Môi trường rỗng, không có biến proxy. Timeout 10 s. Cắt stdout/stderr 4.000 ký tự. Trên macOS nếu có `sandbox-exec` thì dùng hồ sơ cấm mạng và cấm ghi ngoài thư mục tạm; không có thì từ chối chạy với lỗi rõ ràng (không chạy kém an toàn trong im lặng).
3. Mô tả ≤ 400 ký tự; `risk="R1"`, `writes_artefact=False`; thêm vào `_CONG_CU_DOC`.
4. Ghi `ma` và kết quả vào ledger (qua tool_use sẵn có).

**Không được làm (giới hạn phạm vi):**
- Không cho ghi tệp dự án, không cho mạng, không chạy trong tiến trình EIDE (khác với tool.propose).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-21-01 | Lược đồ (cờ BẬT) | tests/test_py_phan_tich.py::test_dang_ky_dung_hop_dong | `reg.get("py.phan_tich")` có `core is False`, `risk=="R1"`, mô tả ≤ 400 ký tự. |
| TC-M1-21-02 | Hành vi | tests/test_py_phan_tich.py::test_dem_dong_main_c | `ma="print(len(open('main.c').read().splitlines()))"`, `tep=["main.c"]` → stdout "1". |
| TC-M1-21-03 | Lỗi | tests/test_py_phan_tich.py::test_khong_ghi_duoc_vao_du_an | Mã ghi `../du-an-thu/x.txt` hoặc đường tuyệt đối dự án → tệp không xuất hiện trong du_an; kết quả báo lỗi. |
| TC-M1-21-04 | Lỗi | tests/test_py_phan_tich.py::test_vong_vo_han_bi_cat_10s | `ma="while True: pass"` → lỗi timeout trong ≤ 12 s (đánh dấu chậm nếu cần). |
| TC-M1-21-05 | Cờ TẮT | tests/test_py_phan_tich.py::test_tat_co_khong_dang_ky | `reg.get("py.phan_tich") is None`; tên có trong `reg.bo_qua_vi_co`. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_policy_tools.py tests/test_nang_luc.py tests/test_loop.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Rà an toàn: đã thử thoát sandbox (mạng, ghi, đọc `~`) và ghi kết quả vào DEV-LOG.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ (công cụ không được đăng ký).

<!-- TASK M1-22 -->
<a id="m1-22"></a>
### [M1-22] Lỗi điều kiện policy không được làm sập cả lượt — P2 · S

**Giai đoạn:** GĐ4 · thứ tự #90

**Mục tiêu:** khi `PolicyEngine.decide` ném ValueError, vòng lặp chặn an toàn lời gọi đó bằng lỗi có hướng dẫn, ghi incident, và lượt tiếp tục. Lỗi cú pháp trong policy.yaml lộ ra ngay lúc khởi tạo.
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** M1-01 (để các lời gọi còn lại trong batch vẫn có kết quả).
**Tệp chạm tới:** src/eide/loop.py, src/eide/policy/engine.py, tests/test_loop.py, tests/test_policy_tools.py

**Hiện trạng (đã kiểm lại trong mã):**
- policy/engine.py `_eval` — `raise ValueError(f"Điều kiện policy không tính được: {expr!r}")`.
- tests/test_policy_tools.py::test_dieu_kien_sai_cu_phap_thi_no_chu_khong_cho_qua — KHẲNG ĐỊNH `pol.decide` phải ném ValueError, nên KHÔNG được đổi hành vi của `decide`.
- loop.py:833 — `perm = self.policy.decide(c, pre.facts, spec)` không có try. `turn` (loop.py ~300-330) chỉ có `try/finally`, nên ngoại lệ thoát ra ngoài lượt.
- ĐÃ KIỂM LẠI: m1.json đề xuất mã E4012, nhưng E4012 đã được dùng. Đổi sang E4033.

**Thay đổi cần làm:**
1. loop.py `_one_tool` (hoặc `kiem_va_chay` sau M1-03): bọc `policy.decide` trong `try/except ValueError as e`. Ghi `ledger.append("incident", {"code":"E4033","tool":..., "loi": str(e)})`, `ctx.emit(uic.notice("Luật cấp quyền lỗi — đã chặn an toàn thao tác này.", level="error", code="E4033"))`, rồi `_tool_error(call, EideError("E4033", "Luật cấp quyền không tính được; thao tác bị chặn an toàn.", hint_for_agent="Đừng thử lại thao tác này; báo người dùng.", blame="system"), ctx)`.
2. engine.py: thêm `PolicyEngine.tu_kiem() -> list[str]` thử `_eval` mọi `when`/`auto_if` với một env mẫu (mọi nhóm known có giá trị `_Dot({})`) và trả danh sách luật lỗi. Agent.__init__ gọi nó và ghi incident nếu có (không ném).

**Không được làm (giới hạn phạm vi):**
- Không đổi `decide`/`_eval` (giữ ném ValueError). Không chuyển lỗi thành "allow".

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M1-22-01 | Tích hợp (ScriptedGateway) | tests/test_loop.py::test_luat_policy_loi_thi_chan_an_toan_khong_sap | `agent.policy.rules.insert(0, {"id":"XX","tool":"fs.read","when":"này ( sai","action":"deny"})`; kịch bản [fs.read main.c, Response(text="ok")] → `agent.turn` không ném; message tool có code E4033; ledger có incident E4033. |
| TC-M1-22-02 | Ca âm | tests/test_loop.py::test_luat_policy_loi_khong_chan_cong_cu_khac | Cùng luật lỗi chỉ cho fs.read; lời gọi fs.glob trong cùng lượt → ok. |
| TC-M1-22-03 | Đơn vị | tests/test_policy_tools.py::test_tu_kiem_phat_hien_luat_loi | `pol.rules.insert(0, luật lỗi)` → `pol.tu_kiem()` trả ["XX"]; policy.yaml gốc → `[]`. |
| TC-M1-22-04 | Hồi quy | tests/test_policy_tools.py::test_dieu_kien_sai_cu_phap_thi_no_chu_khong_cho_qua (có sẵn) | Vẫn ném ValueError từ `decide`. |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_policy_tools.py tests/test_loop.py tests/test_snapshot.py tests/test_cx_cong_tac.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M2-07 -->
<a id="m2-07"></a>
### [M2-07] Bước thất bại và `plan.revise` (Replanner) có trần — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #91

**Mục tiêu:** một bước vỡ thì tác tử đánh dấu `that_bai` kèm lý do và sửa phần CHƯA làm của kế hoạch, không phải bỏ cả kế hoạch.
**Loại:** Công cụ mới (`plan.revise`, `core=False`, `feature="ke_hoach_sua"`) kèm Đổi hành vi.
**Phụ thuộc:** M2-06. Gộp với M1-13: nếu M1-13 đã thêm trạng thái bước hoặc replanner thì chỉ bổ sung phần còn thiếu (trần, Reflexion).
**Tệp chạm tới:** src/eide/ke_hoach.py, src/eide/tools/ke_hoach.py, src/eide/config.py, tests/test_ke_hoach_sua.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- ke_hoach.py `Buoc.xong: bool`; không có trạng thái thất bại.
- ke_hoach.py:285 `doi_chieu`: chỉ báo `ngoai_ke_hoach` và `chua_lam`, "không phía nào bị coi là lỗi".
- `KHONG_KHOA` = plan.enter, plan.exit, plan.cancel, plan.step_done, memory.note. Muốn đổi hướng thì phải `plan.enter` lại và kế hoạch cũ bị cất (`ke_hoach_cu_luu_o`).

**Thay đổi cần làm:**
1. `Buoc` thêm `trang_thai: str = "cho"` (cho | xong | that_bai | bo) và `ly_do: str = ""`. Giữ `xong` như thuộc tính tương thích (`xong == (trang_thai == "xong")`) để mã cũ không vỡ.
2. Thêm công cụ `plan.step_fail(so, ly_do)` (`core=False`, cùng cờ): ghi `that_bai`, lưu `ly_do`, và gọi logic của `memory.note` mục "Bài học" với một dòng ngắn.
3. Thêm `plan.revise(tu_buoc, buoc_moi, ly_do)`: chỉ thay các bước có chỉ số ≥ `tu_buoc` và chưa `xong`, rồi chạy lại `kiem_ke_hoach` + `thieu_phan_tich`. Nếu số bước đổi > 30% hoặc thêm công cụ có gate thì đưa kế hoạch về `cho_duyet` (thẻ G-SCOPE).
4. Trần: mỗi kế hoạch tối đa 3 lần revise (đếm trong `KeHoach.so_lan_sua`); lần thứ 4 trả `E6011`.
5. Thêm `plan.step_fail` và `plan.revise` vào `KHONG_KHOA`.

**Không được làm (giới hạn phạm vi):**
- Không cho revise sửa bước đã `xong`; không tự gọi LLM.
- Không đổi hành vi `plan.enter` cất kế hoạch cũ.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-07-01 | Đơn vị | tests/test_ke_hoach_sua.py::test_revise_giu_buoc_da_xong | kế hoạch 4 bước, bước 1 xong → revise từ 2 → bước 1 nguyên vẹn, các bước sau được thay |
| TC-M2-07-02 | Ca biên | …::test_revise_qua_3_lan_thi_E6011 | 4 lần revise liên tiếp → lần 4 trả lỗi E6011 |
| TC-M2-07-03 | Tích hợp | …::test_step_fail_ghi_bai_hoc | step_fail → `eide_md.get("Bài học")` (hoặc mục tương đương đang dùng) chứa ly_do |
| TC-M2-07-04 | Đơn vị | …::test_doi_nhieu_buoc_thi_quay_ve_cho_duyet | revise đổi >30% số bước → `trang_thai=="cho_duyet"` |
| TC-M2-07-05 | Cờ TẮT | …::test_co_tat_khong_co_cong_cu | `build_registry(Features())` → `get("plan.revise") is None` |
| TC-M2-07-06 | Ca biên | …::test_xong_tuong_thich_nguoc | `Buoc(xong=True)` cũ → `from_dict` cho `trang_thai=="xong"` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ke_hoach.py tests/test_chia_viec_lon.py tests/test_mem_a.py tests/test_mem_b.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ `ke_hoach_sua`.

<!-- TASK M2-12 -->
<a id="m2-12"></a>
### [M2-12] Sơ đồ mô-đun: khớp include theo đường dẫn, kiểm phân tầng — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #92

**Mục tiêu:** cạnh include không nối nhầm khi hai thư mục có cùng tên tệp; và tab Thiết kế báo được include đi ngược tầng đã khai.
**Loại:** Sửa lỗi thuần (khớp sai) cộng phần trình bày trên tab (không đổi hành vi tác tử).
**Phụ thuộc:** Phần phân tầng cần hiện vật `code_structure` từ M2-06 (nếu chưa có thì chỉ làm bước 1).
**Tệp chạm tới:** src/eide/kien_truc.py, tests/test_phan_tich_thiet_ke_len_tab.py.

**Hiện trạng (đã kiểm lại trong mã):**
- kien_truc.py:85–100 `so_do_mo_dun`: `theo_ten.setdefault(Path(d).name, [])`, nên `#include "config.h"` nối tới MỌI `config.h` trong dự án.
- kien_truc.py:150: danh sách tệp lấy từ `store.list("code", limit=200)`.
- Test có sẵn: `test_so_do_dung_canh_tu_include_THAT` khớp `rtos_types.h` từ `main.c` ở gốc tới `rtos/rtos_types.h`. Hành vi khớp theo tên khi chỉ có MỘT ứng viên phải được giữ.

**Thay đổi cần làm:**
1. Hàm `_khop_include(nguon, chuoi_include, theo_ten) -> list[str]`, theo thứ tự: (a) đường tương đối theo thư mục của tệp nguồn; (b) đường tương đối theo gốc; (c) theo tên, chỉ khi có đúng 1 ứng viên; nhiều ứng viên mà không phân giải được thì KHÔNG nối, và đếm vào `mo_ho`.
2. `so_do_mo_dun` trả thêm số cạnh mơ hồ qua một hàm mới `so_do_mo_dun_chi_tiet()`. Giữ `so_do_mo_dun` trả tuple 3 phần tử như cũ.
3. `muc_kien_truc`: nếu có hiện vật `code_structure` với `tang` cho tệp/thư mục (app > service > driver > hal), thì thêm mục "Vi phạm phân tầng" liệt kê cạnh đi từ tầng thấp lên tầng cao.

**Không được làm (giới hạn phạm vi):**
- Không đổi `TRAN_TEP`, không vẽ ô rời (giữ `test_KHONG_ve_so_do_khi_khong_co_quan_he_nao`).
- Không đọc thư mục -I từ cấu hình build ở nhiệm vụ này.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-12-01 | Đơn vị | tests/test_phan_tich_thiet_ke_len_tab.py::test_hai_config_h_khong_noi_nham | `a/x.c` include "config.h"; có `a/config.h` và `b/config.h` → chỉ 1 cạnh, tới `a/config.h` (mã cũ ra 2 cạnh) |
| TC-M2-12-02 | Ca âm | …::test_mot_ung_vien_van_khop_theo_ten | giữ nguyên kịch bản rtos → 2 cạnh |
| TC-M2-12-03 | Ca biên | …::test_mo_ho_thi_khong_noi_va_dem | `main.c` ở gốc include "config.h", có 2 bản ở 2 thư mục → 0 cạnh, `mo_ho == 1` |
| TC-M2-12-04 | Đơn vị | …::test_vi_pham_phan_tang | KhoGia có `code_structure` hal/app; `hal/x.c` include `app/y.h` → mục "Vi phạm phân tầng" có cạnh này |
| TC-M2-12-05 | Ca âm | …::test_khong_co_code_structure_thi_khong_co_muc | không có mục "Vi phạm phân tầng" |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_phan_tich_thiet_ke_len_tab.py tests/test_so_do.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M2-17 -->
<a id="m2-17"></a>
### [M2-17] CodeAct chỉ-đọc: công cụ `analysis.py` chạy Python trong tiến trình con có giới hạn — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #93

**Mục tiêu:** câu hỏi phân tích dùng một lần (log, CSV, quét mã) được trả lời bằng 1 lời gọi chạy mã có giới hạn, thay vì 10–20 lời gọi `fs.grep`.
**Loại:** Công cụ mới (`core=False`, `feature="phan_tich_py"`, mặc định TẮT).
**Phụ thuộc:** Gộp với M1-21 và M3-08 (cùng ý CodeAct). Chỉ làm một công cụ chung; nếu M1-21 đã dựng sandbox thì dùng lại và chỉ thêm helper phân tích mã.
**Tệp chạm tới:** src/eide/tools/phan_tich_py.py (mới), src/eide/tools/__init__.py, src/eide/config.py, tests/test_phan_tich_py.py (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- Danh sách công cụ đăng ký (grep `@r.tool(`) không có công cụ nào chạy Python/shell tuỳ ý. `tool.propose` là đường duy nhất để tác tử tự viết mã công cụ (có bộ kiểm, người duyệt).
- ke_hoach.py docstring: 580/1078 lời gọi (54%) là fs.read/fs.grep/fs.glob trên phiên STM32F469.
- Registry hỗ trợ `feature=` (registry.py:65, 110).

**Thay đổi cần làm:**
1. Công cụ `analysis.py(ma: str ≤ 8000 ký tự, explain)`, R1, `core=False`, `writes_artefact=True` (ghi artefact `analysis`), mô tả ≤ 400 ký tự.
2. Chạy bằng `subprocess.run([sys.executable, "-I", "-c", PRELUDE + ma], cwd=<thư mục tạm>, timeout=30, env={...})` với env tối thiểu: không truyền proxy, PATH rỗng; đặt `resource.setrlimit` (RLIMIT_AS 512 MB, RLIMIT_CPU 30 s) trong `preexec_fn` khi có.
3. PRELUDE vô hiệu ghi: monkeypatch `open` để chặn chế độ ghi ngoài thư mục tạm, chặn `socket`, `subprocess`, `os.system`; cung cấp `GOC` (đường dẫn dự án, chỉ đọc), `doc_ma(p)`, `ky_hieu(p)` (từ phan_tich_ma), `doc_csv(p)`.
4. stdout và stderr cắt ở 4000 ký tự kèm `da_cat` và `do_dai_that` (theo bài học DEV-324 trong VIEC-CHO-LAM mục 7).
5. Kết quả ghi artefact `analysis` (thuộc KHONG_STALE), và `note_vi` nhắc "đây là DỮ KIỆN do mã chạy, không phải kết luận".

**Không được làm (giới hạn phạm vi):**
- Không cho ghi tệp trong dự án, không cho mạng, không bật mặc định.
- Không thay `tool.propose`.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-17-01 | Tích hợp | tests/test_phan_tich_py.py::test_dem_dong_tep | `build_registry(Features(phan_tich_py=True))`, fixture `bo` → `ma="print(len(doc_ma('main.c').splitlines()))"` → stdout "1" |
| TC-M2-17-02 | Ca âm (an toàn) | …::test_ghi_tep_du_an_bi_chan | `open(GOC+'/main.c','w')` → lỗi trong stderr; main.c không đổi |
| TC-M2-17-03 | Ca âm (an toàn) | …::test_mang_bi_chan | `import socket; socket.create_connection(...)` → lỗi |
| TC-M2-17-04 | Ca biên | …::test_vong_vo_han_bi_cat_boi_timeout | `while True: pass` (timeout giảm còn 2 s qua monkeypatch) → `ok` False, mã lỗi mới `E4034` |
| TC-M2-17-05 | Ca biên | …::test_dau_ra_dai_bi_cat_va_noi_ra | in 10 000 ký tự → `da_cat` True, `do_dai_that` ≥ 10000 |
| TC-M2-17-06 | Cờ TẮT | …::test_co_tat_khong_dang_ky | `build_registry(Features()).get("analysis.py") is None` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_policy_tools.py tests/test_loop.py tests/test_tai_lieu_khop_ma.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] Bật cờ, đo số lời gọi mỗi câu hỏi phân tích trên 5 kịch bản phát lại.
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ `phan_tich_py`.

<!-- TASK M2-19 -->
<a id="m2-19"></a>
### [M2-19] REQ: kiểm câu trích có trong sổ cái và bám nguồn (cảnh báo, hạ tầng tin cậy) — P2 · S

**Giai đoạn:** GĐ4 · thứ tự #94

**Mục tiêu:** REQ có `source_quote` không khớp lời người trong sổ cái thì bị gắn tầng `DONG` và cảnh báo, như ADR đã được bảo vệ.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_REQ_BAM_NGUON`, mặc định TẮT).
**Phụ thuộc:** Không.
**Tệp chạm tới:** src/eide/tools/writing.py, src/eide/tools/design.py (tách hàm dùng chung), src/eide/config.py, tests/test_req_bam_nguon.py (mới).

**ĐÃ KIỂM LẠI:** JSON đề xuất "không khớp thì trả lỗi kiểu E5007". Đọc lại test_cx_cong_tac.py:79–86 (CX06): người dùng gõ "Ghi yêu cầu nhận phim qua LAN rồi nối driver", còn `source_quote` là "copy phim qua mạng LAN vào đó". Câu trích không phải chuỗi con của lời người, nên chặn sẽ làm đỏ CX06; việc người dùng diễn đạt qua nhiều lượt hoặc qua tệp cũng hợp lệ. Nhiệm vụ được chỉnh thành CẢNH BÁO kèm hạ `explain.confidence` xuống DONG, không chặn.

**Hiện trạng (đã kiểm lại trong mã):**
- writing.py:186 `store_req_create`: chỉ đòi `source_quote` khác rỗng (qua `required` và luật N7 trong policy).
- design.py `_kiem_nguoi_that_su_chon` bước 1: `noi_nguoi = [_go_dau(e.data.get("text","")) for e in ctx.ledger.read() if e.kind == "human_act"]`, rồi kiểm `t in x`.
- surfaces.py:136–141 bảng A2.1 có cột "Tầng" lấy từ `explain.confidence`.

**Thay đổi cần làm:**
1. Tách `_cau_co_trong_so_cai(ctx, trich) -> bool` từ design.py thành hàm module dùng chung (design.py gọi lại hàm này; hành vi E5007 giữ nguyên).
2. Khi cờ bật, trong `store_req_create`/`store_req_update` (khi có quote): nếu không khớp, hạ `explain["confidence"]="DONG"` trước khi ghi, và trả `canh_bao_nguon` + `note_vi` "câu trích không thấy trong lời người dùng — hỏi lại hoặc trích đúng nguyên văn".
3. Kiểm bám nguồn nhẹ: số có đơn vị trong `text`/`criteria` mà không có trong `source_quote` và không có trong Fact thì liệt kê vào `canh_bao_nguon` (dùng lại cách tìm số của human_edit.py:109).

**Không được làm (giới hạn phạm vi):**
- Không trả `ToolResult(False)`. Không đổi E5006–E5009 và test_ai_quyet.py.
- Không sửa REQ đã có trên đĩa.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-19-01 | Tích hợp | tests/test_req_bam_nguon.py::test_trich_bia_thi_ha_DONG | `make_agent`, cờ bật, ledger có human_act "làm bộ chép phim" → req_create quote "pin dùng 1 tuần" → `store.get("FR-01")["explain"]["confidence"]=="DONG"` và có `canh_bao_nguon` |
| TC-M2-19-02 | Ca âm | …::test_trich_dung_khong_keu | quote là chuỗi con của lời người → giữ confidence gốc, không có cảnh báo |
| TC-M2-19-03 | Đơn vị | …::test_so_khong_co_nguon_bi_liet_ke | criteria "≥ 5 MB/s", quote không có số → "5 MB/s" có trong cảnh báo |
| TC-M2-19-04 | Cờ TẮT | …::test_co_tat_y_cu | cờ tắt → kết quả không có `canh_bao_nguon`, confidence không đổi |
| TC-M2-19-05 | Hồi quy | tests/test_cx_cong_tac.py::test_CX06_nguoi_sua_REQ_thi_ha_nguon_STALE_va_tac_tu_nhac | xanh với cả cờ bật lẫn tắt |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ai_quyet.py tests/test_cx_cong_tac.py tests/test_policy_tools.py`

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh.
- [ ] DEV-LOG.

**Hoàn tác:** tắt cờ `req_bam_nguon`.

<!-- TASK M3-11 -->
<a id="m3-11"></a>
### [M3-11] Footprint trong netlist và đối chiếu footprint BOM ↔ sơ đồ — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #95

**Mục tiêu:** Netlist `.net` mang footprint khi đã biết; BOM lệch footprint với sơ đồ, hoặc số pad lệch số chân, đều bị báo.
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/sch/netlist.py`, `src/eide/sch/soan.py`, `src/eide/sch/doc_skidl.py`, `src/eide/knowledge/eda.py`, `tests/test_sch_a.py`, `tests/test_eda.py`

**Hiện trạng (đã kiểm lại trong mã):**
- sch/netlist.py `viet_net`: `comp` chỉ có `ref`/`value`/`libsource`, không có `(footprint …)`.
- sch/doc_skidl.py:37 `part: ref → {lib, ten, value}`; `_doc_part` (:185) chỉ đọc `ref` và `value`.
- knowledge/eda.py:94 `LinhKien.footprint` được đọc từ `.net`, nhưng `doi_chieu_bom_netlist` (:262) chỉ so ref, giá trị và số lượng. `DongBom` không có cột footprint.

**Thay đổi cần làm:**
1. `soan._part_va_noi`: nếu `canonical.footprint` của lá có giá trị thì sinh `footprint="<...>"` trong `Part(...)`. `doc_skidl._doc_part` đọc thêm kw `footprint`. `viet_net` ghi `(footprint "…")` khi `part[ref]` có.
2. `eda.py`: `_COT_FOOTPRINT = {"footprint","package","gói","fp"}`; `DongBom.footprint: str = ""`; `doc_bom_csv` đọc cột này.
3. `doi_chieu_bom_netlist`: thêm danh sách `footprint_khac` khi cả hai bên có footprint và khác nhau (không phân biệt hoa thường). Chỉ thêm câu vào `se_mat_vi`; `khop` = False khi có lệch.
4. Hàm `so_pad_tu_ten(fp) -> int|None` (regex `-(\d+)` trong SOIC-8, SOT-23-5, QFN-32…). Có Fact pinout (số chân) mà khác số pad thì thêm vào kết quả `pad_lech`.

**Không được làm (giới hạn phạm vi):**
- Không ghi `tstamps` (giữ `test_viet_net_KHONG_ghi_tstamp_bia`).
- Không đổi thứ tự hay dạng của các dòng `.net` hiện có khi không có footprint (giữ `test_viet_net_dung_dang_kicad_va_xac_dinh`).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-11-01 | Đơn vị | tests/test_sch_a.py::test_viet_net_ghi_footprint_khi_co | `viet_net({"N":["U1.1"]}, part={"U1":{"ten":"x","footprint":"SOIC-8"}})` → chuỗi có `(footprint "SOIC-8")` |
| TC-M3-11-02 | Ca âm | tests/test_sch_a.py::test_viet_net_khong_footprint_y_nhu_cu | part không có footprint → đầu ra bằng đúng đầu ra hiện tại (so với chuỗi chụp trước khi sửa) |
| TC-M3-11-03 | Đơn vị | tests/test_eda.py::test_bom_lech_footprint_bi_bao | BOM `R5,4k7,R_0805` và netlist `R5 4k7 R_0603` → `footprint_khac` có R5, `khop` False |
| TC-M3-11-04 | Ca âm | tests/test_eda.py::test_bom_khong_co_cot_footprint_khong_bao_lech | BOM không có cột footprint → không có `footprint_khac` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_sch_a.py tests/test_sch0.py tests/test_eda.py`
- `test_TC062_*` giữ nguyên.

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-16 -->
<a id="m3-16"></a>
### [M3-16] Tách tệp RTL/testbench khi lint và synth; chặn latch và đa nguồn lái — P2 · S

**Giai đoạn:** GĐ4 · thứ tự #96

**Mục tiêu:** Tổng hợp chỉ ăn RTL thật (không lẫn testbench hay bài khác), và latch hoặc tín hiệu nhiều nguồn lái làm chặng không đạt trừ khi người đã chấp nhận.
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/build/hdl.py`, `src/eide/tools/hdl.py`, `tests/test_hdl.py`

**Hiện trạng (đã kiểm lại trong mã):**
- hdl.py:371 `_nguon_hdl(duong)`: mọi `*.v`/`*.sv` dưới thư mục, chỉ loại thư mục ẩn và `build`/`obj_dir`/`node_modules`.
- hdl.py:405 `lint`: `--top-module` chỉ thêm khi có `dinh`. hdl.py:530 `tong_hop`: `read_verilog -sv <mọi tệp>; synth_gowin -top X`, không có `hierarchy -check` hay `check -assert`.
- hdl_cay.py:240 `tu_lenh_tong_hop` đọc danh sách tệp từ lệnh synth đã chạy, nên sửa danh sách tệp sẽ tự đi theo.
- Fixture `_du_an` đặt `tb.v` chung thư mục `rtl/` với `blinky.v` trong vài test sim.

**Thay đổi cần làm:**
1. `_nguon_hdl(duong, *, bo_tb=False)`: khi `bo_tb=True`, loại `*_tb.v`, `tb_*.v`, `tb.v`, `*_tb.sv` và mọi tệp nằm trong thư mục `sim/`, `tb/`, `test/`. `tong_hop` gọi với `bo_tb=True`; `mo_phong` giữ như cũ.
2. Trong `tong_hop`, kịch bản yosys thành `read_verilog -sv ...; hierarchy -check -top X; proc; check -assert; synth_gowin -top X -json ...`. `check -assert` trượt thì `vi_sao_khong_dat` nói "đa nguồn lái / vòng tổ hợp" và trích dòng của yosys.
3. `lint`: phân loại `kq.canh_bao` theo `ma` (LATCH, MULTIDRIVEN, UNDRIVEN, WIDTH…) thành `kq.tai_nguyen["canh_bao_theo_ma"]`. Có LATCH hoặc MULTIDRIVEN thì `dat=False`, trừ khi tham số mới `chap_nhan: list[str]` chứa mã đó.
4. Bước 0 khi làm: chạy thật một RTL có latch trên máy có verilator và yosys, xác nhận mã cảnh báo thực tế; ghi vào DEV-LOG nếu khác giả định.

**Không được làm (giới hạn phạm vi):**
- Không đổi đường dẫn tệp ra (`.eide/hdl/<dinh>.json`).
- Không làm hỏng `hdl_cay.tu_lenh_tong_hop` (định dạng `lenh` phải vẫn có `read_verilog -sv <tệp…>`).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-16-01 | Đơn vị | tests/test_hdl.py::test_nguon_hdl_bo_testbench_khi_tong_hop | thư mục có `blinky.v`, `tb.v`, `sim/x.v` → `_nguon_hdl(d, bo_tb=True)` chỉ có `blinky.v` |
| TC-M3-16-02 | Ca âm | tests/test_hdl.py::test_nguon_hdl_mac_dinh_y_nhu_cu | `bo_tb` mặc định → vẫn có cả `tb.v` |
| TC-M3-16-03 | Tích hợp (`CO_YOSYS`) | tests/test_hdl.py::test_tong_hop_bo_qua_tb_co_initial_delay | `_du_an(tmp_path, **{"tb.v": TB_PASS})` → `tong_hop(..., dinh="blinky").dat`; `lenh` không chứa `tb.v` |
| TC-M3-16-04 | Tích hợp (`CO_VL`) | tests/test_hdl.py::test_lint_latch_thi_khong_dat | RTL `always_comb if (en) q = d;` → lint không đạt, `LATCH` trong `canh_bao_theo_ma`; với `chap_nhan=["LATCH"]` thì đạt |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py tests/test_hdl_cay.py`

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-17 -->
<a id="m3-17"></a>
### [M3-17] Định thời: đích theo từng đồng hồ và báo cáo đường găng — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #97

**Mục tiêu:** `hdl.pnr` so Fmax của từng đồng hồ với đích riêng của nó, và khi không đạt thì trả top-3 đường găng (nguồn, đích, trễ) để tác tử sửa đúng chỗ.
**Loại:** Sửa lỗi thuần
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/build/hdl.py`, `src/eide/tools/hdl.py`, `tests/test_hdl.py`

**Hiện trạng (đã kiểm lại trong mã):**
- hdl.py:190 `_MAU_FMAX` và :209 `fmax = min(...)` trên mọi dòng "Max frequency for clock"; `dat_di_day` so `fmax < tan_so_mhz` (một đích chung, mặc định 27).
- ĐÃ KIỂM LẠI, phát hiện cũ chưa chắc chắn: JSON cho rằng nextpnr in Fmax cả trước và sau routing nên `min` có thể lấy số trước routing. Soát transcript `du-lieu/riscv-tn20k-b/.eide/llm/*.jsonl` thì chỉ thấy đuôi log (`nguyen_van[-4000:]`), mỗi lần chạy một giá trị cho mỗi đồng hồ, nên CHƯA xác nhận được. Vì vậy hạ xuống P2 và thêm bước 0 xác minh.
- Không có mã nào đọc "Critical path report".

**Thay đổi cần làm:**
1. Bước 0: trên máy có `nextpnr-himbaechel` (`CO_PNR`), chạy `blinky` và lưu toàn bộ log vào `tests/du_lieu/pnr_blinky.log` (mẫu cố định cho test). Nếu log có nhiều khối Fmax cho cùng một đồng hồ thì chỉ lấy khối sau dòng `Info: Routing` cuối cùng; nếu không có thì bỏ ý này và ghi lại vào DEV-LOG.
2. `dat_di_day(..., tan_so_mhz: float | dict[str, float] = 27.0)`: nhận dict `{ten_clock: MHz}`; đồng hồ không có trong dict dùng giá trị `"*"` hoặc mặc định. Kết luận không đạt khi BẤT KỲ đồng hồ nào có `fmax < dich` của nó.
3. `doc_duong_gang(log) -> list[dict]`: tách khối "Critical path report for clock '<c>'"; mỗi khối lấy dòng đầu/cuối (nguồn/đích) và tổng trễ "ns". Trả top-3 vào `kq.tai_nguyen["duong_gang"]`; `_loi_chang` của `hdl.pnr` thêm 3 dòng này vào gợi ý.

**Không được làm (giới hạn phạm vi):**
- Không đổi khoá `fmax_mhz` (vẫn là min) và `dong_ho`.
- Truyền `float` thì hành vi như cũ.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-17-01 | Đơn vị | tests/test_hdl.py::test_dich_theo_dong_ho_rieng | log 2 đồng hồ (`clk_fast` 120 MHz, `clk_slow` 40 MHz), đích `{"clk_fast":100,"clk_slow":1}` → đạt (hiện tại: min 40 so với đích chung) |
| TC-M3-17-02 | Ca âm | tests/test_hdl.py::test_mot_dong_ho_truot_dich_rieng_thi_khong_dat | `clk_fast` 90 MHz với đích 100 → không đạt, câu nêu `clk_fast` |
| TC-M3-17-03 | Đơn vị | tests/test_hdl.py::test_doc_duong_gang_top3 | log mẫu có 1 khối Critical path → `duong_gang[0]` có `nguon`, `dich`, `tre_ns` |
| TC-M3-17-04 | Hồi quy | tests/test_hdl.py::test_doc_fmax_lay_dong_ho_CHAM_nhat (đã có) | vẫn 19,50 |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py`
- `test_fmax_thap_hon_tan_so_chay_thi_KHONG_dat`, `test_khong_doc_duoc_fmax_thi_canh_bao_chu_khong_im` giữ nguyên.

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG (kèm kết quả bước 0).

**Hoàn tác:** revert commit.

<!-- TASK M3-19 -->
<a id="m3-19"></a>
### [M3-19] Bản đồ địa chỉ dùng chung RTL ↔ linker ↔ firmware — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #98

**Mục tiêu:** Bản đồ địa chỉ SoC là một hiện vật có STALE; vùng nhớ trong linker và hằng `*_BASE` của firmware được đối chiếu với nó bằng mã.
**Loại:** Công cụ mới (`core=False`) + hạ tầng phụ thuộc
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/knowledge/ban_do_dia_chi.py` (mới), `src/eide/deps.py`, `src/eide/tools/hdl.py`, `tests/test_ban_do_dia_chi.py` (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- docs/md/DE-XUAT-CAU-TRUC-FPGA.md Phần 2: bản đồ địa chỉ "chỉ nằm trong chú thích của soc_top.v và EIDE.md".
- knowledge/vendor.py:142 `doc_ld` trả `CauHinh.khoa["config:<vung>.origin"/".size"]`.
- deps.py `HA_NGUON` không có loại `address_map`.

**Thay đổi cần làm:**
1. `ban_do_dia_chi.tu_khai(ds: list[{ten, base, size, quyen}])` lưu thành hiện vật `address_map:soc` (type `address_map`, ghi bằng `ctx.store.apply`).
2. `tu_rtl(chu)`: nhận các mẫu `localparam ADDR_X = 32'h1000_0000` và `addr[31:28] == 4'h1`, trả ứng viên kèm tệp:dòng, tầng BẠC. Người xác nhận thì lên NGƯỜI.
3. `doi_chieu(ban_do, ld: CauHinh, firmware: list[Path])` bằng mã: vùng `ram`/`bram` trong ld phải nằm trong một mục của bản đồ (origin và size); `#define \w+_BASE 0x...` trong `.c`/`.h` phải trùng `base` của một mục; lệch thì `{muc, tep, dong, mong_doi, thuc_te}`.
4. Thêm `"address_map": ("code", "build", "config")` vào `HA_NGUON` (deps.py).
5. Công cụ `hdl.addrmap_check(ld, firmware_glob)` (R1, `core=False`).

**Không được làm (giới hạn phạm vi):**
- Không coi ứng viên trích từ RTL là sự thật khi chưa có người xác nhận.
- Không sửa tệp linker.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-19-01 | Đơn vị | tests/test_ban_do_dia_chi.py::test_ld_ram_vuot_bram_bi_bao | bản đồ BRAM 0x0/32 KB; ld `RAM (rwx): ORIGIN=0x0, LENGTH=64K` → lệch `size` |
| TC-M3-19-02 | Đơn vị | tests/test_ban_do_dia_chi.py::test_define_base_lech_bi_bao | `#define UART_BASE 0x10000010` với UART 0x10000000 → lệch, có dòng |
| TC-M3-19-03 | Ca âm | tests/test_ban_do_dia_chi.py::test_khop_thi_khong_bao | mọi thứ khớp → danh sách rỗng |
| TC-M3-19-04 | Đơn vị | tests/test_ban_do_dia_chi.py::test_doi_ban_do_danh_stale_code | `deps.ha_nguon_cua` với hiện vật address_map → có hiện vật `code`/`build` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ban_do_dia_chi.py tests/test_stale*.py tests/test_vendor*.py`

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-21 -->
<a id="m3-21"></a>
### [M3-21] HDL: trả lỗi gốc kèm mã nguồn, và bài học theo chữ ký lỗi (Reflexion) — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #99

**Mục tiêu:** Khi một chặng HDL trượt, tác tử thấy lỗi ĐẦU TIÊN kèm 5 dòng mã quanh nó; và ở lần trượt sau với cùng chữ ký lỗi, cách sửa đã thành công lần trước được gắn kèm (tối đa 2).
**Loại:** Sửa lỗi thuần (phần lỗi gốc) + Đổi hành vi (phần bài học, cờ `EIDE_FEATURE_BAI_HOC_HDL`, mặc định TẮT)
**Phụ thuộc:** Gộp với M1-14 / M5-14 (kho bài học Reflexion chung). Nhiệm vụ này chỉ thêm (a) phần chọn lỗi gốc và (b) hàm chuẩn hoá chữ ký lỗi HDL dùng kho của M1-14. M1-14 chưa xong thì chỉ làm (a).
**Tệp chạm tới:** `src/eide/tools/hdl.py`, `src/eide/build/hdl.py`, `src/eide/config.py`, `tests/test_hdl.py`

**Hiện trạng (đã kiểm lại trong mã):**
- tools/hdl.py:72 `_loi_chang`: `hint_for_agent = goi_y + nguyen_van[-1500:]`, `details.loi = kq.loi[:10]`. Lỗi gốc của yosys thường nằm ở đầu log và có thể bị cắt mất.
- `doc_thong_diep` (build/hdl.py:103) đã cho `{tep, dong, cot, thong_diep, ma}`.
- Không có bộ nhớ bài học cho `hdl.*`.

**Thay đổi cần làm:**
1. (a) `_loi_chang`: nếu `kq.loi` không rỗng thì lấy `kq.loi[0]`, đọc 5 dòng quanh `dong` trong `goc/tep` (an toàn: trong dự án, có try), và đặt lên ĐẦU `hint_for_agent` dưới dạng `"Lỗi gốc: tep:dong: thông điệp\n<mã>"`. Giữ đuôi log nhưng rút còn 1000 ký tự.
2. (b) `chu_ky_loi(kq) -> str`: `f"{kq.chang}|{ma}|{thong_diep đã thay số, tên tín hiệu và đường dẫn bằng <x>}"`.
3. (b) Khi cờ bật: chặng trượt thì tra kho bài học (API M1-14) theo chữ ký và gắn `details["bai_hoc"]` (≤ 2). Khi cùng chặng chuyển từ trượt sang đạt trong cùng lượt thì ghi bài học `{chu_ky, cach_sua: tóm tắt diff changeset giữa hai lần}`. Có hết hạn (dùng cơ chế của M1-14).

**Không được làm (giới hạn phạm vi):**
- Không đổi mã lỗi E4030 hay cấu trúc `details` hiện có (chỉ thêm khoá).
- Không đọc tệp ngoài gốc dự án.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-21-01 | Đơn vị | tests/test_hdl.py::test_loi_chang_dat_loi_goc_va_ma_nguon_len_dau | `KetQuaHdl(loi=[{tep:"rtl/blinky.v", dong:5,...}], nguyen_van="x"*5000)` trên `_du_an` → `hint_for_agent` bắt đầu bằng "Lỗi gốc: rtl/blinky.v:5" và chứa dòng 5 của BLINKY |
| TC-M3-21-02 | Ca biên | tests/test_hdl.py::test_loi_chang_tep_ngoai_du_an_khong_doc | `tep="/etc/passwd"` → không có nội dung tệp trong hint |
| TC-M3-21-03 | Đơn vị | tests/test_hdl.py::test_chu_ky_loi_bo_so_va_ten | hai thông điệp chỉ khác số dòng và tên tín hiệu → cùng chữ ký |
| TC-M3-21-04 | Cờ TẮT | tests/test_hdl.py::test_bai_hoc_tat_thi_khong_gan | cờ tắt → `"bai_hoc" not in details` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_hdl.py tests/test_mem_*.py`

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert phần (a); tắt cờ cho phần (b).

<!-- TASK M4-15 -->
<a id="m4-15"></a>
### [M4-15] Đo đại lượng thời gian thực trên bo và đối chiếu với mô phỏng (`target.measure`) — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #100

**Mục tiêu:** EIDE đo được f_cpu/f_tick thật qua DWT->CYCCNT và so với số đo mô phỏng theo cùng mã assert.
**Loại:** Công cụ mới
**Phụ thuộc:** M4-14 (dùng chung hiện vật/khuôn), không bắt buộc
**Tệp chạm tới:** src/eide/build/mach_that.py, src/eide/tools/mach_that.py, tests/test_target_measure.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- build/mach_that.py:1007 `soi_chip(dia_chi, so_tu)` đọc thanh ghi qua openocd (`mdw`); 1038 có hằng CFSR/HFSR; không có DWT.
- DANH-GIA §3.2: "nhịp 1000 Hz" suy từ LOAD của SysTick, thật là 91 Hz; §4: chạy HSI 16 MHz chậm 11,25 lần.

**Thay đổi cần làm:**
1. `do_nhip(bien_tick: int | None, delta_s=1.0)`: lệnh openocd bật `DEMCR.TRCENA` (0xE000EDFC bit 24) và `DWT_CTRL.CYCCNTENA` (0xE0001000 bit 0), đọc `DWT_CYCCNT` (0xE0001004) và biến tick hai lần cách nhau `delta_s`, rồi tính `f_cpu`, `f_tick`. Xử lý tràn 32-bit.
2. Công cụ `target.measure(bien=[...], ma_tieu_chi="")` (core=False, R2): trả `{"do":{"F_CPU":…, "F_TICK":…}}`. Có tiêu chí thì `xet_ket_qua`; có MA_SIM cùng mã assert thì thêm cột `lech_pct`. Ghi `sim_result:doi-chieu-bo`.
3. Chip không phải Cortex-M (theo hộ chiếu) thì E4026 "chưa hỗ trợ".

**Không được làm (giới hạn phạm vi):**
- Không giữ chip dừng quá `delta_s + 1` s; luôn `resume`.
- Không đổi soi_chip.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-15-01 | Đơn vị | tests/test_target_measure.py::test_tinh_f_cpu_tu_hai_lan_doc | cyc 0 → 180_000_000 trong 1 s → F_CPU 180e6 |
| TC-M4-15-02 | Ca biên | …::test_tran_32bit_cyccnt | cyc 0xFFFFFF00 → 0x00000100 → hiệu 0x200 |
| TC-M4-15-03 | Tích hợp (monkeypatch openocd) | …::test_measure_cham_theo_tieu_chi | F_CPU đo 16e6, assert >=170e6 → khong_dat |
| TC-M4-15-04 | Ca âm | …::test_chip_avr_thi_E4026 | hộ chiếu avr8 → not ok, E4026 |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mach_that.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit.

<!-- TASK M4-22 -->
<a id="m4-22"></a>
### [M4-22] Bộ ca gài lỗi để đo verifier và năng lực tự kiểm — P2 · L

**Giai đoạn:** GĐ4 · thứ tự #101

**Mục tiêu:** Có một bộ dự án mini gài lỗi đã biết, chấm bằng code, để đo recall của verifier và tỉ lệ tác tử tự tìm ra lỗi, làm thước đo cho M4-06/07/08/10/13.
**Loại:** Hạ tầng test/đo
**Phụ thuộc:** M4-21 (dùng chung khuôn chạy/băng); M4-09 nên xong trước
**Tệp chạm tới:** tests/kich_ban/gai_loi/*.yaml (mới), tests/du-lieu-chung/gai_loi/<ca>/ (mới), tools/chay_gai_loi.py (mới), tests/test_gai_loi_khuon.py (mới)

**Hiện trạng (đã kiểm lại trong mã):**
- tests/test_tu_phat_hien_sai.py, tests/test_subagent.py kiểm LOGIC hook/verifier bằng `_So`/`_Ctx` giả và ScriptedGateway (lời đáp viết sẵn), nên không đo năng lực thật.
- DANH-GIA-NGUOI-VS-AGENT-2-VIEC.md: năng lực chỉ được đánh giá qua phiên dài chấm tay (14,5 giờ, 1307 lời gọi).

**Thay đổi cần làm:**
1. 15–20 ca, mỗi ca một thư mục dự án dựng sẵn và một YAML: `loi_gai` (tệp:dòng hoặc mã hiện vật), `che_do` (verifier | e2e), `bao_cao_dat_gia` (cho chế độ verifier), `viec` (cho e2e). Ví dụ: ISR không nối vector; test tự định nghĩa lại hàm; assert tự so chính nó; sim_result cũ hơn mã (stale); log UART rác lượt trước; hằng PID sai dấu.
2. tools/chay_gai_loi.py: chế độ verifier gọi `SA.chay(ma="verifier", viec=viec_cho_verifier(bc))`; chế độ e2e chạy Agent với việc "kiểm và báo cáo". Chấm: lời/báo cáo nêu đúng tệp:dòng (±2 dòng) hoặc mã hiện vật. Ghi pass-rate, token, số lời gọi theo khuôn M4-21.
3. tests/test_gai_loi_khuon.py: kiểm mọi YAML hợp lệ, mọi `loi_gai` trỏ tới tệp tồn tại, và lỗi gài THẬT SỰ có (ví dụ grep thấy `Default_Handler` ở ô SysTick).

**Không được làm (giới hạn phạm vi):**
- Không đưa nội dung ca vào prompt/skill/memory của sản phẩm (tránh học thuộc).
- Không chạy bộ này trong CI với LLM thật.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M4-22-01 | Đơn vị khuôn | tests/test_gai_loi_khuon.py::test_moi_ca_co_loi_gai_tro_toi_tep_that | duyệt tests/kich_ban/gai_loi/*.yaml → mọi tệp tồn tại, có ≥15 ca |
| TC-M4-22-02 | Đơn vị máy chấm | …::test_cham_dung_tep_dong_xap_xi | loi_gai "firmware/pid.c:42"; lời "pid.c dòng 43" → đạt; "pid.c dòng 60" → không đạt |
| TC-M4-22-03 | Ca âm | …::test_noi_chung_chung_khong_dat | lời "có thể có lỗi ở firmware" → không đạt |
| TC-M4-22-04 | Tích hợp (ScriptedGateway) | …::test_che_do_verifier_chay_duoc_offline | verifier kịch bản trả khong_dat nêu đúng ref → đạt |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_subagent.py tests/test_tu_phat_hien_sai.py`

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Chỉ số: có mốc recall verifier và tỉ lệ e2e trên phiên bản hiện tại, ghi vào ket-qua-do/.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** revert commit (chỉ thêm dữ liệu và tool).

<!-- TASK M5-12 -->
<a id="m5-12"></a>
### [M5-12] Nạp PDF scan/lai bằng OCR từng trang (`doc.load ocr=true`) — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #102

**Mục tiêu:** PDF scan (hoặc PDF lai có trang ảnh) nạp được qua OCR với nhãn tin cậy từng trang và trần tầng, thay vì ngõ cụt; trang rỗng không còn âm thầm.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_OCR_NAP`, mặc định TẮT; thêm tham số vào lược đồ `doc.load` chỉ khi cờ bật).
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/knowledge/ocr.py`, `src/eide/knowledge/docs.py`, `src/eide/knowledge/ingest.py`, `src/eide/tools/knowledge.py`, `tests/test_ocr_nap.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `ingest.py:560-578` `_doc_pdf`: kiểm chữ ở `r.pages[:5]`; không có chữ thì `doc_duoc=False`, đề xuất "Chấp nhận OCR…" nhưng không có đường nào làm.
- `ocr.py:146` `ocr_anh(path, ma_ngon_ngu)` trả `KetQuaOcr(chu, do_tin_cay, …)`; `ocr.py:228` `rut_hinh_tu_pdf` rút ảnh nhúng bằng pypdf (`trang.images`), không cần render.
- `docs.py:160-187` `nap_tai_lieu`: trang không chữ cho `Trang.chu==""`, không cảnh báo.

**Thay đổi cần làm:**
1. `ocr.py::ocr_trang_pdf(path, so_trang, *, ma_ngon_ngu) -> KetQuaOcr`: lấy ảnh lớn nhất của trang qua `pypdf` (`trang.images`), ghi tạm, gọi `ocr_anh`.
2. `docs.nap_tai_lieu(..., ocr: bool=False, ma_ngon_ngu="eng")`: với mỗi trang có `len(chu.strip()) < 20` thì: nếu `ocr` thì thay `chu` bằng kết quả OCR, `nhan=f"trang {n} (OCR, tin cậy {x:.2f})"`; nếu không thì ghi vào `TaiLieu.trang_rong` (trường mới, list[int]).
3. `fact_tu_ung_vien`: Fact từ trang OCR thì tier `min(tier, "BAC")`; nếu `do_tin_cay < NGUONG_TIN_CAY` thì `"NGUOI"`. Lưu `do_tin_cay` trong `source.ocr`.
4. `doc.load`: khi cờ bật thêm tham số `ocr` (boolean). PDF scan mà `ocr=true` thì đi tiếp thay vì `E1001`. Kiểm gói ngôn ngữ bằng `kiem_goi`, thiếu thì `E1014` như doc.figures.
   Luôn trả `trang_rong=[...]` (kể cả khi cờ tắt: đây là thông tin, không đổi hành vi nạp).

**Không được làm (giới hạn phạm vi):**
- Không bao giờ cho Fact OCR lên VANG tự động. Không OCR khi `ocr` không được truyền.
- Không thêm phụ thuộc render PDF.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-12-01 | Đơn vị | tests/test_ocr_nap.py::test_trang_rong_duoc_bao | `lam_pdf` 3 trang, trang 2 rỗng (`[]`) → `nap_tai_lieu(...).trang_rong == [2]` |
| TC-M5-12-02 | Tích hợp (registry) | tests/test_ocr_nap.py::test_scan_ocr_true_nap_duoc | Cờ bật; `lam_pdf(tmp/"scan.pdf", [[]])`; monkeypatch `ocr_trang_pdf` trả `KetQuaOcr(chu="VDD (max) 5.5 V", do_tin_cay=0.93)` và `kiem_goi` trả `(True,"")` → `doc.load(ocr=True)` `ok`; `fact.extract` ra `vdd.max` tầng BAC |
| TC-M5-12-03 | Đơn vị | tests/test_ocr_nap.py::test_tin_cay_thap_ha_NGUOI | `do_tin_cay=0.5` → Fact tầng `NGUOI` |
| TC-M5-12-04 | Cờ TẮT | tests/test_ocr_nap.py::test_co_tat_van_tu_choi_scan | Không bật cờ → `doc.load` PDF scan vẫn `E1001`; lược đồ `doc.load` không có `ocr` |
| TC-M5-12-05 | Ca âm | tests/test_ocr_nap.py::test_thieu_goi_ngon_ngu | `kiem_goi` trả `(False,"thiếu vie")` → `E1014`, không ghi Fact |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_ing_e.py tests/test_tri_thuc.py tests/test_ingest_v3.py`
- `test_pdf_scan_noi_that_ve_do_tin_cay` giữ nguyên (phan_loai vẫn `doc_duoc=False`).

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ `EIDE_FEATURE_OCR_NAP`; revert commit.

<!-- TASK M5-15 -->
<a id="m5-15"></a>
### [M5-15] EIDE.md: dấu ngày, điều kiện huỷ cho Giả định, gợi ý trùng/mâu thuẫn khi ghi — P2 · M

**Giai đoạn:** GĐ4 · thứ tự #103

**Mục tiêu:** mỗi dòng tác tử ghi vào EIDE.md mang ngày ghi; Giả định có `huy_khi`; `memory.note` báo khi dòng mới nghi trùng hoặc mâu thuẫn với dòng cùng mục.
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_EIDE_MD_KIEM`, mặc định TẮT; phần dấu ngày là định dạng dòng nên cũng đặt sau cờ).
**Phụ thuộc:** Không. Nên làm sau M5-16 (cùng tệp `eide_md.py`).
**Tệp chạm tới:** `src/eide/store/eide_md.py`, `src/eide/tools/writing.py`, `src/eide/config.py`, `tests/test_eide_md_kiem.py` (mới).

**Hiện trạng (đã kiểm lại trong mã):**
- `eide_md.py:135-147` `append_line(section, line, boi)`: thêm hậu tố `[run-xx]`, không có ngày.
- `tools/writing.py:229-276` `memory_note`: ghi thẳng, chỉ kiểm quyền mục (`duoc_ghi`) và trần token. Không so với dòng cũ.
- `memory/summary.py:31` lược đồ C2 có `gia_dinh_dang_dung[{…, huy_khi}]`, EIDE.md thì không.

**Thay đổi cần làm:**
1. Khi cờ bật: `append_line(..., ngay: str | None)` ghi hậu tố `[run-xx · YYYY-MM-DD]`. Dòng cũ không có ngày vẫn đọc được.
2. `memory.note` thêm tham số tuỳ chọn `huy_khi` (chuỗi). Mục `Giả định` khi cờ bật mà thiếu `huy_khi` thì vẫn ghi nhưng kèm `note_vi` nhắc.
3. `EideMd.nghi_trung(section, line) -> list[str]`: các dòng cùng mục có hệ số Jaccard trên tập token (≥3 ký tự, bỏ dấu) ≥ 0.5, hoặc cùng chủ thể (cụm `HSE|HSI|PLL|chip|UART\d|I2C\d`…) mà khác giá trị số.
   `memory.note` trả `nghi_trung=[...]` kèm `note_vi` "nếu dòng mới thay dòng cũ thì gọi memory.forget dòng cũ". KHÔNG chặn ghi.
4. `memory.status` liệt kê Giả định có `huy_khi` và Giả định quá 30 ngày.

**Không được làm (giới hạn phạm vi):**
- Không tự xoá dòng cũ (P5). Không sửa lại các dòng cũ trên đĩa. Không đụng mục `Đừng` (chỉ người ghi).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-15-01 | Đơn vị | tests/test_eide_md_kiem.py::test_nghi_trung_khac_gia_tri | §Quyết định có "- Dùng HSE 8 MHz làm nguồn clock [run-1]" → `nghi_trung("Quyết định","Dùng HSE 25 MHz làm nguồn clock")` trả dòng cũ |
| TC-M5-15-02 | Tích hợp (registry) | tests/test_eide_md_kiem.py::test_memory_note_tra_nghi_trung | Cờ bật → `memory.note` dòng mâu thuẫn → `ok`, có `nghi_trung` không rỗng; tệp có CẢ hai dòng |
| TC-M5-15-03 | Đơn vị | tests/test_eide_md_kiem.py::test_dau_ngay | Cờ bật → dòng mới kết thúc bằng `· 2026-` + ngày (dùng monkeypatch ngày) + `]` |
| TC-M5-15-04 | Cờ TẮT | tests/test_eide_md_kiem.py::test_co_tat_y_nhu_cu | Cờ tắt → dòng kết thúc đúng `[run-1]`, kết quả không có `nghi_trung` |
| TC-M5-15-05 | Ca âm | tests/test_eide_md_kiem.py::test_dong_khac_chu_de_khong_keu_nham | "Dùng I2C1 cho cảm biến" so với "Bật watchdog 2 s" → `[]` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_b.py tests/test_mem_c.py tests/test_mem_d.py`
- Quy tắc `Đừng` chỉ người ghi (`E4003`) và đề xuất lược khi vượt trần giữ nguyên.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ `EIDE_FEATURE_EIDE_MD_KIEM`; revert commit.

<!-- TASK M5-20 -->
<a id="m5-20"></a>
### [M5-20] C1 stub theo lần "được nhắc" gần nhất; gộp trùng cho `doc.read`/`store.get`/`fact.query` — P2 · S

**Giai đoạn:** GĐ4 · thứ tự #104

**Mục tiêu:** C1 không thu gọn một kết quả vẫn đang được dùng lại, và gộp được các lần đọc lặp cùng tham số của công cụ tri thức (không chỉ `fs.read`).
**Loại:** Đổi hành vi (cờ `EIDE_FEATURE_C1_THEO_NHAC`, mặc định TẮT; đổi nội dung ngữ cảnh).
**Phụ thuộc:** Không.
**Tệp chạm tới:** `src/eide/memory/compact.py`, `src/eide/config.py`, `tests/test_mem_a.py`.

**Hiện trạng (đã kiểm lại trong mã):**
- `compact.py:113-118`: stub khi `luot_cuoi - m["_luot"] >= 8`; lý do ghi "chưa được nhắc lại" nhưng mã không theo dõi việc nhắc.
- `compact.py:60-68` `_khoa_doc`: chỉ `fs.read` (khoá `(path, bytes)`).
- ĐÃ KIỂM LẠI: message `role=="tool"` KHÔNG lưu `args` (`loop.py:915-917` chỉ có `tool_call_id`, `tool`, `result`, `envelope`). Args nằm trong message `role=="model"` trước đó (`tool_calls[i]["args"]`), nên phải tra theo `tool_call_id`.

**Thay đổi cần làm:**
1. `_ban_do_args(messages) -> dict[call_id, (tool, args)]` dựng từ các message `model`.
2. `_khoa_doc` mở rộng (khi cờ bật): `doc.read → ("doc.read", doc_id, tim, muc, tu, gioi_han)`, `store.get → ("store.get", id, version trong result)`, `fact.query → ("fact.query", subject, key, tier)`.
3. `_luot_nhac_cuoi`: một kết quả được coi là "được nhắc" ở lượt L nếu ở lượt L có lời gọi cùng khoá đọc, hoặc văn bản mô hình ở lượt L chứa `blob_ref` hay `doc_id`+trích dẫn của nó. Điều kiện stub thành `luot_cuoi - max(_luot, _luot_nhac_cuoi) >= LUOT_GIU_NGUYEN_VAN`.
4. Cờ tắt: hành vi y như cũ (đường mã cũ).

**Không được làm (giới hạn phạm vi):**
- Không đổi `LUOT_GIU_NGUYEN_VAN`, `GHIM_TU_DONG`, hay `c4`. Không đổi định dạng stub (`_da_thu_gon`, `blob.read`).

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M5-20-01 | Đơn vị | tests/test_mem_a.py::test_C1_ket_qua_duoc_nhac_khong_bi_stub | Cờ bật; 12 lượt; kết quả `doc.read` ở lượt 1, văn bản mô hình lượt 10 nhắc `blob_ref` của nó → sau `c1` kết quả đó không `_stub` |
| TC-M5-20-02 | Đơn vị | tests/test_mem_a.py::test_C1_dedup_doc_read_cung_args | Cờ bật; hai lần `doc.read` cùng `{"doc_id":"DS","tim":"VDD"}` (args trong message model) → `bc["dedup"]==1`, lần cũ là stub |
| TC-M5-20-03 | Ca âm | tests/test_mem_a.py::test_C1_doc_read_khac_args_khong_gop | `tim` khác nhau → `bc["dedup"]==0` |
| TC-M5-20-04 | Cờ TẮT | tests/test_mem_a.py::test_C1_co_tat_y_nhu_cu | Cờ tắt, cùng dữ liệu TC-01 → kết quả lượt 1 bị stub (như cũ) |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_mem_a.py tests/test_mem_b.py tests/test_mem_c.py`
- Mọi `test_MEM05_*`, `test_C1_chay_lai_nhieu_lan_khong_hong` giữ xanh.

**Tiêu chí xong:**
- [ ] Các TC mới xanh; đã "phá lại thì đỏ" từng TC.
- [ ] Toàn bộ `pytest -q` xanh, số ca xanh ≥ mốc trước khi sửa.
- [ ] Ghi một mục vào docs/md/EIDE-DEV-LOG.md.

**Hoàn tác:** tắt cờ `EIDE_FEATURE_C1_THEO_NHAC`; revert commit.

<!-- TASK M2-16 -->
<a id="m2-16"></a>
### [M2-16] Bộ vẽ hỗ trợ `stateDiagram-v2` và kiểm máy trạng thái — P3 · M

**Giai đoạn:** GĐ4 · thứ tự #105

**Mục tiêu:** sơ đồ máy trạng thái được vẽ thành PNG trong tài liệu xuất ra, và có hàm báo trạng thái không tới được hoặc trạng thái cụt.
**Loại:** Sửa lỗi thuần ở bộ vẽ/xuất bản. Sửa skill trinh-bay-bang-hinh.md là đổi lời dặn tác tử, nên phần đó sau cờ, hoặc chỉ sửa khi Swift cũng đã vẽ được.
**Phụ thuộc:** Không. Bên Swift (ui/EIDEApp `Views/SoDo.swift` + ui/EIDEApp/Tests) phải làm cùng đợt, vì test_so_do.py::test_hai_bo_doc_ra_cung_mot_thu đối chiếu hai bộ đọc.
**Tệp chạm tới:** src/eide/so_do.py, src/eide/skills/trinh-bay-bang-hinh.md, tests/test_so_do.py, ui/EIDEApp (Swift).

**Hiện trạng (đã kiểm lại trong mã):**
- so_do.py:102–108 `doc()`: chỉ nhận `sequenceDiagram` → `_tuan_tu`, và `graph|flowchart` → `_luong`; kiểu khác trả None.
- test_so_do.py:75 `test_kieu_chua_ve_duoc_tra_None_va_noi_dung_ten`: gantt và classDiagram trả None (phải giữ).
- `_luong` dựng `Luong(nut, canh, cum)`; `_ve_luong` và `xep_cho` dùng lại được cho trạng thái.

**Thay đổi cần làm:**
1. `_trang_thai(nguon) -> Luong | None` cho `stateDiagram`/`stateDiagram-v2`: nhận `[*] --> S`, `S1 --> S2 : nhãn`, `state "Tên dài" as S`. `[*]` vẽ hình `tron`.
2. `doc()` định tuyến kiểu mới tới `_trang_thai`.
3. `kiem_may_trang_thai(nguon, su_kien=None) -> dict`: `khong_toi_duoc` (BFS từ [*]); `cut` (không có cạnh ra và không phải trạng thái kết thúc); `thieu_chuyen` (khi truyền danh sách sự kiện).
4. Cập nhật skill: thêm `stateDiagram-v2` vào bảng "Muốn cho thấy".

**Không được làm (giới hạn phạm vi):**
- Không hỗ trợ composite state, fork hay join ở đợt này (gặp thì trả None như cũ).
- Không đổi bố cục của graph/flowchart hiện có.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M2-16-01 | Đơn vị | tests/test_so_do.py::test_doc_stateDiagram | `doc("stateDiagram-v2\n[*] --> INIT\nINIT --> RUN : ok\n")` không None, 3 nút, 2 cạnh (mã cũ: None) |
| TC-M2-16-02 | Đơn vị | …::test_ve_png_trang_thai | `ve_png(nguon, tmp_path/"s.png")` sinh tệp có kích thước > 0 |
| TC-M2-16-03 | Đơn vị | …::test_trang_thai_khong_toi_duoc | có `X --> RUN` nhưng không cạnh nào vào X → `khong_toi_duoc == ["X"]` |
| TC-M2-16-04 | Ca âm | …::test_may_trang_thai_day_du_khong_keu | máy 3 trạng thái kín → cả ba danh sách rỗng |
| TC-M2-16-05 | Hồi quy | …::test_kieu_chua_ve_duoc_tra_None_va_noi_dung_ten | ca cũ vẫn xanh (classDiagram vẫn None) |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_so_do.py tests/test_xuat_ban.py`
- Bộ Swift ui/EIDEApp/Tests xanh.

**Tiêu chí xong:**
- [ ] TC xanh, "phá lại thì đỏ".
- [ ] `pytest -q` xanh; Swift tests xanh.
- [ ] DEV-LOG.

**Hoàn tác:** revert commit.

<!-- TASK M3-22 -->
<a id="m3-22"></a>
### [M3-22] Khép vòng số đo mạch thật với ERC (dòng đo so với ngân sách) — P3 · S

**Giai đoạn:** GĐ4 · thứ tự #106

**Mục tiêu:** Số đo dòng hay áp do người nhập (Fact tầng NGƯỜI) tự được ERC so với dự đoán và với ngưỡng chập/cắm ngược.
**Loại:** Sửa lỗi thuần (luật ERC đọc Fact đã có)
**Phụ thuộc:** M3-07.
**Tệp chạm tới:** `src/eide/knowledge/erc.py`, `tests/test_erc.py`

**Hiện trạng (đã kiểm lại trong mã):**
- ĐÃ KIỂM LẠI, phát hiện cũ được chỉnh: JSON đề xuất công cụ mới `target.measure`. Thực tế đã có `fact.assert_human` (tools/design.py:307), ghi Fact tầng NGƯỜI với chủ thể tự do (vd `net:/board.3V3`) và bắt trích nguyên văn, nên đường nhập số đo bằng tay ĐÃ CÓ. Phần thiếu chỉ là ERC chưa đọc các Fact đó, nên hạ từ P2·L xuống P3·S và bỏ công cụ mới.
- compare.py:326 `cam_nguoc(dong_do, dong_binh_thuong)` có sẵn nhưng không luật ERC nào gọi.

**Thay đổi cần làm:**
1. Thêm `"i_do": ("i_do","i_measured","dong_do")` và `"v_do": ("v_do","v_measured","ap_do")` vào `KHOA`.
2. Luật `so_do_vs_du_doan(cay, tf, thuoc)`: với mỗi nhóm nguồn có Fact `i_do` (chủ thể `net:<path>` của một net thành viên), lấy tổng tiêu thụ từ `_hai_ve_dong`. Gọi `CP.cam_nguoc(i_do, tong)` (dựng một Fact giả cho `tong`, tier thấp nhất trong các Fact đã cộng). `v_do` lệch hơn 5 % so với `ap_danh_dinh` thì `canh_bao`.
3. Gọi trong `erc()`. Không có Fact đo thì không sinh gì.

**Không được làm (giới hạn phạm vi):**
- Không thêm công cụ mới; không đọc cổng nối tiếp.

**Test case — viết TRƯỚC khi sửa, phải ĐỎ trên mã hiện tại:**
| Mã TC | Loại | Tệp test | Cho trước → Khi → Thì |
|---|---|---|---|
| TC-M3-22-01 | Đơn vị | tests/test_erc.py::test_dong_do_gap_3_lan_du_doan_bao_ngat_nguon | đủ Fact i_max (tổng 12,085 mA) + `_fact(bo,"net:/board.3V3","i_do",0.05,unit="A",tier="NGUOI")` → `cam_nguoc` `khong_dat`, `vi` có "NGẮT NGUỒN" |
| TC-M3-22-02 | Ca âm | tests/test_erc.py::test_dong_do_binh_thuong_khong_bao | `i_do` 0,013 A → không có `khong_dat` |
| TC-M3-22-03 | Đơn vị | tests/test_erc.py::test_ap_do_lech_rail_canh_bao | `v_do` 2,9 V trên 3V3 → `canh_bao` |
| TC-M3-22-04 | Ca âm | tests/test_erc.py::test_khong_co_so_do_thi_im_lang | `bo` nguyên → không có luật `so_do_*` |

**Bảo vệ hồi quy (phải vẫn XANH):**
- `.venv/bin/python -m pytest -q tests/test_erc.py tests/test_mach_that.py`

**Tiêu chí xong:**
- [ ] TC xanh, phá lại thì đỏ.
- [ ] `pytest -q` xanh, ≥ mốc.
- [ ] Ghi DEV-LOG.

**Hoàn tác:** revert commit.


---

## 10. Phụ lục — điều chỉnh so với bảng Excel khi kiểm lại mã

Khi viết đặc tả, người rà soát từng mảng đã mở lại mã và chỉnh một số phát hiện. **Tệp này là bản chuẩn** khi khác với Excel.

| Mã | Điều chỉnh | Lý do |
|---|---|---|
| M1-02 | Phần dài của lược đồ nằm trong mô tả **tham số**, không ở `summary_vi` | Đo lại khai báo công cụ |
| M1-05 | `task.run_many` tách ra làm sau | Giữ nhiệm vụ nhỏ |
| M1-06 | Chỉ thi hành cờ `doc_duoc_viec`; phần 2 verifier/Debate thuộc M4-07/M4-08 | Tránh trùng |
| M1-08 | Chỉ dùng `thinking_level` (SDK google-genai 2.25.0 nói `thinking_budget` không còn hỗ trợ từ Gemini 3.5) | Đọc SDK trong .venv |
| M1-09 | Thành thí nghiệm A/B sau cờ, không đổi mặc định temperature | Khuyến nghị cho dòng Gemini 3 chưa xác minh riêng cho 3.8-flash |
| M1-22 | Giữ `PolicyEngine.decide` ném ValueError (test hiện có đòi vậy); bắt ở vòng lặp | `test_dieu_kien_sai_cu_phap_thi_no_chu_khong_cho_qua` |
| M2-01 | Thêm: `store.apply` xoá `deps` cũ khi upsert; `ghi_tep` cũng thiếu tham số `deps` | Đọc lại db.py, history.py |
| M2-05 | Báo trong kết quả, không chặn (theo chuẩn `ckm.module_set`) | Nhất quán |
| M2-08 | Thêm lỗi: `[^;]*` tham lam nuốt các hàm sau khi thân hàm không có `;` | Chạy regex trên `timer.c` của robot |
| M2-19 | Cảnh báo + hạ tầng tin cậy, không chặn | Chặn sẽ làm đỏ ca CX06 |
| M3-01 | Dùng `canonical.ap_danh_dinh` sẵn có thay vì khoá `v_rail` mới | `ckm.net_set` đã ghi |
| M3-07 | Lỗi nặng hơn: Fact trích ghi chủ thể `chip:X@ver`, ERC chỉ tra `leaf:U1`/`U1`/`X` → Fact datasheet không bao giờ tới ERC | Đọc `TraFact`/`chu_the_la` |
| M3-10 | Bỏ ý "`_GHI_CHAC_CHAN` thiếu `ckm.*`" | `kiem_chung._la_ghi` đã tính mọi `writes_artefact` |
| M3-17 | Hạ P1 → P2; thêm bước 0 lưu log nextpnr đầy đủ trước khi sửa | Chưa xác nhận được log có Fmax hai lần |
| M3-22 | Hạ P2·L → P3·S; dùng `fact.assert_human` sẵn có, chỉ thêm luật ERC | Không cần công cụ đo mới |
| M4-08, M4-12, M4-20 | "Model khác" → cùng model, prompt riêng, temperature 0; nối `ModelConfig.subagent` (đang không ai đọc) | `ALLOWED_MODELS` chỉ một model |
| M4-09 | Phải sửa cả test cũ `test_da_goi_verifier_roi_thi_thoi` đang khoá hành vi sai | Đọc test |
| M4-14 | `target.flash` đã mở cổng trước khi nạp (DEV-331); chỉ làm máy chấm assert log + chạy lặp N lần | Đọc `bat_log_quanh_viec` |
| M5-06 | Phần khoá theo mục (abs_max/operating) chuyển sang M5-04 bước 4 | Cần ngữ cảnh mục từ trích bảng PDF |
| M5-07 | `trich` tuỳ chọn; chỉ bắt buộc với giá trị ≤ 2 ký tự | Không vỡ lời gọi cũ |
| M5-17 | Bỏ phần đưa kế hoạch vào `<resume>` (đã có ở `<pending>`); lỗi chính giữ nguyên | `tools/ke_hoach.py:575-580` |
| Mã lỗi | E5011 → E5012 (M2-04), E5013 (M3-08), E5014 (M5-10); E6010 → E6012 (M2-06); E4024 → E4034 (M2-17) | Trùng giữa các mảng; giữ E5011 cho M1-17, E6010 cho M1-10, E4024 cho M4-01 |

**Ghi chú môi trường:** trong lúc rà soát, một lần chạy `python3` (3.10 của máy ảo) đã sinh vài tệp `src/eide/__pycache__/*.cpython-310.pyc`.
Đó chỉ là bộ đệm, đã nằm trong `.gitignore`, không ảnh hưởng mã; có thể xoá bằng `find src -name "*.cpython-310.pyc" -delete`.

## 11. Định nghĩa "xong" cho cả kế hoạch

- Mọi nhiệm vụ GĐ1 ☑; tổng số ca Python tăng, không ca cũ nào đỏ; Swift 40+ ca xanh; `kiem_tai_lieu` 0 lệch.
- Bộ eval (M4-20/M4-21/M5-21) chạy được, có lịch sử theo commit.
- Mỗi cờ đã bật mặc định đều có bản ghi qua cổng 4.3 trong DEV-LOG.
- README mục "Kiểm thử" cập nhật số ca và các bộ đo mới.
