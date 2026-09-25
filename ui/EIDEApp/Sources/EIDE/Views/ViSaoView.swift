import SwiftUI

/// Lớp giải thích sáu trường — EIDE-MDD-40 §E3.1.
///
/// Đây là thứ nút "Vì sao?" mở ra. Nó **không gọi mô hình**: sáu trường này đã được
/// ghi cùng hiện vật ngay lúc tạo, vì hook `PreToolUse` từ chối ghi hiện vật nào thiếu
/// chúng (N8). Nghĩa là câu trả lời cho "vì sao lại thế" luôn có sẵn, tức thì, miễn phí
/// — kể cả khi mất mạng, kể cả sáu tháng sau.
struct ViSaoView: View {
    let explain: JSONValue
    let tieuDe: String

    private struct Truong: Identifiable {
        let id: String
        let nhan: String
        let cauHoi: String
    }

    private let truong: [Truong] = [
        .init(id: "summary", nhan: "Là gì", cauHoi: "Cái này là gì, một câu?"),
        .init(id: "why", nhan: "Vì sao", cauHoi: "Vì sao làm/chọn thế?"),
        .init(id: "sources", nhan: "Dựa vào", cauHoi: "Dựa vào đâu?"),
        .init(id: "diff_prev", nhan: "Khác trước", cauHoi: "Khác gì bản trước?"),
        .init(id: "next", nhan: "Tiếp theo", cauHoi: "Việc tiếp theo là gì?"),
        .init(id: "confidence", nhan: "Tin được", cauHoi: "Tin được đến đâu?"),
    ]

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(spacing: 6) {
                Text(tieuDe).font(.system(size: 12, weight: .semibold))
                Spacer()
                Text("0 token").font(.system(size: 9, design: .monospaced))
                    .foregroundStyle(.tertiary)
                    .help("Lớp giải thích được ghi cùng hiện vật — mở ra không tốn gì")
            }
            Divider()

            ForEach(truong) { t in
                if let v = explain[t.id], !laRong(v) {
                    VStack(alignment: .leading, spacing: 3) {
                        Text(t.nhan)
                            .font(.system(size: 9, weight: .semibold))
                            .foregroundStyle(.tertiary)
                            .help(t.cauHoi)
                        if t.id == "sources" {
                            NguonView(sources: v)
                        } else if t.id == "confidence" {
                            if let tier = Tier(loose: v.stringValue) {
                                TierChip(tier: tier)
                            } else {
                                Text(v.display).font(.system(size: 11))
                            }
                        } else {
                            Text(v.display)
                                .font(.system(size: 11))
                                .textSelection(.enabled)
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
            }

            if let g = explain["giai_thich_them"]?.stringValue, !g.isEmpty {
                Divider()
                VStack(alignment: .leading, spacing: 3) {
                    Text("Tác tử giải thích thêm")
                        .font(.system(size: 9, weight: .semibold)).foregroundStyle(.tertiary)
                    MarkdownView(text: g, co: 11).textSelection(.enabled)
                }
            }
        }
        .padding(13)
        .frame(width: 380)
    }

    private func laRong(_ v: JSONValue) -> Bool {
        if case .null = v { return true }
        if case .string(let s) = v { return s.isEmpty }
        if case .array(let a) = v { return a.isEmpty }
        return false
    }
}

/// Danh sách nguồn — mỗi nguồn mang tầng tin cậy của nó.
///
/// §E3.2 §2: "mọi con số là một liên kết… không có số trần". Ở đây điều đó thành:
/// mỗi nguồn hiện rõ nó là tài liệu, là lời người, hay là suy đoán của mô hình.
struct NguonView: View {
    let sources: JSONValue

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            ForEach(Array(sources.arrayValue.enumerated()), id: \.offset) { _, s in
                HStack(spacing: 5) {
                    if let t = Tier(loose: s["tier"]?.stringValue) {
                        TierChip(tier: t)
                    }
                    Image(systemName: bieuTuong(s["kind"]?.stringValue))
                        .font(.system(size: 9)).foregroundStyle(.secondary)
                    Text(s["ref"]?.stringValue ?? "—")
                        .font(.system(size: 10, design: .monospaced))
                        .textSelection(.enabled)
                }
            }
            if sources.arrayValue.isEmpty {
                Text("không có nguồn nào").font(.system(size: 10)).foregroundStyle(.tertiary)
            }
        }
    }

    private func bieuTuong(_ k: String?) -> String {
        switch k {
        case "fact": return "number.square"
        case "doc": return "doc.text"
        case "human_act": return "person.fill"
        case "changeset": return "arrow.triangle.branch"
        case "tool": return "wrench.adjustable"
        default: return "questionmark.circle"
        }
    }
}

/// Thanh tác giả — §E7 "thanh tác giả (người/tác tử) trên hiện vật".
struct ThanhTacGia: View {
    let tacGia: String
    private var laNguoi: Bool { tacGia == "nguoi" }

    var body: some View {
        RoundedRectangle(cornerRadius: 2)
            .fill(laNguoi ? Color.accentColor : Color.secondary.opacity(0.45))
            .frame(width: 3, height: 14)
            .help(laNguoi ? "Anh tạo hoặc sửa hiện vật này" : "Tác tử tạo hiện vật này")
    }
}
