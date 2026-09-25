import Foundation

/// Cầu nối tới lõi EIDE — JSON-RPC 2.0 trên stdio, khung Content-Length.
///
/// Lõi chạy như **tiến trình con**: vòng đời của nó gắn với app, không có cổng mạng
/// nào mở ra, không có gì để ai khác kết nối vào. §A2 nói EIDE là ứng dụng một người
/// trên máy cá nhân, và cách chạy này là cách rẻ nhất để điều đó đúng theo nghĩa đen.
///
/// Lớp này **không biết gì về giao diện** và cũng không biết gì về nghiệp vụ. Nó chỉ:
///   - gửi `console.act` khi người làm gì đó (I1),
///   - nhận UICommand và chuyển tiếp đúng thứ tự (I5),
///   - phát hiện lõi chết và nói ra (không im lặng treo).
final class CoreClient {

    struct Config {
        var python: URL
        var repoRoot: URL
        var projectDir: URL
        var autonomy: String = "A3"
    }

    enum CoreError: LocalizedError {
        case notRunning
        case rpc(code: Int, message: String)
        case decode(String)
        case launch(String)

        var errorDescription: String? {
            switch self {
            case .notRunning:            return "Lõi chưa chạy."
            case .rpc(let c, let m):      return "Lõi báo lỗi \(c): \(m)"
            case .decode(let d):          return "Không đọc được trả lời của lõi: \(d)"
            case .launch(let d):          return "Không khởi động được lõi: \(d)"
            }
        }
    }

    // Lõi gửi gì thì gọi hai cái này. Chạy trên hàng đợi chính.
    var onCommand: ((UICommand) -> Void)?
    var onStderr: ((String) -> Void)?
    var onExit: ((Int32) -> Void)?

    private var process: Process?
    private var stdin: FileHandle?
    private let queue = DispatchQueue(label: "eide.core.io")
    private var buffer = Data()
    private var nextID = 0
    private var waiting: [Int: CheckedContinuation<JSONValue, Error>] = [:]
    private let lock = NSLock()

    var isRunning: Bool { process?.isRunning ?? false }

    // MARK: - Vòng đời

    func start(_ cfg: Config) throws {
        let p = Process()
        p.executableURL = cfg.python
        p.arguments = ["-m", "eide",
                       "--du-an", cfg.projectDir.path,
                       "--muc-tu-chu", cfg.autonomy,
                       "--stdio"]
        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = cfg.repoRoot.appendingPathComponent("src").path
        env["PYTHONUNBUFFERED"] = "1"
        p.environment = env
        p.currentDirectoryURL = cfg.repoRoot

        let inPipe = Pipe(), outPipe = Pipe(), errPipe = Pipe()
        p.standardInput = inPipe
        p.standardOutput = outPipe
        p.standardError = errPipe

        outPipe.fileHandleForReading.readabilityHandler = { [weak self] h in
            let d = h.availableData
            guard !d.isEmpty else { return }
            self?.queue.async { self?.feed(d) }
        }
        errPipe.fileHandleForReading.readabilityHandler = { [weak self] h in
            let d = h.availableData
            guard !d.isEmpty, let s = String(data: d, encoding: .utf8) else { return }
            DispatchQueue.main.async { self?.onStderr?(s) }
        }
        p.terminationHandler = { [weak self] proc in
            // Lõi chết giữa chừng: mọi lời gọi đang chờ phải được đánh thức và
            // báo đúng lý do, chứ không treo mãi (UC19 — "không mất dữ liệu,
            // người dùng biết chính xác chuyện gì đã xảy ra").
            self?.failAllWaiting(CoreError.launch("Lõi đã thoát với mã \(proc.terminationStatus)"))
            DispatchQueue.main.async { self?.onExit?(proc.terminationStatus) }
        }

        do { try p.run() } catch { throw CoreError.launch(error.localizedDescription) }
        process = p
        stdin = inPipe.fileHandleForWriting
    }

    func stop() {
        process?.terminationHandler = nil
        process?.terminate()
        process = nil
        stdin = nil
        failAllWaiting(CoreError.notRunning)
    }

    // MARK: - Gọi

