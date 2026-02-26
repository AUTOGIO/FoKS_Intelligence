// SettingsView — FoKS preferences (Settings scene)
// Tabs: General, AI, FileHQ, About

import SwiftUI
import FoKS_Service_Lib

struct SettingsView: View {
    @EnvironmentObject private var hub: FoKSHub
    @AppStorage("openAIAPIKey") private var apiKey = ""
    @AppStorage("openAIChatModel") private var chatModel = "gpt-4o-mini"
    @AppStorage("fbpBaseURL") private var fbpURL = "http://localhost:8000"
    @AppStorage("useOnDeviceAI") private var useOnDevice = true

    var body: some View {
        TabView {
            generalTab.tabItem { Label("General", systemImage: "gear") }
            aiTab.tabItem { Label("AI", systemImage: "brain") }
            fileHQTab.tabItem { Label("FileHQ", systemImage: "folder") }
            aboutTab.tabItem { Label("About", systemImage: "info.circle") }
        }
        .frame(width: 500, height: 340)
        .padding()
    }

    private var generalTab: some View {
        Form {
            Section("System") {
                LabeledContent("Hardware", value: "\(FoKSConfig.chip) · \(FoKSConfig.memoryGB)GB")
                LabeledContent("FBP Backend", value: fbpURL)
                HStack {
                    Circle().fill(hub.openAIOnline ? .green : .red).frame(width: 8, height: 8)
                    Text("OpenAI")
                    Spacer()
                    Circle().fill(hub.fbpOnline ? .green : .red).frame(width: 8, height: 8)
                    Text("FBP")
                }
            }
        }.formStyle(.grouped)
    }

    private var aiTab: some View {
        Form {
            Section("OpenAI") {
                SecureField("API Key", text: $apiKey)
                TextField("Chat Model", text: $chatModel)
            }
            Section("Notes Evaluation") {
                Toggle("Use on-device AI (no API key needed)", isOn: $useOnDevice)
                    .onChange(of: useOnDevice) { _, val in hub.useOnDeviceAI = val }
            }
        }.formStyle(.grouped)
    }

    private var fileHQTab: some View {
        Form {
            Section("File Organization") {
                Text("Default categories: Images, Documents, Videos, Audio, Archives, Scripts, Other")
                    .font(.caption).foregroundStyle(.secondary)
                Text("Custom category editing coming in a future update.")
                    .font(.caption).foregroundStyle(.secondary)
            }
            Section("NFA Integration") {
                LabeledContent("NFA Output Dir") {
                    Text(NFAFileOrganizationBridge.defaultNFADir.path)
                        .font(.system(.caption, design: .monospaced))
                }
                Button("Organize NFA Outputs Now") { Task { await hub.organizeNFAOutputs() } }
            }
        }.formStyle(.grouped)
    }

    private var aboutTab: some View {
        VStack(spacing: 12) {
            Image(systemName: "sparkles.rectangle.stack").font(.system(size: 48)).foregroundStyle(.blue)
            Text("FoKS Intelligence").font(.title.bold())
            Text("AETHER · VESTA · FileHQ").font(.caption).foregroundStyle(.secondary)
            Text("Version 3.0.0").font(.caption2).foregroundStyle(.tertiary)
            Divider()
            Text("iMac Mac15,5 · Apple M3 · macOS Tahoe · Swift 6")
                .font(.caption2).foregroundStyle(.tertiary)
            Text("© 2026 Giovannini Mare Capital LLC")
                .font(.caption2).foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
