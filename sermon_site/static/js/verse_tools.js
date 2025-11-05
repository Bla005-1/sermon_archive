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
    const translationDisplayData = parseJSONScript('verse-translation-display-data');
    const translationSelect = form.querySelector('[data-translation-select]');
    const selectedTranslationInput = form.querySelector('[data-selected-translation]');
    const verseDisplay = form.querySelector('[data-verse-display]');
    const emptyDisplayText = verseDisplay ? verseDisplay.getAttribute('data-empty-text') || '' : '';
    const saveButton = form.querySelector('[data-save-button]');

    const noteEditor = form.querySelector('[data-note-editor]');
    const noteView = form.querySelector('[data-note-view]');
    const noteInput = form.querySelector('[data-note-input]');
    const notePreview = form.querySelector('[data-note-preview]');
    const noteDisplay = form.querySelector('[data-note-display]');
    const noteOriginalInput = form.querySelector('[data-note-original]');
    const noteEditButton = form.querySelector('[data-note-edit-button]');
    const noteCancelButton = form.querySelector('[data-note-cancel-button]');
    const noteEmptyHint = form.querySelector('[data-note-empty-hint]');

    let initialNoteText = noteInput ? noteInput.getAttribute('data-initial-value') || '' : '';

    function syncSaveState() {
      if (!saveButton) {
        return;
      }
      let dirty = false;
      if (noteInput && noteEditor && !noteEditor.hasAttribute('hidden')) {
        dirty = noteInput.value !== initialNoteText;
      }
      saveButton.disabled = !dirty;
      if (dirty) {
        saveButton.removeAttribute('aria-disabled');
      } else {
        saveButton.setAttribute('aria-disabled', 'true');
      }
    }

    function updateVerseDisplayFor(key) {
      if (!verseDisplay) {
        return;
      }
      let htmlValue = '';
      if (key && Object.prototype.hasOwnProperty.call(translationDisplayData, key)) {
        htmlValue = translationDisplayData[key];
      }
      if (htmlValue) {
        verseDisplay.innerHTML = htmlValue;
        return;
      }
      let plainText = '';
      if (key && Object.prototype.hasOwnProperty.call(translationData, key)) {
        plainText = translationData[key] || '';
      }
      if (plainText) {
        verseDisplay.textContent = plainText;
      } else if (emptyDisplayText) {
        verseDisplay.textContent = emptyDisplayText;
      } else {
        verseDisplay.textContent = '';
      }
    }

    if (translationSelect) {
      translationSelect.addEventListener('change', function () {
        const value = translationSelect.value;
        if (selectedTranslationInput) {
          selectedTranslationInput.value = value;
        }
        updateVerseDisplayFor(value);
      });

      if (selectedTranslationInput) {
        selectedTranslationInput.value = translationSelect.value || '';
      }
      updateVerseDisplayFor(translationSelect.value || '');
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

    syncSaveState();

    const commentaryContainer = document.querySelector('[data-commentary-container]');
    if (commentaryContainer) {
      const toggleButton = commentaryContainer.querySelector('[data-commentary-toggle]');
      const contentEl = commentaryContainer.querySelector('[data-commentary-content]');
      const listEl = commentaryContainer.querySelector('[data-commentary-list]');
      const emptyEl = commentaryContainer.querySelector('[data-commentary-empty]');
      const loadingEl = commentaryContainer.querySelector('[data-commentary-loading]');
      const apiUrl = commentaryContainer.getAttribute('data-commentary-api-url') || '';
      const queryRef = commentaryContainer.getAttribute('data-commentary-ref') || '';
      const queryTranslation = commentaryContainer.getAttribute('data-commentary-translation') || '';

      const setExpandedState = function (expanded) {
        if (!toggleButton || !contentEl) {
          return;
        }
        toggleButton.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        contentEl.hidden = !expanded;
      };

      if (toggleButton && contentEl) {
        setExpandedState(false);
        toggleButton.addEventListener('click', function () {
          const currentlyExpanded = toggleButton.getAttribute('aria-expanded') === 'true';
          setExpandedState(!currentlyExpanded);
        });
      }

      const setLoadingState = function (isLoading) {
        if (loadingEl) {
          loadingEl.hidden = !isLoading;
        }
        if (isLoading) {
          if (listEl) {
            listEl.hidden = true;
          }
          if (emptyEl) {
            emptyEl.hidden = true;
          }
        }
      };

      const renderCommentaries = function (items) {
        if (!listEl) {
          return;
        }
        listEl.innerHTML = '';
        if (!Array.isArray(items) || items.length === 0) {
          listEl.hidden = true;
          if (emptyEl) {
            emptyEl.hidden = false;
            emptyEl.textContent = 'No commentaries for this passage yet.';
          }
          return;
        }

        items.forEach(function (item) {
          const li = document.createElement('li');
          li.className = 'commentary-item';

          const header = document.createElement('div');
          header.className = 'commentary-item__header';

          const nameEl = document.createElement('span');
          nameEl.className = 'commentary-item__author';
          nameEl.textContent = item.display_name || item.father_name || 'Commentary';
          header.appendChild(nameEl);

          const referenceEl = document.createElement('span');
          referenceEl.className = 'commentary-item__reference';
          referenceEl.textContent = item.reference || '';
          header.appendChild(referenceEl);

          const textEl = document.createElement('p');
          textEl.className = 'commentary-item__text';
          textEl.textContent = item.text || '';

          li.appendChild(header);
          li.appendChild(textEl);
          listEl.appendChild(li);
        });

        listEl.hidden = false;
        if (emptyEl) {
          emptyEl.hidden = true;
        }
      };

      const handleError = function () {
        if (emptyEl) {
          emptyEl.hidden = false;
          emptyEl.textContent = 'Commentaries could not be loaded.';
        }
        if (listEl) {
          listEl.hidden = true;
          listEl.innerHTML = '';
        }
        setLoadingState(false);
      };

      const loadCommentaries = function () {
        if (!apiUrl || !queryRef) {
          handleError();
          return Promise.resolve();
        }
        setLoadingState(true);
        const params = new URLSearchParams();
        params.set('ref', queryRef);
        if (queryTranslation) {
          params.set('translation', queryTranslation);
        }
        const requestUrl = `${apiUrl}?${params.toString()}`;
        return fetch(requestUrl, { credentials: 'same-origin' })
          .then(function (response) {
            if (!response.ok) {
              throw new Error('Commentaries request failed');
            }
            return response.json();
          })
          .then(function (payload) {
            const items = (payload && payload.commentaries) || [];
            setLoadingState(false);
            renderCommentaries(items);
          })
          .catch(function (err) {
            console.error(err);
            handleError();
          });
      };

      loadCommentaries();
    }

    const crossrefContainer = document.querySelector('[data-crossref-container]');
    if (crossrefContainer) {
      const toggleButton = crossrefContainer.querySelector('[data-crossref-toggle]');
      const contentEl = crossrefContainer.querySelector('[data-crossref-content]');
      const listEl = crossrefContainer.querySelector('[data-crossref-list]');
      const emptyEl = crossrefContainer.querySelector('[data-crossref-empty]');
      const loadingEl = crossrefContainer.querySelector('[data-crossref-loading]');
      const selectEl = crossrefContainer.querySelector('[data-crossref-select]');
      const defaultActive = crossrefContainer.getAttribute('data-active-verse') || '';
      const verseToolsUrl = crossrefContainer.getAttribute('data-verse-tools-url') || '';
      const apiUrl = crossrefContainer.getAttribute('data-crossref-api-url') || '';
      const queryRef = crossrefContainer.getAttribute('data-crossref-ref') || '';
      const queryTranslation = crossrefContainer.getAttribute('data-crossref-translation') || '';

      let crossReferenceData = {};
      let hasLoaded = false;

      const setExpandedState = function (expanded) {
        if (!toggleButton || !contentEl) {
          return;
        }
        toggleButton.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        contentEl.hidden = !expanded;
      };

      if (toggleButton && contentEl) {
        setExpandedState(false);
        toggleButton.addEventListener('click', function () {
          const currentlyExpanded = toggleButton.getAttribute('aria-expanded') === 'true';
          setExpandedState(!currentlyExpanded);
        });
      }

      const buildVerseToolsLink = function (reference) {
        if (!verseToolsUrl || !reference) {
          return '';
        }
        const joiner = verseToolsUrl.includes('?') ? '&' : '?';
        return `${verseToolsUrl}${joiner}ref=${encodeURIComponent(reference)}`;
      };

      const setLoadingState = function (isLoading) {
        if (loadingEl) {
          loadingEl.hidden = !isLoading;
        }
        if (isLoading) {
          if (listEl) {
            listEl.hidden = true;
          }
          if (emptyEl) {
            emptyEl.hidden = true;
          }
          if (selectEl) {
            selectEl.disabled = true;
            selectEl.setAttribute('aria-disabled', 'true');
          }
        } else if (selectEl) {
          selectEl.disabled = false;
          selectEl.removeAttribute('aria-disabled');
        }
      };

      const renderCrossReferences = function (verseId) {
        if (!listEl) {
          return;
        }
        if (!hasLoaded) {
          return;
        }
        const key = String(verseId || '');
        const items = (crossReferenceData && crossReferenceData[key]) || [];
        listEl.innerHTML = '';
        if (items.length === 0) {
          listEl.hidden = true;
          if (emptyEl) {
            emptyEl.hidden = false;
          }
          return;
        }
        for (const item of items) {
          const li = document.createElement('li');
          li.className = 'cross-reference-item';
          const refEl = document.createElement('a');
          refEl.className = 'cross-reference-item__ref';
          const referenceText = item.reference || '';
          refEl.textContent = referenceText;
          const link = buildVerseToolsLink(referenceText);
          if (link) {
            refEl.href = link;
          }
          const textEl = document.createElement('p');
          textEl.className = 'cross-reference-item__text';
          textEl.textContent = item.text || '';
          li.appendChild(refEl);
          li.appendChild(textEl);
          listEl.appendChild(li);
        }
        listEl.hidden = false;
        if (emptyEl) {
          emptyEl.hidden = true;
        }
      };

      const handleError = function () {
        if (emptyEl) {
          emptyEl.hidden = false;
          emptyEl.textContent = 'Cross references could not be loaded.';
        }
        if (listEl) {
          listEl.hidden = true;
          listEl.innerHTML = '';
        }
        hasLoaded = false;
        setLoadingState(false);
      };

      const loadCrossReferences = function () {
        if (!apiUrl || !queryRef) {
          handleError();
          return Promise.resolve();
        }
        setLoadingState(true);
        const params = new URLSearchParams();
        params.set('ref', queryRef);
        if (queryTranslation) {
          params.set('translation', queryTranslation);
        }
        const requestUrl = `${apiUrl}?${params.toString()}`;
        return fetch(requestUrl, { credentials: 'same-origin' })
          .then(function (response) {
            if (!response.ok) {
              throw new Error('Cross references request failed');
            }
            return response.json();
          })
          .then(function (payload) {
            const results = (payload && payload.results) || [];
            const data = {};
            let hasAny = false;
            results.forEach(function (item) {
              const key = String(item.verse_id);
              const refs = Array.isArray(item.cross_refs) ? item.cross_refs : [];
              data[key] = refs.map(function (refItem) {
                return {
                  reference: refItem.reference || '',
                  text: refItem.preview_text || '',
                };
              });
              if (data[key].length > 0) {
                hasAny = true;
              }
            });
            crossReferenceData = data;
            hasLoaded = true;
            setLoadingState(false);
            const initial = (selectEl && (selectEl.value || defaultActive)) || defaultActive;
            if (!hasAny && emptyEl) {
              emptyEl.hidden = false;
              emptyEl.textContent = 'No cross references for this verse yet.';
            }
            if (selectEl) {
              selectEl.addEventListener('change', function () {
                renderCrossReferences(selectEl.value);
              });
            }
            const initialKey = initial || Object.keys(crossReferenceData)[0] || '';
            renderCrossReferences(initialKey);
          })
          .catch(function (err) {
            console.error(err);
            handleError();
          });
      };

      loadCrossReferences();
    }
  });
})();
