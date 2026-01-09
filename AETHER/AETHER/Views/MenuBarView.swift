// AETHER - MenuBar View
// Main menubar dropdown interface

import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var appState: AppState
    @State private var showingStats = false
    @State private var aiSuggestion: String?
    @State private var isLMStudioAvailable = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "sparkles.rectangle.stack")
                    .foregroundColor(.accentColor)
                Text("AETHER")
                    .font(.headline)
                    .fontWeight(.bold)
                Spacer()
                if let profile = appState.currentProfile {
                    Text(profile.name)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(Color.accentColor.opacity(0.2))
                        .cornerRadius(4)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color(NSColor.windowBackgroundColor))

            Divider()

            // AI Suggestion Banner
            if let suggestion = aiSuggestion {
                HStack {
                    Image(systemName: "sparkles")
                        .foregroundColor(.yellow)
                    Text(suggestion)
                        .font(.caption)
                        .foregroundColor(.primary)
                    Spacer()
                    Button(action: { aiSuggestion = nil }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                }
                .padding(10)
                .background(Color.yellow.opacity(0.1))

                Divider()
            }

            // Profiles Section
            VStack(alignment: .leading, spacing: 4) {
                Text("PROFILES")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 16)
                    .padding(.top, 8)

                ForEach(appState.profiles) { profile in
                    ProfileRow(profile: profile, isActive: profile.id == appState.currentProfile?.id) {
                        appState.switchProfile(profile)
                    } onCapture: {
                        appState.captureCurrentLayout(for: profile)
                    }
                }
            }

            Divider()
                .padding(.vertical, 8)

            // Quick Stats
            VStack(alignment: .leading, spacing: 4) {
                Text("TODAY'S FOCUS")
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 16)

                QuickStatsView()
                    .padding(.horizontal, 16)
                    .padding(.bottom, 8)
            }

            Divider()

            // Footer Actions
            HStack {
                Button(action: { checkAISuggestion() }) {
                    Label("Ask AI", systemImage: isLMStudioAvailable ? "sparkles" : "sparkles.rectangle.stack")
                }
                .disabled(!isLMStudioAvailable)

                Spacer()

                SettingsLink {
                    Label("Settings", systemImage: "gear")
                }

                Button(action: { NSApplication.shared.terminate(nil) }) {
                    Label("Quit", systemImage: "power")
                }
            }
            .buttonStyle(.plain)
            .font(.caption)
            .foregroundColor(.secondary)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
        }
        .frame(width: 320)
        .onAppear {
            checkLMStudioStatus()
        }
    }

    private func checkLMStudioStatus() {
        Task {
            isLMStudioAvailable = await LMStudioClient.shared.isAvailable()
        }
    }

    private func checkAISuggestion() {
        Task {
            let apps = WindowManager.shared.getRunningApps()
            let hour = Calendar.current.component(.hour, from: Date())

            if let suggestion = await LMStudioClient.shared.suggestProfile(currentApps: apps, hour: hour) {
                await MainActor.run {
                    aiSuggestion = "Suggestion: Switch to \(suggestion.capitalized)"
                }
            }
        }
    }
}

// MARK: - Profile Row
struct ProfileRow: View {
    let profile: Profile
    let isActive: Bool
    let onSelect: () -> Void
    let onCapture: () -> Void

    @State private var isHovering = false

    var body: some View {
        HStack {
            Image(systemName: profile.icon)
                .foregroundColor(isActive ? .accentColor : .secondary)
                .frame(width: 20)

            Text(profile.name)
                .fontWeight(isActive ? .semibold : .regular)

            if isActive {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundColor(.green)
                    .font(.caption)
            }

            Spacer()

            if isHovering {
                Button(action: onCapture) {
                    Image(systemName: "camera.fill")
                        .font(.caption)
                }
                .buttonStyle(.plain)
                .foregroundColor(.accentColor)
                .help("Capture current layout")
            }

            Text("\(profile.windowStates.count) windows")
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(isHovering || isActive ? Color.accentColor.opacity(0.1) : Color.clear)
        .cornerRadius(6)
        .contentShape(Rectangle())
        .onHover { hovering in
            isHovering = hovering
        }
        .onTapGesture {
            if !isActive {
                onSelect()
            }
        }
    }
}

// MARK: - Quick Stats View
struct QuickStatsView: View {
    @State private var topApps: [AppUsage] = []
    @State private var todayTotal: String = "0m"

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: "clock.fill")
                    .foregroundColor(.accentColor)
                Text("Total: \(todayTotal)")
                    .font(.caption)
                    .fontWeight(.medium)
            }

            ForEach(topApps.prefix(3)) { app in
                HStack {
                    Text(app.appName)
                        .font(.caption)
                        .foregroundColor(.primary)
                        .lineLimit(1)
                    Spacer()
                    Text(app.formattedDuration)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }

            if topApps.isEmpty {
                Text("Tracking started. Check back soon!")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .italic()
            }
        }
        .onAppear {
            loadStats()
        }
    }

    private func loadStats() {
        topApps = ScreenTimeService.shared.getTopApps(limit: 3)
        let stats = ScreenTimeService.shared.getTodayStats()
        todayTotal = stats.formattedTotal
    }
}

#Preview {
    MenuBarView()
        .environmentObject(AppState.shared)
}
