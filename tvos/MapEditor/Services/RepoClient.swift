import Foundation

/// Reads map artifacts from the public repo and writes overrides through the
/// GitHub Contents API. Reads are unauthenticated; the single write path
/// uses a fine-grained PAT scoped to this repository.
struct RepoClient {
    var owner = "dvrensk"
    var repo = "static-tv-maps"
    var branch = "main"
    var session: URLSession = .shared
    var token: () -> String? = { Keychain.string(for: Keychain.tokenKey) }

    var rawBase: URL {
        URL(string: "https://raw.githubusercontent.com/\(owner)/\(repo)/\(branch)/")!
    }

    var apiBase: URL {
        URL(string: "https://api.github.com/repos/\(owner)/\(repo)/")!
    }

    enum ClientError: LocalizedError {
        case http(Int, String)
        case noToken
        case conflictRetryFailed

        var errorDescription: String? {
            switch self {
            case .http(let code, let body): return "HTTP \(code): \(body)"
            case .noToken: return "No GitHub token configured (Ajustes)."
            case .conflictRetryFailed: return "Conflicto al guardar; reintenta."
            }
        }
    }

    // MARK: Reads (raw.githubusercontent.com)

    func fetchData(path: String) async throws -> Data {
        var request = URLRequest(url: rawBase.appending(path: path))
        request.cachePolicy = .reloadIgnoringLocalCacheData
        let (data, response) = try await session.data(for: request)
        try Self.check(response, data)
        return data
    }

    func fetchIndex() async throws -> MapIndex {
        try JSONDecoder.manifest.decode(
            MapIndex.self, from: try await fetchData(path: "editor/index.json"))
    }

    func fetchManifest(map: String) async throws -> Manifest {
        try JSONDecoder.manifest.decode(
            Manifest.self,
            from: try await fetchData(path: "editor/\(map)/labels.json"))
    }

    // MARK: Overrides via the Contents API

    struct RemoteOverrides {
        var file: OverridesFile?
        var sha: String?
    }

    private struct ContentsResponse: Codable {
        let sha: String
        let content: String?
        let encoding: String?
    }

    private func contentsURL(map: String) -> URL {
        apiBase.appending(path: "contents/overrides/\(map).json")
    }

    private func apiRequest(_ url: URL, method: String = "GET") -> URLRequest {
        var r = URLRequest(url: url)
        r.httpMethod = method
        r.setValue("application/vnd.github+json", forHTTPHeaderField: "Accept")
        r.setValue("2022-11-28", forHTTPHeaderField: "X-GitHub-Api-Version")
        if let token = token() {
            r.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return r
    }

    func fetchOverrides(map: String) async throws -> RemoteOverrides {
        var url = contentsURL(map: map)
        url.append(queryItems: [URLQueryItem(name: "ref", value: branch)])
        let (data, response) = try await session.data(for: apiRequest(url))
        if let http = response as? HTTPURLResponse, http.statusCode == 404 {
            return RemoteOverrides(file: nil, sha: nil)
        }
        try Self.check(response, data)
        let contents = try JSONDecoder().decode(ContentsResponse.self, from: data)
        guard let base64 = contents.content,
              let decoded = Data(base64Encoded: base64,
                                 options: .ignoreUnknownCharacters) else {
            return RemoteOverrides(file: nil, sha: contents.sha)
        }
        let file = try JSONDecoder().decode(OverridesFile.self, from: decoded)
        return RemoteOverrides(file: file, sha: contents.sha)
    }

    /// PUT the merged overrides file. On a 409 (someone else pushed since we
    /// fetched the sha) re-fetch once, re-merge the same edits, and retry.
    @discardableResult
    func putOverrides(map: String, edits: [String: LabelOverride],
                      remote: RemoteOverrides,
                      message: String) async throws -> RemoteOverrides {
        guard token() != nil else { throw ClientError.noToken }
        var attempt = remote
        for retry in 0...1 {
            let base = attempt.file ?? OverridesFile(map: map)
            let merged = base.merging(edits: edits)
            var body: [String: Any] = [
                "message": message,
                "content": try merged.encoded().base64EncodedString(),
                "branch": branch,
            ]
            if let sha = attempt.sha { body["sha"] = sha }
            var request = apiRequest(contentsURL(map: map), method: "PUT")
            request.httpBody = try JSONSerialization.data(
                withJSONObject: body, options: [.sortedKeys])
            let (data, response) = try await session.data(for: request)
            if let http = response as? HTTPURLResponse,
               http.statusCode == 409 || http.statusCode == 422 {
                if retry == 1 { throw ClientError.conflictRetryFailed }
                attempt = try await fetchOverrides(map: map)
                continue
            }
            try Self.check(response, data)
            struct PutResponse: Codable {
                struct Content: Codable { let sha: String }
                let content: Content
            }
            let put = try JSONDecoder().decode(PutResponse.self, from: data)
            return RemoteOverrides(file: (attempt.file ?? OverridesFile(map: map))
                .merging(edits: edits), sha: put.content.sha)
        }
        throw ClientError.conflictRetryFailed
    }

    static func check(_ response: URLResponse, _ data: Data) throws {
        guard let http = response as? HTTPURLResponse else { return }
        guard (200..<300).contains(http.statusCode) else {
            throw ClientError.http(http.statusCode,
                                   String(data: data.prefix(300),
                                          encoding: .utf8) ?? "")
        }
    }
}
