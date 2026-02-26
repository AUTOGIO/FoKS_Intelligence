// FileHQBrowserView — File browser with split-view table + preview
// Integrated into FoKS as third pillar alongside AETHER and VESTA

import SwiftUI
import FoKS_Service_Lib

struct FileHQBrowserView: View {
    @EnvironmentObject private var hub: FoKSHub
    @State private var showNewFileSheet = false
    @State private var showNewFolderSheet = false
    @State private var showRenameSheet = false
    @State private var showDeleteConfirm = false
    @State private var inputName = ""

    var body: some View {
        VStack(spacing: 0) {
            toolbar
            Divider()
            HSplitView {
                fileTable.frame(minWidth: 400)
                previewPane.frame(minWidth: 220, idealWidth: 280)
            }
        }
        .sheet(isPresented: $showNewFileSheet) { nameSheet(title: "New File", placeholder: "file.txt") { name in Task { await createFile(name) } } }
        .sheet(isPresented: $showNewFolderSheet) { nameSheet(title: "New Folder", placeholder: "Folder") { name in Task { await createFolder(name) } } }
        .sheet(isPresented: $showRenameSheet) { nameSheet(title: "Rename", placeholder: hub.selectedFileItem?.name ?? "", initial: hub.selectedFileItem?.name ?? "") { name in Task { await rename(name) } } }
        .confirmationDialog("Delete?", isPresented: $showDeleteConfirm) {
            Button("Delete", role: .destructive) {
                if let item = hub.selectedFileItem {
                    Task { try? await hub.fileService.deleteItems(at: [item.url]); await hub.loadFileItems() }
                }
            }
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 10) {
            Text(hub.currentDirectory?.path ?? "No directory selected")
                .font(.system(.caption, design: .monospaced))
                .lineLimit(1).truncationMode(.head)
                .foregroundStyle(.secondary)

            Spacer()

            TextField("Filter...", text: $hub.fileSearchText)
                .textFieldStyle(.roundedBorder)
                .frame(maxWidth: 180)
                .onChange(of: hub.fileSearchText) { _, _ in hub.onFileSearchChanged() }

            Button { selectDir() } label: { Label("Open", systemImage: "folder.badge.plus") }

            Divider().frame(height: 18)

            Button { Task { await hub.organizeCurrentDirectory() } } label: { Label("Organize", systemImage: "tray.2") }
                .disabled(hub.currentDirectory == nil || hub.isOrganizing)
                .tint(.green)

            Button { Task { await hub.organizeNFAOutputs() } } label: { Label("NFA", systemImage: "doc.text") }
                .help("Organize FBP NFA output PDFs (DANFE/DAR)")
                .disabled(!hub.fbpOnline && !FileManager.default.fileExists(atPath: NFAFileOrganizationBridge.defaultNFADir.path))

            Button { showRenameSheet = true } label: { Image(systemName: "pencil") }
                .disabled(hub.selectedFileItem == nil || hub.selectedFileItem?.isParentLink == true)

            Button { showDeleteConfirm = true } label: { Image(systemName: "trash") }
                .disabled(hub.selectedFileItem == nil || hub.selectedFileItem?.isParentLink == true)
                .tint(.red)

            Menu { menuItems } label: { Label("New", systemImage: "plus") }
                .disabled(hub.currentDirectory == nil)
        }
        .padding(.horizontal, 10).padding(.vertical, 6)
    }

    @ViewBuilder private var menuItems: some View {
        Button("New File") { inputName = ""; showNewFileSheet = true }
        Button("New Folder") { inputName = ""; showNewFolderSheet = true }
    }

    // MARK: - File Table

