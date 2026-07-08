import SwiftUI

struct SidebarView: View {
    @Bindable var service: ConversationService
    @State private var searchText = ""
    @State private var renameId: String?
    @State private var renameText = ""
    @State private var deleteId: String?

    private var filteredConversations: [ConversationIndexEntry] {
        if searchText.isEmpty {
            return service.conversations
        }
        return service.conversations.filter {
            $0.title.localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            newChatButton
            searchBar
            content
        }
        .frame(minWidth: 240, maxWidth: 300)
        .alert("Rename Conversation", isPresented: renameAlertVisible) {
            TextField("Title", text: $renameText)
            Button("Rename") {
                if let id = renameId {
                    Task { await service.renameConversation(id, to: renameText) }
                }
                renameId = nil
            }
            Button("Cancel", role: .cancel) {
                renameId = nil
            }
        }
        .alert("Delete Conversation", isPresented: deleteAlertVisible) {
            Button("Delete", role: .destructive) {
                if let id = deleteId {
                    Task { await service.deleteConversation(id) }
                }
                deleteId = nil
            }
            Button("Cancel", role: .cancel) {
                deleteId = nil
            }
        } message: {
            Text("This cannot be undone.")
        }
    }

    private var renameAlertVisible: Binding<Bool> {
        Binding(
            get: { renameId != nil },
            set: { if !$0 { renameId = nil } }
        )
    }

    private var deleteAlertVisible: Binding<Bool> {
        Binding(
            get: { deleteId != nil },
            set: { if !$0 { deleteId = nil } }
        )
    }

    @ViewBuilder
    private var content: some View {
        if service.isLoading && service.conversations.isEmpty {
            loadingView
        } else if let error = service.error, service.conversations.isEmpty {
            errorView(error)
        } else if filteredConversations.isEmpty {
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
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
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
            ForEach(filteredConversations) { item in
                VStack(alignment: .leading, spacing: 1) {
                    Text(item.title)
                        .lineLimit(1)
                        .font(.body)
                    Text(relativeDate(item.updatedAt))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(.vertical, 6)
                .padding(.horizontal, 4)
                .tag(item.id as String?)
                .contextMenu {
                    Button("Rename…") {
                        renameId = item.id
                        renameText = item.title
                    }
                    Divider()
                    Button("Delete", role: .destructive) {
                        deleteId = item.id
                    }
                }
            }
        }
        .listStyle(.plain)
        .onChange(of: service.selectedId) { _, newId in
            guard let id = newId else { return }
            Task { await service.selectConversation(id) }
        }
    }
}

private func relativeDate(_ iso: String) -> String {
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    if let date = formatter.date(from: iso) {
        return format(date)
    }
    formatter.formatOptions = [.withInternetDateTime]
    if let date = formatter.date(from: iso) {
        return format(date)
    }
    return ""
}

private func format(_ date: Date) -> String {
    let rel = RelativeDateTimeFormatter()
    rel.unitsStyle = .abbreviated
    return rel.localizedString(for: date, relativeTo: Date())
}
