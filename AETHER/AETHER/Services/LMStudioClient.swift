// AETHER - LM Studio Client
// Connects to local LM Studio for AI-powered suggestions

import Foundation

class LMStudioClient {
    static let shared = LMStudioClient()

    // Your LM Studio endpoint (Tailscale address)
    private let baseURL = "http://100.72.60.38:1234/v1"

    // Models for different purposes
    private let routingModel = "SmolLM2-1.7B-Instruct"  // Fast routing decisions
    private let reasoningModel = "DeepSeek-R1-Distill-Qwen-7B-4bit"  // Complex reasoning

    private init() {}

    // MARK: - Profile Suggestion
    func suggestProfile(currentApps: [String], hour: Int) async -> String? {
        let prompt = """
        You are a workspace assistant. Based on the current context, suggest which workspace profile to use.

        Current hour: \(hour)
        Active applications: \(currentApps.joined(separator: ", "))

        Available profiles:
        - work: For coding, development, and productivity (VS Code, Terminal, Safari, Xcode)
        - personal: For entertainment, social, and relaxation (Netflix, Spotify, WhatsApp, Safari)
        - ai_research: For AI development and research (LM Studio, Terminal, Obsidian, ChatGPT)

        Respond with ONLY the profile name (work, personal, or ai_research). No explanation.
        """

        return await chat(prompt: prompt, model: routingModel)
    }

    // MARK: - Smart Suggestions
    func getSmartSuggestion(profile: String, timeOfDay: String, recentApps: [String]) async -> String? {
        let prompt = """
        Current profile: \(profile)
        Time: \(timeOfDay)
        Recent apps: \(recentApps.joined(separator: ", "))

        Give a brief, helpful one-line suggestion for productivity. Be friendly and concise.
        Example: "Consider taking a break - you've been coding for a while!"
        """

        return await chat(prompt: prompt, model: routingModel)
    }

    // MARK: - Core Chat Function
    func chat(prompt: String, model: String? = nil) async -> String? {
        let selectedModel = model ?? routingModel

        guard let url = URL(string: "\(baseURL)/chat/completions") else { return nil }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30

        let body: [String: Any] = [
            "model": selectedModel,
            "messages": [
                ["role": "user", "content": prompt]
            ],
            "max_tokens": 100,
            "temperature": 0.3
        ]

        guard let httpBody = try? JSONSerialization.data(withJSONObject: body) else { return nil }
        request.httpBody = httpBody

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                print("⚠️ LM Studio request failed")
                return nil
            }

            if let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
               let choices = json["choices"] as? [[String: Any]],
               let firstChoice = choices.first,
               let message = firstChoice["message"] as? [String: Any],
               let content = message["content"] as? String {
                return content.trimmingCharacters(in: .whitespacesAndNewlines)
            }
        } catch {
            print("⚠️ LM Studio error: \(error.localizedDescription)")
        }

        return nil
    }

    // MARK: - Health Check
    func isAvailable() async -> Bool {
        guard let url = URL(string: "\(baseURL)/models") else { return false }

        var request = URLRequest(url: url)
        request.timeoutInterval = 5

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            return (response as? HTTPURLResponse)?.statusCode == 200
        } catch {
            return false
        }
    }
}
