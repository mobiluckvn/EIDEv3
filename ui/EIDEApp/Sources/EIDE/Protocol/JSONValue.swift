import Foundation

/// Giá trị JSON động.
///
/// Vì sao cần: I3 nói giao diện chỉ *render* thứ lõi gửi. Nếu Swift phải khai báo một
/// `struct` cho từng loại khối thì mỗi lần lõi thêm một loại khối, giao diện lại phải
/// sửa và biên dịch lại — và trong lúc chờ, nó sẽ **bỏ qua trong im lặng** thứ lõi gửi.
/// Đó đúng là kiểu hỏng mà E3.2 §5 cấm.
///
/// Nên: phần khung (surface, code, title, blocks) có kiểu chặt; phần ruột của khối giữ
/// dạng động, và bộ render nào không hiểu một loại khối thì **nói ra** chứ không giấu.
enum JSONValue: Codable, Hashable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let v = try? c.decode(Bool.self) { self = .bool(v) }
        else if let v = try? c.decode(Double.self) { self = .number(v) }
        else if let v = try? c.decode(String.self) { self = .string(v) }
        else if let v = try? c.decode([JSONValue].self) { self = .array(v) }
        else if let v = try? c.decode([String: JSONValue].self) { self = .object(v) }
        else {
            throw DecodingError.dataCorruptedError(in: c, debugDescription: "JSON lạ")
        }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .string(let v): try c.encode(v)
        case .number(let v): try c.encode(v)
        case .bool(let v):   try c.encode(v)
        case .object(let v): try c.encode(v)
        case .array(let v):  try c.encode(v)
        case .null:          try c.encodeNil()
        }
    }

    // MARK: - Đọc

    subscript(key: String) -> JSONValue? {
        if case .object(let o) = self { return o[key] }
        return nil
    }

    var stringValue: String? {
        switch self {
        case .string(let s): return s
        case .number(let n): return n == n.rounded() ? String(Int(n)) : String(n)
        case .bool(let b):   return b ? "có" : "không"
        case .null:          return nil
        default:             return nil
        }
    }

    var intValue: Int? {
        if case .number(let n) = self { return Int(n) }
        if case .string(let s) = self { return Int(s) }
        return nil
    }

    var boolValue: Bool? {
        if case .bool(let b) = self { return b }
        return nil
    }

    var arrayValue: [JSONValue] {
        if case .array(let a) = self { return a }
        return []
    }

    var objectValue: [String: JSONValue] {
        if case .object(let o) = self { return o }
        return [:]
    }

    /// Dạng chữ để hiện trong ô bảng: mọi kiểu đều có chữ, không bao giờ là ô trống câm.
    var display: String {
        switch self {
        case .null: return "—"
        case .array(let a): return a.map(\.display).joined(separator: ", ")
        case .object(let o):
            return o.map { "\($0.key): \($0.value.display)" }.sorted().joined(separator: " · ")
        default: return stringValue ?? "—"
        }
    }

    static func from(_ any: Any) -> JSONValue {
        switch any {
        case let v as String: return .string(v)
        case let v as Bool:   return .bool(v)
        case let v as Int:    return .number(Double(v))
        case let v as Double: return .number(v)
        case let v as [Any]:  return .array(v.map(JSONValue.from))
        case let v as [String: Any]: return .object(v.mapValues(JSONValue.from))
        default: return .null
        }
    }
}
