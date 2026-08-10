// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import Foundation

public enum APIError: Error, LocalizedError, Equatable {
    case invalidURL
    case invalidResponse
    case httpError(statusCode: Int, message: String)
    case decodingFailed(Error)
    case encodingFailed(Error)
    case networkError(Error)

    public var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response"
        case .httpError(let code, let message):
            return "[\(code)] \(message)"
        case .decodingFailed(let error):
            return "Decoding failed: \(error.localizedDescription)"
        case .encodingFailed(let error):
            return "Encoding failed: \(error.localizedDescription)"
        case .networkError(let error):
            return error.localizedDescription
        }
    }

    public static func == (lhs: APIError, rhs: APIError) -> Bool {
        switch (lhs, rhs) {
        case (.invalidURL, .invalidURL): return true
        case (.invalidResponse, .invalidResponse): return true
        case (.httpError(let lc, let lm), .httpError(let rc, let rm)):
            return lc == rc && lm == rm
        case (.decodingFailed(let lE), .decodingFailed(let rE)):
            return lE.localizedDescription == rE.localizedDescription
        case (.encodingFailed(let lE), .encodingFailed(let rE)):
            return lE.localizedDescription == rE.localizedDescription
        case (.networkError(let lE), .networkError(let rE)):
            return lE.localizedDescription == rE.localizedDescription
        default:
            return false
        }
    }
}

public final class APIClient: Sendable {
    public let baseURL: URL
    public let session: URLSession
    public let decoder: JSONDecoder
    public let encoder: JSONEncoder

    public init(
        baseURL: URL,
        session: URLSession = .shared,
        decoder: JSONDecoder? = nil,
        encoder: JSONEncoder? = nil
    ) {
        self.baseURL = baseURL
        self.session = session
        self.decoder = decoder ?? {
            let d = JSONDecoder()
            d.keyDecodingStrategy = .convertFromSnakeCase
            return d
        }()
        self.encoder = encoder ?? {
            let e = JSONEncoder()
            e.keyEncodingStrategy = .convertToSnakeCase
            e.outputFormatting = [.sortedKeys]
            return e
        }()
    }

    public func buildRequest(
        path: String,
        method: String = "GET",
        queryItems: [URLQueryItem]? = nil,
        body: Data? = nil,
        contentType: String? = "application/json"
    ) throws -> URLRequest {
        guard var components = URLComponents(url: baseURL.appendingPathComponent(path), resolvingAgainstBaseURL: true)
        else {
            throw APIError.invalidURL
        }
        components.queryItems = queryItems
        guard let url = components.url else {
            throw APIError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        if let contentType {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.httpBody = body
        return request
    }

    public func perform<T: Decodable>(_ request: URLRequest) async throws -> T {
        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        try validate(httpResponse, data: data)

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decodingFailed(error)
        }
    }

    public func performRaw(_ request: URLRequest) async throws -> Data {
        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        try validate(httpResponse, data: data)
        return data
    }

    public func performWithoutBody(_ request: URLRequest) async throws {
        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.networkError(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        try validate(httpResponse, data: data)
    }

    // MARK: - Validation

    private func validate(_ response: HTTPURLResponse, data: Data) throws {
        let statusCode = response.statusCode
        guard !(200...299).contains(statusCode) else { return }

        let message = (
            try? decoder.decode([String: String].self, from: data)
        )?["error"] ?? "HTTP \(statusCode)"

        throw APIError.httpError(statusCode: statusCode, message: message)
    }

    // MARK: - Convenience

    public func get<T: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem]? = nil
    ) async throws -> T {
        let request = try buildRequest(path: path, queryItems: queryItems)
        return try await perform(request)
    }

    public func post<Body: Encodable, T: Decodable>(
        _ path: String,
        body: Body
    ) async throws -> T {
        let data = try encoder.encode(body)
        let request = try buildRequest(path: path, method: "POST", body: data)
        return try await perform(request)
    }

    public func put<Body: Encodable, T: Decodable>(
        _ path: String,
        body: Body
    ) async throws -> T {
        let data = try encoder.encode(body)
        let request = try buildRequest(path: path, method: "PUT", body: data)
        return try await perform(request)
    }

    public func delete(
        _ path: String
    ) async throws {
        let request = try buildRequest(path: path, method: "DELETE")
        try await performWithoutBody(request)
    }

    public func delete<T: Decodable>(
        _ path: String
    ) async throws -> T {
        let request = try buildRequest(path: path, method: "DELETE")
        return try await perform(request)
    }
}
