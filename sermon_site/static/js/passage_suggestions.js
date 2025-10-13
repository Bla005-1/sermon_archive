(function () {
  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else {
      fn();
    }
  }

  function normalizeBook(raw, aliases) {
    if (!raw) {
      return '';
    }
    let name = raw.replace(/\s+/g, ' ').trim().toLowerCase();
    if (!name) {
      return '';
    }
    if (aliases && Object.prototype.hasOwnProperty.call(aliases, name)) {
      return aliases[name];
    }
    name = name.replace(/\b\w/g, function (c) {
      return c.toUpperCase();
    });
    name = name.replace(/(^| )i{3}(?= [A-Za-z])/gi, '$1 3');
    name = name.replace(/(^| )i{2}(?= [A-Za-z])/gi, '$1 2');
    name = name.replace(/(^| )i{1}(?= [A-Za-z])/gi, '$1 1');
    return name.replace(/^\s+/, '');
  }

  function getBookPart(raw) {
    if (!raw) {
      return '';
    }
    const match = raw.match(/^\s*(.+?)\s+\d/);
    if (match) {
      return match[1];
    }
    return raw.trim();
  }

  ready(function () {
    const input = document.querySelector('[data-passage-input]');
    if (!input) {
      return;
    }
    const suggestionsEl = document.querySelector('[data-passage-suggestions]');
    if (!suggestionsEl) {
      return;
    }

    const dataEl = document.getElementById('passage-book-data');
    const aliasEl = document.getElementById('passage-book-aliases');
    if (!dataEl) {
      return;
    }

    let books = [];
    try {
      books = JSON.parse(dataEl.textContent || '[]');
    } catch (err) {
      console.error('Failed to parse passage suggestions data', err);
      books = [];
    }
    let aliases = {};
    if (aliasEl) {
      try {
        aliases = JSON.parse(aliasEl.textContent || '{}');
      } catch (err) {
        console.error('Failed to parse passage alias data', err);
        aliases = {};
      }
    }

    if (!Array.isArray(books) || books.length === 0) {
      return;
    }

    const normalizedBooks = books.map(function (book) {
      return {
        name: book.name,
        normalized: (book.normalized || '').trim(),
      };
    });

    function hideSuggestions() {
      suggestionsEl.hidden = true;
      suggestionsEl.innerHTML = '';
    }

    function renderSuggestions(matches) {
      if (!matches.length) {
        hideSuggestions();
        return;
      }
      const fragment = document.createDocumentFragment();
      matches.slice(0, 8).forEach(function (match) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'suggestion-option';
        button.textContent = match.name;
        button.setAttribute('data-book-name', match.name);
        fragment.appendChild(button);
      });
      suggestionsEl.innerHTML = '';
      suggestionsEl.appendChild(fragment);
      suggestionsEl.hidden = false;
    }

    function updateSuggestions() {
      const bookPartRaw = getBookPart(input.value || '');
      if (!bookPartRaw) {
        hideSuggestions();
        return;
      }
      const normalizedQuery = normalizeBook(bookPartRaw, aliases);
      if (!normalizedQuery) {
        hideSuggestions();
        return;
      }
      const exact = normalizedBooks.some(function (book) {
        return book.normalized === normalizedQuery;
      });
      if (exact) {
        hideSuggestions();
        return;
      }
      const matches = normalizedBooks.filter(function (book) {
        return book.normalized.toLowerCase().startsWith(normalizedQuery.toLowerCase());
      });
      if (!matches.length) {
        hideSuggestions();
        return;
      }
      renderSuggestions(matches);
    }

    suggestionsEl.addEventListener('pointerdown', function (event) {
      const target = event.target;
      if (!(target instanceof HTMLElement)) {
        return;
      }
      const name = target.getAttribute('data-book-name');
      if (!name) {
        return;
      }
      event.preventDefault();
      input.value = name + ' ';
      input.focus();
      input.dispatchEvent(new Event('input', { bubbles: true }));
      hideSuggestions();
    });

    input.addEventListener('input', updateSuggestions);
    input.addEventListener('focus', updateSuggestions);
    input.addEventListener('blur', function () {
      window.setTimeout(hideSuggestions, 120);
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') {
        hideSuggestions();
      }
    });
  });
})();
