// AETHER - Profile Manager Service
// Handles profile CRUD and switching

import Foundation

class ProfileManager {
    static let shared = ProfileManager()

    private let fileManager = FileManager.default
    private var profilesURL: URL {
        let appSupport = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first!
        let aetherDir = appSupport.appendingPathComponent("AETHER")

        // Create directory if needed
        if !fileManager.fileExists(atPath: aetherDir.path) {
            try? fileManager.createDirectory(at: aetherDir, withIntermediateDirectories: true)
        }

        return aetherDir.appendingPathComponent("profiles.json")
    }

    private init() {
        // Initialize default profiles if none exist
        if loadProfiles().isEmpty {
            saveProfiles(Profile.defaultProfiles)
            print("🌌 Created default profiles")
        }
    }

    // MARK: - Load Profiles
    func loadProfiles() -> [Profile] {
        guard fileManager.fileExists(atPath: profilesURL.path),
              let data = try? Data(contentsOf: profilesURL),
              let profiles = try? JSONDecoder().decode([Profile].self, from: data) else {
            return []
        }
        return profiles
    }

    // MARK: - Save Profiles
    func saveProfiles(_ profiles: [Profile]) {
        guard let data = try? JSONEncoder().encode(profiles) else { return }
        try? data.write(to: profilesURL)
        print("🌌 Saved \(profiles.count) profiles")
    }

    // MARK: - Activate Profile
    func activateProfile(_ profile: Profile) {
        var profiles = loadProfiles()

        // Deactivate all, activate selected
        for i in profiles.indices {
            profiles[i].isActive = (profiles[i].id == profile.id)
            if profiles[i].id == profile.id {
                profiles[i].lastUsed = Date()
            }
        }

        saveProfiles(profiles)

        // Restore windows
        Task {
            await WindowManager.shared.restoreWindows(from: profile.windowStates)
        }

        print("🌌 Activated profile: \(profile.name)")
    }

    // MARK: - Capture Layout for Profile
    func captureLayout(for profile: Profile) async {
        var profiles = loadProfiles()

        guard let index = profiles.firstIndex(where: { $0.id == profile.id }) else { return }

        let windowStates = await WindowManager.shared.captureAllWindows()
        profiles[index].windowStates = windowStates

        saveProfiles(profiles)
        print("🌌 Captured layout for: \(profile.name) (\(windowStates.count) windows)")
    }

    // MARK: - Create Profile
    func createProfile(name: String, icon: String = "rectangle.3.group") -> Profile {
        var profiles = loadProfiles()
        let newProfile = Profile(name: name, icon: icon)
        profiles.append(newProfile)
        saveProfiles(profiles)
        print("🌌 Created profile: \(name)")
        return newProfile
    }

    // MARK: - Delete Profile
    func deleteProfile(_ profile: Profile) {
        var profiles = loadProfiles()
        profiles.removeAll { $0.id == profile.id }
        saveProfiles(profiles)
        print("🌌 Deleted profile: \(profile.name)")
    }

    // MARK: - Update Profile
    func updateProfile(_ profile: Profile) {
        var profiles = loadProfiles()
        guard let index = profiles.firstIndex(where: { $0.id == profile.id }) else { return }
        profiles[index] = profile
        saveProfiles(profiles)
        print("🌌 Updated profile: \(profile.name)")
    }

    // MARK: - Get Active Profile
    func getActiveProfile() -> Profile? {
        loadProfiles().first { $0.isActive }
    }
}