    private var fileTable: some View {
        Table(hub.fileItems, selection: Binding(
            get: { hub.selectedFileItem?.id },
            set: { id in hub.selectedFileItem = hub.fileItems.first { $0.id == id } }
        )) {
            TableColumn("Name") { (item: FileItem) in
                HStack(spacing: 5) {
                    Image(systemName: item.isDirectory ? "folder.fill" : "doc.fill")
                        .foregroundStyle(item.isDirectory ? .blue : .secondary).font(.caption2)
                    Text(item.name).lineLimit(1)
                }
            }.width(min: 140, ideal: 240)
            TableColumn("Type") { (item: FileItem) in Text(item.typeDescription) }.width(min: 70, ideal: 90)
            TableColumn("Size") { (item: FileItem) in Text(item.formattedSize).monospacedDigit() }.width(min: 60, ideal: 80)
            TableColumn("Modified") { (item: FileItem) in Text(item.formattedDate) }.width(min: 90, ideal: 130)
        }
        .contextMenu(forSelectionType: String.self) { _ in } primaryAction: { ids in
            if let id = ids.first, let item = hub.fileItems.first(where: { $0.id == id }) {
                Task { await hub.navigateToItem(item) }
            }
        }
    }

    // MARK: - Preview Pane

    private var previewPane: some View {
        VStack {
            Text("Preview").font(.headline).foregroundStyle(.secondary).padding(.top, 6)
            Divider()
            if let item = hub.selectedFileItem {
                if item.isDirectory || item.isParentLink {
                    VStack { Image(systemName: "folder.fill").font(.largeTitle).foregroundStyle(.blue); Text(item.name) }
                } else if let ct = item.contentType, ct.conforms(to: .image) {
                    if let img = NSImage(contentsOf: item.url) {
                        Image(nsImage: img).resizable().aspectRatio(contentMode: .fit).frame(maxWidth: 260, maxHeight: 260)
                            .clipShape(RoundedRectangle(cornerRadius: 6))
                    }
                    Text(item.name).font(.caption).foregroundStyle(.secondary)
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Name: \(item.name)\nSize: \(item.formattedSize)\nType: \(item.typeDescription)\nModified: \(item.formattedDate)")
                                .font(.system(.caption, design: .monospaced))
                            if let ct = item.contentType, ct.conforms(to: .text),
                               let preview = try? String(contentsOf: item.url, encoding: .utf8).prefix(2048) {
                                Divider()
                                Text(preview).font(.system(.caption2, design: .monospaced)).foregroundStyle(.secondary).textSelection(.enabled)
                            }
                        }.padding(8)
                    }
                }
            } else {
                Spacer()
                Image(systemName: "doc.questionmark").font(.title).foregroundStyle(.tertiary)
                Text("Select a file").font(.caption).foregroundStyle(.tertiary)
                Spacer()
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(.black.opacity(0.1))
    }

    // MARK: - Directory Picker

    private func selectDir() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false; panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url { hub.selectDirectory(url) }
    }

    // MARK: - CRUD Helpers

    private func createFile(_ name: String) async {
        guard let dir = hub.currentDirectory else { return }
        _ = try? await hub.fileService.createFile(named: name, in: dir)
        await hub.loadFileItems()
    }
    private func createFolder(_ name: String) async {
        guard let dir = hub.currentDirectory else { return }
        _ = try? await hub.fileService.createDirectory(named: name, in: dir)
        await hub.loadFileItems()
    }
    private func rename(_ name: String) async {
        guard let item = hub.selectedFileItem else { return }
        _ = try? await hub.fileService.renameItem(at: item.url, to: name)
        await hub.loadFileItems()
    }

    // MARK: - Name Input Sheet

    private func nameSheet(title: String, placeholder: String, initial: String = "", action: @escaping (String) -> Void) -> some View {
        VStack(spacing: 14) {
            Text(title).font(.headline)
            TextField(placeholder, text: $inputName).textFieldStyle(.roundedBorder).frame(width: 280)
                .onAppear { inputName = initial }
            HStack {
                Button("Cancel") { showNewFileSheet = false; showNewFolderSheet = false; showRenameSheet = false }
                    .keyboardShortcut(.cancelAction)
                Button("OK") {
                    let n = inputName.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard !n.isEmpty else { return }
                    action(n)
                    showNewFileSheet = false; showNewFolderSheet = false; showRenameSheet = false
                }.keyboardShortcut(.defaultAction)
            }
        }.padding(20)
    }
}
