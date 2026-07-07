import Foundation

public final class ConversationAPI: Sendable {
    private let client: APIClient

    public init(client: APIClient) {
        self.client = client
    }

    public func list() async throws -> [ConversationIndexEntry] {
        try await client.get("/api/conversations")
    }

    public func get(id: String) async throws -> Conversation {
        try await client.get("/api/conversations/\(id)")
    }

    public func create(_ conversation: Conversation) async throws -> Conversation {
        try await client.post("/api/conversations", body: conversation)
    }

    public func update(id: String, _ conversation: Conversation) async throws -> Conversation {
        try await client.put("/api/conversations/\(id)", body: conversation)
    }

    public func delete(id: String) async throws {
        try await client.delete("/api/conversations/\(id)")
    }
}
