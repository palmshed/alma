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

/* ── Results ── */

function clearResults() {
  const scroll = document.getElementById('conversation-scroll');
  scroll.innerHTML = '';
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
  var scroll = document.getElementById('conversation-scroll');
  var loading = scroll.querySelector('.loading-dots');
  if (loading) {
    var container = loading.closest('.response-container');
    container.innerHTML = '<em>Error: ' + msg + '</em>';
  } else {
    scroll.innerHTML = '<div class="response-container"><em>Error: ' + msg + '</em></div>';
  }
}

function showSidebarError(msg) {
  var el = document.getElementById('sidebar-error');
  if (!el) return;
  el.textContent = msg;
  el.style.display = '';
  setTimeout(function () { el.style.display = 'none'; }, 4000);
}

/* ── Attachment Handling ── */

function uploadAttachment(file) {
  return new Promise(function (resolve, reject) {
    var formData = new FormData();
    formData.append('file', file);
    fetch('/api/attachments', {
      method: 'POST',
      body: formData,
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (d) { throw new Error(d.error || 'Upload failed'); });
      return r.json();
    }).then(resolve).catch(reject);
  });
}

function deleteAttachment(id) {
  return fetch('/api/attachments/' + encodeURIComponent(id), {
    method: 'DELETE',
  }).then(function (r) {
    if (!r.ok && r.status !== 404) throw new Error('Failed to delete attachment');
  });
}

function handleFilesSelected(fileList) {
  var files = Array.from(fileList);
  function uploadNext() {
    if (files.length === 0) return;
    var file = files.shift();
    uploadAttachment(file).then(function (att) {
      pendingAttachments.push(att);
      renderPendingAttachments();
      uploadNext();
    }).catch(function (err) {
      console.error('Upload failed:', file.name, err);
      uploadNext();
    });
  }
  uploadNext();
}

function renderPendingAttachments() {
  var landingContainer = document.getElementById('landing-pending-attachments');
  var convContainer = document.getElementById('conv-pending-attachments');
  if (pendingAttachments.length === 0) {
    if (landingContainer) landingContainer.style.display = 'none';
    if (convContainer) convContainer.style.display = 'none';
    return;
  }
  var html = '';
  pendingAttachments.forEach(function (att) {
    html += '<span class="attachment-chip">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="12" height="12">' +
      '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>' +
      escapeHtml(att.filename) +
      '<button class="attachment-chip-remove" data-attachment-id="' + att.id + '" type="button" aria-label="Remove ' + escapeHtml(att.filename) + '">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="10" height="10">' +
      '<path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg></button></span>';
  });
  if (landingContainer) { landingContainer.innerHTML = html; landingContainer.style.display = ''; }
  if (convContainer) { convContainer.innerHTML = html; convContainer.style.display = ''; }

  /* Wire remove buttons */
  var removeBtns = (landingContainer || convContainer).querySelectorAll('.attachment-chip-remove');
  removeBtns.forEach(function (btn) {
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var id = btn.getAttribute('data-attachment-id');
      removePendingAttachment(id);
    });
  });
}

function removePendingAttachment(id) {
  var att = null;
  for (var i = 0; i < pendingAttachments.length; i++) {
    if (pendingAttachments[i].id === id) {
      att = pendingAttachments[i];
      pendingAttachments.splice(i, 1);
      break;
    }
  }
  renderPendingAttachments();
  if (att) {
    deleteAttachment(att.id).catch(function (err) {
      console.error('Failed to delete attachment:', err);
    });
  }
}

function clearPendingAttachments() {
  pendingAttachments = [];
  renderPendingAttachments();
}

/* ── API Calls ── */

