import SwiftUI

/// Bảng **Giới thiệu** — ai làm ra EIDE, và nó là gì.
///
/// Vì sao nó đáng có một bề mặt riêng thay vì một dòng trong `Info.plist`: EIDE là đề án
/// thạc sĩ, nên "ai làm" và "hướng dẫn bởi ai" là thông tin người xem cần thấy được khi họ
/// mở ứng dụng lần đầu — không phải thứ phải đi tìm trong Finder.
///
/// Mọi thông tin ở đây là **hằng số của mã**, không lấy từ kho hay từ tác tử. Tên người là
/// thứ duy nhất trong cả hệ thống mà không phép đo nào kiểm được, nên nó phải nằm ở chỗ chỉ
/// người sửa được — đúng bài học của chặng bo thật, khi tác tử tự nghĩ ra tên học viên và
/// tên thầy hướng dẫn rồi vẽ chúng lên màn LCD.
struct GioiThieuView: View {
    /// Đóng bảng. Cửa sổ phụ tự quản, nên view không cần biết gì về `AppState`.
    var dong: (() -> Void)?

    private let phienBan = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString")
        as? String ?? "3.0.0"

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top, spacing: 18) {
                bieuTuong
                VStack(alignment: .leading, spacing: 6) {
                    Text("EIDE")
                        .font(.system(size: 34, weight: .bold, design: .rounded))
                    Text("IDE nhúng có tác tử đồng tác giả")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                    Text("Phiên bản \(phienBan)")
                        .font(.callout)
                        .foregroundStyle(.tertiary)
                        .padding(.top, 2)
                }
                Spacer(minLength: 0)
            }
            .padding(.bottom, 20)

            Divider()

            VStack(alignment: .leading, spacing: 14) {
                dong_muc("Đề án", "Luận văn Thạc sĩ Kỹ thuật Điện tử")
                dong_muc("Học viện", "Học viện Công nghệ Bưu chính Viễn thông (PTIT)")
                dong_muc("Học viên thực hiện", "Vũ Trí Công", nhan_manh: true)
                dong_muc("Giảng viên hướng dẫn", "TS. Nguyễn Trung Hiếu", nhan_manh: true)
            }
            .padding(.vertical, 20)

            Divider()

            Text(y_tuong)
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
                .padding(.vertical, 18)

            HStack {
                Spacer()
                if let dong {
                    Button("Đóng", action: dong).keyboardShortcut(.defaultAction)
                }
            }
        }
        .padding(28)
        .frame(width: 560)
    }

    /// Biểu tượng lấy từ chính gói ứng dụng — không nhúng lại ảnh vào mã.
    ///
    /// Đọc từ `Resources/AppIcon.png` trước, rồi mới tới biểu tượng hệ thống: khi chạy bằng
    /// `swift run` (chưa đóng gói .app) thì `NSApp.applicationIconImage` là biểu tượng mặc
    /// định của macOS, và hiện nó ra sẽ trông như ứng dụng chưa có biểu tượng.
    @ViewBuilder private var bieuTuong: some View {
        if let u = Bundle.main.url(forResource: "AppIcon", withExtension: "png"),
           let img = NSImage(contentsOf: u) {
            Image(nsImage: img).resizable().frame(width: 96, height: 96)
                .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        } else {
            Image(nsImage: NSApp.applicationIconImage)
                .resizable().frame(width: 96, height: 96)
        }
    }

    private func dong_muc(_ nhan: String, _ gia_tri: String,
                          nhan_manh: Bool = false) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 14) {
            Text(nhan)
                .font(.callout)
                .foregroundStyle(.secondary)
                .frame(width: 168, alignment: .leading)
            Text(gia_tri)
                .font(nhan_manh ? .body.weight(.semibold) : .body)
                .textSelection(.enabled)
            Spacer(minLength: 0)
        }
    }

    private let y_tuong = """
        EIDE coi tác tử là người đồng tác giả chứ không phải công cụ gợi ý: mọi con số phải \
        truy được về tài liệu gốc, mọi thao tác chạm phần cứng đều đi qua một thẻ cổng do \
        người duyệt, và không có lời "đạt" nào được nói ra khi chưa có bằng chứng đứng sau.
        """
}


/// Cửa sổ phụ cho bảng giới thiệu.
///
/// Dùng `NSWindow` thay vì `Scene` riêng vì bảng này mở theo lệnh menu, không theo vòng đời
/// tài liệu: một `WindowGroup` thứ hai sẽ hiện thêm một mục trong menu Window và mở lại khi
/// khôi phục phiên — cả hai đều không đúng với một bảng "về ứng dụng".
@MainActor
enum GioiThieuCuaSo {
    private static var cua_so: NSWindow?

    static func hien() {
        if let w = cua_so {
            w.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
            return
        }
        let w = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 560, height: 520),
            styleMask: [.titled, .closable, .fullSizeContentView],
            backing: .buffered, defer: false)
        w.title = "Giới thiệu EIDE"
        w.titlebarAppearsTransparent = true
        w.isReleasedWhenClosed = false
        w.contentView = NSHostingView(rootView: GioiThieuView(dong: { cua_so?.close() }))
        w.center()
        cua_so = w
        w.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
}
