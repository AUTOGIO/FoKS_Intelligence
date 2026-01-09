// VESTA - MenuBar View
// GMC Brand Theme with Asset Management

import SwiftUI

struct MenuBarView: View {
    @EnvironmentObject var viewModel: PortfolioViewModel
    @State private var showingAssetEditor = false
    @State private var newAsset: Asset?

    var body: some View {
        VStack(spacing: 0) {
            // Header
            headerSection

            Divider().background(Color.gmcVerdeScandal.opacity(0.3))

            // AI Suggestion Banner
            if let suggestion = viewModel.suggestion {
                suggestionBanner(suggestion)
                Divider().background(Color.gmcVerdeScandal.opacity(0.3))
            }

            // Main Content
            if let portfolio = viewModel.portfolio {
                ScrollView {
                    VStack(spacing: 12) {
                        // Portfolio Summary
                        portfolioSummary(portfolio)

                        Divider().background(Color.gmcGrigioAcheso)

                        // Bucket Allocation
                        bucketSection(portfolio)

                        Divider().background(Color.gmcGrigioAcheso)

                        // Top Assets
                        topAssetsSection(portfolio)
                    }
                    .padding(.vertical, 8)
                }
                .frame(maxHeight: 350)
            } else if viewModel.isLoading {
                loadingView
            } else if let error = viewModel.error {
                errorView(error)
            }

            Divider().background(Color.gmcVerdeScandal.opacity(0.3))

            // Footer Actions
            footerSection
        }
        .frame(width: 360)
        .background(Color.gmcCarbonBlack)
        .sheet(isPresented: $showingAssetEditor) {
            if let asset = newAsset {
                AssetEditorView(asset: asset, isNew: true) { savedAsset in
                    viewModel.addAsset(savedAsset)
                    showingAssetEditor = false
                    newAsset = nil
                }
            }
        }
    }

    // MARK: - Header
    private var headerSection: some View {
        HStack {
            // GMC Logo placeholder
            Image(systemName: "chart.pie.fill")
                .foregroundColor(.gmcVerdeScandal)
                .font(.title2)

            VStack(alignment: .leading, spacing: 0) {
                Text("VESTA")
                    .font(.headline)
                    .fontWeight(.bold)
                    .foregroundColor(.gmcMetallicSilver)
                Text("GMC Portfolio")
                    .font(.caption2)
                    .foregroundColor(.gmcGrigioAcheso)
            }

            Spacer()

            // Currency Toggle
            Button(action: { viewModel.toggleCurrency() }) {
                Text(viewModel.currency.rawValue)
                    .font(.caption)
                    .fontWeight(.bold)
                    .foregroundColor(.gmcCarbonBlack)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color.gmcVerdeScandal)
                    .cornerRadius(4)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gmcCarbonBlack)
    }

    // MARK: - Suggestion Banner
    private func suggestionBanner(_ suggestion: String) -> some View {
        HStack {
            Image(systemName: "sparkles")
                .foregroundColor(.gmcVerdeScandal)
            Text(suggestion)
                .font(.caption)
                .foregroundColor(.gmcMetallicSilver)
                .lineLimit(2)
            Spacer()
            Button(action: { viewModel.suggestion = nil }) {
                Image(systemName: "xmark.circle.fill")
                    .foregroundColor(.gmcGrigioAcheso)
            }
            .buttonStyle(.plain)
        }
        .padding(10)
        .background(Color.gmcGrigioAcheso.opacity(0.3))
    }

    // MARK: - Portfolio Summary
    private func portfolioSummary(_ portfolio: Portfolio) -> some View {
        VStack(spacing: 12) {
            // Total Value
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("TOTAL PORTFOLIO")
                        .font(.caption2)
                        .foregroundColor(.gmcGrigioAcheso)

                    Text(formatValue(portfolio.totalValueUSD, portfolio: portfolio))
                        .font(.title)
                        .fontWeight(.bold)
                        .foregroundColor(.gmcVerdeScandal)
                }
                Spacer()
            }

