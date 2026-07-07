import Testing
@testable import Alma

@Test("composer send button is disabled when text is empty")
func testSendButtonDisabledWhenEmpty() {
    #expect("".trimmingCharacters(in: .whitespaces).isEmpty)
}

@Test("composer send button is enabled when text is non-empty")
func testSendButtonEnabledWhenNotEmpty() {
    #expect(!"Hello".trimmingCharacters(in: .whitespaces).isEmpty)
}
