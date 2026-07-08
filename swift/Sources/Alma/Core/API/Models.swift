import Foundation

public struct ConversationIndexEntry: Codable, Identifiable, Equatable, Sendable {
    public let id: String
    public var title: String
    public let mode: String
    public let createdAt: String
    public let updatedAt: String
}

public struct Conversation: Codable, Identifiable, Equatable, Sendable {
    public let id: String
    public var title: String
    public let mode: String
    public let schemaVersion: Int
    public let createdAt: String?
    public let updatedAt: String?
    public var messages: [ChatMessage]
    public let titleIsManual: Bool?

    public init(
        id: String,
        title: String,
        mode: String,
        schemaVersion: Int = 1,
        createdAt: String? = nil,
        updatedAt: String? = nil,
        messages: [ChatMessage],
        titleIsManual: Bool? = nil
    ) {
        self.id = id
        self.title = title
        self.mode = mode
        self.schemaVersion = schemaVersion
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.messages = messages
        self.titleIsManual = titleIsManual
    }
}

public struct ChatMessage: Codable, Identifiable, Equatable, Sendable {
    public let id: String
    public let role: String
    public let timestamp: String
    public let content: String
    public let thinking: String?
    public let image: String?

    public init(
        id: String,
        role: String,
        timestamp: String,
        content: String,
        thinking: String? = nil,
        image: String? = nil
    ) {
        self.id = id
        self.role = role
        self.timestamp = timestamp
        self.content = content
        self.thinking = thinking
        self.image = image
    }
}

public struct Attachment: Codable, Identifiable, Equatable, Sendable {
    public let id: String
    public let filename: String
    public let mimeType: String
    public let size: Int
    public let checksum: String
    public let storageKey: String
    public let createdAt: String
}

public struct GenerationResponse: Codable, Equatable, Sendable {
    public let response: String
}

public struct ThinkingResponse: Codable, Equatable, Sendable {
    public let response: String
    public let thinkingSummary: [String]
}

public struct HealthResponse: Codable, Equatable, Sendable {
    public let status: String
}
