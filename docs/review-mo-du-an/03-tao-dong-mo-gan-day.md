# Phiên làm việc: Vòng đời dự án: tạo mới · đóng · mở lại gần đây

Ghi tự động. Mỗi mục là một bước có thật trong một phiên EIDE chạy trên máy, với ảnh chụp cửa sổ EIDE làm sở cứ.

- Nguồn: `ba thư mục dựng tại chỗ`
- Thư mục dự án: `du-lieu/thu-vong-doi/mot`
- Bắt đầu: 28/09/2026 20:44:47

---

## Bước 1. Mở dự án thứ nhất

✅ Đang ở màn làm việc

```
man_hinh = lam-viec
```

✅ Dự án TỰ MỞ lúc khởi động cũng vào danh sách gần đây

```
gần đây: ['/Users/congvt/Documents/EIDE_v3/du-lieu/thu-vong-doi/mot']
```


## Bước 2. Tạo dự án MỚI — thứ trước đây không có nút nào gọi được

✅ Tạo được thư mục dự án mới từ giao diện

```
{'stt': 2, 'su_kien': 'du_an_moi', 'tep': '/Users/congvt/Documents/EIDE_v3/du-lieu/thu-vong-doi/hai', 'ts': '2026-09-28T13:44:51Z'} · thư mục có: True
```

✅ Lõi tự dựng `.eide/` và `EIDE.md` cho dự án mới — app KHÔNG tự dựng hộ

```
.eide: True · EIDE.md: True
```

✅ Tạo xong thì mở luôn, không phải mở lại bằng tay

```
man_hinh = lam-viec
```


## Bước 3. Từ chối tạo dự án LỒNG trong một dự án khác

✅ Chặn dự án lồng nhau, và nói rõ vì sao

```
Chỗ này nằm bên trong dự án /Users/congvt/Documents/EIDE_v3/du-lieu/thu-vong-doi/mot. Một dự án lồng trong dự án khác thì sổ cái và kho hiện vật của nó trở thành tệp thường trong hộp cát của tác tử ngoài. Chọn một chỗ bên ngoài.
```

✅ Từ chối khi chỗ ấy đã có sẵn thứ gì đó

```
Đã có thứ gì đó ở /Users/congvt/Documents/EIDE_v3/du-lieu/thu-vong-doi/hai. Chọn tên khác, hoặc dùng "Mở dự án" nếu đây đã là dự án cũ của anh.
```


## Bước 4. Đóng dự án — đường quay lại màn mở, trước đây không có

✅ Về được màn mở dự án

```
man_hinh = mo-du-an
```


## Bước 5. Mở lại dự án thứ nhất từ danh sách gần đây — không gõ lại đường dẫn

✅ Danh sách gần đây có cả hai dự án, mới nhất trước

```
['/Users/congvt/Documents/EIDE_v3/du-lieu/thu-vong-doi/hai', '/Users/congvt/Documents/EIDE_v3/du-lieu/thu-vong-doi/mot']
```

✅ Mở lại được, và nó nhảy lên đầu danh sách

```
man_hinh = lam-viec · gần đây: ['/Users/congvt/Documents/EIDE_v3/du-lieu/thu-vong-doi/mot', '/Users/congvt/Documents/EIDE_v3/du-lieu/thu-vong-doi/hai']
```


## Bước 6. Dự án trong danh sách bị xoá khỏi đĩa — hiện thế nào?

✅ Vẫn HIỆN trong danh sách (mờ, không bấm được) thay vì lặng lẽ biến mất

```
lặng lẽ lọc ra thì người thấy một mục mất đi mà không biết vì sao — mà lý do thường là họ vừa đổi tên hoặc chuyển thư mục, đúng lúc họ cần biết nhất
```

![man-mo-du-an](anh/06-man-mo-du-an.png)

**Kết thúc**

nhật ký: /Users/congvt/Documents/EIDE_v3/du-lieu/ket-qua/vong-doi/NHAT-KY.md

