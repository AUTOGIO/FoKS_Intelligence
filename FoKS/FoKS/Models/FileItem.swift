// FileItem — FileHQ file/directory domain model
// Uses UTType for Apple-native type identification

import Foundation
import UniformTypeIdentifiers

public struct FileItem: Identifiable, Hashable {
    public let id: String
    public let url: URL
    public let name: String
    public let isDirectory: Bool
    public let size: Int64
    public let modificationDate: Date
    public let contentType: UTType?
    public let isParentLink: Bool

    public init(url: URL, isParentLink: Bool = false) {
        self.url = url
        self.isParentLink = isParentLink
        self.id = isParentLink ? ".." : url.absoluteString

        if isParentLink {
            self.name = ".."; self.isDirectory = true; self.size = 0
            self.modificationDate = .distantPast; self.contentType = nil
            return
        }

        let rv = try? url.resourceValues(forKeys: [
            .nameKey, .isDirectoryKey, .fileSizeKey,
            .contentModificationDateKey, .contentTypeKey
        ])
        self.name = rv?.name ?? url.lastPathComponent
        self.isDirectory = rv?.isDirectory ?? false
        self.size = Int64(rv?.fileSize ?? 0)
        self.modificationDate = rv?.contentModificationDate ?? .distantPast
        self.contentType = rv?.contentType
    }

    public var typeDescription: String {
        if isParentLink { return "<Parent>" }
        if isDirectory { return "<Folder>" }
        if let ct = contentType { return ct.localizedDescription ?? ct.identifier }
        let ext = url.pathExtension.uppercased()
        return ext.isEmpty ? "File" : "\(ext) File"
    }

    public var formattedSize: String {
        guard !isDirectory && !isParentLink else { return "" }
        return ByteCountFormatter.string(fromByteCount: size, countStyle: .file)
    }

    public var formattedDate: String {
        guard !isParentLink else { return "" }
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd HH:mm"
        return f.string(from: modificationDate)
    }

    /// Check if file belongs to a category via UTType conformance or extension.
    public func belongs(to category: FileCategory) -> Bool {
        if isDirectory || isParentLink { return false }
        if let ct = contentType {
            for parentType in category.conformingTypes {
                if ct.conforms(to: parentType) { return true }
            }
        }
        return category.extensions.contains(url.pathExtension.lowercased())
    }
}
