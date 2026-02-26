// AETHERMenuBarView — MenuBar dropdown for workspace management

import SwiftUI
import FoKS_Service_Lib

struct AETHERMenuBarView: View {
    @EnvironmentObject private var hub: FoKSHub

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "sparkles.rectangle.stack").foregroundStyle(.blue)
                Text("AETHER").font(.headline.bold())
                Spacer()
                if let p = hub.activeProfile { Text(p.name).font(.caption).foregroundStyle(.secondary) }
            }

            if let suggestion = hub.aiSuggestion {
                Label(suggestion, systemImage: "sparkles").font(.caption).foregroundStyle(.yellow)
            }

            Divider()
            Text("PROFILES").font(.caption2).foregroundStyle(.secondary)

            ForEach(hub.profiles) { profile in
                HStack {
                    Image(systemName: profile.icon).frame(width: 16)
                    Text(profile.name)
                    Spacer()
                    Text("\(profile.windowStates.count)w").font(.caption2).foregroundStyle(.secondary)
                    if profile.isActive { Image(systemName: "checkmark").foregroundStyle(.green).font(.caption) }
                }
                .contentShape(Rectangle())
                .onTapGesture { hub.switchProfile(profile) }
            }

            Divider()
            Text("TODAY").font(.caption2).foregroundStyle(.secondary)
            Text(hub.screenTime.todayTotal()).font(.callout.bold())
            ForEach(hub.screenTime.topApps(limit: 3)) { app in
                HStack { Text(app.appName).font(.caption); Spacer(); Text(app.formatted).font(.caption).foregroundStyle(.secondary) }
            }

            Divider()
            Button("Ask AI") { hub.askAISuggestion() }.font(.caption)
            Button("Dashboard ⌘D") { openDashboard() }.font(.caption)
            Divider()
            Button("Quit FoKS") { NSApplication.shared.terminate(nil) }.font(.caption)
        }
        .padding(12)
        .frame(width: 300)
    }

    private func openDashboard() {
        if let window = NSApp.windows.first(where: { $0.title == "FoKS Dashboard" }) {
            window.makeKeyAndOrderFront(nil)
        } else {
            NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
        }
    }
}
