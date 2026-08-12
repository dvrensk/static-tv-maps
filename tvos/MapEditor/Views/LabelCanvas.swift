import SwiftUI
import UIKit

/// Draws the exported base image with the editable labels overlaid natively:
/// Inter text with a stroke halo (two passes, stroke under fill, matching
/// matplotlib's withStroke), leader lines, and numbered badges. Canvas
/// coordinates are the manifest's 4000x2250 px, scaled to the view.
final class LabelCanvasView: UIView {
    var baseImage: UIImage? { didSet { setNeedsDisplay() } }
    var manifest: Manifest? { didSet { setNeedsDisplay() } }
    var states: [String: LabelState] = [:] { didSet { setNeedsDisplay() } }
    var selectedID: String? { didSet { setNeedsDisplay() } }
    var editing = false { didSet { setNeedsDisplay() } }

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .black
        contentMode = .redraw
    }

    required init?(coder: NSCoder) { fatalError() }

    /// View points per canvas pixel (the base image is 16:9 like the screen).
    private var scale: CGFloat {
        guard let m = manifest else { return 1 }
        return min(bounds.width / CGFloat(m.canvas.widthPx),
                   bounds.height / CGFloat(m.canvas.heightPx))
    }

    private func viewPoint(_ p: PixelPoint) -> CGPoint {
        CGPoint(x: CGFloat(p.x) * scale, y: CGFloat(p.y) * scale)
    }

    override func draw(_ rect: CGRect) {
        guard let ctx = UIGraphicsGetCurrentContext(),
              let m = manifest else { return }
        let s = scale
        baseImage?.draw(in: CGRect(x: 0, y: 0,
                                   width: CGFloat(m.canvas.widthPx) * s,
                                   height: CGFloat(m.canvas.heightPx) * s))

        for entry in m.labels {
            guard let st = states[entry.id] else { continue }
            drawLabel(entry, st, in: ctx)
        }
        if let id = selectedID, let entry = m.labels.first(where: { $0.id == id }),
           let st = states[id] {
            drawSelection(entry, st, in: ctx)
        }
    }

    // MARK: Label drawing

    private func drawLabel(_ e: LabelEntry, _ st: LabelState,
                           in ctx: CGContext) {
        let m = manifest!
        let k = m.kmPerPx
        let textAt = viewPoint(st.textPx(anchor: e.anchorPx, kmPerPx: k))

        if st.isCallout {
            let anchorAt = viewPoint(st.leaderAnchorPx(anchor: e.anchorPx,
                                                       kmPerPx: k))
            drawLeader(e, from: textAt, to: anchorAt, in: ctx)
        }

        if let badge = e.badge {
            drawBadgedText(e, st, badge, at: textAt, in: ctx)
        } else {
            drawHaloText(text: e.text, at: textAt, sizePt: st.size,
                         weight: e.weight, color: e.color,
                         halo: e.halo.color,
                         haloWidthPt: haloWidth(e, st),
                         ha: st.ha, va: st.va, rotation: st.rotation,
                         linespacing: e.linespacing, in: ctx)
        }

        if let sub = e.sub {
            // Second line under the main text (product zones). Offset formula
            // mirrors tvmaps/labeling.py.
            let lines = Double(e.text.components(separatedBy: "\n").count)
            let dyPx = (st.size * (0.45 + 0.95 * (lines - 1))
                        + sub.sizePt * 0.75) * Double(m.canvas.dpi) / 72
            let at = CGPoint(x: textAt.x,
                             y: textAt.y + CGFloat(dyPx) * scale)
            drawHaloText(text: sub.text, at: at, sizePt: sub.sizePt,
                         weight: "semibold", color: e.color,
                         halo: "#ffffff", haloWidthPt: 4,
                         ha: st.ha, va: st.va, rotation: st.rotation,
                         linespacing: e.linespacing, in: ctx)
        }
    }

    private func haloWidth(_ e: LabelEntry, _ st: LabelState) -> Double {
        // The exporter records the width for the exported size; recompute the
        // default rule when the size has been edited.
        if abs(st.size - e.sizePt) < 0.01 { return e.halo.widthPt }
        return max(2.5, st.size / 9)
    }

    private func drawLeader(_ e: LabelEntry, from: CGPoint, to: CGPoint,
                            in ctx: CGContext) {
        let color = UIColor(hex: e.leader?.color ?? "#55524d")
        let widthPt = e.leader?.widthPt ?? 2.2
        let shrinkFrom = (e.leader?.shrinkFromPt ?? 8) * ptToPx * scale
        let shrinkTo = (e.leader?.shrinkToPt ?? 2) * ptToPx * scale
        let v = CGPoint(x: to.x - from.x, y: to.y - from.y)
        let len = max(sqrt(v.x * v.x + v.y * v.y), 1)
        guard len > shrinkFrom + shrinkTo else { return }
        let u = CGPoint(x: v.x / len, y: v.y / len)
        ctx.saveGState()
        ctx.setStrokeColor(color.cgColor)
        ctx.setLineWidth(CGFloat(widthPt) * ptToPx * scale)
        ctx.move(to: CGPoint(x: from.x + u.x * shrinkFrom,
                             y: from.y + u.y * shrinkFrom))
        ctx.addLine(to: CGPoint(x: to.x - u.x * shrinkTo,
                                y: to.y - u.y * shrinkTo))
        ctx.strokePath()
        ctx.restoreGState()
    }

    private func drawBadgedText(_ e: LabelEntry, _ st: LabelState,
                                _ badge: LabelEntry.Badge, at: CGPoint,
                                in ctx: CGContext) {
        // Group layout mirrors draw.numbered_label: circle of radius r, a gap
        // of 0.9r, then the name; the whole group anchored per ha/va.
        let sizePx = CGFloat(st.size) * ptToPx * scale
        let r = 0.9 * sizePx
        let gap = 0.9 * r
        let nameSize = measure(text: e.text.replacingOccurrences(of: "\n",
                                                                 with: " "),
                               sizePt: st.size, weight: e.weight,
                               linespacing: e.linespacing)
        let groupW = 2 * r + gap + nameSize.width
        let left: CGFloat
        switch st.ha {
        case "left": left = at.x
        case "right": left = at.x - groupW
        default: left = at.x - groupW / 2
        }
        let cy: CGFloat
        switch st.va {
        case "bottom": cy = at.y - r
        case "top": cy = at.y + r
        default: cy = at.y
        }
        let center = CGPoint(x: left + r, y: cy)
        ctx.saveGState()
        ctx.setFillColor(UIColor(hex: badge.face).cgColor)
        ctx.setStrokeColor(UIColor.white.cgColor)
        ctx.setLineWidth(2.2 * ptToPx * scale)
        let circle = CGRect(x: center.x - r, y: center.y - r,
                            width: 2 * r, height: 2 * r)
        ctx.fillEllipse(in: circle)
        ctx.strokeEllipse(in: circle)
        ctx.restoreGState()
        drawText(text: "\(badge.number)", at: center,
                 sizePt: st.size * 0.72, weight: "extrabold",
                 color: badge.numberColor, ha: "center", va: "center",
                 rotation: 0, linespacing: 1, in: ctx)
        drawHaloText(text: e.text, at: CGPoint(x: center.x + r + gap, y: cy),
                     sizePt: st.size, weight: e.weight, color: e.color,
                     halo: e.halo.color, haloWidthPt: haloWidth(e, st),
                     ha: "left", va: "center", rotation: 0,
                     linespacing: e.linespacing, in: ctx)
    }

    private func drawSelection(_ e: LabelEntry, _ st: LabelState,
                               in ctx: CGContext) {
        let k = manifest!.kmPerPx
        let p = viewPoint(st.textPx(anchor: e.anchorPx, kmPerPx: k))
        let size = measure(text: e.text, sizePt: st.size, weight: e.weight,
                           linespacing: e.linespacing)
        let pad: CGFloat = 8
        var rect = CGRect(origin: alignedOrigin(p, size, ha: st.ha, va: st.va),
                          size: size).insetBy(dx: -pad, dy: -pad)
        if e.badge != nil {
            rect = rect.insetBy(dx: -2.2 * CGFloat(st.size) * ptToPx * scale,
                                dy: 0)
        }
        ctx.saveGState()
        ctx.setStrokeColor((editing ? UIColor.systemOrange
                                    : UIColor.systemBlue).cgColor)
        ctx.setLineWidth(3)
        ctx.setLineDash(phase: 0, lengths: editing ? [] : [8, 6])
        ctx.stroke(rect.integral)
        ctx.restoreGState()
    }

    // MARK: Text primitives

    /// 1 pt = DPI/72 canvas px (DPI is 100 for every map).
    private var ptToPx: CGFloat {
        CGFloat(manifest?.canvas.dpi ?? 100) / 72
    }

    private func font(sizePt: Double, weight: String) -> UIFont {
        let names = ["regular": "Inter-Regular",
                     "semibold": "Inter-SemiBold",
                     "extrabold": "Inter-ExtraBold"]
        let px = CGFloat(sizePt) * ptToPx * scale
        return UIFont(name: names[weight] ?? "Inter-SemiBold", size: px)
            ?? UIFont.systemFont(ofSize: px)
    }

    private func paragraphStyle(ha: String, linespacing: Double)
        -> NSParagraphStyle {
        let p = NSMutableParagraphStyle()
        p.alignment = ha == "left" ? .left : ha == "right" ? .right : .center
        p.lineHeightMultiple = CGFloat(linespacing)
        return p
    }

    private func attributes(sizePt: Double, weight: String, color: String,
                            ha: String, linespacing: Double)
        -> [NSAttributedString.Key: Any] {
        [.font: font(sizePt: sizePt, weight: weight),
         .foregroundColor: UIColor(hex: color),
         .paragraphStyle: paragraphStyle(ha: ha, linespacing: linespacing)]
    }

    private func measure(text: String, sizePt: Double, weight: String,
                         linespacing: Double) -> CGSize {
        let attrs = attributes(sizePt: sizePt, weight: weight,
                               color: "#000000", ha: "center",
                               linespacing: linespacing)
        return (text as NSString).boundingRect(
            with: CGSize(width: CGFloat.greatestFiniteMagnitude,
                         height: CGFloat.greatestFiniteMagnitude),
            options: [.usesLineFragmentOrigin], attributes: attrs,
            context: nil).size
    }

    private func alignedOrigin(_ p: CGPoint, _ size: CGSize,
                               ha: String, va: String) -> CGPoint {
        let x: CGFloat
        switch ha {
        case "left": x = p.x
        case "right": x = p.x - size.width
        default: x = p.x - size.width / 2
        }
        let y: CGFloat
        switch va {
        case "top": y = p.y
        case "bottom": y = p.y - size.height
        default: y = p.y - size.height / 2
        }
        return CGPoint(x: x, y: y)
    }

    private func drawHaloText(text: String, at: CGPoint, sizePt: Double,
                              weight: String, color: String, halo: String,
                              haloWidthPt: Double, ha: String, va: String,
                              rotation: Double, linespacing: Double,
                              in ctx: CGContext) {
        // Stroke pass under the fill pass, like matplotlib's withStroke.
        // NSAttributedString strokeWidth is a percentage of the font size.
        var strokeAttrs = attributes(sizePt: sizePt, weight: weight,
                                     color: color, ha: ha,
                                     linespacing: linespacing)
        strokeAttrs[.strokeColor] = UIColor(hex: halo)
        strokeAttrs[.strokeWidth] = haloWidthPt / sizePt * 100
        draw(text: text, at: at, attrs: strokeAttrs, ha: ha, va: va,
             rotation: rotation, linespacing: linespacing,
             sizePt: sizePt, weight: weight, in: ctx)
        let fillAttrs = attributes(sizePt: sizePt, weight: weight,
                                   color: color, ha: ha,
                                   linespacing: linespacing)
        draw(text: text, at: at, attrs: fillAttrs, ha: ha, va: va,
             rotation: rotation, linespacing: linespacing,
             sizePt: sizePt, weight: weight, in: ctx)
    }

    private func drawText(text: String, at: CGPoint, sizePt: Double,
                          weight: String, color: String, ha: String,
                          va: String, rotation: Double, linespacing: Double,
                          in ctx: CGContext) {
        let attrs = attributes(sizePt: sizePt, weight: weight, color: color,
                               ha: ha, linespacing: linespacing)
        draw(text: text, at: at, attrs: attrs, ha: ha, va: va,
             rotation: rotation, linespacing: linespacing,
             sizePt: sizePt, weight: weight, in: ctx)
    }

    private func draw(text: String, at: CGPoint,
                      attrs: [NSAttributedString.Key: Any], ha: String,
                      va: String, rotation: Double, linespacing: Double,
                      sizePt: Double, weight: String, in ctx: CGContext) {
        let size = measure(text: text, sizePt: sizePt, weight: weight,
                           linespacing: linespacing)
        ctx.saveGState()
        ctx.translateBy(x: at.x, y: at.y)
        if rotation != 0 {
            // Cartographic rotation is counter-clockwise; view y is down.
            ctx.rotate(by: CGFloat(-rotation * .pi / 180))
        }
        let origin = alignedOrigin(.zero, size, ha: ha, va: va)
        (text as NSString).draw(
            with: CGRect(origin: origin, size: size),
            options: [.usesLineFragmentOrigin], attributes: attrs,
            context: nil)
        ctx.restoreGState()
    }
}

extension UIColor {
    convenience init(hex: String) {
        var value: UInt64 = 0
        let hexString = hex.hasPrefix("#") ? String(hex.dropFirst()) : hex
        Scanner(string: hexString).scanHexInt64(&value)
        self.init(red: CGFloat((value >> 16) & 0xFF) / 255,
                  green: CGFloat((value >> 8) & 0xFF) / 255,
                  blue: CGFloat(value & 0xFF) / 255, alpha: 1)
    }
}

// MARK: SwiftUI bridge

struct LabelCanvas: UIViewRepresentable {
    let baseImage: UIImage?
    let manifest: Manifest
    let states: [String: LabelState]
    let selectedID: String?
    let editing: Bool

    func makeUIView(context: Context) -> LabelCanvasView {
        LabelCanvasView(frame: .zero)
    }

    func updateUIView(_ view: LabelCanvasView, context: Context) {
        view.baseImage = baseImage
        view.manifest = manifest
        view.states = states
        view.selectedID = selectedID
        view.editing = editing
    }
}
