"use strict";
marked.setOptions({ breaks: true, gfm: true });

/* ── Helpers ── */

function getActiveInput() {
  const landing = document.getElementById('landing');
  const conversation = document.getElementById('conversation');
  if (landing && landing.style.display !== 'none') {
    return document.getElementById('landing-input');
  }
  return document.getElementById('conversation-input');
}

function getActiveSubmit() {
  const landing = document.getElementById('landing');
  if (landing && landing.style.display !== 'none') {
    return document.getElementById('submit-button');
  }
  return document.getElementById('conversation-submit');
}

function getActiveMode() {
  const active = document.querySelector('.segmented-control-btn.active');
  return {
    mode: active ? active.dataset.mode : 'text',
    style: active ? active.dataset.style : 'normal',
  };
}

/* ── TTS ── */

function handleTTS() {
  const btn = document.getElementById('tts-button');
  const text = btn.getAttribute('data-text');
  const audio = document.getElementById('audio-player');
  if (!text || !text.trim()) return;

  btn.disabled = true;
  btn.textContent = 'Generating...';

  fetch('/api/text-to-speech', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
    .then((r) => {
      if (!r.ok) throw new Error('TTS failed');
      return r.blob();
    })
    .then((blob) => {
      audio.src = URL.createObjectURL(blob);
      audio.style.display = 'block';
      audio.play();
    })
    .catch((e) => console.error('TTS:', e))
    .finally(() => {
      btn.disabled = false;
      btn.textContent = 'Listen';
    });
}

/* ── Results ── */

function clearResults() {
  const scroll = document.getElementById('conversation-scroll');
  scroll.innerHTML = '';
  document.getElementById('tts-button').style.display = 'none';
  const audio = document.getElementById('audio-player');
  audio.style.display = 'none';
  audio.pause();
  audio.src = '';
  document.getElementById('image-container').style.display = 'none';
}

function showLoading() {
  const btn = getActiveSubmit();
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="composer-loading-dots"><span></span><span></span><span></span></span>';
  }
  document.getElementById('conversation-loading-bar').style.display = 'block';
}

function hideLoading() {
  const btn = getActiveSubmit();
  if (btn) {
    btn.disabled = false;
    btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="18" height="18"><path d="M14.536 21.686a.5.5 0 0 0 .937-.024l6.5-19a.496.496 0 0 0-.635-.635l-19 6.5a.5.5 0 0 0-.024.937l7.93 3.18a2 2 0 0 1 1.112 1.11z"/><path d="m21.854 2.147-10.94 10.939"/></svg>';
  }
  document.getElementById('conversation-loading-bar').style.display = 'none';
}

function showError(msg) {
  const scroll = document.getElementById('conversation-scroll');
  scroll.innerHTML = `<div class="response-container"><em>Error: ${msg}</em></div>`;
}

function showSidebarError(msg) {
  var el = document.getElementById('sidebar-error');
  if (!el) return;
  el.textContent = msg;
  el.style.display = '';
  setTimeout(function () { el.style.display = 'none'; }, 4000);
}

/* ── API Calls ── */

function handleSubmit() {
  const input = getActiveInput();
  const prompt = input.value.trim();
  if (!prompt) return;
  const { mode, style } = getActiveMode();

  lastPrompt = prompt;
  switchToConversation();

  const scroll = document.getElementById('conversation-scroll');
  scroll.innerHTML = `
    <div class="response-container">
      <div class="loading-dots" role="status" aria-label="Generating">
        <span class="loading-dots-label">Generating</span>
        <div class="loading-dots-track" style="gap:5px">
          <span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0s"></span>
          <span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.2s"></span>
          <span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.4s"></span>
        </div>
      </div>
    </div>`;

  if (mode === 'image') {
    handleImageGen(prompt);
  } else {
    handleTextGen(prompt, style);
  }
}

