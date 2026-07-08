import SwiftUI

struct SettingsView: View {
    @Binding var selectedTheme: AppTheme

    var body: some View {
        TabView {
            appearanceTab
            shortcutsTab
        }
        .scenePadding()
        .frame(width: 450, height: 300)
    }

    private var appearanceTab: some View {
        Form {
            Picker("Theme", selection: $selectedTheme) {
                ForEach(AppTheme.allCases) { theme in
                    Text(theme.displayName).tag(theme)
                }
            }
        }
        .formStyle(.grouped)
        .tabItem {
            Label("Appearance", systemImage: "paintbrush")
        }
    }

    private var shortcutsTab: some View {
        Form {
            Text("Keyboard shortcuts will be configurable here.")
                .foregroundStyle(.secondary)
        }
        .formStyle(.grouped)
        .tabItem {
            Label("Shortcuts", systemImage: "keyboard")
        }
    }
}
