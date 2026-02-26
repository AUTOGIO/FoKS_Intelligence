// SystemStats — Shared system telemetry model

import Foundation

public struct SystemStats {
    public let cpuUsage: Double       // 0-100
    public let memoryUsedGB: Double
    public let memoryTotalGB: Double
    public let uptime: TimeInterval
    public let activeProcessCount: Int

    public var memoryPressure: String {
        let pct = (memoryUsedGB / memoryTotalGB) * 100
        if pct > 85 { return "High" }
        if pct > 60 { return "Medium" }
        return "Low"
    }

    public var uptimeFormatted: String {
        let h = Int(uptime) / 3600
        let m = (Int(uptime) % 3600) / 60
        return "\(h)h \(m)m"
    }
}

// MARK: - Screen Time Entry
public struct ScreenTimeEntry: Identifiable {
    public let id = UUID()
    public let bundleId: String
    public let appName: String
    public let seconds: Int

    public var formatted: String {
        let h = seconds / 3600, m = (seconds % 3600) / 60
        return h > 0 ? "\(h)h \(m)m" : "\(m)m"
    }
}

// MARK: - Chat models (for HTTP server compatibility)
struct ChatRequest: Codable {
    let message: String
    let history: [ChatMessage]?
    let model: String?
    let source: String?
}

struct ChatMessage: Codable {
    let role: String   // "user", "assistant", "system"
    let content: String
}

struct ChatResponse: Codable {
    let reply: String
    let raw: [String: AnyCodable]?
}

// Generic Codable wrapper
struct AnyCodable: Codable {
    let value: Any
    init(_ value: Any) { self.value = value }
    init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if let s = try? c.decode(String.self) { value = s }
        else if let i = try? c.decode(Int.self) { value = i }
        else if let d = try? c.decode(Double.self) { value = d }
        else if let b = try? c.decode(Bool.self) { value = b }
        else { value = "null" }
    }
    func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch value {
        case let s as String: try c.encode(s)
        case let i as Int: try c.encode(i)
        case let d as Double: try c.encode(d)
        case let b as Bool: try c.encode(b)
        default: try c.encode("\(value)")
        }
    }
}
