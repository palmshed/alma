import Testing
import Foundation
@testable import Alma

final class MockURLProtocol: URLProtocol {
    nonisolated(unsafe) static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        guard let handler = Self.requestHandler else {
            fatalError("No mock handler set")
        }
        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

func makeClient() -> APIClient {
    let config = URLSessionConfiguration.ephemeral
    config.protocolClasses = [MockURLProtocol.self]
    let session = URLSession(configuration: config)
    return APIClient(baseURL: URL(string: "http://localhost:8080")!, session: session)
}

@Suite(.serialized) struct NetworkingTests {

    // MARK: - APIClient

    @Test("GET request decodes response")
    func testGet() async throws {
        try await withMock(json: """
        {"id":"1","title":"Test","mode":"chat","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}
        """) {
            let entry: ConversationIndexEntry = try await makeClient().get("/api/conversations")
            #expect(entry.id == "1")
            #expect(entry.title == "Test")
        }
    }

    @Test("POST request encodes body and decodes response")
    func testPost() async throws {
        let msg = ChatMessage(id: "m1", role: "user", timestamp: "2025-01-01T00:00:00Z", content: "Hello")
        let conversation = Conversation(
            id: "1", title: "New Chat", mode: "chat",
            createdAt: "2025-01-01T00:00:00Z", updatedAt: "2025-01-01T00:00:00Z",
            messages: [msg]
        )
        try await withMock(json: """
        {"id":"1","title":"New Chat","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-01T00:00:00Z","content":"Hello"}]}
        """, statusCode: 201) {
            let created: Conversation = try await makeClient().post("/api/conversations", body: conversation)
            #expect(created.id == "1")
            #expect(created.messages.count == 1)
            #expect(created.messages[0].content == "Hello")
        }
    }

    @Test("PUT request encodes body and decodes response")
    func testPut() async throws {
        let msg = ChatMessage(id: "m1", role: "user", timestamp: "2025-01-01T00:00:00Z", content: "Updated")
        let conversation = Conversation(
            id: "1", title: "Updated Chat", mode: "chat",
            createdAt: "2025-01-01T00:00:00Z", updatedAt: "2025-01-01T00:00:00Z",
            messages: [msg]
        )
        try await withMock(json: """
        {"id":"1","title":"Updated Chat","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-01T00:00:00Z","content":"Updated"}]}
        """) {
            let updated: Conversation = try await makeClient().put("/api/conversations/1", body: conversation)
            #expect(updated.title == "Updated Chat")
            #expect(updated.messages[0].content == "Updated")
        }
    }

    @Test("DELETE request returns no content")
    func testDeleteNoContent() async throws {
        try await withMock(data: Data(), statusCode: 204) {
            let client = makeClient()
            let request = try client.buildRequest(path: "/api/conversations/1", method: "DELETE")
            try await client.performWithoutBody(request)
        }
    }

    @Test("HTTP 404 throws not found error")
    func testNotFound() async throws {
        try await withMock(json: """
        {"error":"Conversation not found"}
        """, statusCode: 404) {
            do {
                let _: Conversation = try await makeClient().get("/api/conversations/nonexistent")
                #expect(Bool(false), "Expected error to be thrown")
            } catch APIError.httpError(let code, let message) {
                #expect(code == 404)
                #expect(message == "Conversation not found")
            }
        }
    }

    @Test("HTTP 500 throws server error")
    func testServerError() async throws {
        try await withMock(json: """
        {"error":"Internal server error"}
        """, statusCode: 500) {
            do {
                let _: [ConversationIndexEntry] = try await makeClient().get("/api/conversations")
                #expect(Bool(false), "Expected error to be thrown")
            } catch APIError.httpError(let code, let message) {
                #expect(code == 500)
                #expect(message == "Internal server error")
            }
        }
    }

    // MARK: - ConversationAPI

    @Test("list returns conversation index entries")
    func testConversationList() async throws {
        try await withMock(json: """
        [{"id":"1","title":"Chat 1","mode":"chat","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"},{"id":"2","title":"Chat 2","mode":"chat","created_at":"2025-01-02T00:00:00Z","updated_at":"2025-01-02T00:00:00Z"}]
        """) {
            let api = ConversationAPI(client: makeClient())
            let entries = try await api.list()
            #expect(entries.count == 2)
            #expect(entries[0].title == "Chat 1")
            #expect(entries[1].id == "2")
        }
    }

    @Test("get returns single conversation")
    func testConversationGet() async throws {
        try await withMock(json: """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-01T00:00:00Z","content":"Hello"}]}
        """) {
            let api = ConversationAPI(client: makeClient())
            let conv = try await api.get(id: "1")
            #expect(conv.title == "Chat 1")
            #expect(conv.messages.count == 1)
        }
    }

    @Test("create returns created conversation")
    func testConversationCreate() async throws {
        try await withMock(json: """
        {"id":"new-id","title":"New Chat","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """, statusCode: 201) {
            let api = ConversationAPI(client: makeClient())
            let conv = Conversation(
                id: "new-id", title: "New Chat", mode: "chat",
                createdAt: "2025-01-01T00:00:00Z", updatedAt: "2025-01-01T00:00:00Z",
                messages: []
            )
            let created = try await api.create(conv)
            #expect(created.id == "new-id")
        }
    }

