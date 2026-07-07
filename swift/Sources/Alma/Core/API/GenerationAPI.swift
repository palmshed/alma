import Foundation

public struct GenerateRequest: Codable, Sendable {
    public let prompt: String?
    public let messages: [ChatMessage]?

    public init(prompt: String? = nil, messages: [ChatMessage]? = nil) {
        self.prompt = prompt
        self.messages = messages
    }
}

public final class GenerationAPI: Sendable {
    private let client: APIClient

    public init(client: APIClient) {
        self.client = client
    }

    public func generate(prompt: String) async throws -> String {
        let request = GenerateRequest(prompt: prompt)
        let response: GenerationResponse = try await client.post("/api/generate", body: request)
        return response.response
    }

    public func generate(messages: [ChatMessage]) async throws -> String {
        let request = GenerateRequest(messages: messages)
        let response: GenerationResponse = try await client.post("/api/generate", body: request)
        return response.response
    }

    public func generateWithThinking(prompt: String) async throws -> ThinkingResponse {
        let request = GenerateRequest(prompt: prompt)
        return try await client.post("/api/generate-with-thinking", body: request)
    }

    public func generateWithThinking(messages: [ChatMessage]) async throws -> ThinkingResponse {
        let request = GenerateRequest(messages: messages)
        return try await client.post("/api/generate-with-thinking", body: request)
    }

    public func generateWithURLContext(prompt: String) async throws -> String {
        let request = GenerateRequest(prompt: prompt)
        let response: GenerationResponse = try await client.post("/api/generate-with-url-context", body: request)
        return response.response
    }

    public func generateWithURLContext(messages: [ChatMessage]) async throws -> String {
        let request = GenerateRequest(messages: messages)
        let response: GenerationResponse = try await client.post("/api/generate-with-url-context", body: request)
        return response.response
    }
}
