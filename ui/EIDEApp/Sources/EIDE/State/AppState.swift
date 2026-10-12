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

    // Lịch sử: thứ ba nút lùi cần, do lõi khai qua `history.update` (EIDE-EDIT-47 DEV-365).
    //
    // Trước gói này ba thứ dưới đây **không tồn tại phía Swift**, nên menu "Về bản…" và
    // "Nhánh ▸" không có gì để vẽ, và `grep "kind: .snapshot"` trong `Views/` = 0 — cả phần
    // `history.py` lo việc lùi (snapshot, nhánh, khôi phục) không có đường nào đi tới từ
    // giao diện.
    @Published var snapshots: [JSONValue] = []
    @Published var nhanh: [String] = []
    @Published var nhanhHienTai: String = "main"

    /// Lần lưu vừa rồi của người — thanh "Đã ghi `cs-12` · **Hoàn tác**", sống 30 giây.
    ///
    /// README §3.3 gọi đây là "gỡ 30 giây", cách lùi thứ nhất trong ba cách. Lõi KHAI nó ra
    /// (`history.update.vua_ghi`) chứ không để giao diện suy từ danh sách changeset: cùng
    /// lệnh ấy còn được phát cuối mỗi lượt với 40 changeset, nên "cái nào người vừa lưu"
    /// không đọc được từ danh sách.
    @Published var toastLuu: ToastLuu?

    /// Mã phiên sửa đang mở (`es-<n>`) — gom nhiều lần lưu của MỘT lần ngồi sửa.
    ///
    /// Có nó thì nút Hoàn tác trên thanh toast lùi *cái người vừa làm*, không phải riêng
    /// changeset cuối: sửa bốn ô trong một biểu mẫu là bốn lần lưu.
    @Published var sessionSua: String?

    /// Khối diff lõi đã gửi, theo `diff_id` — lệnh thứ 17 của UAP (EIDE-EDIT-47 DEV-366).
    ///
    /// Giữ riêng chứ không nhét vào `Card`: một khối diff có thể gắn vào thẻ xung đột, gắn
    /// vào thẻ cổng, hoặc không gắn vào đâu cả (mở ở một tấm riêng). Và nó tới bằng một
    /// lệnh RIÊNG, sau `console.post` dựng thẻ — nên lúc thẻ tới thì diff chưa có.
    @Published var diffs: [String: JSONValue] = [:]

    /// HumanAct đã gửi, 20 cái gần nhất.
    ///
    /// Có nó vì phần lớn gói này là **những cái nút**, và câu cần đo về một cái nút là
    /// *"nó gửi đi cái gì"*. Không có chỗ này thì câu ấy chỉ trả lời được bằng cách mở app
    /// ra bấm — tức là không trả lời lại được ở lần sau. Lỗi đã trả giá thật: nút "Khôi
    /// phục" ở tab Lịch sử gửi một câu `say` cho mô hình thay vì một `undo`, và mọi ca đo
    /// vẫn xanh vì không ca nào hỏi nút ấy gửi gì.
    @Published var daGui: [HumanAct] = []

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
        /// Lượt này để lại bao nhiêu thay đổi lùi được — LÕI đếm (`run.update.so_thay_doi`).
        var soThayDoi: Int = 0
        /// Nút lõi cho phép ở cuối lượt. Giao diện không tự thêm nút nào.
        var buttons: [String] = []
    }

    /// Lần lưu vừa rồi của người, kèm lúc nó xảy ra để thanh toast tự hết.
    struct ToastLuu: Equatable {
        var changeset: String
        var tomTat: String
        var session: String? = nil
        var soTrongPhien: Int = 1
        var hoanTacDuoc: Bool = true
        var luc: Date = Date()

        /// Hoàn tác cái gì: cả lượt ngồi sửa nếu có mã phiên, không thì riêng changeset ấy.
        var target: HumanAct.Target {
            if let s = session, !s.isEmpty {
                return .init(type: "session", id: s)
            }
            return .init(type: "changeset", id: changeset)
        }

        var nhan: String {
            guard session != nil, soTrongPhien > 1 else { return "Hoàn tác" }
            return "Hoàn tác cả \(soTrongPhien) thay đổi vừa sửa"
        }
    }

    struct Notice: Identifiable {
        let id = UUID()
        let level: String
        let text: String
        let code: String?
        /// Cảnh báo giống hệt nổ bao nhiêu lần. Hiện dạng `×3` thay vì ba thẻ.
        var soLan: Int = 1
        /// Lúc nổ lần đầu — dùng cho việc tự hết của mức `info`.
        var luc: Date = Date()

        /// Hai cảnh báo là MỘT khi cùng mức, cùng chữ, cùng mã.
        func giongVoi(_ k: Notice) -> Bool {
            level == k.level && text == k.text && code == k.code
        }
    }

    /// Mức `info` tự hết sau bao lâu. Mức `warn` và `error` KHÔNG tự hết — người dùng phải
    /// thấy chúng, và việc bỏ đi là quyết định của họ.
    static let giayThongBaoInfo: TimeInterval = 25

    /// Thêm một cảnh báo, GỘP cái trùng thay vì xếp thêm một thẻ.
    ///
    /// Vì sao phải có hàm này thay vì `notices.append` khắp nơi: trong mã có **10 chỗ thêm**
    /// mà chỉ **1 chỗ xoá**, và chỗ xoá ấy là `doiDuAn()`. Nên suốt một phiên `notices` chỉ
    /// tăng, và cách duy nhất để nó rỗng lại là đổi sang dự án khác — điều không ai làm giữa
    /// lúc đang chạy việc. Chúng được vẽ sau transcript trong cùng cột, nên càng dồn thì
    /// càng đẩy hội thoại lên.
    ///
    /// Lại không có khâu gộp trùng: cùng một cảnh báo nổ mười lần thì hiện mười thẻ. Mà một
    /// cảnh báo nổ mười lần nói lên điều khác với mười cảnh báo khác nhau — số lần là thông
    /// tin, mười thẻ giống nhau thì không.
    func themThongBao(level: String, text: String, code: String? = nil) {
        donThongBaoHetHan()
        let moi = Notice(level: level, text: text, code: code)
        if let i = notices.lastIndex(where: { $0.giongVoi(moi) }) {
            notices[i].soLan += 1
            return
        }
        notices.append(moi)
    }

    /// Bỏ một thẻ — người dùng bấm dấu nhân.
    func boThongBao(_ id: UUID) {
        notices.removeAll { $0.id == id }
    }

    /// Dọn hết. Nút "Dọn" ở khu cảnh báo.
    func xoaHetThongBao() {
        notices.removeAll()
    }

    /// Bỏ các thẻ `info` đã quá hạn. Gọi mỗi lần thêm thẻ mới, nên không cần bộ đếm giờ.
    func donThongBaoHetHan() {
        let bay = Date()
        notices.removeAll { $0.level == "info"
            && bay.timeIntervalSince($0.luc) > Self.giayThongBaoInfo }
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

    /// Xuất dự án đang mở thành `.zip` — lớp App gắn vào, vì nó cần bảng chọn tệp.
    var xuatGoi: (() -> Void)?
    var nhapGoi: (() -> Void)?

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
            // Dọn sạch mọi thứ THUỘC VỀ dự án cũ, trước khi lõi mới nói câu đầu tiên.
            //
            // Không có chỗ này thì mở một dự án mới xong vẫn thấy nguyên hội thoại của dự án
            // trước — anh Công báo đúng chuyện đó. Và chat mới là phần dễ thấy nhất, chứ chưa
            // phải phần nguy nhất: `cards` giữ lại các **thẻ cổng đang chờ duyệt** của dự án
            // cũ. Bấm *Duyệt* trên một thẻ như vậy là gửi quyết định về một lõi đã chết, cho
            // một hiện vật ở một thư mục khác.
            //
            // Lõi tự dựng lại phần của nó khi mở (`<resume>` + `ui.sync`), nên xoá ở đây
            // không mất gì: cái gì thuộc dự án mới sẽ tới ngay sau.
            doiDuAn(duAn)
            try client.start(.init(python: python, repoRoot: repo, projectDir: duAn))
            let hello = try await client.call("hello", ["client": .object([
                "name": .string("EIDE.app"), "uap": .string("1.2")
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
            themThongBao(level: "warn", text: "Không vẽ lại được: \(error)",
                                 code: nil)
        }
    }

    func dong() {
        client.stop()
        connection = .chuaKetNoi
    }

    /// Xoá mọi trạng thái gắn với dự án cũ và ghim dự án mới.
    ///
    /// Danh sách này là **danh sách đầy đủ** những gì trong `AppState` thuộc về một dự án cụ
    /// thể. Thêm một `@Published` mới mà quên thêm vào đây thì nó sẽ rò từ dự án này sang dự
    /// án kia — nên có một ca kiểm đọc chính tệp này và đối chiếu hai danh sách.
    ///
    /// `draft` **không** bị xoá: đó là chữ người dùng tự gõ mà chưa gửi. Xoá nó là làm mất
    /// việc của người để cho gọn màn hình của máy. Nó nằm ngay trước mắt nên không ai gửi
    /// nhầm mà không thấy.
    ///
    /// `selectedSurface` cũng giữ: tab đang xem là thói quen của người, không phải dữ liệu
    /// của dự án.
    func doiDuAn(_ duAn: URL) {
        // Kênh kiểm thử trỏ vào `.eide/ui-test` của dự án CŨ và chạy một bộ đếm giờ 4 Hz.
        // `tat()` có sẵn từ đầu nhưng chưa nơi nào gọi, nên mỗi lần đổi dự án lại thêm một
        // bộ đếm giờ nữa — đổi năm lần là năm bộ cùng đọc một tệp.
        kenhKiemThu.tat()
        transcript.removeAll()
        surfaces.removeAll()
        cards.removeAll()
        notices.removeAll()
        staleList.removeAll()
        snapshots.removeAll()
        diffs.removeAll()
        nhanh.removeAll()
        nhanhHienTai = "main"
        toastLuu = nil
        sessionSua = nil
        daGui.removeAll()
        coreLog.removeAll()
        khungKhoi.removeAll()
        khoiChuaBietVe.removeAll()
        streaming.removeAll()
        status = StatusBar()
        run = nil
        busy = false
        duAnDir = duAn
    }

    /// Đưa tệp người dùng vừa kéo–thả (hoặc vừa chọn) vào dự án rồi báo cho tác tử.
    ///
    /// Chép vào trong dự án TRƯỚC khi báo: hộp cát của tác tử là thư mục dự án, nên một
    /// đường dẫn ở `~/Downloads` với nó là không tồn tại. Xem `ThemTaiLieu`.
    func themTaiLieu(_ nguon: [URL]) {
        guard let goc = duAnDir, connection.ok else { return }
        let kq = ThemTaiLieu.dua(nguon, vaoDuAn: goc)
        for l in kq.loi {
            themThongBao(level: "warn", text: "Không thêm được \(l)", code: nil)
        }
        guard !kq.duong.isEmpty else { return }
        if !kq.daChep.isEmpty {
            // Nói ra việc đã chép. Người kéo một tệp từ Desktop mà không biết nó vừa được
            // nhân bản vào dự án sẽ ngạc nhiên đúng lúc họ dọn thư mục.
            themThongBao(
                level: "info",
                text: "Đã chép vào \(ThemTaiLieu.THU_MUC)/: " + kq.daChep.joined(separator: ", ")
                    + " — tác tử chỉ đọc được tệp nằm trong thư mục dự án.",
                code: nil)
        }
        gui(.upload(files: kq.duong))
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
        daGui.append(act)
        if daGui.count > 20 { daGui.removeFirst(daGui.count - 20) }
        busy = true
        Task {
            do { _ = try await client.send(act) }
            catch {
                themThongBao(level: "error", text: error.localizedDescription, code: nil)
            }
            busy = false
        }
    }

    /// Khối diff gắn vào một thẻ (xung đột) hoặc một cổng. Lõi khai `gan_voi`, giao diện
    /// chỉ tra ngược — nó không tự gán diff cho thẻ nào.
    func diffGanVoi(cardID: String? = nil, gateID: String? = nil) -> JSONValue? {
        diffs.values.first { d in
            let g = d["gan_voi"]
            if let c = cardID, g?["card_id"]?.stringValue == c { return true }
            if let x = gateID, g?["gate_id"]?.stringValue == x { return true }
            return false
        }
    }

    // MARK: - Năm tầng lùi (EIDE-EDIT-47 DEV-365)
    //
    // Năm hàm dưới đây là CẢ phần nghiệp vụ của các nút lùi. Chúng nằm ở đây, không nằm
    // trong thân view, vì một hàm trong `AppState` thì ca kiểm gọi được — còn một closure
    // trong `Button { … }` thì chỉ kiểm được bằng cách mở app ra bấm.

    /// Ghi bản ưng ý. Trả `false` khi tên rỗng và **không gửi gì**.
    ///
    /// Tên rỗng bị chặn ở cả hai đầu: lõi cũng từ chối (`_nguoi_ghi_ban`). Chặn ở đây là để
    /// người không phải trả giá một vòng đi–về mới biết mình chưa đặt tên.
    @discardableResult
    func ghiBanUngY(ten: String, ghiChu: String = "") -> Bool {
        let t = ten.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return false }
        gui(HumanAct(kind: .snapshot,
                     data: ["name": .string(t), "note": .string(ghiChu)],
                     origin: .init(surface: "history")))
        return true
    }

    /// Về một bản ưng ý. `giuBanHienTai` = tên để giữ lại trạng thái đang bỏ dở (§E6.3).
    func veBanUngY(_ snapshotID: String, giuBanHienTai: String? = nil) {
        var data: [String: JSONValue] = ["mode": .string("restore_branch")]
        if let g = giuBanHienTai?.trimmingCharacters(in: .whitespacesAndNewlines), !g.isEmpty {
            data["giu_ban_hien_tai"] = .string(g)
        }
        gui(HumanAct(kind: .undo, target: .init(type: "snapshot", id: snapshotID),
                     data: data, origin: .init(surface: "history")))
        boToast()
    }

    /// Hỏi lõi "về bản này thì mất gì" — máy–máy, chỉ đọc, 0 token (xem `RPC_CHI_DOC`).
    func xemTruocKhoiPhuc(_ snapshotID: String) async -> JSONValue? {
        guard connection.ok else { return nil }
        do {
            return try await client.call("history.preview_restore",
                                         ["snapshot_id": .string(snapshotID)])
        } catch {
            themThongBao(level: "warn",
                         text: "Không xem trước được hậu quả khi về \(snapshotID): \(error). "
                             + "Chưa khôi phục gì cả.", code: nil)
            return nil
        }
    }

    /// Lùi cả lượt vừa xong.
    func luiCaLuot() {
        guard let r = run, r.soThayDoi > 0 else { return }
        gui(HumanAct(kind: .undo, target: .init(type: "run", id: r.id),
                     data: ["mode": .string("revert")], origin: .init(surface: "console")))
        boToast()
    }

    /// Hoàn tác lần lưu vừa rồi của người — nút trên thanh toast.
    func hoanTacVuaGhi() {
        guard let t = toastConHieuLuc, t.hoanTacDuoc else { return }
        gui(HumanAct(kind: .undo, target: t.target,
                     data: ["mode": .string("revert")], origin: .init(surface: "history")))
        boToast()
        dongPhienSua()
    }

    /// Bỏ thanh "vừa ghi" sau BẤT KỲ phép lùi nào.
    ///
    /// Thấy trên ảnh chụp của bộ `thu_nut_lui`: người lùi về một bản ưng ý xong, thanh
    /// "Đã ghi cs-0006 · Hoàn tác" vẫn nằm đó — mà cs-0006 chính là thay đổi phép khôi phục
    /// vừa cuốn đi. Nút ấy không hỏng (lõi vẫn lùi được, kèm cảnh báo chuỗi), nhưng nó MÔ TẢ
    /// SAI trạng thái: nó nói "anh vừa lưu cái này" trong khi cái ấy không còn ở đỉnh lịch sử.
    private func boToast() {
        toastLuu = nil
    }

    /// Tạo / chuyển / gộp nhánh. Trả `false` khi tên rỗng và **không gửi gì**.
    @discardableResult
    func thaoTacNhanh(_ viec: String, ten: String) -> Bool {
        let t = ten.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return false }
        gui(HumanAct(kind: .branch,
                     data: ["action": .string(viec), "name": .string(t)],
                     origin: .init(surface: "history")))
        return true
    }

    // MARK: - Thanh "Đã ghi … · Hoàn tác"

    /// Thanh toast sống bao lâu. README §3.3: "gỡ 30 giây".
    static let giayToast: TimeInterval = 30

    /// Thanh toast nếu còn hiệu lực. Hết 30 giây thì nó không còn là một cái nút nữa —
    /// và một cái nút bấm được mà không làm gì là thứ tệ nhất trong ba khả năng.
    var toastConHieuLuc: ToastLuu? {
        guard let t = toastLuu, Date().timeIntervalSince(t.luc) <= Self.giayToast else {
            return nil
        }
        return t
    }

    /// Bỏ thanh toast đã quá hạn. `ThanhVuaGhi` gọi mỗi giây trong lúc nó còn hiện — nên
    /// không có bộ đếm giờ nào chạy khi không có toast nào.
    func donToastHetHan() {
        if toastLuu != nil, toastConHieuLuc == nil { toastLuu = nil }
    }

    // MARK: - Phiên sửa

    /// Phiên sửa tự hết sau bấy nhiêu giây không ai gõ.
    static let giayPhienSua: TimeInterval = 120

    private var demPhienSua = 0
    /// Lần gõ/lưu gần nhất. Không `private` để ca kiểm dựng được tình huống "phiên đã nguội"
    /// mà không phải ngồi chờ hai phút.
    var lanChamPhienSua = Date.distantPast

    /// Mã phiên sửa để kèm vào `edit`. Mở trình soạn, hoặc lưu một ô, đều gọi hàm này.
    func moPhienSua() -> String {
        donPhienSuaHetHan()
        lanChamPhienSua = Date()
        if let s = sessionSua { return s }
        demPhienSua += 1
        let s = "es-\(demPhienSua)"
        sessionSua = s
        return s
    }

    /// Đóng trình soạn. Lần sửa sau là một lượt sửa khác, có mốc lùi riêng.
    func dongPhienSua() {
        sessionSua = nil
    }

    /// Bỏ phiên sửa đã nguội. Không có chỗ này thì hai lần sửa cách nhau cả tiếng vẫn bị
    /// gom vào một đơn vị hoàn tác, và nút Hoàn tác sẽ lùi nhiều hơn người tưởng.
    func donPhienSuaHetHan() {
        if Date().timeIntervalSince(lanChamPhienSua) > Self.giayPhienSua {
            sessionSua = nil
        }
    }

    func guiCauDangGo() {
        let t = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !t.isEmpty else { return }
        draft = ""
        gui(.say(t))
    }

    // MARK: - Nhận UICommand (16 lệnh)

    /// Nhận một UICommand từ lõi. Không `private`: bộ kiểm giao diện nạp lệnh qua đúng
    /// đường này, nên nó đo thứ app THẬT làm với lệnh của lõi, không đo một bản dựng riêng.
    func apply(_ c: UICommand) {
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
                assumptions: (c.params["assumptions"]?.arrayValue ?? []).compactMap(\.stringValue),
                soThayDoi: c.params["so_thay_doi"]?.intValue ?? 0,
                buttons: (c.params["buttons"]?.arrayValue ?? []).compactMap(\.stringValue))

        case "notice":
            themThongBao(level: c.params["level"]?.stringValue ?? "info",
                                 text: c.params["text"]?.stringValue ?? "",
                                 code: c.params["code"]?.stringValue)

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
            // Danh sách bản ưng ý và nhánh: chỉ GHI ĐÈ khi lõi gửi kèm. Lệnh này còn được
            // phát sau mỗi lần người sửa, lúc ấy nó chỉ mang một changeset — xoá hai danh
            // sách kia theo thì menu "Về bản…" sẽ rỗng đi ngay sau khi người sửa một ô.
            if let s = c.params["snapshots"]?.arrayValue, !s.isEmpty { snapshots = s }
            if let n = c.params["nhanh"], !n.objectValue.isEmpty {
                nhanh = (n["danh_sach"]?.arrayValue ?? []).compactMap(\.stringValue)
                nhanhHienTai = n["hien_tai"]?.stringValue ?? nhanhHienTai
            }
            if let v = c.params["vua_ghi"], !v.objectValue.isEmpty,
               let cs = v["changeset"]?.stringValue {
                toastLuu = ToastLuu(
                    changeset: cs,
                    tomTat: v["tom_tat"]?.stringValue ?? "sửa",
                    session: v["session"]?.stringValue,
                    soTrongPhien: v["so_trong_phien"]?.intValue ?? 1,
                    hoanTacDuoc: v["hoan_tac_duoc"]?.boolValue ?? true)
            }

        case "diff.show":
            if let id = c.params["diff_id"]?.stringValue {
                diffs[id] = .object(c.params)
            }

        case "surface.lock", "surface.unlock", "surface.highlight", "explain.show":
            break

        default:
            // E3.2 §5 — không giấu thất bại: lệnh lạ phải hiện ra, không bỏ qua im lặng.
            themThongBao(level: "warn",
                                 text: "Giao diện chưa biết lệnh “\(c.method)” của lõi. "
                                     + "Bản giao diện này cũ hơn lõi.",
                                 code: "E_UI_UNKNOWN_CMD")
        }
    }

    // MARK: - Tiện

    var theDangCho: [Card] { cards.filter { !$0.resolved } }

    /// Thứ tự tab trên thanh.
    ///
    /// Danh sách này là một HỢP ĐỒNG với `src/eide/surfaces.py::SURFACES`, và nó viết cứng ở
    /// hai phía bằng hai ngôn ngữ. Thiếu một dòng ở đây thì lõi vẫn gửi `surface.set` cho bề
    /// mặt ấy, mà giao diện **không có tab nào nhận** — cả bề mặt trở thành vô hình, không
    /// lỗi nào kêu lên.
    ///
    /// Đã xảy ra thật 11/10/2026: thêm bề mặt `screen` (A15) ở phía Python, bộ kiểm Python
    /// xanh, và anh Công mở app lên thì **không thấy tab Màn hình**. Tệ hơn: tôi đã viết vào
    /// chú thích của `TabBar` rằng *"`surfaceOrder` do lõi cấp, nên thanh này tự dài ra"* —
    /// một câu tôi viết mà không mở tệp này ra kiểm.
    ///
    /// `tests/test_thiet_ke_ui.py::test_thanh_tab_Swift_KHOP_danh_sach_be_mat_cua_loi` đọc
    /// chính tệp này và so với `SURFACES`, nên lần sau thiếu một dòng sẽ ĐỎ ở bộ kiểm.
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
        ("screen", "A15", "Màn hình"),
    ] }
}
