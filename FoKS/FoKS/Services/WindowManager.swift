// WindowManager — Accessibility API window capture & restore
// Uses AXUIElement for native window management on M3 iMac

import Foundation
import AppKit
import CoreGraphics
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "WindowManager")

public final class WindowManager: @unchecked Sendable {
    public init() {}

    // MARK: - Capture All Visible Windows
    public func captureAllWindows() async -> [WindowState] {
        var states: [WindowState] = []
        let apps = NSWorkspace.shared.runningApplications.filter {
            $0.activationPolicy == .regular && !$0.isHidden
        }

        for app in apps {
            guard let bundleId = app.bundleIdentifier,
                  let appName = app.localizedName else { continue }
            let windows = windowsForPID(app.processIdentifier)
            for (i, win) in windows.enumerated() {
                let displayIdx = displayIndex(for: win.frame)
                states.append(WindowState(
                    bundleId: bundleId, appName: appName,
                    windowTitle: win.title ?? "Window \(i + 1)",
                    frame: win.frame, displayIndex: displayIdx
                ))
            }
        }
        logger.info("Captured \(states.count) windows")
        return states
    }

    // MARK: - Restore Windows from Profile
    public func restoreWindows(from states: [WindowState]) async {
        for state in states {
            if !isRunning(bundleId: state.bundleId) {
                await launchApp(bundleId: state.bundleId)
                try? await Task.sleep(for: .milliseconds(500))
            }
            guard let app = NSWorkspace.shared.runningApplications
                .first(where: { $0.bundleIdentifier == state.bundleId }) else { continue }
            moveWindow(pid: app.processIdentifier, to: state.frame.cgRect)
        }
        logger.info("Restored \(states.count) windows")
    }

    // MARK: - Get Active App
    public func getActiveApp() -> (bundleId: String, appName: String)? {
        guard let app = NSWorkspace.shared.frontmostApplication,
              let bid = app.bundleIdentifier,
              let name = app.localizedName else { return nil }
        return (bid, name)
    }

    public func getRunningApps() -> [String] {
        NSWorkspace.shared.runningApplications
            .filter { $0.activationPolicy == .regular }
            .compactMap(\.localizedName)
    }

    // MARK: - AX Helpers
    private func windowsForPID(_ pid: pid_t) -> [(frame: CGRect, title: String?)] {
        var results: [(CGRect, String?)] = []
        let appRef = AXUIElementCreateApplication(pid)
        var val: CFTypeRef?
        guard AXUIElementCopyAttributeValue(appRef, kAXWindowsAttribute as CFString, &val) == .success,
              let list = val as? [AXUIElement] else { return results }

        for win in list {
            var posRef: CFTypeRef?, sizeRef: CFTypeRef?, titleRef: CFTypeRef?
            AXUIElementCopyAttributeValue(win, kAXPositionAttribute as CFString, &posRef)
            AXUIElementCopyAttributeValue(win, kAXSizeAttribute as CFString, &sizeRef)
            AXUIElementCopyAttributeValue(win, kAXTitleAttribute as CFString, &titleRef)

            var pos = CGPoint.zero, size = CGSize.zero
            if let p = posRef { AXValueGetValue(p as! AXValue, .cgPoint, &pos) }
            if let s = sizeRef { AXValueGetValue(s as! AXValue, .cgSize, &size) }
            guard size.width > 100 && size.height > 100 else { continue }
            results.append((CGRect(origin: pos, size: size), titleRef as? String))
        }
        return results
    }

    private func moveWindow(pid: pid_t, to frame: CGRect) {
        let appRef = AXUIElementCreateApplication(pid)
        var val: CFTypeRef?
        guard AXUIElementCopyAttributeValue(appRef, kAXWindowsAttribute as CFString, &val) == .success,
              let list = val as? [AXUIElement], let win = list.first else { return }

        var pos = frame.origin
        if let pv = AXValueCreate(.cgPoint, &pos) {
            AXUIElementSetAttributeValue(win, kAXPositionAttribute as CFString, pv)
        }
        var sz = frame.size
        if let sv = AXValueCreate(.cgSize, &sz) {
            AXUIElementSetAttributeValue(win, kAXSizeAttribute as CFString, sv)
        }
    }

    private func displayIndex(for frame: CGRect) -> Int {
        for (i, screen) in NSScreen.screens.enumerated() {
            if screen.frame.contains(frame.origin) { return i }
        }
        return 0
    }

    private func isRunning(bundleId: String) -> Bool {
        NSWorkspace.shared.runningApplications.contains { $0.bundleIdentifier == bundleId }
    }

    private func launchApp(bundleId: String) async {
        guard let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundleId) else { return }
        do {
            try await NSWorkspace.shared.openApplication(at: url, configuration: .init())
        } catch {
            logger.error("Failed to launch \(bundleId): \(error.localizedDescription)")
        }
    }
}
