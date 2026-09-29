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
                    MenuDon.boMenuRong()
                    state.taoDuAnTai = { try setup.taoDuAn(tai: URL(fileURLWithPath: $0)) }
                    state.moDuAnKhac = { d in
                        setup.duAnPath = d
                        if state.connection.ok { state.dong() }
                        await moRoiGhiNho()
                    }
                    state.duAnGanDay = { setup.ganDay }
                    guard setup.hopLe, !state.connection.ok else { return }
                    // Đi qua `moRoiGhiNho` chứ không gọi thẳng `state.mo`: dự án tự mở lúc
                    // khởi động cũng phải vào danh sách gần đây, nếu không thì dự án người
                    // dùng dùng NHIỀU NHẤT lại là dự án duy nhất không có trong đó.
                    await moRoiGhiNho()
                }
        }
        .windowToolbarStyle(.unified)
        .commands {
            // File ▸ Dự án mới / Mở gần đây / Đóng dự án.
            //
            // Bản trước xoá trắng nhóm này (`CommandGroup(replacing: .newItem) {}`) và không
            // thay gì vào, nên "tạo dự án" CHẠY ĐƯỢC mà không nhìn được: nó chỉ là hệ quả
            // của việc mở một thư mục rỗng. Và vì `dong()` chưa từng được gọi ở đâu, một khi
            // đã đặt dự án thì không còn đường quay lại màn mở — danh sách gần đây có làm ra
            // cũng không ai tới được.
            CommandGroup(replacing: .newItem) {
                Button("Dự án mới…") { taoDuAnMoi() }
                    .keyboardShortcut("n", modifiers: .command)
                Menu("Mở gần đây") {
                    ForEach(setup.ganDay, id: \.self) { d in
                        Button(URL(fileURLWithPath: d).lastPathComponent) { moDuAn(d) }
                            .help(d)
                    }
                    if setup.ganDay.isEmpty { Text("Chưa có dự án nào") }
                }
                Divider()
                Button("Đóng dự án") { state.dong() }
                    .keyboardShortcut("w", modifiers: [.command, .shift])
                    .disabled(!state.connection.ok)
            }
            // Thay mục "About EIDE" mặc định của macOS bằng bảng của mình.
            //
            // Bảng mặc định chỉ đọc `Info.plist`, nên nó không nói được ai hướng dẫn đề án —
            // mà với một luận văn thì đó đúng là thông tin người xem tìm đầu tiên.
            CommandGroup(replacing: .appInfo) {
                Button("Giới thiệu EIDE") { GioiThieuCuaSo.hien() }
            }
            CommandMenu("Tác tử") {
                // ⌘Z của macOS là Undo của Ô VĂN BẢN, không phải của dự án.
                //
                // Đo được 29/09/2026 bằng cách bảo app tự khai thanh menu: Edit ▸ Undo ⌘Z có
                // sẵn và nó lùi chữ vừa gõ. Người bấm ⌘Z mong lùi việc tác tử vừa làm sẽ
                // được một kết quả hợp lý mà sai — loại nhầm khó phát hiện nhất, vì không có
                // thông báo nào.
                //
                // Nên việc lùi DỰ ÁN có phím riêng và tên riêng, đặt cạnh nhau để đọc là
                // thấy khác nhau.
                Button("Hoàn tác việc vừa làm") {
                    state.gui(.say("Hoàn tác việc bạn vừa làm giúp mình."))
                }
                .keyboardShortcut("z", modifiers: [.command, .option])
                .disabled(!state.connection.ok || state.busy)
                Divider()
                Button("Dừng khẩn") { state.gui(.stopNow()) }
                    .keyboardShortcut(".", modifiers: .command)
                Button("Vẽ lại bề mặt") { Task { await state.veLai() } }
                    .keyboardShortcut("r", modifiers: .command)
            }
            // `View` và `Help` là hai menu macOS tự thêm cho một `WindowGroup`. App này
            // không có sidebar, không có thanh công cụ, không có tệp trợ giúp — nên bỏ ba
            // nhóm lệnh ấy đi.
            //
            // `Help` biến mất hẳn. `View` thì SwiftUI dựng lại sau mỗi lần gỡ, nên thay vì
            // đuổi theo nó bằng một cái đồng hồ mỗi lúc một dài, ĐỔ VÀO ĐÓ thứ vốn thuộc về
            // nó: ba bề rộng Console. Trước đây chúng chỉ bấm được bằng chuột, không có phím
            // tắt nào — nên đây vừa dọn được một menu rỗng vừa thêm một đường cho bàn phím.
            CommandGroup(replacing: .sidebar) {
                Picker("Bề rộng bàn giao tiếp", selection: $state.consoleWidth) {
                    Text("Hẹp").tag(AppState.ConsoleWidth.hep)
                    Text("Vừa").tag(AppState.ConsoleWidth.vua)
                    Text("Rộng").tag(AppState.ConsoleWidth.rong)
                }
                .pickerStyle(.inline)
            }
            CommandGroup(replacing: .toolbar) {}
            CommandGroup(replacing: .help) {}
        }
    }

    /// Hỏi chỗ đặt, tạo thư mục, rồi mở luôn.
    ///
    /// Dùng `NSSavePanel` chứ không phải `NSOpenPanel`: người đang ĐẶT TÊN một thứ chưa có,
    /// không phải chọn một thứ đã có. Bảng "mở" không có ô gõ tên, nên với nó "tạo dự án"
    /// vẫn là "tự tạo thư mục trong Finder trước đã".
    @MainActor private func taoDuAnMoi() {
        let p = NSSavePanel()
        p.title = "Dự án EIDE mới"
        p.prompt = "Tạo"
        p.nameFieldLabel = "Tên dự án:"
        p.nameFieldStringValue = "du-an-moi"
        p.canCreateDirectories = true
        guard p.runModal() == .OK, let u = p.url else { return }
        do {
            try setup.taoDuAn(tai: u)
            Task { await moRoiGhiNho() }
        } catch {
            state.notices.append(.init(level: "error",
                                       text: error.localizedDescription, code: nil))
        }
    }

    @MainActor private func moDuAn(_ duong: String) {
        setup.duAnPath = duong
        Task {
            if state.connection.ok { state.dong() }
            await moRoiGhiNho()
        }
    }

    /// Mở, rồi CHỈ ghi nhớ khi lõi đã bắt tay xong.
    ///
    /// Ghi nhớ lúc bấm nút thì danh sách "gần đây" sẽ đầy những đường dẫn gõ sai, và người
    /// phải thử từng cái mới biết cái nào thật.
    @MainActor private func moRoiGhiNho() async {
        await state.mo(python: setup.pythonURL, repo: setup.repoURL, duAn: setup.duAnURL)
        if state.connection.ok { setup.ghiNho(setup.duAnPath) }
    }
}


