import SwiftUI
import UIKit

/// The editing screen for one map.
///
/// Remote controls:
///   Browse   — left/right: previous/next label · click: move the label ·
///              play/pause: save to GitHub
///   Move     — d-pad taps: nudge 1 km (5 km on repeat) · touchpad pan:
///              drag continuously · click: confirm · menu: cancel
///   Size     — up/down: ±2 pt (long-press a label to enter) ·
///              click: confirm · menu: cancel
struct EditorView: View {
    let map: MapIndexEntry
    var client = RepoClient()

    enum Mode { case browse, move, resize }

    @State private var session: EditSession?
    @State private var baseImage: UIImage?
    @State private var remote: RepoClient.RemoteOverrides?
    @State private var mode: Mode = .browse
    @State private var status: String?
    @State private var error: String?
    @State private var saving = false

    var body: some View {
        Group {
            if let session {
                editor(session)
            } else if let error {
                VStack(spacing: 20) {
                    Text("No se pudo cargar el mapa").font(.headline)
                    Text(error).font(.caption).foregroundStyle(.secondary)
                    Button("Reintentar") { Task { await load() } }
                }
            } else {
                ProgressView("Cargando \(map.name)…")
            }
        }
        .task { await load() }
    }

    private func editor(_ session: EditSession) -> some View {
        ZStack(alignment: .topLeading) {
            PanCatcher(enabled: mode == .move) { deltaPx in
                nudgeSelected(byPx: deltaPx, session: session)
            } content: {
                LabelCanvas(baseImage: baseImage,
                            manifest: session.manifest,
                            states: session.states,
                            selectedID: session.selectedID,
                            editing: mode != .browse)
            }
            .ignoresSafeArea()
            hud(session)
        }
        .focusable()
        .onMoveCommand { direction in handleMove(direction, session: session) }
        .onExitCommand { handleExit(session: session) }
        .onPlayPauseCommand { Task { await save(session) } }
        .onLongPressGesture(minimumDuration: 0.7) {
            if mode == .browse { enter(.resize, session: session) }
        }
        .onTapGesture { handleClick(session: session) }
    }

    // MARK: HUD

