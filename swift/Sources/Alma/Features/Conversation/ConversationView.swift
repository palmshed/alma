import SwiftUI

struct ConversationView: View {
    let service: ConversationService
    @State private var text = ""

    var body: some View {
        if let conversation = service.selectedConversation {
            VStack(spacing: 0) {
                messageList(conversation)
                ComposerView(text: $text, onSend: {
                    let textToSend = text
                    text = ""
                    Task { await service.send(text: textToSend) }
                })
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
            }
            .padding()
        }
        .overlay {
            if conversation.messages.isEmpty {
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
                Spacer()
            }

            Group {
                if message.role == "user" {
                    Text(message.content)
                        .padding(12)
                        .background(Color.accentColor)
                        .foregroundStyle(.white)
                } else {
                    Text(message.content)
                        .padding(12)
                        .background(.fill.tertiary)
                        .foregroundStyle(.primary)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: 12))

            if message.role != "user" {
                Spacer()
            }
        }
    }
}
