import XCTest
@testable import MapEditor

/// URLProtocol stub so RepoClient can be tested without the network.
final class StubProtocol: URLProtocol {
    static var handler: ((URLRequest) -> (Int, Data))?
    static var requests: [URLRequest] = []

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for r: URLRequest) -> URLRequest { r }

    override func startLoading() {
        Self.requests.append(request)
        let (status, data) = Self.handler!(request)
        let response = HTTPURLResponse(url: request.url!, statusCode: status,
                                       httpVersion: nil, headerFields: nil)!
        client?.urlProtocol(self, didReceive: response,
                            cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: data)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

final class RepoClientTests: XCTestCase {
    private func makeClient() -> RepoClient {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [StubProtocol.self]
        var client = RepoClient(session: URLSession(configuration: config))
        client.branch = "test-branch"
        client.token = { "test-token" }
        return client
    }

    override func setUp() {
        StubProtocol.requests = []
    }

    private static func contentsJSON(_ file: OverridesFile,
                                     sha: String) -> Data {
        let content = try! file.encoded().base64EncodedString()
        return try! JSONSerialization.data(withJSONObject: [
            "sha": sha, "content": content, "encoding": "base64"])
    }

    func testFetchOverrides404MeansNoFile() async throws {
        StubProtocol.handler = { _ in (404, Data("{}".utf8)) }
        let remote = try await makeClient().fetchOverrides(map: "x")
        XCTAssertNil(remote.file)
        XCTAssertNil(remote.sha)
    }

    func testFetchOverridesDecodesContent() async throws {
        let file = OverridesFile(map: "x",
                                 labels: ["a": ["dx": .number(3)]])
        StubProtocol.handler = { _ in
            (200, Self.contentsJSON(file, sha: "abc123"))
        }
        let remote = try await makeClient().fetchOverrides(map: "x")
        XCTAssertEqual(remote.sha, "abc123")
        XCTAssertEqual(remote.file?.labels["a"]?["dx"], .number(3))
    }

    func testPutSendsShaAndMergedContent() async throws {
        StubProtocol.handler = { request in
            (200, Data(#"{"content": {"sha": "new-sha"}}"#.utf8))
        }
        let fetched = OverridesFile(map: "x",
                                    labels: ["keep": ["dy": .number(1)]])
        let result = try await makeClient().putOverrides(
            map: "x", edits: ["a": ["dx": .number(9)]],
            remote: .init(file: fetched, sha: "old-sha"), message: "test")
        XCTAssertEqual(result.sha, "new-sha")
        XCTAssertEqual(result.file?.labels.count, 2)

        let put = try XCTUnwrap(StubProtocol.requests.first {
            $0.httpMethod == "PUT" })
        XCTAssertEqual(put.value(forHTTPHeaderField: "Authorization"),
                       "Bearer test-token")
        let stream = try XCTUnwrap(put.httpBodyStream)
        stream.open()
        var body = Data()
        let buffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 65536)
        defer { buffer.deallocate() }
        while stream.hasBytesAvailable {
            let n = stream.read(buffer, maxLength: 65536)
            if n <= 0 { break }
            body.append(buffer, count: n)
        }
        let payload = try XCTUnwrap(
            try JSONSerialization.jsonObject(with: body) as? [String: Any])
        XCTAssertEqual(payload["sha"] as? String, "old-sha")
        XCTAssertEqual(payload["branch"] as? String, "test-branch")
        let sent = try XCTUnwrap(Data(base64Encoded:
            payload["content"] as! String))
        let decoded = try JSONDecoder().decode(OverridesFile.self, from: sent)
        XCTAssertEqual(decoded.labels["a"]?["dx"], .number(9))
        XCTAssertEqual(decoded.labels["keep"]?["dy"], .number(1))
    }

    func testPutRetriesOnceOn409() async throws {
        var puts = 0
        let fresh = OverridesFile(map: "x",
                                  labels: ["other": ["dx": .number(5)]])
        StubProtocol.handler = { request in
            if request.httpMethod == "PUT" {
                puts += 1
                if puts == 1 { return (409, Data("{}".utf8)) }
                return (200, Data(#"{"content": {"sha": "s2"}}"#.utf8))
            }
            return (200, Self.contentsJSON(fresh, sha: "fresh-sha"))
        }
        let result = try await makeClient().putOverrides(
            map: "x", edits: ["a": ["dx": .number(9)]],
            remote: .init(file: nil, sha: nil), message: "test")
        XCTAssertEqual(puts, 2)
        XCTAssertEqual(result.sha, "s2")
        // The retry merged our edit over the freshly fetched file.
        XCTAssertEqual(result.file?.labels["other"]?["dx"], .number(5))
        XCTAssertEqual(result.file?.labels["a"]?["dx"], .number(9))
    }

    func testPutWithoutTokenFails() async {
        var client = makeClient()
        client.token = { nil }
        do {
            _ = try await client.putOverrides(
                map: "x", edits: [:], remote: .init(file: nil, sha: nil),
                message: "test")
            XCTFail("expected noToken")
        } catch { /* expected */ }
    }
}
