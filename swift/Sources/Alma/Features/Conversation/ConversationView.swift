import SwiftUI
import MarkdownUI

struct ConversationView: View {
    let service: ConversationService
    @State private var text = ""

    var body: some View {
        if let conversation = service.selectedConversation {
            VStack(spacing: 0) {
                messageList(conversation)
                if let error = service.generationError {
                    errorBanner(error)
                }
                ComposerView(
                    text: $text,
                    onSend: {
                        let textToSend = text
                        text = ""
                        Task { await service.send(text: textToSend) }
                    },
                    isGenerating: service.isGenerating
                )
            }
        } else {
            ContentUnavailableView(
                "Select a conversation",
                systemImage: "sidebar.left",
                description: Text("Choose a conversation from the sidebar.")
            )
        }
    }

    private func messageList(_ conversation: Conversation) -> some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(conversation.messages) { message in
                    MessageBubble(message: message)
                }

                if service.isGenerating {
                    HStack {
                        ProgressView()
                            .padding(12)
                        Spacer()
                    }
                }
            }
            .padding()
        }
        .overlay {
            if conversation.messages.isEmpty && !service.isGenerating {
                ContentUnavailableView(
                    "Start a conversation",
                    systemImage: "message",
                    description: Text("Send a message to begin.")
                )
            }
        }
    }

    private func errorBanner(_ error: String) -> some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.yellow)
            Text(error)
                .font(.callout)
                .textSelection(.enabled)
            Spacer()
            Button {
                service.generationError = nil
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(.fill.quaternary)
        .padding(.horizontal)
        .padding(.bottom, 8)
        .transition(.move(edge: .bottom).combined(with: .opacity))
    }
}

struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            if message.role == "user" {
                Spacer(minLength: 60)
            }

            content
                .frame(maxWidth: 0.72, alignment: .leading)

            if message.role != "user" {
                Spacer(minLength: 60)
            }
        }
    }

    @ViewBuilder
    private var content: some View {
        if message.role == "user" {
            Text(message.content)
                .padding(12)
                .background(Color.accentColor)
                .foregroundStyle(.white)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .textSelection(.enabled)
        } else {
            Markdown(message.content)
                .markdownTheme(.basic)
                .markdownTextStyle {
                    FontSize(14)
                }
                .padding(16)
                .background(.fill.tertiary)
                .clipShape(RoundedRectangle(cornerRadius: 12))
                .textSelection(.enabled)
        }
    }
}
