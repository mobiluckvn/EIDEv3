# design-review-checklist
tu_khoa: rà soát, review, thiết kế, sơ đồ, netlist, erc, kiểm mạch
khi_nao: Rà soát một bản đồ mạch hoặc sơ đồ nguyên lý trước khi chốt.

## Đi theo thứ tự này, vì lỗi sau phụ thuộc lỗi trước

1. **Net hở.** Net chỉ có một đầu gần như luôn là lỗi vẽ. Đếm trước, giải thích sau.
2. **Chân có thật không.** Mọi chân dùng trong net phải có trong Fact pinout. Không có Fact
   thì không có chân — đừng suy từ tên chip.
3. **Bus có điện trở kéo lên không.** I2C là open-drain: không pull-up thì đường không bao
   giờ lên mức cao. Kiểm cả SDA và SCL.
4. **Ngân sách dòng.** Cộng dòng của mọi khối trên một net nguồn, so với `iout_max` của khối
   cấp. Thiếu Fact nào thì kết luận là *chưa đủ dữ kiện*, không phải *đạt*.
5. **Mức logic.** `VOH` của bên phát so với `VIH` của bên nhận, qua mọi cặp nối nhau.
6. **Địa chỉ trùng.** Hai thiết bị cùng địa chỉ trên một bus I2C.

## Cách viết phát hiện

Mỗi phát hiện nêu đủ ba phần: **sai ở đâu** (đường dẫn khối/net), **vì sao biết là sai**
(Fact nào, luật nào, trích dẫn nào), **hậu quả nếu để nguyên**. Thiếu phần ba thì người đọc
không có cách nào xếp thứ tự việc phải làm.

Không viết "có vẻ ổn". Một bản rà soát toàn màu xanh mà không nói đã soi những gì thì không
phân biệt được với một bản rà soát chưa chạy.
