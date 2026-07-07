import Foundation

public final class HealthAPI: Sendable {
    private let client: APIClient

    public init(client: APIClient) {
        self.client = client
    }

    public func health() async throws -> HealthResponse {
        try await client.get("/api/health")
    }
}