function handleTextGen(prompt, style) {
  const endpoint =
    style === 'thinking' ? '/api/generate-with-thinking'
    : style === 'url-context' ? '/api/generate-with-url-context'
    : '/api/generate';

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })
    .then((r) => {
      if (!r.ok) throw new Error('Request failed');
      return r.json();
    })
    .then((data) => {
      const scroll = document.getElementById('conversation-scroll');
      let html = '';
      var thinkingText = '';
      if (data.thinking_summary) {
        thinkingText = data.thinking_summary.join('\n');
        html += `<div class="thinking-container">${thinkingText}</div>`;
      }
      html += `<div class="response-container">${marked.parse(data.response || '')}</div>`;
      scroll.innerHTML = html;

      if (data.response && data.response.trim()) {
        const btn = document.getElementById('tts-button');
        btn.style.display = 'block';
        btn.setAttribute('data-text', data.response);
      }

      saveConversation(lastPrompt, data.response || '', thinkingText);
    })
    .catch((e) => { showError(e.message); });
}

function handleImageGen(prompt) {
  fetch('/api/generate-image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  })
    .then((r) => {
      if (!r.ok) throw new Error('Image generation failed');
      return r.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      document.getElementById('generated-image').src = url;
      document.getElementById('generated-image').style.display = 'block';
      document.getElementById('download-image').href = url;
      document.getElementById('download-image').style.display = 'inline-block';
      document.getElementById('fullscreen-image').style.display = 'inline-block';
      document.getElementById('image-container').style.display = 'block';
      document.getElementById('conversation-scroll').innerHTML = '';

      saveConversation(lastPrompt, '[Image generated]', '');
    })
    .catch((e) => { showError(e.message); });
}

/* ── Layout Transitions ── */

function switchToConversation() {
  document.getElementById('landing').style.display = 'none';
  document.getElementById('conversation').style.display = 'flex';
}

function switchToLanding() {
  document.getElementById('landing').style.display = '';
  document.getElementById('conversation').style.display = 'none';
}

function hasConversationContent() {
  const scroll = document.getElementById('conversation-scroll');
  return scroll && scroll.innerHTML.trim().length > 0;
}

function handleNewChat() {
  var loadingBar = document.getElementById('conversation-loading-bar');
  if (loadingBar && loadingBar.style.display !== 'none') return;
  if (hasConversationContent()) {
    showNewChatDialog();
  } else {
    clearResults();
    switchToLanding();
    var input = document.getElementById('landing-input');
    if (input) input.focus();
  }
}

function showNewChatDialog() {
  document.getElementById('new-chat-dialog').style.display = '';
  document.getElementById('dialog-overlay').style.display = '';
}

function hideNewChatDialog() {
  document.getElementById('new-chat-dialog').style.display = 'none';
  document.getElementById('dialog-overlay').style.display = 'none';
}

function confirmNewChat() {
  hideNewChatDialog();
  clearResults();
  setActiveConversationId(null);
  activeConversationData = null;
  switchToLanding();
  const input = document.getElementById('landing-input');
  if (input) input.focus();
  const sidebar = document.getElementById('sidebar-menu');
  if (sidebar && sidebar.classList.contains('open')) closeMenu();
}

/* ── Conversation State ── */

var activeConversationId = null;
var activeConversationData = null;
var lastPrompt = '';
var sidebarConversations = [];
var sidebarEditingId = null;
var sidebarEditTitle = '';
var sidebarConfirmDeleteId = null;
var sidebarSearchQuery = '';

function setActiveConversationId(id) {
  activeConversationId = id;
  try {
    if (id) { localStorage.setItem('alma_active_conversation', id); }
    else { localStorage.removeItem('alma_active_conversation'); }
  } catch (e) {}
}

function formatDate(iso) {
  var d = new Date(iso);
  var now = new Date();
  var diffMs = now.getTime() - d.getTime();
  var diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return diffDays + 'd ago';
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function fetchConversations() {
  fetch('/api/conversations')
    .then(function (r) {
      if (!r.ok) throw new Error('Failed to fetch conversations');
      return r.json();
    })
    .then(function (list) {
      sidebarConversations = list || [];
      renderConversationList();
    })
    .catch(function () {
      sidebarConversations = [];
      renderConversationList();
    });
}

function escapeHtml(str) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function highlightText(text, query) {
  if (!query) return escapeHtml(text);
  var idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return escapeHtml(text);
  return escapeHtml(text.slice(0, idx)) + '<mark>' + escapeHtml(text.slice(idx, idx + query.length)) + '</mark>' + escapeHtml(text.slice(idx + query.length));
}

function renderConversationList() {
  var list = document.getElementById('conversation-list');
  var empty = document.getElementById('sidebar-empty');
  var searchEmpty = document.getElementById('sidebar-search-empty');
  if (!list) return;

  list.innerHTML = '';

  var filtered = sidebarConversations;
  if (sidebarSearchQuery) {
    var q = sidebarSearchQuery.toLowerCase();
    filtered = sidebarConversations.filter(function (c) { return c.title.toLowerCase().indexOf(q) !== -1; });
  }

  if (filtered.length === 0) {
    if (sidebarSearchQuery) {
      if (searchEmpty) searchEmpty.style.display = '';
      if (empty) empty.style.display = 'none';
    } else {
      if (empty) empty.style.display = sidebarConversations.length === 0 ? '' : 'none';
      if (searchEmpty) searchEmpty.style.display = 'none';
    }
    return;
  }

  if (empty) empty.style.display = 'none';
  if (searchEmpty) searchEmpty.style.display = 'none';

  var sorted = filtered.slice().sort(function (a, b) {
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });

  sorted.forEach(function (conv) {
    var item = document.createElement('div');
    item.className = 'sidebar-conversation-item' + (conv.id === activeConversationId ? ' sidebar-conversation-item--active' : '');
    item.setAttribute('role', 'button');
    item.setAttribute('tabindex', '0');

    var main = document.createElement('div');
    main.className = 'sidebar-conversation-item-main';

    if (sidebarEditingId === conv.id) {
      var input = document.createElement('input');
      input.className = 'sidebar-conversation-rename-input';
      input.setAttribute('aria-label', 'Rename conversation');
      input.value = sidebarEditTitle || conv.title;
      input.addEventListener('blur', function () { finishRename(conv.id); });
      input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') finishRename(conv.id);
        if (e.key === 'Escape') { sidebarEditingId = null; renderConversationList(); }
      });
      input.addEventListener('click', function (e) { e.stopPropagation(); });
      setTimeout(function () { input.focus(); input.select(); }, 10);
      main.appendChild(input);
    } else {
      var title = document.createElement('span');
      title.className = 'sidebar-conversation-title';
      title.innerHTML = highlightText(conv.title, sidebarSearchQuery);
      main.appendChild(title);

      var date = document.createElement('span');
      date.className = 'sidebar-conversation-date';
      date.textContent = formatDate(conv.updated_at);
      main.appendChild(date);
    }

    item.appendChild(main);

    var actions = document.createElement('div');
    actions.className = 'sidebar-conversation-actions';

    if (sidebarEditingId !== conv.id) {
      var renameBtn = document.createElement('button');
      renameBtn.className = 'btn btn--ghost sidebar-action-btn';
      renameBtn.setAttribute('aria-label', 'Rename conversation');
      renameBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="12" height="12"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>';
      renameBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        sidebarEditingId = conv.id;
        sidebarEditTitle = conv.title;
        renderConversationList();
      });
      actions.appendChild(renameBtn);

      var deleteBtn = document.createElement('button');
      deleteBtn.className = 'btn btn--ghost sidebar-action-btn';
      deleteBtn.setAttribute('aria-label', 'Delete conversation');
      deleteBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="12" height="12"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>';
      deleteBtn.addEventListener('click', function (e) {
        e.stopPropagation();
        sidebarConfirmDeleteId = conv.id;
        document.getElementById('sidebar-delete-dialog').style.display = '';
      });
      actions.appendChild(deleteBtn);
    }

    item.appendChild(actions);

    item.addEventListener('click', function () { selectConversation(conv.id); });
    item.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        selectConversation(conv.id);
      }
    });

    list.appendChild(item);
  });
}

