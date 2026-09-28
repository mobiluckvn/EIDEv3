import Foundation
import SwiftUI

/// Trạng thái giao diện — **hình chiếu** của những gì lõi đã gửi, không hơn.
///
/// I3: giao diện không quyết. Cụ thể ở đây nghĩa là lớp này không có một dòng nào tự
/// nghĩ ra nội dung: mọi bề mặt, mọi thẻ, mọi dòng transcript đều đến từ một UICommand.
/// Thứ duy nhất nó tự giữ là trạng thái *nhìn* (tab nào đang mở, ô nhập đang gõ gì).
@MainActor
final class AppState: ObservableObject {

    // Từ lõi
    @Published var transcript: [TranscriptLine] = []
    @Published var surfaces: [String: SurfaceModel] = [:]
    @Published var cards: [Card] = []
    @Published var status = StatusBar()
    @Published var run: RunState?
    @Published var notices: [Notice] = []
    @Published var staleList: [String] = []

    // Trạng thái nhìn (của riêng giao diện)
    @Published var selectedSurface: String = "project"
    @Published var draft: String = ""
    @Published var consoleWidth: ConsoleWidth = .vua
    @Published var connection: Connection = .chuaKetNoi
    @Published var coreLog: [String] = []
    @Published var busy = false
    /// Khung THẬT của từng khối sau khi vẽ (toạ độ trong tab). Khoá là mã khối.
    ///
    /// Có nó để bộ đo hỏi được một câu mà trước đây không hỏi được: **khối nào đang vẽ đè lên
    /// khối nào**. Lỗi đó đã xảy ra thật — bảng 256 dòng nằm trong một `ScrollView(.horizontal)`
    /// (không cắt theo chiều dọc) tràn ra ngoài khung và phủ lên hai khối bên dưới, làm cả tab
    /// Tri thức mạch không đọc được dòng nào. Mọi ca đo khi đó vẫn xanh, vì chúng đếm khối và
    /// đếm dòng chứ không hỏi khối nằm ở đâu.
    @Published var khungKhoi: [String: CGRect] = [:]

    /// Loại khối mà giao diện KHÔNG biết vẽ, do chính nhánh `default` của bộ vẽ ghi vào.
    ///
    /// Có nó vì một ca đo trước đây xanh nhờ một danh sách loại khối viết trong Python: nó
    /// kiểm rằng *bộ đo* biết loại khối đó, chứ không kiểm rằng *giao diện* vẽ được. Bây giờ
    /// chỗ báo là chỗ hỏng.
    @Published var khoiChuaBietVe: Set<String> = []

    /// Thư mục dự án đang mở — khối A5.8 cần nó để đọc tệp SVG mà lõi vừa ghi.
    ///
    /// Lõi gửi ĐƯỜNG DẪN chứ không gửi nội dung ảnh: một SVG mạch 120 linh kiện là hàng trăm
    /// KB, và nhét nó vào mọi lần `surface.set` là trả giá đó ở mỗi lượt vẽ lại.
    @Published var duAnDir: URL?

    private let client = CoreClient()
    private var streaming: [String: Int] = [:]   // stream_id → chỉ số dòng transcript
    /// Kênh kiểm thử giao diện — chỉ bật khi dự án có thư mục `.eide/ui-test/`.
    let kenhKiemThu = UITestChannel()

    enum ConsoleWidth: CGFloat, CaseIterable {
        case hep = 320, vua = 460, rong = 640
        var nhan: String { self == .hep ? "Hẹp" : self == .vua ? "Vừa" : "Rộng" }
    }

    enum Connection: Equatable {
        case chuaKetNoi
        case dangChay(String)          // tóm tắt sổ cái khi mở dự án
        case hong(String)

        var ok: Bool { if case .dangChay = self { return true }; return false }
    }

    struct RunState {
        var id: String
        var status: String
        var tools: Int
        var seconds: Double
        var tokensIn: Int
        var tokensOut: Int
        var assumptions: [String]
    }

    struct Notice: Identifiable {
        let id = UUID()
        let level: String
        let text: String
        let code: String?
    }

    // MARK: - Mở dự án