/// Bỏ khỏi thanh menu những menu KHÔNG có mục nào.
///
/// macOS tự thêm `View` và `Help` cho một `WindowGroup`. App này không có sidebar, không có
/// thanh công cụ, không có tệp trợ giúp — nên sau khi thay chúng bằng nhóm rỗng, hai cái tên
/// ấy vẫn nằm trên thanh menu với **không mục nào bên trong**.
///
/// Một menu rỗng là một lời hứa không có gì sau lưng: người bấm vào, thấy trống, và không
/// biết đó là lỗi hay là chưa làm. Cùng họ với thẻ cổng bấm được mà không làm gì (DEV-289)
/// và nhãn "không còn ở đây" không hiện ra (DEV-290).
///
/// Lọc theo **số mục**, không theo tên: tên menu đổi theo ngôn ngữ hệ thống, còn "rỗng" thì
/// không.
@MainActor
enum MenuDon {
    /// Gọi lặp vài nhịp, không gọi một lần.
    ///
    /// SwiftUI dựng thanh menu SAU khi `.task` của khung gốc chạy, nên một lần gọi duy nhất
    /// không đụng được vào gì — đo được đúng như vậy: gọi một lần thì `View` và `Help` vẫn
    /// còn nguyên với 0 mục. Và nó còn dựng lại menu mỗi khi `commands` đổi, nên phải quét
    /// thêm vài nhịp nữa thay vì tin lần đầu.
    static func boMenuRong(soLan: Int = 6) {
        guard soLan > 0 else { return }
        let thanh = NSApp.mainMenu
        if let thanh {
            for m in thanh.items.reversed() where (m.submenu?.items.isEmpty ?? false) {
                thanh.removeItem(m)
            }
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.25) {
            boMenuRong(soLan: soLan - 1)
        }
    }
}

/// Nơi app biết tìm lõi ở đâu. Không phải trạng thái nghiệp vụ — chỉ là đường dẫn.
@MainActor
final class Setup: ObservableObject {
    @AppStorage("repoPath") var repoPath: String = Setup.doanRepo()
    @AppStorage("pythonPath") var pythonPath: String = ""
    @AppStorage("duAnPath") var duAnPath: String = ""

