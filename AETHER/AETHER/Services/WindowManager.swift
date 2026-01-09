// AETHER - Window Manager Service
// Uses Accessibility API for window management

import Foundation
import AppKit
import CoreGraphics

class WindowManager {
    static let shared = WindowManager()

    private init() {}

    // MARK: - Capture All Windows
    func captureAllWindows() async -> [WindowState] {
        var windowStates: [WindowState] = []

        let apps = NSWorkspace.shared.runningApplications.filter {
            $0.activationPolicy == .regular && !$0.isHidden
        }

        for app in apps {
            guard let bundleId = app.bundleIdentifier,
                  let appName = app.localizedName else { continue }

            let windows = getWindowsForApp(pid: app.processIdentifier)

            for (index, window) in windows.enumerated() {
                let displayIndex = getDisplayIndex(for: window.frame)
                let state = WindowState(
                    bundleId: bundleId,
                    appName: appName,
                    windowTitle: window.title ?? "Window \(index + 1)",
                    frame: window.frame,
                    displayIndex: displayIndex
                )
                windowStates.append(state)
            }
        }

        print("🌌 Captured \(windowStates.count) windows")
        return windowStates
    }

    // MARK: - Restore Windows
    func restoreWindows(from states: [WindowState]) async {
        for state in states {
            // First, ensure the app is running
            if !isAppRunning(bundleId: state.bundleId) {
                await launchApp(bundleId: state.bundleId)
                try? await Task.sleep(nanoseconds: 500_000_000) // 0.5s delay
            }

            // Find the app and move its window
            guard let app = NSWorkspace.shared.runningApplications.first(where: {
                $0.bundleIdentifier == state.bundleId
            }) else { continue }

            moveWindow(pid: app.processIdentifier, to: state.frame.cgRect)
        }

        print("🌌 Restored \(states.count) windows")
    }

    // MARK: - Get Windows for App (Accessibility API)
    private func getWindowsForApp(pid: pid_t) -> [(frame: CGRect, title: String?)] {
        var windows: [(frame: CGRect, title: String?)] = []

        let appRef = AXUIElementCreateApplication(pid)

        var value: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(appRef, kAXWindowsAttribute as CFString, &value)

        guard result == .success, let windowList = value as? [AXUIElement] else {
            return windows
        }

        for window in windowList {
            var positionValue: CFTypeRef?
            var sizeValue: CFTypeRef?
            var titleValue: CFTypeRef?

            AXUIElementCopyAttributeValue(window, kAXPositionAttribute as CFString, &positionValue)
            AXUIElementCopyAttributeValue(window, kAXSizeAttribute as CFString, &sizeValue)
            AXUIElementCopyAttributeValue(window, kAXTitleAttribute as CFString, &titleValue)

            var position = CGPoint.zero
            var size = CGSize.zero

            if let positionValue = positionValue {
                AXValueGetValue(positionValue as! AXValue, .cgPoint, &position)
            }
            if let sizeValue = sizeValue {
                AXValueGetValue(sizeValue as! AXValue, .cgSize, &size)
            }

            let title = titleValue as? String
            let frame = CGRect(origin: position, size: size)

            // Skip tiny windows (likely hidden/helper windows)
            if size.width > 100 && size.height > 100 {
                windows.append((frame: frame, title: title))
            }
        }

        return windows
    }

    // MARK: - Move Window
    private func moveWindow(pid: pid_t, to frame: CGRect) {
        let appRef = AXUIElementCreateApplication(pid)

        var value: CFTypeRef?
        let result = AXUIElementCopyAttributeValue(appRef, kAXWindowsAttribute as CFString, &value)

        guard result == .success, let windowList = value as? [AXUIElement],
              let window = windowList.first else { return }

        // Set position
        var position = frame.origin
        if let positionValue = AXValueCreate(.cgPoint, &position) {
            AXUIElementSetAttributeValue(window, kAXPositionAttribute as CFString, positionValue)
        }

        // Set size
        var size = frame.size
        if let sizeValue = AXValueCreate(.cgSize, &size) {
            AXUIElementSetAttributeValue(window, kAXSizeAttribute as CFString, sizeValue)
        }
    }

    // MARK: - Helpers
    private func getDisplayIndex(for frame: CGRect) -> Int {
        let screens = NSScreen.screens
        for (index, screen) in screens.enumerated() {
            if screen.frame.contains(frame.origin) {
                return index
            }
        }
        return 0
    }

    private func isAppRunning(bundleId: String) -> Bool {
        NSWorkspace.shared.runningApplications.contains { $0.bundleIdentifier == bundleId }
    }

    private func launchApp(bundleId: String) async {
        guard let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundleId) else {
            print("⚠️ Could not find app: \(bundleId)")
            return
        }

        do {
            try await NSWorkspace.shared.openApplication(at: url, configuration: .init())
            print("🚀 Launched: \(bundleId)")
        } catch {
            print("⚠️ Failed to launch \(bundleId): \(error)")
        }
    }

    // MARK: - Get Active App Info
    func getActiveApp() -> (bundleId: String, appName: String)? {
        guard let app = NSWorkspace.shared.frontmostApplication,
              let bundleId = app.bundleIdentifier,
              let appName = app.localizedName else {
            return nil
        }
        return (bundleId, appName)
    }

    // MARK: - Get Running Apps
    func getRunningApps() -> [String] {
        NSWorkspace.shared.runningApplications
            .filter { $0.activationPolicy == .regular }
            .compactMap { $0.localizedName }
    }
}
