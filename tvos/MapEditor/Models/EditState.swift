import Foundation

/// The editable fields of one label, plus the drag math that converts a
/// pixel delta on the canvas into cartographic km offsets.
struct LabelState: Equatable {
    var dx: Double
    var dy: Double
    var tx: Double?
    var ty: Double?
    var size: Double
    var ha: String
    var va: String
    var rotation: Double

    init(_ e: LabelEntry) {
        dx = e.offsetKm.dx
        dy = e.offsetKm.dy
        tx = e.calloutKm?.tx
        ty = e.calloutKm?.ty
        size = e.sizePt
        ha = e.ha
        va = e.va
        rotation = e.rotation
    }

    var isCallout: Bool { tx != nil && ty != nil }

    /// Move the text by a canvas-pixel delta (y down). Callouts move their
    /// text (tx/ty); plain labels move their offset (dx/dy).
    mutating func move(byPx delta: PixelPoint, kmPerPx: Double) {
        let dkx = delta.x * kmPerPx
        let dky = -delta.y * kmPerPx
        if isCallout {
            tx! += dkx
            ty! += dky
        } else {
            dx += dkx
            dy += dky
        }
    }

    /// Where the text anchor sits on the canvas, in pixels.
    func textPx(anchor: PixelPoint, kmPerPx: Double) -> PixelPoint {
        let kx = dx + (tx ?? 0)
        let ky = dy + (ty ?? 0)
        return PixelPoint(x: anchor.x + kx / kmPerPx,
                          y: anchor.y - ky / kmPerPx)
    }

    /// Where the leader line starts (the moved anchor), in pixels.
    func leaderAnchorPx(anchor: PixelPoint, kmPerPx: Double) -> PixelPoint {
        PixelPoint(x: anchor.x + dx / kmPerPx, y: anchor.y - dy / kmPerPx)
    }

    /// Round km offsets to one decimal (the repo convention).
    mutating func quantize() {
        func q(_ v: Double) -> Double { (v * 10).rounded() / 10 }
        dx = q(dx); dy = q(dy)
        if let v = tx { tx = q(v) }
        if let v = ty { ty = q(v) }
    }

    /// The override fields whose values differ from `base`.
    func changedFields(from base: LabelState) -> LabelOverride {
        var out: LabelOverride = [:]
        if dx != base.dx { out["dx"] = .number(dx) }
        if dy != base.dy { out["dy"] = .number(dy) }
        if tx != base.tx { out["tx"] = tx.map { .number($0) } ?? .null }
        if ty != base.ty { out["ty"] = ty.map { .number($0) } ?? .null }
        if size != base.size { out["size"] = .number(size) }
        if ha != base.ha { out["ha"] = .string(ha) }
        if va != base.va { out["va"] = .string(va) }
        if rotation != base.rotation { out["rotation"] = .number(rotation) }
        return out
    }

    /// Apply a fetched override entry on top (used when the overrides file
    /// is newer than the exported manifest).
    mutating func apply(_ override: LabelOverride, editable: [String]) {
        for (key, value) in override where editable.contains(key) {
            switch key {
            case "dx": if let v = value.doubleValue { dx = v }
            case "dy": if let v = value.doubleValue { dy = v }
            case "tx": tx = value.doubleValue
            case "ty": ty = value.doubleValue
            case "size": if let v = value.doubleValue { size = v }
            case "ha": if let v = value.stringValue { ha = v }
            case "va": if let v = value.stringValue { va = v }
            case "rotation": if let v = value.doubleValue { rotation = v }
            default: break
            }
        }
    }
}

/// One editing session over one map.
@MainActor
final class EditSession: ObservableObject {
    let manifest: Manifest
    /// Session-start state per label id (manifest + fetched overrides).
    let baseline: [String: LabelState]
    @Published var states: [String: LabelState]
    @Published var selectedID: String?
    private var undoStack: [(String, LabelState)] = []

    init(manifest: Manifest, fetched: OverridesFile?) {
        self.manifest = manifest
        var s: [String: LabelState] = [:]
        for e in manifest.labels {
            var st = LabelState(e)
            if let ov = fetched?.labels[e.id] {
                st.apply(ov, editable: e.editable)
            }
            s[e.id] = st
        }
        baseline = s
        states = s
        selectedID = manifest.labels.first?.id
    }

    var isDirty: Bool { states != baseline }

    func entry(_ id: String) -> LabelEntry? {
        manifest.labels.first { $0.id == id }
    }

    func beginEdit(_ id: String) {
        if let st = states[id] { undoStack.append((id, st)) }
    }

    func cancelEdit() {
        if let (id, st) = undoStack.popLast() { states[id] = st }
    }

    func commitEdit() {
        if let (id, _) = undoStack.popLast(), var st = states[id] {
            st.quantize()
            states[id] = st
        }
    }

    /// Session edits as override entries (absolute values, changed fields
    /// only), ready to merge over the fetched overrides file.
    func edits() -> [String: LabelOverride] {
        var out: [String: LabelOverride] = [:]
        for (id, st) in states {
            guard let base = baseline[id] else { continue }
            let changed = st.changedFields(from: base)
            if !changed.isEmpty { out[id] = changed }
        }
        return out
    }
}
