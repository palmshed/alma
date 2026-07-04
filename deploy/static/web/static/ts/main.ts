// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT

// Global declarations
declare var marked: any;

// Type definitions
interface ModeStyle {
    mode: string;
    style: string;
}

interface ApiResponse {
    response?: string;
    thinking_summary?: string[];
    error?: string;
}

// Initialize marked.js for markdown rendering
marked.setOptions({
    breaks: true,
    gfm: true
});

// Unified search handler
function handleUnifiedSearch(): void {
    const input = document.querySelector('.unified-input') as HTMLTextAreaElement;
    const { mode, style } = getSelectedMode();
    const prompt = input.value.trim();

    if (!prompt) {
        showError('Hmm… we\'re waiting on your next word. What would you like to ask?');
        return;
    }

    // Clear previous results
    clearResults();

    // Show loading state
    showLoading(mode);

    // Route to appropriate handler based on mode and style
    if (mode === 'text') {
        handleTextGeneration(prompt, style);
    } else if (mode === 'image') {
        handleImageGeneration(prompt);
    }
}

// Clear all result containers
function clearResults(): void {
    const responseContainer = document.getElementById('response') as HTMLElement;
    const thinkingContainer = document.getElementById('thinking') as HTMLElement;
    const imageContainer = document.getElementById('image-container') as HTMLElement;
    const ttsButton = document.getElementById('tts-button') as HTMLElement;
    const audioPlayer = document.getElementById('audio-player') as HTMLAudioElement;

    responseContainer.style.display = 'none';
    thinkingContainer.style.display = 'none';
    imageContainer.style.display = 'none';
    ttsButton.style.display = 'none';
    audioPlayer.style.display = 'none';
    audioPlayer.pause();
    audioPlayer.src = '';
}

// Show loading state
function showLoading(mode: string): void {
    const submitButton = document.getElementById('submit-button') as HTMLButtonElement;
    submitButton.classList.add('loading');
    submitButton.disabled = true;

    if (mode === 'text') {
        const responseContainer = document.getElementById('response') as HTMLElement;
        responseContainer.innerHTML = '<em id="thinking-text" class="character-by-character">Thinking...</em>';
        animateText(responseContainer.querySelector('#thinking-text') as HTMLElement);
        responseContainer.style.display = 'block';
    } else if (mode === 'image') {
        const imageContainer = document.getElementById('image-container') as HTMLElement;
        const imageMessage = document.getElementById('image-message') as HTMLElement;
        imageMessage.textContent = 'Generating your image. This may take a minute...';
        imageMessage.style.display = 'block';
        imageContainer.style.display = 'block';
    }
}

// Hide loading state
function hideLoading(): void {
    const submitButton = document.getElementById('submit-button') as HTMLButtonElement;
    submitButton.classList.remove('loading');
    submitButton.disabled = false;
}

// Show error message
function showError(message: string): void {
    const responseContainer = document.getElementById('response') as HTMLElement;
    responseContainer.innerHTML = `<em>Error: ${message}</em>`;
    responseContainer.style.display = 'block';
}

// Handle text generation based on style
function handleTextGeneration(prompt: string, style: string): void {
    if (style === 'thinking') {
        handleThinkingMode(prompt);
    } else if (style === 'url-context') {
        handleUrlContext(prompt);
    } else {
        handleNormalGeneration(prompt);
    }
}

// Handle normal text generation
function handleNormalGeneration(prompt: string): void {
    fetch('/api/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt: prompt })
    })
    .then((response: Response) => {
        if (!response.ok) {
            throw new Error('Hmm… grace takes time. Try again.');
        }
        return response.json();
    })
    .then((data: ApiResponse) => {
        const responseContainer = document.getElementById('response') as HTMLElement;
        responseContainer.innerHTML = marked.parse(data.response || '');

        // Show the TTS button if we have a response
        if (data.response && data.response.trim()) {
            const ttsButton = document.getElementById('tts-button') as HTMLElement;
            ttsButton.style.display = 'block';
            ttsButton.setAttribute('data-text', data.response);
        }
        hideLoading();
    })
    .catch((error: Error) => {
        console.error('Error:', error);
        showError(error.message);
        hideLoading();
    });
}

// Get selected mode
function getSelectedMode(): ModeStyle {
    const activeTab = document.querySelector('.search-tab.active') as HTMLElement;
    return {
        mode: activeTab.dataset.mode || '',
        style: activeTab.dataset.style || ''
    };
}

// Character-by-character animation
function animateText(element: HTMLElement): void {
    const text = element.textContent || '';
    element.textContent = '';
    let i = 0;
    const intervalId = setInterval(() => {
        element.textContent += text[i];
        i++;
        if (i === text.length) {
            clearInterval(intervalId);
        }
    }, 20);
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupUnifiedSearchHandlers();
    // Add other setup functions as needed
});

// Setup unified search handlers
function setupUnifiedSearchHandlers(): void {
    const input = document.querySelector('.unified-input') as HTMLTextAreaElement;
    const submitButton = document.getElementById('submit-button') as HTMLButtonElement;
    const clearButton = document.getElementById('clear-button') as HTMLElement;

    // Handle submit button click
    submitButton.addEventListener('click', handleUnifiedSearch);

    // Handle clear button click
    clearButton.addEventListener('click', function() {
        input.value = '';
        clearButton.style.display = 'none';
        clearResults();
        input.focus();
    });

    // Handle Enter key press
    input.addEventListener('keypress', function(event: KeyboardEvent) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            handleUnifiedSearch();
        }
    });

    // Show/hide clear button based on input content
    input.addEventListener('input', function() {
        clearButton.style.display = input.value.trim() ? 'block' : 'none';

        // Auto-resize textarea
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    // Auto-focus on input
    input.focus();
}

// Placeholder for other functions (simplified for demo)
function handleThinkingMode(prompt: string): void {
    // Implementation here
    console.log('Thinking mode:', prompt);
}

function handleUrlContext(prompt: string): void {
    // Implementation here
    console.log('URL context:', prompt);
}

function handleImageGeneration(prompt: string): void {
    // Implementation here
    console.log('Image generation:', prompt);
}
