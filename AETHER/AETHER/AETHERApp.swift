// AETHER - Adaptive Environment & Task Handler for Enhanced Reality
// Main App Entry Point
// Native SwiftUI Menubar App for M3 iMac

import SwiftUI
import AppKit

@main
struct AETHERApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var appState = AppState.shared

    var body: some Scene {
        MenuBarExtra {
            MenuBarView()
                .environmentObject(appState)
        } label: {
            Image(systemName: "sparkles.rectangle.stack")
        }
        .menuBarExtraStyle(.window)

        Settings {
            SettingsView()
                .environmentObject(appState)
        }
    }
}

// MARK: - App Delegate
class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Hide dock icon - menubar only app
        NSApp.setActivationPolicy(.accessory)

        // Start screen time tracking
        ScreenTimeService.shared.startTracking()

        // Check accessibility permissions
        checkAccessibilityPermissions()

        // Launch LM Studio if not running
        launchLMStudioIfNeeded()

        print("🌌 AETHER launched successfully")
    }

    func applicationWillTerminate(_ notification: Notification) {
        ScreenTimeService.shared.stopTracking()
        print("🌌 AETHER shutting down")
    }

    private func checkAccessibilityPermissions() {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true]
        let trusted = AXIsProcessTrustedWithOptions(options as CFDictionary)

        if !trusted {
            print("⚠️ Accessibility permission required - prompting user")
        } else {
            print("✅ Accessibility permission granted")
        }
    }

    private func launchLMStudioIfNeeded() {
        // Check if LM Studio is already running
        let runningApps = NSWorkspace.shared.runningApplications
        let lmStudioRunning = runningApps.contains {
            $0.bundleIdentifier == "com.lmstudio.LMStudio" ||
            $0.localizedName?.lowercased().contains("lm studio") == true
        }

        if lmStudioRunning {
            print("✅ LM Studio already running")
            return
        }

        // Try to launch LM Studio
        let possiblePaths = [
            "/Applications/LM Studio.app",
            "/Applications/LMStudio.app",
            "~/Applications/LM Studio.app"
        ]

        for path in possiblePaths {
            let expandedPath = NSString(string: path).expandingTildeInPath
            let url = URL(fileURLWithPath: expandedPath)

            if FileManager.default.fileExists(atPath: expandedPath) {
                NSWorkspace.shared.openApplication(at: url, configuration: .init()) { app, error in
                    if let error = error {
                        print("⚠️ Failed to launch LM Studio: \(error)")
                    } else {
                        print("🚀 LM Studio launched automatically")
                    }
                }
                return
            }
        }

        print("⚠️ LM Studio not found in Applications")
    }
}

// MARK: - Global App State
class AppState: ObservableObject {
    static let shared = AppState()

    @Published var currentProfile: Profile?
    @Published var profiles: [Profile] = []
    @Published var isCapturing = false
    @Published var lastSuggestion: String?

    private init() {
        loadProfiles()
    }

    func loadProfiles() {
        profiles = ProfileManager.shared.loadProfiles()
        currentProfile = profiles.first { $0.isActive }
    }

    func switchProfile(_ profile: Profile) {
        ProfileManager.shared.activateProfile(profile)
        loadProfiles()
    }

    func captureCurrentLayout(for profile: Profile) {
        isCapturing = true
        Task {
            await ProfileManager.shared.captureLayout(for: profile)
            await MainActor.run {
                self.isCapturing = false
                self.loadProfiles()
            }
        }
    }
}
