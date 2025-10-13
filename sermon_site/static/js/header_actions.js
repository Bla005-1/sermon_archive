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

  document.addEventListener('DOMContentLoaded', function(){
    document.querySelectorAll('[data-logout-link]').forEach(function(el){
      el.addEventListener('click', function(ev){
        ev.preventDefault();
        const url = el.getAttribute('href') || '/logout/';
        postLogout(url);
      });
    });
  });
})();

