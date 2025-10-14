// Handle header actions such as Logout via JS POST to keep styling unified.
(function(){
  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  function postLogout(url){
    const csrftoken = getCookie('csrftoken');
    return fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken || '',
        'X-Requested-With': 'XMLHttpRequest'
      },
      credentials: 'same-origin',
      redirect: 'follow'
    }).then(res => {
      if (res.ok){
        // If server redirected, just follow by reloading
        window.location.reload();
      } else {
        // Fallback: navigate to GET logout (server likely handles)
        window.location.href = url;
      }
    }).catch(() => {
      window.location.href = url;
    });
  }

  function setupLogout(){
    document.querySelectorAll('[data-logout-link]').forEach(function(el){
      el.addEventListener('click', function(ev){
        ev.preventDefault();
        const url = el.getAttribute('href') || '/logout/';
        postLogout(url);
      });
    });
  }

  function setupResponsiveHeader(){
    const headerActions = document.querySelector('[data-header-actions]');
    if (!headerActions) return;

    const toggle = headerActions.querySelector('[data-header-menu-toggle]');
    const nav = headerActions.querySelector('.header-nav');
    if (!toggle || !nav) return;

    const links = Array.from(nav.querySelectorAll('.header-action'));
    if (!links.length){
      toggle.setAttribute('hidden', '');
      return;
    }

    let collapsed = false;
    const headerInner = headerActions.closest('.header-inner');
    const brandBlock = headerInner ? headerInner.querySelector('.brand-block') : null;

    function isNavVisuallyHidden(){
      if (nav.hasAttribute('hidden')) return true;
      const style = window.getComputedStyle(nav);
      return style.display === 'none' || style.visibility === 'hidden';
    }

    function closeMenu(){
      headerActions.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
      // If layout is collapsed (JS or CSS fallback), keep nav hidden by attribute
      const cssCollapsed = window.matchMedia && window.matchMedia('(max-width: 720px)').matches;
      if (collapsed || headerActions.classList.contains('is-collapsed') || cssCollapsed){
        nav.setAttribute('hidden', '');
      } else {
        nav.removeAttribute('hidden');
      }
    }

    function setCollapsed(state){
      if (state){
        collapsed = true;
        headerActions.classList.add('is-collapsed');
        closeMenu();
      } else {
        collapsed = false;
        headerActions.classList.remove('is-collapsed');
        headerActions.classList.remove('is-open');
        nav.removeAttribute('hidden');
        toggle.setAttribute('aria-expanded', 'false');
      }
    }

    function needsCollapse(){
      const wasCollapsed = headerActions.classList.contains('is-collapsed');
      const wasOpen = headerActions.classList.contains('is-open');
      const wasHidden = nav.hasAttribute('hidden');

      if (wasHidden){
        nav.removeAttribute('hidden');
      }
      if (wasOpen){
        headerActions.classList.remove('is-open');
      }
      if (wasCollapsed){
        headerActions.classList.remove('is-collapsed');
      }

      let wrapped = false;
      // Compute how much room actions actually have within the header row
      const innerWidth = headerInner ? headerInner.clientWidth : headerActions.clientWidth;
      const brandWidth = brandBlock ? brandBlock.clientWidth : 0;
      // Header uses a flex gap of ~20px between brand and actions
      const gapAllowance = 24; // include gap + minor padding
      const availableWidth = Math.max(0, innerWidth - brandWidth - gapAllowance);
      const navWidth = nav.scrollWidth;

      if (navWidth - availableWidth > 2){
        wrapped = true;
      } else if (links.length){
        const top = links[0].offsetTop;
        for (let i = 1; i < links.length; i += 1){
          if (Math.abs(links[i].offsetTop - top) > 1){
            wrapped = true;
            break;
          }
        }
      }

      if (wasCollapsed){
        headerActions.classList.add('is-collapsed');
      }
      if (wasOpen){
        headerActions.classList.add('is-open');
      }
      if (wasHidden && (wasCollapsed && !wasOpen)){
        nav.setAttribute('hidden', '');
      }

      return wrapped;
    }

    function updateCollapse(){
      const shouldCollapse = needsCollapse();
      setCollapsed(shouldCollapse);
    }

    toggle.addEventListener('click', function(){
      // Allow toggling when JS thinks not collapsed but CSS fallback hides the nav
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      const cssCollapsed = window.matchMedia && window.matchMedia('(max-width: 720px)').matches;
      const canToggle = collapsed || headerActions.classList.contains('is-collapsed') || cssCollapsed || isNavVisuallyHidden();
      if (!canToggle && !expanded){
        // Not in a collapsed state, nothing to toggle
        return;
      }
      if (expanded){
        closeMenu();
      } else {
        headerActions.classList.add('is-open');
        nav.removeAttribute('hidden');
        toggle.setAttribute('aria-expanded', 'true');
      }
    });

    links.forEach(function(link){
      link.addEventListener('click', function(){
        if (!collapsed) return;
        closeMenu();
      });
    });

    document.addEventListener('click', function(ev){
      const cssCollapsed = window.matchMedia && window.matchMedia('(max-width: 720px)').matches;
      if (!collapsed && !headerActions.classList.contains('is-collapsed') && !cssCollapsed) return;
      if (headerActions.contains(ev.target)) return;
      closeMenu();
    });

    document.addEventListener('keydown', function(ev){
      const cssCollapsed = window.matchMedia && window.matchMedia('(max-width: 720px)').matches;
      if (!collapsed && !headerActions.classList.contains('is-collapsed') && !cssCollapsed) return;
      if (ev.key === 'Escape' && headerActions.classList.contains('is-open')){
        closeMenu();
        toggle.focus();
      }
    });

    if (typeof ResizeObserver !== 'undefined'){
      const observer = new ResizeObserver(function(){
        updateCollapse();
      });
      observer.observe(headerActions);
      if (headerInner){
        observer.observe(headerInner);
      }
      if (brandBlock){
        observer.observe(brandBlock);
      }
    }

    window.addEventListener('resize', function(){
      window.requestAnimationFrame(updateCollapse);
    });

    updateCollapse();
    window.requestAnimationFrame(updateCollapse);
    window.addEventListener('load', updateCollapse);
  }

  document.addEventListener('DOMContentLoaded', function(){
    setupLogout();
    setupResponsiveHeader();
  });
})();

