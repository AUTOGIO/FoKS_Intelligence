// FileHQNotesView — Notes.app organizer integrated into FoKS
// Uses FoKSHub.openAI (shared) or on-device NLP for evaluation

import SwiftUI
import FoKS_Service_Lib

struct FileHQNotesView: View {
    @EnvironmentObject private var hub: FoKSHub

    var body: some View {
        VStack(spacing: 0) {
            headerControls
            Divider()
            if hub.noteEvaluations.isEmpty && !hub.isProcessingNotes {
                emptyState
            } else {
                evaluationList
            }
            Divider()
            statusBar
        }
        .padding()
    }

    // MARK: - Header

    private var headerControls: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Notes Organizer").font(.title3.bold())
                Spacer()
                Picker("AI", selection: $hub.useOnDeviceAI) {
                    Text("On-Device").tag(true)
                    Text("Cloud (OpenAI)").tag(false)
                }
                .pickerStyle(.segmented).frame(width: 200)
                Circle()
                    .fill(hub.useOnDeviceAI ? .green : (hub.openAIOnline ? .green : .red))
                    .frame(width: 8, height: 8)
                    .help(hub.useOnDeviceAI ? "On-device — no network" : (hub.openAIOnline ? "OpenAI connected" : "OpenAI offline"))
            }
            HStack(spacing: 10) {
                Button("Fetch Notes") { Task { await hub.fetchNotes() } }
                    .disabled(hub.isProcessingNotes)
                Button("Process All") { Task { await hub.processNotes() } }
                    .disabled(hub.notes.isEmpty || hub.isProcessingNotes)
                    .tint(.green)
                if hub.isProcessingNotes {
                    ProgressView(value: hub.notesProgress).frame(width: 140)
                }
                Spacer()
                Text("\(hub.notes.count) notes").foregroundStyle(.secondary).font(.callout)
                Button("Export") { exportReport() }.disabled(hub.noteEvaluations.isEmpty)
            }
        }
        .padding(.bottom, 6)
    }

    // MARK: - Evaluation Results

    private var evaluationList: some View {
        List(hub.noteEvaluations) { eval in
            HStack(spacing: 10) {
                Image(systemName: actionIcon(eval.action))
                    .foregroundStyle(actionColor(eval.action))
                    .font(.body)
                    .frame(width: 20)
                VStack(alignment: .leading, spacing: 2) {
                    Text(eval.noteTitle).font(.body.bold()).lineLimit(1)
                    Text(eval.reason).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                }
                Spacer()
                if let cat = eval.suggestedCategory {
                    Text(cat).font(.caption2.bold())
                        .padding(.horizontal, 6).padding(.vertical, 3)
                        .background(.blue.opacity(0.15)).clipShape(Capsule())
                }
                Text(eval.action.rawValue.capitalized).font(.caption2.bold())
                    .padding(.horizontal, 6).padding(.vertical, 3)
                    .background(actionColor(eval.action).opacity(0.12))
                    .foregroundStyle(actionColor(eval.action))
                    .clipShape(Capsule())
            }
            .padding(.vertical, 2)
        }
    }

    private var emptyState: some View {
        VStack(spacing: 12) {
            Spacer()
            Image(systemName: "note.text").font(.system(size: 40)).foregroundStyle(.tertiary)
            Text("Click \"Fetch Notes\" to load from Notes.app").foregroundStyle(.secondary)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var statusBar: some View {
        HStack {
            Text(hub.notesStatus).font(.system(.caption, design: .monospaced)).foregroundStyle(.secondary)
            Spacer()
            if hub.fbpOnline {
                HStack(spacing: 4) {
                    Circle().fill(.green).frame(width: 6, height: 6)
                    Text("FBP").font(.caption2).foregroundStyle(.secondary)
                }
            }
        }
        .padding(.top, 4)
    }

    // MARK: - Export

    private func exportReport() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.json]
        panel.nameFieldStringValue = "notes_organization_results.json"
        if panel.runModal() == .OK, let url = panel.url {
            let encoder = JSONEncoder(); encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
            if let data = try? encoder.encode(hub.noteEvaluations) {
                try? data.write(to: url)
            }
        }
    }

    // MARK: - Helpers

    private func actionIcon(_ action: NoteEvaluation.Action) -> String {
        switch action {
        case .kept: "checkmark.circle.fill"
        case .moved: "arrow.right.circle.fill"
        case .deleted: "trash.circle.fill"
        case .failed: "exclamationmark.triangle.fill"
        }
    }

    private func actionColor(_ action: NoteEvaluation.Action) -> Color {
        switch action {
        case .kept: .green; case .moved: .blue; case .deleted: .red; case .failed: .orange
        }
    }
}
