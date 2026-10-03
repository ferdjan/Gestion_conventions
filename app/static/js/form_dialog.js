/* Formulaires Word : dialogue de saisie avant téléchargement.
 *
 * Les boutons sont des liens directs (téléchargement possible sans JavaScript) ;
 * ce script intercepte le clic pour ouvrir le dialogue et compléter les champs
 * libres. Aucun attribut en ligne : CSP `script-src 'self'`.
 */
(function () {
  "use strict";

  var dialog = document.getElementById("form-dialog");
  var form = document.getElementById("form-dialog-form");
  if (!dialog || !form || typeof dialog.showModal !== "function") return;

  var label = document.getElementById("form-dialog-label");

  document.addEventListener("click", function (event) {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var link = event.target.closest("[data-form-kind]");
    if (!link) return;

    event.preventDefault();
    form.setAttribute("action", link.getAttribute("href") || "");
    if (label) {
      label.textContent = link.getAttribute("data-form-label") || link.textContent;
    }
    var kind = link.getAttribute("data-form-kind");
    Array.prototype.forEach.call(
      dialog.querySelectorAll("[data-for-kind]"),
      function (field) {
        field.hidden =
          field.getAttribute("data-for-kind").split(" ").indexOf(kind) === -1;
      }
    );
    dialog.showModal();
    var first = dialog.querySelector("[data-for-kind]:not([hidden]) input");
    if (first) first.focus();
  });
})();
