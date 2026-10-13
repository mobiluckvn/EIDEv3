import XCTest
@testable import EIDE

/// Trả nợ giao diện của EDIT-47 — §DEV-380.
///
/// Hai thứ đo được ở mức hàm: cú bấm mang `di_tab` phải **đổi tab** chứ không chỉ ghi sổ,
/// và `Card` phải đọc được `hanh_dong` mà lõi khai **trên thẻ** (trước đây chỉ khối mới có).
@MainActor
final class NoGiaoDienTests: XCTestCase {

    private func state() -> AppState {
        let s = AppState()
        s.connection = .dangChay("thử")
        s.selectedSurface = "console"
        return s
    }

    /// Đúng hình dạng `ask_user` gắn vào thẻ khi kho có phương án chưa chốt.
    private func nutSuaPhuongAn() -> HanhDong {
        HanhDong(.object([
            "ma": .string("mo_bang_phuong_an"),
            "nhan": .string("Sửa phương án (2 cách)"),
            "kind": .string("attend"), "muc": .string("khoi"),
            "data": .object(["di_tab": .string("requirements")]),
            "giai_thich": .string("Mở bảng Phương án ở tab Yêu cầu. 0 token."),
        ]))
    }

    func testThePhanBietDuocHanhDongTrenTHE() {
        let the = Card(id: "card-1", raw: [
            "type": .string("clarify"), "card_id": .string("card-1"),
            "hanh_dong": .array([nutSuaPhuongAn().raw]),
        ])
        XCTAssertEqual(the.hanhDong.count, 1)
        XCTAssertEqual(HanhDong(the.hanhDong[0]).ma, "mo_bang_phuong_an")

        // Thẻ KHÔNG khai gì thì không có nút nào — không tự bày ra một cái.
        let tron = Card(id: "card-2", raw: ["type": .string("clarify")])
        XCTAssertTrue(tron.hanhDong.isEmpty)
    }

    func testGuiAttendMangDUNGBeMatSapNhin() {
        let hd = nutSuaPhuongAn()
        // `act(surface:)` nhận bề mặt do chỗ gọi quyết định; `NutHanhDong` truyền
        // `di_tab` vào đây. Thiếu phần ấy thì `attend` nói "tôi đang xem tab Yêu cầu"
        // trong khi người vẫn ngồi ở Console — lõi và màn hình nói hai chuyện khác nhau.
        let act = hd.act(ma: "", loai: "", khoi: "card-1",
                         surface: "requirements", lyDo: "")
        XCTAssertEqual(act?.kind, .attend)
        XCTAssertEqual(act?.origin.surface, "requirements")
        XCTAssertEqual(act?.data["di_tab"]?.stringValue, "requirements")
        XCTAssertNil(act?.target, "mở một tab không trỏ vào hiện vật nào")
    }

    /// Nhãn số của một dòng `diff_tom_tat`. `doi` phải có mặt — một ô bị SỬA đếm vào `doi`
    /// và để `them`/`bot` bằng 0, nên bảng chỉ hiện `+them −bot` sẽ in "+0 −0" cho đúng ca
    /// thường gặp nhất: nói "không đổi gì" về một thay đổi.
    func testNhanSoCuaDongDiffTomTat() {
        let oSua = JSONValue.object(["doi": .number(1), "them": .number(0),
                                     "bot": .number(0)])
        XCTAssertEqual(SeMatGiView.nhanSo(oSua).map(\.0), ["1 đổi"])

        let themBot = JSONValue.object(["doi": .number(2), "them": .number(3),
                                        "bot": .number(1)])
        XCTAssertEqual(SeMatGiView.nhanSo(themBot).map(\.0), ["2 đổi", "+3", "−1"])

        // Không số nào > 0 mà dòng vẫn ở đây (gỡ bỏ / dựng lại cả hiện vật): phải nói
        // thẳng, đừng để một dòng trống trông như lỗi hiển thị.
        let rong = JSONValue.object(["doi": .number(0), "them": .number(0),
                                     "bot": .number(0)])
        XCTAssertEqual(SeMatGiView.nhanSo(rong).map(\.0), ["cả hiện vật"])
    }

    /// Nút "Quét lại ngay" ở A11.1 gửi `set` — 0 token, và KHÔNG được mang `target`.
    func testNutQuetLaiGuiSetKhongTarget() {
        let hd = HanhDong(.object([
            "ma": .string("quet_lai"), "nhan": .string("Quét lại ngay"),
            "kind": .string("set"), "muc": .string("khoi"),
            "data": .object(["key": .string("watcher.quet_lai"), "value": .bool(true)]),
        ]))
        let act = hd.act(ma: "", loai: "", khoi: "A11.1", surface: "history", lyDo: "")
        XCTAssertEqual(act?.kind, .set)
        XCTAssertEqual(act?.data["key"]?.stringValue, "watcher.quet_lai")
        XCTAssertEqual(act?.data["value"]?.boolValue, true)
        XCTAssertFalse(hd.tonToken, "quét lại là việc của mã")
    }
}
