(function () {
  function initializeNotesWidget(widget) {
    const source = widget.querySelector('[data-notes-source]');
    const plainEl = widget.querySelector('[data-notes-plain]');
    const markdownEl = widget.querySelector('[data-notes-markdown]');
    const toggleButton = widget.querySelector('[data-notes-toggle-button]');

    if (!source || !plainEl || !markdownEl || !toggleButton) {
      return;
    }

    // Initial mode: aria-pressed="true" means Markdown preview is currently shown.
    // Rely solely on the button state to avoid desync with hidden attributes.
    let isMarkdown = toggleButton.getAttribute('aria-pressed') === 'true';
    const readSource = () => {
      if (source.tagName === 'TEXTAREA') {
        return source.value || '';
      }
      return source.textContent || '';
    };

    const renderPlain = (text) => {
      plainEl.textContent = text;
    };

    const renderMarkdown = (text) => {
      if (window.marked) {
        markdownEl.innerHTML = window.marked.parse(text || '');
      } else {
        markdownEl.textContent = text;
      }
    };

    const syncContent = () => {
      const text = readSource();
      renderPlain(text);
      renderMarkdown(text);
    };

    const updateMode = () => {
      if (isMarkdown) {
        // Show Markdown, hide plain
        markdownEl.hidden = false;
        plainEl.hidden = true;
        // Button indicates the action (switch to Plain Text)
        toggleButton.textContent = 'Show Plain Text';
        toggleButton.setAttribute('aria-pressed', 'true');
      } else {
        // Show Plain, hide Markdown
        plainEl.hidden = false;
        markdownEl.hidden = true;
        // Button indicates the action (switch to Markdown)
        toggleButton.textContent = 'Show Markdown';
        toggleButton.setAttribute('aria-pressed', 'false');
      }
    };

    toggleButton.addEventListener('click', () => {
      isMarkdown = !isMarkdown;
      updateMode();
    });

    if (source.tagName === 'TEXTAREA' && !source.hasAttribute('hidden')) {
      source.addEventListener('input', syncContent);
    }

    syncContent();
    updateMode();
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-notes-widget]').forEach(initializeNotesWidget);
  });
})();
