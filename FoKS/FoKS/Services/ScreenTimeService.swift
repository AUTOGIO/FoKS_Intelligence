// ScreenTimeService — SQLite-backed app usage tracker
// Polls frontmost app every 30s, stores sessions in ~/Library/Application Support/FoKS/screentime.db

import Foundation
import SQLite3
import AppKit
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "ScreenTime")

public final class ScreenTimeService {
    private var db: OpaquePointer?
    private var timer: Timer?
    private var currentApp: (bundleId: String, appName: String, startTime: Date)?
    private let interval: TimeInterval = 30

    private var dbPath: String {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
            .first!.appendingPathComponent("FoKS")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("screentime.db").path
    }

    public init() {
        guard sqlite3_open(dbPath, &db) == SQLITE_OK else {
            logger.error("Failed to open screentime DB"); return
        }
        let sql = """
        CREATE TABLE IF NOT EXISTS usage_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bundle_id TEXT NOT NULL, app_name TEXT NOT NULL,
            started_at REAL NOT NULL, ended_at REAL,
            duration_seconds INTEGER DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_started ON usage_sessions(started_at);
        """
        sqlite3_exec(db, sql, nil, nil, nil)
        logger.info("ScreenTime DB ready")
    }

    deinit { sqlite3_close(db) }

    public func startTracking() {
        timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            self?.record()
        }
        record()
        logger.info("ScreenTime tracking started (\(Int(self.interval))s interval)")
    }

    public func stopTracking() {
        timer?.invalidate(); timer = nil
        if let c = currentApp { endSession(bundleId: c.bundleId, startTime: c.startTime) }
    }

    private func record() {
        guard let active = WindowManager().getActiveApp() else { return }
        if let c = currentApp, c.bundleId == active.bundleId { return }
        if let c = currentApp { endSession(bundleId: c.bundleId, startTime: c.startTime) }
        currentApp = (active.bundleId, active.appName, Date())
        let sql = "INSERT INTO usage_sessions (bundle_id, app_name, started_at) VALUES (?, ?, ?)"
        var stmt: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_text(stmt, 1, active.bundleId, -1, nil)
            sqlite3_bind_text(stmt, 2, active.appName, -1, nil)
            sqlite3_bind_double(stmt, 3, Date().timeIntervalSince1970)
            sqlite3_step(stmt)
        }
        sqlite3_finalize(stmt)
    }

    private func endSession(bundleId: String, startTime: Date) {
        let now = Date(); let dur = Int(now.timeIntervalSince(startTime))
        let sql = "UPDATE usage_sessions SET ended_at=?, duration_seconds=? WHERE bundle_id=? AND started_at=? AND ended_at IS NULL"
        var stmt: OpaquePointer?
        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_double(stmt, 1, now.timeIntervalSince1970)
            sqlite3_bind_int(stmt, 2, Int32(dur))
            sqlite3_bind_text(stmt, 3, bundleId, -1, nil)
            sqlite3_bind_double(stmt, 4, startTime.timeIntervalSince1970)
            sqlite3_step(stmt)
        }
        sqlite3_finalize(stmt)
    }

    // MARK: - Queries
    public func todayTotal() -> String {
        let sod = Calendar.current.startOfDay(for: Date()).timeIntervalSince1970
        let sql = "SELECT SUM(duration_seconds) FROM usage_sessions WHERE started_at >= ?"
        var stmt: OpaquePointer?; var total = 0
        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_double(stmt, 1, sod)
            if sqlite3_step(stmt) == SQLITE_ROW { total = Int(sqlite3_column_int(stmt, 0)) }
        }
        sqlite3_finalize(stmt)
        let h = total / 3600, m = (total % 3600) / 60
        return h > 0 ? "\(h)h \(m)m" : "\(m)m"
    }

    public func topApps(limit: Int = 5) -> [ScreenTimeEntry] {
        let sod = Calendar.current.startOfDay(for: Date()).timeIntervalSince1970
        let sql = "SELECT bundle_id, app_name, SUM(duration_seconds) as t FROM usage_sessions WHERE started_at >= ? GROUP BY bundle_id ORDER BY t DESC LIMIT ?"
        var stmt: OpaquePointer?; var apps: [ScreenTimeEntry] = []
        if sqlite3_prepare_v2(db, sql, -1, &stmt, nil) == SQLITE_OK {
            sqlite3_bind_double(stmt, 1, sod)
            sqlite3_bind_int(stmt, 2, Int32(limit))
            while sqlite3_step(stmt) == SQLITE_ROW {
                let bid = String(cString: sqlite3_column_text(stmt, 0))
                let name = String(cString: sqlite3_column_text(stmt, 1))
                let secs = Int(sqlite3_column_int(stmt, 2))
                apps.append(ScreenTimeEntry(bundleId: bid, appName: name, seconds: secs))
            }
        }
        sqlite3_finalize(stmt)
        return apps
    }
}
