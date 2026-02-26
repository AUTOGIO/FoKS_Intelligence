// FileOrganizationService — FileHQ file system operations
// Directory enumeration, CRUD, smart organization by UTType categories
// Actor-isolated for thread safety (matches OpenAIService pattern)

import Foundation
import UniformTypeIdentifiers
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "FileOrg")

public actor FileOrganizationService {
    private let fm = FileManager.default

    public init() {}

    // MARK: - Directory Enumeration

    public func listDirectory(at url: URL, filter: String = "") throws -> [FileItem] {
        var items: [FileItem] = []
        let parent = url.deletingLastPathComponent()
        if parent != url {
            items.append(FileItem(url: parent, isParentLink: true))
        }
        let contents = try fm.contentsOfDirectory(
            at: url,
            includingPropertiesForKeys: [.nameKey, .isDirectoryKey, .fileSizeKey, .contentModificationDateKey, .contentTypeKey],
            options: [.skipsHiddenFiles]
        )
        for itemURL in contents {
            let item = FileItem(url: itemURL)
            if !filter.isEmpty {
                guard item.name.localizedCaseInsensitiveContains(filter) else { continue }
            }
            items.append(item)
        }
        return items
    }

    // MARK: - Smart Organization

    public func organizeDirectory(at url: URL, using categories: [FileCategory]) throws -> Int {
        let contents = try fm.contentsOfDirectory(
            at: url,
            includingPropertiesForKeys: [.isDirectoryKey, .contentTypeKey],
            options: [.skipsHiddenFiles]
        )
        var movedCount = 0
        for itemURL in contents {
            let rv = try itemURL.resourceValues(forKeys: [.isDirectoryKey])
            guard !(rv.isDirectory ?? false) else { continue }

            let fileItem = FileItem(url: itemURL)
            let targetCategory = categories.first { fileItem.belongs(to: $0) }
                ?? categories.first { $0.id == "other" }
                ?? FileCategory.defaults.last!

            let targetDir = url.appendingPathComponent(targetCategory.name, isDirectory: true)
            if !fm.fileExists(atPath: targetDir.path) {
                try fm.createDirectory(at: targetDir, withIntermediateDirectories: true)
                logger.info("Created: \(targetCategory.name)/")
            }
            let dest = targetDir.appendingPathComponent(itemURL.lastPathComponent)
            try fm.moveItem(at: itemURL, to: dest)
            logger.info("Moved '\(itemURL.lastPathComponent)' → \(targetCategory.name)/")
            movedCount += 1
        }
        logger.info("Organization complete: \(movedCount) files")
        return movedCount
    }

    // MARK: - CRUD

    public func createFile(named name: String, in directory: URL) throws -> URL {
        let fileURL = directory.appendingPathComponent(name)
        guard !fm.fileExists(atPath: fileURL.path) else {
            throw FileHQError.itemAlreadyExists(name)
        }
        fm.createFile(atPath: fileURL.path, contents: Data())
        logger.info("Created file: \(name)")
        return fileURL
    }

    public func createDirectory(named name: String, in directory: URL) throws -> URL {
        let dirURL = directory.appendingPathComponent(name, isDirectory: true)
        guard !fm.fileExists(atPath: dirURL.path) else {
            throw FileHQError.itemAlreadyExists(name)
        }
        try fm.createDirectory(at: dirURL, withIntermediateDirectories: false)
        logger.info("Created folder: \(name)")
        return dirURL
    }

    public func renameItem(at url: URL, to newName: String) throws -> URL {
        let newURL = url.deletingLastPathComponent().appendingPathComponent(newName)
        guard !fm.fileExists(atPath: newURL.path) else {
            throw FileHQError.itemAlreadyExists(newName)
        }
        try fm.moveItem(at: url, to: newURL)
        logger.info("Renamed '\(url.lastPathComponent)' → '\(newName)'")
        return newURL
    }

    public func deleteItems(at urls: [URL]) throws -> (deleted: Int, failed: Int) {
        var deleted = 0, failed = 0
        for url in urls {
            do {
                try fm.removeItem(at: url)
                logger.info("Deleted: \(url.lastPathComponent)")
                deleted += 1
            } catch {
                logger.error("Delete failed '\(url.lastPathComponent)': \(error.localizedDescription)")
                failed += 1
            }
        }
        return (deleted, failed)
    }
}

public enum FileHQError: LocalizedError {
    case itemAlreadyExists(String)
    case noDirectorySelected
    public var errorDescription: String? {
        switch self {
        case .itemAlreadyExists(let n): "'\(n)' already exists."
        case .noDirectorySelected: "Select a directory first."
        }
    }
}
