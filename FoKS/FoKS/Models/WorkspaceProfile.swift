// WorkspaceProfile — AETHER workspace profile model

import Foundation
import CoreGraphics

public struct WorkspaceProfile: Codable, Identifiable, Hashable {
    public let id: UUID
    public var name: String
    public var icon: String
    public var windowStates: [WindowState]
    public var appsToLaunch: [String]
    public var isActive: Bool
    public var createdAt: Date
    public var lastUsed: Date?

    public init(
        id: UUID = UUID(), name: String, icon: String = "rectangle.3.group",
        windowStates: [WindowState] = [], appsToLaunch: [String] = [],
        isActive: Bool = false, createdAt: Date = Date(), lastUsed: Date? = nil
    ) {
        self.id = id; self.name = name; self.icon = icon
        self.windowStates = windowStates; self.appsToLaunch = appsToLaunch
        self.isActive = isActive; self.createdAt = createdAt; self.lastUsed = lastUsed
    }

    public func hash(into hasher: inout Hasher) { hasher.combine(id) }
    public static func == (lhs: Self, rhs: Self) -> Bool { lhs.id == rhs.id }

    public static let defaults: [WorkspaceProfile] = [
        .init(name: "Work", icon: "briefcase.fill",
              appsToLaunch: ["com.microsoft.VSCode", "com.apple.Safari", "com.apple.Terminal"],
              isActive: true),
        .init(name: "Personal", icon: "person.fill",
              appsToLaunch: ["com.apple.Safari", "net.whatsapp.WhatsApp", "com.spotify.client"]),
        .init(name: "AI Research", icon: "brain.head.profile",
              appsToLaunch: ["com.apple.Terminal", "md.obsidian"]),
    ]
}

public struct WindowState: Codable, Identifiable, Hashable {
    public let id: UUID
    public let bundleId: String
    public let appName: String
    public let windowTitle: String
    public let frame: CodableRect
    public let displayIndex: Int

    public init(
        id: UUID = UUID(), bundleId: String, appName: String,
        windowTitle: String = "", frame: CGRect, displayIndex: Int
    ) {
        self.id = id; self.bundleId = bundleId; self.appName = appName
        self.windowTitle = windowTitle; self.frame = CodableRect(rect: frame)
        self.displayIndex = displayIndex
    }

    public func hash(into hasher: inout Hasher) { hasher.combine(id) }
}

public struct CodableRect: Codable, Hashable {
    public let x, y, width, height: CGFloat
    public init(rect: CGRect) { x = rect.origin.x; y = rect.origin.y; width = rect.size.width; height = rect.size.height }
    public var cgRect: CGRect { CGRect(x: x, y: y, width: width, height: height) }
}
