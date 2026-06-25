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

export const PHONE_PATTERN_RE = /^[\d+\-\s()]{6,20}$/;
export const PHONE_PATTERN_HTML = "[\\d+\\-\\s()]{6,20}";

// Standard email pattern. Conservative — matches what `<input type='email'>`
// does in modern browsers but we re-check on save so server-side
// validation isn't required.
export const EMAIL_PATTERN_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidPhone(value: string): boolean {
  if (!value) return true; // empty = no value submitted, not "invalid"
  return PHONE_PATTERN_RE.test(value.trim());
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
