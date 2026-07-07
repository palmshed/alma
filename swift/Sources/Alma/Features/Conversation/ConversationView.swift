import SwiftUI

struct ConversationView: View {
    let service: ConversationService
    @State private var text = ""

    var body: some View {
        if let conversation = service.selectedConversation {
            VStack(spacing: 0) {
                messageList(conversation)
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

                if let error = service.generationError {
                    HStack {
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(.red)
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
}

struct MessageBubble: View {
    let message: ChatMessage

    var body: some View {
        HStack {
            if message.role == "user" {
                Spacer(minLength: 60)
            }

            if message.role == "user" {
                Text(message.content)
                    .padding(12)
                    .background(Color.accentColor)
                    .foregroundStyle(.white)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .textSelection(.enabled)
            } else {
                Text(message.content)
                    .padding(12)
                    .background(.fill.tertiary)
                    .foregroundStyle(.primary)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .textSelection(.enabled)
            }

            if message.role != "user" {
                Spacer(minLength: 60)
            }
        }
    }
}
