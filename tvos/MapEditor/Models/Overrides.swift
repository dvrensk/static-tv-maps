import Foundation

// overrides/<map>.json — the editor's output. Values are absolute
// replacements of the normalized label fields; `tx: null` demotes a callout
// to a plain label. See docs/editor-protocol.md.

/// A JSON scalar that can round-trip an explicit null (needed for tx/ty).
enum OverrideValue: Codable, Equatable {
    case number(Double)
    case string(String)
    case null

    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() {
            self = .null
        } else if let n = try? c.decode(Double.self) {
            self = .number(n)
        } else {
            self = .string(try c.decode(String.self))
        }
    }

    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .number(let n):
            // Whole numbers encode without a trailing ".0" for tidy diffs.
            if n == n.rounded() && abs(n) < 1e15 {
                try c.encode(Int(n))
            } else {
                try c.encode(n)
            }
        case .string(let s): try c.encode(s)
        case .null: try c.encodeNil()
        }
    }

    var doubleValue: Double? {
        if case .number(let n) = self { return n }
        return nil
    }

    var stringValue: String? {
        if case .string(let s) = self { return s }
        return nil
    }
}

typealias LabelOverride = [String: OverrideValue]

struct OverridesFile: Codable, Equatable {
    var schema: Int = 1
    var map: String
    var labels: [String: LabelOverride]

    init(map: String, labels: [String: LabelOverride] = [:]) {
        self.map = map
        self.labels = labels
    }

    /// Merge session edits on top of the fetched file. Existing entries are
    /// kept (they may patch fields this session never touched) and edited
    /// fields replace or extend them.
    func merging(edits: [String: LabelOverride]) -> OverridesFile {
        var merged = labels
        for (id, fields) in edits {
            merged[id] = (merged[id] ?? [:]).merging(fields) { _, new in new }
        }
        return OverridesFile(map: map, labels: merged)
    }

    /// Stable, human-diffable JSON bytes.
    func encoded() throws -> Data {
        let e = JSONEncoder()
        e.outputFormatting = [.prettyPrinted, .sortedKeys,
                              .withoutEscapingSlashes]
        return try e.encode(self)
    }
}
