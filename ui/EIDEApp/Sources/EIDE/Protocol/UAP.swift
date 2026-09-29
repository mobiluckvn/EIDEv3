import Foundation

// EIDE-MDD-40 Phần D — Giao thức điều khiển giao diện UAP v1.1.
//
// Sáu bất biến:
//   I1  Một cửa vào: lõi chỉ nhận thao tác người qua console.act/HumanAct.
//   I2  Một dòng hội thoại: mỗi HumanAct → đúng một dòng "[Bạn] …".
//   I3  Giao diện không quyết: chỉ render SurfaceModel/Card do lõi gửi.
//   I4  Lõi không biết giao diện: chỉ thấy HumanAct (ý chí + xuất xứ).
//   I5  Có thứ tự (seq), không trùng (id), khôi phục được (resume seq).
//   I6  Cổng là thẻ riêng: chỉ HumanAct kind=decide với gate_id đang chờ mới mở cổng.

// MARK: - HumanAct (13 loại)

/// Ý chí của người. Đây là **thứ duy nhất** giao diện được phép gửi vào lõi.
struct HumanAct: Codable {
    enum Kind: String, Codable, CaseIterable {
        case say, choose, decide, confirm, edit, upload, stop, undo, resume, attend, set
        case snapshot, branch
    }

    struct Target: Codable {
        var type: String
        var id: String
        var version: String?
    }

    /// Xuất xứ: cái chạm này đến từ đâu trên bề mặt nào.
    /// `block` dùng mã khối của `ui_model.py` (A2.1, A4.2…) để ma trận ánh xạ
    /// yêu cầu ↔ giao diện còn đúng khi mã chạy.
    struct Origin: Codable {
        var surface: String
        var block: String?
        var row: String?
        var selection: String?
    }

    var kind: Kind
    var text: String = ""
    var target: Target?
    var data: [String: JSONValue] = [:]
    var origin: Origin
    var note: String?

    init(kind: Kind, text: String = "", target: Target? = nil,
         data: [String: JSONValue] = [:], origin: Origin, note: String? = nil) {
        self.kind = kind
        self.text = text
        self.target = target
        self.data = data
        self.origin = origin
        self.note = note
    }

    /// Giải mã khoan dung: thiếu `data`, `origin`, `text` thì dùng mặc định.
    ///
    /// Bộ giải mã Swift tự sinh **không** dùng giá trị mặc định của thuộc tính — thiếu
    /// một khoá là hỏng cả thông điệp. Lõi Python (`HumanAct.from_dict`) vốn khoan dung
    /// đúng ở những khoá này, và hai đầu của một giao thức không được khác nhau về việc
    /// cái gì là bắt buộc. Bỏ qua chuyện này đã làm toàn bộ bài kiểm giao diện im lặng
    /// hỏng: mọi câu gõ vào đều bị vứt với một dòng "HumanAct không hợp lệ".
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        kind = try c.decode(Kind.self, forKey: .kind)
        text = (try? c.decode(String.self, forKey: .text)) ?? ""
        target = try? c.decode(Target.self, forKey: .target)
        data = (try? c.decode([String: JSONValue].self, forKey: .data)) ?? [:]
        origin = (try? c.decode(Origin.self, forKey: .origin))
            ?? Origin(surface: "console")
        note = try? c.decode(String.self, forKey: .note)
    }

    static func say(_ text: String) -> HumanAct {
        HumanAct(kind: .say, text: text, origin: .init(surface: "console"))
    }

    /// I6 — chỉ đường này mở được một cổng. Một chữ "có" gõ trong ô nhập thì không.
    static func decide(gateID: String, approved: Bool, choice: String? = nil,
                       note: String? = nil) -> HumanAct {
        var data: [String: JSONValue] = [
            "gate_id": .string(gateID), "approved": .bool(approved)
        ]
        if let choice { data["choice"] = .string(choice) }
        return HumanAct(kind: .decide, data: data,
                        origin: .init(surface: "console"), note: note)
    }

    static func choose(cardID: String, answers: [String: String],
                       surface: String = "console") -> HumanAct {
        HumanAct(kind: .choose,
                 data: ["card_id": .string(cardID),
                        "answers": .object(answers.mapValues { .string($0) })],
                 origin: .init(surface: surface))
    }

    /// Người kéo–thả hoặc chọn tệp để đưa vào cho tác tử đọc.
    ///
    /// `files` là đường dẫn TƯƠNG ĐỐI so với gốc dự án. Tuyệt đối thì vô dụng với tác tử —
    /// hộp cát của nó là thư mục dự án, nên một tệp ở `~/Downloads` với nó là không tồn tại.
    static func upload(files: [String]) -> HumanAct {
        HumanAct(kind: .upload,
                 data: ["files": .array(files.map { .string($0) })],
                 origin: .init(surface: "console"))
    }

    static func stopNow() -> HumanAct {
        HumanAct(kind: .stop, text: "dừng", origin: .init(surface: "console"))
    }

    static func attend(surface: String, block: String? = nil) -> HumanAct {
        HumanAct(kind: .attend, origin: .init(surface: surface, block: block))
    }
}

