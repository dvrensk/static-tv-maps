import XCTest
@testable import MapEditor

final class EditStateTests: XCTestCase {
    private func entry(dx: Double = 0, dy: Double = 0,
                       tx: Double? = nil, ty: Double? = nil) -> LabelEntry {
        let json = """
        {"id": "ccaa:12", "kind": "region", "text": "Galicia",
         "anchor_px": {"x": 1000.0, "y": 500.0},
         "offset_km": {"dx": \(dx), "dy": \(dy)},
         "callout_km": \(tx != nil ? "{\"tx\": \(tx!), \"ty\": \(ty!)}" : "null"),
         "text_px": {"x": 1000.0, "y": 500.0}, "bbox_px": null,
         "size_pt": 48, "weight": "extrabold", "color": "#26241f",
         "halo": {"color": "#ffffff", "width_pt": 5.33},
         "ha": "center", "va": "center", "rotation": 0, "linespacing": 0.95,
         "leader": null, "sub": null, "badge": null, "marker": null,
         "in_canary_inset": false,
         "editable": ["dx", "dy", "tx", "ty", "size", "ha"]}
        """
        return try! JSONDecoder.manifest.decode(LabelEntry.self,
                                                from: Data(json.utf8))
    }

    func testMoveConvertsPxToKmWithYFlip() {
        var st = LabelState(entry())
        st.move(byPx: PixelPoint(x: 10, y: -6), kmPerPx: 0.5)
        XCTAssertEqual(st.dx, 5.0, accuracy: 1e-9)
        XCTAssertEqual(st.dy, 3.0, accuracy: 1e-9)   // up on screen = +dy km
    }

    func testMoveCalloutMovesTextNotAnchor() {
        var st = LabelState(entry(tx: 20, ty: 30))
        st.move(byPx: PixelPoint(x: 4, y: 4), kmPerPx: 0.5)
        XCTAssertEqual(st.tx!, 22.0, accuracy: 1e-9)
        XCTAssertEqual(st.ty!, 28.0, accuracy: 1e-9)
        XCTAssertEqual(st.dx, 0)
        XCTAssertEqual(st.dy, 0)
    }

    func testTextPxRoundTrip() {
        var st = LabelState(entry())
        let before = st.textPx(anchor: PixelPoint(x: 1000, y: 500),
                               kmPerPx: 0.48262)
        st.move(byPx: PixelPoint(x: 33, y: -21), kmPerPx: 0.48262)
        let after = st.textPx(anchor: PixelPoint(x: 1000, y: 500),
                              kmPerPx: 0.48262)
        XCTAssertEqual(after.x - before.x, 33, accuracy: 1e-6)
        XCTAssertEqual(after.y - before.y, -21, accuracy: 1e-6)
    }

    func testQuantizeRoundsToTenthKm()  {
        var st = LabelState(entry())
        st.move(byPx: PixelPoint(x: 7, y: 3), kmPerPx: 0.48262)
        st.quantize()
        XCTAssertEqual(st.dx, 3.4, accuracy: 1e-9)
        XCTAssertEqual(st.dy, -1.4, accuracy: 1e-9)
    }

    func testChangedFieldsProducesMinimalOverride() {
        let base = LabelState(entry())
        var st = base
        st.dx = 60
        st.size = 50
        let changed = st.changedFields(from: base)
        XCTAssertEqual(changed.count, 2)
        XCTAssertEqual(changed["dx"], .number(60))
        XCTAssertEqual(changed["size"], .number(50))
    }

    func testDemoteCalloutEncodesExplicitNull() throws {
        let base = LabelState(entry(tx: 20, ty: 30))
        var st = base
        st.tx = nil
        st.ty = nil
        let changed = st.changedFields(from: base)
        XCTAssertEqual(changed["tx"], .null)
        let file = OverridesFile(map: "m", labels: ["ccaa:12": changed])
        let json = String(data: try file.encoded(), encoding: .utf8)!
        XCTAssertTrue(json.contains("\"tx\" : null")
                      || json.contains("\"tx\": null"), json)
    }

    func testApplyFetchedOverrideRespectsEditableList() {
        var st = LabelState(entry())
        st.apply(["dx": .number(12), "rotation": .number(45)],
                 editable: ["dx", "dy", "tx", "ty", "size", "ha"])
        XCTAssertEqual(st.dx, 12)
        XCTAssertEqual(st.rotation, 0)   // not editable on this label
    }

    func testOverridesMergeKeepsForeignEntriesAndFields() {
        let fetched = OverridesFile(
            map: "m",
            labels: ["a": ["dx": .number(1), "size": .number(40)],
                     "b": ["dy": .number(2)]])
        let merged = fetched.merging(edits: ["a": ["dx": .number(9)]])
        XCTAssertEqual(merged.labels["a"]?["dx"], .number(9))
        XCTAssertEqual(merged.labels["a"]?["size"], .number(40))
        XCTAssertEqual(merged.labels["b"]?["dy"], .number(2))
    }
}
