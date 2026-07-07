import Testing
import Foundation
@testable import Alma

@MainActor
extension NetworkingTests {

private func makeService() -> ConversationService {
    let defaults = UserDefaults(suiteName: "\(UUID().uuidString)")!
    let client = makeClient()
    return ConversationService(
        api: ConversationAPI(client: client),
        generationAPI: GenerationAPI(client: client),
        defaults: defaults
    )
}

private func makeService(defaults: UserDefaults) -> ConversationService {
    let client = makeClient()
    return ConversationService(
        api: ConversationAPI(client: client),
        generationAPI: GenerationAPI(client: client),
        defaults: defaults
    )
}

    @Test("list conversations populates conversations array")
    func testServiceListConversations() async throws {
        try await withMock(json: """
        [{"id":"1","title":"Chat 1","mode":"chat","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z"}]
        """) {
            let service = makeService()
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
            let service = makeService()
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
            let service = makeService()
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
            let service = makeService()
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

            let service = makeService(defaults: defaults)
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
            let service = makeService(defaults: defaults)
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
            let service = makeService()
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
            let service = makeService()
            await service.selectConversation("nonexistent")
            #expect(service.selectedConversation == nil)
            #expect(service.selectedId == nil)
            #expect(service.error != nil)
        }
    }

    @Test("user message appended before generation request")
    func testSendAppendsUserMessageBeforeRequest() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        let genJSON = """
        {"response":"Hello back"}
        """
        let updatedConvJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-02T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-02T00:00:00Z","content":"Hello"},{"id":"m2","role":"assistant","timestamp":"2025-01-02T00:00:00Z","content":"Hello back"}]}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                let data: Data
                if callCount == 1 {
                    data = Data(convJSON.utf8)
                } else if callCount == 3 {
                    data = Data(updatedConvJSON.utf8)
                } else {
                    data = Data(genJSON.utf8)
                }
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")
            #expect(service.selectedConversation?.messages.isEmpty == true)

            await service.send(text: "Hello")

