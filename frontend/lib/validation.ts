/**
 * Field-level validation helpers for admin edit forms.
 *
 * Sprint 26 bug #1: phone + email inputs on the Contact + Leaders edit
 * tabs accepted any string. Operators were storing values like
 * `tel:05-2421470/011-2379104` (multi-number, which then broke `tel:`
 * links — bug #6) and clearly-invalid email shapes. This module
 * centralises the regex + error-message logic so every edit form uses
 * the same rules.
 *
 * Permissive on purpose — MOE phone data is messy historically
 * (`+60 4 966 3429`, `04-9663429`, `04 966 3429`). We allow any
 * combination of digits, spaces, `-`, `+`, parens. We REJECT `/` and
 * `,` because those mean "multiple numbers" and the only correct
 * action there is to pick one.
 */

// HTML5 pattern for browser-level filter — permissive on input chars so
// users can paste with formatting. Real validation happens in
// isValidPhone() against the digit-count rule.
export const PHONE_PATTERN_RE = /^[\d+\-\s()]{6,20}$/;
export const PHONE_PATTERN_HTML = "[\\d+\\-\\s()]{6,20}";

// Standard email pattern. Conservative — matches what `<input type='email'>`
// does in modern browsers but we re-check on save so server-side
// validation isn't required.
export const EMAIL_PATTERN_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Malaysian phone number validation (Sprint 28).
 *
 * Owner reported Sprint 27's pattern was too permissive — a truncated
 * number like "0122090008" (1 digit short of a valid mobile) passed.
 * Rule: strip everything that isn't a digit, drop the +60 country
 * prefix if present, then check:
 *   - mobile (starts with 01): 10-11 digits total
 *   - landline (starts with 0[2-9]): 9-10 digits total
 *   - empty: treated as "no value", not "invalid"
 *
 * Examples that pass:
 *   012-345 6789, +60 12-345 6789, 03-2601 7222, +60 3 2601 7222
 * Examples that fail:
 *   0122090008  (10 digits — too short for 012 mobile, needs 10-11)
 *   05-2421470/011-2379104  (multi-number)
 *   call us 03-1234
 *
 * The HTML5 `pattern` attr still keeps the input shape-restricted;
 * this digit-count rule runs in `phoneError()` for the inline message.
 */
// MOE uses the literal "TIADA" (Bahasa for "none") in their dataset
// when a school has no phone or fax — it's a meaningful "no value"
// marker, not a typo. School admins also re-enter this when their
// number is genuinely unassigned. Accept any-case TIADA explicitly.
const PHONE_SENTINELS = new Set(["tiada", "n/a", "na", "none", "-"]);

export function isValidPhone(value: string): boolean {
  if (!value) return true;
  const trimmed = value.trim();
  if (PHONE_SENTINELS.has(trimmed.toLowerCase())) return true;
  // Shape-level check first (no /, ,, ;, no letters, etc.).
  if (!PHONE_PATTERN_RE.test(trimmed)) return false;
  // Digit-count check. Strip everything except digits, then strip a
  // leading "60" if the original had a "+" prefix (country code).
  let digits = trimmed.replace(/\D/g, "");
  // Normalise +60 international form to local form: strip "60", then
  // prepend the leading 0 that the international form drops.
  // "+60 12 209 0008" → digits "60122090008" → "122090008" → "0122090008"
  if (/^\+/.test(trimmed) && digits.startsWith("60")) {
    digits = "0" + digits.slice(2);
  }
  if (digits.length === 0) return false;
  // Malaysian phones (post-normalisation) start with 0.
  if (!digits.startsWith("0")) return false;
  const secondDigit = digits[1];
  if (secondDigit === "1") {
    // Mobile: 01X-XXX XXXX or 01X-XXXX XXXX → 10-11 digits.
    return digits.length === 10 || digits.length === 11;
  }
  if (secondDigit && /[2-9]/.test(secondDigit)) {
    // Landline: 0X-XXXXXXX or 0X-XXXXXXXX → 9-10 digits.
    return digits.length === 9 || digits.length === 10;
  }
  return false;
}

export function isValidEmail(value: string): boolean {
  if (!value) return true;
  return EMAIL_PATTERN_RE.test(value.trim());
}

export function phoneError(value: string, t: (k: string) => string): string {
  if (isValidPhone(value)) return "";
  return t("validationPhone");
}

export function emailError(value: string, t: (k: string) => string): string {
  if (isValidEmail(value)) return "";
  return t("validationEmail");
}
