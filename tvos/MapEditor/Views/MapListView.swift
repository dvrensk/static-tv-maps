import SwiftUI

struct MapListView: View {
    var client = RepoClient()

    @State private var index: MapIndex?
    @State private var error: String?
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            Group {
                if let index {
                    List {
                        ForEach(index.maps) { map in
                            NavigationLink(value: map) {
                                HStack {
                                    Text(map.name)
                                    Spacer()
                                    Text("\(map.labels) etiquetas")
                                        .foregroundStyle(.secondary)
                                        .font(.caption)
                                }
                            }
                        }
                    }
                } else if let error {
                    VStack(spacing: 20) {
                        Text("No se pudo cargar el índice").font(.headline)
                        Text(error).font(.caption)
                            .foregroundStyle(.secondary)
                        Button("Reintentar") { Task { await load() } }
                    }
                } else {
                    ProgressView("Cargando mapas…")
                }
            }
            .navigationTitle("Mapas")
            .navigationDestination(for: MapIndexEntry.self) { map in
                EditorView(map: map, client: client)
            }
            .toolbar {
                Button("Ajustes") { showSettings = true }
            }
            .sheet(isPresented: $showSettings) { SettingsView() }
        }
        .task { await load() }
    }

    private func load() async {
        error = nil
        do {
            index = try await client.fetchIndex()
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct SettingsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var token = Keychain.string(for: Keychain.tokenKey) ?? ""

    var body: some View {
        VStack(spacing: 30) {
            Text("Token de GitHub").font(.title2)
            Text("Fine-grained PAT con permiso Contents (read/write) "
                 + "solo sobre dvrensk/static-tv-maps. Puedes escribirlo "
                 + "con el teclado del iPhone.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            TextField("github_pat_…", text: $token)
                .textContentType(.password)
                .frame(maxWidth: 900)
            HStack {
                Button("Guardar") {
                    if token.isEmpty {
                        Keychain.delete(Keychain.tokenKey)
                    } else {
                        Keychain.set(token, for: Keychain.tokenKey)
                    }
                    dismiss()
                }
                Button("Cancelar") { dismiss() }
            }
        }
        .padding(60)
    }
}