function selectConversation(id) {
  fetch('/api/conversations/' + encodeURIComponent(id))
    .then(function (r) {
      if (!r.ok) throw new Error('Failed to load conversation');
      return r.json();
    })
    .then(function (conv) {
      setActiveConversationId(id);
      activeConversationData = conv;
      var msgs = conv.messages || [];
      var lastAssistant = null;
      var lastThinking = null;
      var lastImage = null;
      for (var i = msgs.length - 1; i >= 0; i--) {
        if (msgs[i].role === 'assistant' && !lastAssistant) lastAssistant = msgs[i];
        if (msgs[i].thinking && !lastThinking) lastThinking = msgs[i];
        if (msgs[i].image && !lastImage) lastImage = msgs[i];
      }
      var scroll = document.getElementById('conversation-scroll');
      var html = '';
      msgs.forEach(function (m) {
        if (m.role === 'user') {
          html += '<div class="user-message">' + m.content + '</div>';
        } else if (m.role === 'assistant') {
          if (m.thinking) html += '<div class="thinking-container">' + m.thinking + '</div>';
          if (m.image) {
            html += '<div class="image-container" style="display:block"><img src="' + m.image + '" class="generated-image" style="display:block;max-width:100%;border-radius:8px"/></div>';
          }
          html += '<div class="response-container">' + (m.content ? marked.parse(m.content) : '') + '</div>';
        }
      });
      scroll.innerHTML = html;
      if (lastAssistant && lastAssistant.content) {
        var btn = document.getElementById('tts-button');
        btn.style.display = '';
        btn.setAttribute('data-text', lastAssistant.content);
      }
      /* Restore conversation mode */
      if (conv.mode) {
        var modeMap = { canvas: 'text_normal', thinking: 'text_thinking', web: 'text_url-context', images: 'image_normal' };
        var targetStyle = modeMap[conv.mode];
        if (targetStyle) {
          var parts = targetStyle.split('_');
          document.querySelectorAll('.segmented-control-btn').forEach(function (b) {
            var match = b.dataset.mode === parts[0] && b.dataset.style === parts[1];
            b.classList.toggle('active', match);
            b.setAttribute('aria-checked', match ? 'true' : 'false');
          });
          updateSuggestionsVisibility();
        }
      }
      switchToConversation();
      renderConversationList();
      closeMenu();
    })
    .catch(function () {});
}