// MARK: - UICommand (16 lệnh)

/// Lệnh lõi gửi cho giao diện. Giao diện **chỉ** làm những gì có trong 16 lệnh này.
struct UICommand {
    let method: String
    let params: [String: JSONValue]
    let seq: Int

    var paramsValue: JSONValue { .object(params) }
}

// MARK: - SurfaceModel

/// Một bề mặt (tab) do lõi vẽ.
struct SurfaceModel: Codable, Identifiable {
    var surface: String
    var code: String          // mã vùng trong ui_model.py: A2, A4, A10…
    var title: String
    var blocks: [SurfaceBlock]

    var id: String { surface }
}

/// Một khối trên bề mặt. Phần khung có kiểu chặt; phần ruột giữ dạng động (xem JSONValue).
struct SurfaceBlock: Codable, Identifiable {
    var id: String
    var code: String
    var title: String
    var type: String          // kv | table | timeline | list | sections | text | code | empty
    var summary: String?
    var stale: [String]?
    var payload: [String: JSONValue] = [:]

    private enum Known: String, CodingKey {
        case id, code, title, type, summary, stale
    }

    private struct Any_: CodingKey {
        var stringValue: String
        var intValue: Int? { nil }
        init?(stringValue: String) { self.stringValue = stringValue }
        init?(intValue: Int) { nil }
    }

    init(from decoder: Decoder) throws {
        let k = try decoder.container(keyedBy: Known.self)
        id = try k.decode(String.self, forKey: .id)
        code = (try? k.decode(String.self, forKey: .code)) ?? id
        title = (try? k.decode(String.self, forKey: .title)) ?? ""
        type = (try? k.decode(String.self, forKey: .type)) ?? "text"
        summary = try? k.decode(String.self, forKey: .summary)
        stale = try? k.decode([String].self, forKey: .stale)

        // Mọi khoá còn lại giữ nguyên — bộ render đọc theo loại khối.
        let all = try decoder.container(keyedBy: Any_.self)
        let knownKeys: Set<String> = ["id", "code", "title", "type", "summary", "stale"]
        for key in all.allKeys where !knownKeys.contains(key.stringValue) {
            payload[key.stringValue] = try all.decode(JSONValue.self, forKey: key)
        }
    }

    func encode(to encoder: Encoder) throws {
        var k = encoder.container(keyedBy: Known.self)
        try k.encode(id, forKey: .id)
        try k.encode(code, forKey: .code)
        try k.encode(title, forKey: .title)
        try k.encode(type, forKey: .type)
        try k.encodeIfPresent(summary, forKey: .summary)
    }

    func str(_ key: String) -> String? { payload[key]?.stringValue }
    func arr(_ key: String) -> [JSONValue] { payload[key]?.arrayValue ?? [] }
}

// MARK: - Thẻ (Card)

