// VESTA - Settings View
// GMC Brand Theme with Asset Management

import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var viewModel: PortfolioViewModel
    @State private var foksURL = "http://localhost:3000"
    @State private var isFoKSConnected = false
    @State private var selectedAsset: Asset?
    @State private var showingAssetEditor = false

    var body: some View {
        TabView {
            portfolioTab
                .tabItem {
                    Label("Portfolio", systemImage: "chart.pie.fill")
                }

            assetsTab
                .tabItem {
                    Label("Assets", systemImage: "dollarsign.circle.fill")
                }

            integrationTab
                .tabItem {
                    Label("Integration", systemImage: "link")
                }

            aboutTab
                .tabItem {
                    Label("About", systemImage: "info.circle")
                }
        }
        .frame(width: 550, height: 450)
        .background(Color.gmcCarbonBlack)
        .onAppear {
            checkFoKSConnection()
        }
    }

    // MARK: - Portfolio Tab
    private var portfolioTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Portfolio Summary")
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(.gmcMetallicSilver)

            if let portfolio = viewModel.portfolio {
                GroupBox {
                    VStack(alignment: .leading, spacing: 12) {
                        LabeledContent("Name", value: portfolio.meta.portfolioName)
                        LabeledContent("Version", value: portfolio.meta.version)
                        LabeledContent("As Of", value: portfolio.meta.asOf)
                        LabeledContent("Total Assets", value: "\(portfolio.assets.count)")

                        Divider()

                        LabeledContent("USD/BRL", value: String(format: "%.2f", portfolio.meta.fxUsdBrl))
                        if let eurBrl = portfolio.meta.fxEurBrl {
                            LabeledContent("EUR/BRL", value: String(format: "%.2f", eurBrl))
                        }

                        Divider()

                        LabeledContent("Total (BRL)") {
                            Text(formatCurrency(portfolio.totalValueBRL, symbol: "R$"))
                                .foregroundColor(.gmcVerdeScandal)
                                .fontWeight(.bold)
                        }
                        LabeledContent("Total (USD)") {
                            Text(formatCurrency(portfolio.totalValueUSD, symbol: "$"))
                                .foregroundColor(.gmcVerdeScandal)
                                .fontWeight(.bold)
                        }
                    }
                    .padding()
                }

                HStack {
                    Button("Reload Data") {
                        viewModel.loadPortfolio()
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.gmcVerdeScandal)

                    Button("Open JSON File") {
                        let path = DataLoader.shared.getPortfolioPath()
                        NSWorkspace.shared.selectFile(path, inFileViewerRootedAtPath: "")
                    }
                }
            } else {
                Text("No portfolio loaded")
                    .foregroundColor(.secondary)

                Button("Load Portfolio") {
                    viewModel.loadPortfolio()
                }
                .buttonStyle(.borderedProminent)
                .tint(.gmcVerdeScandal)
            }

            Spacer()
        }
        .padding()
    }

    // MARK: - Assets Tab
    private var assetsTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Asset Management")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.gmcMetallicSilver)

                Spacer()

                Menu {
                    Button("Add Real Estate") {
                        selectedAsset = Asset.newRealEstate()
                        showingAssetEditor = true
                    }
                    Button("Add Financial Asset") {
                        selectedAsset = Asset.newFinancialAsset()
                        showingAssetEditor = true
                    }
                } label: {
                    Label("Add Asset", systemImage: "plus.circle.fill")
                }
                .buttonStyle(.borderedProminent)
                .tint(.gmcVerdeScandal)
            }

            if let portfolio = viewModel.portfolio {
                List {
                    ForEach(portfolio.assets) { asset in
                        HStack {
                            Text(asset.icon)
                            VStack(alignment: .leading) {
                                Text(asset.displayName)
                                    .font(.headline)
                                Text("\(asset.assetClass) • \(asset.bucket ?? "N/A")")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            Spacer()
                            Text(formatCurrency(asset.valueBRL ?? 0, symbol: "R$"))
                                .foregroundColor(.gmcVerdeScandal)
                        }
                        .contextMenu {
                            Button("Edit") {
                                selectedAsset = asset
                                showingAssetEditor = true
                            }
                            Button("Delete", role: .destructive) {
                                viewModel.deleteAsset(asset.assetId)
                            }
                        }
                    }
                }
                .listStyle(.inset)
            }

            Spacer()
        }
        .padding()
        .sheet(isPresented: $showingAssetEditor) {
            if let asset = selectedAsset {
                AssetEditorView(
                    asset: asset,
                    isNew: viewModel.portfolio?.assets.contains { $0.assetId == asset.assetId } != true
                ) { savedAsset in
                    if viewModel.portfolio?.assets.contains(where: { $0.assetId == savedAsset.assetId }) == true {
                        viewModel.updateAsset(savedAsset)
                    } else {
                        viewModel.addAsset(savedAsset)
                    }
                    showingAssetEditor = false
                }
            }
        }
    }

    // MARK: - Integration Tab
    private var integrationTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("FoKS Integration")
                .font(.title2)
                .fontWeight(.bold)
                .foregroundColor(.gmcMetallicSilver)

            GroupBox("FoKS Intelligence API") {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Circle()
                            .fill(isFoKSConnected ? Color.gmcVerdeScandal : Color.red)
                            .frame(width: 10, height: 10)
                        Text(isFoKSConnected ? "Connected" : "Disconnected")
                            .foregroundColor(isFoKSConnected ? .gmcVerdeScandal : .red)
                    }

                    TextField("FoKS URL", text: $foksURL)
                        .textFieldStyle(.roundedBorder)

                    Button("Test Connection") {
                        checkFoKSConnection()
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.gmcVerdeScandal)
                }
                .padding()
            }

            GroupBox("Data Source") {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Portfolio Location:")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text(DataLoader.shared.getPortfolioPath())
                        .font(.caption)
                        .foregroundColor(.gmcMetallicSilver)
                        .textSelection(.enabled)
                }
                .padding()
            }

            Spacer()
        }
        .padding()
    }

    // MARK: - About Tab
    private var aboutTab: some View {
        VStack(spacing: 20) {
            // Logo placeholder
            Image(systemName: "chart.pie.fill")
                .font(.system(size: 64))
                .foregroundColor(.gmcVerdeScandal)

            Text("VESTA")
                .font(.largeTitle)
                .fontWeight(.bold)
                .foregroundColor(.gmcMetallicSilver)

            Text("Visualization & Execution Status\nTerminal for Assets")
                .multilineTextAlignment(.center)
                .foregroundColor(.gmcGrigioAcheso)

            Divider()
                .frame(width: 200)

            VStack(spacing: 4) {
                Text("Version 1.0.0")
                    .font(.caption)
                    .foregroundColor(.gmcMetallicSilver)
                Text("Built for Apple M3")
                    .font(.caption)
                    .foregroundColor(.gmcGrigioAcheso)
            }

            // Brand Colors
            HStack(spacing: 10) {
                Circle().fill(Color.gmcGrigioAcheso).frame(width: 20, height: 20)
                Circle().fill(Color.gmcVerdeScandal).frame(width: 20, height: 20)
                Circle().fill(Color.gmcCarbonBlack).frame(width: 20, height: 20)
                    .overlay(Circle().stroke(Color.gmcGrigioAcheso, lineWidth: 1))
                Circle().fill(Color.gmcMetallicSilver).frame(width: 20, height: 20)
            }

            Spacer()

            Text("© 2026 Giovannini Mare Capital LLC")
                .font(.caption2)
                .foregroundColor(.gmcGrigioAcheso)
        }
        .padding()
    }

    // MARK: - Helpers
    private func checkFoKSConnection() {
        Task {
            isFoKSConnected = await FoKSClient.shared.isAvailable()
        }
    }

    private func formatCurrency(_ value: Double, symbol: String) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencySymbol = symbol
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "\(symbol)0"
    }
}

#Preview {
    SettingsView()
        .environmentObject(PortfolioViewModel())
}