function finishRename(id) {
  var input = document.querySelector('.sidebar-conversation-rename-input');
  var trimmed = input ? input.value.trim() : sidebarEditTitle;
  if (!trimmed) {
    sidebarEditingId = null;
    renderConversationList();
    return;
  }
  /* Optimistic update */
  var prevConv = null;
  for (var i = 0; i < sidebarConversations.length; i++) {
    if (sidebarConversations[i].id === id) {
      prevConv = sidebarConversations[i];
      sidebarConversations[i] = Object.assign({}, sidebarConversations[i], { title: trimmed });
      break;
    }
  }
  renderConversationList();

  fetch('/api/conversations/' + encodeURIComponent(id))
    .then(function (r) { return r.json(); })
    .then(function (conv) {
      conv.title = trimmed;
      conv.title_is_manual = true;
      return fetch('/api/conversations/' + encodeURIComponent(id), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(conv),
      });
    })
    .then(function () {
      sidebarEditingId = null;
    })
    .catch(function () {
      /* Rollback */
      if (prevConv) {
        for (var i = 0; i < sidebarConversations.length; i++) {
          if (sidebarConversations[i].id === id) {
            sidebarConversations[i] = prevConv;
            break;
          }
        }
      }
      showSidebarError('Failed to rename conversation');
    });
  sidebarEditingId = null;
}