function handleSubmit() {
  const input = getActiveInput();
  const prompt = input.value.trim();
  if (!prompt) return;
  /* Clear input immediately */
  input.value = '';
  var convInput = document.getElementById('conversation-input');
  if (convInput) convInput.value = '';
  var submitBtn = document.getElementById('submit-button');
  if (submitBtn) { submitBtn.disabled = true; submitBtn.classList.remove('has-text'); }
  var convSubmit = document.getElementById('conversation-submit');
  if (convSubmit) { convSubmit.disabled = true; convSubmit.classList.remove('has-text'); }
  var clearBtn = document.getElementById('clear-button');
  if (clearBtn) clearBtn.style.display = 'none';
  /* Reset textarea height */
  input.style.height = 'auto';
  if (convInput) convInput.style.height = 'auto';

  var attData = pendingAttachments.length > 0
    ? pendingAttachments.map(function (a) { return { id: a.id, filename: a.filename, mime_type: a.mime_type, size: a.size }; })
    : null;
  clearPendingAttachments();

  const { mode, style } = getActiveMode();
  var modeStr = style === 'thinking' ? 'thinking' : style === 'url-context' ? 'web' : mode === 'image' ? 'images' : 'canvas';

  lastPrompt = prompt;
  switchToConversation();

  clearResults();

  /* Show loading immediately */
  var scroll = document.getElementById('conversation-scroll');
  scroll.innerHTML = '<div class="response-container"><div class="loading-dots" role="status" aria-label="Generating"><span class="loading-dots-label">Generating</span><div class="loading-dots-track" style="gap:5px"><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.2s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.4s"></span></div></div></div>';

  var createPromise;
  if (activeConversationId) {
    /* Existing conversation — add user message now */
    var payload = cloneConversation(activeConversationData);
    var userMsg = { role: 'user', content: prompt, timestamp: new Date().toISOString() };
    if (attData) userMsg.attachments = attData;
    payload.messages.push(userMsg);
    payload.metadata = payload.metadata || {};
    payload.metadata.status = 'pending';
    createPromise = fetch('/api/conversations/' + encodeURIComponent(activeConversationId), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(function (r) {
      if (!r.ok) throw new Error('Failed to save message');
      return r.json();
    }).then(function (conv) {
      activeConversationData = conv;
      fetchConversations();
    });
  } else {
    /* New conversation — create with user message */
    var title = prompt.slice(0, 60);
    var userMsg = { role: 'user', content: prompt, timestamp: new Date().toISOString() };
    if (attData) userMsg.attachments = attData;
    createPromise = fetch('/api/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title,
        mode: modeStr,
        messages: [userMsg],
        metadata: { status: 'pending' },
      }),
    }).then(function (r) {
      if (!r.ok) throw new Error('Failed to create conversation');
      return r.json();
    }).then(function (conv) {
      setActiveConversationId(conv.id);
      activeConversationData = conv;
      fetchConversations();
    });
  }

  createPromise.then(function () {
    renderConversation();
    /* Append loading indicator */
    var scroll = document.getElementById('conversation-scroll');
    scroll.insertAdjacentHTML('beforeend', '<div class="response-container"><div class="loading-dots" role="status" aria-label="Generating"><span class="loading-dots-label">Generating</span><div class="loading-dots-track" style="gap:5px"><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.2s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.4s"></span></div></div></div>');
    if (mode === 'image') {
      handleImageGen(prompt);
    } else {
      handleTextGen(prompt, style);
    }
  }).catch(function (e) {
    showError(e.message);
  });
}

function handleTextGen(prompt, style) {
  const endpoint =
    style === 'thinking' ? '/api/generate-with-thinking'
    : style === 'url-context' ? '/api/generate-with-url-context'
    : '/api/generate';

  /* Include full conversation history for context */
  var messages = activeConversationData ? activeConversationData.messages : null;

  fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: prompt, messages: messages }),
  })
    .then((r) => {
      if (!r.ok) throw new Error('Request failed');
      return r.json();
    })
    .then((data) => {
      var thinkingText = data.thinking_summary ? data.thinking_summary.join('\n') : '';
      /* Optimistically update local state */
      activeConversationData.messages.push({
        role: 'assistant',
        content: data.response || '',
        thinking: thinkingText || undefined,
        timestamp: new Date().toISOString(),
      });
      activeConversationData.metadata = activeConversationData.metadata || {};
      activeConversationData.metadata.status = 'complete';
      renderConversation();
      persistConversation();
    })
    .catch((e) => {
      showError(e.message);
      setConversationFailed();
    });
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

      activeConversationData.messages.push({
        role: 'assistant',
        content: '[Image generated]',
        timestamp: new Date().toISOString(),
      });
      activeConversationData.metadata = activeConversationData.metadata || {};
      activeConversationData.metadata.status = 'complete';
      renderConversation();
      persistConversation();
    })
    .catch((e) => {
      showError(e.message);
      setConversationFailed();
    });
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
  clearPendingAttachments();
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
var pendingAttachments = [];

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
      renderConversation();
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

function cloneConversation(conv) {
  return JSON.parse(JSON.stringify(conv));
}

