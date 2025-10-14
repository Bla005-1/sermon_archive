(function () {
  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  function parseJSONScript(id) {
    const el = document.getElementById(id);
    if (!el) {
      return {};
    }
    try {
      return JSON.parse(el.textContent || '{}');
    } catch (err) {
      console.error('Failed to parse JSON script', err);
      return {};
    }
  }

  function renderMarkdown(text, target) {
    if (!target) {
      return;
    }
    if (window.marked) {
      target.innerHTML = window.marked.parse(text || '');
    } else {
      target.textContent = text || '';
    }
  }

  ready(function () {
    const form = document.querySelector('[data-verse-editor-form]');
    if (!form) {
      return;
    }

    const translationData = parseJSONScript('verse-translation-data');
    const translationSelect = form.querySelector('[data-translation-select]');
    const selectedTranslationInput = form.querySelector('[data-selected-translation]');
    const translationModeInput = form.querySelector('[data-translation-mode]');
    const verseText = form.querySelector('[data-verse-text]');
    const saveButton = form.querySelector('[data-save-button]');
    const addTranslationButton = form.querySelector('[data-add-translation]');
    const newTranslationField = form.querySelector('[data-new-translation-field]');
    const newTranslationInput = form.querySelector('[data-new-translation-input]');

    const noteEditor = form.querySelector('[data-note-editor]');
    const noteView = form.querySelector('[data-note-view]');
    const noteInput = form.querySelector('[data-note-input]');
    const notePreview = form.querySelector('[data-note-preview]');
    const noteDisplay = form.querySelector('[data-note-display]');
    const noteOriginalInput = form.querySelector('[data-note-original]');
    const noteEditButton = form.querySelector('[data-note-edit-button]');
    const noteCancelButton = form.querySelector('[data-note-cancel-button]');

    let initialVerseText = verseText ? verseText.getAttribute('data-initial-value') || '' : '';
    let initialNoteText = noteInput ? noteInput.getAttribute('data-initial-value') || '' : '';
    let isNewTranslation = false;

    function syncSaveState() {
      if (!saveButton) {
        return;
      }
      let dirty = false;
      if (verseText && !verseText.readOnly) {
        dirty = dirty || verseText.value !== initialVerseText;
      }
      if (noteInput && noteEditor && !noteEditor.hasAttribute('hidden')) {
        dirty = dirty || noteInput.value !== initialNoteText;
      }
      saveButton.disabled = !dirty;
      if (dirty) {
        saveButton.removeAttribute('aria-disabled');
      } else {
        saveButton.setAttribute('aria-disabled', 'true');
      }
    }

    function setTranslationMode(newMode) {
      if (!translationModeInput) {
        return;
      }
      translationModeInput.value = newMode;
    }

    function enterNewTranslationMode(initialName, initialText) {
      if (!verseText || !addTranslationButton || !newTranslationField) {
        return;
      }
      isNewTranslation = true;
      setTranslationMode('new');
      verseText.readOnly = false;
      const textValue = typeof initialText === 'string' ? initialText : '';
      verseText.value = textValue;
      verseText.setAttribute('data-initial-value', '');
      initialVerseText = '';
      if (newTranslationField) {
        newTranslationField.hidden = false;
      }
      if (newTranslationInput) {
        newTranslationInput.required = true;
        if (typeof initialName === 'string') {
          newTranslationInput.value = initialName;
        }
        newTranslationInput.focus();
      }
      if (translationSelect) {
        translationSelect.disabled = true;
        translationSelect.selectedIndex = -1;
      }
      if (selectedTranslationInput) {
        selectedTranslationInput.value = '';
      }
      addTranslationButton.textContent = 'Cancel New Translation';
      syncSaveState();
    }

    function exitNewTranslationMode() {
      isNewTranslation = false;
      setTranslationMode('existing');
      if (newTranslationField) {
        newTranslationField.hidden = true;
      }
      if (newTranslationInput) {
        newTranslationInput.required = false;
        newTranslationInput.value = '';
      }
      if (translationSelect) {
        translationSelect.disabled = false;
        const value = translationSelect.value || '';
        if (selectedTranslationInput) {
          selectedTranslationInput.value = value;
        }
        if (value && Object.prototype.hasOwnProperty.call(translationData, value)) {
          verseText.value = translationData[value];
        }
      }
      initialVerseText = verseText ? verseText.value : '';
      if (verseText) {
        verseText.setAttribute('data-initial-value', initialVerseText);
      }
      addTranslationButton.textContent = 'Add New Translation';
      syncSaveState();
    }

    if (addTranslationButton && !addTranslationButton.disabled) {
      addTranslationButton.addEventListener('click', function () {
        if (isNewTranslation) {
          exitNewTranslationMode();
        } else {
          enterNewTranslationMode('', '');
        }
      });
    }

    if (translationSelect) {
      translationSelect.addEventListener('change', function () {
        if (!verseText) {
          return;
        }
        const value = translationSelect.value;
        if (selectedTranslationInput) {
          selectedTranslationInput.value = value;
        }
        if (value && Object.prototype.hasOwnProperty.call(translationData, value)) {
          verseText.value = translationData[value];
        } else {
          verseText.value = '';
        }
        verseText.setAttribute('data-initial-value', verseText.value);
        initialVerseText = verseText.value;
        syncSaveState();
      });
    }

    if (verseText && !verseText.readOnly) {
      verseText.addEventListener('input', syncSaveState);
    }

    if (noteInput) {
      const updatePreview = function () {
        renderMarkdown(noteInput.value, notePreview);
        syncSaveState();
      };
      noteInput.addEventListener('input', updatePreview);
      updatePreview();
    }

    if (noteDisplay && noteOriginalInput) {
      renderMarkdown(noteOriginalInput.value || '', noteDisplay);
    }

    if (noteEditButton && noteEditor && noteView) {
      noteEditButton.addEventListener('click', function () {
        noteEditor.hidden = false;
        noteView.hidden = true;
        if (noteCancelButton) {
          noteCancelButton.hidden = false;
        }
        if (noteInput) {
          noteInput.focus();
        }
        syncSaveState();
      });
    }

    if (noteCancelButton && noteEditor && noteView && noteOriginalInput && noteInput) {
      noteCancelButton.addEventListener('click', function () {
        noteInput.value = noteOriginalInput.value || '';
        renderMarkdown(noteInput.value, notePreview);
        noteEditor.hidden = true;
        noteView.hidden = false;
        noteCancelButton.hidden = true;
        initialNoteText = noteInput.value;
        noteInput.setAttribute('data-initial-value', initialNoteText);
        syncSaveState();
      });
    }

    if (verseText && verseText.readOnly) {
      saveButton && (saveButton.disabled = true);
      saveButton && saveButton.setAttribute('aria-disabled', 'true');
    } else {
      syncSaveState();
    }

    if (translationSelect && translationSelect.value) {
      const current = translationSelect.value;
      if (selectedTranslationInput) {
        selectedTranslationInput.value = current;
      }
      if (verseText && Object.prototype.hasOwnProperty.call(translationData, current)) {
        verseText.value = translationData[current];
        verseText.setAttribute('data-initial-value', verseText.value);
        initialVerseText = verseText.value;
      }
    }

    const forceNewTranslation = form.getAttribute('data-force-new-translation') === 'true';
    if ((Object.keys(translationData).length === 0 || forceNewTranslation) && addTranslationButton && !addTranslationButton.disabled) {
      const initialName = newTranslationInput ? newTranslationInput.value : '';
      const initialText = verseText ? verseText.value : '';
      enterNewTranslationMode(initialName, initialText);
    }
  });
})();
