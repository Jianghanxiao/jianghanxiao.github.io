(function() {
  this.util = {
    hasField: function(obj, field, values) {
      var ovs;
      if (obj[field]) {
        ovs = obj[field];
        if (typeof ovs === 'string') {
          ovs = ovs.split(',');
        }
        if (!Array.isArray(values)) {
          values = [values];
        }
        return !values.every(function(v) {
          return ovs.indexOf(v) < 0;
        });
      }
      return false;
    },
    showPubs: function(field, values) {
      if (!Array.isArray(values)) {
        values = [values];
      }
      return $('.paper').each(function(x, i) {
        var d;
        d = $(this).data();
        if (util.hasField(d, field, values)) {
          return $(this).show();
        } else {
          return $(this).hide();
        }
      });
    },
    showAllPubs: function() {
      return $('.paper').each(function(x, i) {
        return $(this).show();
      });
    }
  };

  function markCurrentNavigation() {
    var currentPage = window.location.pathname.split('/').pop() || 'index.html';
    var navigationLinks = document.querySelectorAll('#site-navigation a');

    Array.prototype.forEach.call(navigationLinks, function(link) {
      if (link.getAttribute('href') === currentPage) {
        link.setAttribute('aria-current', 'page');
        if (link.parentElement) {
          link.parentElement.classList.add('active');
        }
      }
    });
  }

  function addNavigationFallback() {
    var hasBootstrapCollapse = window.jQuery &&
      window.jQuery.fn &&
      typeof window.jQuery.fn.collapse === 'function';

    if (hasBootstrapCollapse) {
      return;
    }

    var toggle = document.querySelector('[data-target="#site-navigation"]');
    var navigation = document.getElementById('site-navigation');

    if (!toggle || !navigation) {
      return;
    }

    toggle.addEventListener('click', function() {
      var isOpen = navigation.classList.toggle('in');
      toggle.classList.toggle('collapsed', !isOpen);
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
    });
  }

  function initializeSite() {
    markCurrentNavigation();
    addNavigationFallback();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeSite);
  } else {
    initializeSite();
  }
}).call(this);
