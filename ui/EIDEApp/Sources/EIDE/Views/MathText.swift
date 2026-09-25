import Foundation

/// Công thức toán trong lời tác tử.
///
/// Bối cảnh: mô hình hay viết `$\ge$ 5 MB/s`, `$> 40\text{ Mbps}$`, `$I = \frac{U}{R}$`.
/// Để nguyên thì người đọc thấy rác; dựng cả một bộ sắp chữ TeX thì quá tay cho thứ
/// 95 % là ký hiệu đơn lẻ và vài phân số.
///
/// Đường giữa: **đổi sang Unicode**. Tiếng Việt kỹ thuật vốn viết ≥, ×, µF, Ω, °C —
/// đó mới là dạng người trong ngành đọc quen, và nó sao chép dán được sang email hay
/// Word mà không vỡ. Phần nào không đổi được (tích phân, ma trận) thì giữ nguyên và
/// hiện trong khối công thức riêng, không giả vờ đã sắp chữ xong.
enum MathText {

    /// Ký hiệu một-đổi-một. Danh sách chọn theo thứ hay gặp trong kỹ thuật nhúng.
    private static let kyHieu: [String: String] = [
        // so sánh
        "\\ge": "≥", "\\geq": "≥", "\\le": "≤", "\\leq": "≤", "\\ne": "≠", "\\neq": "≠",
        "\\approx": "≈", "\\sim": "∼", "\\propto": "∝", "\\equiv": "≡",
        "\\ll": "≪", "\\gg": "≫",
        // phép toán
        "\\times": "×", "\\cdot": "·", "\\div": "÷", "\\pm": "±", "\\mp": "∓",
        "\\ast": "∗", "\\star": "⋆",
        // mũi tên
        "\\to": "→", "\\rightarrow": "→", "\\leftarrow": "←", "\\Rightarrow": "⇒",
        "\\Leftarrow": "⇐", "\\leftrightarrow": "↔", "\\uparrow": "↑", "\\downarrow": "↓",
        // chữ Hy Lạp hay dùng trong điện tử
        "\\alpha": "α", "\\beta": "β", "\\gamma": "γ", "\\delta": "δ", "\\Delta": "Δ",
        "\\epsilon": "ε", "\\varepsilon": "ε", "\\eta": "η", "\\theta": "θ",
        "\\lambda": "λ", "\\mu": "µ", "\\pi": "π", "\\rho": "ρ", "\\sigma": "σ",
        "\\tau": "τ", "\\phi": "φ", "\\omega": "ω", "\\Omega": "Ω",
        // tập hợp & logic
        "\\in": "∈", "\\notin": "∉", "\\subset": "⊂", "\\cup": "∪", "\\cap": "∩",
        "\\forall": "∀", "\\exists": "∃", "\\neg": "¬", "\\land": "∧", "\\lor": "∨",
        // khác
        "\\infty": "∞", "\\partial": "∂", "\\nabla": "∇", "\\sum": "Σ", "\\prod": "Π",
        "\\int": "∫", "\\sqrt": "√", "\\degree": "°", "\\circ": "°", "\\percent": "%",
        "\\ohm": "Ω", "\\micro": "µ", "\\angle": "∠", "\\perp": "⊥", "\\parallel": "∥",
        // khoảng trắng của TeX
        "\\,": " ", "\\;": " ", "\\:": " ", "\\!": "", "\\quad": "  ", "\\qquad": "    ",
        "\\ ": " ", "\\%": "%", "\\&": "&", "\\#": "#", "\\_": "_",
        "\\left": "", "\\right": "", "\\displaystyle": "", "\\limits": "",
    ]

    private static let mu: [Character: Character] = [
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
        "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "+": "⁺", "-": "⁻",
        "(": "⁽", ")": "⁾", "n": "ⁿ", "i": "ⁱ",
    ]

    private static let chiSo: [Character: Character] = [
        "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
        "6": "₆", "7": "₇", "8": "₈", "9": "₉", "+": "₊", "-": "₋",
        "(": "₍", ")": "₎", "a": "ₐ", "e": "ₑ", "o": "ₒ", "x": "ₓ",
        "h": "ₕ", "k": "ₖ", "l": "ₗ", "m": "ₘ", "n": "ₙ", "p": "ₚ",
        "s": "ₛ", "t": "ₜ", "i": "ᵢ", "r": "ᵣ", "u": "ᵤ", "v": "ᵥ",
    ]

    /// Đổi một đoạn LaTeX sang Unicode. Trả về `nil` nếu còn sót lệnh không hiểu —
    /// gọi tới sẽ hiện nguyên bản trong khối công thức thay vì trình một kết quả sai.
    static func sangUnicode(_ tex: String) -> (text: String, tron: Bool) {
        var s = tex

        // \text{...} và \mathrm{...}: chỉ là chữ thường.
        for lenh in ["\\text", "\\mathrm", "\\mathit", "\\mathbf", "\\operatorname"] {
            s = thayNgoacNhon(s, lenh: lenh) { $0 }
        }
        // \frac{a}{b} → a/b  (đóng ngoặc khi tử/mẫu có phép cộng trừ)
        s = thayFrac(s)
        // \sqrt{x} → √(x)
        s = thayNgoacNhon(s, lenh: "\\sqrt") { "√(\($0))" }

        for (k, v) in kyHieu.sorted(by: { $0.key.count > $1.key.count }) {
            s = s.replacingOccurrences(of: k, with: v)
        }

        s = thayChiSoMu(s, dau: "^", bang: mu)
        s = thayChiSoMu(s, dau: "_", bang: chiSo)

        s = s.replacingOccurrences(of: "{", with: "")
             .replacingOccurrences(of: "}", with: "")
        s = s.replacingOccurrences(of: "  ", with: " ")
             .trimmingCharacters(in: .whitespaces)

        // Còn dấu gạch chéo ngược = còn lệnh ta chưa hiểu.
        return (s, !s.contains("\\"))
    }

