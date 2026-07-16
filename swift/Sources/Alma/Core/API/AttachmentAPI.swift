// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import Foundation

final class MultipartFormData {
    private let boundary: String
    private var body: Data

    init(boundary: String = "Boundary-\(UUID().uuidString)") {
        self.boundary = boundary
        self.body = Data()
    }

    func appendField(name: String, data: Data, filename: String? = nil, mimeType: String? = nil) {
        body.append("--\(boundary)\r\n")

        if let filename {
            body.append("Content-Disposition: form-data; name=\"\(name)\"; filename=\"\(filename)\"\r\n")
        } else {
            body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n")
        }

        if let mimeType {
            body.append("Content-Type: \(mimeType)\r\n")
        }

        body.append("\r\n")
        body.append(data)
        body.append("\r\n")
    }

    func build() -> (Data, contentType: String) {
        var finalBody = body
        finalBody.append("--\(boundary)--\r\n")
        return (finalBody, "multipart/form-data; boundary=\(boundary)")
    }
}

extension Data {
    mutating func append(_ string: String) {
        if let data = string.data(using: .utf8) {
            append(data)
        }
    }
}

public final class AttachmentAPI: Sendable {
    private let client: APIClient

    public init(client: APIClient) {
        self.client = client
    }

    public func upload(data: Data, filename: String, mimeType: String) async throws -> Attachment {
        let form = MultipartFormData()
        form.appendField(name: "file", data: data, filename: filename, mimeType: mimeType)
        let (body, contentType) = form.build()

        let request = try client.buildRequest(
            path: "/api/attachments",
            method: "POST",
            body: body,
            contentType: contentType
        )
        return try await client.perform(request)
    }

    public func download(id: String) async throws -> Data {
        let request = try client.buildRequest(path: "/api/attachments/\(id)")
        return try await client.performRaw(request)
    }

    public func getMetadata(id: String) async throws -> Attachment {
        try await client.get("/api/attachments/\(id)/metadata")
    }

    public func delete(id: String) async throws {
        try await client.delete("/api/attachments/\(id)")
    }
}
