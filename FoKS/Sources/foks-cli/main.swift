import Foundation
import FoKS_Service_Lib

let config = FoKSConfig.load()
let arguments = CommandLine.arguments

func printUsage() {
    print("""
    FoKS Intelligence CLI
    Usage: foks-cli <command> [options]

    Commands:
      status    Show system and service status
      portfolio Show portfolio summary
      health    Check OpenAI and service health
    """)
}

guard arguments.count > 1 else {
    printUsage()
    exit(0)
}

let command = arguments[1]

switch command {
case "status":
    print("FoKS System Status")
    print("------------------")
    print("Chip: \(FoKSConfig.chip)")
    print("Memory: \(FoKSConfig.memoryGB)GB")
    print("OpenAI Base: \(config.openAIBaseURL)")

case "health":
    print("Checking Health...")
    Task {
        let openAI = OpenAIService(config: config)
        let available = await openAI.isAvailable()
        print("OpenAI Service: \(available ? "ONLINE" : "OFFLINE")")
        exit(0)
    }
    RunLoop.main.run(until: Date(timeIntervalSinceNow: 10))

case "portfolio":
    let store = PortfolioStore()
    Task {
        do {
            let portfolio = try await store.load()
            print("Portfolio: \(portfolio.meta.asOf)")
            print("Assets: \(portfolio.assets.count)")
            exit(0)
        } catch {
            print("Error loading portfolio: \(error.localizedDescription)")
            exit(1)
        }
    }
    RunLoop.main.run(until: Date(timeIntervalSinceNow: 10))

default:
    print("Unknown command: \(command)")
    printUsage()
    exit(1)
}
