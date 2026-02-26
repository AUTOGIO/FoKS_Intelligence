// FoKSHub — Central state object connecting all services
// Single source of truth for AETHER, VESTA, FileHQ, and system state

import SwiftUI
import os.log
import Combine
import FoKS_Service_Lib

private let logger = Logger(subsystem: "us.giovannini.foks", category: "Hub")

@MainActor
final class FoKSHub: ObservableObject {
    static let shared = FoKSHub()

    // MARK: - Services
    let openAI: OpenAIService
    let windowManager: WindowManager
    let screenTime: ScreenTimeService
    let processMonitor: ProcessMonitor
    let httpServer: EmbeddedHTTPServer
    let fbpClient: FBPClient
    let portfolioStore: PortfolioStore
    let fileService: FileOrganizationService
    let notesBridge: NotesAppleScriptBridge
    let nfaBridge: NFAFileOrganizationBridge

    // MARK: - AETHER State
    @Published var profiles: [WorkspaceProfile] = []
    @Published var activeProfile: WorkspaceProfile?
    @Published var aiSuggestion: String?
    @Published var isCapturingLayout = false

    // MARK: - VESTA State
    @Published var portfolio: Portfolio?
    @Published var currency: Currency = .usd
    @Published var portfolioSuggestion: String?

    // MARK: - FileHQ State
    @Published var currentDirectory: URL?
    @Published var fileItems: [FileItem] = []
    @Published var selectedFileItem: FileItem?
    @Published var fileSearchText: String = ""
    @Published var isOrganizing = false
    @Published var notes: [NoteItem] = []
    @Published var noteEvaluations: [NoteEvaluation] = []
    @Published var isProcessingNotes = false
    @Published var notesProgress: Double = 0
    @Published var notesStatus: String = "Ready"
    @Published var useOnDeviceAI = true

    // MARK: - System State
    @Published var openAIOnline = false
    @Published var fbpOnline = false
    @Published var systemStats: SystemStats?

    var portfolioTotalFormatted: String? {
        guard let p = portfolio else { return nil }
        let usd = p.totalValueUSD
        if usd >= 1_000_000 { return String(format: "$%.1fM", usd / 1_000_000) }
        if usd >= 1_000 { return String(format: "$%.0fK", usd / 1_000) }
        return String(format: "$%.0f", usd)
    }

    /// AI evaluation provider — routes through FoKS OpenAI or on-device NLP
    var aiEvaluationProvider: AIEvaluationProvider {
        useOnDeviceAI
            ? OnDeviceAIEvaluationService()
            : FoKSAIEvaluationAdapter(openAI: openAI)
    }

    private var searchDebounceTask: Task<Void, Never>?

