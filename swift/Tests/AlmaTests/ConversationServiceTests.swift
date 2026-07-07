import Testing
import Foundation
@testable import Alma

@MainActor
extension NetworkingTests {

    @Test("list conversations populates conversations array")
    func testServiceListConversations() async throws {
        try await withMock(json: """
        [{"id":"1","title":"Chat 1","mode":"chat","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}]
        """) {
            let service = ConversationService(api: ConversationAPI(client: makeClient()))
            await service.loadConversations()
            #expect(service.conversations.count == 1)
            #expect(service.conversations[0].title == "Chat 1")
            #expect(service.isLoading == false)
            #expect(service.error == nil)
        }
    }

    @Test("empty list shows no conversations")
    func testServiceEmptyList() async throws {
        try await withMock(json: "[]") {
            let service = ConversationService(api: ConversationAPI(client: makeClient()))
            await service.loadConversations()
            #expect(service.conversations.isEmpty)
            #expect(service.selectedConversation == nil)
        }
    }

    @Test("load conversation populates selected conversation")
    func testServiceLoadConversation() async throws {
        try await withMock(json: """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-01T00:00:00Z","content":"Hello"}]}
        """) {
            let service = ConversationService(api: ConversationAPI(client: makeClient()))
            await service.selectConversation("1")
            #expect(service.selectedConversation != nil)
            #expect(service.selectedConversation?.title == "Chat 1")
            #expect(service.selectedConversation?.messages.count == 1)
            #expect(service.selectedId == "1")
        }
    }

    @Test("create conversation adds to list and selects it")
    func testServiceCreateConversation() async throws {
        let responseJSON = """
        {"id":"new-id","title":"New Chat","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        try await withMock(json: responseJSON, statusCode: 201) {
            let service = ConversationService(api: ConversationAPI(client: makeClient()))
            await service.createConversation()
            #expect(service.conversations.count == 1)
            #expect(service.conversations[0].id == "new-id")
            #expect(service.selectedConversation?.id == "new-id")
            #expect(service.selectedId == "new-id")
        }
    }

    @Test("restore loads saved conversation on launch")
    func testServiceRestoreConversation() async throws {
        let savedId = "saved-1"
        let defaults = UserDefaults(suiteName: "test-restore-\(UUID().uuidString)")!
        defaults.set(savedId, forKey: "selectedConversationId")

        let listJSON = """
        [{"id":"saved-1","title":"Saved Chat","mode":"chat","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}]
        """
        let convJSON = """
        {"id":"saved-1","title":"Saved Chat","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-01T00:00:00Z","content":"Hello"}]}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 1 {
                    let data = Data(listJSON.utf8)
                    let response = try #require(HTTPURLResponse(
                        url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "application/json"]
                    ))
                    return (response, data)
                }
                let data = Data(convJSON.utf8)
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = ConversationService(
                api: ConversationAPI(client: makeClient()),
                defaults: defaults
            )
            await service.loadConversations()
            #expect(service.selectedConversation?.id == "saved-1")
            #expect(service.selectedConversation?.title == "Saved Chat")
            #expect(service.selectedId == "saved-1")
            #expect(callCount == 2)
        }
    }

    @Test("restore falls back gracefully when saved conversation is gone")
    func testServiceRestoreFallback() async throws {
        let savedId = "deleted-id"
        let defaults = UserDefaults(suiteName: "test-fallback-\(UUID().uuidString)")!
        defaults.set(savedId, forKey: "selectedConversationId")

        let listJSON = """
        [{"id":"other-1","title":"Other Chat","mode":"chat","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}]
        """

        try await withMock(json: listJSON) {
            let service = ConversationService(
                api: ConversationAPI(client: makeClient()),
                defaults: defaults
            )
            await service.loadConversations()
            #expect(service.conversations.count == 1)
            #expect(service.selectedConversation == nil)
            #expect(service.selectedId == nil)
        }
    }

    @Test("API failure sets error and clears state")
    func testServiceError() async throws {
        try await withMock(json: """
        {"error":"Internal server error"}
        """, statusCode: 500) {
            let service = ConversationService(api: ConversationAPI(client: makeClient()))
            await service.loadConversations()
            #expect(service.error != nil)
            #expect(service.conversations.isEmpty)
            #expect(service.isLoading == false)
        }
    }

    @Test("selecting nonexistent conversation clears selection")
    func testServiceSelectNotFound() async throws {
        try await withMock(json: """
        {"error":"Conversation not found"}
        """, statusCode: 404) {
            let service = ConversationService(api: ConversationAPI(client: makeClient()))
            await service.selectConversation("nonexistent")
            #expect(service.selectedConversation == nil)
            #expect(service.selectedId == nil)
            #expect(service.error != nil)
        }
    }
}