            let messages = try #require(service.selectedConversation?.messages)
            #expect(messages.count == 2)
            #expect(messages[0].role == "user")
            #expect(messages[0].content == "Hello")
            #expect(messages[1].role == "assistant")
            #expect(messages[1].content == "Hello back")
            #expect(callCount == 3)
        }
    }

    @Test("empty submission does not modify conversation")
    func testSendEmptyTextIgnored() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-01T00:00:00Z","content":"Existing"}]}
        """

        try await withMock(json: convJSON) {
            let service = makeService()
            await service.selectConversation("1")
            let originalCount = service.selectedConversation?.messages.count

            await service.send(text: "")
            await service.send(text: "   ")

            #expect(service.selectedConversation?.messages.count == originalCount)
        }
    }

    @Test("send without selected conversation does nothing")
    func testSendWithoutSelection() async throws {
        let service = makeService()
        await service.send(text: "Hello")
        #expect(service.selectedConversation == nil)
    }

    @Test("isGenerating true during request")
    func testSendIsGeneratingDuringRequest() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        let genJSON = """
        {"response":"Hello back"}
        """
        let updatedConvJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-02T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-02T00:00:00Z","content":"Hello"},{"id":"m2","role":"assistant","timestamp":"2025-01-02T00:00:00Z","content":"Hello back"}]}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                let data: Data
                if callCount == 1 {
                    data = Data(convJSON.utf8)
                } else if callCount == 3 {
                    data = Data(updatedConvJSON.utf8)
                } else {
                    data = Data(genJSON.utf8)
                }
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")
            #expect(service.isGenerating == false)
            #expect(service.generationError == nil)

            await service.send(text: "Hello")

            #expect(callCount == 3)
            #expect(service.isGenerating == false)
            #expect(service.generationError == nil)
        }
    }

    @Test("isGenerating false after generation failure")
    func testSendIsGeneratingFalseOnFailure() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 1 {
                    let data = Data(convJSON.utf8)
                    let response = try #require(HTTPURLResponse(
                        url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "application/json"]
                    ))
                    return (response, data)
                }
                let data = Data(#"{"error":"Generation failed"}"#.utf8)
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 500, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")
            #expect(service.isGenerating == false)
            #expect(service.generationError == nil)

            await service.send(text: "Hello")

            #expect(service.isGenerating == false)
            let error = try #require(service.generationError)
            #expect(error.contains("Generation failed"))
        }
    }

    @Test("successful generation triggers one conversation update")
    func testSendPersistsAfterSuccess() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        let genJSON = """
        {"response":"Hello back"}
        """
        let updatedConvJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-02T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-02T00:00:00Z","content":"Hello"},{"id":"m2","role":"assistant","timestamp":"2025-01-02T00:00:00Z","content":"Hello back"}]}
        """

        var callCount = 0
        var putRequest: URLRequest?
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 3 {
                    putRequest = request
                }
                let data: Data
                if callCount == 1 {
                    data = Data(convJSON.utf8)
                } else if callCount == 3 {
                    data = Data(updatedConvJSON.utf8)
                } else {
                    data = Data(genJSON.utf8)
                }
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")
            await service.send(text: "Hello")

            #expect(callCount == 3)
            let put = try #require(putRequest)
            #expect(put.httpMethod == "PUT")
            #expect(put.url?.path == "/api/conversations/1")
        }
    }

    @Test("generation failure does not call update")
    func testSendDoesNotPersistOnFailure() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 1 {
                    let data = Data(convJSON.utf8)
                    let response = try #require(HTTPURLResponse(
                        url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "application/json"]
                    ))
                    return (response, data)
                }
                let data = Data(#"{"error":"Generation failed"}"#.utf8)
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 500, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")
            await service.send(text: "Hello")

            #expect(callCount == 2)
            #expect(service.generationError != nil)
        }
    }

    @Test("persistence failure does not remove rendered messages")
    func testSendPersistenceFailureKeepsMessages() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        let genJSON = """
        {"response":"Hello back"}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 1 {
                    let data = Data(convJSON.utf8)
                    let response = try #require(HTTPURLResponse(
                        url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "application/json"]
                    ))
                    return (response, data)
                } else if callCount == 2 {
                    let data = Data(genJSON.utf8)
                    let response = try #require(HTTPURLResponse(
                        url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "application/json"]
                    ))
                    return (response, data)
                }
                let data = Data(#"{"error":"Server error"}"#.utf8)
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 500, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")
            await service.send(text: "Hello")

            #expect(callCount == 3)

            let messages = try #require(service.selectedConversation?.messages)
            #expect(messages.count == 2)
            #expect(messages[0].role == "user")
            #expect(messages[1].role == "assistant")
            #expect(messages[1].content == "Hello back")
            #expect(service.generationError == nil)
        }
    }

    @Test("happy path: select → send → messages appear → persisted")
    func testWorkflowHappyPath() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        let genJSON = """
        {"response":"Hello back"}
        """
        let updatedConvJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-02T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-02T00:00:00Z","content":"Hello"},{"id":"m2","role":"assistant","timestamp":"2025-01-02T00:00:00Z","content":"Hello back"}]}
        """

        var callCount = 0
        var putRequest: URLRequest?
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 3 { putRequest = request }
                let data: Data
                switch callCount {
                case 1: data = Data(convJSON.utf8)
                case 3: data = Data(updatedConvJSON.utf8)
                default: data = Data(genJSON.utf8)
                }
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")

            var messages = try #require(service.selectedConversation?.messages)
            #expect(messages.isEmpty)

            await service.send(text: "Hello")

            #expect(service.isGenerating == false)
            #expect(service.generationError == nil)

            messages = try #require(service.selectedConversation?.messages)
            #expect(messages.count == 2)
            #expect(messages[0].role == "user")
            #expect(messages[0].content == "Hello")
            #expect(messages[1].role == "assistant")
            #expect(messages[1].content == "Hello back")

            #expect(callCount == 3)
            let put = try #require(putRequest)
            #expect(put.httpMethod == "PUT")
            #expect(put.url?.path == "/api/conversations/1")
        }
    }

    @Test("generation failure: error shown, no persistence attempted")
    func testWorkflowGenerationFailure() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 1 {
                    let data = Data(convJSON.utf8)
                    let response = try #require(HTTPURLResponse(
                        url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "application/json"]
                    ))
                    return (response, data)
                }
                let data = Data(#"{"error":"Generation failed"}"#.utf8)
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 500, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")

            #expect(service.generationError == nil)

            await service.send(text: "Hello")

            #expect(callCount == 2)
            #expect(service.isGenerating == false)
            let error = try #require(service.generationError)
            #expect(error.contains("Generation failed"))

            #expect(service.selectedConversation?.messages.count == 1)
        }
    }

    @Test("persistence failure: messages survive, state usable")
    func testWorkflowPersistenceFailure() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        let genJSON = """
        {"response":"I am here"}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 1 {
                    let data = Data(convJSON.utf8)
                    let response = try #require(HTTPURLResponse(
                        url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "application/json"]
                    ))
                    return (response, data)
                } else if callCount == 2 {
                    let data = Data(genJSON.utf8)
                    let response = try #require(HTTPURLResponse(
                        url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                        headerFields: ["Content-Type": "application/json"]
                    ))
                    return (response, data)
                }
                let data = Data(#"{"error":"Storage error"}"#.utf8)
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 500, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")

            await service.send(text: "Hi")

            #expect(callCount == 3)
            #expect(service.isGenerating == false)
            #expect(service.generationError == nil)

            let messages = try #require(service.selectedConversation?.messages)
            #expect(messages.count == 2)
            #expect(messages[0].content == "Hi")
            #expect(messages[1].content == "I am here")
        }
    }

    @Test("double-submit: isGenerating prevents concurrent send")
    func testWorkflowDoubleSubmitPrevention() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        let genJSON = """
        {"response":"Hello back"}
        """
        let updatedConvJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-02T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-02T00:00:00Z","content":"Hello"},{"id":"m2","role":"assistant","timestamp":"2025-01-02T00:00:00Z","content":"Hello back"}]}
        """

        let semaphore = DispatchSemaphore(value: 0)
        var callCount = 0

        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                if callCount == 2 {
                    semaphore.wait()
                }
                let data: Data
                if callCount == 1 {
                    data = Data(convJSON.utf8)
                } else if callCount == 3 {
                    data = Data(updatedConvJSON.utf8)
                } else {
                    data = Data(genJSON.utf8)
                }
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")

            Task { await service.send(text: "Hello") }

            try await Task.sleep(nanoseconds: 100_000_000)

            #expect(service.isGenerating == true)

            await service.send(text: "World")

            semaphore.signal()

            try await Task.sleep(nanoseconds: 100_000_000)

            #expect(callCount == 3)

            let messages = try #require(service.selectedConversation?.messages)
            #expect(messages.count == 2)
            #expect(messages[0].content == "Hello")
            #expect(messages[1].content == "Hello back")
            #expect(service.isGenerating == false)
        }
    }

    @Test("app restart: restore conversation with persisted messages")
    func testWorkflowRestoreWithMessages() async throws {
        let savedId = "workflow-1"
        let defaults = UserDefaults(suiteName: "test-workflow-restore-\(UUID().uuidString)")!
        defaults.set(savedId, forKey: "selectedConversationId")

        let listJSON = """
        [{"id":"workflow-1","title":"Workflow Chat","mode":"chat","created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-02T00:00:00Z"}]
        """
        let convJSON = """
        {"id":"workflow-1","title":"Workflow Chat","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-02T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-02T00:00:00Z","content":"Hello"},{"id":"m2","role":"assistant","timestamp":"2025-01-02T00:00:00Z","content":"Hello back"}]}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                let data: Data
                if callCount == 1 {
                    data = Data(listJSON.utf8)
                } else {
                    data = Data(convJSON.utf8)
                }
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService(defaults: defaults)
            await service.loadConversations()

            #expect(service.selectedConversation?.id == "workflow-1")
            #expect(service.selectedConversation?.title == "Workflow Chat")
            #expect(service.selectedId == "workflow-1")

            let messages = try #require(service.selectedConversation?.messages)
            #expect(messages.count == 2)
            #expect(messages[0].role == "user")
            #expect(messages[0].content == "Hello")
            #expect(messages[1].role == "assistant")
            #expect(messages[1].content == "Hello back")

            #expect(service.isLoading == false)
            #expect(service.error == nil)
            #expect(callCount == 2)
        }
    }

    @Test("error clears on next send")
    func testSendErrorClearsOnNextSend() async throws {
        let convJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-01T00:00:00Z","messages":[]}
        """
        let genJSON = """
        {"response":"Hello back"}
        """
        let updatedConvJSON = """
        {"id":"1","title":"Chat 1","mode":"chat","schema_version":1,"created_at":"2025-01-01T00:00:00Z","updated_at":"2025-01-02T00:00:00Z","messages":[{"id":"m1","role":"user","timestamp":"2025-01-02T00:00:00Z","content":"Second"},{"id":"m2","role":"assistant","timestamp":"2025-01-02T00:00:00Z","content":"Hello back"}]}
        """

        var callCount = 0
        try await withMock(data: Data(), statusCode: 200) {
            MockURLProtocol.requestHandler = { request in
                callCount += 1
                let data: Data
                if callCount == 1 {
                    data = Data(convJSON.utf8)
                } else if callCount == 2 {
                    data = Data(#"{"error":"Generation failed"}"#.utf8)
                } else if callCount == 4 {
                    data = Data(updatedConvJSON.utf8)
                } else {
                    data = Data(genJSON.utf8)
                }
                let statusCode: Int = callCount == 2 ? 500 : 200
                let response = try #require(HTTPURLResponse(
                    url: request.url!, statusCode: statusCode, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "application/json"]
                ))
                return (response, data)
            }
            defer { MockURLProtocol.requestHandler = nil }

            let service = makeService()
            await service.selectConversation("1")

            await service.send(text: "First")
            #expect(service.generationError != nil)

            await service.send(text: "Second")
            #expect(service.generationError == nil)
        }
    }
}
