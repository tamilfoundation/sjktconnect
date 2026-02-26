# Lessons Learned

Cross-cutting lessons from SJK(T) Connect development. Project-specific decisions live in CLAUDE.md.

- Hoisting constants out of loop bodies (regex patterns, sets) is easy to miss during initial development — run a simplification pass after each feature sprint (Sprint 0.3)
- Signal handlers that resolve settings on every fire (e.g. `_get_tracked_models()`) can be silently expensive — cache at module level when the setting doesn't change at runtime (Sprint 0.3)
- f-string logging (`logger.warning(f"...")`) defeats lazy evaluation — always use `%s` style for log messages (Sprint 0.3)
- `%-d` strftime flag is Linux-only — use `f"{d.day}"` for cross-platform no-leading-zero day formatting (Sprint 0.4)
- `google.generativeai` is deprecated — use `google.genai` with client pattern (`genai.Client(api_key=...)`) instead of global `genai.configure()` (Sprint 0.4)
- Django ChoiceField with `required=False` saves empty string `''`, not None — for IntegerField model fields use `TypedChoiceField(coerce=int, empty_value=None)` (Sprint 0.5)
- When redirecting after a model update, double-check the target URL's kwargs match the right model — `pk=instance.fk_id` redirects to the FK's PK, not the instance's PK (Sprint 0.5)
