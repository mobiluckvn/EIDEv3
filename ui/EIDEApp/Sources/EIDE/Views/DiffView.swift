import SwiftUI

/// Khối `diff` — hai bản cạnh nhau. EIDE-EDIT-47 §3.3, DEV-366.
///
/// Trước khối này, ba chỗ trong EIDE **nói** "xem diff" mà không có gì để xem: thẻ xung đột
/// (hai bản nhét vào một trường chữ, cắt ở 4 000 ký tự), cổng G-FILE ("ghi đè bản của anh" —
/// không nói đè cái gì), và phép xem trước khôi phục.
///
/// **Lõi tính `hunks`, đây chỉ vẽ** (I3). `difflib` của Python và một bộ dựng diff viết bằng
/// Swift là hai hiện thực của cùng một thuật toán, và hai hiện thực thì lệch nhau ở ca biên —
/// người sẽ thấy một diff khác với diff mà lõi dùng để quyết.
struct DiffView: View {
    @EnvironmentObject var state: AppState
    let d: JSONValue
    /// Người sửa cột phải tới đâu. `nil` = chưa đụng vào.
    @Binding var banDaSua: String?
    /// Đang nằm trong tấm rộng: không hiện lại nút "Mở rộng", và cho khung cao hết chỗ.
    var trongTam: Bool = false

    /// Mở khối này ra một tấm rộng. Cần thật: cột Console rộng 460 pt, chia đôi ra còn
    /// ~230 pt mỗi bên — đủ cho một dòng `int main(void){return 0;}` và không đủ cho mã
    /// thật. Thấy bằng ảnh chụp, không con số nào trong bản chụp giao diện kêu lên.
    @State private var moRong = false

    private var trai: [String] { Self.tachDong(d["trai"]?["noi_dung"]?.stringValue ?? "") }
    private var phai: [String] { Self.tachDong(d["phai"]?["noi_dung"]?.stringValue ?? "") }

