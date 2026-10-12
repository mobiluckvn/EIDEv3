import XCTest
@testable import EIDE

/// Những cái NÚT của năm tầng lùi — EIDE-EDIT-47 §DEV-365.
///
/// Câu phải trả lời được bằng số, không bằng cách mở app ra bấm: **nút ấy gửi đi cái gì**.
///
/// Lỗi đã trả giá thật và nằm ngay trong tệp này: nút "Khôi phục" ở tab Lịch sử gửi một câu
/// `say` — tức nhờ MÔ HÌNH khôi phục hộ — trong khi `history.khoi_phuc_snapshot` đã có từ
/// bước G5. Nó "chạy được", nên không ai nhìn lại; và mọi ca đo vẫn xanh vì không ca nào
/// hỏi cái nút ấy gửi gì. Một lượt mô hình cho một việc 0 token, với mô hình đứng giữa
/// người và một thao tác R0.
@MainActor
final class LuiTests: XCTestCase {

    /// Một `AppState` coi như đã nối lõi. `gui(_:)` chặn ở `connection.ok`, nên không đặt
    /// cờ này thì mọi ca dưới đây xanh một cách vô nghĩa: không có gì được gửi, và không có
    /// gì được gửi thì cũng không có gì sai.
    private func state() -> AppState {
        let s = AppState()
        s.connection = .dangChay("thử")
        return s
    }

    private func lenh(_ method: String, _ params: [String: JSONValue]) -> UICommand {
        UICommand(method: method, params: params, seq: 1)
    }

    // ===================================================== (6) ghi bản ưng ý
    func test_ghi_ban_ung_y_ten_RONG_thi_KHONG_gui_gi() {
        let s = state()
        XCTAssertFalse(s.ghiBanUngY(ten: "   "))
        XCTAssertFalse(s.ghiBanUngY(ten: ""))
        XCTAssertTrue(s.daGui.isEmpty,
                      "tên rỗng thì không được gửi — lõi cũng từ chối, và một vòng đi–về "
                      + "để biết mình chưa đặt tên là một vòng người không cần trả")
    }

    func test_ghi_ban_ung_y_gui_dung_kind_va_cat_khoang_trang() {
        let s = state()
        XCTAssertTrue(s.ghiBanUngY(ten: "  nạp xong, LED nháy đúng  ", ghiChu: "đo trên bo"))
        XCTAssertEqual(s.daGui.count, 1)
        let a = s.daGui[0]
        XCTAssertEqual(a.kind, .snapshot)
        XCTAssertEqual(a.data["name"]?.stringValue, "nạp xong, LED nháy đúng")
        XCTAssertEqual(a.data["note"]?.stringValue, "đo trên bo")
    }

    // ===================================================== (7) thanh "vừa ghi"
    func test_thanh_vua_ghi_gui_dung_target_PHIEN_SUA_khi_co_ma_phien() {
        let s = state()
        s.apply(lenh("history.update", ["vua_ghi": .object([
            "changeset": .string("cs-123"), "tom_tat": .string("anh sửa FR-01"),
            "session": .string("es-7"), "so_trong_phien": .number(3),
            "hoan_tac_duoc": .bool(true)])]))

        XCTAssertEqual(s.toastLuu?.changeset, "cs-123")
        XCTAssertEqual(s.toastLuu?.nhan, "Hoàn tác cả 3 thay đổi vừa sửa")

        s.hoanTacVuaGhi()
        XCTAssertEqual(s.daGui.count, 1)
        XCTAssertEqual(s.daGui[0].kind, .undo)
        XCTAssertEqual(s.daGui[0].target?.type, "session",
                       "có mã phiên thì lùi CẢ LƯỢT SỬA — sửa bốn ô là bốn lần lưu, và "
                       + "người bấm Hoàn tác muốn lùi cái họ vừa làm")
        XCTAssertEqual(s.daGui[0].target?.id, "es-7")
        XCTAssertNil(s.toastLuu, "đã bấm thì thanh phải mất — bấm lần nữa là lùi hai lần")
    }

