// FileCategory — FileHQ organization category with UTType + extension matching
// Codable for user-customizable rules in Settings

import Foundation
import UniformTypeIdentifiers

public struct FileCategory: Identifiable, Codable, Hashable {
    public let id: String
    public let name: String
    public let extensions: Set<String>
    public let conformingTypeIdentifiers: [String]

    public var conformingTypes: [UTType] {
        conformingTypeIdentifiers.compactMap { UTType($0) }
    }

    public static let defaults: [FileCategory] = [
        FileCategory(
            id: "images", name: "Images",
            extensions: ["jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp", "svg", "heic", "heif"],
            conformingTypeIdentifiers: [UTType.image.identifier]
        ),
        FileCategory(
            id: "documents", name: "Documents",
            extensions: ["pdf", "docx", "doc", "txt", "xlsx", "xls", "pptx", "ppt", "odt", "ods", "odp", "rtf", "pages", "numbers", "key"],
            conformingTypeIdentifiers: [UTType.pdf.identifier, UTType.plainText.identifier, UTType.rtf.identifier, UTType.spreadsheet.identifier, UTType.presentation.identifier]
        ),
        FileCategory(
            id: "videos", name: "Videos",
            extensions: ["mp4", "mkv", "mov", "avi", "wmv", "flv", "webm"],
            conformingTypeIdentifiers: [UTType.movie.identifier]
        ),
        FileCategory(
            id: "audio", name: "Audio",
            extensions: ["mp3", "wav", "aac", "flac", "ogg", "m4a", "aiff"],
            conformingTypeIdentifiers: [UTType.audio.identifier]
        ),
        FileCategory(
            id: "archives", name: "Archives",
            extensions: ["zip", "rar", "7z", "tar", "gz", "bz2", "xz", "dmg", "iso"],
            conformingTypeIdentifiers: [UTType.archive.identifier]
        ),
        FileCategory(
            id: "scripts", name: "Scripts",
            extensions: ["py", "js", "ts", "java", "cpp", "c", "h", "swift", "html", "css", "sh", "bat", "rb", "go", "rs"],
            conformingTypeIdentifiers: [UTType.sourceCode.identifier]
        ),
        FileCategory(
            id: "other", name: "Other",
            extensions: [],
            conformingTypeIdentifiers: []
        )
    ]
}
