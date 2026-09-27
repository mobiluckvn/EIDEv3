import SwiftUI

/// Hiển thị lời tác tử: markdown khối + công thức toán.
///
/// Vì sao không dùng thẳng `Text(AttributedString(markdown:))`: bộ dựng markdown của
/// Foundation chỉ xử lý **inline** (đậm, nghiêng, mã, liên kết). Tiêu đề, bảng, danh
/// sách, khối mã, đường kẻ — tức phần lớn cấu trúc trong câu trả lời kỹ thuật — sẽ hiện
/// ra dạng ký tự thô. Phiên chạy thật cho thấy tác tử dùng rất nhiều bảng so sánh và
/// tiêu đề; để nguyên thì người đọc phải tự giải mã `|---|---|`.
///
/// Bộ này cố ý **nhỏ**: nó xử lý đúng những khối mà một tác tử kỹ thuật thật sự sinh ra.
/// Gặp thứ không hiểu thì in nguyên văn — không bao giờ nuốt nội dung.

// MARK: - Mô hình khối

enum MdKhoi: Identifiable {
    case doan(String)
    case tieuDe(Int, String)
    case danhSach([(String, Bool, Int)])     // (nội dung, có đánh số, mức thụt)
    case bang([String], [[String]])
    case ma(String, String?)                 // nội dung, ngôn ngữ
    case trichDan([String])
    case duongKe
    case congThuc(String, Bool)              // đã đổi Unicode, có trọn vẹn không

    var id: String {
        switch self {
        case .doan(let s): return "p\(s.hashValue)"
        case .tieuDe(let n, let s): return "h\(n)\(s.hashValue)"
        case .danhSach(let x): return "l\(x.map(\.0).joined().hashValue)"
        case .bang(let h, let r): return "t\(h.joined().hashValue)\(r.count)"
        case .ma(let s, _): return "c\(s.hashValue)"
        case .trichDan(let x): return "q\(x.joined().hashValue)"
        case .duongKe: return "hr\(UUID().uuidString)"
        case .congThuc(let s, _): return "m\(s.hashValue)"
        }
    }
}

// MARK: - Bộ tách khối

enum Markdown {

    static func tach(_ raw: String) -> [MdKhoi] {
        var ra: [MdKhoi] = []
        let dong = raw.components(separatedBy: .newlines)
        var i = 0
        var doan: [String] = []
        var ds: [(String, Bool, Int)] = []
        var trich: [String] = []

        func xaDoan() {
            if !doan.isEmpty { ra.append(.doan(doan.joined(separator: "\n"))); doan = [] }
        }
        func xaDs() {
            if !ds.isEmpty { ra.append(.danhSach(ds)); ds = [] }
        }
        func xaTrich() {
            if !trich.isEmpty { ra.append(.trichDan(trich)); trich = [] }
        }
        func xaTatCa() { xaDoan(); xaDs(); xaTrich() }

        while i < dong.count {
            let d = dong[i]
            let t = d.trimmingCharacters(in: .whitespaces)

            // --- khối mã ```
            if t.hasPrefix("```") {
                xaTatCa()
                let ngonNgu = String(t.dropFirst(3)).trimmingCharacters(in: .whitespaces)
                var than: [String] = []
                i += 1
                while i < dong.count,
                      !dong[i].trimmingCharacters(in: .whitespaces).hasPrefix("```") {
                    than.append(dong[i])
                    i += 1
                }
                i += 1
                ra.append(.ma(than.joined(separator: "\n"), ngonNgu.isEmpty ? nil : ngonNgu))
                continue
            }

            // --- công thức đứng riêng
            if let tex = MathText.khoiCongThuc(t) {
                xaTatCa()
                let (s, tron) = MathText.sangUnicode(tex)
                ra.append(.congThuc(tron ? s : tex, tron))
                i += 1
                continue
            }

            // --- dòng trống
            if t.isEmpty {
                xaTatCa()
                i += 1
                continue
            }

            // --- đường kẻ
            if t.allSatisfy({ $0 == "-" || $0 == "*" || $0 == "_" }), t.count >= 3 {
                xaTatCa()
                ra.append(.duongKe)
                i += 1
                continue
            }

            // --- tiêu đề
            if t.hasPrefix("#") {
                let muc = t.prefix(while: { $0 == "#" }).count
                if muc <= 6, t.dropFirst(muc).hasPrefix(" ") {
                    xaTatCa()
                    ra.append(.tieuDe(muc, String(t.dropFirst(muc + 1))))
                    i += 1
                    continue
                }
            }

            // --- bảng: dòng này và dòng sau là hàng ngăn cách
            if t.hasPrefix("|"), i + 1 < dong.count, laHangNgan(dong[i + 1]) {
                xaTatCa()
                let cot = oCua(t)
                var hang: [[String]] = []
                i += 2
                while i < dong.count,
                      dong[i].trimmingCharacters(in: .whitespaces).hasPrefix("|") {
                    hang.append(oCua(dong[i]))
                    i += 1
                }
                ra.append(.bang(cot, hang))
                continue
            }

            // --- trích dẫn
            if t.hasPrefix(">") {
                xaDoan(); xaDs()
                trich.append(String(t.dropFirst()).trimmingCharacters(in: .whitespaces))
                i += 1
                continue
            }

            // --- danh sách
            if let muc = mucDanhSach(d) {
                xaDoan(); xaTrich()
                ds.append(muc)
                i += 1
                continue
            }

            xaDs(); xaTrich()
            doan.append(d)
            i += 1
        }
        xaTatCa()
        return ra
    }