    /// Ba việc thuộc về `Setup` mà `AppState` không với tới: tạo dự án, mở một dự án khác,
    /// và đọc danh sách gần đây. Lớp `EIDEApp` gắn vào lúc dựng.
    ///
    /// Có chúng thì kênh kiểm thử giao diện gọi được — nếu không, ba tính năng vừa làm sẽ
    /// chỉ kiểm được bằng mắt, mà kiểm bằng mắt thì không chạy lại được ở lần sau.
    var taoDuAnTai: ((String) throws -> Void)?
    var moDuAnKhac: ((String) async -> Void)?
    var duAnGanDay: (() -> [String])?

    func mo(python: URL, repo: URL, duAn: URL) async {
        client.onCommand = { [weak self] c in self?.apply(c) }
        client.onStderr = { [weak self] s in
            self?.coreLog.append(s)
            if self?.coreLog.count ?? 0 > 400 { self?.coreLog.removeFirst(200) }
        }
        client.onExit = { [weak self] code in
            self?.connection = .hong("Lõi đã thoát (mã \(code)). Xem Nhật ký để biết vì sao.")
        }

        do {
            duAnDir = duAn
            try client.start(.init(python: python, repoRoot: repo, projectDir: duAn))
            let hello = try await client.call("hello", ["client": .object([
                "name": .string("EIDE.app"), "uap": .string("1.1")
            ])])
            let so = hello["ledger"]?["message_vi"]?.stringValue ?? ""
            connection = .dangChay(so)
            // Vẽ lần đầu: lời gọi MÁY–MÁY, không để lại dòng nào trong transcript (I1/I2).
            try await client.call("ui.sync")
            kenhKiemThu.batNeuCo(duAn: duAn, state: self)
        } catch {
            connection = .hong(error.localizedDescription)
        }
    }

    /// Vẽ lại mọi tab: lời gọi MÁY–MÁY, 0 token, không để lại dòng nào trong transcript.
    ///
    /// Chuyển tab KHÔNG vẽ lại (đó là "sự chú ý", không phải "yêu cầu" — xem `_dieu_huong`),
    /// nên bộ đo cần một cách xin vẽ lại sau khi kho đổi mà không phải tiêu một lượt mô hình.
    func veLai() async {
        do { _ = try await client.call("ui.sync") } catch {
            notices.append(.init(level: "warn", text: "Không vẽ lại được: \(error)",
                                 code: nil))
        }
    }

    func dong() {
        client.stop()
        connection = .chuaKetNoi
    }

    /// Xin lõi vẽ lại toàn bộ bề mặt. Máy–máy: không phải ý chí của người, nên không
    /// đi qua console.act và không để lại dòng nào trong transcript (I1, I2).
    func veLai() {
        guard connection.ok else { return }
        Task { _ = try? await client.call("ui.sync") }
    }

    // MARK: - Gửi ý chí của người (I1 — mọi đường đều qua đây)

    func gui(_ act: HumanAct) {
        guard connection.ok else { return }
        busy = true
        Task {
            do { _ = try await client.send(act) }
            catch {
                notices.append(.init(level: "error", text: error.localizedDescription, code: nil))
            }
            busy = false
        }
    }

