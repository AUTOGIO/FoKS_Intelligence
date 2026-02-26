// NotesAppleScriptBridge — Apple Notes.app automation via NSAppleScript
// Actor-isolated. macOS only.

import Foundation
import os.log

private let logger = Logger(subsystem: "us.giovannini.foks", category: "NotesBridge")

public actor NotesAppleScriptBridge {
    public init() {}

    // MARK: - AppleScript Execution

    private func run(_ source: String) throws -> String {
        var errorDict: NSDictionary?
        guard let script = NSAppleScript(source: source) else {
            throw NotesError.appleScriptFailed("Failed to create script")
        }
        let result = script.executeAndReturnError(&errorDict)
        if let err = errorDict {
            let msg = err[NSAppleScript.errorMessage] as? String ?? "Unknown error"
            logger.error("AppleScript: \(msg)")
            throw NotesError.appleScriptFailed(msg)
        }
        return result.stringValue ?? ""
    }

    // MARK: - Fetch All Notes

    public func getAllNotes() throws -> [NoteItem] {
        let script = """
        tell application "Notes"
            set output to "["
            set noteList to every note
            set noteCount to count of noteList
            repeat with i from 1 to noteCount
                set theNote to item i of noteList
                set noteID to id of theNote
                set noteTitle to name of theNote
                set noteBody to body of theNote
                set noteFolder to name of container of theNote
                set noteTitle to my escapeJSON(noteTitle)
                set noteBody to my escapeJSON(noteBody)
                set noteFolder to my escapeJSON(noteFolder)
                set output to output & "{\\"id\\":\\"" & noteID & "\\",\\"title\\":\\"" & noteTitle & "\\",\\"body\\":\\"" & noteBody & "\\",\\"folder\\":\\"" & noteFolder & "\\"}"
                if i < noteCount then set output to output & ","
            end repeat
            return output & "]"
        end tell

        on escapeJSON(txt)
            set AppleScript's text item delimiters to "\\"
            set parts to text items of txt
            set AppleScript's text item delimiters to "\\\\\\"
            set txt to parts as text
            set AppleScript's text item delimiters to return
            set parts to text items of txt
            set AppleScript's text item delimiters to "\\\\n"
            set txt to parts as text
            set AppleScript's text item delimiters to ""
            return txt
        end escapeJSON
        """
        let json = try run(script)
        guard let data = json.data(using: .utf8) else { throw NotesError.invalidData }
        do {
            return try JSONDecoder().decode([NoteItem].self, from: data)
        } catch {
            logger.error("JSON decode failed: \(error.localizedDescription)")
            throw NotesError.invalidData
        }
    }

    // MARK: - Note Operations

    public func deleteNote(id: String) throws -> Bool {
        let result = try run("""
        tell application "Notes"
            delete (note id "\(id)")
            return "true"
        end tell
        """)
        return result.lowercased() == "true"
    }

    public func createFolder(named name: String) throws {
        _ = try run("""
        tell application "Notes"
            if not (exists folder "\(name)") then
                make new folder with properties {name:"\(name)"}
            end if
        end tell
        """)
        logger.info("Ensured folder: \(name)")
    }

    public func moveNote(id: String, toFolder folderName: String) throws -> Bool {
        let result = try run("""
        tell application "Notes"
            move (note id "\(id)") to folder "\(folderName)"
            return "true"
        end tell
        """)
        return result.lowercased() == "true"
    }

    public func getExistingFolders() throws -> [String] {
        let json = try run("""
        tell application "Notes"
            set output to "["
            set fl to every folder
            set fc to count of fl
            repeat with i from 1 to fc
                set output to output & "\\"" & name of item i of fl & "\\""
                if i < fc then set output to output & ","
            end repeat
            return output & "]"
        end tell
        """)
        guard let data = json.data(using: .utf8) else { return [] }
        return (try? JSONDecoder().decode([String].self, from: data)) ?? []
    }
}

public enum NotesError: LocalizedError {
    case appleScriptFailed(String)
    case invalidData
    public var errorDescription: String? {
        switch self {
        case .appleScriptFailed(let m): "AppleScript: \(m)"
        case .invalidData: "Failed to parse Notes data"
        }
    }
}
