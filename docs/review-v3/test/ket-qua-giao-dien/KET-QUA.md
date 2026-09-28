# Quét toàn bộ giao diện — 11 bề mặt, mọi nhãn, mọi nút

**124/124 ô đạt.** Ảnh do chính app tự vẽ, nằm ở `anh/`.

Bộ quét hỏi ba câu cho từng bề mặt: *có nhãn nào rỗng không · có khối nào giao diện không biết vẽ không · có nút nào bấm mà không làm gì không*. Ô trống được coi là ĐẠT chỉ khi nó nói đủ ba câu — **chưa có gì · vì sao · cần gì để có** — vì một ô trống câm là một ô người dùng không biết phải làm gì tiếp.

## Khung chung

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Đủ 11 tab, đúng thứ tự tài liệu | ['requirements', 'documents', 'knowledge', 'design', 'tools', 'code', 'simulation', 'hardware', 'journal', 'history', 'project'] |
| ✅ | Đọc được khung cửa sổ để đo tràn | {'cao': 1018, 'rong': 1700, 'so': 24585, 'x': 28, 'y': 33} |
| ✅ | Ba nút Hẹp / Vừa / Rộng của Console cho ba bề rộng KHÁC nhau | {'Hẹp': 320, 'Vừa': 460, 'Rộng': 640} |
| ✅ | Bấm nút bề rộng thì trạng thái đổi theo | Vừa |
## Bề mặt requirements — Yêu cầu & Giải pháp

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: requirements |
| ✅ | Bề mặt có khối để hiện | 3 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 3 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt documents — Tài liệu & Nguồn

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: documents |
| ✅ | Bề mặt có khối để hiện | 1 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 1 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt knowledge — Tri thức mạch

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: knowledge |
| ✅ | Bề mặt có khối để hiện | 2 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 2 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt design — Thiết kế

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: design |
| ✅ | Bề mặt có khối để hiện | 2 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 2 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt tools — Công cụ

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: tools |
| ✅ | Bề mặt có khối để hiện | 1 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 1 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt code — Mã nguồn

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: code |
| ✅ | Bề mặt có khối để hiện | 3 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 1 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt simulation — Mô phỏng

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: simulation |
| ✅ | Bề mặt có khối để hiện | 3 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 0 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt hardware — Mạch thật

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: hardware |
| ✅ | Bề mặt có khối để hiện | 1 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 1 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt journal — Nhật ký

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: journal |
| ✅ | Bề mặt có khối để hiện | 2 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 0 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt history — Lịch sử

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: history |
| ✅ | Bề mặt có khối để hiện | 3 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 1 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Bề mặt project — Dự án & Bộ nhớ

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Bấm tab thì đúng bề mặt ấy hiện ra | đang xem: project |
| ✅ | Bề mặt có khối để hiện | 6 khối |
| ✅ | Mọi khối đều có TIÊU ĐỀ | thiếu: — |
| ✅ | Giao diện biết vẽ mọi kiểu khối lõi gửi sang | không vẽ được: — · kiểu lạ toàn app: [] |
| ✅ | Ô trống nói đủ: chưa có gì · vì sao · cần gì để có | 2 khối trống, câm: — |
| ✅ | Khối nào có nút "Vì sao?" thì lớp giải thích đủ SÁU trường (N8) | thiếu trường: — |
| ✅ | Không nhãn nào lộ giá trị thô (None / dict / traceback) | — |
| ✅ | Không khối nào đè lên khối khác | — |
| ✅ | Không khối nào rộng hơn khung bên phải (không đẩy nút ra ngoài màn) | khung phải ≈ 1240 px (cửa sổ 1700 − console 460) · tràn: — |
| ✅ | Không khối nào cao gấp hơn 4 lần cửa sổ (khối không ai đọc hết) | khung cao 1018 · — |
## Tổng các bề mặt

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Tổng số khối đã soi qua 11 bề mặt | 27 khối |
## Bảng Giới thiệu

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Mở được bảng Giới thiệu từ menu và chụp lại được | /Users/congvt/Documents/EIDE_v3/docs/review-v3/test/ket-qua-giao-dien/anh/gioi-thieu.png |
## Cửa sổ nhỏ nhất

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Ở khổ nhỏ nhất (1100×720) vẫn không khối nào tràn ngang | khung {'cao': 752, 'rong': 1100, 'so': 24585, 'x': 28, 'y': 331} · tràn: — |
## Thanh trạng thái

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Thanh trạng thái có dữ liệu | {'chang': 'C6 Mạch thật', 'chip': 'chưa ghim', 'du_an': 'stm32f469-freertos', 'fact': {}, 'mo_hinh': 'gemini-3.8-flash', 'ngu_canh': {'cua_so': 1000000, 'kha_dung': 800000, 'khoi': [{'ten': 'constitution', 'token': 3598, 'tran': 3600, 'vuot': False}, {'ten': 'eide_md', 'token': 1041, 'tran': 3000, 'vuot': False}, {'ten': 'inventory', 'token': 202, 'tran': 800, 'vuot': False}, {'ten': 'facts', 'token': 0, 'tran': 2000, 'vuot': False}, {'ten': 'human_edits', 'token': 0, 'tran': 1000, 'vuot': False}, {'ten': 'pending', 'token': 0, 'tran': 300, 'vuot': False}, {'ten': 'skills_hint', 'token': 0, 'tran': 300, 'vuot': False}, {'ten': 'transcript', 'token': 0, 'tran': 0, 'vuot': False}, {'ten': 'dự trữ (bất khả xâm phạm)', 'token': 200000, 'tran': 200000, 'vuot': False}], 'muc': 'C0', 'tong': 204841, 'ty_le': 0.205}, 'stale': 0} |
| ✅ | Không ô nào trên thanh trạng thái bỏ trống câm | ô rỗng: — · đủ: ['chang', 'chip', 'du_an', 'fact', 'mo_hinh', 'ngu_canh', 'stale'] |
| ✅ | Thanh trạng thái không lộ giá trị thô | — |
## Widget sửa tay (§E2 — người sửa được gì)

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Có ít nhất một khối cho người sửa trực tiếp bằng widget | simulation/criteria:sim-01: Ngưỡng |
## Thông báo và hội thoại

| Kết quả | Điều được kiểm | Bằng chứng |
|---|---|---|
| ✅ | Không thẻ nào còn nút bấm được sau khi đã trả lời / hết hạn | 0 thẻ còn nút · 0 chờ |
| ✅ | Thông báo không lộ giá trị thô | 1 thông báo · — |
| ✅ | Lời tác tử đã được DỰNG thành chữ, không còn dấu Markdown thô trên màn | còn: — |
