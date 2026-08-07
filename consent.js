/* ══════════════════════════════════════════════════════════════════════════
   CONSENTIMIENTO SMS — evidencia para la verificación A2P 10DLC
   (Spanish mirror of ~/Downloads/homes/consent.js — keep the two in step)
   ══════════════════════════════════════════════════════════════════════════
   Carriers can ask us, months later, to prove that a specific number opted in,
   and that proof has to show WHAT the person actually saw. Someone who opted
   in on this site saw the SPANISH wording, so that is what gets stored —
   never a translation of it, and never the English text. That is the whole
   reason CONSENT_TEXT is recorded verbatim alongside its own version string.

   Fields sent with every submission:
     sms_consent          "Sí" / "No"   (never blank — "No" is a real record)
     consent_timestamp    ISO-8601 UTC
     consent_timestamp_local  human-readable, with timezone
     consent_ip           submitter's public IP (see note below)
     consent_page_url     the exact page the form was on
     consent_text_version CONSENT_TEXT_VERSION below
     consent_text         the verbatim Spanish wording displayed at submit time

   Bump CONSENT_TEXT_VERSION *and* CONSENT_TEXT together whenever the wording
   on the checkbox changes. Old records keep their old version string — that is
   the point: we can always show what a given person agreed to, in the language
   they agreed to it in.

   IP note: a browser can't read its own public IP, so we ask ipify for it.
   If that call fails we send "unavailable" rather than dropping the field;
   Formspree also records the submitting IP server-side as a backstop. ipify is
   disclosed in the Política de Privacidad.
   ══════════════════════════════════════════════════════════════════════════ */

const CONSENT_TEXT_VERSION = "2026-08-07.es.v1";

const CONSENT_TEXT =
  "Acepto recibir mensajes de texto de Americas Best Home Solutions LLC sobre " +
  "casas disponibles, citas para ver casas, ofertas y seguimiento. La frecuencia " +
  "de mensajes varía. Pueden aplicar tarifas de mensajes y datos. Responda STOP " +
  "para cancelar la suscripción o HELP para obtener ayuda. Consulte nuestra " +
  "Política de Privacidad y nuestros Términos de Mensajes.";

/* Fetch the public IP once per page load, with a short timeout so a slow or
   blocked lookup can never hold up a lead. Resolves to a string, never throws. */
const CONSENT_IP = (function () {
  if (!window.fetch || !window.AbortController) return Promise.resolve("unavailable");
  const stop = new AbortController();
  const timer = setTimeout(() => stop.abort(), 2500);
  return fetch("https://api.ipify.org?format=json", { signal: stop.signal })
    .then((r) => (r.ok ? r.json() : null))
    .then((j) => (j && j.ip ? j.ip : "unavailable"))
    .catch(() => "unavailable")
    .finally(() => clearTimeout(timer));
})();

/* Append the consent evidence fields to a FormData about to be submitted.
   `form` is the <form> element; the checkbox must be named "sms_consent". */
async function addConsentRecord(data, form) {
  const box = form.querySelector('input[name="sms_consent"]');
  const now = new Date();

  // An unchecked box is meaningful evidence too: it proves we were told NOT to
  // text this person. FormData omits unchecked boxes, so set it explicitly.
  data.set("sms_consent", box && box.checked ? "Sí" : "No");
  data.set("consent_timestamp", now.toISOString());
  data.set("consent_timestamp_local", now.toString());
  data.set("consent_page_url", window.location.href);
  data.set("consent_text_version", CONSENT_TEXT_VERSION);
  data.set("consent_text", CONSENT_TEXT);
  data.set("consent_language", "es");
  data.set("consent_ip", await CONSENT_IP);
  return data;
}
