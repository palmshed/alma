import Foundation
import Observation

@MainActor
@Observable
public final class ConversationService {
    public var conversations: [ConversationIndexEntry] = []
    public var selectedConversation: Conversation? = nil
    public var selectedId: String? = nil
    public var isLoading = false
    public var error: String? = nil

    private let api: ConversationAPI
    private let defaults: UserDefaults

    public init(api: ConversationAPI, defaults: UserDefaults = .standard) {
        self.api = api
        self.defaults = defaults
    }

    private var savedConversationId: String? {
        get { defaults.string(forKey: selectedIdKey) }
        set { defaults.set(newValue, forKey: selectedIdKey) }
    }

    public func loadConversations() async {
        isLoading = true
        error = nil
        do {
            conversations = try await api.list()
            let savedId = savedConversationId
            if let savedId,
               conversations.contains(where: { $0.id == savedId })
            {
                selectedId = savedId
                await selectConversation(savedId)
            }
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }

    public func selectConversation(_ id: String) async {
        savedConversationId = id
        selectedId = id
        isLoading = true
        error = nil
        do {
            selectedConversation = try await api.get(id: id)
        } catch {
            savedConversationId = nil
            selectedId = nil
            selectedConversation = nil
            self.error = error.localizedDescription
        }
        isLoading = false
    }

    public func createConversation() async {
        isLoading = true
        error = nil
        do {
            let conv = Conversation(
                id: "",
                title: "",
                mode: "chat",
                messages: []
            )
            let created = try await api.create(conv)
            let entry = ConversationIndexEntry(
                id: created.id,
                title: created.title,
                mode: created.mode,
                createdAt: created.createdAt ?? "",
                updatedAt: created.updatedAt ?? ""
            )
            conversations.insert(entry, at: 0)
            selectedConversation = created
            selectedId = created.id
            savedConversationId = created.id
        } catch {
            self.error = error.localizedDescription
        }
        isLoading = false
    }
}

private let selectedIdKey = "selectedConversationId"
