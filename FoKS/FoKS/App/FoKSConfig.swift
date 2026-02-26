// FoKSConfig — Centralized configuration
// Replaces Python's pydantic Settings + .env files
// Uses UserDefaults + Keychain for persistence

import Foundation
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "Config")

public struct FoKSConfig {
    // Hardware identity
    public static let hardwareModel = "Mac15,5"
    public static let chip = "Apple M3"
    public static let coreCount = 8 // 4P + 4E
    public static let memoryGB = 16

    // OpenAI API
    public var openAIBaseURL: String
    public var openAIAPIKey: String
    public var openAIChatModel: String
    public var openAIReasoningModel: String
    public var openAIRoutingModel: String
    public var openAIVisionModel: String
    public var openAITimeout: TimeInterval

    // FBP Backend (kept as Python sidecar)
    public var fbpBaseURL: String
    public var fbpSocketPath: String
    public var fbpTransport: FBPTransport

    // HTTP Server (for n8n / Shortcuts compatibility)
    public var httpPort: UInt16

    // Paths
    public var portfolioPath: URL
    public var profilesPath: URL
    public var screenTimeDBPath: URL
    public var logsPath: URL

    // Networking
    public var defaultTimeout: TimeInterval
    public var allowedOrigins: [String]

    // Identity Guard
    public var localIdentityGuard: Bool
    public var localSystemPrompt: String

    public enum FBPTransport: String {
        case socket, tcp
    }

    public static func load() -> FoKSConfig {
        let appSupport = FileManager.default.urls(
            for: .applicationSupportDirectory,
            in: .userDomainMask
        ).first!.appendingPathComponent("FoKS")

        // Ensure dirs exist
        try? FileManager.default.createDirectory(at: appSupport, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(
            at: appSupport.appendingPathComponent("logs"),
            withIntermediateDirectories: true
        )

        let defaults = UserDefaults.standard

        let keychain = KeychainHelper.shared
        let apiKeyEnv = ProcessInfo.processInfo.environment["OPENAI_API_KEY"]
        let apiKeyKeychain = keychain.read(for: "openAIAPIKey")
        let apiKeyUserDefaults = defaults.string(forKey: "openAIAPIKey")

        let apiKey: String
        if let env = apiKeyEnv {
            apiKey = env
        } else if let keychain = apiKeyKeychain {
            apiKey = keychain
        } else if let legacy = apiKeyUserDefaults {
            apiKey = legacy
            // Migrate to keychain
            try? keychain.save(legacy, for: "openAIAPIKey")
            defaults.removeObject(forKey: "openAIAPIKey")
            logger.info("Migrated API key to Keychain")
        } else {
            apiKey = ""
        }

        let config = FoKSConfig(
            openAIBaseURL: defaults.string(forKey: "openAIBaseURL")
                ?? "https://api.openai.com/v1",
            openAIAPIKey: apiKey,
            openAIChatModel: defaults.string(forKey: "openAIChatModel")
                ?? "gpt-4o-mini",
            openAIReasoningModel: defaults.string(forKey: "openAIReasoningModel")
                ?? "gpt-4o",
            openAIRoutingModel: defaults.string(forKey: "openAIRoutingModel")
                ?? "gpt-4o-mini",
            openAIVisionModel: defaults.string(forKey: "openAIVisionModel")
                ?? "gpt-4o",
            openAITimeout: defaults.double(forKey: "openAITimeout") > 0
                ? defaults.double(forKey: "openAITimeout") : 120,

            fbpBaseURL: defaults.string(forKey: "fbpBaseURL")
                ?? "http://localhost:8000",
            fbpSocketPath: defaults.string(forKey: "fbpSocketPath")
                ?? "/tmp/fbp.sock",
            fbpTransport: FBPTransport(rawValue: defaults.string(forKey: "fbpTransport") ?? "socket")
                ?? .socket,

            httpPort: UInt16(defaults.integer(forKey: "httpPort") > 0
                ? defaults.integer(forKey: "httpPort") : 3000),

            portfolioPath: appSupport.appendingPathComponent("portfolio.json"),
            profilesPath: appSupport.appendingPathComponent("profiles.json"),
            screenTimeDBPath: appSupport.appendingPathComponent("screentime.db"),
            logsPath: appSupport.appendingPathComponent("logs"),

            defaultTimeout: 30,
            allowedOrigins: [
                "http://localhost",
                "https://foks.giovannini.us",
                "https://fbp.giovannini.us",
            ],

            localIdentityGuard: true,
            localSystemPrompt: """
            You are a helpful AI assistant. Provide concise, actionable advice. \
            Respect user privacy. Be direct and avoid unnecessary elaboration.
            """
        )

        logger.info("Config loaded — \(Self.chip) \(Self.memoryGB)GB — OpenAI: \(config.openAIBaseURL)")
        return config
    }

    public func save() {
        let defaults = UserDefaults.standard
        defaults.set(openAIBaseURL, forKey: "openAIBaseURL")

        if !openAIAPIKey.isEmpty {
            try? KeychainHelper.shared.save(openAIAPIKey, for: "openAIAPIKey")
        }

        defaults.set(openAIChatModel, forKey: "openAIChatModel")
        defaults.set(openAIReasoningModel, forKey: "openAIReasoningModel")
        defaults.set(openAIRoutingModel, forKey: "openAIRoutingModel")
        defaults.set(openAIVisionModel, forKey: "openAIVisionModel")
        defaults.set(openAITimeout, forKey: "openAITimeout")
        defaults.set(fbpBaseURL, forKey: "fbpBaseURL")
        defaults.set(fbpSocketPath, forKey: "fbpSocketPath")
        defaults.set(fbpTransport.rawValue, forKey: "fbpTransport")
        defaults.set(Int(httpPort), forKey: "httpPort")
        logger.info("Config saved")
    }
}