    func test_thanh_vua_ghi_khong_co_ma_phien_thi_lui_RIENG_changeset() {
        let s = state()
        s.apply(lenh("history.update", ["vua_ghi": .object([
            "changeset": .string("cs-9"), "tom_tat": .string("anh sửa ngưỡng")])]))
        XCTAssertEqual(s.toastLuu?.nhan, "Hoàn tác")
        s.hoanTacVuaGhi()
        XCTAssertEqual(s.daGui[0].target?.type, "changeset")
        XCTAssertEqual(s.daGui[0].target?.id, "cs-9")
    }

    func test_thanh_vua_ghi_HET_HAN_sau_30_giay_va_khong_con_bam_duoc() {
        let s = state()
        s.toastLuu = .init(changeset: "cs-1", tomTat: "sửa", session: nil,
                           luc: Date().addingTimeInterval(-(AppState.giayToast + 1)))
        XCTAssertNil(s.toastConHieuLuc, "quá 30 giây thì nó không còn là một cái nút")

        s.hoanTacVuaGhi()
        XCTAssertTrue(s.daGui.isEmpty,
                      "một cái nút bấm được mà không làm gì là thứ tệ nhất: người tưởng "
                      + "mình vừa lùi xong")
        s.donToastHetHan()
        XCTAssertNil(s.toastLuu)
    }

    func test_thanh_vua_ghi_khong_hoan_tac_duoc_thi_khong_gui() {
        let s = state()
        s.apply(lenh("history.update", ["vua_ghi": .object([
            "changeset": .string("cs-5"), "hoan_tac_duoc": .bool(false)])]))
        s.hoanTacVuaGhi()
        XCTAssertTrue(s.daGui.isEmpty)
    }

    // ===================================================== (8) "Lùi cả lượt"
    func test_lui_ca_luot_CHI_hien_khi_luot_co_thay_doi() {
        let s = state()
        s.apply(lenh("run.update", ["run_id": .string("run-1"), "status": .string("done"),
                                    "so_thay_doi": .number(0),
                                    "buttons": .array([.string("Ghi bản ưng ý")])]))
        XCTAssertEqual(s.run?.soThayDoi, 0)
        XCTAssertFalse(s.run?.buttons.contains("Lùi cả lượt") ?? true)
        s.luiCaLuot()
        XCTAssertTrue(s.daGui.isEmpty, "lượt không đổi gì thì không có gì để lùi")

        s.apply(lenh("run.update", ["run_id": .string("run-2"), "status": .string("done"),
                                    "so_thay_doi": .number(4),
                                    "buttons": .array([.string("Lùi cả lượt"),
                                                       .string("Ghi bản ưng ý")])]))
        XCTAssertEqual(s.run?.soThayDoi, 4)
        // Thanh nút do LÕI khai (I3). `run.update` đã mang `buttons` từ bước G2 và giao diện
        // **bỏ qua nó** suốt từ đó — đúng kiểu hỏng mà cả gói này tồn tại để vá, nên nó phải
        // có một phép đo riêng, không nấp sau phép đo của `so_thay_doi`.
        XCTAssertEqual(s.run?.buttons, ["Lùi cả lượt", "Ghi bản ưng ý"])
        s.luiCaLuot()
        XCTAssertEqual(s.daGui.count, 1)
        XCTAssertEqual(s.daGui[0].kind, .undo)
        XCTAssertEqual(s.daGui[0].target?.type, "run")
        XCTAssertEqual(s.daGui[0].target?.id, "run-2")
        XCTAssertEqual(s.daGui[0].data["mode"]?.stringValue, "revert")
    }

