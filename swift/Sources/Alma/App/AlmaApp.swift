import SwiftUI

@main
struct AlmaApp: App {
    @State private var selectedTheme: AppTheme = .system
    @State private var service = ConversationService(
        api: ConversationAPI(
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
        .task {
            await service.loadConversations()
        }
    }
}
