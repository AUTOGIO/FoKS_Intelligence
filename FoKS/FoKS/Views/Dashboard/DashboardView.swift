// DashboardView — Main FoKS window (Cmd+D)
// Tabbed interface: AETHER | VESTA | FileHQ Files | FileHQ Notes

import SwiftUI
import FoKS_Service_Lib

struct DashboardView: View {
    @EnvironmentObject private var hub: FoKSHub

    enum Tab: String, CaseIterable {
        case aether = "AETHER"
        case vesta = "VESTA"
        case files = "FileHQ"
        case notes = "Notes"

        var icon: String {
            switch self {
            case .aether: "sparkles.rectangle.stack"
            case .vesta: "chart.pie.fill"
            case .files: "folder.fill"
            case .notes: "note.text"
            }
        }
    }

    @State private var selectedTab: Tab = .files

    var body: some View {
        NavigationSplitView {
            List(Tab.allCases, id: \.self, selection: $selectedTab) { tab in
                Label(tab.rawValue, systemImage: tab.icon)
            }
            .navigationSplitViewColumnWidth(min: 130, ideal: 150)

            // System health footer
            VStack(alignment: .leading, spacing: 4) {
                Divider()
                HStack(spacing: 6) {
                    Circle().fill(hub.openAIOnline ? .green : .red).frame(width: 6, height: 6)
                    Text("OpenAI").font(.caption2)
                }
                HStack(spacing: 6) {
                    Circle().fill(hub.fbpOnline ? .green : .red).frame(width: 6, height: 6)
                    Text("FBP").font(.caption2)
                }
                if let stats = hub.systemStats {
                    Text("CPU \(String(format: "%.0f", stats.cpuUsage))% · Mem \(String(format: "%.1f", stats.memoryUsedGB))G")
                        .font(.caption2).foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 12).padding(.bottom, 8)
        } detail: {
            switch selectedTab {
            case .aether:
                AETHERDashboardView()
            case .vesta:
                VESTADashboardView()
            case .files:
                FileHQBrowserView()
            case .notes:
                FileHQNotesView()
            }
        }
        .preferredColorScheme(.dark)
    }
}

// MARK: - Placeholder views for AETHER and VESTA dashboard panels

struct AETHERDashboardView: View {
    @EnvironmentObject private var hub: FoKSHub

    var body: some View {
        VStack(spacing: 16) {
            Text("AETHER — Workspace Manager").font(.title2.bold())
            if let profile = hub.activeProfile {
                Label("Active: \(profile.name)", systemImage: profile.icon).font(.headline)
                Text("\(profile.windowStates.count) windows captured").foregroundStyle(.secondary)
            }
            HStack(spacing: 12) {
                ForEach(hub.profiles) { profile in
                    Button(profile.name) { hub.switchProfile(profile) }
                        .buttonStyle(.borderedProminent)
                        .tint(profile.isActive ? .blue : .gray)
                }
            }
            if let suggestion = hub.aiSuggestion {
                Label(suggestion, systemImage: "sparkles").foregroundStyle(.yellow)
            }
            Button("Ask AI Suggestion") { hub.askAISuggestion() }
            Spacer()

            // Screen Time
            VStack(alignment: .leading) {
                Text("Today's Focus: \(hub.screenTime.todayTotal())").font(.headline)
                ForEach(hub.screenTime.topApps()) { app in
                    HStack { Text(app.appName); Spacer(); Text(app.formatted).foregroundStyle(.secondary) }
                        .font(.caption)
                }
            }
            .padding()
            .background(RoundedRectangle(cornerRadius: 8).fill(.black.opacity(0.2)))
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct VESTADashboardView: View {
    @EnvironmentObject private var hub: FoKSHub

    var body: some View {
        VStack(spacing: 16) {
            Text("VESTA — Portfolio Tracker").font(.title2.bold())
            if let p = hub.portfolio {
                HStack {
                    VStack {
                        Text("Total (\(hub.currency.rawValue))").font(.caption).foregroundStyle(.secondary)
                        switch hub.currency {
                        case .usd: Text(String(format: "$%.0f", p.totalValueUSD)).font(.title.bold())
                        case .brl: Text(String(format: "R$%.0f", p.totalValueBRL)).font(.title.bold())
                        case .eur: Text(String(format: "€%.0f", p.totalValueUSD * 0.92)).font(.title.bold())
                        }
                    }
                    Button { hub.toggleCurrency() } label: { Image(systemName: "arrow.triangle.2.circlepath") }
                }
                // Bucket percentages
                ForEach(Array(p.bucketPercentages.sorted(by: { $0.key < $1.key })), id: \.key) { bucket, pct in
                    HStack {
                        Text(bucket)
                        Spacer()
                        ProgressView(value: pct, total: 100).frame(width: 100)
                        Text(String(format: "%.1f%%", pct)).monospacedDigit()
                    }
                    .font(.caption)
                }
                // Top assets
                ForEach(p.topAssets) { asset in
                    HStack {
                        Text(asset.icon + " " + asset.displayName)
                        Spacer()
                        Text(String(format: "R$%.0f", asset.valueBRL ?? 0)).monospacedDigit().foregroundStyle(.secondary)
                    }
                    .font(.caption)
                }
            } else {
                Text("No portfolio loaded").foregroundStyle(.secondary)
            }
            if let s = hub.portfolioSuggestion {
                Label(s, systemImage: "sparkles").foregroundStyle(.yellow).font(.callout)
            }
            Button("Ask AI Advice") { hub.askPortfolioSuggestion() }
            Spacer()
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