function confirmDeleteConversation() {
  var id = sidebarConfirmDeleteId;
  if (!id) return;
  /* Optimistic remove */
  var deletedConv = null;
  for (var i = 0; i < sidebarConversations.length; i++) {
    if (sidebarConversations[i].id === id) {
      deletedConv = sidebarConversations[i];
      sidebarConversations.splice(i, 1);
      break;
    }
  }
  sidebarConfirmDeleteId = null;
  document.getElementById('sidebar-delete-dialog').style.display = 'none';
  renderConversationList();

  fetch('/api/conversations/' + encodeURIComponent(id), { method: 'DELETE' })
    .then(function () {
      /* Re-fetch to sync */
      return fetch('/api/conversations');
    })
    .then(function (r) { return r.json(); })
    .then(function (list) {
      sidebarConversations = list || [];
      /* Auto-select next most recent if deleted was active */
      if (id === activeConversationId) {
        var sorted = sidebarConversations.slice().sort(function (a, b) {
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        });
        if (sorted.length > 0) {
          selectConversation(sorted[0].id);
        } else {
          setActiveConversationId(null);
          activeConversationData = null;
          clearResults();
          switchToLanding();
          var landingInput = document.getElementById('landing-input');
          if (landingInput) landingInput.focus();
        }
      } else {
        renderConversationList();
      }
    })
    .catch(function () {
      /* Rollback */
      if (deletedConv) {
        sidebarConversations.push(deletedConv);
        sidebarConversations.sort(function (a, b) {
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        });
      }
      showSidebarError('Failed to delete conversation');
      renderConversationList();
    });
}

function cancelDeleteConversation() {
  sidebarConfirmDeleteId = null;
  document.getElementById('sidebar-delete-dialog').style.display = 'none';
}

function saveConversation(prompt, responseText, thinkingText) {
  var existing = (activeConversationData && activeConversationData.messages) || [];
  var newMessages = existing.concat([
    { role: 'user', content: prompt, timestamp: new Date().toISOString() },
    { role: 'assistant', content: responseText || '', thinking: thinkingText || undefined, timestamp: new Date().toISOString() },
  ]);
  var nextTitle = existing.length === 0 ? (responseText || prompt).slice(0, 60) : undefined;
  var currentMode = getActiveMode();
  var mode = currentMode.style === 'thinking' ? 'thinking' : currentMode.style === 'url-context' ? 'web' : currentMode.mode === 'image' ? 'images' : 'canvas';

  if (activeConversationId) {
    var payload = { messages: newMessages, mode: mode };
    if (nextTitle) payload.title = nextTitle;
    fetch('/api/conversations/' + encodeURIComponent(activeConversationId), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function () {
        fetchConversations();
      })
      .catch(function () {});
  } else {
    fetch('/api/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: nextTitle || 'New conversation', messages: newMessages, mode: mode }),
    })
      .then(function (r) { return r.json(); })
      .then(function (conv) {
        setActiveConversationId(conv.id);
        activeConversationData = conv;
        fetchConversations();
      })
      .catch(function () {});
  }
}

/* ── Suggestions ── */

function updateSuggestionsVisibility() {
  const input = getActiveInput();
  const hasContent = input && input.value.trim();
  const suggestions = document.querySelector('.landing-suggestions');
  if (!suggestions) return;

  if (hasContent) {
    suggestions.style.display = 'none';
    return;
  }

  suggestions.style.display = 'flex';
  const active = document.querySelector('.segmented-control-btn.active');
  const tabStyle = active ? active.dataset.style : 'normal';
  const tabMode = active ? active.dataset.mode : 'text';

  document.querySelectorAll('.chip').forEach((c) => (c.style.display = 'none'));

  let selector = '.tab-canvas';
  if (tabMode === 'image') selector = '.tab-image';
  else if (tabStyle === 'thinking') selector = '.tab-thinking';
  else if (tabStyle === 'url-context') selector = '.tab-url';

  document.querySelectorAll(selector).forEach((c) => (c.style.display = 'inline-block'));
}

/* ── Init ── */

