// Portfolio — VESTA asset management models

import Foundation

public struct Portfolio: Codable {
    public var meta: PortfolioMeta
    public var assets: [Asset]

    public var totalValueBRL: Double { assets.compactMap(\.valueBRL).reduce(0, +) }
    public var totalValueUSD: Double { totalValueBRL / meta.fxUsdBrl }
    public var realEstateValueBRL: Double {
        assets.filter { $0.assetClass == "Real Estate" }.compactMap(\.valueBRL).reduce(0, +)
    }
    public var financialAssetsValueBRL: Double {
        assets.filter { $0.assetClass != "Real Estate" }.compactMap(\.valueBRL).reduce(0, +)
    }
    public var bucketPercentages: [String: Double] {
        let total = totalValueBRL
        guard total > 0 else { return ["Survival": 0, "Convex": 0, "Illiquid Duration": 0] }
        var buckets: [String: Double] = [:]
        for a in assets { buckets[a.bucket ?? "Unknown", default: 0] += a.valueBRL ?? 0 }
        return buckets.mapValues { ($0 / total) * 100 }
    }
    public var topAssets: [Asset] {
        Array(assets.sorted { ($0.valueBRL ?? 0) > ($1.valueBRL ?? 0) }.prefix(5))
    }
}

public struct PortfolioMeta: Codable {
    public var portfolioName: String
    public var baseCurrency: String
    public var fxUsdBrl: Double
    public var fxEurBrl: Double?
    public var version: String
    public var asOf: String

    enum CodingKeys: String, CodingKey {
        case portfolioName = "portfolio_name"
        case baseCurrency = "base_currency"
        case fxUsdBrl = "fx_usd_brl"
        case fxEurBrl = "fx_eur_brl"
        case version, asOf = "as_of"
    }
}

public struct Asset: Codable, Identifiable {
    public var assetId: String
    public var assetClass: String
    public var type: String?
    public var instrument: String?
    public var description: String?
    public var country, state, city, address: String?
    public var areaM2: Double?
    public var currency: String?
    public var valueUsd: Double?
    public var marketValueEstBrl: Double?
    public var liquidity: String?
    public var bucket: String?

    public var id: String { assetId }
    public var valueBRL: Double? { marketValueEstBrl }

    public var displayName: String {
        instrument ?? (city.map { "\(type ?? "Asset") - \($0)" }) ?? type ?? assetId
    }
    public var icon: String {
        switch assetClass {
        case "Real Estate": "🏠"
        case "Cash": "💵"
        case "ETF": "📈"
        case "Cryptocurrency": "₿"
        case "Bond Fund": "📊"
        case "Commodity": "🥇"
        default: "💰"
        }
    }

    enum CodingKeys: String, CodingKey {
        case assetId = "asset_id"; case assetClass = "asset_class"
        case type, instrument, description, country, state, city, address
        case areaM2 = "area_m2"; case currency; case valueUsd = "value_usd"
        case marketValueEstBrl = "market_value_est_brl"; case liquidity, bucket
    }

    public static func newRealEstate() -> Asset {
        Asset(assetId: "RE_\(Int.random(in: 100...999))", assetClass: "Real Estate",
              type: "Property", country: "Brazil", marketValueEstBrl: 0,
              liquidity: "Very Low", bucket: "Illiquid Duration")
    }
    public static func newFinancial() -> Asset {
        Asset(assetId: "FA_\(Int.random(in: 100...999))", assetClass: "ETF",
              instrument: "NEW", currency: "USD", marketValueEstBrl: 0,
              liquidity: "High", bucket: "Convex")
    }
}

public enum Currency: String, CaseIterable {
    case usd = "USD", brl = "BRL", eur = "EUR"
    public var symbol: String {
        switch self { case .usd: "$"; case .brl: "R$"; case .eur: "€" }
    }
}
