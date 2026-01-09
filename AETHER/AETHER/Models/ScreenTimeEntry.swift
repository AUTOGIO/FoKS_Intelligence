// AETHER - Screen Time Entry Model
// Tracks application usage

import Foundation

struct ScreenTimeEntry: Codable, Identifiable {
    let id: UUID
    let bundleId: String
    let appName: String
    let startedAt: Date
    var endedAt: Date?
    var durationSeconds: Int

    init(
        id: UUID = UUID(),
        bundleId: String,
        appName: String,
        startedAt: Date = Date(),
        endedAt: Date? = nil,
        durationSeconds: Int = 0
    ) {
        self.id = id
        self.bundleId = bundleId
        self.appName = appName
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.durationSeconds = durationSeconds
    }
}

struct DailyStats: Identifiable {
    let id = UUID()
    let date: Date
    var totalSeconds: Int
    var appBreakdown: [String: Int]  // bundleId -> seconds

    var formattedTotal: String {
        let hours = totalSeconds / 3600
        let minutes = (totalSeconds % 3600) / 60
        if hours > 0 {
            return "\(hours)h \(minutes)m"
        }
        return "\(minutes)m"
    }
}

struct AppUsage: Identifiable {
    let id = UUID()
    let bundleId: String
    let appName: String
    let seconds: Int

    var formattedDuration: String {
        let hours = seconds / 3600
        let minutes = (seconds % 3600) / 60
        if hours > 0 {
            return "\(hours)h \(minutes)m"
        }
        return "\(minutes)m"
    }
}
