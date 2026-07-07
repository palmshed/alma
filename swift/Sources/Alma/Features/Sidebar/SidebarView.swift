import SwiftUI

struct SidebarView: View {
    @Bindable var service: ConversationService
    @State private var searchText = ""

    var body: some View {
        VStack(spacing: 0) {
            newChatButton
            searchBar
            content
        }
        .frame(minWidth: 240, maxWidth: 300)
    }

    @ViewBuilder
    private var content: some View {
        if service.isLoading && service.conversations.isEmpty {
            loadingView
        } else if let error = service.error, service.conversations.isEmpty {
            errorView(error)
        } else if service.conversations.isEmpty {
            emptyView
        } else {
            conversationList
        }
    }

    private var loadingView: some View {
        Spacer()
    }

    private var emptyView: some View {
        ContentUnavailableView(
            "No conversations",
            systemImage: "message",
            description: Text("Start a new conversation.")
        )
    }

    private func errorView(_ error: String) -> some View {
        ContentUnavailableView {
            Label("Could not load", systemImage: "exclamationmark.triangle")
        } description: {
            Text(error)
        } actions: {
            Button("Retry") {
                Task { await service.loadConversations() }
            }
        }
    }

    private var newChatButton: some View {
        Button(action: {
            Task { await service.createConversation() }
        }) {
            Label("New conversation", systemImage: "plus")
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .buttonStyle(.plain)
        .padding(12)
    }

    private var searchBar: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundStyle(.secondary)
            TextField("Search conversations…", text: $searchText)
                .textFieldStyle(.plain)
        }
        .padding(8)
        .background(.fill.quaternary)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
    }

    private var conversationList: some View {
        List(selection: $service.selectedId) {
            ForEach(service.conversations) { item in
                VStack(alignment: .leading, spacing: 2) {
                    Text(item.title)
                        .lineLimit(1)
                        .font(.body)
                }
                .padding(.vertical, 4)
                .tag(item.id as String?)
            }
        }
        .listStyle(.plain)
        .onChange(of: service.selectedId) { _, newId in
            guard let id = newId else { return }
            Task { await service.selectConversation(id) }
        }
    }
}
