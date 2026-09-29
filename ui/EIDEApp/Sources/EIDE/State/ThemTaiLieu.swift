import AppKit
import Foundation

/// Đưa tệp của người dùng vào cho tác tử đọc — kéo–thả hoặc chọn bằng bảng tệp.
///
/// ## Vì sao việc này không phải "gửi đường dẫn cho tác tử"
///
/// Hộp cát của tác tử là **thư mục dự án**. Một tệp nằm ở `~/Downloads` với nó là không tồn
/// tại: `fs.read` từ chối, `doc.load` từ chối. Nên đưa tài liệu vào là **chép tệp vào trong
/// dự án** rồi mới nói tên, không phải đưa một đường dẫn tuyệt đối rồi mong nó đọc được.
///
/// Trước khi có tệp này, cách duy nhất để đưa một datasheet vào là mở Finder, chép tay, rồi
/// gõ bảo tác tử. Mà cả sản phẩm dựng trên *"mọi con số truy về datasheet"* — nên chỗ **đưa
/// datasheet vào** không nên là chỗ khó nhất.
///
/// ## Ba điều nó cố ý KHÔNG làm
///
/// * **Không tự nạp vào kho.** Chép xong là báo cho tác tử, để nó hỏi lại "nạp vào kho
///   không" — `doc.load` là R2 và sinh hiện vật, không phải việc một cú kéo–thả tự quyết.
/// * **Không ghi đè.** Trùng tên thì thêm hậu tố `-2`, `-3`. Người kéo nhầm một tệp cùng tên
///   mà mất bản cũ thì cú kéo ấy đắt hơn nhiều so với một tệp thừa.
/// * **Không đi vòng qua I1.** Kết quả là một `HumanAct` đi qua `console.act` như mọi thứ
///   khác — kéo–thả thay NGÓN TAY, không thay giao thức.
@MainActor
enum ThemTaiLieu {
    /// Thư mục nhận tệp, trùng với chỗ `doc.fetch` tải về.
    static let THU_MUC = "tai-lieu"

    struct KetQua {
        var duong: [String] = []          // đường dẫn tương đối, để gửi cho tác tử
        var daChep: [String] = []         // tệp phải chép vào (nằm ngoài dự án)
        var loi: [String] = []
    }

    /// Đưa danh sách tệp vào dự án. Trả đường dẫn TƯƠNG ĐỐI so với gốc.
    static func dua(_ nguon: [URL], vaoDuAn goc: URL) -> KetQua {
        var kq = KetQua()
        let fm = FileManager.default
        for u in nguon {
            let s = u.standardizedFileURL
            // Đã nằm trong dự án rồi thì đừng chép — chỉ lấy đường dẫn tương đối.
            if s.path.hasPrefix(goc.standardizedFileURL.path + "/") {
                kq.duong.append(String(s.path.dropFirst(goc.standardizedFileURL.path.count + 1)))
                continue
            }
            var la = ObjCBool(false)
            guard fm.fileExists(atPath: s.path, isDirectory: &la), !la.boolValue else {
                kq.loi.append("\(s.lastPathComponent): không phải một tệp")
                continue
            }
            let thuMuc = goc.appendingPathComponent(THU_MUC)
            do {
                try fm.createDirectory(at: thuMuc, withIntermediateDirectories: true)
                let dich = _tenKhongDe(thuMuc, ten: s.lastPathComponent)
                try fm.copyItem(at: s, to: dich)
                kq.duong.append("\(THU_MUC)/\(dich.lastPathComponent)")
                kq.daChep.append(dich.lastPathComponent)
            } catch {
                kq.loi.append("\(s.lastPathComponent): \(error.localizedDescription)")
            }
        }
        return kq
    }

    /// Tên chưa ai dùng trong thư mục: `a.pdf` → `a-2.pdf` → `a-3.pdf`.
    private static func _tenKhongDe(_ thuMuc: URL, ten: String) -> URL {
        let fm = FileManager.default
        let goc = (ten as NSString).deletingPathExtension
        let duoi = (ten as NSString).pathExtension
        var u = thuMuc.appendingPathComponent(ten)
        var i = 2
        while fm.fileExists(atPath: u.path) {
            let t = duoi.isEmpty ? "\(goc)-\(i)" : "\(goc)-\(i).\(duoi)"
            u = thuMuc.appendingPathComponent(t)
            i += 1
        }
        return u
    }

    /// Bảng chọn tệp. Nhiều tệp một lần — người có datasheet thường có vài quyển.
    static func chon() -> [URL] {
        let p = NSOpenPanel()
        p.title = "Thêm tài liệu cho tác tử"
        p.prompt = "Thêm"
        p.canChooseFiles = true
        p.canChooseDirectories = false
        p.allowsMultipleSelection = true
        return p.runModal() == .OK ? p.urls : []
    }
}