    func test_moi_phep_lui_khac_deu_BO_thanh_vua_ghi() {
        // Thấy trên ảnh chụp của `tools/thu_nut_lui.py`: lùi về một bản ưng ý xong, thanh
        // "Đã ghi cs-0006 · Hoàn tác" vẫn nằm đó — mà cs-0006 chính là thay đổi phép khôi
        // phục vừa cuốn đi. Nút không hỏng, nhưng nó MÔ TẢ SAI trạng thái.
        for lui in ["ve_ban", "lui_luot"] {
            let s = state()
            s.apply(lenh("history.update", ["vua_ghi": .object([
                "changeset": .string("cs-6"), "tom_tat": .string("anh sửa")])]))
            s.apply(lenh("run.update", ["run_id": .string("run-9"),
                                        "status": .string("done"),
                                        "so_thay_doi": .number(2)]))
            if lui == "ve_ban" { s.veBanUngY("snap-1") } else { s.luiCaLuot() }
            XCTAssertNil(s.toastLuu, "sau \(lui), thanh “vừa ghi” nói về một trạng thái "
                                     + "không còn ở đỉnh lịch sử")
        }
    }

    // ===================================================== về bản ưng ý
    func test_ve_ban_ung_y_gui_undo_target_snapshot_kem_ten_giu_ban_hien_tai() {
        let s = state()
        s.veBanUngY("snap-3", giuBanHienTai: " hướng đã thử ")
        let a = s.daGui[0]
        XCTAssertEqual(a.kind, .undo)
        XCTAssertEqual(a.target?.type, "snapshot")
        XCTAssertEqual(a.target?.id, "snap-3")
        XCTAssertEqual(a.data["mode"]?.stringValue, "restore_branch")
        XCTAssertEqual(a.data["giu_ban_hien_tai"]?.stringValue, "hướng đã thử")
    }

    func test_ve_ban_ung_y_bo_trong_ten_giu_thi_KHONG_kem_truong_do() {
        let s = state()
        s.veBanUngY("snap-3", giuBanHienTai: "   ")
        XCTAssertNil(s.daGui[0].data["giu_ban_hien_tai"],
                     "gửi một tên rỗng sẽ tạo một bản ưng ý không tên — lõi từ chối, và "
                     + "cả phép khôi phục mang theo một cảnh báo không cần thiết")
    }

    // ===================================================== nhánh
    func test_thao_tac_nhanh_ten_rong_thi_khong_gui_gi() {
        let s = state()
        XCTAssertFalse(s.thaoTacNhanh("merge", ten: " "))
        XCTAssertTrue(s.daGui.isEmpty)
    }

    func test_thao_tac_nhanh_gui_dung_ba_viec() {
        for viec in ["create", "switch", "merge"] {
            let s = state()
            XCTAssertTrue(s.thaoTacNhanh(viec, ten: "thu-a"))
            XCTAssertEqual(s.daGui[0].kind, .branch)
            XCTAssertEqual(s.daGui[0].data["action"]?.stringValue, viec)
            XCTAssertEqual(s.daGui[0].data["name"]?.stringValue, "thu-a")
        }
    }

    func test_danh_sach_nhanh_va_ban_ung_y_den_TU_LOI_chu_khong_tu_git() {
        let s = state()
        s.apply(lenh("history.update", [
            "snapshots": .array([.object(["id": .string("snap-1"),
                                          "name": .string("mốc A")])]),
            "nhanh": .object(["hien_tai": .string("thu-b"),
                              "danh_sach": .array([.string("main"), .string("thu-b")])])]))
        XCTAssertEqual(s.nhanhHienTai, "thu-b")
        XCTAssertEqual(s.nhanh, ["main", "thu-b"])
        XCTAssertEqual(s.snapshots.count, 1)
    }

    func test_history_update_mot_changeset_KHONG_xoa_danh_sach_ban_ung_y() {
        // Lệnh này được phát cả sau mỗi lần người sửa, lúc ấy nó chỉ mang một changeset.
        // Xoá hai danh sách kia theo thì menu "Về bản…" rỗng đi ngay sau khi sửa một ô.
        let s = state()
        s.apply(lenh("history.update", [
            "snapshots": .array([.object(["id": .string("snap-1")])]),
            "nhanh": .object(["hien_tai": .string("main"),
                              "danh_sach": .array([.string("main")])])]))
        s.apply(lenh("history.update", [
            "changesets": .array([.object(["id": .string("cs-2")])]),
            "snapshots": .array([]), "nhanh": .object([:])]))
        XCTAssertEqual(s.snapshots.count, 1)
        XCTAssertEqual(s.nhanh, ["main"])
    }

