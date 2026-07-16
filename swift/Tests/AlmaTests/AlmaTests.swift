// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
import Testing
@testable import Alma

struct AlmaTests {
    @Test("App launches with default theme system")
    func defaultTheme() {
        let theme = AppTheme.system
        #expect(theme.colorScheme == nil)
        #expect(theme.displayName == "System")
    }

    @Test("Theme cases are unique")
    func themeUniqueness() {
        let cases = AppTheme.allCases.map(\.rawValue)
        #expect(Set(cases).count == cases.count)
    }

    @Test("Light theme produces light color scheme")
    func lightTheme() {
        #expect(AppTheme.light.colorScheme == .light)
    }

    @Test("Dark theme produces dark color scheme")
    func darkTheme() {
        #expect(AppTheme.dark.colorScheme == .dark)
    }
}
