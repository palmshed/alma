import SwiftUI

struct SidebarView: View {
    @State private var conversations: [ConversationListItem] = []
    @State private var searchText = ""

    var body: some View {
        VStack(spacing: 0) {
            newChatButton
            searchBar
            conversationList
        }
        .frame(minWidth: 240, maxWidth: 300)
    }

    private var newChatButton: some View {
        Button(action: {}) {
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
        List(conversations) { item in
            VStack(alignment: .leading, spacing: 2) {
                Text(item.title)
                    .lineLimit(1)
                    .font(.body)
                Text(item.preview)
                    .lineLimit(1)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 4)
        }
        .listStyle(.plain)
    }
}

struct ConversationListItem: Identifiable {
    let id: String
    let title: String
    let preview: String
}