    private static func laHangNgan(_ s: String) -> Bool {
        let t = s.trimmingCharacters(in: .whitespaces)
        guard t.hasPrefix("|") else { return false }
        return t.allSatisfy { "|-: ".contains($0) } && t.contains("-")
    }

    private static func oCua(_ s: String) -> [String] {
        var t = s.trimmingCharacters(in: .whitespaces)
        if t.hasPrefix("|") { t = String(t.dropFirst()) }
        if t.hasSuffix("|") { t = String(t.dropLast()) }
        return t.components(separatedBy: "|").map { $0.trimmingCharacters(in: .whitespaces) }
    }

    /// Số hiện ra cho từng mục của một danh sách đã làm phẳng.
    ///
    /// Đếm **riêng theo mức thụt**, và mỗi lần quay về mức nông hơn thì xoá bộ đếm của các mức
    /// sâu hơn. Bản trước lấy thẳng chỉ số trong mảng đã làm phẳng, nên một danh sách viết
    /// `1. 2. 3.` mà mục 2 có hai gạch đầu dòng con sẽ hiện ra **1, 2, 5** — tác tử viết đúng,
    /// giao diện đọc sai, và người đọc tưởng tác tử đếm nhầm.
    static func soThuTu(_ muc: [(String, Bool, Int)]) -> [Int] {
        var dem: [Int: Int] = [:]
        var ra: [Int] = []
        for m in muc {
            for k in dem.keys where k > m.2 { dem[k] = nil }
            if m.1 {
                dem[m.2, default: 0] += 1
                ra.append(dem[m.2] ?? 1)
            } else {
                ra.append(0)
            }
        }
        return ra
    }

    private static func mucDanhSach(_ d: String) -> (String, Bool, Int)? {
        let thut = d.prefix(while: { $0 == " " }).count / 2
        let t = d.trimmingCharacters(in: .whitespaces)
        for dau in ["- ", "* ", "• "] where t.hasPrefix(dau) {
            return (String(t.dropFirst(2)), false, thut)
        }
        // "1. ", "12) "
        let so = t.prefix(while: \.isNumber)
        if !so.isEmpty, so.count <= 3 {
            let sau = t.dropFirst(so.count)
            if sau.hasPrefix(". ") || sau.hasPrefix(") ") {
                return (String(sau.dropFirst(2)), true, thut)
            }
        }
        return nil
    }

    /// Inline (đậm/nghiêng/mã/liên kết) + công thức trong dòng.
    static func inline(_ s: String) -> AttributedString {
        var ra = AttributedString("")
        for m in MathText.tach(s) {
            if m.laCongThuc {
                var a = AttributedString(m.text)
                a.font = .system(size: 12, design: .serif).italic()
                ra += a
            } else if let a = try? AttributedString(
                markdown: m.text,
                options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)) {
                ra += a
            } else {
                ra += AttributedString(m.text)
            }
        }
        return ra
    }
}

