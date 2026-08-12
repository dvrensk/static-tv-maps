import XCTest
@testable import MapEditor

final class ManifestTests: XCTestCase {
    func fixture() throws -> Manifest {
        let url = try XCTUnwrap(Bundle(for: Self.self).url(
            forResource: "spain-comunidades-labels", withExtension: "json"))
        return try JSONDecoder.manifest.decode(Manifest.self,
                                               from: Data(contentsOf: url))
    }

    func testDecodeRealManifest() throws {
        let m = try fixture()
        XCTAssertEqual(m.schema, 1)
        XCTAssertEqual(m.map, "spain-comunidades")
        XCTAssertEqual(m.canvas.widthPx, 4000)
        XCTAssertEqual(m.canvas.heightPx, 2250)
        XCTAssertEqual(m.labels.count, 21)
        XCTAssertGreaterThan(m.kmPerPx, 0)
        XCTAssertNotNil(m.canaryInsetPx)
        XCTAssertFalse(m.locked.isEmpty)
    }

    func testCalloutEntry() throws {
        let m = try fixture()
        let pv = try XCTUnwrap(m.labels.first { $0.id == "ccaa:16" })
        let callout = try XCTUnwrap(pv.calloutKm)
        XCTAssertEqual(callout.tx, 75)
        XCTAssertEqual(callout.ty, 100)
        let leader = try XCTUnwrap(pv.leader)
        XCTAssertEqual(leader.fromPx, pv.textPx)
        XCTAssertEqual(leader.toPx, pv.anchorPx)
    }

    func testManifestTextPxMatchesDragMath() throws {
        let m = try fixture()
        for e in m.labels {
            let st = LabelState(e)
            let p = st.textPx(anchor: e.anchorPx, kmPerPx: m.kmPerPx)
            XCTAssertEqual(p.x, e.textPx.x, accuracy: 0.25, e.id)
            XCTAssertEqual(p.y, e.textPx.y, accuracy: 0.25, e.id)
        }
    }
}
