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
    public var isGenerating = false
    public var generationError: String? = nil

    private let api: ConversationAPI
    private let generationAPI: GenerationAPI
    private let defaults: UserDefaults

    public init(
        api: ConversationAPI,
        generationAPI: GenerationAPI,
        defaults: UserDefaults = .standard
    ) {
        self.api = api
        self.generationAPI = generationAPI
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

    public func deleteConversation(_ id: String) async {
        do {
            try await api.delete(id: id)
            conversations.removeAll { $0.id == id }
            if selectedId == id {
                selectedId = nil
                selectedConversation = nil
                savedConversationId = nil
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func renameConversation(_ id: String, to title: String) async {
        guard let conversation = try? await api.get(id: id) else { return }
        let update = Conversation(
            id: id,
            title: title,
            mode: conversation.mode,
            messages: conversation.messages,
            titleIsManual: true
        )
        do {
            let updated = try await api.update(id: id, update)
            if let idx = conversations.firstIndex(where: { $0.id == id }) {
                conversations[idx].title = updated.title
            }
            if selectedId == id {
                selectedConversation?.title = updated.title
            }
        } catch {
            self.error = error.localizedDescription
        }
    }

    public func send(text: String) async {
        guard !isGenerating else { return }
        guard !text.trimmingCharacters(in: .whitespaces).isEmpty else { return }
        guard var conversation = selectedConversation else { return }

        isGenerating = true
        generationError = nil

        let userMessage = ChatMessage(
            id: UUID().uuidString,
            role: "user",
            timestamp: ISO8601DateFormatter().string(from: Date()),
            content: text
        )
        conversation.messages.append(userMessage)
        selectedConversation = conversation

        updateConversationTitle(with: text)

        do {
            let response = try await generationAPI.generate(messages: conversation.messages)
            let assistantMessage = ChatMessage(
                id: UUID().uuidString,
                role: "assistant",
                timestamp: ISO8601DateFormatter().string(from: Date()),
                content: response
            )
            conversation.messages.append(assistantMessage)
            selectedConversation = conversation

            if let updated = try? await api.update(id: conversation.id, conversation) {
                applyServerTitle(updated.title)
            }
        } catch {
            generationError = error.localizedDescription
        }
        isGenerating = false
    }

    private func updateConversationTitle(with text: String) {
        guard let convId = selectedConversation?.id else { return }
        guard let idx = conversations.firstIndex(where: { $0.id == convId }) else { return }
        let current = conversations[idx].title
        guard current.isEmpty || current == "New conversation" else { return }
        let truncated = text.prefix(60) + (text.count > 60 ? "…" : "")
        conversations[idx].title = String(truncated)
        selectedConversation?.title = String(truncated)
    }

    private func applyServerTitle(_ title: String) {
        guard !title.isEmpty else { return }
        guard let convId = selectedConversation?.id else { return }
        guard let idx = conversations.firstIndex(where: { $0.id == convId }) else { return }
        conversations[idx].title = title
        selectedConversation?.title = title
    }
}

private let selectedIdKey = "selectedConversationId"
