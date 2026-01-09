// VESTA - Data Loader Service
// Loads and saves portfolio from ~/Library/Application Support/GMC/portfolio.json

import Foundation

class DataLoader {
    static let shared = DataLoader()

    private let fileManager = FileManager.default

    private var portfolioURL: URL {
        let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        return appSupport.appendingPathComponent("GMC/portfolio.json")
    }

    private init() {
        // Ensure directory exists
        let dir = portfolioURL.deletingLastPathComponent()
        if !fileManager.fileExists(atPath: dir.path) {
            try? fileManager.createDirectory(at: dir, withIntermediateDirectories: true)
        }
    }

    func loadPortfolio() async throws -> Portfolio {
        guard fileManager.fileExists(atPath: portfolioURL.path) else {
            throw DataLoaderError.fileNotFound(portfolioURL.path)
        }

        let data = try Data(contentsOf: portfolioURL)
        let decoder = JSONDecoder()
        let portfolio = try decoder.decode(Portfolio.self, from: data)

        print("📊 Loaded: \(portfolio.assets.count) assets from \(portfolioURL.path)")
        return portfolio
    }

    func savePortfolio(_ portfolio: Portfolio) async throws {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(portfolio)
        try data.write(to: portfolioURL)
        print("💾 Saved portfolio to \(portfolioURL.path)")
    }

    func portfolioExists() -> Bool {
        fileManager.fileExists(atPath: portfolioURL.path)
    }

    func getPortfolioPath() -> String {
        portfolioURL.path
    }
}

enum DataLoaderError: LocalizedError {
    case fileNotFound(String)

    var errorDescription: String? {
        switch self {
        case .fileNotFound(let path):
            return "Portfolio not found at:\n\(path)\n\nCreate the file or copy from GMC_System."
        }
    }
}
