// NoteItem — FileHQ Apple Notes domain model + AI evaluation result

import Foundation

public struct NoteItem: Identifiable, Codable {
    public let id: String
    public let title: String
    public let body: String
    public let folder: String

    public init(id: String, title: String, body: String, folder: String) {
        self.id = id; self.title = title; self.body = body; self.folder = folder
    }

    public var plainBody: String {
        body.replacingOccurrences(of: "<br>", with: "\n")
            .replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

public struct NoteEvaluation: Identifiable, Codable {
    public let id: String
    public let noteTitle: String
    public let isMeaningful: Bool
    public let reason: String
    public let suggestedCategory: String?
    public let action: Action

    public init(id: String, noteTitle: String, isMeaningful: Bool, reason: String, suggestedCategory: String?, action: Action) {
        self.id = id
        self.noteTitle = noteTitle
        self.isMeaningful = isMeaningful
        self.reason = reason
        self.suggestedCategory = suggestedCategory
        self.action = action
    }

    public enum Action: String, Codable {
        case kept, moved, deleted, failed
    }
}

/// Structured response from AI note evaluation (both cloud and on-device).
public struct AIEvaluationResponse: Codable {
    public let isMeaningful: Bool
    public let reason: String
    public let suggestedCategory: String?

    public init(isMeaningful: Bool, reason: String, suggestedCategory: String?) {
        self.isMeaningful = isMeaningful
        self.reason = reason
        self.suggestedCategory = suggestedCategory
    }

    enum CodingKeys: String, CodingKey {
        case isMeaningful = "is_meaningful"
        case reason
        case suggestedCategory = "suggested_category"
    }
}
