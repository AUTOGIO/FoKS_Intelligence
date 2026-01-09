// AETHER - Settings View
// Profile management and app settings

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var appState: AppState
    @State private var selectedProfile: Profile?
    @State private var newProfileName = ""
    @State private var showingNewProfile = false
    @State private var lmStudioURL = "http://100.72.60.38:1234/v1"
    @State private var isLMStudioConnected = false

    var body: some View {
        TabView {
            // Profiles Tab
            profilesTab
                .tabItem {
                    Label("Profiles", systemImage: "rectangle.3.group")
                }

            // Screen Time Tab
            screenTimeTab
                .tabItem {
                    Label("Screen Time", systemImage: "clock.fill")
                }

            // AI Settings Tab
            aiSettingsTab
                .tabItem {
                    Label("AI", systemImage: "sparkles")
                }

            // About Tab
            aboutTab
                .tabItem {
                    Label("About", systemImage: "info.circle")
                }
        }
        .frame(width: 500, height: 400)
        .onAppear {
            checkLMStudioConnection()
        }
    }

    // MARK: - Profiles Tab
    private var profilesTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Workspace Profiles")
                .font(.title2)
                .fontWeight(.bold)

            List(selection: $selectedProfile) {
                ForEach(appState.profiles) { profile in
                    HStack {
                        Image(systemName: profile.icon)
                            .foregroundColor(.accentColor)
                            .frame(width: 24)

                        VStack(alignment: .leading) {
                            Text(profile.name)
                                .fontWeight(.medium)
                            Text("\(profile.windowStates.count) windows saved")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }

                        Spacer()

                        if profile.isActive {
                            Text("Active")
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 2)
                                .background(Color.green.opacity(0.2))
                                .foregroundColor(.green)
                                .cornerRadius(4)
                        }
                    }
                    .padding(.vertical, 4)
                    .tag(profile)
                }
                .onDelete(perform: deleteProfile)
            }
            .listStyle(.inset)

            HStack {
                Button(action: { showingNewProfile = true }) {
                    Label("New Profile", systemImage: "plus")
                }

                Spacer()

                if let profile = selectedProfile {
                    Button("Capture Layout") {
                        appState.captureCurrentLayout(for: profile)
                    }

                    Button("Activate") {
                        appState.switchProfile(profile)
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
        }
        .padding()
        .sheet(isPresented: $showingNewProfile) {
            newProfileSheet
        }
    }

    // MARK: - New Profile Sheet
    private var newProfileSheet: some View {
        VStack(spacing: 16) {
            Text("Create New Profile")
                .font(.headline)

            TextField("Profile Name", text: $newProfileName)
                .textFieldStyle(.roundedBorder)

            HStack {
                Button("Cancel") {
                    showingNewProfile = false
                    newProfileName = ""
                }

                Spacer()

                Button("Create") {
                    if !newProfileName.isEmpty {
                        _ = ProfileManager.shared.createProfile(name: newProfileName)
                        appState.loadProfiles()
                        showingNewProfile = false
                        newProfileName = ""
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(newProfileName.isEmpty)
            }
        }
        .padding()
        .frame(width: 300)
    }

    // MARK: - Screen Time Tab
    private var screenTimeTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Screen Time Today")
                .font(.title2)
                .fontWeight(.bold)

            let stats = ScreenTimeService.shared.getTodayStats()

            HStack {
                VStack(alignment: .leading) {
                    Text("Total Focus Time")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(stats.formattedTotal)
                        .font(.largeTitle)
                        .fontWeight(.bold)
                        .foregroundColor(.accentColor)
                }
                Spacer()
            }
            .padding()
            .background(Color.accentColor.opacity(0.1))
            .cornerRadius(12)

            Text("Top Applications")
                .font(.headline)

            let topApps = ScreenTimeService.shared.getTopApps(limit: 10)

            List(topApps) { app in
                HStack {
                    Text(app.appName)
                    Spacer()
                    Text(app.formattedDuration)
                        .foregroundColor(.secondary)
                }
            }
            .listStyle(.inset)

            Spacer()
        }
        .padding()
    }

    // MARK: - AI Settings Tab
    private var aiSettingsTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("AI Integration")
                .font(.title2)
                .fontWeight(.bold)

            GroupBox("LM Studio Connection") {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Circle()
                            .fill(isLMStudioConnected ? Color.green : Color.red)
                            .frame(width: 10, height: 10)
                        Text(isLMStudioConnected ? "Connected" : "Disconnected")
                            .foregroundColor(isLMStudioConnected ? .green : .red)
                    }

                    TextField("LM Studio URL", text: $lmStudioURL)
                        .textFieldStyle(.roundedBorder)

                    Button("Test Connection") {
                        checkLMStudioConnection()
                    }
                }
                .padding(.vertical, 8)
            }

            GroupBox("AI Features") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Profile Suggestions", isOn: .constant(true))
                    Text("AI will suggest optimal profiles based on time and apps")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Toggle("Smart Productivity Tips", isOn: .constant(true))
                    Text("Get occasional tips to improve focus")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.vertical, 8)
            }

            Spacer()
        }
        .padding()
    }

    // MARK: - About Tab
    private var aboutTab: some View {
        VStack(spacing: 20) {
            Image(systemName: "sparkles.rectangle.stack")
                .font(.system(size: 64))
                .foregroundColor(.accentColor)

            Text("AETHER")
                .font(.largeTitle)
                .fontWeight(.bold)

            Text("Adaptive Environment & Task Handler\nfor Enhanced Reality")
                .multilineTextAlignment(.center)
                .foregroundColor(.secondary)

            Divider()
                .frame(width: 200)

            VStack(spacing: 4) {
                Text("Version 1.0.0")
                    .font(.caption)
                Text("Built for Apple M3")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Text("© 2026 Giovannini Mare Capital LLC - Tech Division")
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .padding()
    }

    // MARK: - Helpers
    private func deleteProfile(at offsets: IndexSet) {
        for index in offsets {
            let profile = appState.profiles[index]
            ProfileManager.shared.deleteProfile(profile)
        }
        appState.loadProfiles()
    }

    private func checkLMStudioConnection() {
        Task {
            isLMStudioConnected = await LMStudioClient.shared.isAvailable()
        }
    }
}

#Preview {
    SettingsView()
        .environmentObject(AppState.shared)
}
