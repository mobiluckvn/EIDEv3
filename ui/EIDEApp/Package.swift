// swift-tools-version: 6.0
import PackageDescription

// Giao diện EIDE v3 — EIDE-MDD-40 Phần D & E7.
//
// Giao diện là CHI của tác tử (§D): nó không quyết gì, chỉ render SurfaceModel/Card do
// lõi gửi (I3), và gói mọi cái chạm của người thành HumanAct đi qua đúng một cửa
// `console.act` (I1).
//
// Lõi chạy như tiến trình con, nói JSON-RPC 2.0 trên stdio với khung Content-Length.
// Không mở cổng mạng nào: EIDE là ứng dụng một người trên máy cá nhân (§A2).

let package = Package(
    name: "EIDE",
    platforms: [.macOS(.v14)],
    targets: [
        .executableTarget(
            name: "EIDE",
            path: "Sources/EIDE",
            swiftSettings: [.swiftLanguageMode(.v5)]
        )
    ]
)
