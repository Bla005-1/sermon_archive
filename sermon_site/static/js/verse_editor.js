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

  const SUPERSCRIPT_PATTERN = /[\u00B2\u00B3\u00B9\u2070-\u209F]/g;

  function normalizeVerseText(value) {
    return (value || '').replace(SUPERSCRIPT_PATTERN, '').trim();
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
    const translationSelectField = form.querySelector('[data-translation-select-field]');
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
    const noteEmptyHint = form.querySelector('[data-note-empty-hint]');

    const baseVerseReadOnly = verseText ? verseText.readOnly : false;
    const baseVerseDisabled = verseText ? verseText.disabled : false;
    let initialExistingText = normalizeVerseText(
      verseText ? verseText.getAttribute('data-initial-value') || verseText.value || '' : ''
    );
    let initialNewTranslationText = '';
    let initialNoteText = noteInput ? noteInput.getAttribute('data-initial-value') || '' : '';
    let isNewTranslation = false;
    let lastSelectedTranslation = translationSelect ? translationSelect.value || '' : '';

    function resolveExistingBaseline() {
      const activeValue =
        translationSelect && translationSelect.value
          ? translationSelect.value
          : lastSelectedTranslation;
      if (activeValue && Object.prototype.hasOwnProperty.call(translationData, activeValue)) {
        return translationData[activeValue];
      }
      if (verseText) {
        const stored = verseText.getAttribute('data-initial-value');
        if (typeof stored === 'string') {
          return stored;
        }
        return verseText.value || '';
      }
      return '';
    }

    function syncSaveState() {
      if (!saveButton) {
        return;
      }
      let dirty = false;
      if (verseText && !verseText.readOnly && !verseText.disabled) {
        const baseline = isNewTranslation ? initialNewTranslationText : initialExistingText;
        dirty = normalizeVerseText(verseText.value) !== baseline;
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
      if (!addTranslationButton || !newTranslationField || !verseText) {
        return;
      }
      isNewTranslation = true;
      setTranslationMode('new');
      if (translationSelectField) {
        translationSelectField.hidden = true;
      }
      if (translationSelect) {
        lastSelectedTranslation = translationSelect.value || '';
        translationSelect.disabled = true;
        translationSelect.value = '';
        translationSelect.selectedIndex = -1;
      }
      if (selectedTranslationInput) {
        selectedTranslationInput.value = '';
      }
      newTranslationField.hidden = false;
      if (newTranslationInput) {
        newTranslationInput.required = true;
        newTranslationInput.value = typeof initialName === 'string' ? initialName : '';
        newTranslationInput.focus();
      } else {
        verseText.focus();
      }
      const textValue = typeof initialText === 'string' ? initialText : '';
      verseText.disabled = false;
      verseText.readOnly = false;
      verseText.value = textValue;
      verseText.setAttribute('data-initial-value', textValue);
      initialNewTranslationText = normalizeVerseText(textValue);
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
      if (translationSelectField) {
        translationSelectField.hidden = false;
      }
      if (translationSelect) {
        translationSelect.disabled = false;
        if (lastSelectedTranslation) {
          translationSelect.value = lastSelectedTranslation;
        } else if (translationSelect.options && translationSelect.options.length > 0) {
          translationSelect.selectedIndex = 0;
          lastSelectedTranslation = translationSelect.value || '';
        }
        const value = translationSelect.value || '';
        if (selectedTranslationInput) {
          selectedTranslationInput.value = value;
        }
      }
      const baseline = resolveExistingBaseline();
      if (verseText) {
        verseText.disabled = baseVerseDisabled;
        verseText.readOnly = baseVerseReadOnly;
        verseText.value = baseline;
        verseText.setAttribute('data-initial-value', baseline);
        initialExistingText = normalizeVerseText(baseline);
      }
      initialNewTranslationText = '';
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

    if (translationSelect && verseText) {
      translationSelect.addEventListener('change', function () {
        const value = translationSelect.value;
        if (selectedTranslationInput) {
          selectedTranslationInput.value = value;
        }
        let nextValue = '';
        if (value && Object.prototype.hasOwnProperty.call(translationData, value)) {
          nextValue = translationData[value];
        }
        verseText.value = nextValue;
        verseText.setAttribute('data-initial-value', nextValue);
        initialExistingText = normalizeVerseText(nextValue);
        lastSelectedTranslation = value;
        syncSaveState();
      });
    }

    if (verseText) {
      verseText.addEventListener('input', function () {
        syncSaveState();
      });
    }

    if (noteInput) {
      const updatePreview = function () {
        renderMarkdown(noteInput.value, notePreview);
        if (noteEmptyHint) {
          noteEmptyHint.hidden = !!noteInput.value.trim();
        }
        syncSaveState();
      };
      noteInput.addEventListener('input', updatePreview);
      updatePreview();
    }

    if (noteDisplay && noteOriginalInput) {
      const originalText = noteOriginalInput.value || '';
      renderMarkdown(originalText, noteDisplay);
      noteDisplay.hidden = !originalText.trim();
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
        if (noteEmptyHint) {
          noteEmptyHint.hidden = !!noteInput.value.trim();
        }
        if (noteDisplay) {
          noteDisplay.hidden = !noteInput.value.trim();
          renderMarkdown(noteInput.value, noteDisplay);
        }
        syncSaveState();
      });
    }

    if (verseText && verseText.readOnly) {
      if (saveButton) {
        saveButton.disabled = true;
        saveButton.setAttribute('aria-disabled', 'true');
      }
    } else {
      syncSaveState();
    }

    if (translationSelect && translationSelect.value) {
      const current = translationSelect.value;
      if (selectedTranslationInput) {
        selectedTranslationInput.value = current;
      }
      if (verseText && Object.prototype.hasOwnProperty.call(translationData, current)) {
        const textValue = translationData[current];
        verseText.value = textValue;
        verseText.setAttribute('data-initial-value', textValue);
        initialExistingText = normalizeVerseText(textValue);
      }
    }

    const forceNewTranslation = form.getAttribute('data-force-new-translation') === 'true';
    if ((Object.keys(translationData).length === 0 || forceNewTranslation) && addTranslationButton && !addTranslationButton.disabled) {
      const initialName = newTranslationInput ? newTranslationInput.value : '';
      enterNewTranslationMode(initialName, '');
    }
  });
})();