function persistConversation() {
  if (!activeConversationId || !activeConversationData) return;
  var payload = JSON.parse(JSON.stringify(activeConversationData));
  fetch('/api/conversations/' + encodeURIComponent(activeConversationId), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
    .then(function (r) {
      if (!r.ok) throw new Error('Failed to save');
      return r.json();
    })
    .then(function (conv) {
      activeConversationData = conv;
      fetchConversations();
    })
    .catch(function () {});
}

function renderConversation() {
  var scroll = document.getElementById('conversation-scroll');
  if (!activeConversationData || !activeConversationData.messages) {
    scroll.innerHTML = '';
    return;
  }
  var msgs = activeConversationData.messages;
  var html = '';
  msgs.forEach(function (m) {
    if (m.role === 'user') {
      html += '<div class="user-message">' + escapeHtml(m.content) + '</div>';
      if (m.attachments && m.attachments.length > 0) {
        html += '<div class="message-attachments">';
        for (var ai = 0; ai < m.attachments.length; ai++) {
          var att = m.attachments[ai];
          var isImage = att.mime_type && att.mime_type.indexOf('image/') === 0;
          var attId = encodeURIComponent(att.id || '');
          var fname = escapeHtml(att.filename || 'file');
          if (isImage) {
            html += '<a href="/api/attachments/' + attId + '" target="_blank" rel="noopener noreferrer" class="attachment-image-link">' +
              '<img src="/api/attachments/' + attId + '" alt="' + fname + '" class="attachment-image" loading="lazy"></a>';
          } else {
            html += '<a href="/api/attachments/' + attId + '" target="_blank" rel="noopener noreferrer" class="attachment-chip" download="' + fname + '">' +
              '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="12" height="12">' +
              '<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>' +
              fname + '</a>';
          }
        }
        html += '</div>';
      }
    } else if (m.role === 'assistant') {
      if (m.thinking) html += '<div class="thinking-container">' + m.thinking + '</div>';
      html += '<div class="response-container">' + (m.content ? marked.parse(m.content) : '') + '</div>';
    }
  });
  scroll.innerHTML = html;

  /* Attach inline TTS to last assistant message */
  var lastMsg = msgs.length > 0 ? msgs[msgs.length - 1] : null;
  if (lastMsg && lastMsg.role === 'assistant' && lastMsg.content && lastMsg.content.trim()) {
    var lastResponse = scroll.querySelector('.response-container:last-child');
    if (lastResponse) {
      var actionsDiv = document.createElement('div');
      actionsDiv.className = 'response-actions';

      var ttsBtn = document.createElement('button');
      ttsBtn.className = 'btn btn--ghost message-tts-btn';
      ttsBtn.textContent = 'Listen';
      ttsBtn.setAttribute('data-text', lastMsg.content);

      var audioEl = document.createElement('audio');
      audioEl.className = 'audio-player';
      audioEl.controls = true;
      audioEl.preload = 'none';
      audioEl.style.display = 'none';

      ttsBtn.addEventListener('click', function () {
        var btn = this;
        var audio = btn.parentNode.querySelector('.audio-player');
        var text = btn.getAttribute('data-text');
        if (!text || !text.trim()) return;
        btn.disabled = true;
        btn.textContent = 'Generating...';
        fetch('/api/text-to-speech', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text }),
        })
          .then(function (r) {
            if (!r.ok) throw new Error('TTS failed');
            return r.blob();
          })
          .then(function (blob) {
            audio.src = URL.createObjectURL(blob);
            audio.style.display = 'block';
            audio.play();
          })
          .catch(function (e) { console.error('TTS:', e); })
          .finally(function () {
            btn.disabled = false;
            btn.textContent = 'Listen';
          });
      });

      actionsDiv.appendChild(ttsBtn);
      actionsDiv.appendChild(audioEl);
      lastResponse.appendChild(actionsDiv);
    }
  }
}

function setConversationFailed() {
  if (!activeConversationId || !activeConversationData) return;
  var conv = cloneConversation(activeConversationData);
  conv.metadata = conv.metadata || {};
  conv.metadata.status = 'failed';
  fetch('/api/conversations/' + encodeURIComponent(activeConversationId), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(conv),
  })
    .then(function (r) {
      if (!r.ok) return;
      return r.json();
    })
    .then(function (conv) {
      activeConversationData = conv;
      fetchConversations();
    })
    .catch(function () {});
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

  /* ── Attachment file input ── */
  var fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.multiple = true;
  fileInput.accept = 'image/png,image/jpeg,image/webp,image/gif,application/pdf,text/plain,text/markdown';
  fileInput.style.display = 'none';
  fileInput.id = 'attachment-file-input';
  fileInput.addEventListener('change', function (e) {
    if (e.target.files && e.target.files.length > 0) {
      handleFilesSelected(e.target.files);
    }
    e.target.value = '';
  });
  document.body.appendChild(fileInput);

  function triggerFileInput() {
    fileInput.click();
  }

  /* Wire attach buttons */
  var attachBtn = document.getElementById('attach-button');
  if (attachBtn) attachBtn.addEventListener('click', triggerFileInput);
  var convAttachBtn = document.getElementById('conv-attach-button');
  if (convAttachBtn) convAttachBtn.addEventListener('click', triggerFileInput);

  /* ── Segmented control clicks ── */
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
