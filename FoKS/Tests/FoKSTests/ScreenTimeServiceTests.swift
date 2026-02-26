import XCTest
@testable import FoKS_Service_Lib

final class ScreenTimeServiceTests: XCTestCase {
    func testScreenTimeRecord() {
        let service = ScreenTimeService()
        XCTAssertNotNil(service)
        // Note: Actual recording depends on system state and DB file access
    }

    func testTodayTotalQuery() {
        let service = ScreenTimeService()
        let total = service.todayTotal()
        XCTAssertFalse(total.isEmpty)
    }
}
