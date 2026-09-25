import SwiftUI

/// Quy ước màu và chữ.
///
/// Bốn tầng tin cậy (§C1) có màu cố định, và đây là chỗ DUY NHẤT định nghĩa chúng —
/// một con số tầng VÀNG ở tab Tri thức mạch phải trông giống hệt nó ở tab Thiết kế,
/// nếu không người sẽ học sai cách đọc màu.
enum Tier: String {
    case vang = "VANG", bac = "BAC", nguoi = "NGUOI", dong = "DONG"

    init?(loose s: String?) {
        guard let s = s?.uppercased() else { return nil }
        if s.contains("VÀNG") || s.contains("VANG") { self = .vang; return }
        if s.contains("BẠC") || s.contains("BAC") { self = .bac; return }
        if s.contains("NGƯỜI") || s.contains("NGUOI") { self = .nguoi; return }
        if s.contains("ĐỒNG") || s.contains("DONG") { self = .dong; return }
        return nil
    }

    var nhan: String {
        switch self {
        case .vang: return "VÀNG"
        case .bac:  return "BẠC"
        case .nguoi: return "NGƯỜI"
        case .dong: return "ĐỒNG"
        }
    }

    var nen: Color {
        switch self {
        case .vang: return Color(red: 1.00, green: 0.95, blue: 0.75)
        case .bac:  return Color(nsColor: .quaternaryLabelColor)
        case .nguoi: return Color(red: 0.82, green: 0.90, blue: 1.00)
        case .dong: return .clear
        }
    }

    var chu: Color {
        switch self {
        case .vang: return Color(red: 0.42, green: 0.31, blue: 0.00)
        case .bac:  return .secondary
        case .nguoi: return Color(red: 0.08, green: 0.29, blue: 0.55)
        case .dong: return .secondary
        }
    }

    /// Chú giải hiện khi rê chuột — §E3.2 §2 "không có số trần".
    var giaiThich: String {
        switch self {
        case .vang: return "VÀNG — tài liệu đã duyệt, đã xác nhận đúng dòng. Dùng được để quyết định và sinh mã."
        case .bac:  return "BẠC — nguồn đã duyệt nhưng chưa xác nhận từng dòng. Dùng được, có cảnh báo."
        case .nguoi: return "NGƯỜI — anh cho, chưa có tài liệu. Dùng được, nhưng mọi nơi dùng đều ghi rõ điều đó."
        case .dong: return "ĐỒNG — tri thức chung của mô hình, CHƯA KIỂM CHỨNG. Không được dùng làm vế so sánh, không vào mã."
        }
    }
}

extension Color {
    static let gateRed = Color(red: 0.72, green: 0.10, blue: 0.14)
    static let staleAmber = Color(red: 0.72, green: 0.48, blue: 0.00)
    static let okGreen = Color(red: 0.10, green: 0.45, blue: 0.20)
}

struct TierChip: View {
    let tier: Tier
    var body: some View {
        Text(tier.nhan)
            .font(.system(size: 10, weight: .semibold))
            .padding(.horizontal, 5).padding(.vertical, 1)
            .background(tier.nen, in: RoundedRectangle(cornerRadius: 3))
            .foregroundStyle(tier.chu)
            .overlay(RoundedRectangle(cornerRadius: 3)
                .strokeBorder(tier == .dong ? Color.secondary.opacity(0.4) : .clear))
            .italic(tier == .dong)
            .help(tier.giaiThich)
    }
}

/// Nhãn bước lộ trình (G1–G7) cho khối chưa có dữ liệu.
struct BuocChip: View {
    let buoc: String
    var body: some View {
        Text(buoc)
            .font(.system(size: 10, weight: .semibold, design: .monospaced))
            .padding(.horizontal, 5).padding(.vertical, 1)
            .background(Color.accentColor.opacity(0.14), in: RoundedRectangle(cornerRadius: 3))
            .foregroundStyle(Color.accentColor)
            .help("Tính năng này thuộc bước \(buoc) của lộ trình hiện thực.")
    }
}

struct MaKhoi: View {
    let ma: String
    var body: some View {
        Text(ma)
            .font(.system(size: 9, design: .monospaced))
            .foregroundStyle(.tertiary)
            .help("Mã khối giao diện \(ma) — khớp với ma trận ánh xạ yêu cầu ↔ giao diện.")
    }
}
