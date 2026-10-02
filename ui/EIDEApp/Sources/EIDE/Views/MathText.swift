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

    /// Ký hiệu một-đổi-một — **sinh ra từ `_TEX_KY_HIEU` của `src/eide/xuat_ban.py`**.
    ///
    /// Hai bên phải GIỐNG NHAU từng mục. Trước ngày 02/10/2026 chúng lệch ba kiểu, và cả ba
    /// đều âm thầm:
    ///
    /// - Swift thiếu **28** ký hiệu Python có (`\Sigma`, `\Theta`, `\chi`, `\emptyset`,
    ///   `\implies`…). Cùng một câu tác tử viết ra thì đẹp trong tệp Word mà vẫn là lệnh TeX
    ///   thô trên màn hình — đúng điều anh Công nêu ngày 01/10/2026.
    /// - Python thiếu **13** lệnh bố cục Swift có (`\left`, `\right`, `\quad`…), nên
    ///   `\left( a \right)` in ra tệp Word còn nguyên hai lệnh ấy.
    /// - Hai mục **SAI**: Swift đổi `\sum` thành `Σ` và `\prod` thành `Π` — chữ Hy Lạp, không
    ///   phải ký hiệu phép toán `∑` `∏`. Trông gần giống, khác nghĩa, và khác hẳn bề rộng.
    ///   Tệ hơn: `\Sigma` và `\sum` ra cùng một chữ, nên hai thứ khác nhau hiện ra như một.
    ///
    /// Ca kiểm `test_hai_bang_ky_hieu_phai_giong_nhau` đọc thẳng tệp này rồi so với bảng
    /// Python. Sửa một bên mà quên bên kia thì đỏ ở đó. Xem DEV-325.
    private static let kyHieu: [String: String] = [
        "\\ ": " ", "\\!": "", "\\,": " ", "\\:": " ",
        "\\;": " ", "\\alpha": "α", "\\angle": "∠", "\\approx": "≈",
        "\\ast": "∗", "\\beta": "β", "\\cap": "∩", "\\cdot": "·",
        "\\cdots": "⋯", "\\chi": "χ", "\\circ": "°", "\\cup": "∪",
        "\\degree": "°", "\\delta": "δ", "\\Delta": "Δ", "\\displaystyle": "",
        "\\div": "÷", "\\dots": "…", "\\downarrow": "↓", "\\emptyset": "∅",
        "\\epsilon": "ε", "\\equiv": "≡", "\\eta": "η", "\\exists": "∃",
        "\\forall": "∀", "\\gamma": "γ", "\\Gamma": "Γ", "\\ge": "≥",
        "\\geq": "≥", "\\gg": "≫", "\\iff": "⇔", "\\implies": "⇒",
        "\\in": "∈", "\\infty": "∞", "\\int": "∫", "\\iota": "ι",
        "\\kappa": "κ", "\\lambda": "λ", "\\Lambda": "Λ", "\\land": "∧",
        "\\ldots": "…", "\\le": "≤", "\\left": "", "\\Leftarrow": "⇐",
        "\\leftarrow": "←", "\\Leftrightarrow": "⇔", "\\leftrightarrow": "↔", "\\leq": "≤",
        "\\limits": "", "\\ll": "≪", "\\lor": "∨", "\\mapsto": "↦",
        "\\micro": "µ", "\\mp": "∓", "\\mu": "µ", "\\nabla": "∇",
        "\\ne": "≠", "\\neg": "¬", "\\neq": "≠", "\\notin": "∉",
        "\\nu": "ν", "\\ohm": "Ω", "\\omega": "ω", "\\Omega": "Ω",
        "\\parallel": "∥", "\\partial": "∂", "\\percent": "%", "\\perp": "⊥",
        "\\phi": "φ", "\\Phi": "Φ", "\\pi": "π", "\\Pi": "Π",
        "\\pm": "±", "\\prime": "′", "\\prod": "∏", "\\propto": "∝",
        "\\psi": "ψ", "\\Psi": "Ψ", "\\qquad": " ", "\\quad": " ",
        "\\rho": "ρ", "\\right": "", "\\Rightarrow": "⇒", "\\rightarrow": "→",
        "\\sigma": "σ", "\\Sigma": "Σ", "\\sim": "∼", "\\sqrt": "√",
        "\\star": "⋆", "\\subset": "⊂", "\\subseteq": "⊆", "\\sum": "∑",
        "\\tau": "τ", "\\theta": "θ", "\\Theta": "Θ", "\\times": "×",
        "\\to": "→", "\\uparrow": "↑", "\\upsilon": "υ", "\\varepsilon": "ε",
        "\\varnothing": "∅", "\\varphi": "φ", "\\xi": "ξ", "\\Xi": "Ξ",
        "\\zeta": "ζ",
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
    /// Đổi cả bảng ký hiệu trong MỘT lượt duyệt, có chốt biên.
    ///
    /// Bản trước thay từng mục bằng `replacingOccurrences`, xếp dài trước ngắn. Xếp dài trước
    /// đủ để `\\leftarrow` không bị `\\left` ăn mất đầu — nhưng **chỉ với những lệnh có trong
    /// bảng**. Một lệnh ta chưa biết mà bắt đầu bằng tên một lệnh đã biết thì vẫn bị cắt:
    ///
    ///     \alphabet  →  αbet        \leftroot  →  root
    ///
    /// Hai hậu quả, và cái thứ hai tệ hơn. Thứ nhất, chữ hiện ra sai. Thứ hai, phép kiểm cuối
    /// hàm — *"còn dấu gạch chéo nghĩa là còn lệnh chưa hiểu"* — **mất tác dụng**: gạch chéo
    /// đã bị ăn cùng với phần đầu lệnh, nên hàm báo đã đổi trọn vẹn và khối công thức hiện ra
    /// một kết quả sai thay vì hiện nguyên bản kèm dòng *"giao diện chưa đổi hết ký hiệu"*.
    /// Đúng cái mà chú thích của hàm hứa là sẽ không xảy ra.
    ///
    /// Chốt biên phải chia **hai nhóm**, giống `_MOT_LUOT` phía Python:
    /// - lệnh viết bằng **chữ** cần `(?![A-Za-z])` phía sau — `\\leftb` không phải `\\left`;
    /// - lệnh dạng **dấu câu** (`\\,` `\\;` `\\:` `\\!` `\\ `) thì tên kết thúc ngay ở dấu ấy,
    ///   nên một chữ đứng sau là cách dùng thường: `a\\,b`. Áp chốt cho nhóm này thì chúng
    ///   không đổi được.
    private static func doiKyHieu(_ s: String) -> String {
        guard let re = motLuot else { return s }
        let ns = s as NSString
        var ra = ""
        var vt = 0
        re.enumerateMatches(in: s, range: NSRange(location: 0, length: ns.length)) { m, _, _ in
            guard let m else { return }
            ra += ns.substring(with: NSRange(location: vt, length: m.range.location - vt))
            ra += kyHieu[ns.substring(with: m.range)] ?? ns.substring(with: m.range)
            vt = m.range.location + m.range.length
        }
        ra += ns.substring(from: vt)
        return ra
    }

    private static let motLuot: NSRegularExpression? = {
        func nhanh(_ ds: [String]) -> String {
            ds.sorted { $0.count > $1.count }
              .map { NSRegularExpression.escapedPattern(for: $0) }
              .joined(separator: "|")
        }
        let chu = kyHieu.keys.filter { $0.dropFirst().first?.isLetter == true }
        let dau = kyHieu.keys.filter { $0.dropFirst().first?.isLetter != true }
        return try? NSRegularExpression(
            pattern: "(?:(?:\(nhanh(Array(chu))))(?![A-Za-z])|(?:\(nhanh(Array(dau)))))")
    }()

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

        s = doiKyHieu(s)

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
    /// Ruột giữa hai dấu `$` là CÔNG THỨC hay là TIỀN?
    ///
    /// Đây là chỗ khó nhất của việc đọc công thức giữa dòng: **dấu đô-la cũng là tiền**. Một
    /// câu "giá $5 và $10 nữa" mà đọc thành công thức thì ăn mất cả đoạn chữ ở giữa.
    ///
    /// Bốn điều kiện dưới đây **sao đúng từ `_dong_cong_thuc` của `src/eide/xuat_ban.py`**, và
    /// phải giữ giống. Bản Swift trước đây dùng một luật khác hẳn — *"có lệnh `\\`, hoặc có chữ
    /// cái, hoặc có `^`/`_`"* — và nó sai theo CẢ HAI chiều:
    ///
    /// - `$[-128, 127]$` **không có** thứ nào trong ba thứ ấy, nên nó rơi xuống chữ thường
    ///   **mang theo cả hai dấu đô-la**. Anh Công nhìn thấy đúng câu ấy trên màn hình ngày
    ///   02/10/2026: *"Với kiểu I8: giá trị trong $[-128, 127]$"*. Trong tệp Word thì đúng, vì
    ///   phía Python dùng luật khác — lại thêm một chỗ hai bên lệch nhau.
    /// - `giá $5 và $10 nữa` có ruột `"5 và "`, **có chữ cái**, nên luật cũ nhận là công thức
    ///   và ăn mất đoạn chữ. Luật của Python loại nó đúng, bằng điều kiện khoảng trắng ở cuối.
    ///
    /// Và một điều về bộ kiểm của tôi: ca `test_cong_thuc_trong_dong_doi_thanh_ky_hieu` thử
    /// `$\\alpha \\le 0.05$` — một công thức **có lệnh TeX**. Nó xanh với cả luật cũ. Phải có
    /// một ca không chứa lệnh nào mới thấy, và tôi không nghĩ ra ca ấy.
    static func laCongThucChuKhongPhaiTien(_ ruot: String) -> Bool {
        // không rỗng, không bắt đầu/kết thúc bằng khoảng trắng — "giá $5 và $10" có ruột
        // `"5 và "` kết thúc bằng khoảng trắng, nên bị loại đúng như mong muốn
        guard !ruot.isEmpty,
              ruot == ruot.trimmingCharacters(in: .whitespacesAndNewlines),
              !ruot.contains("$"),
              ruot.count <= 300 else { return false }
        // Ruột chỉ có chữ số, dấu chấm phẩy và khoảng trắng thì đó là TIỀN: `$5$`, `$1.000$`.
        // Một công thức thật luôn có thêm thứ gì đó — biến, phép toán, hoặc một lệnh TeX.
        let chiSo = CharacterSet(charactersIn: "0123456789.,")
            .union(.whitespacesAndNewlines)
        if ruot.unicodeScalars.allSatisfy({ chiSo.contains($0) }) { return false }
        return true
    }

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
                if let end = s[sau...].firstIndex(of: "$"), end > sau,
                   laCongThucChuKhongPhaiTien(String(s[sau..<end])) {
                    xa()
                    ra.append(.init(text: sangUnicode(String(s[sau..<end])).text,
                                    laCongThuc: true))
                    i = s.index(after: end)
                    continue
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
