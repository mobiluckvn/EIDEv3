import XCTest
@testable import EIDE

final class ThuNoi: XCTestCase {
    func test_noi_duoc_vao_ma_giao_dien() {
        XCTAssertEqual(Markdown.tach("xin chào").count, 1)
    }
}