// MARK: - Hiển thị

/// `Text` cho **chữ do tác tử viết**, ở bất kỳ đâu ngoài Console.
///
/// Lý do tồn tại: bộ dựng markdown ban đầu chỉ được nối vào Console, nên mọi chỗ khác —
/// tóm tắt khối trên các tab, ô bảng, chữ trên thẻ, thông báo, lớp "Vì sao?" — hiện
/// `**đậm**` dưới dạng ký tự thô. Người dùng đọc phải tự bóc dấu sao (DEV-247).
///
/// Ranh giới: chỉ dùng cho chữ **tác tử sinh ra**. Chữ do mã sinh (mã hiệu, số đếm,
/// nhãn cột, đường dẫn) vẫn dùng `Text` thường — ở đó dấu `*` và `_` là ký tự thật của
/// một cái tên, không phải cú pháp, và diễn dịch chúng là làm hỏng cái tên.
func TextMd(_ s: String) -> Text { Text(Markdown.inline(s)) }

extension Markdown {
    /// Chữ **sau khi dựng** — thứ người thật sự nhìn thấy.
    ///
    /// Có hàm này để phép kiểm hỏi được đúng câu hỏi của người dùng: "trên màn hình
    /// còn dấu sao không?". Kiểm trên chuỗi gốc thì luôn thấy `**` và không nói lên
    /// điều gì; kiểm trên chuỗi này thì `**` còn sót nghĩa là có một chỗ chưa nối vào
    /// bộ dựng.
    static func chuThuan(_ raw: String) -> String {
        tach(raw).map { k -> String in
            switch k {
            case .doan(let s), .tieuDe(_, let s):
                return String(inline(s).characters)
            case .danhSach(let m):
                return m.map { String(inline($0.0).characters) }.joined(separator: "\n")
            case .bang(let cot, let hang):
                return (([cot] + hang).map { h in
                    h.map { String(inline($0).characters) }.joined(separator: " ")
                }).joined(separator: "\n")
            case .ma(let than, _):
                return than                 // khối mã cố ý giữ nguyên văn
            case .trichDan(let d):
                return d.map { String(inline($0).characters) }.joined(separator: "\n")
            case .duongKe:
                return ""
            case .congThuc(let s, _):
                return s
            }
        }.joined(separator: "\n")
    }
}

struct MarkdownView: View {
    let text: String
    var co: CGFloat = 12

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            ForEach(Markdown.tach(text)) { k in KhoiView(khoi: k, co: co) }
        }
    }
}

private struct KhoiView: View {
    let khoi: MdKhoi
    let co: CGFloat