    // ===================================================== phiên sửa
    func test_phien_sua_gom_nhieu_lan_luu_lai_mot_ma() {
        let s = state()
        let a = s.moPhienSua()
        XCTAssertEqual(a, s.moPhienSua(), "cùng một lần ngồi sửa thì cùng một mã")
        s.dongPhienSua()
        XCTAssertNotEqual(a, s.moPhienSua(), "đóng trình soạn rồi mở lại là một lượt khác")
    }

    func test_phien_sua_nguoi_thi_HET_han() {
        let s = state()
        let a = s.moPhienSua()
        // Hai lần sửa cách nhau cả tiếng mà cùng một mã thì nút Hoàn tác sẽ lùi nhiều hơn
        // người tưởng — và họ không có cách nào biết trước.
        s.lanChamPhienSua = Date().addingTimeInterval(-(AppState.giayPhienSua + 1))
        XCTAssertNotEqual(a, s.moPhienSua())
    }

    // ===================================================== ô sửa trong bảng
    func test_o_sua_trong_bang_GUI_KEM_ma_phien_sua() {
        let a = OSuaDuoc.actLuu(ma: "FR-01", truong: "criteria", gia: "≥ 5 MB/s",
                                phienBan: 3, khoi: "A2.1", loai: "req",
                                surface: "requirements", session: "es-4",
                                viSao: "phim 4K")
        XCTAssertEqual(a.kind, .edit)
        XCTAssertEqual(a.target?.type, "req")
        XCTAssertEqual(a.data["base_version"]?.stringValue, "v3")
        XCTAssertEqual(a.data["session_id"]?.stringValue, "es-4",
                       "không gửi mã phiên thì lõi đặt một mốc lùi cho MỖI ô người sửa, và "
                       + "thanh Hoàn tác chỉ lùi được ô cuối cùng")
        XCTAssertEqual(a.data["fields"]?["criteria"]?.stringValue, "≥ 5 MB/s")
        XCTAssertEqual(a.origin.block, "A2.1")
        XCTAssertEqual(a.origin.row, "FR-01")
        XCTAssertEqual(a.note, "phim 4K")
    }

    func test_o_sua_khong_co_ly_do_thi_KHONG_dat_mot_chuoi_rong_vao_note() {
        let a = OSuaDuoc.actLuu(ma: "FR-01", truong: "text", gia: "x", phienBan: 1,
                                khoi: "A2.1", loai: "req", surface: "requirements",
                                session: "es-1", viSao: "")
        XCTAssertNil(a.note, "“vì sao” là tuỳ chọn; một chuỗi rỗng đứng tên lý do thì "
                             + "transcript sẽ ghi “vì: ” rồi bỏ lửng")
    }

    // ===================================================== đổi dự án
    func test_doi_du_an_xoa_ca_toast_va_phien_sua() {
        let s = state()
        s.toastLuu = .init(changeset: "cs-1", tomTat: "x")
        _ = s.moPhienSua()
        s.snapshots = [.object(["id": .string("snap-1")])]
        s.nhanh = ["main", "thu"]
        _ = s.ghiBanUngY(ten: "x")

        s.doiDuAn(URL(fileURLWithPath: "/tmp/du-an-khac"))

        XCTAssertNil(s.toastLuu, "bấm Hoàn tác cho một changeset của dự án CŨ là gửi một "
                                 + "quyết định về một lõi đã chết")
        XCTAssertNil(s.sessionSua)
        XCTAssertTrue(s.snapshots.isEmpty)
        XCTAssertTrue(s.nhanh.isEmpty)
        XCTAssertTrue(s.daGui.isEmpty)
    }
}