    /// Tách dòng ĐÚNG NHƯ LÕI tách (`str.splitlines()`): một tệp kết thúc bằng xuống dòng
    /// có `n` dòng, không phải `n + 1`.
    ///
    /// `components(separatedBy:)` đếm thừa một dòng rỗng ở cuối, và cái dòng ma ấy hiện ra
    /// trên màn hình: ảnh chụp thẻ xung đột cho thấy một tệp MỘT dòng được đánh số tới 2.
    /// Tệ hơn con số: số dòng của giao diện lệch với số dòng trong `hunks` của lõi, nên
    /// phép tô màu sẽ trượt đúng một dòng ở mọi tệp kết thúc bằng xuống dòng.
    static func tachDong(_ s: String) -> [String] {
        var ds = s.components(separatedBy: "\n")
        if ds.count > 1, ds.last == "" { ds.removeLast() }
        return ds
    }
    private var hunks: [JSONValue] { d["hunks"]?.arrayValue ?? [] }
    private var choPhepSua: Bool { d["cho_phep_sua"]?.boolValue ?? false }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            dongTomTat
            if hunks.isEmpty {
                Label("Hai bản giống hệt nhau.", systemImage: "equal.circle")
                    .font(.system(size: 11)).foregroundStyle(.secondary)
            } else if choPhepSua {
                // Cột phải là một ô soạn THẬT, nên nó tự cuộn: `TextEditor` giữ vị trí
                // cuộn của riêng nó và SwiftUI thuần không đọc được vị trí ấy. Nên chỉ ca
                // "hai cột đều để đọc" cuộn đồng bộ được — nói ra, thay vì để người tưởng
                // cuộn hỏng ở đúng một trong hai ca.
                HStack(alignment: .top, spacing: 1) {
                    cot(nhan: d["trai"]?["nhan"]?.stringValue ?? "Bản A",
                        dong: trai, ben: .trai)
                    Divider()
                    cotSuaDuoc
                }
                .frame(maxHeight: trongTam ? .infinity : 340)
                .overlay(RoundedRectangle(cornerRadius: 5)
                    .strokeBorder(Color.secondary.opacity(0.25)))
            } else {
                haiCotCuonCungNhau
            }
            canhBaoCat
        }
    }

    // MARK: - Đầu

    private var dongTomTat: some View {
        let t = d["tom_tat"]
        let xd = t?["xung_dot"]?.intValue ?? 0
        return HStack(spacing: 8) {
            Text(d["tieu_de"]?.stringValue ?? "Diff")
                .font(.system(size: 11, weight: .semibold))
            if xd > 0 {
                Label("\(xd) đoạn CẢ HAI bên cùng sửa", systemImage: "exclamationmark.2")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(Color.gateRed)
            }
            Text("+\(t?["them"]?.intValue ?? 0) −\(t?["bot"]?.intValue ?? 0) "
                 + "· \(t?["doi"]?.intValue ?? 0) đoạn đổi")
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.secondary)
            Spacer()
            if !trongTam {
                Button("Mở rộng") { moRong = true }
                .buttonStyle(.plain).font(.system(size: 10, weight: .medium))
                .foregroundStyle(Color.accentColor)
                .help("Xem hai cột ở khổ lớn — cột Console quá hẹp cho mã thật")
            }
        }
        .sheet(isPresented: $moRong) {
            // Cùng một `banDaSua`: sửa ở tấm rộng rồi đóng lại thì chữ vẫn còn, và nút
            // "Dùng bản tôi vừa sửa" trên thẻ gửi đúng cái ấy.
            DiffSheet(d: d, banDaSua: $banDaSua)
        }
    }

    @ViewBuilder private var canhBaoCat: some View {
        // Lõi cắt nội dung quá dài và NÓI RA. Một diff cắt im lặng là thứ tệ nhất ở đây:
        // người đọc tưởng mình đã xem hết rồi mới bấm.
        if (d["trai"]?["cat"]?.boolValue ?? false) || (d["phai"]?["cat"]?.boolValue ?? false) {
            Label("Nội dung quá dài nên đã bị cắt để hiện — mở tệp ra xem bản đủ trước khi "
                  + "quyết.", systemImage: "scissors")
                .font(.system(size: 10)).foregroundStyle(Color.staleAmber)
        }
    }

    // MARK: - Hai cột

    private enum Ben { case trai, phai }

    /// Hai cột trong **MỘT** khung cuộn dọc — EIDE-EDIT-47 §DEV-380.
    ///
    /// Bản trước cho mỗi cột một `ScrollView` riêng, nên cuộn bên trái thì bên phải đứng
    /// im: đọc một diff 200 dòng thành việc canh hai thanh cuộn bằng tay, và đó đúng là
    /// lúc người ta bỏ không đọc nữa. Đặc tả có nêu "cuộn đồng bộ hai cột".
    ///
    /// Cách làm: **một** khung cuộn dọc bọc cả hai cột, nên chúng cuộn cùng nhau *vì cấu
    /// trúc* — không phải vì một phép đồng bộ hai chiều phải tự giữ cho khỏi lệch. Cuộn
    /// NGANG thì vẫn riêng từng cột, có chủ ý: hai bản thường dài dòng khác nhau, và ép
    /// chúng cuộn ngang cùng nhau là ép người đọc kéo cột trái để nhìn cột phải.
    ///
    /// Nhãn cột nằm NGOÀI khung cuộn: cuộn xuống 50 dòng mà không biết mình đang đọc cột
    /// nào thì hai cột cạnh nhau cũng chẳng để làm gì.
    private var haiCotCuonCungNhau: some View {
        VStack(spacing: 0) {
            HStack(alignment: .top, spacing: 1) {
                nhanCot(d["trai"]?["nhan"]?.stringValue ?? "Bản A")
                Divider()
                nhanCot(d["phai"]?["nhan"]?.stringValue ?? "Bản B")
            }
            ScrollView(.vertical) {
                HStack(alignment: .top, spacing: 1) {
                    dongCua(trai, ben: .trai)
                    Divider()
                    dongCua(phai, ben: .phai)
                }
            }
        }
        .frame(maxHeight: trongTam ? .infinity : 340)
        .overlay(RoundedRectangle(cornerRadius: 5)
            .strokeBorder(Color.secondary.opacity(0.25)))
    }

    private func nhanCot(_ nhan: String) -> some View {
        Text(nhan)
            .font(.system(size: 10, weight: .medium))
            .foregroundStyle(.secondary)
            .padding(.horizontal, 6).padding(.vertical, 3)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.secondary.opacity(0.08))
    }

    /// Phần DÒNG của một cột, không có khung cuộn dọc của riêng nó.
    private func dongCua(_ dong: [String], ben: Ben) -> some View {
        ScrollView(.horizontal) {
            VStack(alignment: .leading, spacing: 0) {
                ForEach(Array(dong.enumerated()), id: \.offset) { i, l in
                    hangDong(i: i, l: l, ben: ben)
                }
            }
            .padding(.vertical, 2)
        }
        .frame(maxWidth: .infinity)
    }

    private func hangDong(i: Int, l: String, ben: Ben) -> some View {
        HStack(alignment: .top, spacing: 6) {
            Text("\(i + 1)")
                .font(.system(size: 9, design: .monospaced))
                .foregroundStyle(.tertiary)
                .frame(width: 30, alignment: .trailing)
            Text(l.isEmpty ? " " : l)
                .font(.system(size: 11, design: .monospaced))
                .textSelection(.enabled)
                .fixedSize(horizontal: true, vertical: false)
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(mau(dong: i, ben: ben))
    }

    /// Một cột ĐỦ (nhãn + dòng), có khung cuộn dọc riêng. Chỉ còn dùng cho ca cột phải
    /// là ô soạn — ca ấy không cuộn đồng bộ được, xem `haiCotCuonCungNhau`.
    ///
    /// Dựng từ `nhanCot` + `dongCua`, KHÔNG vẽ lại dòng diff lần thứ hai: hai bản vẽ cùng
    /// một dòng sẽ lệch nhau ở màu hoặc ở số dòng, và lệch ở đây nghĩa là người đọc hai
    /// diff khác nhau tuỳ chỗ nó hiện ra.
    private func cot(nhan: String, dong: [String], ben: Ben) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            nhanCot(nhan)
            ScrollView(.vertical) { dongCua(dong, ben: ben) }
        }
        .frame(maxWidth: .infinity)
    }

    /// Cột phải sửa được — lựa chọn "dùng bản tôi vừa sửa" của thẻ xung đột.
    ///
    /// Dùng `TextEditor` chứ không phải NSTextView bọc như đặc tả: nó mất phần tô màu theo
    /// hunk **trong lúc đang gõ**, và điều đó được nói ra ngay trên nhãn. Đổi lại, nó là
    /// một ô văn bản thật — chép, dán, hoàn tác bằng Cmd-Z đều đúng như macOS, không phải
    /// dựng lại từng cái.
    private var cotSuaDuoc: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 5) {
                Text(d["phai"]?["nhan"]?.stringValue ?? "Bản B")
                    .font(.system(size: 10, weight: .medium)).foregroundStyle(.secondary)
                Text(banDaSua == nil ? "— sửa được" : "— anh đã sửa")
                    .font(.system(size: 9))
                    .foregroundStyle(banDaSua == nil ? Color.secondary : Color.accentColor)
                Spacer()
                if banDaSua != nil {
                    Button("Trả lại bản gốc") { banDaSua = nil }
                        .buttonStyle(.plain).font(.system(size: 9))
                        .foregroundStyle(Color.accentColor)
                }
            }
            .padding(.horizontal, 6).padding(.vertical, 3)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.secondary.opacity(0.08))

            TextEditor(text: Binding(
                get: { banDaSua ?? (d["phai"]?["noi_dung"]?.stringValue ?? "") },
                set: { banDaSua = $0 }))
                .font(.system(size: 11, design: .monospaced))
                .scrollContentBackground(.hidden)
        }
        .frame(maxWidth: .infinity)
    }

    /// Màu nền một dòng, theo hunk lõi gửi. Không tự dò khác biệt ở đây — xem đầu tệp.
    private func mau(dong i: Int, ben: Ben) -> Color {
        for h in hunks {
            let loai = h["loai"]?.stringValue ?? ""
            let bat = (h[ben == .trai ? "dong_trai" : "dong_phai"]?.intValue ?? 1) - 1
            let so = h[ben == .trai ? "so_trai" : "so_phai"]?.intValue ?? 0
            guard so > 0, i >= bat, i < bat + so else { continue }
            switch loai {
            case "xung_dot": return Color.gateRed.opacity(0.18)
            case "them":     return Color.okGreen.opacity(0.14)
            case "xoa":      return Color.gateRed.opacity(0.10)
            default:         return Color.staleAmber.opacity(0.14)
            }
        }
        return .clear
    }
}

/// Khối diff mở trong một tấm riêng — khi lõi gửi `diff.show` không gắn vào thẻ nào.
struct DiffSheet: View {
    @Environment(\.dismiss) private var dong
    let d: JSONValue
    @Binding var banDaSua: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            DiffView(d: d, banDaSua: $banDaSua, trongTam: true)
            HStack {
                Text("Sửa ở đây rồi đóng lại — chữ vẫn còn, và nút trên thẻ gửi đúng bản này.")
                    .font(.system(size: 10)).foregroundStyle(.secondary)
                Spacer()
                Button("Đóng") { dong() }.keyboardShortcut(.defaultAction)
            }
        }
        .padding(16).frame(width: 980, height: 620)
    }
}
