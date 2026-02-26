// swift-tools-version: 5.9
// FoKS Intelligence — SwiftUI macOS menubar app
// AETHER (workspace) + VESTA (portfolio) + FileHQ (files + notes)
// Build: swift build | Run: swift run foks-app

import PackageDescription

let package = Package(
    name: "FoKS",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "foks-app", targets: ["FoKS"]),
        .executable(name: "foks-cli", targets: ["foks-cli"])
    ],
    targets: [
        .executableTarget(
            name: "FoKS",
            dependencies: ["FoKS_Service_Lib"],
            path: "FoKS",
            exclude: [
                "Resources",
                "Intents",
                "Models",
                "Services",
                "App/FoKSConfig.swift"
            ],
            swiftSettings: [
                .define("FOKS_SWIFT_APP"),
            ]
        ),
        .executableTarget(
            name: "foks-cli",
            dependencies: ["FoKS_Service_Lib"],
            path: "Sources/foks-cli"
        ),
        .target(
            name: "FoKS_Service_Lib",
            path: "FoKS",
            exclude: [
                "App/FoKSApp.swift",
                "App/FoKSHub.swift",
                "Views",
                "Resources",
                "Intents"
            ],
            linkerSettings: [
                .linkedFramework("AppKit"),
                .linkedFramework("Network"),
                .linkedFramework("UniformTypeIdentifiers"),
                .linkedFramework("Security"),
                .linkedFramework("NaturalLanguage"),
            ]
        ),
        .testTarget(
            name: "FoKSTests",
            dependencies: ["FoKS_Service_Lib"]
        )
    ]
)
