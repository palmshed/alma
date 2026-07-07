import SwiftUI

struct ConversationView: View {
    @State private var messages: [Message] = []
    @State private var inputText = ""

    var body: some View {
        VStack(spacing: 0) {
            messageList
            Divider()
            composer
        }
    }

    private var messageList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(messages) { message in
                    MessageBubble(message: message)
                }
            }
            .padding()
        }
        .overlay {
            if messages.isEmpty {
                ContentUnavailableView(
                    "Start a conversation",
                    systemImage: "message",
                    description: Text("Send a message to begin.")
                )
            }
        }
    }

    private var composer: some View {
        HStack(spacing: 8) {
            TextField("Message Alma…", text: $inputText, axis: .vertical)
                .textFieldStyle(.plain)
                .lineLimit(1...6)

            if !inputText.trimmingCharacters(in: .whitespaces).isEmpty {
                Button(action: sendMessage) {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.title2)
                }
                .buttonStyle(.plain)
                .keyboardShortcut(.return, modifiers: [])
            }
        }
        .padding(12)
        .background(.fill.quaternary)
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .padding()
    }

    private func sendMessage() {
        guard !inputText.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        let message = Message(
            id: UUID().uuidString,
            role: "user",
            content: inputText.trimmingCharacters(in: .whitespaces)
        )
        messages.append(message)
        inputText = ""
    }
}

struct Message: Identifiable {
    let id: String
    let role: String
    let content: String
}

struct MessageBubble: View {
    let message: Message

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