    private init() {
        let config = FoKSConfig.load()

        self.openAI = OpenAIService(config: config)
        self.windowManager = WindowManager()
        self.screenTime = ScreenTimeService()
        self.processMonitor = ProcessMonitor()
        self.fbpClient = FBPClient(config: config)
        self.portfolioStore = PortfolioStore()
        self.httpServer = EmbeddedHTTPServer(port: config.httpPort)
        self.fileService = FileOrganizationService()
        self.notesBridge = NotesAppleScriptBridge()
        self.nfaBridge = NFAFileOrganizationBridge()

        loadProfiles()
        loadPortfolio()

        // Register FileHQ HTTP routes
        Task { await registerHTTPRoutes() }

        // Health check timer
        Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.refreshHealth()
            }
        }

        Task { await refreshHealth() }
    }

    // MARK: - AETHER Actions

    func loadProfiles() {
        profiles = ProfileStore.shared.loadAll()
        activeProfile = profiles.first(where: \.isActive)
    }

    func switchProfile(_ profile: WorkspaceProfile) {
        ProfileStore.shared.activate(profile)
        loadProfiles()
        Task {
            await windowManager.restoreWindows(from: profile.windowStates)

            // FileHQ integration: auto-organize Downloads on "Work" profile
            if profile.name.lowercased().contains("work") || profile.name.lowercased().contains("produc") {
                let downloadsURL = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask).first!
                let count = try? await fileService.organizeDirectory(at: downloadsURL, using: FileCategory.defaults)
                logger.info("AETHER→FileHQ: auto-organized Downloads (\(count ?? 0) files)")
            }
        }
    }

    func captureLayout(for profile: WorkspaceProfile) {
        isCapturingLayout = true
        Task {
            let states = await windowManager.captureAllWindows()
            ProfileStore.shared.updateWindowStates(for: profile, states: states)
            loadProfiles()
            isCapturingLayout = false
        }
    }

    func askAISuggestion() {
        Task {
            let apps = windowManager.getRunningApps()
            let hour = Calendar.current.component(.hour, from: Date())
            let result = await openAI.suggestProfile(currentApps: apps, hour: hour)
            aiSuggestion = result
        }
    }

    // MARK: - VESTA Actions

    func loadPortfolio() {
        Task {
            do {
                portfolio = try await portfolioStore.load()
            } catch {
                logger.error("Portfolio load failed: \(error.localizedDescription)")
            }
        }
    }

    func askPortfolioSuggestion() {
        Task {
            let buckets = portfolio?.bucketPercentages ?? [:]
            let result = await openAI.portfolioAdvice(buckets: buckets)
            portfolioSuggestion = result
        }
    }

    func toggleCurrency() {
        switch currency {
        case .usd: currency = .brl
        case .brl: currency = .eur
        case .eur: currency = .usd
        }
    }

    // MARK: - FileHQ Actions

    func selectDirectory(_ url: URL) {
        currentDirectory = url
        logger.info("FileHQ: selected \(url.path)")
        Task { await loadFileItems() }
    }

    func loadFileItems() async {
        guard let dir = currentDirectory else { return }
        do {
            fileItems = try await fileService.listDirectory(at: dir, filter: fileSearchText)
        } catch {
            logger.error("FileHQ list failed: \(error.localizedDescription)")
        }
    }

    func onFileSearchChanged() {
        searchDebounceTask?.cancel()
        searchDebounceTask = Task {
            try? await Task.sleep(for: .milliseconds(300))
            guard !Task.isCancelled else { return }
            await loadFileItems()
        }
    }

    func navigateToItem(_ item: FileItem) async {
        if item.isParentLink {
            currentDirectory = currentDirectory?.deletingLastPathComponent()
        } else if item.isDirectory {
            currentDirectory = item.url
        } else {
            NSWorkspace.shared.open(item.url)
            logger.info("FileHQ: opened \(item.name)")
            return
        }
        await loadFileItems()
    }

    func organizeCurrentDirectory() async {
        guard let dir = currentDirectory else { return }
        isOrganizing = true
        defer { isOrganizing = false }
        do {
            let count = try await fileService.organizeDirectory(at: dir, using: FileCategory.defaults)
            logger.info("FileHQ: organized \(count) files")
            await loadFileItems()
        } catch {
            logger.error("FileHQ organize failed: \(error.localizedDescription)")
        }
    }

    func organizeNFAOutputs() async {
        do {
            let count = try await nfaBridge.organizeNFAOutputs()
            logger.info("FileHQ→FBP: organized \(count) NFA PDFs")
        } catch {
            logger.error("NFA organize failed: \(error.localizedDescription)")
        }
    }

    // MARK: - FileHQ Notes Actions

    func fetchNotes() async {
        notesStatus = "Fetching notes..."
        do {
            notes = try await notesBridge.getAllNotes()
            notesStatus = "Found \(notes.count) notes"
            logger.info("FileHQ: fetched \(self.notes.count) notes")
        } catch {
            notesStatus = "Fetch failed: \(error.localizedDescription)"
            logger.error("Notes fetch: \(error.localizedDescription)")
        }
    }

    func processNotes() async {
        guard !notes.isEmpty else { notesStatus = "Fetch notes first."; return }
        isProcessingNotes = true
        noteEvaluations = []
        notesProgress = 0
        let provider = aiEvaluationProvider
        let total = Double(notes.count)

        for (i, note) in notes.enumerated() {
            notesStatus = "Evaluating: \(note.title) (\(i+1)/\(notes.count))"
            do {
                let response = try await provider.evaluate(note: note)
                var action: NoteEvaluation.Action = .kept

                if response.isMeaningful {
                    if let cat = response.suggestedCategory {
                        try await notesBridge.createFolder(named: cat)
                        if try await notesBridge.moveNote(id: note.id, toFolder: cat) {
                            action = .moved
                        } else { action = .failed }
                    }
                } else {
                    if try await notesBridge.deleteNote(id: note.id) {
                        action = .deleted
                    } else { action = .failed }
                }

                noteEvaluations.append(NoteEvaluation(
                    id: note.id, noteTitle: note.title,
                    isMeaningful: response.isMeaningful, reason: response.reason,
                    suggestedCategory: response.suggestedCategory, action: action
                ))
            } catch {
                noteEvaluations.append(NoteEvaluation(
                    id: note.id, noteTitle: note.title,
                    isMeaningful: true, reason: "Error: \(error.localizedDescription)",
                    suggestedCategory: nil, action: .failed
                ))
            }
            notesProgress = Double(i + 1) / total
            if !useOnDeviceAI { try? await Task.sleep(for: .milliseconds(500)) }
        }

        isProcessingNotes = false
        let kept = noteEvaluations.filter { $0.action == .kept }.count
        let moved = noteEvaluations.filter { $0.action == .moved }.count
        let deleted = noteEvaluations.filter { $0.action == .deleted }.count
        notesStatus = "Done — Kept: \(kept), Moved: \(moved), Deleted: \(deleted)"
        logger.info("Notes processing complete: \(self.notesStatus)")
    }

    // MARK: - HTTP Routes (Shortcuts / n8n / Node-RED)

    private func registerHTTPRoutes() async {
        // GET /health — PromptForge integration check
        await httpServer.registerRoute("/health") { [weak self] _ in
            guard let self else { return (500, ["status": "error"]) }
            let openAI = await self.openAI.isAvailable()
            let fbp = await self.fbpClient.isHealthy()
            return (200, [
                "status": "ok",
                "project": "FoKS",
                "modules": ["AETHER", "VESTA", "FileHQ"],
                "openai": openAI,
                "fbp": fbp
            ] as [String: Any])
        }

        // POST /files/organize {"path": "/some/directory"}
        await httpServer.registerRoute("/files/organize") { [weak self] body in
            guard let self else { return (500, ["error": "Hub unavailable"]) }
            guard let body, let json = try? JSONSerialization.jsonObject(with: body) as? [String: Any],
                  let path = json["path"] as? String else {
                return (400, ["error": "Missing 'path' in body"])
            }
            let url = URL(fileURLWithPath: path)
            do {
                let count = try await self.fileService.organizeDirectory(at: url, using: FileCategory.defaults)
                return (200, ["organized": count, "path": path])
            } catch {
                return (500, ["error": error.localizedDescription])
            }
        }

        // GET /files/nfa/organize
        await httpServer.registerRoute("/files/nfa/organize") { [weak self] _ in
            guard let self else { return (500, ["error": "Hub unavailable"]) }
            do {
                let count = try await self.nfaBridge.organizeNFAOutputs()
                return (200, ["organized": count])
            } catch {
                return (500, ["error": error.localizedDescription])
            }
        }

        // POST /notes/evaluate
        await httpServer.registerRoute("/notes/evaluate") { [weak self] _ in
            guard let self else { return (500, ["error": "Hub unavailable"]) }
            await self.fetchNotes()
            await self.processNotes()
            let results = await MainActor.run {
                self.noteEvaluations.map { ["title": $0.noteTitle, "action": $0.action.rawValue] }
            }
            return (200, ["results": results, "count": results.count])
        }

        logger.info("FileHQ HTTP routes registered: /files/organize, /files/nfa/organize, /notes/evaluate")
    }

    // MARK: - System Health

    func refreshHealth() async {
        openAIOnline = await openAI.isAvailable()
        fbpOnline = await fbpClient.isHealthy()
        systemStats = ProcessMonitor.currentStats()
    }
}
