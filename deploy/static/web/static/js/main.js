// SPDX-FileCopyrightText: Copyright (c) 2025-2026 Palmshed
// SPDX-License-Identifier: MIT
"use strict";
marked.setOptions({ breaks: true, gfm: true });

/* ── Mode Menu ── */

var currentMode = 'canvas';
var _skipInitSound = false;
var currentModel = 'auto';

var MODEL_LABELS = {
  'auto': 'Auto',
  'gemini-2.5-flash': 'Gemini 2.5 Flash',
  'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
  'gemini-3.0-flash': 'Gemini 3 Flash',
  'gemini-3.1-flash-lite': 'Gemini 3.1 Flash Lite',
  'gemini-3.5-flash': 'Gemini 3.5 Flash',
};

var MODEL_PRIORITY = ['gemini-2.5-flash', 'gemini-3.5-flash', 'gemini-3.0-flash', 'gemini-2.5-flash-lite', 'gemini-3.1-flash-lite'];
var modelAvailability = {};

function resolveModel() {
  if (currentModel !== 'auto') return currentModel;
  var now = Date.now();
  for (var i = 0; i < MODEL_PRIORITY.length; i++) {
    var m = MODEL_PRIORITY[i];
    var avail = modelAvailability[m];
    if (!avail || (avail.availableAt && now >= avail.availableAt)) {
      return m;
    }
  }
  return MODEL_PRIORITY[0];
}

function markModelUnavailable(model, retryAfter) {
  modelAvailability[model] = { availableAt: retryAfter ? Date.now() + retryAfter * 1000 : Infinity };
}

var MODE_ICONS = {
  auto: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  chat: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>',
  code: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
  canvas: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M12 2l10 5-10 5L2 7Z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>',
  thinking: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063A2 2 0 0 0 14.063 15.5l-1.582 6.135a.5.5 0 0 1-.963 0z"/></svg>',
  web: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>',
  images: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" width="15" height="15"><rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>',
};

var MODE_LABELS = {
  auto: 'Auto',
  chat: 'Chat',
  search: 'Search',
  code: 'Code',
  canvas: 'Canvas',
  thinking: 'Thinking',
  web: 'Web',
  images: 'Images',
};

