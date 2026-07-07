import SwiftUI

struct ComposerView: View {
    @Binding var text: String
    let onSend: () -> Void
    var isGenerating = false

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            attachmentButton
            textEditor
            sendButton
        }
        .padding(12)
        .background(.fill.quaternary)
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .padding()
    }

    private var attachmentButton: some View {
        Button(action: {}) {
            Image(systemName: "plus")
                .font(.body)
        }
        .buttonStyle(.plain)
    }

    private var textEditor: some View {
        TextField("Message Alma…", text: $text, axis: .vertical)
            .textFieldStyle(.plain)
            .lineLimit(1...6)
            .disabled(isGenerating)
    }

    private var sendButton: some View {
        Button(action: onSend) {
            Image(systemName: "arrow.up.circle.fill")
                .font(.title2)
        }
        .buttonStyle(.plain)
        .disabled(isGenerating || text.trimmingCharacters(in: .whitespaces).isEmpty)
        .keyboardShortcut(.return, modifiers: [])
    }
}
