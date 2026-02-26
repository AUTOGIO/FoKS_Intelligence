// FoKS - Unified Intelligence Platform
// Single native macOS app replacing FoKS_Intelligence + AETHER + VESTA
// Target: iMac Mac15,5 / Apple M3 / 16GB / macOS 26.3

import SwiftUI
import AppKit
import os.log
import ServiceManagement
import FoKS_Service_Lib

private let logger = Logger(subsystem: "us.giovannini.foks", category: "App")

@main
struct FoKSApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var hub = FoKSHub.shared

    var body: some Scene {
        // AETHER menubar (workspace manager)
        MenuBarExtra {
            AETHERMenuBarView()
                .environmentObject(hub)
        } label: {
            Image(systemName: "sparkles.rectangle.stack")
        }
        .menuBarExtraStyle(.window)

        // VESTA menubar (portfolio tracker)
        MenuBarExtra {
            VESTAMenuBarView()
                .environmentObject(hub)
        } label: {
            HStack(spacing: 4) {
                Image(systemName: "chart.pie.fill")
                if let total = hub.portfolioTotalFormatted {
                    Text(total).font(.caption)
                }
            }
        }
        .menuBarExtraStyle(.window)

        // Dashboard window (CMD+D to open)
        Window("FoKS Dashboard", id: "dashboard") {
            DashboardView()
                .environmentObject(hub)
        }
        .defaultSize(width: 900, height: 600)
        .keyboardShortcut("d", modifiers: [.command])

        Settings {
            SettingsView()
                .environmentObject(hub)
        }
    }
}

// MARK: - App Delegate
class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Menubar-only — hide dock icon
        NSApp.setActivationPolicy(.accessory)

        let hub = FoKSHub.shared

        // Start services
        hub.screenTime.startTracking()
        hub.processMonitor.startMonitoring()

        // Check accessibility
        let opts = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true]
        let trusted = AXIsProcessTrustedWithOptions(opts as CFDictionary)
        logger.info("Accessibility: \(trusted ? "granted" : "needs prompt")")


        // Register as login item
        if #available(macOS 13.0, *) {
            try? SMAppService.mainApp.register()
        }

        // Start embedded HTTP server for n8n/Shortcuts compatibility
        Task { await hub.httpServer.start() }

        logger.info("🚀 FoKS launched — Mac15,5 M3 16GB")
    }

    func applicationWillTerminate(_ notification: Notification) {
        FoKSHub.shared.screenTime.stopTracking()
        FoKSHub.shared.processMonitor.stopMonitoring()
        Task { await FoKSHub.shared.httpServer.stop() }
        logger.info("FoKS shutting down")
    }
}
