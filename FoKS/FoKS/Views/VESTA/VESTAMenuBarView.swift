// VESTAMenuBarView — MenuBar dropdown for portfolio tracking

import SwiftUI
import FoKS_Service_Lib

struct VESTAMenuBarView: View {
    @EnvironmentObject private var hub: FoKSHub

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: "chart.pie.fill").foregroundStyle(.green)
                Text("VESTA").font(.headline.bold())
                Spacer()
                Button { hub.toggleCurrency() } label: {
                    Text(hub.currency.symbol).font(.caption.bold())
                }
            }

            if let p = hub.portfolio {
                Divider()
                HStack {
                    Text("Total").foregroundStyle(.secondary)
                    Spacer()
                    switch hub.currency {
                    case .usd: Text(String(format: "$%.0f", p.totalValueUSD)).font(.title3.bold())
                    case .brl: Text(String(format: "R$%.0f", p.totalValueBRL)).font(.title3.bold())
                    case .eur: Text(String(format: "€%.0f", p.totalValueUSD * 0.92)).font(.title3.bold())
                    }
                }

                Divider()
                Text("BUCKETS").font(.caption2).foregroundStyle(.secondary)
                ForEach(Array(p.bucketPercentages.sorted(by: { $0.key < $1.key })), id: \.key) { bucket, pct in
                    HStack {
                        Text(bucket).font(.caption)
                        Spacer()
                        Text(String(format: "%.1f%%", pct)).font(.caption.monospacedDigit())
                    }
                }

                Divider()
                Text("TOP ASSETS").font(.caption2).foregroundStyle(.secondary)
                ForEach(p.topAssets.prefix(5)) { asset in
                    HStack {
                        Text(asset.icon + " " + asset.displayName).font(.caption).lineLimit(1)
                        Spacer()
                        Text(String(format: "R$%.0f", asset.valueBRL ?? 0)).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                    }
                }
            } else {
                Text("No portfolio loaded").font(.caption).foregroundStyle(.secondary)
            }

            if let s = hub.portfolioSuggestion {
                Divider()
                Label(s, systemImage: "sparkles").font(.caption).foregroundStyle(.yellow)
            }

            Divider()
            Button("Ask AI") { hub.askPortfolioSuggestion() }.font(.caption)
            Button("Refresh") { hub.loadPortfolio() }.font(.caption)
            Divider()
            Button("Quit FoKS") { NSApplication.shared.terminate(nil) }.font(.caption)
        }
        .padding(12)
        .frame(width: 340)
    }
}