function renderSourceCardsHTML(sources) {
  if (!sources || !sources.length) return '';
  var html = '<div class="source-cards-container">';
  html += '<div class="source-cards-header">';
  html += '<svg class="source-cards-header-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="14" height="14"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>';
  html += '<span>Sources</span></div>';
  html += '<div class="source-cards-grid">';
  for (var i = 0; i < sources.length; i++) {
    var s = sources[i];
    var domain = s.domain || (s.url ? s.url.replace(/^https?:\/\//, '').split('/')[0].replace('www.', '') : 'web');
    html += '<a href="' + s.url + '" target="_blank" rel="noopener noreferrer" class="source-card">';
    html += '<div class="source-card-top"><span class="source-card-domain">' + domain + '</span>';
    html += '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="12" height="12"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg></div>';
    html += '<div class="source-card-title">' + (s.title || '') + '</div>';
    if (s.snippet) {
      html += '<div class="source-card-snippet">' + s.snippet + '</div>';
    }
    html += '</a>';
  }
  html += '</div></div>';
  return html;
}

function setMode(value) {
  currentMode = value;

  document.querySelectorAll('.mode-menu-trigger').forEach(function (t) {
    t.innerHTML = MODE_ICONS[value];
    t.setAttribute('aria-label', 'Mode: ' + MODE_LABELS[value]);
  });

  document.querySelectorAll('.mode-menu-item').forEach(function (item) {
    var isActive = item.dataset.mode === value;
    item.classList.toggle('active', isActive);
    item.setAttribute('aria-checked', isActive ? 'true' : 'false');
  });

  updateSuggestionsVisibility();
  if (_skipInitSound) { _skipInitSound = false; } else { playNavSound(); }
}

/* ── Navigation sound ── */
var _audioCtx = null;
function playNavSound() {
  try {
    if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    var osc = _audioCtx.createOscillator();
    var gain = _audioCtx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(420, _audioCtx.currentTime);
    osc.frequency.linearRampToValueAtTime(640, _audioCtx.currentTime + 0.07);
    gain.gain.setValueAtTime(0.06, _audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, _audioCtx.currentTime + 0.12);
    osc.connect(gain);
    gain.connect(_audioCtx.destination);
    osc.start(_audioCtx.currentTime);
    osc.stop(_audioCtx.currentTime + 0.12);
  } catch (e) {}
}

var overflowParents = [];

function findOverflowParent(el) {
  while (el) {
    var style = getComputedStyle(el);
    if (style.overflow === 'hidden' || style.overflowX === 'hidden' || style.overflowY === 'hidden') {
      return el;
    }
    el = el.parentElement;
  }
  return null;
}

function setOverflowVisible(menuEl, enable) {
  if (enable) {
    var parent = findOverflowParent(menuEl);
    if (parent) {
      overflowParents.push({ el: parent, overflow: parent.style.overflow || '' });
      parent.style.overflow = 'visible';
    }
  } else {
    overflowParents.forEach(function (entry) {
      entry.el.style.overflow = entry.overflow;
    });
    overflowParents = [];
  }
}

function setupModeMenu(menuId) {
  var menu = document.getElementById(menuId);
  if (!menu) return;
  var trigger = menu.querySelector('.mode-menu-trigger');
  var dropdown = menu.querySelector('.mode-menu-dropdown');

  trigger.addEventListener('click', function (e) {
    e.stopPropagation();
    var isOpen = dropdown.style.display !== 'none';
    document.querySelectorAll('.mode-menu-dropdown').forEach(function (d) { d.style.display = 'none'; });
    document.querySelectorAll('.mode-menu-trigger').forEach(function (t) { t.setAttribute('aria-expanded', 'false'); });
    setOverflowVisible(null, false);
    if (!isOpen) {
      dropdown.style.display = 'flex';
      trigger.setAttribute('aria-expanded', 'true');
      setOverflowVisible(menu, true);
    }
  });

  menu.querySelectorAll('.mode-menu-item').forEach(function (item) {
    item.addEventListener('click', function () {
      setMode(item.dataset.mode);
      dropdown.style.display = 'none';
      trigger.setAttribute('aria-expanded', 'false');
      setOverflowVisible(null, false);
    });
  });
}

/* ── Model Menu ── */

function setModel(value) {
  currentModel = value;
  var label = MODEL_LABELS[value] || value;

  document.querySelectorAll('.model-menu-trigger').forEach(function (t) {
    t.setAttribute('aria-label', 'Model: ' + label);
  });
  document.querySelectorAll('.model-menu-trigger-label').forEach(function (el) {
    el.textContent = label;
  });
  document.querySelectorAll('.model-menu-item').forEach(function (item) {
    var isActive = item.dataset.model === value;
    item.classList.toggle('active', isActive);
    item.setAttribute('aria-checked', isActive ? 'true' : 'false');
  });
}

function setupModelMenu(menuId) {
  var menu = document.getElementById(menuId);
  if (!menu) return;
  var trigger = menu.querySelector('.model-menu-trigger');
  var dropdown = menu.querySelector('.model-menu-dropdown');

  trigger.addEventListener('click', function (e) {
    e.stopPropagation();
    var isOpen = dropdown.style.display !== 'none';
    document.querySelectorAll('.model-menu-dropdown').forEach(function (d) { d.style.display = 'none'; });
    document.querySelectorAll('.model-menu-trigger').forEach(function (t) { t.setAttribute('aria-expanded', 'false'); });
    setOverflowVisible(null, false);
    if (!isOpen) {
      dropdown.style.display = 'flex';
      trigger.setAttribute('aria-expanded', 'true');
      setOverflowVisible(menu, true);
    }
  });

  menu.querySelectorAll('.model-menu-item').forEach(function (item) {
    item.addEventListener('click', function () {
      setModel(item.dataset.model);
      dropdown.style.display = 'none';
      trigger.setAttribute('aria-expanded', 'false');
      setOverflowVisible(null, false);
    });
  });
}


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

/* ── Results ── */

function clearResults() {
  const scroll = document.getElementById('conversation-scroll');
  scroll.innerHTML = '';
  document.getElementById('image-container').style.display = 'none';
}

function showError(msg) {
  var scroll = document.getElementById('conversation-scroll');
  var loading = scroll.querySelector('.loading-dots');
  if (loading) {
    var container = loading.closest('.conversation-loading');
    if (container) {
      container.outerHTML = '<div class="response-container"><em>Error: ' + msg + '</em></div>';
    } else {
      container = loading.closest('.response-container');
      if (container) container.innerHTML = '<em>Error: ' + msg + '</em>';
    }
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
  /* Reset textarea height */
  input.style.height = 'auto';
  if (convInput) convInput.style.height = 'auto';

  var attData = pendingAttachments.length > 0
    ? pendingAttachments.map(function (a) { return { id: a.id, filename: a.filename, mime_type: a.mime_type, size: a.size }; })
    : null;
  clearPendingAttachments();

  var mode = currentMode;

  switchToConversation();

  clearResults();

  /* Show loading immediately */
  var scroll = document.getElementById('conversation-scroll');
  scroll.innerHTML = '<div class="conversation-loading"><div class="loading-dots" role="status" aria-label="Generating"><span class="loading-dots-label">Generating</span><div class="loading-dots-track" style="gap:5px"><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.2s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.4s"></span></div></div></div>';

  var createPromise;
  if (activeConversationId) {
    /* Existing conversation — add user message now */
    var payload = cloneConversation(activeConversationData);
    var userMsg = { role: 'user', content: prompt, timestamp: new Date().toISOString() };
    if (attData) userMsg.attachments = attData;
    payload.messages.push(userMsg);
    payload.metadata = payload.metadata || {};
    payload.metadata.status = 'pending';
    activeConversationData = payload;
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
    activeConversationData = {
      title: title,
      mode: mode,
      model: resolveModel(),
      messages: [userMsg],
      metadata: { status: 'pending' },
    };
    createPromise = fetch('/api/conversations', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title,
        mode: mode,
        model: resolveModel(),
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

  /* Show the submitted message without waiting for the persistence request. */
  renderConversation();
  scroll = document.getElementById('conversation-scroll');
  scroll.insertAdjacentHTML('beforeend', '<div class="conversation-loading"><div class="loading-dots" role="status" aria-label="Generating"><span class="loading-dots-label">Generating</span><div class="loading-dots-track" style="gap:5px"><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.2s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.4s"></span></div></div></div>');

  createPromise.then(function () {
    renderConversation();
    /* Append loading indicator */
    var scroll = document.getElementById('conversation-scroll');
    scroll.insertAdjacentHTML('beforeend', '<div class="conversation-loading"><div class="loading-dots" role="status" aria-label="Generating"><span class="loading-dots-label">Generating</span><div class="loading-dots-track" style="gap:5px"><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.2s"></span><span class="loading-dots-dot" style="width:6px;height:6px;animation-delay:0.4s"></span></div></div></div>');
    if (currentMode === 'images') {
      handleImageGen(prompt);
    } else {
      var genStyle = currentMode === 'thinking' ? 'thinking' : currentMode === 'web' ? 'url-context' : 'normal';
      handleTextGen(prompt, genStyle);
    }
  }).catch(function (e) {
    showError(e.message);
  });
}

function handleTextGen(prompt, style) {
  const isSearchMode = ['search', 'auto', 'code', 'web'].includes(currentMode) || style === 'search' || style === 'url-context';
  const endpoint =
    style === 'thinking' ? '/api/generate-with-thinking'
    : isSearchMode ? '/api/search'
    : '/api/generate';

  /* Include full conversation history for context */
  var messages = activeConversationData ? activeConversationData.messages : null;
  var firstModel = resolveModel();
  var usedFallback = false;
  var startTime = performance.now();

  function doRequest(model) {
    return fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: prompt, messages: messages, model: model, mode: currentMode }),
    });
  }

  function handleResponse(r, model) {
    if (!r.ok) {
      if ((r.status === 429 || r.status === 503) && currentModel === 'auto' && !usedFallback) {
        var retryAfter = r.headers.get('Retry-After');
        markModelUnavailable(model, retryAfter ? parseInt(retryAfter, 10) : undefined);
        var fallbackModel = resolveModel();
        if (fallbackModel && fallbackModel !== model) {
          usedFallback = true;
          return doRequest(fallbackModel).then(function (r2) {
            if (!r2.ok) throw new Error('Request failed');
            return r2.json().then(function (data) { return { data: data, model: fallbackModel }; });
          });
        }
      }
      throw new Error('Request failed');
    }
    return r.json().then(function (data) { return { data: data, model: model }; });
  }

  doRequest(firstModel).then(function (r) { return handleResponse(r, firstModel); })
    .then(function (result) {
      var data = result.data;
      var actualModel = result.model;
      var elapsed = Math.round((performance.now() - startTime) / 1000);
      var thinkingText = data.thinking_summary ? data.thinking_summary.map(function(s) { return s.replace(/[,;:\s-]+$/, ''); }).join('\n') : '';
      /* Optimistically update local state */
      var msg = {
        role: 'assistant',
        content: data.response || '',
        thinking: thinkingText || undefined,
        sources: data.sources || undefined,
        search_steps: data.search_steps || undefined,
        timestamp: new Date().toISOString(),
        model: actualModel,
        ...(style === 'thinking' && thinkingText ? { thinking_duration_sec: elapsed } : {}),
      };
      if (usedFallback) {
        msg.metadata = { autoFallback: true, requestedModel: 'auto', resolvedModel: firstModel, fallbackModel: actualModel };
      }
      activeConversationData.messages.push(msg);
      activeConversationData.metadata = activeConversationData.metadata || {};
      activeConversationData.metadata.status = 'complete';
      renderConversation();
      persistConversation();
    })
    .catch(function (e) {
      showError(e.message);
      setConversationFailed();
    });
}

function handleImageGen(prompt) {
  var actualModel = resolveModel();
  fetch('/api/generate-image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, model: actualModel }),
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
        model: actualModel,
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

/* ── Disclaimer Dialog ── */

function showDisclaimerDialog() {
  document.getElementById('disclaimer-dialog').style.display = '';
  document.getElementById('disclaimer-overlay').style.display = '';
}

function hideDisclaimerDialog() {
  document.getElementById('disclaimer-dialog').style.display = 'none';
  document.getElementById('disclaimer-overlay').style.display = 'none';
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

var ACCENT_PRESETS = [
  { color: '#24d455', hover: '#1fbf4a' },
  { color: '#3b82f6', hover: '#2563eb' },
  { color: '#8b5cf6', hover: '#7c3aed' },
  { color: '#f59e0b', hover: '#d97706' },
  { color: '#ec4899', hover: '#db2777' },
  { color: '#14b8a6', hover: '#0d9488' },
  { color: '#9ca3af', hover: '#6b7280' },
];

function setAccentColor(color) {
  var preset = null;
  for (var i = 0; i < ACCENT_PRESETS.length; i++) {
    if (ACCENT_PRESETS[i].color === color) { preset = ACCENT_PRESETS[i]; break; }
  }
  if (!preset) preset = ACCENT_PRESETS[0];
  document.documentElement.style.setProperty('--accent', preset.color);
  document.documentElement.style.setProperty('--accent-hover', preset.hover);
  try { localStorage.setItem('accent', preset.color); } catch (e) {}
}

var _sidebarLoading = false;

function fetchConversations() {
  _sidebarLoading = true;
  renderConversationList();
  fetch('/api/conversations')
    .then(function (r) {
      if (!r.ok) throw new Error('Failed to fetch conversations');
      return r.json();
    })
    .then(function (list) {
      sidebarConversations = list || [];
      _sidebarLoading = false;
      renderConversationList();
    })
    .catch(function () {
      sidebarConversations = [];
      _sidebarLoading = false;
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
  var loading = document.getElementById('sidebar-loading');
  if (!list) return;

  list.innerHTML = '';
  if (loading) loading.style.display = _sidebarLoading ? '' : 'none';

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
        document.getElementById('sidebar-delete-overlay').style.display = '';
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
        setMode(conv.mode);
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
  document.getElementById('sidebar-delete-overlay').style.display = 'none';
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
  document.getElementById('sidebar-delete-overlay').style.display = 'none';
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
      if (m.model) {
        var modelLabel = MODEL_LABELS[m.model] || m.model;
        if (m.metadata && m.metadata.autoFallback) {
          html += '<div class="response-model response-model--fallback">' + escapeHtml(modelLabel) + ' <span class="response-model-badge">Auto fallback</span></div>';
        } else {
          html += '<div class="response-model">' + escapeHtml(modelLabel) + '</div>';
        }
      }
      if (m.thinking) {
        var cleanedThinking = m.thinking.replace(/^(My thought process:|I need to:|Let's think:|Let's think about|Let's start by|Let me think|I'll think|I should start|First,|First:|Okay,|Alright,|So,)\s*/i, '');
        var newlineCount = (cleanedThinking.match(/\n/g) || []).length;
        var isShort = newlineCount <= 1;
        if (isShort) {
          html += '<div class="thinking-container">';
          html += '<div class="thinking-content">' + cleanedThinking + '</div>';
          html += '</div>';
        } else {
          var durationLabel = 'Show reasoning';
          if (m.thinking_duration_sec != null) {
            durationLabel = 'Thought for ' + m.thinking_duration_sec + 's';
          }
          html += '<div class="thinking-container">';
          html += '<button class="thinking-toggle" type="button" aria-expanded="false">';
          html += '<span class="thinking-toggle-icon">&#9654;</span> ' + durationLabel;
          html += '</button>';
          html += '<div class="thinking-content" style="display:none">' + cleanedThinking + '</div>';
          html += '</div>';
        }
      }
      html += '<div class="response-container">' + (m.content ? marked.parse(m.content) : '') + '</div>';
      if (m.sources && m.sources.length > 0) {
        html += renderSourceCardsHTML(m.sources);
      }
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

  document.querySelectorAll('.chip').forEach((c) => (c.style.display = 'none'));

  let selector = '.tab-canvas';
  if (currentMode === 'images') selector = '.tab-image';
  else if (currentMode === 'thinking') selector = '.tab-thinking';
  else if (currentMode === 'web') selector = '.tab-url';

  document.querySelectorAll(selector).forEach((c) => (c.style.display = 'inline-block'));
}

/* ── Init ── */

document.addEventListener('DOMContentLoaded', function () {
  const input = getActiveInput();
  const submitBtn = document.getElementById('submit-button');
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

  /* ── Mode menu setup ── */
  setupModeMenu('landing-mode-menu');
  setupModeMenu('conv-mode-menu');
  _skipInitSound = true;
  setMode('canvas');

  /* ── Model menu setup ── */
  setupModelMenu('landing-model-menu');
  setupModelMenu('conv-model-menu');
  setModel('auto');

  /* Outside click to close mode/model dropdowns */
  document.addEventListener('mousedown', function (e) {
    if (!e.target.closest('.mode-menu')) {
      document.querySelectorAll('.mode-menu-dropdown').forEach(function (d) { d.style.display = 'none'; });
      document.querySelectorAll('.mode-menu-trigger').forEach(function (t) { t.setAttribute('aria-expanded', 'false'); });
      setOverflowVisible(null, false);
    }
    if (!e.target.closest('.model-menu')) {
      document.querySelectorAll('.model-menu-dropdown').forEach(function (d) { d.style.display = 'none'; });
      document.querySelectorAll('.model-menu-trigger').forEach(function (t) { t.setAttribute('aria-expanded', 'false'); });
      setOverflowVisible(null, false);
    }
  });

  /* Submit handlers */
  function resizeComposerInput(composerInput) {
    composerInput.style.height = 'auto';
    var height = Math.min(composerInput.scrollHeight, 120);
    composerInput.style.height = height + 'px';
    composerInput.style.overflowY = composerInput.scrollHeight > 120 ? 'auto' : 'hidden';
  }

  function onInputChange() {
    const val = input.value.trim();
    if (submitBtn) {
      submitBtn.disabled = !val;
      if (val) submitBtn.classList.add('has-text');
      else submitBtn.classList.remove('has-text');
    }
    updateSuggestionsVisibility();
    resizeComposerInput(input);

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
    resizeComposerInput(convInput);
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

  /* Chip clicks */
  document.querySelectorAll('.chip').forEach((chip) => {
    chip.addEventListener('click', function () {
      input.value = this.dataset.text;
      input.focus();
      input.dispatchEvent(new Event('input'));
    });
  });

  /* Accent color picker */
  var savedAccent = null;
  try { savedAccent = localStorage.getItem('accent'); } catch (e) {}
  if (savedAccent) setAccentColor(savedAccent);

  var accentBtn = document.getElementById('accent-picker-btn');
  var accentPopup = document.getElementById('accent-picker-popup');
  if (accentBtn && accentPopup) {
    /* Render swatches */
    var swatchHtml = '';
    var currentAccent = savedAccent || '#24d455';
    for (var ai = 0; ai < ACCENT_PRESETS.length; ai++) {
      var p = ACCENT_PRESETS[ai];
      var active = p.color === currentAccent ? ' active' : '';
      swatchHtml += '<button class="accent-swatch' + active + '" style="background:' + p.color + '" data-accent="' + p.color + '" aria-label="Set accent to ' + p.color + '" type="button"></button>';
    }
    accentPopup.innerHTML = swatchHtml;

    accentBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var isOpen = accentPopup.style.display !== 'none';
      accentPopup.style.display = isOpen ? 'none' : 'flex';
    });

    accentPopup.addEventListener('click', function (e) {
      var swatch = e.target.closest('.accent-swatch');
      if (!swatch) return;
      setAccentColor(swatch.getAttribute('data-accent'));
      accentPopup.style.display = 'none';
      /* Update active state */
      accentPopup.querySelectorAll('.accent-swatch').forEach(function (s) { s.classList.remove('active'); });
      swatch.classList.add('active');
    });

    /* Close on outside click */
    document.addEventListener('mousedown', function (e) {
      if (accentPopup.style.display === 'none') return;
      if (!e.target.closest('#accent-picker-btn') && !e.target.closest('#accent-picker-popup')) {
        accentPopup.style.display = 'none';
      }
    });
  }

  /* ── Rotating placeholder ── */
  var PLACEHOLDERS = ['Ask anything...', 'Debug a bug...', 'Send a message...', 'Fix an issue...', 'Explore a topic...'];
  var placeholderIdx = Math.floor(Math.random() * PLACEHOLDERS.length);
  setInterval(function () {
    var landingInput = document.getElementById('landing-input');
    var convInput = document.getElementById('conversation-input');
    [landingInput, convInput].forEach(function (el) {
      if (el) el.classList.add('placeholder-hidden');
    });
    setTimeout(function () {
      placeholderIdx = (placeholderIdx + 1) % PLACEHOLDERS.length;
      var p = PLACEHOLDERS[placeholderIdx];
      if (landingInput) { landingInput.placeholder = p; landingInput.classList.remove('placeholder-hidden'); }
      if (convInput) { convInput.placeholder = p; convInput.classList.remove('placeholder-hidden'); }
    }, 800);
  }, 8000);

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
  const close = document.getElementById('sidebar-close');

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
    document.getElementById('sidebar-delete-overlay').style.display = 'none';
    renderConversationList();
  }

  if (menuToggle) menuToggle.addEventListener('click', openMenu);
  if (close) close.addEventListener('click', closeMenu);
  if (overlay) overlay.addEventListener('click', closeMenu);

  /* Footer links toggle */
  var footerToggle = document.getElementById('sidebar-footer-toggle');
  var footerLinks = document.getElementById('sidebar-footer-links');
  if (footerToggle && footerLinks) {
    footerToggle.addEventListener('click', function () {
      var isVisible = footerLinks.style.display !== 'none';
      footerLinks.style.display = isVisible ? 'none' : 'flex';
    });
  }

  /* Delete dialog buttons */
  document.getElementById('sidebar-delete-confirm').addEventListener('click', confirmDeleteConversation);
  document.getElementById('sidebar-delete-cancel').addEventListener('click', cancelDeleteConversation);
  document.getElementById('sidebar-delete-overlay').addEventListener('click', cancelDeleteConversation);

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

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'p') {
      e.preventDefault();
    }
  });

  /* Disclaimer dialog */
  var disclaimerShown = false;
  try { disclaimerShown = !!localStorage.getItem('alma_disclaimer_shown'); } catch (e) {}
  if (!disclaimerShown) {
    try { localStorage.setItem('alma_disclaimer_shown', '1'); } catch (e) {}
    showDisclaimerDialog();
  }
  const disclaimerClose = document.getElementById('disclaimer-close');
  const disclaimerOverlay = document.getElementById('disclaimer-overlay');
  const disclaimerHint = document.getElementById('landing-footer-hint');
  if (disclaimerClose) disclaimerClose.addEventListener('click', hideDisclaimerDialog);
  if (disclaimerOverlay) disclaimerOverlay.addEventListener('click', hideDisclaimerDialog);
  if (disclaimerHint) disclaimerHint.addEventListener('click', showDisclaimerDialog);

  /* Update footer hint visibility on layout change */
  function updateFooterHint() {
    var hint = document.getElementById('landing-footer-hint');
    var landing = document.getElementById('landing');
    if (hint && landing) {
      hint.style.display = landing.style.display !== 'none' ? '' : 'none';
    }
  }
  updateFooterHint();
  /* Override switchToLanding/switchToConversation to update hint */
  var _origSwitchToLanding = switchToLanding;
  var _origSwitchToConversation = switchToConversation;
  switchToLanding = function () { _origSwitchToLanding(); updateFooterHint(); };
  switchToConversation = function () { _origSwitchToConversation(); updateFooterHint(); };

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
        if (conv.mode) {
          setMode(conv.mode);
        }
        selectConversation(storedId);
      })
      .catch(function () {
        try { localStorage.removeItem('alma_active_conversation'); } catch (e) {}
      });
  }

  /* Thinking toggle */
  document.getElementById('conversation-scroll').addEventListener('click', function (e) {
    var toggle = e.target.closest('.thinking-toggle');
    if (!toggle) return;
    var container = toggle.closest('.thinking-container');
    var content = container.querySelector('.thinking-content');
    var expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!expanded));
    content.style.display = expanded ? 'none' : 'block';
    toggle.querySelector('.thinking-toggle-icon').innerHTML = expanded ? '&#9654;' : '&#9660;';
  });

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
