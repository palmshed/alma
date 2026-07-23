(function() {
  if (window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') return;

  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var storageKey = 'alma-design';
  var root = document.documentElement;
  var hideTimer = null;

  var designs = {
    previous: {
      label: 'Previous',
      notes: [],
      changes: [
        'Stronger borders',
        'Rounded code blocks',
        'Full width',
        'Card tables'
      ]
    },
    current: {
      label: 'Current',
      notes: [
        'Reduced visual weight',
        'Improved reading rhythm',
        'Simplified navigation',
        'Softer writing'
      ],
      changes: [
        'Softer borders',
        'Flatter code blocks',
        'Narrower measure',
        'Better mobile tables'
      ]
    }
  };

  function getDesign() {
    var url = new URL(window.location);
    var p = url.searchParams.get('design');
    if (p === 'previous' || p === 'current') return p;
    return sessionStorage.getItem(storageKey) || 'current';
  }

  function setDesign(v) {
    sessionStorage.setItem(storageKey, v);
    if (v === 'previous') {
      root.dataset.design = 'previous';
    } else {
      delete root.dataset.design;
    }
    updateUI(v);
  }

  function toggle() {
    var current = getDesign();
    setDesign(current === 'current' ? 'previous' : 'current');
  }

  function show() {
    var panel = document.getElementById('design-panel');
    var btn = document.getElementById('design-toggle');
    if (panel) panel.style.display = 'block';
    if (btn) btn.style.opacity = '0.65';
  }

  function hide() {
    var panel = document.getElementById('design-panel');
    var btn = document.getElementById('design-toggle');
    clearTimeout(hideTimer);
    if (panel) panel.style.display = 'none';
    if (btn) btn.style.opacity = '0.2';
  }

  function scheduleHide() {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, 200);
  }

  function updateUI(v) {
    var dot = document.getElementById('design-dot');
    var label = document.getElementById('design-label');
    var panel = document.getElementById('design-panel');
    if (dot) dot.textContent = v === 'current' ? '◉' : '○';
    if (label) label.textContent = designs[v].label;
    if (panel) {
      panel.innerHTML = '';
      var d = designs[v];

      var title = document.createElement('div');
      title.textContent = 'Design review';
      title.style.cssText = 'font-size:8px;color:#444;margin-bottom:6px;text-transform:uppercase;letter-spacing:.06em;';
      panel.appendChild(title);

      var state = document.createElement('div');
      state.textContent = d.label;
      state.style.cssText = 'font-size:11px;color:#999;font-weight:500;margin-bottom:8px;';
      panel.appendChild(state);

      if (d.notes.length) {
        var whyLabel = document.createElement('div');
        whyLabel.textContent = 'Why';
        whyLabel.style.cssText = 'font-size:8px;color:#444;margin-bottom:3px;text-transform:uppercase;letter-spacing:.06em;';
        panel.appendChild(whyLabel);
        for (var k = 0; k < d.notes.length; k++) {
          var note = document.createElement('div');
          note.textContent = d.notes[k];
          note.style.cssText = 'font-size:10px;color:#777;line-height:1.6;';
          panel.appendChild(note);
        }
        var spacer = document.createElement('div');
        spacer.style.cssText = 'height:6px;';
        panel.appendChild(spacer);
      }

      var changesLabel = document.createElement('div');
      changesLabel.textContent = 'Changes';
      changesLabel.style.cssText = 'font-size:8px;color:#444;margin-bottom:3px;text-transform:uppercase;letter-spacing:.06em;';
      panel.appendChild(changesLabel);
      for (var j = 0; j < d.changes.length; j++) {
        var item = document.createElement('div');
        item.textContent = '· ' + d.changes[j];
        item.style.cssText = 'font-size:10px;color:#777;line-height:1.7;';
        panel.appendChild(item);
      }
    }
  }

  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      hide();
      return;
    }
    if (e.key === 'd' || e.key === 'D') {
      if (e.metaKey && e.shiftKey) {
        e.preventDefault();
        toggle();
        show();
      } else if (!e.metaKey && !e.ctrlKey && !e.altKey) {
        var tag = e.target && e.target.tagName;
        if (tag !== 'INPUT' && tag !== 'TEXTAREA' && !e.target.isContentEditable) {
          e.preventDefault();
          toggle();
          show();
        }
      }
    }
  });

  setDesign(getDesign());

  var wrapper = document.createElement('div');
  wrapper.id = 'design-wrapper';
  wrapper.style.cssText = 'position:fixed;bottom:12px;right:12px;z-index:9999;font-family:system-ui,-apple-system,sans-serif;user-select:none;';

  var toggleBtn = document.createElement('button');
  toggleBtn.id = 'design-toggle';
  toggleBtn.style.cssText = 'display:flex;align-items:center;gap:3px;background:rgba(10,10,10,0.6);border:none;border-radius:2px;padding:3px 7px;cursor:pointer;font-size:10px;color:#666;line-height:1;opacity:0.2;';
  toggleBtn.addEventListener('focus', function() { show(); });
  toggleBtn.addEventListener('blur', function() { scheduleHide(); });

  var dot = document.createElement('span');
  dot.id = 'design-dot';
  dot.textContent = '◉';
  dot.style.cssText = 'font-size:7px;color:#484;margin-right:1px;';
  toggleBtn.appendChild(dot);

  var label = document.createElement('span');
  label.id = 'design-label';
  label.textContent = 'Current';
  toggleBtn.appendChild(label);

  var hint = document.createElement('span');
  hint.textContent = 'D';
  hint.style.cssText = 'font-size:8px;color:#555;margin-left:2px;';
  toggleBtn.appendChild(hint);

  toggleBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    toggle();
    toggleBtn.focus();
    show();
  });

  wrapper.appendChild(toggleBtn);

  var panel = document.createElement('div');
  panel.id = 'design-panel';
  panel.style.cssText = 'display:none;margin-top:4px;background:rgba(10,10,10,0.8);border:none;padding:8px;width:150px;';
  wrapper.appendChild(panel);

  wrapper.addEventListener('mouseenter', function() { clearTimeout(hideTimer); show(); });
  wrapper.addEventListener('mouseleave', scheduleHide);

  document.body.appendChild(wrapper);
  updateUI(getDesign());
})();
