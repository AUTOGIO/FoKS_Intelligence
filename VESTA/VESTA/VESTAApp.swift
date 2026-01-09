// VESTA - Visualization & Execution Status Terminal for Assets
// GMC Brand Colors + Full Asset Management
// Native SwiftUI Menubar Widget

import SwiftUI
import AppKit

// MARK: - GMC Brand Colors
extension Color {
    // Primary: Grigio Acheso (Matte Grey)
    static let gmcGrigioAcheso = Color(red: 0.29, green: 0.31, blue: 0.32) // #4A4E52

    // Secondary: Verde Scandal (Neon Green)
    static let gmcVerdeScandal = Color(red: 0.82, green: 1.0, blue: 0.0) // #D0FF00

    // Tertiary: Carbon Black
    static let gmcCarbonBlack = Color(red: 0.04, green: 0.04, blue: 0.04) // #0A0A0A

    // Accent: Metallic Silver
    static let gmcMetallicSilver = Color(red: 0.75, green: 0.75, blue: 0.75) // #C0C0C0
}

@main
struct VESTAApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @StateObject private var viewModel = PortfolioViewModel()

    var body: some Scene {
        MenuBarExtra {
            MenuBarView()
                .environmentObject(viewModel)
        } label: {
            HStack(spacing: 4) {
                Image(systemName: "chart.pie.fill")
                if let total = viewModel.portfolioTotalUSD {
                    Text(formatCompact(total))
                        .font(.caption)
                }
            }
        }
        .menuBarExtraStyle(.window)

        Settings {
            SettingsView()
                .environmentObject(viewModel)
        }
    }

    private func formatCompact(_ value: Double) -> String {
        if value >= 1_000_000 {
            return String(format: "$%.1fM", value / 1_000_000)
        } else if value >= 1_000 {
            return String(format: "$%.0fK", value / 1_000)
        }
        return String(format: "$%.0f", value)
    }
}

// MARK: - App Delegate
class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        print("📊 VESTA launched - Giovannini Mare Capital")
    }
}

// MARK: - Portfolio ViewModel
class PortfolioViewModel: ObservableObject {
    @Published var portfolio: Portfolio?
    @Published var isLoading = false
    @Published var error: String?
    @Published var suggestion: String?
    @Published var currency: Currency = .usd
    @Published var showingAddAsset = false
    @Published var editingAsset: Asset?

    var portfolioTotalUSD: Double? {
        portfolio?.totalValueUSD
    }

    var portfolioTotalBRL: Double? {
        portfolio?.totalValueBRL
    }

    init() {
        loadPortfolio()
    }

    func loadPortfolio() {
        isLoading = true
        error = nil

        Task {
            do {
                let loaded = try await DataLoader.shared.loadPortfolio()
                await MainActor.run {
                    self.portfolio = loaded
                    self.isLoading = false
                    print("📊 Portfolio loaded: \(loaded.assets.count) assets, total BRL: \(loaded.totalValueBRL)")
                }
            } catch {
                await MainActor.run {
                    self.error = error.localizedDescription
                    self.isLoading = false
                    print("❌ Portfolio error: \(error.localizedDescription)")
                }
            }
        }
    }

    func askForSuggestion() {
        Task {
            let result = await FoKSClient.shared.getProfileSuggestion(
                buckets: portfolio?.bucketPercentages ?? [:]
            )
            await MainActor.run {
                self.suggestion = result ?? "FoKS not available. Start http://localhost:3000"
            }
        }
    }

    func toggleCurrency() {
        switch currency {
        case .usd: currency = .brl
        case .brl: currency = .eur
        case .eur: currency = .usd
        }
    }

    // MARK: - Asset Management
    func addAsset(_ asset: Asset) {
        guard var portfolio = portfolio else { return }
        portfolio.assets.append(asset)
        self.portfolio = portfolio
        savePortfolio()
    }

    func updateAsset(_ asset: Asset) {
        guard var portfolio = portfolio else { return }
        if let index = portfolio.assets.firstIndex(where: { $0.assetId == asset.assetId }) {
            portfolio.assets[index] = asset
            self.portfolio = portfolio
            savePortfolio()
        }
    }

    func deleteAsset(_ assetId: String) {
        guard var portfolio = portfolio else { return }
        portfolio.assets.removeAll { $0.assetId == assetId }
        self.portfolio = portfolio
        savePortfolio()
    }

    func savePortfolio() {
        guard let portfolio = portfolio else { return }
        Task {
            do {
                try await DataLoader.shared.savePortfolio(portfolio)
                print("✅ Portfolio saved")
            } catch {
                print("❌ Save error: \(error)")
            }
        }
    }
}

enum Currency: String, CaseIterable {
    case usd = "USD"
    case brl = "BRL"
    case eur = "EUR"

    var symbol: String {
        switch self {
        case .usd: return "$"
        case .brl: return "R$"
        case .eur: return "€"
        }
    }
}
