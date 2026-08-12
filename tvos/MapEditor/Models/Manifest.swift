import Foundation

// Mirrors editor/<map>/labels.json (schema 1). See docs/editor-protocol.md.

struct MapIndex: Codable {
    let schema: Int
    let maps: [MapIndexEntry]
}

struct MapIndexEntry: Codable, Identifiable, Hashable {
    var id: String { name }
    let name: String
    let base: String
    let manifest: String
    let output: String
    let labels: Int
}

struct Manifest: Codable {
    let schema: Int
    let map: String
    let canvas: CanvasInfo
    let kmPerPx: Double
    let canaryInsetPx: PixelRect?
    let labels: [LabelEntry]
    let locked: [LockedEntry]

    struct CanvasInfo: Codable {
        let widthPx: Int
        let heightPx: Int
        let dpi: Int
    }
}

struct PixelPoint: Codable, Equatable {
    var x: Double
    var y: Double
}

struct PixelRect: Codable, Equatable {
    let x0: Double
    let y0: Double
    let x1: Double
    let y1: Double
}

struct KmOffset: Codable, Equatable {
    var dx: Double
    var dy: Double
}

struct KmCallout: Codable, Equatable {
    var tx: Double
    var ty: Double
}

struct LabelEntry: Codable, Identifiable {
    let id: String
    let kind: String
    let text: String
    let anchorPx: PixelPoint
    let offsetKm: KmOffset
    let calloutKm: KmCallout?
    let textPx: PixelPoint
    let bboxPx: PixelRect?
    let sizePt: Double
    let weight: String
    let color: String
    let halo: Halo
    let ha: String
    let va: String
    let rotation: Double
    let linespacing: Double
    let leader: Leader?
    let sub: SubLine?
    let badge: Badge?
    let marker: Marker?
    let inCanaryInset: Bool
    let editable: [String]

    struct Halo: Codable {
        let color: String
        let widthPt: Double
    }

    struct Leader: Codable {
        let fromPx: PixelPoint
        let toPx: PixelPoint
        let color: String
        let widthPt: Double
        let shrinkFromPt: Double
        let shrinkToPt: Double
    }

    struct SubLine: Codable {
        let text: String
        let sizePt: Double
    }

    struct Badge: Codable {
        let number: Int
        let face: String
        let numberColor: String
        let numberSizePt: Double
        let centerPx: PixelPoint?
        let radiusPx: Double?
        let gapPx: Double?
    }

    struct Marker: Codable {
        let type: String
        let baked: Bool
    }
}

struct LockedEntry: Codable, Identifiable {
    let id: String
    let kind: String
    let text: String
    let bboxPx: PixelRect?
}

extension JSONDecoder {
    /// Decoder configured for the exporter's snake_case JSON.
    static var manifest: JSONDecoder {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }
}