    func guiCauDangGo() {
        let t = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return }
        draft = ""
        gui(.say(t))
    }

    // MARK: - Nhận UICommand (16 lệnh)

    private func apply(_ c: UICommand) {
        switch c.method {

        case "console.post":
            let role = TranscriptLine.Role(rawValue: c.params["role"]?.stringValue ?? "agent") ?? .agent
            var card: Card?
            if let raw = c.params["card"]?.objectValue, !raw.isEmpty {
                let id = raw["card_id"]?.stringValue ?? UUID().uuidString
                card = Card(id: id, raw: raw)
                cards.append(card!)
            }
            transcript.append(.init(role: role,
                                    text: c.params["text"]?.stringValue ?? "",
                                    card: card))

        case "console.stream":
            let sid = c.params["stream_id"]?.stringValue ?? "?"
            let delta = c.params["delta"]?.stringValue ?? ""
            let done = c.params["done"]?.boolValue ?? false
            if done {
                // Văn bản đầy đủ tới sau bằng console.post; bỏ dòng stream tạm đi để
                // transcript giữ đúng một dòng cho mỗi lượt nói (I2).
                if let i = streaming.removeValue(forKey: sid), i < transcript.count {
                    transcript.remove(at: i)
                }
            } else if let i = streaming[sid], i < transcript.count {
                transcript[i].text += delta
            } else if !delta.isEmpty {
                streaming[sid] = transcript.count
                transcript.append(.init(role: .agent, text: delta))
            }

        case "card.resolve", "card.expire":
            let id = c.params["card_id"]?.stringValue ?? ""
            if let i = cards.firstIndex(where: { $0.id == id }) { cards[i].resolved = true }
            // `Card` là struct — KIỂU TRỊ. Dòng hội thoại giữ một BẢN SAO của nó
            // (`transcript[i].card`), nên sửa `cards[i]` ở trên không đụng tới bản sao ấy, và
            // `ConsoleView` vẽ nút Duyệt/Từ chối dựa vào chính bản sao ấy.
            //
            // Hậu quả, thấy bằng ảnh chụp chứ không thấy bằng số đo: sau khi người đã trả
            // lời (hoặc thẻ đã hết hạn), hai cái nút VẪN nằm trong dòng hội thoại và VẪN bấm
            // được, trong khi `theDangCho` báo 0. Bản đo của tôi hỏi `theDangCho` nên nó xanh
            // — số đo đúng câu hỏi sai. Một cái nút bấm được mà không làm gì là thứ tệ nhất
            // trong ba khả năng: người tưởng mình vừa quyết định điều gì đó.
            for i in transcript.indices where transcript[i].card?.id == id {
                transcript[i].card?.resolved = true
            }

        case "surface.set":
            guard let name = c.params["surface"]?.stringValue,
                  let model = c.params["model"] else { return }
            if let m = try? JSONDecoder().decode(
                SurfaceModel.self, from: JSONEncoder().encode(model)) {
                surfaces[name] = m
            }

        case "surface.patch", "surface.append":
            // Lõi ở bước này luôn gửi cả bề mặt; khi G2 bật vá từng phần thì nối vào đây.
            break

        case "surface.focus":
            if let s = c.params["surface"]?.stringValue { selectedSurface = s }

        case "run.update":
            let cost = c.params["cost"]?.objectValue ?? [:]
            let tok = cost["tokens"]?.objectValue ?? [:]
            run = RunState(
                id: c.params["run_id"]?.stringValue ?? "",
                status: c.params["status"]?.stringValue ?? "",
                tools: cost["tools"]?.intValue ?? 0,
                seconds: Double(cost["seconds"]?.stringValue ?? "0") ?? 0,
                tokensIn: tok["in"]?.intValue ?? 0,
                tokensOut: tok["out"]?.intValue ?? 0,
                assumptions: (c.params["assumptions"]?.arrayValue ?? []).compactMap(\.stringValue))

        case "notice":
            notices.append(.init(level: c.params["level"]?.stringValue ?? "info",
                                 text: c.params["text"]?.stringValue ?? "",
                                 code: c.params["code"]?.stringValue))

        case "ui.set":
            if c.params["key"]?.stringValue == "status_bar",
               let v = c.params["value"],
               let s = try? JSONDecoder().decode(StatusBar.self,
                                                 from: JSONEncoder().encode(v)) {
                status = s
            }

        case "history.update":
            staleList = (c.params["stale"]?.arrayValue ?? []).map {
                "\($0["id"]?.stringValue ?? "?") — \($0["ly_do"]?.stringValue ?? "")"
            }

        case "surface.lock", "surface.unlock", "surface.highlight", "explain.show":
            break

        default:
            // E3.2 §5 — không giấu thất bại: lệnh lạ phải hiện ra, không bỏ qua im lặng.
            notices.append(.init(level: "warn",
                                 text: "Giao diện chưa biết lệnh “\(c.method)” của lõi. "
                                     + "Bản giao diện này cũ hơn lõi.",
                                 code: "E_UI_UNKNOWN_CMD"))
        }
    }

    // MARK: - Tiện

    var theDangCho: [Card] { cards.filter { !$0.resolved } }

    var surfaceOrder: [(key: String, code: String, title: String)] { [
        ("requirements", "A2", "Yêu cầu & Giải pháp"),
        ("documents", "A3", "Tài liệu & Nguồn"),
        ("knowledge", "A4", "Tri thức mạch"),
        ("design", "A5", "Thiết kế"),
        ("tools", "A6", "Công cụ"),
        ("code", "A7", "Mã nguồn"),
        ("simulation", "A8", "Mô phỏng"),
        ("hardware", "A9", "Mạch thật"),
        ("journal", "A10", "Nhật ký"),
        ("history", "A11", "Lịch sử"),
        ("project", "A14", "Dự án & Bộ nhớ"),
    ] }
}
