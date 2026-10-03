# Các quyết định thiết kế kỹ thuật (Engineering Decisions)

## ADR-01: Dải giá trị phần tử cho phép nhân ma trận N = 32 chống tràn số

### 1. Bối cảnh & Ràng buộc
- Kích thước ma trận: $N = 32$.
- Kiểu dữ liệu phần tử đầu vào: Số nguyên có dấu kiểu `I32` (hoặc số nguyên $b$-bit).
- Đích tích luỹ (accumulator): Kiểu `int32_t`, có dải biểu diễn:
  $$\text{Dải } int32\_t = [-2^{31}, 2^{31}-1] = [-2.147.483.648, 2.147.483.647]$$
- Mỗi phần tử ma trận kết quả $C_{ij}$ được tính bằng tích vô hướng của hàng $i$ ma trận $A$ và cột $j$ ma trận $B$:
  $$C_{ij} = \sum_{k=0}^{31} A_{ik} \times B_{kj}$$
  Bao gồm đúng $N = 32$ phép nhân và cộng dồn.

### 2. Tính toán dải giá trị an toàn
Trường hợp xấu nhất (worst-case scenario) xảy ra khi cả 32 tích thành phần đều mang giá trị dương lớn nhất có thể:
$$C_{\max} = N \times (\max |x|)^2 = 32 \times (\max |x|)^2$$

Để đảm bảo không bao giờ xảy ra hiện tượng tràn số (arithmetic overflow) trên biến 32-bit có dấu:
$$32 \times (\max |x|)^2 \le 2^{31} - 1$$
$$(\max |x|)^2 \le \left\lfloor \frac{2.147.483.647}{32} \right\rfloor = 67.108.863$$
$$\max |x| \le \lfloor \sqrt{67.108.863} \rfloor = \lfloor 8.191,9999 \rfloor = 8.191$$

- Kiểm tra lại:
  - Nếu tất cả các phần tử đều là $-8.191$ hoặc $8.191$:
    $$C_{\max} = 32 \times (8.191)^2 = 32 \times 67.092.481 = 2.146.959.392$$
    Số này nhỏ hơn $2.147.483.647$ một biên an toàn là $524.255$.
  - Nếu lấy giá trị $8.192$:
    $$32 \times (-8.192) \times (-8.192) = 32 \times 67.108.864 = 2.147.483.648 > 2^{31}-1 \quad (\text{Bị tràn!})$$

### 3. Quyết định lựa chọn
- **Dải giá trị an toàn tối đa cho mỗi phần tử:** $[-8.191, 8.191]$.
- **Đề xuất sử dụng trong thực tế:**
  - Để tương thích tự nhiên với các kiểu dữ liệu lũy thừa 2 trong phần cứng và phần mềm, chọn dải **13-bit có dấu** (Signed 13-bit: $[-4.096, 4.095]$) hoặc **12-bit có dấu** ($[-2.048, 2.047]$), hoặc dải **8-bit có dấu (`int8_t`)** ($[-128, 127]$).
  - Chọn dải chính thức cho bộ sinh test: $[-4.096, 4.095]$ (nằm trọn vẹn bên trong ngưỡng an toàn 8.191, có biên an toàn dồi dào, thuận tiện cho việc dịch bit).

---

## ADR-02: Giải thuật tổng kiểm (Checksum) cho truyền nhận ma trận

### 1. Lựa chọn giải thuật
Chọn giải thuật **Fletcher-32** (tính trên các từ 16-bit) hoặc **Sum32 Modulo (Tổng cộng dồn tràn tự nhiên 32-bit kèm xoay bit)**.
Để đơn giản tối đa, dễ hiểu nhất cho sinh viên đọc mã mà vẫn phát hiện tốt lỗi đảo vị trí / lỗi bit, ta chuẩn hóa giải thuật **Fletcher-32**:
- Gồm hai bộ tích lũy 16-bit $C_0$ và $C_1$ thực hiện phép cộng dồn với modulo $65.535$ ($0xFFFF$).
- $C_0$ tính tổng các phần tử, $C_1$ tính tổng tích lũy của $C_0$ (nhờ đó phân biệt được thứ tự dữ liệu, hoán vị vị trí sẽ đổi checksum).

### 2. Cài đặt đối ứng (C và Python)
- **Mã C:**
```c
#include <stdint.h>
#include <stddef.h>

uint32_t checksum_fletcher32(const uint16_t *data, size_t len) {
    uint32_t c0 = 0, c1 = 0;
    for (size_t i = 0; i < len; ++i) {
        c0 = (c0 + data[i]) % 65535;
        c1 = (c1 + c0) % 65535;
    }
    return (c1 << 16) | c0;
}
```

- **Mã Python:**
```python
def checksum_fletcher32(data: list[int]) -> int:
    c0 = 0
    c1 = 0
    for val in data:
        c0 = (c0 + (val & 0xFFFF)) % 65535
        c1 = (c1 + c0) % 65535
    return (c1 << 16) | c0
```

### 3. Ví dụ kiểm chứng
Với mảng đầu vào gồm 4 từ 16-bit: `[1, 2, 3, 4]`:
- Bước 1: $val = 1 \implies c_0 = 1, c_1 = 1$
- Bước 2: $val = 2 \implies c_0 = 3, c_1 = 4$
- Bước 3: $val = 3 \implies c_0 = 6, c_1 = 10$
- Bước 4: $val = 4 \implies c_0 = 10, c_1 = 20$
- Kết quả: $(20 \ll 16) \mid 10 = 0x0014000A = 1.310.730$.
Cả hai mã C và Python đều cho ra cùng kết quả chính xác $1.310.730$ ($0x0014000A$).
