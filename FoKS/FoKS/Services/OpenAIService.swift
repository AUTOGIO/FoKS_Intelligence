// OpenAIService — OpenAI API client for FoKS
// Replaces LMStudioService for cloud-based LLM inference
// Requires OPENAI_API_KEY (env or UserDefaults)

import Foundation
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "OpenAI")

public actor OpenAIService {
    private let baseURL: String
    private let apiKey: String
    private let chatModel: String
    private let reasoningModel: String
    private let routingModel: String
    private let visionModel: String
    private let timeout: TimeInterval
    private let session: URLSession

    public init(config: FoKSConfig) {
        self.baseURL = config.openAIBaseURL
        self.apiKey = config.openAIAPIKey
        self.chatModel = config.openAIChatModel
        self.reasoningModel = config.openAIReasoningModel
        self.routingModel = config.openAIRoutingModel
        self.visionModel = config.openAIVisionModel
        self.timeout = config.openAITimeout

        let sessionConfig = URLSessionConfiguration.default
        sessionConfig.timeoutIntervalForRequest = config.openAITimeout
        sessionConfig.timeoutIntervalForResource = config.openAITimeout + 10
        self.session = URLSession(configuration: sessionConfig)
    }

    // MARK: - Health Check
    public func isAvailable() async -> Bool {
        guard !apiKey.isEmpty else { return false }
        guard let url = URL(string: "\(baseURL)/models") else { return false }
        var req = URLRequest(url: url)
        req.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        req.timeoutInterval = 5
        do {
            let (_, resp) = try await session.data(for: req)
            return (resp as? HTTPURLResponse)?.statusCode == 200
        } catch {
            logger.error("OpenAI health check failed: \(error.localizedDescription)")
            return false
        }
    }

    // MARK: - Chat (general purpose)
    public func chat(
        prompt: String,
        systemPrompt: String? = nil,
        model: String? = nil,
        maxTokens: Int = 2048,
        temperature: Double = 0.7
    ) async -> String? {
        guard !apiKey.isEmpty else {
            logger.warning("OpenAI API key not configured")
            return nil
        }

        let selectedModel = model ?? chatModel
        guard let url = URL(string: "\(baseURL)/chat/completions") else { return nil }

        var messages: [[String: String]] = []
        if let sys = systemPrompt {
            messages.append(["role": "system", "content": sys])
        }
        messages.append(["role": "user", "content": prompt])

        let body: [String: Any] = [
            "model": selectedModel,
            "messages": messages,
            "max_tokens": maxTokens,
            "temperature": temperature,
        ]

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        req.timeoutInterval = timeout

        guard let httpBody = try? JSONSerialization.data(withJSONObject: body) else { return nil }
        req.httpBody = httpBody

        do {
            let (data, resp) = try await session.data(for: req)
            guard (resp as? HTTPURLResponse)?.statusCode == 200 else {
                logger.warning("OpenAI returned non-200")
                return nil
            }
            return extractContent(from: data)
        } catch {
            logger.error("OpenAI chat error: \(error.localizedDescription)")
            return nil
        }
    }

    // MARK: - AETHER: Profile Suggestion
    public func suggestProfile(currentApps: [String], hour: Int) async -> String? {
        let prompt = """
        Based on the context, suggest which workspace profile to use.
        Current hour: \(hour)
        Active applications: \(currentApps.joined(separator: ", "))
        Available profiles: work, personal, ai_research
        Respond with ONLY the profile name. No explanation.
        """
        return await chat(prompt: prompt, model: routingModel, maxTokens: 20, temperature: 0.3)
    }

    // MARK: - VESTA: Portfolio Advice
    public func portfolioAdvice(buckets: [String: Double]) async -> String? {
        let info = buckets.map { "\($0.key): \(String(format: "%.1f", $0.value))%" }
            .joined(separator: ", ")
        let prompt = """
        You are a portfolio advisor. Current bucket allocation: \(info)
        Target (Barbell Strategy): Survival 20-40%, Convex 20-40%, Illiquid Duration 20-40%
        Provide a one-line recommendation. Be concise.
        """
        return await chat(prompt: prompt, model: routingModel, maxTokens: 100, temperature: 0.3)
    }

    // MARK: - Parse Response
    private func extractContent(from data: Data) -> String? {
        guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let choices = json["choices"] as? [[String: Any]],
              let first = choices.first,
              let message = first["message"] as? [String: Any],
              let content = message["content"] as? String else { return nil }
        return content.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
