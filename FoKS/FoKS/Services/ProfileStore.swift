// ProfileStore — JSON-backed workspace profile persistence
// ~/Library/Application Support/FoKS/profiles.json

import Foundation
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "ProfileStore")

public final class ProfileStore {
    public static let shared = ProfileStore()

    private var url: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)
            .first!.appendingPathComponent("FoKS")
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir.appendingPathComponent("profiles.json")
    }

    private init() {
        if loadAll().isEmpty {
            save(WorkspaceProfile.defaults)
            logger.info("Created default workspace profiles")
        }
    }

    public func loadAll() -> [WorkspaceProfile] {
        guard FileManager.default.fileExists(atPath: url.path),
              let data = try? Data(contentsOf: url),
              let profiles = try? JSONDecoder().decode([WorkspaceProfile].self, from: data)
        else { return [] }
        return profiles
    }

    public func save(_ profiles: [WorkspaceProfile]) {
        guard let data = try? JSONEncoder().encode(profiles) else { return }
        try? data.write(to: url)
    }

    public func activate(_ profile: WorkspaceProfile) {
        var all = loadAll()
        for i in all.indices {
            all[i].isActive = (all[i].id == profile.id)
            if all[i].id == profile.id { all[i].lastUsed = Date() }
        }
        save(all)
        logger.info("Activated profile: \(profile.name)")
    }

    public func updateWindowStates(for profile: WorkspaceProfile, states: [WindowState]) {
        var all = loadAll()
        guard let idx = all.firstIndex(where: { $0.id == profile.id }) else { return }
        all[idx].windowStates = states
        save(all)
        logger.info("Saved \(states.count) windows for: \(profile.name)")
    }

    public func create(name: String, icon: String = "rectangle.3.group") -> WorkspaceProfile {
        var all = loadAll()
        let p = WorkspaceProfile(name: name, icon: icon)
        all.append(p); save(all)
        return p
    }

    public func delete(_ profile: WorkspaceProfile) {
        var all = loadAll()
        all.removeAll { $0.id == profile.id }
        save(all)
    }
}
