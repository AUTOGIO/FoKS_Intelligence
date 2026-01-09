// VESTA - LM Studio AI Client
// Connects directly to LM Studio for AI-powered suggestions

import Foundation

class FoKSClient {
    static let shared = FoKSClient()

    // LM Studio API endpoint (same as AETHER uses)
    private var baseURL = "http://100.72.60.38:1234/v1"

    private init() {}

    // MARK: - Profile Suggestion
    func getProfileSuggestion(buckets: [String: Double]) async -> String? {
        // Format bucket info for AI
        let bucketInfo = buckets.map { "\($0.key): \(String(format: "%.1f", $0.value))%" }
            .joined(separator: ", ")

        let prompt = """
        You are a portfolio advisor for a Family Office. Based on the current bucket allocation:
        \(bucketInfo)

        Target allocation (Barbell Strategy):
        - Survival (cash, bonds): 20-40%
        - Convex (ETFs, crypto): 20-40%
        - Illiquid Duration (real estate): 20-40%

        Provide a one-line recommendation. Be concise.
        """

        return await chat(prompt: prompt)
    }

    // MARK: - Chat with LM Studio
    func chat(prompt: String) async -> String? {
        guard let url = URL(string: "\(baseURL)/chat/completions") else { return nil }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30

        let body: [String: Any] = [
            "model": "SmolLM2-1.7B-Instruct",
            "messages": [
                ["role": "user", "content": prompt]
            ],
            "max_tokens": 150,
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

            // Parse OpenAI-compatible response
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
            let success = (response as? HTTPURLResponse)?.statusCode == 200
            print(success ? "✅ LM Studio connected" : "❌ LM Studio not available")
            return success
        } catch {
            print("❌ LM Studio connection failed: \(error.localizedDescription)")
            return false
        }
    }

    // MARK: - Update URL
    func updateBaseURL(_ newURL: String) {
        baseURL = newURL
    }

    func getBaseURL() -> String {
        baseURL
    }
}