    @discardableResult
    func call(_ method: String, _ params: [String: JSONValue] = [:]) async throws -> JSONValue {
        guard isRunning, let stdin else { throw CoreError.notRunning }
        let id: Int = {
            lock.lock(); defer { lock.unlock() }
            nextID += 1
            return nextID
        }()

        let body: [String: JSONValue] = [
            "jsonrpc": .string("2.0"),
            "id": .number(Double(id)),
            "method": .string(method),
            "params": .object(params)
        ]
        let data = try JSONEncoder().encode(JSONValue.object(body))

        return try await withCheckedThrowingContinuation { cont in
            lock.lock(); waiting[id] = cont; lock.unlock()
            queue.async {
                var frame = Data("Content-Length: \(data.count)\r\n\r\n".utf8)
                frame.append(data)
                do { try stdin.write(contentsOf: frame) }
                catch {
                    self.lock.lock(); let c = self.waiting.removeValue(forKey: id); self.lock.unlock()
                    c?.resume(throwing: CoreError.notRunning)
                }
            }
        }
    }

    /// I1 — **cửa duy nhất** cho ý chí của người.
    @discardableResult
    func send(_ act: HumanAct) async throws -> JSONValue {
        let enc = JSONEncoder()
        let data = try enc.encode(act)
        let value = try JSONDecoder().decode(JSONValue.self, from: data)
        return try await call("console.act", ["act": value])
    }

    // MARK: - Đọc khung

    private func feed(_ chunk: Data) {
        buffer.append(chunk)
        while let frame = takeFrame() { handle(frame) }
    }

    /// Tách một khung `Content-Length: N\r\n\r\n<N byte>`.
    private func takeFrame() -> Data? {
        let sep = Data("\r\n\r\n".utf8)
        guard let hdrEnd = buffer.range(of: sep) else { return nil }
        guard let header = String(data: buffer[buffer.startIndex..<hdrEnd.lowerBound],
                                  encoding: .utf8) else {
            buffer.removeSubrange(buffer.startIndex..<hdrEnd.upperBound)
            return nil
        }
        var length = 0
        for line in header.split(whereSeparator: \.isNewline)
        where line.lowercased().hasPrefix("content-length:") {
            length = Int(line.dropFirst("content-length:".count)
                .trimmingCharacters(in: .whitespaces)) ?? 0
        }
        let bodyStart = hdrEnd.upperBound
        guard length > 0, buffer.count - buffer.distance(from: buffer.startIndex, to: bodyStart) >= length
        else { return nil }
        let bodyEnd = buffer.index(bodyStart, offsetBy: length)
        let body = buffer[bodyStart..<bodyEnd]
        buffer.removeSubrange(buffer.startIndex..<bodyEnd)
        return Data(body)
    }

    private func handle(_ data: Data) {
        guard let msg = try? JSONDecoder().decode(JSONValue.self, from: data) else {
            DispatchQueue.main.async { self.onStderr?("Khung JSON không đọc được\n") }
            return
        }

        // Thông báo (không id) = UICommand theo chiều lõi → giao diện.
        if let method = msg["method"]?.stringValue, msg["id"] == nil {
            let params = msg["params"]?.objectValue ?? [:]
            let seq = params["_seq"]?.intValue ?? 0
            let cmd = UICommand(method: method,
                                params: params.filter { $0.key != "_seq" },
                                seq: seq)
            DispatchQueue.main.async { self.onCommand?(cmd) }
            return
        }

        // Trả lời cho một lời gọi.
        guard let id = msg["id"]?.intValue else { return }
        lock.lock(); let cont = waiting.removeValue(forKey: id); lock.unlock()
        guard let cont else { return }
        if let err = msg["error"] {
            cont.resume(throwing: CoreError.rpc(
                code: err["code"]?.intValue ?? -1,
                message: err["message"]?.stringValue ?? "không rõ"))
        } else {
            cont.resume(returning: msg["result"] ?? .null)
        }
    }

    private func failAllWaiting(_ error: Error) {
        lock.lock()
        let all = waiting
        waiting.removeAll()
        lock.unlock()
        for (_, c) in all { c.resume(throwing: error) }
    }
}
