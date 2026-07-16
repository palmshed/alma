// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import SwiftUI

@main
struct AlmaApp: App {
    @State private var selectedTheme: AppTheme = .system
    @State private var service = ConversationService(
        api: ConversationAPI(
            client: APIClient(baseURL: URL(string: "http://localhost:8080")!)
        ),
        generationAPI: GenerationAPI(
            client: APIClient(baseURL: URL(string: "http://localhost:8080")!)
        )
    )

    var body: some Scene {
        WindowGroup {
            ContentView(service: service)
                .environment(\.theme, selectedTheme)
                .preferredColorScheme(selectedTheme.colorScheme)
        }
        .windowStyle(.titleBar)
        .windowResizability(.contentSize)
        .commands {
            CommandGroup(replacing: .newItem) {
                Button("New Conversation") {
                    Task { await service.createConversation() }
                }
                .keyboardShortcut("n", modifiers: .command)
            }
        }

        Settings {
            SettingsView(selectedTheme: $selectedTheme)
        }
    }
}

struct ContentView: View {
    let service: ConversationService

    var body: some View {
        NavigationSplitView {
            SidebarView(service: service)
        } detail: {
            ConversationView(service: service)
        }
        .navigationTitle(service.selectedConversation?.title ?? "Alma")
        .task {
            await service.loadConversations()
        }
    }
}