            // Breakdown
            HStack(spacing: 20) {
                StatBox(
                    title: "Real Estate",
                    value: formatValue(portfolio.realEstateValueBRL / portfolio.meta.fxUsdBrl, portfolio: portfolio),
                    icon: "🏠"
                )
                StatBox(
                    title: "Financial",
                    value: formatValue(portfolio.financialAssetsValueBRL / portfolio.meta.fxUsdBrl, portfolio: portfolio),
                    icon: "📈"
                )
            }
        }
        .padding(.horizontal, 16)
    }

    // MARK: - Bucket Section
    private func bucketSection(_ portfolio: Portfolio) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("BUCKET ALLOCATION")
                .font(.caption2)
                .foregroundColor(.gmcGrigioAcheso)
                .padding(.horizontal, 16)

            ForEach(["Survival", "Convex", "Illiquid Duration"], id: \.self) { bucket in
                let pct = portfolio.bucketPercentages[bucket] ?? 0
                BucketBar(name: bucket, percentage: pct)
                    .padding(.horizontal, 16)
            }
        }
    }

    // MARK: - Top Assets
    private func topAssetsSection(_ portfolio: Portfolio) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("TOP ASSETS")
                    .font(.caption2)
                    .foregroundColor(.gmcGrigioAcheso)
                Spacer()
                Button(action: {
                    newAsset = Asset.newFinancialAsset()
                    showingAssetEditor = true
                }) {
                    Image(systemName: "plus.circle.fill")
                        .foregroundColor(.gmcVerdeScandal)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 16)

            ForEach(portfolio.topAssets) { asset in
                AssetRow(asset: asset, portfolio: portfolio, currency: viewModel.currency)
                    .padding(.horizontal, 16)
            }
        }
    }

    // MARK: - Loading View
    private var loadingView: some View {
        VStack(spacing: 12) {
            ProgressView()
                .progressViewStyle(CircularProgressViewStyle(tint: .gmcVerdeScandal))
            Text("Loading portfolio...")
                .font(.caption)
                .foregroundColor(.gmcMetallicSilver)
        }
        .padding(40)
    }

    // MARK: - Error View
    private func errorView(_ error: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.largeTitle)
                .foregroundColor(.gmcVerdeScandal)
            Text(error)
                .font(.caption)
                .foregroundColor(.gmcMetallicSilver)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
            Button("Retry") {
                viewModel.loadPortfolio()
            }
            .buttonStyle(.borderedProminent)
            .tint(.gmcVerdeScandal)
        }
        .padding(20)
    }

    // MARK: - Footer
    private var footerSection: some View {
        HStack(spacing: 16) {
            Button(action: { viewModel.loadPortfolio() }) {
                Label("Refresh", systemImage: "arrow.clockwise")
            }

            Button(action: { viewModel.askForSuggestion() }) {
                Label("Ask AI", systemImage: "sparkles")
            }

            Spacer()

            SettingsLink {
                Label("Settings", systemImage: "gear")
            }

            Button(action: { NSApplication.shared.terminate(nil) }) {
                Image(systemName: "power")
            }
        }
        .buttonStyle(.plain)
        .font(.caption)
        .foregroundColor(.gmcMetallicSilver)
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(Color.gmcCarbonBlack)
    }

    // MARK: - Helpers
    private func formatValue(_ usdValue: Double, portfolio: Portfolio) -> String {
        let value: Double
        switch viewModel.currency {
        case .usd: value = usdValue
        case .brl: value = usdValue * portfolio.meta.fxUsdBrl
        case .eur: value = usdValue * (portfolio.meta.fxUsdBrl / (portfolio.meta.fxEurBrl ?? 6.6)) * (portfolio.meta.fxEurBrl ?? 6.6) / portfolio.meta.fxUsdBrl
        }

        if value >= 1_000_000 {
            return "\(viewModel.currency.symbol)\(String(format: "%.1fM", value / 1_000_000))"
        } else if value >= 1_000 {
            return "\(viewModel.currency.symbol)\(String(format: "%.0fK", value / 1_000))"
        }
        return "\(viewModel.currency.symbol)\(String(format: "%.0f", value))"
    }
}

// MARK: - Supporting Views

struct StatBox: View {
    let title: String
    let value: String
    let icon: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(icon)
                Text(title)
                    .font(.caption2)
                    .foregroundColor(.gmcGrigioAcheso)
            }
            Text(value)
                .font(.callout)
                .fontWeight(.semibold)
                .foregroundColor(.gmcMetallicSilver)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Color.gmcGrigioAcheso.opacity(0.2))
        .cornerRadius(8)
    }
}