    @Test("conversation delete removes conversation")
    func testConversationDelete() async throws {
        try await withMock(data: Data(), statusCode: 204) {
            let api = ConversationAPI(client: makeClient())
            try await api.delete(id: "1")
        }
    }

    // MARK: - GenerationAPI

    @Test("generate with prompt returns response")
    func testGeneratePrompt() async throws {
        try await withMock(json: """
        {"response":"Hello! How can I help you?"}
        """) {
            let api = GenerationAPI(client: makeClient())
            let result = try await api.generate(prompt: "Hi")
            #expect(result == "Hello! How can I help you?")
        }
    }

    @Test("generate with messages returns response")
    func testGenerateMessages() async throws {
        try await withMock(json: """
        {"response":"I remember our conversation."}
        """) {
            let api = GenerationAPI(client: makeClient())
            let messages = [ChatMessage(id: "1", role: "user", timestamp: "", content: "Do you remember?")]
            let result = try await api.generate(messages: messages)
            #expect(result == "I remember our conversation.")
        }
    }

    @Test("generate with thinking returns response and thinking summary")
    func testGenerateWithThinking() async throws {
        try await withMock(json: """
        {"response":"Here is my answer.","thinking_summary":["Step 1: thinking","Step 2: more thinking"]}
        """) {
            let api = GenerationAPI(client: makeClient())
            let result = try await api.generateWithThinking(prompt: "Think about this")
            #expect(result.response == "Here is my answer.")
            #expect(result.thinkingSummary.count == 2)
            #expect(result.thinkingSummary[0] == "Step 1: thinking")
        }
    }

    @Test("generate with URL context returns response")
    func testGenerateWithURLContext() async throws {
        try await withMock(json: """
        {"response":"Based on the URL content..."}
        """) {
            let api = GenerationAPI(client: makeClient())
            let result = try await api.generateWithURLContext(prompt: "Summarize this URL")
            #expect(result == "Based on the URL content...")
        }
    }

    // MARK: - AttachmentAPI

    @Test("upload returns attachment metadata")
    func testUpload() async throws {
        try await withMock(json: """
        {"id":"att-1","filename":"photo.png","mime_type":"image/png","size":1234,"checksum":"abc123","storage_key":"attachments/att-1.bin","created_at":"2025-01-01T00:00:00Z"}
        """, statusCode: 201) {
            let api = AttachmentAPI(client: makeClient())
            let attachment = try await api.upload(
                data: Data("fake-png".utf8),
                filename: "photo.png",
                mimeType: "image/png"
            )
            #expect(attachment.id == "att-1")
            #expect(attachment.filename == "photo.png")
            #expect(attachment.mimeType == "image/png")
            #expect(attachment.size == 1234)
        }
    }

    @Test("download returns raw data")
    func testDownload() async throws {
        let imageData = Data([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])
        try await withMock(data: imageData) {
            let api = AttachmentAPI(client: makeClient())
            let data = try await api.download(id: "att-1")
            #expect(data == imageData)
        }
    }

    @Test("get metadata returns attachment info")
    func testGetMetadata() async throws {
        try await withMock(json: """
        {"id":"att-1","filename":"doc.pdf","mime_type":"application/pdf","size":5000,"checksum":"def456","storage_key":"attachments/att-1.bin","created_at":"2025-01-01T00:00:00Z"}
        """) {
            let api = AttachmentAPI(client: makeClient())
            let metadata = try await api.getMetadata(id: "att-1")
            #expect(metadata.filename == "doc.pdf")
            #expect(metadata.mimeType == "application/pdf")
        }
    }

    @Test("attachment delete removes attachment")
    func testAttachmentDelete() async throws {
        try await withMock(data: Data(), statusCode: 204) {
            let api = AttachmentAPI(client: makeClient())
            try await api.delete(id: "att-1")
        }
    }

    // MARK: - HealthAPI

    @Test("health returns status")
    func testHealth() async throws {
        try await withMock(json: """
        {"status":"ok"}
        """) {
            let api = HealthAPI(client: makeClient())
            let health = try await api.health()
            #expect(health.status == "ok")
        }
    }

    @Test("health returns degraded status")
    func testDegraded() async throws {
        try await withMock(json: """
        {"status":"degraded"}
        """) {
            let api = HealthAPI(client: makeClient())
            let health = try await api.health()
            #expect(health.status == "degraded")
        }
    }
}

// MARK: - Helpers

func withMock<T>(
    json: String,
    statusCode: Int = 200,
    operation: () async throws -> T
) async throws -> T {
    try await withMock(
        data: Data(json.utf8),
        statusCode: statusCode,
        operation: operation
    )
}

func withMock<T>(
    data: Data,
    statusCode: Int = 200,
    operation: () async throws -> T
) async throws -> T {
    MockURLProtocol.requestHandler = { request in
        let response = try #require(HTTPURLResponse(
            url: request.url!,
            statusCode: statusCode,
            httpVersion: "HTTP/1.1",
            headerFields: ["Content-Type": "application/json"]
        ))
        return (response, data)
    }
    defer { MockURLProtocol.requestHandler = nil }
    return try await operation()
}
