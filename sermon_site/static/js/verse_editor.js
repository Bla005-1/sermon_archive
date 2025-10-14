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
    const existingTranslationField = form.querySelector('[data-existing-translation-field]');
    const newTranslationTextField = form.querySelector('[data-new-translation-text]');
    const existingVerseText = form.querySelector('[data-verse-text-existing]');
    const newVerseText = form.querySelector('[data-verse-text-new]');
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

    let initialVerseText = {
      existing: normalizeVerseText(
        existingVerseText
          ? existingVerseText.getAttribute('data-initial-value') || existingVerseText.value || ''
          : ''
      ),
      new: normalizeVerseText(
        newVerseText ? newVerseText.getAttribute('data-initial-value') || newVerseText.value || '' : ''
      ),
    };
    let initialNoteText = noteInput ? noteInput.getAttribute('data-initial-value') || '' : '';
    let isNewTranslation = false;
    let lastSelectedTranslation = translationSelect ? translationSelect.value || '' : '';

    function getActiveVerseKey() {
      return isNewTranslation ? 'new' : 'existing';
    }

    function getActiveVerseElement() {
      return isNewTranslation ? newVerseText : existingVerseText;
    }

    function setInitialVerseTextValue(key, value) {
      initialVerseText[key] = normalizeVerseText(value || '');
    }

    function resolveExistingBaseline() {
      if (
        translationSelect &&
        translationSelect.value &&
        Object.prototype.hasOwnProperty.call(translationData, translationSelect.value)
      ) {
        return translationData[translationSelect.value];
      }
      if (
        lastSelectedTranslation &&
        Object.prototype.hasOwnProperty.call(translationData, lastSelectedTranslation)
      ) {
        return translationData[lastSelectedTranslation];
      }
      if (existingVerseText) {
        const currentValue = existingVerseText.value || '';
        if (currentValue) {
          return currentValue;
        }
        const stored = existingVerseText.getAttribute('data-initial-value');
        if (typeof stored === 'string') {
          return stored;
        }
        return existingVerseText.value || '';
      }
      return '';
    }

    function syncSaveState() {
      if (!saveButton) {
        return;
      }
      let dirty = false;
      const activeVerse = getActiveVerseElement();
      const activeKey = getActiveVerseKey();
      if (activeVerse && !activeVerse.readOnly && !activeVerse.disabled) {
        dirty =
          dirty || normalizeVerseText(activeVerse.value) !== initialVerseText[activeKey];
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
      if (!addTranslationButton || !newTranslationField || !newVerseText) {
        return;
      }
      isNewTranslation = true;
      setTranslationMode('new');
      if (existingTranslationField) {
        existingTranslationField.hidden = true;
      }
      if (existingVerseText) {
        existingVerseText.disabled = true;
      }
      if (newTranslationTextField) {
        newTranslationTextField.hidden = false;
      }
      const textValue = typeof initialText === 'string' ? initialText : '';
      newVerseText.disabled = false;
      newVerseText.readOnly = false;
      newVerseText.value = textValue;
      newVerseText.setAttribute('data-initial-value', textValue);
      setInitialVerseTextValue('new', '');
      newTranslationField.hidden = false;
      if (newTranslationInput) {
        newTranslationInput.required = true;
        if (typeof initialName === 'string') {
          newTranslationInput.value = initialName;
        }
        newTranslationInput.focus();
      }
      if (translationSelect) {
        lastSelectedTranslation = translationSelect.value || '';
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
      if (newTranslationTextField) {
        newTranslationTextField.hidden = true;
      }
      if (newVerseText) {
        newVerseText.disabled = true;
        newVerseText.value = '';
        newVerseText.setAttribute('data-initial-value', '');
        setInitialVerseTextValue('new', '');
      }
      if (existingTranslationField) {
        existingTranslationField.hidden = false;
      }
      const baseline = resolveExistingBaseline();
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
      if (existingVerseText) {
        existingVerseText.disabled = false;
        existingVerseText.value = baseline;
        existingVerseText.setAttribute('data-initial-value', baseline);
        setInitialVerseTextValue('existing', baseline);
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

    if (translationSelect && existingVerseText) {
      translationSelect.addEventListener('change', function () {
        const value = translationSelect.value;
        if (selectedTranslationInput) {
          selectedTranslationInput.value = value;
        }
        let nextValue = '';
        if (value && Object.prototype.hasOwnProperty.call(translationData, value)) {
          nextValue = translationData[value];
        }
        existingVerseText.value = nextValue;
        existingVerseText.setAttribute('data-initial-value', nextValue);
        setInitialVerseTextValue('existing', nextValue);
        lastSelectedTranslation = value;
        syncSaveState();
      });
    }

    [existingVerseText, newVerseText].forEach(function (el) {
      if (!el) {
        return;
      }
      el.addEventListener('input', function () {
        syncSaveState();
      });
    });

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

    const initialActiveVerse = getActiveVerseElement();
    if (initialActiveVerse && initialActiveVerse.readOnly) {
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
      if (existingVerseText && Object.prototype.hasOwnProperty.call(translationData, current)) {
        const textValue = translationData[current];
        existingVerseText.value = textValue;
        existingVerseText.setAttribute('data-initial-value', textValue);
        setInitialVerseTextValue('existing', textValue);
      }
    }

    const forceNewTranslation = form.getAttribute('data-force-new-translation') === 'true';
    if ((Object.keys(translationData).length === 0 || forceNewTranslation) && addTranslationButton && !addTranslationButton.disabled) {
      const initialName = newTranslationInput ? newTranslationInput.value : '';
      const initialText = newVerseText ? newVerseText.getAttribute('data-initial-value') || newVerseText.value || '' : '';
      enterNewTranslationMode(initialName, initialText);
    }
  });
})();