    /// Các dự án đã mở, mới nhất trước. Lưu JSON vì `@AppStorage` không giữ được mảng.
    ///
    /// Vì sao cần: đề án này có HAI dự án trên cùng một bo (`stm32f469-disco` giữ nguyên làm
    /// hiện vật G7, `stm32f469-freertos` làm tiếp) và người dùng đi lại giữa chúng. Trước
    /// đây chỉ có một chuỗi `duAnPath` bị ghi đè mỗi lần, nên đổi dự án là gõ lại đường dẫn.
    @AppStorage("duAnGanDay") private var ganDayJSON: String = "[]"

    var ganDay: [String] {
        (try? JSONDecoder().decode([String].self,
                                   from: Data(ganDayJSON.utf8))) ?? []
    }

    /// Ghi nhớ một dự án vừa mở THÀNH CÔNG.
    ///
    /// Chỉ gọi sau khi lõi đã bắt tay xong. Ghi nhớ lúc bấm nút thì danh sách sẽ đầy những
    /// đường dẫn gõ sai — và một danh sách "gần đây" toàn thứ không mở được thì tệ hơn không
    /// có, vì người phải thử từng cái mới biết cái nào thật.
    func ghiNho(_ duong: String) {
        guard !duong.isEmpty else { return }
        var ds = ganDay.filter { $0 != duong }
        ds.insert(duong, at: 0)
        if ds.count > 8 { ds = Array(ds.prefix(8)) }
        ganDayJSON = String(data: (try? JSONEncoder().encode(ds)) ?? Data("[]".utf8),
                            encoding: .utf8) ?? "[]"
    }

    func quen(_ duong: String) {
        let ds = ganDay.filter { $0 != duong }
        ganDayJSON = String(data: (try? JSONEncoder().encode(ds)) ?? Data("[]".utf8),
                            encoding: .utf8) ?? "[]"
    }

    /// Thư mục tổ tiên nào của `url` đã là một dự án EIDE rồi — `nil` nếu không có.
    ///
    /// Luật "không tạo lồng" (bản mẫu UI, A14.1.1). Một dự án nằm trong một dự án khác thì
    /// `.eide/` của cái trong — sổ cái, kho hiện vật, ảnh chụp — trở thành tệp thường trong
    /// hộp cát của tác tử ngoài: nó đọc được, sửa được, và không có gì nói cho nó biết đấy là
    /// sổ cái của một dự án khác.
    static func duAnBaoTrum(_ url: URL) -> String? {
        let fm = FileManager.default
        var u = url.standardizedFileURL
        for _ in 0..<24 {
            let cha = u.deletingLastPathComponent()
            if cha.path == u.path { break }
            u = cha
            if fm.fileExists(atPath: u.appendingPathComponent(".eide").path) { return u.path }
        }
        return nil
    }

    enum LoiTaoDuAn: LocalizedError {
        case daTonTai(String)
        case namTrongDuAnKhac(String)
        case khongTaoDuoc(String)

        var errorDescription: String? {
            switch self {
            case .daTonTai(let p):
                return "Đã có thứ gì đó ở \(p). Chọn tên khác, hoặc dùng \"Mở dự án\" nếu "
                     + "đây đã là dự án cũ của anh."
            case .namTrongDuAnKhac(let p):
                return "Chỗ này nằm bên trong dự án \(p). Một dự án lồng trong dự án khác thì "
                     + "sổ cái và kho hiện vật của nó trở thành tệp thường trong hộp cát của "
                     + "tác tử ngoài. Chọn một chỗ bên ngoài."
            case .khongTaoDuoc(let m):
                return "Không tạo được thư mục: \(m)"
            }
        }
    }

    /// Tạo thư mục cho một dự án mới. KHÔNG dựng `.eide/` — việc ấy là của lõi khi nó mở.
    ///
    /// Giữ đúng một nguồn sự thật cho chuyện "một dự án gồm những gì": `Paths.ensure` bên
    /// Python. App mà tự dựng lấy vài thư mục thì hai chỗ sẽ trôi khỏi nhau, và cái trôi ấy
    /// chỉ lộ ra khi có người mở một dự án do bản app cũ tạo.
    func taoDuAn(tai url: URL) throws {
        let fm = FileManager.default
        if fm.fileExists(atPath: url.path) { throw LoiTaoDuAn.daTonTai(url.path) }
        if let ngoai = Setup.duAnBaoTrum(url) { throw LoiTaoDuAn.namTrongDuAnKhac(ngoai) }
        do { try fm.createDirectory(at: url, withIntermediateDirectories: true) }
        catch { throw LoiTaoDuAn.khongTaoDuoc(error.localizedDescription) }
        duAnPath = url.path
    }

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
