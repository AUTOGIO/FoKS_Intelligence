// NFAFileOrganizationBridge — Organizes FBP NFA output PDFs
// Watches /Users/dnigga/Downloads/NFA_Outputs and sorts DANFE vs DAR
// Integration point: FBPClient + FileOrganizationService

import Foundation
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "NFABridge")

public actor NFAFileOrganizationBridge {
    public static let defaultNFADir = URL(fileURLWithPath: "/Users/dnigga/Downloads/NFA_Outputs")
    private let nfaDir: URL
    private let fm = FileManager.default

    public init(nfaDir: URL = NFAFileOrganizationBridge.defaultNFADir) {
        self.nfaDir = nfaDir
    }

    /// Organize all NFA output subdirectories — DANFE PDFs and DAR PDFs
    /// into consolidated category folders.
    /// Returns count of PDFs moved.
    public func organizeNFAOutputs() async throws -> Int {
        guard fm.fileExists(atPath: nfaDir.path) else {
            logger.info("NFA output directory not found: \(self.nfaDir.path)")
            return 0
        }

        let subDirs = try fm.contentsOfDirectory(at: nfaDir, includingPropertiesForKeys: [.isDirectoryKey])
        var totalMoved = 0

        for dir in subDirs {
            let isDir = (try? dir.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) ?? false
            guard isDir else { continue }
            // Skip already-organized category folders
            let dirName = dir.lastPathComponent
            if ["DANFE", "DAR_Taxa_Servico", "Other_NFA_Docs"].contains(dirName) { continue }

            let pdfs = try fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
                .filter { $0.pathExtension.lowercased() == "pdf" }

            for pdf in pdfs {
                let name = pdf.lastPathComponent.uppercased()
                let targetFolder: String
                if name.contains("DANFE") {
                    targetFolder = "DANFE"
                } else if name.contains("TAXA") || name.contains("DAR") || name.contains("SERVICO") {
                    targetFolder = "DAR_Taxa_Servico"
                } else {
                    targetFolder = "Other_NFA_Docs"
                }

                let targetDir = nfaDir.appendingPathComponent(targetFolder)
                if !fm.fileExists(atPath: targetDir.path) {
                    try fm.createDirectory(at: targetDir, withIntermediateDirectories: true)
                }

                let dest = targetDir.appendingPathComponent(pdf.lastPathComponent)
                if !fm.fileExists(atPath: dest.path) {
                    try fm.moveItem(at: pdf, to: dest)
                    totalMoved += 1
                    logger.info("NFA: \(pdf.lastPathComponent) → \(targetFolder)/")
                }
            }
        }

        logger.info("NFA organization complete: \(totalMoved) PDFs sorted")
        return totalMoved
    }
}
