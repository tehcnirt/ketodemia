(function () {
    function decode(el, attr) {
        var value = el.getAttribute(attr);
        return value ? atob(value) : '';
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.email-link').forEach(function (el) {
            var email = decode(el, 'data-u') + '@' + decode(el, 'data-d');
            el.setAttribute('href', 'mailto:' + email);
            if (el.hasAttribute('data-show-email')) {
                el.textContent = email;
            }
        });
    });
})();