struct AssetRow: View {
    let asset: Asset
    let portfolio: Portfolio
    let currency: Currency

    var body: some View {
        HStack {
            Text(asset.icon)
            Text(asset.displayName)
                .font(.caption)
                .foregroundColor(.gmcMetallicSilver)
                .lineLimit(1)
            Spacer()
            Text(formatAssetValue())
                .font(.caption)
                .foregroundColor(.gmcGrigioAcheso)
        }
        .padding(.vertical, 4)
    }

    private func formatAssetValue() -> String {
        guard let brl = asset.valueBRL else { return "-" }
        let usd = brl / portfolio.meta.fxUsdBrl

        let value: Double
        switch currency {
        case .usd: value = usd
        case .brl: value = brl
        case .eur: value = usd * 0.92
        }

        if value >= 1_000_000 {
            return "\(currency.symbol)\(String(format: "%.1fM", value / 1_000_000))"
        } else if value >= 1_000 {
            return "\(currency.symbol)\(String(format: "%.0fK", value / 1_000))"
        }
        return "\(currency.symbol)\(String(format: "%.0f", value))"
    }
}

struct BucketBar: View {
    let name: String
    let percentage: Double

    private var color: Color {
        switch name {
        case "Survival": return .green
        case "Convex": return .gmcVerdeScandal
        case "Illiquid Duration": return .gmcGrigioAcheso
        default: return .gray
        }
    }

    private var shortName: String {
        switch name {
        case "Illiquid Duration": return "Illiquid"
        default: return name
        }
    }

    var body: some View {
        VStack(spacing: 4) {
            HStack {
                Text(shortName)
                    .font(.caption)
                    .foregroundColor(.gmcMetallicSilver)
                Spacer()
                Text(String(format: "%.1f%%", percentage))
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(color)
            }

            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Rectangle()
                        .fill(Color.gmcGrigioAcheso.opacity(0.3))
                        .cornerRadius(3)

                    Rectangle()
                        .fill(color)
                        .frame(width: geo.size.width * min(percentage / 100, 1))
                        .cornerRadius(3)
                }
            }
            .frame(height: 6)
        }
    }
}

// MARK: - Asset Editor View
struct AssetEditorView: View {
    @State var asset: Asset
    let isNew: Bool
    let onSave: (Asset) -> Void
    @Environment(\.dismiss) var dismiss

    var body: some View {
        VStack(spacing: 20) {
            Text(isNew ? "Add Asset" : "Edit Asset")
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(.gmcMetallicSilver)

            Form {
                TextField("Asset ID", text: $asset.assetId)

                Picker("Asset Class", selection: $asset.assetClass) {
                    Text("Real Estate").tag("Real Estate")
                    Text("Cash").tag("Cash")
                    Text("ETF").tag("ETF")
                    Text("Cryptocurrency").tag("Cryptocurrency")
                    Text("Bond Fund").tag("Bond Fund")
                    Text("Commodity").tag("Commodity")
                }

                TextField("Instrument/Type", text: Binding(
                    get: { asset.instrument ?? asset.type ?? "" },
                    set: { asset.instrument = $0 }
                ))

                TextField("Value (BRL)", value: Binding(
                    get: { asset.marketValueEstBrl ?? 0 },
                    set: { asset.marketValueEstBrl = $0 }
                ), format: .number)

                Picker("Bucket", selection: Binding(
                    get: { asset.bucket ?? "Convex" },
                    set: { asset.bucket = $0 }
                )) {
                    Text("Survival").tag("Survival")
                    Text("Convex").tag("Convex")
                    Text("Illiquid Duration").tag("Illiquid Duration")
                }

                Picker("Liquidity", selection: Binding(
                    get: { asset.liquidity ?? "High" },
                    set: { asset.liquidity = $0 }
                )) {
                    Text("High").tag("High")
                    Text("Medium").tag("Medium")
                    Text("Low").tag("Low")
                    Text("Very Low").tag("Very Low")
                }
            }

            HStack {
                Button("Cancel") {
                    dismiss()
                }

                Spacer()

                Button("Save") {
                    onSave(asset)
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .tint(.gmcVerdeScandal)
            }
        }
        .padding()
        .frame(width: 400, height: 400)
        .background(Color.gmcCarbonBlack)
    }
}

#Preview {
    MenuBarView()
        .environmentObject(PortfolioViewModel())
}
