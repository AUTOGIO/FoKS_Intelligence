// PortfolioStore — JSON-backed portfolio persistence + FX
// ~/Library/Application Support/FoKS/portfolio.json

import Foundation
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "Portfolio")

public final class PortfolioStore {
    public init() {}
    private var url: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
            .first!.appendingPathComponent("FoKS")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("portfolio.json")
    }

    // Also check GMC legacy path
    private var legacyURL: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
            .first!.appendingPathComponent("GMC/portfolio.json")
    }

    public func load() async throws -> Portfolio {
        // Try FoKS path first, fall back to legacy GMC path
        let path: URL
        if FileManager.default.fileExists(atPath: url.path) {
            path = url
        } else if FileManager.default.fileExists(atPath: legacyURL.path) {
            path = legacyURL
            logger.info("Loading portfolio from legacy GMC path")
        } else {
            throw PortfolioError.notFound(url.path)
        }

        let data = try Data(contentsOf: path)
        var portfolio = try JSONDecoder().decode(Portfolio.self, from: data)

        // Refresh FX rates
        if let rates = await fetchFXRates() {
            portfolio.meta.fxUsdBrl = rates.usdBrl
            portfolio.meta.fxEurBrl = rates.eurBrl
        }

        logger.info("Portfolio loaded: \(portfolio.assets.count) assets")
        return portfolio
    }

    public func save(_ portfolio: Portfolio) throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(portfolio)
        try data.write(to: url)
        logger.info("Portfolio saved")
    }

    // MARK: - FX Rates (free API, no key)
    private func fetchFXRates() async -> (usdBrl: Double, eurBrl: Double)? {
        guard let url = URL(string: "https://api.exchangerate-api.com/v4/latest/USD") else { return nil }
        var req = URLRequest(url: url)
        req.timeoutInterval = 10
        do {
            let (data, resp) = try await URLSession.shared.data(for: req)
            guard (resp as? HTTPURLResponse)?.statusCode == 200 else { return nil }
            let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
            let rates = json?["rates"] as? [String: Double]
            let usdBrl = rates?["BRL"] ?? 6.10
            let eurUsd = rates?["EUR"] ?? 0.92
            logger.info("Live FX: USD/BRL=\(String(format: "%.2f", usdBrl))")
            return (usdBrl, usdBrl / eurUsd)
        } catch {
            logger.warning("FX fetch failed, using fallback rates")
            return (6.10, 6.60)
        }
    }
}

public enum PortfolioError: LocalizedError {
    case notFound(String)
    public var errorDescription: String? {
        switch self {
        case .notFound(let p): "Portfolio not found at: \(p)"
        }
    }
}
