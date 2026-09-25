# Prompt dán vào Claude Code (chạy trong repo EIDE)

Gói thiết kế v3.0 nằm ở `docs/review-v3/`. Hãy:

1. Đọc `docs/review-v3/README_REVIEW_BRIEF.md` (chú ý khung CẬP NHẬT ở đầu), rồi đọc **toàn bộ** `docs/review-v3/docs/md/EIDE-MDD-40_v3.0_Thiet_ke_Tong_the.md` — đây là tài liệu thiết kế duy nhất có hiệu lực. Đọc `docs/review-v3/test/Usecase_Test_23-09-2026.md` để biết 76 ca đo và nguyên nhân từng ca. Chỉ mở các tài liệu cũ (AGD-32, AAD-33, UIP-34) khi MDD-40 dẫn chiếu.
2. Rà soát mã hiện tại (`rpc.py`, `src/eide/**`, `caps.json`, `intent.schema.json`, `chains.yaml`, cầu giao diện) so với MDD-40. Viết gap report `docs/md/EIDE-GAP-41_Ra_soat_ma_v3.md`: mỗi mục thiết kế (đánh số theo Phần/mục của MDD-40: A3 N1–N9, B1–B6, C1–C3, D1–D2, E1–E8, F, G) → CÓ / MỘT PHẦN / KHÔNG / KHÁC, tệp:dòng, ca đo (TC/CX), hành động, bước G1–G7. Xác minh bằng cách đọc mã, không tin dự đoán trong brief.
3. Dừng lại, tóm tắt gap report (số mục theo trạng thái, 10 sai lệch quan trọng nhất, ước lượng công cho G1–G3). Chờ tôi gật.
4. Khi tôi gật: làm theo G1 → G2 → G3 (lõi vòng lặp → changeset & lịch sử → hiện vật hai dạng + đồng bộ khi người sửa), mỗi bước một nhánh, unit test cho hook/policy/changeset/merge, chạy hồi quy 16 ca đang đạt + ca mục tiêu ×5, cập nhật Excel. Mọi chỗ mã phải khác MDD-40 → ghi `docs/md/EIDE-DEV-LOG.md` dạng [DEV-2xx]. Không làm UC15, TC071; G4–G7 chỉ khi được gật.
5. Kết thúc mỗi G: báo cáo thống kê, DEV-2xx mới, đề xuất bước tiếp.

Ngôn ngữ: mã tiếng Anh; thông điệp cho người dùng, lớp giải thích (explain) và tài liệu tiếng Việt.
