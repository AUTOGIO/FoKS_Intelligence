// AETHER - Profile Model
// Defines workspace profile structure

import Foundation
import CoreGraphics

struct Profile: Codable, Identifiable, Hashable {
    let id: UUID
    var name: String
    var icon: String
    var windowStates: [WindowState]
    var appsToLaunch: [String]
    var isActive: Bool
    var createdAt: Date
    var lastUsed: Date?

    init(
        id: UUID = UUID(),
        name: String,
        icon: String = "rectangle.3.group",
        windowStates: [WindowState] = [],
        appsToLaunch: [String] = [],
        isActive: Bool = false,
        createdAt: Date = Date(),
        lastUsed: Date? = nil
    ) {
        self.id = id
        self.name = name
        self.icon = icon
        self.windowStates = windowStates
        self.appsToLaunch = appsToLaunch
        self.isActive = isActive
        self.createdAt = createdAt
        self.lastUsed = lastUsed
    }

    // Hashable conformance (hash only by ID)
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: Profile, rhs: Profile) -> Bool {
        lhs.id == rhs.id
    }
}

struct WindowState: Codable, Identifiable, Hashable {
    let id: UUID
    let bundleId: String
    let appName: String
    let windowTitle: String
    let frame: CodableRect
    let displayIndex: Int

    init(
        id: UUID = UUID(),
        bundleId: String,
        appName: String,
        windowTitle: String = "",
        frame: CGRect,
        displayIndex: Int
    ) {
        self.id = id
        self.bundleId = bundleId
        self.appName = appName
        self.windowTitle = windowTitle
        self.frame = CodableRect(rect: frame)
        self.displayIndex = displayIndex
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }
}

// CGRect is not Codable by default, so we wrap it
struct CodableRect: Codable, Hashable {
    let x: CGFloat
    let y: CGFloat
    let width: CGFloat
    let height: CGFloat

    init(rect: CGRect) {
        self.x = rect.origin.x
        self.y = rect.origin.y
        self.width = rect.size.width
        self.height = rect.size.height
    }

    var cgRect: CGRect {
        CGRect(x: x, y: y, width: width, height: height)
    }
}

// MARK: - Default Profiles
extension Profile {
    static let defaultProfiles: [Profile] = [
        Profile(
            name: "Work",
            icon: "briefcase.fill",
            appsToLaunch: ["com.microsoft.VSCode", "com.apple.Safari", "com.apple.Terminal"],
            isActive: true
        ),
        Profile(
            name: "Personal",
            icon: "person.fill",
            appsToLaunch: ["com.apple.Safari", "net.whatsapp.WhatsApp", "com.spotify.client"]
        ),
        Profile(
            name: "AI Research",
            icon: "brain.head.profile",
            appsToLaunch: ["com.lmstudio.LMStudio", "com.apple.Terminal", "md.obsidian"]
        )
    ]
}