    // MARK: - Tách công thức khỏi văn xuôi

    struct Manh {
        let text: String
        let laCongThuc: Bool
    }

    /// Tách `$...$` và `\(...\)` khỏi phần chữ. Dùng cho một dòng văn xuôi.
    static func tach(_ s: String) -> [Manh] {
        var ra: [Manh] = []
        var dem = ""
        var i = s.startIndex

        func xa() {
            if !dem.isEmpty { ra.append(.init(text: dem, laCongThuc: false)); dem = "" }
        }

        while i < s.endIndex {
            let c = s[i]
            // \(...\)
            if c == "\\", s.index(after: i) < s.endIndex, s[s.index(after: i)] == "(" {
                if let end = s.range(of: "\\)", range: s.index(i, offsetBy: 2)..<s.endIndex) {
                    xa()
                    let tex = String(s[s.index(i, offsetBy: 2)..<end.lowerBound])
                    ra.append(.init(text: sangUnicode(tex).text, laCongThuc: true))
                    i = end.upperBound
                    continue
                }
            }
            // $...$  (một đô la; hai đô la do bộ tách khối xử lý trước)
            if c == "$" {
                let sau = s.index(after: i)
                if let end = s[sau...].firstIndex(of: "$"), end > sau {
                    let tex = String(s[sau..<end])
                    // "$5" hay "giá $100" không phải công thức — công thức có lệnh
                    // hoặc ký hiệu toán, chứ không phải thuần chữ số.
                    if tex.contains("\\") || tex.rangeOfCharacter(from: .letters) != nil
                        || tex.contains("^") || tex.contains("_") {
                        xa()
                        ra.append(.init(text: sangUnicode(tex).text, laCongThuc: true))
                        i = s.index(after: end)
                        continue
                    }
                }
            }
            dem.append(c)
            i = s.index(after: i)
        }
        xa()
        return ra
    }

    /// Dòng này có phải một công thức đứng riêng không (`$$…$$`, `\[…\]`).
    static func khoiCongThuc(_ dong: String) -> String? {
        let t = dong.trimmingCharacters(in: .whitespaces)
        if t.hasPrefix("$$"), t.hasSuffix("$$"), t.count > 4 {
            return String(t.dropFirst(2).dropLast(2))
        }
        if t.hasPrefix("\\["), t.hasSuffix("\\]"), t.count > 4 {
            return String(t.dropFirst(2).dropLast(2))
        }
        return nil
    }

    // MARK: - Phụ

    private static func thayNgoacNhon(_ s: String, lenh: String,
                                      _ bien: (String) -> String) -> String {
        var ra = s
        while let r = ra.range(of: lenh + "{") {
            guard let dong = timDongNgoac(ra, moTai: ra.index(before: r.upperBound)) else { break }
            let trong = String(ra[ra.index(after: ra.index(before: r.upperBound))..<dong])
            ra.replaceSubrange(r.lowerBound...dong, with: bien(trong))
        }
        return ra
    }

    private static func thayFrac(_ s: String) -> String {
        var ra = s
        while let r = ra.range(of: "\\frac{") {
            let mo1 = ra.index(before: r.upperBound)
            guard let dong1 = timDongNgoac(ra, moTai: mo1) else { break }
            let tu = String(ra[ra.index(after: mo1)..<dong1])
            let sau = ra.index(after: dong1)
            guard sau < ra.endIndex, ra[sau] == "{",
                  let dong2 = timDongNgoac(ra, moTai: sau) else { break }
            let mau = String(ra[ra.index(after: sau)..<dong2])
            let cong = CharacterSet(charactersIn: "+-")
            let t = tu.rangeOfCharacter(from: cong) != nil ? "(\(tu))" : tu
            let m = mau.rangeOfCharacter(from: cong) != nil ? "(\(mau))" : mau
            ra.replaceSubrange(r.lowerBound...dong2, with: "\(t)/\(m)")
        }
        return ra
    }

    private static func timDongNgoac(_ s: String, moTai: String.Index) -> String.Index? {
        var sau = 0
        var i = moTai
        while i < s.endIndex {
            if s[i] == "{" { sau += 1 }
            if s[i] == "}" {
                sau -= 1
                if sau == 0 { return i }
            }
            i = s.index(after: i)
        }
        return nil
    }

    /// `x^2` → `x²`, `V_{max}` → `V_max` (chỉ hạ chỉ số khi mọi ký tự đổi được).
    private static func thayChiSoMu(_ s: String, dau: Character,
                                    bang: [Character: Character]) -> String {
        var ra = ""
        var i = s.startIndex
        while i < s.endIndex {
            guard s[i] == dau, s.index(after: i) < s.endIndex else {
                ra.append(s[i]); i = s.index(after: i); continue
            }
            var j = s.index(after: i)
            var noi = ""
            if s[j] == "{" {
                guard let dong = timDongNgoac(s, moTai: j) else {
                    ra.append(s[i]); i = s.index(after: i); continue
                }
                noi = String(s[s.index(after: j)..<dong])
                j = s.index(after: dong)
            } else {
                noi = String(s[j])
                j = s.index(after: j)
            }
            let doi = noi.map { bang[$0] }
            if !noi.isEmpty, doi.allSatisfy({ $0 != nil }) {
                ra.append(contentsOf: doi.compactMap { $0 })
            } else {
                // Không hạ được thì giữ dạng đọc được, đừng bịa.
                ra.append(dau)
                ra.append(contentsOf: noi)
            }
            i = j
        }
        return ra
    }
}