/// Thẻ trong Console: thẻ làm rõ (clarify) hoặc thẻ cổng (gate).
struct Card: Identifiable {
    enum Kind: String { case clarify, gate, plan, report, unknown }

    let id: String
    let kind: Kind
    let raw: [String: JSONValue]
    var resolved: Bool = false

    // Thẻ cổng
    var gate: String? { raw["gate"]?.stringValue }
    var gateID: String? { raw["gate_id"]?.stringValue }
    var title: String { raw["title"]?.stringValue ?? "" }
    var risk: String { raw["risk"]?.stringValue ?? "" }
    var neverAuto: Bool { raw["never_auto"]?.boolValue ?? false }
    var irreversible: Bool { raw["irreversible"]?.boolValue ?? false }
    var consequences: [String] { (raw["consequences_vi"]?.arrayValue ?? []).compactMap(\.stringValue) }
    var requireText: String? { raw["require_vi"]?.stringValue }
    var requireFields: [String] { (raw["require_fields"]?.arrayValue ?? []).compactMap(\.stringValue) }
    var options: [String] { (raw["options"]?.arrayValue ?? []).compactMap(\.stringValue) }

    // Thẻ làm rõ
    var intro: String? { raw["intro"]?.stringValue }
    var assumptionIfSkipped: String? { raw["assumption_if_skipped"]?.stringValue }
    var questions: [Question] {
        (raw["questions"]?.arrayValue ?? []).map(Question.init)
    }

    struct Question: Identifiable {
        let raw: JSONValue
        var id: String { raw["key"]?.stringValue ?? UUID().uuidString }
        var text: String { raw["question"]?.stringValue ?? "" }
        var why: String? { raw["why"]?.stringValue }
        var prefill: String? { raw["prefill"]?.stringValue }
        var required: Bool { raw["required"]?.boolValue ?? false }
        var choices: [String] { (raw["choices"]?.arrayValue ?? []).compactMap(\.stringValue) }
        init(_ raw: JSONValue) { self.raw = raw }
    }

    init(id: String, raw: [String: JSONValue]) {
        self.id = id
        self.raw = raw
        self.kind = Kind(rawValue: raw["type"]?.stringValue ?? "") ?? .unknown
    }
}

// MARK: - Thanh trạng thái (§E7)

struct StatusBar: Codable {
    var du_an: String = ""
    var nhanh: String = "main"
    var chip: String = "chưa ghim"
    var isa: String?
    var fact: [String: Int] = [:]
    var chang: String = ""
    var snapshot: String?
    var khoang_cach_snapshot: Int = 0
    var stale: Int = 0
    var tu_chu: String = "A3"
    var mo_hinh: String = ""
    var ngan_sach: Budget = .init()
    var ngu_canh: NguCanh = .init()

    struct Budget: Codable {
        var tool: Int = 40
        var giay: Double = 300
        var da_dung_tool: Int = 0
        var da_dung_giay: Double = 0
    }

    /// Đồng hồ ngữ cảnh — EIDE-MEM-42 §4, khối A14.6.
    ///
    /// Người nhìn thanh này để biết vì sao tác tử "quên": không phải nó kém trí nhớ,
    /// mà là một khối cụ thể đã chạm trần. Không có bảng này thì "ngữ cảnh đầy" là
    /// một lời giải thích không ai kiểm được.
    struct NguCanh: Codable {
        var khoi: [Khoi] = []
        var tong: Int = 0
        var cua_so: Int = 0
        var ty_le: Double = 0
        var muc: String = "C0"          // C0…C4 theo bốn ngưỡng §4.2
        var kha_dung: Int = 0

        struct Khoi: Codable {
            var ten: String = ""
            var token: Int = 0
            var tran: Int?
            var vuot: Bool = false
        }

        var phanTram: Int { Int((ty_le * 100).rounded()) }
    }
}

// MARK: - Dòng transcript

struct TranscriptLine: Identifiable {
    enum Role: String { case human, agent, system }
    let id = UUID()
    let role: Role
    var text: String
    var card: Card?
    let at = Date()
}
