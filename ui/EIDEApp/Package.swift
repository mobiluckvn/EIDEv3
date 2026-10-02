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
        ),
        // Bộ kiểm cho phần LOGIC THUẦN của giao diện.
        //
        // Vì sao phải có: ba việc anh Công nêu về giao diện — dấu `**` lọt ra màn, bảng dựng
        // sai, công thức chưa đổi ký hiệu — đều kết thúc bằng cùng một câu trong sổ việc:
        // *"không con số nào bắt được chuyện này, phải nhìn màn hình"*. Câu ấy đúng với BỀ
        // RỘNG CỘT và màu sắc, nhưng KHÔNG đúng với phần tách khối, tách ô, đổi ký hiệu —
        // những phần ấy là hàm thuần, vào chuỗi ra chuỗi, và kiểm được bằng số.
        //
        // Không có mục tiêu này thì mọi lần sửa bộ dựng Markdown đều phải mở app ra nhìn, và
        // một lỗi cũ quay lại sẽ không ai biết.
        .testTarget(
            name: "EIDETests",
            dependencies: ["EIDE"],
            path: "Tests/EIDETests",
            swiftSettings: [.swiftLanguageMode(.v5)]
        )
    ]
)