document.addEventListener('DOMContentLoaded', function () {
  const input = getActiveInput();
  const submitBtn = document.getElementById('submit-button');
  const clearBtn = document.getElementById('clear-button');
  const convInput = document.getElementById('conversation-input');
  const convSubmit = document.getElementById('conversation-submit');

  /* Segmented control clicks */
  document.querySelectorAll('.segmented-control-btn').forEach((btn) => {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.segmented-control-btn').forEach((b) => {
        b.classList.remove('active');
        b.setAttribute('aria-checked', 'false');
      });
      this.classList.add('active');
      this.setAttribute('aria-checked', 'true');
      updateSuggestionsVisibility();
    });
  });

  /* Submit handlers */
  function onInputChange() {
    const val = input.value.trim();
    if (submitBtn) {
      submitBtn.disabled = !val;
      if (val) submitBtn.classList.add('has-text');
      else submitBtn.classList.remove('has-text');
    }
    if (clearBtn) clearBtn.style.display = val ? 'block' : 'none';
    updateSuggestionsVisibility();
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';

    /* Conversation input sync */
    if (convInput) {
      convInput.value = input.value;
    }
  }

  function onConvInputChange() {
    const val = convInput.value.trim();
    if (convSubmit) {
      convSubmit.disabled = !val;
      if (val) convSubmit.classList.add('has-text');
      else convSubmit.classList.remove('has-text');
    }
  }

  if (input) {
    input.addEventListener('input', onInputChange);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (input.value.trim()) handleSubmit();
      }
    });
    input.focus();
  }

  if (convInput) {
    convInput.addEventListener('input', onConvInputChange);
    convInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (convInput.value.trim()) {
          /* Sync and submit */
          const landingInput = document.getElementById('landing-input');
          if (landingInput) landingInput.value = convInput.value;
          handleSubmit();
        }
      }
    });
  }

  if (submitBtn) submitBtn.addEventListener('click', handleSubmit);
  if (convSubmit) convSubmit.addEventListener('click', handleSubmit);

  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      input.value = '';
      clearBtn.style.display = 'none';
      if (submitBtn) { submitBtn.disabled = true; submitBtn.classList.remove('has-text'); }
      updateSuggestionsVisibility();
      input.focus();
    });
  }

  /* Chip clicks */
  document.querySelectorAll('.chip').forEach((chip) => {
    chip.addEventListener('click', function () {
      input.value = this.dataset.text;
      input.focus();
      input.dispatchEvent(new Event('input'));
    });
  });

  /* Theme toggle */
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    const saved = localStorage.getItem('theme');
    if (saved === 'light') document.documentElement.setAttribute('data-theme', 'light');
    themeToggle.addEventListener('click', function () {
      const cur = document.documentElement.getAttribute('data-theme');
      if (cur === 'light') {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'dark');
      } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
      }
    });
  }

  /* Menu toggle */
  const menuToggle = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar-menu');
  const overlay = document.getElementById('menu-overlay');
  const close = document.getElementById('close-menu');

  function openMenu() {
    sidebar.classList.add('open');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    fetchConversations();
  }
  function closeMenu() {
    sidebar.classList.remove('open');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
    sidebarEditingId = null;
    sidebarConfirmDeleteId = null;
    sidebarSearchQuery = '';
    var si = document.getElementById('sidebar-search-input');
    if (si) { si.value = ''; }
    var sc = document.getElementById('sidebar-search-clear');
    if (sc) { sc.style.display = 'none'; }
    document.getElementById('sidebar-delete-dialog').style.display = 'none';
    renderConversationList();
  }

  if (menuToggle) menuToggle.addEventListener('click', openMenu);
  if (close) close.addEventListener('click', closeMenu);
  if (overlay) overlay.addEventListener('click', closeMenu);

  /* Delete dialog buttons */
  document.getElementById('sidebar-delete-confirm').addEventListener('click', confirmDeleteConversation);
  document.getElementById('sidebar-delete-cancel').addEventListener('click', cancelDeleteConversation);

  /* Search */
  var searchInput = document.getElementById('sidebar-search-input');
  var searchClear = document.getElementById('sidebar-search-clear');
  if (searchInput) {
    searchInput.addEventListener('input', function () {
      sidebarSearchQuery = searchInput.value;
      if (sidebarSearchQuery) {
        searchClear.style.display = '';
      } else {
        searchClear.style.display = 'none';
      }
      renderConversationList();
    });
  }
  if (searchClear) {
    searchClear.addEventListener('click', function () {
      sidebarSearchQuery = '';
      searchInput.value = '';
      searchClear.style.display = 'none';
      renderConversationList();
      searchInput.focus();
    });
  }

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar && sidebar.classList.contains('open')) closeMenu();
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (searchInput && sidebar && sidebar.classList.contains('open')) {
        searchInput.focus();
      }
    }
  });

  /* TTS */
  const ttsBtn = document.getElementById('tts-button');
  if (ttsBtn) ttsBtn.addEventListener('click', handleTTS);

  /* New conversation */
  const newChatBtn = document.getElementById('new-chat-btn');
  const sidebarNewChat = document.getElementById('sidebar-new-chat');
  const dialogConfirm = document.getElementById('dialog-confirm');
  const dialogCancel = document.getElementById('dialog-cancel');
  const dialogOverlay = document.getElementById('dialog-overlay');

  if (newChatBtn) newChatBtn.addEventListener('click', handleNewChat);
  if (sidebarNewChat) {
    sidebarNewChat.addEventListener('click', function () {
      closeMenu();
      handleNewChat();
    });
  }
  if (dialogConfirm) dialogConfirm.addEventListener('click', confirmNewChat);
  if (dialogCancel) dialogCancel.addEventListener('click', hideNewChatDialog);
  if (dialogOverlay) dialogOverlay.addEventListener('click', hideNewChatDialog);

  document.addEventListener('keydown', function (e) {
    var dialog = document.getElementById('new-chat-dialog');
    if (!dialog || dialog.style.display === 'none') return;
    if (e.key === 'Escape') {
      e.stopPropagation();
      hideNewChatDialog();
      return;
    }
    if (e.key === 'Tab') {
      var focusable = dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (!focusable.length) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
      e.preventDefault();
      handleNewChat();
    }
  });

  /* Initial suggestions */
  updateSuggestionsVisibility();

  /* Pre-fetch conversations for sidebar */
  setTimeout(fetchConversations, 500);

  /* Restore active conversation on reload */
  var storedId = null;
  try { storedId = localStorage.getItem('alma_active_conversation'); } catch (e) {}
  if (storedId) {
    fetch('/api/conversations/' + encodeURIComponent(storedId))
      .then(function (r) {
        if (!r.ok) throw new Error('Not found');
        return r.json();
      })
      .then(function (conv) {
        setActiveConversationId(storedId);
        activeConversationData = conv;
        var modeMap = { canvas: 'text_normal', thinking: 'text_thinking', web: 'text_url-context', images: 'image_normal' };
        if (conv.mode) {
          var targetStyle = modeMap[conv.mode];
          if (targetStyle) {
            var parts = targetStyle.split('_');
            document.querySelectorAll('.segmented-control-btn').forEach(function (b) {
              var match = b.dataset.mode === parts[0] && b.dataset.style === parts[1];
              b.classList.toggle('active', match);
              b.setAttribute('aria-checked', match ? 'true' : 'false');
            });
            updateSuggestionsVisibility();
          }
        }
        selectConversation(storedId);
      })
      .catch(function () {
        try { localStorage.removeItem('alma_active_conversation'); } catch (e) {}
      });
  }

  /* Delete dialog focus trap */
  document.addEventListener('keydown', function (e) {
    var dialog = document.getElementById('sidebar-delete-dialog');
    if (!dialog || dialog.style.display === 'none') return;
    if (e.key === 'Escape') {
      e.stopPropagation();
      cancelDeleteConversation();
      return;
    }
    if (e.key === 'Tab') {
      var focusable = dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (!focusable.length) return;
      var first = focusable[0];
      var last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });
});
