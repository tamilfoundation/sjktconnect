"""
Pipeline version registry.

Every component that affects output quality is registered here.
AI prompts are content-hashed automatically — if you change a prompt
but forget to bump the version, check_drift() will catch it.

RULE: When you change ANY prompt or algorithm, bump the version here.
"""
import hashlib

# --- Component Registry ---
# "hash_source" is a dotted import path to the prompt constant.
# Leave it None for deterministic tools (version bump is manual).

COMPONENTS = {
    "mention_analysis": {
        "version": "1.0.0",
        "hash_source": "parliament.services.gemini_client:ANALYSIS_PROMPT",
    },
    "brief_generation": {
        "version": "1.2.0",
        "hash_source": "parliament.services.brief_generator:BRIEF_PROMPT",
    },
    "brief_regeneration": {
        "version": "1.0.0",
        "hash_source": "parliament.management.commands.regenerate_briefs:BRIEF_PROMPT",
    },
    "report_generation": {
        "version": "1.0.0",
        "hash_source": "parliament.management.commands.generate_meeting_reports:MEETING_REPORT_PROMPT",
    },
    "evaluation": {
        "version": "1.0.0",
        "hash_source": "parliament.services.evaluator:EVALUATOR_PROMPT",
    },
    "correction": {
        "version": "1.0.0",
        "hash_source": "parliament.services.corrector:CORRECTION_PROMPT",
    },
    "illustration": {
        "version": "1.0.0",
        "hash_source": "parliament.management.commands.generate_meeting_reports:ILLUSTRATION_PROMPT",
    },
    "extractor": {
        "version": "1.0.0",
        "hash_source": None,
    },
    "matcher": {
        "version": "1.0.0",
        "hash_source": None,
    },
    "normalizer": {
        "version": "1.0.0",
        "hash_source": None,
    },
    "keywords": {
        "version": "1.0.0",
        "hash_source": None,
    },
    "searcher": {
        "version": "1.0.0",
        "hash_source": None,
    },
    "context_data": {
        "version": "2.0.0",
        "hash_source": None,
    },
}

# Stored hashes — updated by running: manage.py check_pipeline_drift --update
_STORED_HASHES = {}


def _resolve_prompt(dotted_path: str) -> str:
    """Import and return the prompt string from 'module.path:CONSTANT'."""
    module_path, attr = dotted_path.rsplit(":", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, attr)


def _hash_content(text: str) -> str:
    """SHA-256 truncated to 8 chars."""
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def get_component_version(name: str) -> str:
    """Return the semantic version of a component."""
    return COMPONENTS[name]["version"]


def get_pipeline_version() -> str:
    """Composite hash of all component versions. Changes when anything changes."""
    parts = sorted(f"{k}={v['version']}" for k, v in COMPONENTS.items())
    combined = "|".join(parts)
    return f"pipeline-{_hash_content(combined)}"


def get_stamp(component: str) -> dict:
    """Return version info to stamp on a generated record."""
    return {
        "pipeline_version": get_pipeline_version(),
        "component_version": get_component_version(component),
        "component_name": component,
    }


def check_drift() -> list[tuple[str, bool, str]]:
    """
    Check each prompt-based component for content drift.
    Returns list of (component_name, has_drifted, detail_message).
    """
    results = []
    for name, info in COMPONENTS.items():
        if not info.get("hash_source"):
            results.append((name, False, "deterministic — no hash check"))
            continue
        try:
            prompt = _resolve_prompt(info["hash_source"])
            current_hash = _hash_content(prompt)
            stored = _STORED_HASHES.get(name)
            if stored is None:
                results.append((name, False, f"no baseline — current hash: {current_hash}"))
            elif stored != current_hash:
                results.append((name, True,
                    f"DRIFT: stored={stored}, current={current_hash}. "
                    f"Bump version in registry (currently {info['version']})."))
            else:
                results.append((name, False, "clean"))
        except Exception as e:
            results.append((name, False, f"import error: {e}"))
    return results
