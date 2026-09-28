import SwiftUI

@main
struct EIDEApp: App {
    @StateObject private var state = AppState()
    @StateObject private var setup = Setup()

    var body: some Scene {
        WindowGroup("EIDE") {
            RootView()
                .environmentObject(state)
                .environmentObject(setup)
                .frame(minWidth: 1100, minHeight: 720)
                // Mở cửa sổ NẰM TRỌN trong màn hình đang dùng. Bản trước để macOS tự đặt,
                // và trên một máy có nhiều màn hình nó mở lệch ra ngoài mép trái — phần
                // hội thoại bị cắt mất, trông y như một lỗi trình bày.
                .task {
                    // Mở cửa sổ nằm trọn trong màn hình đang dùng (xem `DatCuaSo`).
                    DatCuaSo.motLan()
                    guard setup.hopLe, !state.connection.ok else { return }
                    await state.mo(python: setup.pythonURL,
                                   repo: setup.repoURL,
                                   duAn: setup.duAnURL)
                }
        }
        .windowToolbarStyle(.unified)
        .commands {
            CommandGroup(replacing: .newItem) {}
            // Thay mục "About EIDE" mặc định của macOS bằng bảng của mình.
            //
            // Bảng mặc định chỉ đọc `Info.plist`, nên nó không nói được ai hướng dẫn đề án —
            // mà với một luận văn thì đó đúng là thông tin người xem tìm đầu tiên.
            CommandGroup(replacing: .appInfo) {
                Button("Giới thiệu EIDE") { GioiThieuCuaSo.hien() }
            }
            CommandMenu("Tác tử") {
                Button("Dừng khẩn") { state.gui(.stopNow()) }
                    .keyboardShortcut(".", modifiers: .command)
                Divider()
                Button("Vẽ lại bề mặt") { Task { await state.veLai() } }
                    .keyboardShortcut("r", modifiers: .command)
            }
        }
    }
}

/// Nơi app biết tìm lõi ở đâu. Không phải trạng thái nghiệp vụ — chỉ là đường dẫn.
@MainActor
final class Setup: ObservableObject {
    @AppStorage("repoPath") var repoPath: String = Setup.doanRepo()
    @AppStorage("pythonPath") var pythonPath: String = ""
    @AppStorage("duAnPath") var duAnPath: String = ""

    var repoURL: URL { URL(fileURLWithPath: repoPath) }
    var duAnURL: URL { URL(fileURLWithPath: duAnPath) }
    var pythonURL: URL {
        pythonPath.isEmpty
            ? repoURL.appendingPathComponent(".venv/bin/python")
            : URL(fileURLWithPath: pythonPath)
    }

    var hopLe: Bool {
        let fm = FileManager.default
        var laThuMuc: ObjCBool = false
        let coDuAn = fm.fileExists(atPath: duAnPath, isDirectory: &laThuMuc)
        return !duAnPath.isEmpty && coDuAn && laThuMuc.boolValue
            && fm.fileExists(atPath: pythonURL.path)
            && fm.fileExists(atPath: repoURL.appendingPathComponent("src/eide").path)
    }

    var vanDe: String? {
        let fm = FileManager.default
        if !fm.fileExists(atPath: repoURL.appendingPathComponent("src/eide").path) {
            return "Không thấy lõi ở \(repoPath)/src/eide"
        }
        if !fm.fileExists(atPath: pythonURL.path) {
            return "Không thấy Python ở \(pythonURL.path). Chạy: python3 -m venv .venv"
        }
        if duAnPath.isEmpty { return nil }
        var laThuMuc: ObjCBool = false
        if !fm.fileExists(atPath: duAnPath, isDirectory: &laThuMuc) {
            return "Thư mục dự án không tồn tại."
        }
        if !laThuMuc.boolValue {
            return "Đây là một TỆP, không phải thư mục. Dự án cần một thư mục — "
                 + "tác tử sẽ đọc/ghi bên trong nó, và `.eide/` nằm ở đó."
        }
        return nil
    }

    /// Đoán gốc repo từ vị trí tệp thực thi — đúng khi chạy bằng `swift run`.
    private static func doanRepo() -> String {
        var u = URL(fileURLWithPath: CommandLine.arguments[0]).resolvingSymlinksInPath()
        for _ in 0..<8 {
            u.deleteLastPathComponent()
            if FileManager.default.fileExists(
                atPath: u.appendingPathComponent("src/eide/loop.py").path) {
                return u.path
            }
        }
        return FileManager.default.currentDirectoryPath
    }
}
