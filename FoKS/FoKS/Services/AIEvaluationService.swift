// AIEvaluationService — Note evaluation via FoKS OpenAIService or on-device NLP
// Bridges FileHQ note evaluation into FoKS's existing AI infrastructure
// KEY INTEGRATION: Uses FoKSHub.shared.openAI instead of standalone HTTP client

import Foundation
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "AIEval")

// MARK: - Protocol

public protocol AIEvaluationProvider: Sendable {
    func evaluate(note: NoteItem) async throws -> AIEvaluationResponse
}

// MARK: - Cloud: Adapter wrapping FoKS OpenAIService (SHARED — no duplicate API client)

public final class FoKSAIEvaluationAdapter: AIEvaluationProvider {
    private let openAI: OpenAIService

    public init(openAI: OpenAIService) {
        self.openAI = openAI
    }

    public func evaluate(note: NoteItem) async throws -> AIEvaluationResponse {
        let systemPrompt = """
        You are a note evaluator. Determine if a note contains meaningful information \
        worthy of keeping and suggest a folder category. Respond with JSON only:
        {"is_meaningful": true/false, "reason": "Brief reason", "suggested_category": "Category or null"}
        """

        let userPrompt = """
        Title: \(note.title)
        Content: \(String(note.plainBody.prefix(2000)))

        A note is meaningful if it has specific information, tasks, or ideas valuable for reference.
        """

        // Uses the SAME OpenAI actor as AETHER suggestions and VESTA portfolio advice
        guard let response = await openAI.chat(
            prompt: userPrompt,
            systemPrompt: systemPrompt,
            model: nil,  // uses default chatModel from FoKSConfig
            maxTokens: 150,
            temperature: 0.3
        ) else {
            throw AIEvalError.noResponse
        }

        guard let data = response.data(using: .utf8) else {
            throw AIEvalError.parseError
        }
        return try JSONDecoder().decode(AIEvaluationResponse.self, from: data)
    }
}

// MARK: - On-Device: NaturalLanguage heuristics (no API key, no network)

public final class OnDeviceAIEvaluationService: AIEvaluationProvider {
    public init() {}

    public func evaluate(note: NoteItem) async throws -> AIEvaluationResponse {
        let text = "\(note.title) \(note.plainBody)".trimmingCharacters(in: .whitespacesAndNewlines)

        // Empty or trivially short
        if text.count < 5 {
            return AIEvaluationResponse(isMeaningful: false, reason: "Empty or too short.", suggestedCategory: nil)
        }

        let isMeaningful = text.count >= 20 || hasStructuredContent(text)
        let category = isMeaningful ? suggestCategory(text) : nil

        return AIEvaluationResponse(
            isMeaningful: isMeaningful,
            reason: isMeaningful ? "Contains identifiable content." : "Fragment or placeholder.",
            suggestedCategory: category
        )
    }

    private func hasStructuredContent(_ text: String) -> Bool {
        let patterns = ["https?://", "[\\w.]+@[\\w.]+", "\\d{2,4}[-/]\\d{2}", "^\\s*[-*•]\\s+", "\\b(TODO|FIXME|NOTE|IMPORTANT)\\b"]
        return patterns.contains {
            (try? NSRegularExpression(pattern: $0, options: .caseInsensitive))?.firstMatch(
                in: text, range: NSRange(text.startIndex..., in: text)
            ) != nil
        }
    }

    private func suggestCategory(_ text: String) -> String {
        let lower = text.lowercased()
        let map: [(String, [String])] = [
            ("Work", ["meeting", "project", "deadline", "client", "report", "office"]),
            ("Personal", ["birthday", "family", "vacation", "health", "doctor"]),
            ("Finance", ["invoice", "payment", "bank", "budget", "expense", "salary", "nfa", "nota fiscal"]),
            ("Ideas", ["idea", "concept", "brainstorm", "creative", "design"]),
            ("Tasks", ["todo", "task", "checklist", "reminder", "action"]),
            ("Tech", ["code", "api", "server", "database", "bug", "deploy", "swift", "python"]),
            ("Learning", ["course", "book", "study", "tutorial", "lesson", "research"])
        ]
        for (cat, keywords) in map {
            if keywords.contains(where: { lower.contains($0) }) { return cat }
        }
        return "General"
    }
}

public enum AIEvalError: LocalizedError {
    case noResponse, parseError
    public var errorDescription: String? {
        switch self {
        case .noResponse: "AI returned no response."
        case .parseError: "Could not parse AI evaluation."
        }
    }
}