    var body: some View {
        switch khoi {
        case .doan(let s):
            Text(Markdown.inline(s))
                .font(.system(size: co))
                .textSelection(.enabled)
                .fixedSize(horizontal: false, vertical: true)

        case .tieuDe(let muc, let s):
            Text(Markdown.inline(s))
                .font(.system(size: coTieuDe(muc), weight: muc <= 2 ? .bold : .semibold))
                .textSelection(.enabled)
                .padding(.top, muc <= 2 ? 4 : 2)

        case .danhSach(let muc):
            let so = Markdown.soThuTu(muc)
            VStack(alignment: .leading, spacing: 3) {
                ForEach(Array(muc.enumerated()), id: \.offset) { i, m in
                    HStack(alignment: .firstTextBaseline, spacing: 6) {
                        Text(m.1 ? "\(so[i])." : "•")
                            .font(.system(size: co - 1))
                            .foregroundStyle(.secondary)
                            .frame(minWidth: 16, alignment: .trailing)
                        Text(Markdown.inline(m.0))
                            .font(.system(size: co))
                            .textSelection(.enabled)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(.leading, CGFloat(m.2) * 14)
                }
            }

        case .bang(let cot, let hang):
            BangMd(cot: cot, hang: hang, co: co)

        case .ma(let than, let ngonNgu):
            VStack(alignment: .leading, spacing: 0) {
                if let n = ngonNgu {
                    Text(n).font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(.tertiary)
                        .padding(.horizontal, 8).padding(.top, 5)
                }
                Text(than)
                    .font(.system(size: co - 1, design: .monospaced))
                    .textSelection(.enabled)
                    .padding(8)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color(nsColor: .underPageBackgroundColor),
                        in: RoundedRectangle(cornerRadius: 5))

        case .trichDan(let dong):
            HStack(alignment: .top, spacing: 8) {
                RoundedRectangle(cornerRadius: 1).fill(Color.secondary.opacity(0.4))
                    .frame(width: 2)
                VStack(alignment: .leading, spacing: 2) {
                    ForEach(dong, id: \.self) { d in
                        Text(Markdown.inline(d)).font(.system(size: co))
                            .foregroundStyle(.secondary)
                    }
                }
            }

        case .duongKe:
            Divider().padding(.vertical, 2)

        case .congThuc(let s, let tron):
            VStack(alignment: .leading, spacing: 2) {
                Text(s)
                    .font(.system(size: co + 2, design: tron ? .serif : .monospaced))
                    .italic(tron)
                    .textSelection(.enabled)
                if !tron {
                    Text("công thức nguyên bản — giao diện chưa đổi hết ký hiệu")
                        .font(.system(size: 9)).foregroundStyle(.tertiary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .center)
            .padding(.vertical, 5)
        }
    }

    private func coTieuDe(_ muc: Int) -> CGFloat {
        switch muc {
        case 1: return co + 5
        case 2: return co + 3
        case 3: return co + 1
        default: return co
        }
    }
}

/// Bảng markdown trong ô hội thoại.
///
/// Panel hội thoại chỉ rộng 320–640 px, nên một bảng cột cứng 130 px và chữ một dòng sẽ **cắt
/// mất nội dung** — và trong bảng của tác tử, cột dài nhất thường là cột nói CÁCH LÀM. Nên:
/// bề rộng cột tính theo nội dung của chính cột đó, và ô dài thì XUỐNG DÒNG chứ không cắt.
/// Vẫn cuộn ngang được cho bảng nhiều cột.
private struct BangMd: View {
    let cot: [String]
    let hang: [[String]]
    let co: CGFloat

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 0) {
                HStack(alignment: .top, spacing: 0) {
                    ForEach(Array(cot.enumerated()), id: \.offset) { j, c in
                        Text(Markdown.inline(c))
                            .font(.system(size: co - 1, weight: .semibold))
                            .fixedSize(horizontal: false, vertical: true)
                            .frame(width: rongCot(j), alignment: .leading)
                            .padding(.vertical, 5).padding(.horizontal, 7)
                    }
                }
                .background(Color(nsColor: .underPageBackgroundColor))
                Divider()
                ForEach(Array(hang.enumerated()), id: \.offset) { i, h in
                    HStack(alignment: .top, spacing: 0) {
                        ForEach(Array(h.enumerated()), id: \.offset) { j, o in
                            Text(Markdown.inline(o))
                                .font(.system(size: co - 1))
                                .textSelection(.enabled)
                                .fixedSize(horizontal: false, vertical: true)
                                .frame(width: rongCot(j), alignment: .topLeading)
                                .padding(.vertical, 4).padding(.horizontal, 7)
                                .help(o)
                        }
                    }
                    .background(i % 2 == 1
                                ? Color(nsColor: .underPageBackgroundColor).opacity(0.45)
                                : Color.clear)
                    Divider().opacity(0.3)
                }
            }
        }
        .overlay(RoundedRectangle(cornerRadius: 4)
            .strokeBorder(Color.secondary.opacity(0.2)))
    }

    /// Bề rộng cột theo NỘI DUNG của cột đó, trong khoảng vừa panel hội thoại.
    ///
    /// Trần thấp hơn bảng trên tab (220 so với 420) vì panel hẹp hơn nhiều; phần dài hơn thì
    /// xuống dòng, không cắt.
    private func rongCot(_ j: Int) -> CGFloat {
        let tran: CGFloat = cot.count >= 4 ? 170 : cot.count == 3 ? 200 : 240
        let dai = max(j < cot.count ? cot[j].count : 0,
                      hang.prefix(20).map { j < $0.count ? $0[j].count : 0 }.max() ?? 0)
        return min(max(CGFloat(dai) * 6.2 + 14, 70), tran)
    }
}
