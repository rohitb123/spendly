// main.js — students will add JavaScript here as features are built

// Confirmation prompt for any control carrying a data-confirm message
// (e.g. the per-row Delete buttons on the profile page). Cancelling the
// dialog prevents the default action, so the form is never submitted.
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-confirm]").forEach(function (el) {
        el.addEventListener("click", function (event) {
            if (!window.confirm(el.getAttribute("data-confirm"))) {
                event.preventDefault();
            }
        });
    });
});
