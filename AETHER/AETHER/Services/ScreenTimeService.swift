// AETHER - Screen Time Service
// Tracks application usage with SQLite storage

import Foundation
import SQLite3

class ScreenTimeService {
    static let shared = ScreenTimeService()

    private var db: OpaquePointer?
    private var trackingTimer: Timer?
    private var currentApp: (bundleId: String, appName: String, startTime: Date)?
    private let trackingInterval: TimeInterval = 30 // seconds

    private var dbPath: String {
        let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let aetherDir = appSupport.appendingPathComponent("AETHER")

        if !FileManager.default.fileExists(atPath: aetherDir.path) {
            try? FileManager.default.createDirectory(at: aetherDir, withIntermediateDirectories: true)
        }

        return aetherDir.appendingPathComponent("screentime.db").path
    }

    private init() {
        openDatabase()
        createTable()
    }

    deinit {
        sqlite3_close(db)
    }

    // MARK: - Database Setup
    private func openDatabase() {
        if sqlite3_open(dbPath, &db) != SQLITE_OK {
            print("⚠️ Failed to open database")
        } else {
            print("🌌 Screen time database ready: \(dbPath)")
        }
    }

    private func createTable() {
        let sql = """
        CREATE TABLE IF NOT EXISTS usage_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_id TEXT NOT NULL,
            app_name TEXT NOT NULL,
            started_at REAL NOT NULL,
            ended_at REAL,
            duration_seconds INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_started_at ON usage_sessions(started_at);
        CREATE INDEX IF NOT EXISTS idx_bundle_id ON usage_sessions(bundle_id);
        """

        var errMsg: UnsafeMutablePointer<CChar>?
        if sqlite3_exec(db, sql, nil, nil, &errMsg) != SQLITE_OK {
            if let error = errMsg {
                print("⚠️ Table creation failed: \(String(cString: error))")
                sqlite3_free(error)
            }
        }
    }

    // MARK: - Tracking Control
    func startTracking() {
        trackingTimer = Timer.scheduledTimer(withTimeInterval: trackingInterval, repeats: true) { [weak self] _ in
            self?.recordActiveApp()
        }
        recordActiveApp() // Record immediately
        print("🌌 Screen time tracking started (interval: \(Int(trackingInterval))s)")
    }

    func stopTracking() {
        trackingTimer?.invalidate()
        trackingTimer = nil

        // End current session
        if let current = currentApp {
            endSession(bundleId: current.bundleId, startTime: current.startTime)
        }

        print("🌌 Screen time tracking stopped")
    }

    // MARK: - Recording
    private func recordActiveApp() {
        guard let active = WindowManager.shared.getActiveApp() else { return }

        // Same app as before - continue session
        if let current = currentApp, current.bundleId == active.bundleId {
            return
        }

        // End previous session
        if let current = currentApp {
            endSession(bundleId: current.bundleId, startTime: current.startTime)
        }

        // Start new session
        currentApp = (bundleId: active.bundleId, appName: active.appName, startTime: Date())
        startSession(bundleId: active.bundleId, appName: active.appName)
    }

    private func startSession(bundleId: String, appName: String) {
        let sql = "INSERT INTO usage_sessions (bundle_id, app_name, started_at) VALUES (?, ?, ?)"

        var statement: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_text(statement, 1, bundleId, -1, nil)
            sqlite3_bind_text(statement, 2, appName, -1, nil)
            sqlite3_bind_double(statement, 3, Date().timeIntervalSince1970)
            sqlite3_step(statement)
        }
        sqlite3_finalize(statement)
    }

    private func endSession(bundleId: String, startTime: Date) {
        let now = Date()
        let duration = Int(now.timeIntervalSince(startTime))

        let sql = """
        UPDATE usage_sessions
        SET ended_at = ?, duration_seconds = ?
        WHERE bundle_id = ? AND started_at = ? AND ended_at IS NULL
        """

        var statement: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_double(statement, 1, now.timeIntervalSince1970)
            sqlite3_bind_int(statement, 2, Int32(duration))
            sqlite3_bind_text(statement, 3, bundleId, -1, nil)
            sqlite3_bind_double(statement, 4, startTime.timeIntervalSince1970)
            sqlite3_step(statement)
        }
        sqlite3_finalize(statement)
    }

    // MARK: - Statistics
    func getTodayStats() -> DailyStats {
        let calendar = Calendar.current
        let startOfDay = calendar.startOfDay(for: Date())

        return getStats(from: startOfDay, to: Date())
    }

    func getStats(from: Date, to: Date) -> DailyStats {
        var totalSeconds = 0
        var breakdown: [String: Int] = [:]

        let sql = """
        SELECT bundle_id, app_name, SUM(duration_seconds) as total
        FROM usage_sessions
        WHERE started_at >= ? AND started_at <= ?
        GROUP BY bundle_id
        ORDER BY total DESC
        """

        var statement: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_double(statement, 1, from.timeIntervalSince1970)
            sqlite3_bind_double(statement, 2, to.timeIntervalSince1970)

            while sqlite3_step(statement) == SQLITE_ROW {
                if let bundleIdPtr = sqlite3_column_text(statement, 0) {
                    let bundleId = String(cString: bundleIdPtr)
                    let seconds = Int(sqlite3_column_int(statement, 2))
                    breakdown[bundleId] = seconds
                    totalSeconds += seconds
                }
            }
        }
        sqlite3_finalize(statement)

        return DailyStats(date: from, totalSeconds: totalSeconds, appBreakdown: breakdown)
    }

    func getTopApps(limit: Int = 5) -> [AppUsage] {
        let stats = getTodayStats()

        var apps: [AppUsage] = []
        let sql = """
        SELECT bundle_id, app_name, SUM(duration_seconds) as total
        FROM usage_sessions
        WHERE started_at >= ?
        GROUP BY bundle_id
        ORDER BY total DESC
        LIMIT ?
        """

        let startOfDay = Calendar.current.startOfDay(for: Date())

        var statement: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_double(statement, 1, startOfDay.timeIntervalSince1970)
            sqlite3_bind_int(statement, 2, Int32(limit))

            while sqlite3_step(statement) == SQLITE_ROW {
                if let bundleIdPtr = sqlite3_column_text(statement, 0),
                   let appNamePtr = sqlite3_column_text(statement, 1) {
                    let bundleId = String(cString: bundleIdPtr)
                    let appName = String(cString: appNamePtr)
                    let seconds = Int(sqlite3_column_int(statement, 2))
                    apps.append(AppUsage(bundleId: bundleId, appName: appName, seconds: seconds))
                }
            }
        }
        sqlite3_finalize(statement)

        return apps
    }
}
