// VESTA - FX Service
// Fetches real-time exchange rates from free API

import Foundation

class FXService {
    static let shared = FXService()

    // Free API (no key required)
    private let baseURL = "https://api.exchangerate-api.com/v4/latest"

    private init() {}

    struct FXRates: Codable {
        let rates: [String: Double]
        let base: String
        let date: String
    }

    // MARK: - Get Current Rates
    func getCurrentRates(base: String = "USD") async -> (usdBrl: Double, eurBrl: Double)? {
        // Default fallback rates
        let fallbackUsdBrl = 6.10
        let fallbackEurBrl = 6.60

        guard let url = URL(string: "\(baseURL)/\(base)") else {
            return (fallbackUsdBrl, fallbackEurBrl)
        }

        var request = URLRequest(url: url)
        request.timeoutInterval = 10

        do {
            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                print("⚠️ FX API request failed, using fallback rates")
                return (fallbackUsdBrl, fallbackEurBrl)
            }

            let decoder = JSONDecoder()
            let rates = try decoder.decode(FXRates.self, from: data)

            let usdBrl = rates.rates["BRL"] ?? fallbackUsdBrl
            let eurUsd = rates.rates["EUR"] ?? 0.92
            let eurBrl = usdBrl / eurUsd

            print("📈 Live FX: USD/BRL = \(String(format: "%.2f", usdBrl)), EUR/BRL = \(String(format: "%.2f", eurBrl))")
            return (usdBrl, eurBrl)

        } catch {
            print("⚠️ FX error: \(error.localizedDescription), using fallback rates")
            return (fallbackUsdBrl, fallbackEurBrl)
        }
    }

    // MARK: - Update Portfolio with Live Rates
    func updatePortfolioRates(_ portfolio: inout Portfolio) async {
        if let rates = await getCurrentRates() {
            portfolio.meta.fxUsdBrl = rates.usdBrl
            portfolio.meta.fxEurBrl = rates.eurBrl
            print("✅ Portfolio FX updated to live rates")
        }
    }
}