    private func hud(_ session: EditSession) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            if let id = session.selectedID, let st = session.states[id] {
                Text(session.entry(id)?.text.replacingOccurrences(
                    of: "\n", with: " ") ?? id)
                    .font(.headline)
                Text(hudDetail(id: id, st: st))
                    .font(.caption).foregroundStyle(.secondary)
            }
            Text(hudHint).font(.caption2).foregroundStyle(.tertiary)
            if let status { Text(status).font(.caption).foregroundStyle(.blue) }
            if let error { Text(error).font(.caption).foregroundStyle(.red) }
            if session.isDirty && mode == .browse {
                Text("Cambios sin guardar · ▶︎ para guardar")
                    .font(.caption).foregroundStyle(.orange)
            }
        }
        .padding(24)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
        .padding(40)
    }

    private func hudDetail(id: String, st: LabelState) -> String {
        var parts = ["\(Int(st.size)) pt"]
        if st.isCallout {
            parts.append(String(format: "tx %.0f · ty %.0f", st.tx!, st.ty!))
        } else {
            parts.append(String(format: "dx %.0f · dy %.0f km", st.dx, st.dy))
        }
        if st.rotation != 0 {
            parts.append(String(format: "%.0f°", st.rotation))
        }
        return parts.joined(separator: " · ")
    }

    private var hudHint: String {
        switch mode {
        case .browse:
            return "◀︎ ▶︎ etiqueta · clic: mover · mantener: tamaño · ▶︎ guardar"
        case .move:
            return "Mover: cruceta o panel táctil · clic: fijar · menú: cancelar"
        case .resize:
            return "▲ ▼ tamaño · clic: fijar · menú: cancelar"
        }
    }

    // MARK: Input handling

    private func handleMove(_ direction: MoveCommandDirection,
                            session: EditSession) {
        switch mode {
        case .browse:
            let labels = session.manifest.labels
            guard let current = session.selectedID,
                  let i = labels.firstIndex(where: { $0.id == current })
            else {
                session.selectedID = labels.first?.id
                return
            }
            if direction == .right || direction == .down {
                session.selectedID = labels[(i + 1) % labels.count].id
            } else {
                session.selectedID = labels[(i + labels.count - 1)
                                            % labels.count].id
            }
        case .move:
            let km: Double = 1
            var d = PixelPoint(x: 0, y: 0)
            let perKm = 1 / session.manifest.kmPerPx
            switch direction {
            case .left: d.x = -km * perKm
            case .right: d.x = km * perKm
            case .up: d.y = -km * perKm
            case .down: d.y = km * perKm
            @unknown default: break
            }
            nudgeSelected(byPx: d, session: session)
        case .resize:
            guard let id = session.selectedID,
                  var st = session.states[id] else { return }
            if direction == .up { st.size += 2 }
            if direction == .down { st.size = max(12, st.size - 2) }
            session.states[id] = st
            status = st.size < 24 ? "⚠️ por debajo de 24 pt" : nil
        }
    }

    private func nudgeSelected(byPx delta: PixelPoint, session: EditSession) {
        guard mode == .move, let id = session.selectedID,
              var st = session.states[id] else { return }
        st.move(byPx: delta, kmPerPx: session.manifest.kmPerPx)
        session.states[id] = st
    }

    private func handleClick(session: EditSession) {
        switch mode {
        case .browse: enter(.move, session: session)
        case .move, .resize:
            session.commitEdit()
            mode = .browse
            status = nil
        }
    }

    private func handleExit(session: EditSession) {
        guard mode != .browse else { return }
        session.cancelEdit()
        mode = .browse
        status = nil
    }

    private func enter(_ newMode: Mode, session: EditSession) {
        guard let id = session.selectedID else { return }
        session.beginEdit(id)
        mode = newMode
    }

    // MARK: Data

    private func load() async {
        error = nil
        do {
            async let manifestTask = client.fetchManifest(map: map.name)
            async let imageTask = client.fetchData(path: map.base)
            async let overridesTask = client.fetchOverrides(map: map.name)
            let manifest = try await manifestTask
            baseImage = UIImage(data: try await imageTask)
            let fetched = try await overridesTask
            remote = fetched
            session = EditSession(manifest: manifest, fetched: fetched.file)
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func save(_ session: EditSession) async {
        guard mode == .browse, !saving else { return }
        let edits = session.edits()
        guard !edits.isEmpty else { status = "Sin cambios"; return }
        saving = true
        status = "Guardando…"
        error = nil
        do {
            let result = try await client.putOverrides(
                map: map.name, edits: edits,
                remote: remote ?? .init(file: nil, sha: nil),
                message: "Ajustes de etiquetas: \(map.name) (Map Editor)")
            remote = result
            status = "Guardado ✓ · el Action re-renderiza en ~2 min"
        } catch {
            self.error = error.localizedDescription
            status = nil
        }
        saving = false
    }
}

/// Routes Siri Remote touchpad pans to a callback, in canvas pixels.
struct PanCatcher<Content: View>: UIViewControllerRepresentable {
    let enabled: Bool
    let onPan: (PixelPoint) -> Void
    @ViewBuilder let content: () -> Content

    func makeUIViewController(context: Context) -> UIHostingController<Content> {
        let controller = UIHostingController(rootView: content())
        let pan = UIPanGestureRecognizer(
            target: context.coordinator,
            action: #selector(Coordinator.handlePan(_:)))
        pan.allowedTouchTypes = [NSNumber(value: UITouch.TouchType.indirect.rawValue)]
        controller.view.addGestureRecognizer(pan)
        context.coordinator.view = controller.view
        return controller
    }

    func updateUIViewController(_ controller: UIHostingController<Content>,
                                context: Context) {
        controller.rootView = content()
        context.coordinator.enabled = enabled
        context.coordinator.onPan = onPan
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(enabled: enabled, onPan: onPan)
    }

    final class Coordinator: NSObject {
        var enabled: Bool
        var onPan: (PixelPoint) -> Void
        weak var view: UIView?
        private var last = CGPoint.zero

        init(enabled: Bool, onPan: @escaping (PixelPoint) -> Void) {
            self.enabled = enabled
            self.onPan = onPan
        }

        @objc func handlePan(_ gesture: UIPanGestureRecognizer) {
            guard enabled, let view else { return }
            switch gesture.state {
            case .began:
                last = .zero
            case .changed:
                let t = gesture.translation(in: view)
                // Touchpad points -> canvas px: the canvas fills the view
                // horizontally at 4000 px. Slow the mapping down for control.
                let pxPerPoint = 4000 / view.bounds.width * 0.55
                let delta = PixelPoint(x: Double((t.x - last.x) * pxPerPoint),
                                       y: Double((t.y - last.y) * pxPerPoint))
                last = t
                onPan(delta)
            default:
                break
            }
        }
    }
}
