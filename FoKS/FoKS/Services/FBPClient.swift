// FBPClient — FBP Backend REST client for FoKS
// Mirrors FBPApiClient from fbp-cli but tailored for in-app use
// Connects via TCP (http://localhost:8000) or Unix socket (/tmp/fbp.sock)

import Foundation
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "FBPClient")

public final class FBPClient: @unchecked Sendable {
    private let baseURL: String
    private let session: URLSession

    public init(config: FoKSConfig) {
        // For now, always use TCP — socket support can be added via NWConnection later
        self.baseURL = config.fbpBaseURL.hasSuffix("/")
            ? String(config.fbpBaseURL.dropLast())
            : config.fbpBaseURL

        let sessionConfig = URLSessionConfiguration.default
        sessionConfig.timeoutIntervalForRequest = config.defaultTimeout
        self.session = URLSession(configuration: sessionConfig)
    }

    // MARK: - Health Check

    public func isHealthy() async -> Bool {
        guard let url = URL(string: "\(baseURL)/health") else { return false }
        var req = URLRequest(url: url)
        req.timeoutInterval = 5
        do {
            let (data, resp) = try await session.data(for: req)
            guard (resp as? HTTPURLResponse)?.statusCode == 200 else { return false }
            let health = try? JSONDecoder().decode(HealthResponse.self, from: data)
            return health?.status == "ok"
        } catch {
            logger.debug("FBP health check failed: \(error.localizedDescription)")
            return false
        }
    }

    // MARK: - Generic HTTP

    public func get<T: Decodable>(path: String) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(path)") else {
            throw FBPError.invalidURL(path)
        }
        let (data, resp) = try await session.data(from: url)
        guard let http = resp as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw FBPError.requestFailed(path, (resp as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    public func post<T: Decodable, B: Encodable>(path: String, body: B) async throws -> T {
        guard let url = URL(string: "\(baseURL)\(path)") else {
            throw FBPError.invalidURL(path)
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(body)
        let (data, resp) = try await session.data(for: req)
        guard let http = resp as? HTTPURLResponse, (200...299).contains(http.statusCode) else {
            throw FBPError.requestFailed(path, (resp as? HTTPURLResponse)?.statusCode ?? -1)
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    // MARK: - NFA Consult (used by FileHQ NFA bridge)

    public func nfaConsult(from: String, to: String, matricula: String = "1595504") async throws -> NFAConsultResponse {
        try await post(path: "/nfa/consult", body: NFAConsultRequest(
            data_inicial: from, data_final: to, matricula: matricula,
            username: nil, password: nil
        ))
    }

    public func nfaJobStatus(jobId: String) async throws -> NFAJobStatusResponse {
        try await get(path: "/nfa/consult/status/\(jobId)")
    }

    // MARK: - Script Execution (sandboxed bash via FBP)

    public func runScript(content: String, timeout: Int = 30) async throws -> ScriptExecutionResponse {
        try await post(path: "/api/executor/run-bash", body: ScriptExecutionRequest(
            script_content: content, timeout: timeout
        ))
    }
}

// MARK: - FBP-compatible Models (inline, matching fbp-cli Models.swift exactly)

public struct HealthResponse: Codable {
    public let status: String
    public let machine: String?
    public let project: String?
}

public struct NFAConsultRequest: Encodable {
    public let data_inicial: String
    public let data_final: String
    public let matricula: String?
    public let username: String?
    public let password: String?
}

public struct NFAConsultResponse: Codable {
    public let job_id: String
    public let status: String
}

public struct NFAJobStatusResponse: Codable {
    public let job_id: String
    public let job_type: String
    public let status: String
    public let created_at: String
    public let started_at: String?
    public let completed_at: String?
    public let nfa_numero: String?
    public let danfe_path: String?
    public let dar_path: String?
    public let result: [String: String]?
    public let error: String?
}

public struct ScriptExecutionRequest: Encodable {
    public let script_content: String
    public let timeout: Int
}

public struct ScriptExecutionResponse: Codable {
    public let success: Bool
    public let exit_code: Int
    public let stdout: String
    public let stderr: String
    public let duration_ms: Int
}

public enum FBPError: LocalizedError {
    case invalidURL(String)
    case requestFailed(String, Int)
    public var errorDescription: String? {
        switch self {
        case .invalidURL(let p): "Invalid URL for path: \(p)"
        case .requestFailed(let p, let code): "FBP \(p) returned \(code)"
        }
    }
}
