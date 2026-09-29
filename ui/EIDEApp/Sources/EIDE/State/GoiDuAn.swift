import Foundation

/// Nhập một gói dự án `.zip` — gọi lõi Python, không tự giải nén.
///
/// Vì sao không dùng `unzip` của hệ điều hành cho nhanh: việc nhập **phải kiểm sổ cái** trước
/// khi nói "xong". Một gói hỏng hoặc bị sửa mà giải nén im lặng sẽ mở ra như bình thường, và
/// chỉ lộ ra ở một lúc nào đó rất xa — lúc người dùng đang tin vào một lịch sử không còn
/// nguyên vẹn. Phép kiểm chuỗi hash nằm ở `eide.goi_du_an`, nên gọi đúng nó.
///
/// Đây cũng là chỗ duy nhất giao diện chạy lõi mà KHÔNG qua `console.act`, và có lý do: chưa
/// có dự án nào đang mở thì chưa có lõi nào đang chạy để mà gửi `HumanAct` vào.
enum GoiDuAn {
    enum KetQua {
        case dat(String)
        case hong(String)
    }

    static func nhap(goi: URL, den: URL, python: URL, repo: URL) -> KetQua {
        let ma = """
        import json, sys
        sys.path.insert(0, sys.argv[1] + "/src")
        from eide.goi_du_an import nhap
        k = nhap(sys.argv[2], sys.argv[3])
        print(json.dumps({"dat": k.dat, "so_tep": k.so_tep,
                          "so_cai": k.so_cai_toan_ven, "noi": k.so_cai_noi,
                          "vi_sao": k.vi_sao_khong_dat}, ensure_ascii=False))
        """
        let p = Process()
        p.executableURL = python
        p.arguments = ["-c", ma, repo.path, goi.path, den.path]
        let ra = Pipe()
        p.standardOutput = ra
        p.standardError = Pipe()
        do { try p.run() } catch {
            return .hong("Không chạy được lõi: \(error.localizedDescription)")
        }
        let d = ra.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        guard let o = try? JSONSerialization.jsonObject(with: d) as? [String: Any] else {
            return .hong("Lõi không trả lời được — gói có thể hỏng.")
        }
        if (o["dat"] as? Bool) != true {
            return .hong((o["vi_sao"] as? String) ?? "Không nhập được gói.")
        }
        let n = (o["so_tep"] as? Int) ?? 0
        let soCai = (o["noi"] as? String) ?? ""
        return .dat("Đã nhập \(n) tệp vào \(den.lastPathComponent). \(soCai)")
    }
}
