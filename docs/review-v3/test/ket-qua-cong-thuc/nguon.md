# Thử công thức LaTeX — sáu ngữ cảnh

Tệp này là **nguồn**. Bốn tệp cạnh nó dựng từ chính nó bằng `doc.render`.
Mở từng tệp ra, không chỗ nào được còn cú pháp TeX thô.

## 1. Công thức nguyên một đoạn

$$f_{VCO} = f_{in} \times \frac{PLLN}{PLLM}$$

## 2. Công thức GIỮA DÒNG

Tần số ra là $f_{out} = \frac{f_{VCO}}{PLLP}$ với $PLLP \in \{2,4,6,8\}$, nên
$f_{out} \leq 180$ MHz. Sai lệch pha $\Delta\phi \approx \pm 2^{\circ}$.

## 3. Trong gạch đầu dòng

- Chu kỳ SysTick: $T = \frac{1}{1000}$ s
- Ngưỡng dẫn: $V_{th} \approx 0.7$ V
- Sai số $\pm 2\%$, hằng số thời gian $\tau = R \cdot C$
- Điều kiện ổn định: $\omega_{c} \ll \omega_{s}$

## 4. Trong bảng

| Tham số | Công thức | Giá trị |
|---|---|---|
| Tần số VCO | $f_{in} \times \frac{N}{M}$ | 360 MHz |
| Dòng tải | $I = \frac{V}{R}$ | 200 mA |
| Trở kháng | $Z = \sqrt{R^2 + X^2}$ | 50 Ω |

## 5. Trong trích dẫn

> Điện áp rơi $V_{drop} = I \times R_{DS(on)}$ phải nhỏ hơn 100 mV, nếu không
> thì hiệu suất tụt dưới $\eta = 0.9$.

## 6. Khối math rào ba dấu backtick

```math
\tau = R \cdot C, \quad f_{c} = \frac{1}{2\pi\tau}
```

## 7. Dấu đô-la là TIỀN — phải giữ nguyên

Ba mức chi phí: $82 triệu · $111 triệu · $142 triệu, tức khoảng $4,450 USD.
Biến môi trường $HOME và $PATH cũng không được đụng tới.
