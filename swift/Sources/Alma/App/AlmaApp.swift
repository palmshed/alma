import SwiftUI

@main
struct AlmaApp: App {
    @State private var selectedTheme: AppTheme = .system

    var body: some Scene {
        WindowGroup {
            ContentView()
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
    var body: some View {
        NavigationSplitView {
            SidebarView()
        } detail: {
            ConversationView()
        }
    }
}
