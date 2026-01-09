// VESTA - Portfolio Data Models

import Foundation

struct Portfolio: Codable {
    var meta: PortfolioMeta
    var assets: [Asset]

    var totalValueBRL: Double {
        assets.compactMap { $0.valueBRL }.reduce(0, +)
    }

    var totalValueUSD: Double {
        totalValueBRL / meta.fxUsdBrl
    }

    var realEstateValueBRL: Double {
        assets.filter { $0.assetClass == "Real Estate" }
            .compactMap { $0.valueBRL }
            .reduce(0, +)
    }

    var financialAssetsValueBRL: Double {
        assets.filter { $0.assetClass != "Real Estate" }
            .compactMap { $0.valueBRL }
            .reduce(0, +)
    }

    var bucketPercentages: [String: Double] {
        var buckets: [String: Double] = [
            "Survival": 0,
            "Convex": 0,
            "Illiquid Duration": 0
        ]
        let total = totalValueBRL
        guard total > 0 else { return buckets }

        for asset in assets {
            let bucket = asset.bucket ?? "Unknown"
            let value = asset.valueBRL ?? 0
            buckets[bucket, default: 0] += value
        }

        return buckets.mapValues { ($0 / total) * 100 }
    }

    var topAssets: [Asset] {
        assets
            .sorted { ($0.valueBRL ?? 0) > ($1.valueBRL ?? 0) }
            .prefix(5)
            .map { $0 }
    }
}

struct PortfolioMeta: Codable {
    var portfolioName: String
    var baseCurrency: String
    var fxUsdBrl: Double
    var fxEurBrl: Double?
    var version: String
    var asOf: String

    enum CodingKeys: String, CodingKey {
        case portfolioName = "portfolio_name"
        case baseCurrency = "base_currency"
        case fxUsdBrl = "fx_usd_brl"
        case fxEurBrl = "fx_eur_brl"
        case version
        case asOf = "as_of"
    }
}

struct Asset: Codable, Identifiable {
    var assetId: String
    var assetClass: String
    var type: String?
    var instrument: String?
    var description: String?
    var country: String?
    var state: String?
    var city: String?
    var address: String?
    var areaM2: Double?
    var currency: String?
    var valueUsd: Double?
    var marketValueEstBrl: Double?
    var liquidity: String?
    var bucket: String?

    var id: String { assetId }

    var valueBRL: Double? {
        marketValueEstBrl
    }

    var displayName: String {
        if let instrument = instrument {
            return instrument
        }
        if let city = city, let type = type {
            return "\(type) - \(city)"
        }
        return type ?? assetId
    }

    var icon: String {
        switch assetClass {
        case "Real Estate": return "🏠"
        case "Cash": return "💵"
        case "ETF": return "📈"
        case "Cryptocurrency": return "₿"
        case "Bond Fund": return "📊"
        case "Commodity": return "🥇"
        default: return "💰"
        }
    }

    enum CodingKeys: String, CodingKey {
        case assetId = "asset_id"
        case assetClass = "asset_class"
        case type
        case instrument
        case description
        case country
        case state
        case city
        case address
        case areaM2 = "area_m2"
        case currency
        case valueUsd = "value_usd"
        case marketValueEstBrl = "market_value_est_brl"
        case liquidity
        case bucket
    }

    // MARK: - Factory Methods
    static func newRealEstate() -> Asset {
        Asset(
            assetId: "RE_\(Int.random(in: 100...999))",
            assetClass: "Real Estate",
            type: "Property",
            country: "Brazil",
            marketValueEstBrl: 0,
            liquidity: "Very Low",
            bucket: "Illiquid Duration"
        )
    }

    static func newFinancialAsset() -> Asset {
        Asset(
            assetId: "FA_\(Int.random(in: 100...999))",
            assetClass: "ETF",
            instrument: "NEW",
            currency: "USD",
            marketValueEstBrl: 0,
            liquidity: "High",
            bucket: "Convex"
        )
    }
}
