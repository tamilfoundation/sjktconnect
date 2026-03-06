# Historical Hansard Rebuild Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve speaker extraction and Gemini analysis, then rebuild all 97 Hansard sittings for v1.0 release.

**Architecture:** Three code improvements (speaker regex, Gemini prompt, MP cross-reference), then a new `rebuild_all_hansards` management command that resets all sittings to PENDING, re-downloads/re-extracts/re-searches/re-matches/re-analyses them, and regenerates scorecards and briefs. The command runs overnight since it involves ~97 PDF downloads and ~200+ Gemini API calls.

**Tech Stack:** Django 5.x, pdfplumber, google.genai SDK (Gemini 2.5 Flash), PostgreSQL (Supabase)

---

### Task 1: Improve Speaker Extraction Regex

The current `SPEAKER_PATTERN` in `searcher.py` misses some Malaysian parliamentary title variants. Also, the backward search only looks at the current page + 1 previous page. We need to expand both.

**Files:**
- Modify: `backend/hansard/pipeline/searcher.py:27-38` (SPEAKER_PATTERN)
- Modify: `backend/hansard/pipeline/searcher.py:124-166` (_find_speaker — extend to 2 previous pages)
- Test: `backend/hansard/tests/test_searcher.py`

**Step 1: Write failing tests for new speaker patterns**

Add these tests to `backend/hansard/tests/test_searcher.py`:

```python
def test_speaker_extraction_yab(self):
    """YAB title should be captured."""
    pages = self._make_pages(
        "YAB Perdana Menteri [Dato' Sri Anwar Ibrahim]: "
        "Kerajaan akan membaiki SJK(T) di seluruh negara."
    )
    matches = search_keywords(pages, ["sjk(t)"])
    self.assertEqual(len(matches), 1)
    self.assertIn("Anwar Ibrahim", matches[0]["speaker_name"])

def test_speaker_extraction_dato_seri(self):
    """Dato' Seri title should be captured."""
    pages = self._make_pages(
        "Dato' Seri Dr. Mah Hang Soon [Jempol]: "
        "SJK(T) di kawasan saya memerlukan peruntukan."
    )
    matches = search_keywords(pages, ["sjk(t)"])
    self.assertEqual(len(matches), 1)
    self.assertIn("Mah Hang Soon", matches[0]["speaker_name"])

def test_speaker_extraction_tuan_pengerusi(self):
    """Tuan Pengerusi is a generic title, should return empty speaker."""
    pages = self._make_pages(
        "Tuan Pengerusi: SJK(T) Ladang Bikam perlu dibaiki."
    )
    matches = search_keywords(pages, ["sjk(t)"])
    self.assertEqual(len(matches), 1)
    self.assertEqual(matches[0]["speaker_name"], "")

def test_speaker_two_pages_back(self):
    """Speaker started 2 pages before the keyword — should still find them."""
    pages = self._make_pages(
        "Tuan Ganabatirau a/l Veraman [Klang]: Saya ingin bertanya...",
        "...sambungan ucapan tentang pendidikan...",
        "...khususnya SJK(T) di kawasan saya."
    )
    matches = search_keywords(pages, ["sjk(t)"])
    self.assertEqual(len(matches), 1)
    self.assertIn("Ganabatirau", matches[0]["speaker_name"])

def test_speaker_menteri_besar(self):
    """Menteri Besar title should be captured."""
    pages = self._make_pages(
        "Menteri Besar Perak [Dato' Saarani Mohamad]: "
        "Kerajaan negeri akan bantu SJK(T) di Perak."
    )
    matches = search_keywords(pages, ["sjk(t)"])
    self.assertEqual(len(matches), 1)
    self.assertIn("Saarani", matches[0]["speaker_name"])
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest hansard/tests/test_searcher.py -v -k "test_speaker"`
Expected: Several FAIL (new patterns not matched, 2-page-back not searched)

**Step 3: Update SPEAKER_PATTERN and _find_speaker**

In `backend/hansard/pipeline/searcher.py`, replace the SPEAKER_PATTERN (lines 27-38) with:

```python
SPEAKER_PATTERN = re.compile(
    r'(?:^|\n)\s*'  # Start of line
    r'('
    r'(?:YAB|Y\.?A\.?B\.?'
    r'|Tuan|Puan|Dato\'?|Datuk|Tan Sri|Tun|Dr\.'
    r'|Y\.?B\.?|Yang Berhormat'
    r'|Timbalan (?:Menteri|Yang di-Pertua)'
    r'|Menteri(?:\s+Besar)?'
    r'|Setiausaha Parlimen'
    r'|Tuan Yang di-Pertua)'
    r'[^:\n]{2,120}'  # Name + optional [constituency], 2-120 chars
    r')'
    r'\s*:',  # Colon marks end of speaker identification
    re.IGNORECASE,
)
```

Changes: Added `YAB`, `Y.A.B.`, `Tun`, `Menteri Besar`.

In `_clean_speaker_name` (line 211-216), add "tuan pengerusi" to generic_titles:

```python
generic_titles = [
    "tuan yang di-pertua",
    "timbalan yang di-pertua",
    "tuan pengerusi",
    "puan pengerusi",
]
```

In `_find_speaker` (lines 124-166), extend to search up to 2 previous pages:

```python
def _find_speaker(
    raw_text: str,
    normalised: str,
    match_pos: int,
    page_num: int,
    page_texts: dict[int, str],
    page_nums: list[int],
) -> tuple[str, str]:
    """Find the speaker by searching backwards for a Hansard speaker pattern.

    Looks through the current page text before the keyword match. If no
    speaker is found, searches up to 2 previous pages (speakers often
    start on one page and their speech continues across pages).

    Returns:
        (speaker_name, constituency) -- empty strings if not found.
    """
    # Map normalised position to approximate raw text position
    ratio = len(raw_text) / len(normalised) if normalised else 1
    raw_pos = min(len(raw_text), int(match_pos * ratio))

    # Search current page text BEFORE the match
    text_before_match = raw_text[:raw_pos]
    speaker, constituency = _extract_last_speaker(text_before_match)

    if speaker:
        return speaker, constituency

    # If not found, try up to 2 previous pages
    try:
        page_idx = page_nums.index(page_num)
    except ValueError:
        return "", ""

    for lookback in range(1, 3):  # 1 and 2 pages back
        prev_idx = page_idx - lookback
        if prev_idx < 0:
            break
        prev_page_num = page_nums[prev_idx]
        prev_text = page_texts.get(prev_page_num, "")
        if prev_text:
            speaker, constituency = _extract_last_speaker(prev_text)
            if speaker:
                return speaker, constituency

    return "", ""
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest hansard/tests/test_searcher.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/hansard/pipeline/searcher.py backend/hansard/tests/test_searcher.py
git commit -m "feat: improve speaker extraction — more titles, 2-page lookback, generic title filter"
```

---

### Task 2: Tighten Gemini Analysis Prompt

The current prompt is loose — no guidance on summary substance, no speaker hint from regex, no party validation instruction. Tighten it for better v1.0 quality.

**Files:**
- Modify: `backend/parliament/services/gemini_client.py:29-57` (ANALYSIS_PROMPT)
- Modify: `backend/parliament/services/gemini_client.py:71-91` (_build_excerpt — add speaker hint)
- Modify: `backend/parliament/services/gemini_client.py:129-179` (analyse_mention — pass speaker hint)
- Test: `backend/parliament/tests/test_gemini_client.py`

**Step 1: Write failing test for speaker hint in excerpt**

Add to `backend/parliament/tests/test_gemini_client.py`:

```python
def test_excerpt_includes_speaker_hint(self):
    """When mention has mp_name from regex, excerpt should include it as a hint."""
    mention = self._make_mention(
        quote="SJK(T) Ladang Bikam needs repairs.",
        before="Tuan Ganabatirau a/l Veraman [Klang]:",
    )
    mention.mp_name = "Tuan Ganabatirau a/l Veraman"
    mention.mp_constituency = "Klang"
    mention.save()
    excerpt = _build_excerpt(mention)
    self.assertIn("[Speaker detected: Tuan Ganabatirau a/l Veraman", excerpt)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest parliament/tests/test_gemini_client.py::BuildExcerptTests::test_excerpt_includes_speaker_hint -v`
Expected: FAIL (no speaker hint in current implementation)

**Step 3: Update the prompt and excerpt builder**

Replace `ANALYSIS_PROMPT` in `backend/parliament/services/gemini_client.py` (lines 29-57):

```python
ANALYSIS_PROMPT = """\
You are analysing a Malaysian parliamentary Hansard excerpt that mentions Tamil schools (SJK(T)).

Extract the following fields as a JSON object:
- mp_name: Full name of the MP speaking (string, or "" if unclear). Use the speaker hint if provided.
- mp_constituency: Parliamentary constituency code or name (string, or "" if unclear)
- mp_party: Political party (string, or "" if unknown — do NOT guess)
- mention_type: One of BUDGET, QUESTION, POLICY, COMMITMENT, THROWAWAY, OTHER
  - BUDGET: Allocation, funding, or financial request for schools
  - QUESTION: Parliamentary question (oral or written) about Tamil schools
  - POLICY: Policy discussion, proposal, or announcement affecting Tamil schools
  - COMMITMENT: Specific promise or pledge by MP/minister for Tamil schools
  - THROWAWAY: Passing mention without substance (e.g. listing school types)
  - OTHER: Does not fit the above categories
- significance: Integer 1-5
  - 1: Passing mention, no substance (school name listed without discussion)
  - 2: Brief reference with minimal context (one sentence)
  - 3: Substantive discussion (specific issue raised, question asked)
  - 4: Detailed debate with specific data, allocations, or commitments
  - 5: Major policy announcement, large budget allocation, or national-level commitment
- sentiment: One of ADVOCATING, DEFLECTING, PROMISING, NEUTRAL, CRITICAL
  - ADVOCATING: Actively pushing for resources/improvements for Tamil schools
  - DEFLECTING: Avoiding direct answers or redirecting responsibility
  - PROMISING: Making specific commitments or pledges
  - NEUTRAL: Factual statement without clear position
  - CRITICAL: Criticising government/policy handling of Tamil school issues
- change_indicator: One of NEW, REPEAT, ESCALATION, REVERSAL
  - Default to NEW unless the excerpt explicitly references a previous discussion
- summary: 1-2 sentence English summary focused on the MP's stated position or request. Be specific — include amounts, school names, and actions mentioned. Do not pad with filler.

Return ONLY valid JSON, no markdown fences, no extra text.

--- HANSARD EXCERPT ---
{excerpt}
--- END EXCERPT ---
"""
```

Update `_build_excerpt` (lines 71-91) to include the speaker hint:

```python
def _build_excerpt(mention):
    """Build a token-budgeted excerpt from a mention.

    Concatenates context_before + verbatim_quote + context_after,
    truncating to ~1500 chars total. Prepends speaker hint if available.
    """
    parts = []

    # Add speaker hint from regex extraction (if available)
    if mention.mp_name:
        hint = f"[Speaker detected: {mention.mp_name}"
        if mention.mp_constituency:
            hint += f", constituency: {mention.mp_constituency}"
        hint += "]"
        parts.append(hint)

    if mention.context_before:
        parts.append(mention.context_before.strip())
    parts.append(mention.verbatim_quote.strip())
    if mention.context_after:
        parts.append(mention.context_after.strip())

    excerpt = "\n\n".join(parts)

    # Truncate to ~1500 chars to stay within token budget
    max_chars = 1500
    if len(excerpt) > max_chars:
        excerpt = excerpt[:max_chars] + "..."

    return excerpt
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest parliament/tests/test_gemini_client.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/parliament/services/gemini_client.py backend/parliament/tests/test_gemini_client.py
git commit -m "feat: tighten Gemini prompt — significance scale, speaker hint, substance focus"
```

---

### Task 3: Add MP Cross-Reference After Analysis

After Gemini returns `mp_name` and `mp_constituency`, cross-reference against the MP database (222 MPs from Sprint 5.3) to validate and enrich the party field.

**Files:**
- Create: `backend/parliament/services/mp_resolver.py`
- Test: `backend/parliament/tests/test_mp_resolver.py`

**Step 1: Write failing tests**

Create `backend/parliament/tests/test_mp_resolver.py`:

```python
"""Tests for MP resolver — cross-references Gemini output against MP database."""

from django.test import TestCase

from parliament.models import MP
from schools.models import Constituency
from parliament.services.mp_resolver import resolve_mp


class ResolveMPTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P078", name="Klang", state="Selangor",
        )
        cls.mp = MP.objects.create(
            constituency=cls.constituency,
            name="Tuan Ganabatirau a/l Veraman",
            party="PH(DAP)",
        )

    def test_resolve_by_constituency_name(self):
        """Should match MP when constituency name matches."""
        result = resolve_mp(mp_name="", mp_constituency="Klang", mp_party="")
        self.assertEqual(result["mp_name"], "Tuan Ganabatirau a/l Veraman")
        self.assertEqual(result["mp_party"], "PH(DAP)")

    def test_resolve_by_constituency_code(self):
        """Should match MP when constituency code matches."""
        result = resolve_mp(mp_name="", mp_constituency="P078", mp_party="")
        self.assertEqual(result["mp_name"], "Tuan Ganabatirau a/l Veraman")

    def test_resolve_by_name_substring(self):
        """Should match MP when name contains a substring match."""
        result = resolve_mp(mp_name="Ganabatirau", mp_constituency="", mp_party="")
        self.assertEqual(result["mp_constituency"], "Klang")
        self.assertEqual(result["mp_party"], "PH(DAP)")

    def test_no_match_returns_original(self):
        """When no MP matches, return the original values unchanged."""
        result = resolve_mp(mp_name="Unknown Person", mp_constituency="Unknown", mp_party="")
        self.assertEqual(result["mp_name"], "Unknown Person")
        self.assertEqual(result["mp_constituency"], "Unknown")
        self.assertEqual(result["mp_party"], "")

    def test_enriches_party_only(self):
        """When name matches but party is empty, fill in party from DB."""
        result = resolve_mp(mp_name="Tuan Ganabatirau a/l Veraman", mp_constituency="Klang", mp_party="")
        self.assertEqual(result["mp_party"], "PH(DAP)")

    def test_does_not_overwrite_existing_party(self):
        """When party is already set, don't overwrite it."""
        result = resolve_mp(mp_name="Ganabatirau", mp_constituency="Klang", mp_party="BN")
        self.assertEqual(result["mp_party"], "BN")
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest parliament/tests/test_mp_resolver.py -v`
Expected: FAIL (module not found)

**Step 3: Implement mp_resolver.py**

Create `backend/parliament/services/mp_resolver.py`:

```python
"""Cross-reference Gemini-extracted MP data against the MP database.

Looks up the MP by constituency (name or code) or by name substring.
Enriches missing fields (party, constituency) from the database.
"""

import logging

from django.db.models import Q

from parliament.models import MP

logger = logging.getLogger(__name__)


def resolve_mp(mp_name: str, mp_constituency: str, mp_party: str) -> dict:
    """Try to match extracted MP data against the MP database.

    Matching priority:
    1. Constituency code (exact, e.g. "P078")
    2. Constituency name (case-insensitive, e.g. "Klang")
    3. MP name substring (case-insensitive)

    Returns dict with mp_name, mp_constituency, mp_party — enriched
    from DB where possible, original values preserved otherwise.
    """
    result = {
        "mp_name": mp_name,
        "mp_constituency": mp_constituency,
        "mp_party": mp_party,
    }

    mp = None

    # Try constituency match first (most reliable)
    if mp_constituency:
        mp = (
            MP.objects.filter(
                Q(constituency__code__iexact=mp_constituency)
                | Q(constituency__name__iexact=mp_constituency)
            )
            .select_related("constituency")
            .first()
        )

    # Fall back to name match
    if not mp and mp_name:
        # Try exact match first, then substring
        mp = (
            MP.objects.filter(name__iexact=mp_name)
            .select_related("constituency")
            .first()
        )
        if not mp:
            mp = (
                MP.objects.filter(name__icontains=mp_name)
                .select_related("constituency")
                .first()
            )
            if not mp and len(mp_name) > 5:
                # Try each word of the name (skip short titles)
                for word in mp_name.split():
                    if len(word) > 4:
                        mp = (
                            MP.objects.filter(name__icontains=word)
                            .select_related("constituency")
                            .first()
                        )
                        if mp:
                            break

    if mp:
        if not result["mp_name"] or len(result["mp_name"]) < len(mp.name):
            result["mp_name"] = mp.name
        if not result["mp_constituency"]:
            result["mp_constituency"] = mp.constituency.name
        if not result["mp_party"]:
            result["mp_party"] = mp.party
        logger.debug("Resolved MP: %s (%s)", mp.name, mp.constituency.code)

    return result
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest parliament/tests/test_mp_resolver.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/parliament/services/mp_resolver.py backend/parliament/tests/test_mp_resolver.py
git commit -m "feat: add MP resolver — cross-references Gemini output against MP database"
```

---

### Task 4: Wire MP Resolver Into Analysis Pipeline

After Gemini returns analysis, run `resolve_mp` to enrich/validate the MP fields before saving.

**Files:**
- Modify: `backend/hansard/management/commands/run_hansard_pipeline.py:31-55` (run_analysis function)
- Test: `backend/parliament/tests/test_gemini_client.py` (add integration test)

**Step 1: Write failing test**

Add to `backend/parliament/tests/test_gemini_client.py`:

```python
class ApplyAnalysisWithResolverTests(TestCase):
    """Test that analysis pipeline enriches MP data from database."""

    @classmethod
    def setUpTestData(cls):
        cls.constituency = Constituency.objects.create(
            code="P078", name="Klang", state="Selangor",
        )
        cls.mp = MP.objects.create(
            constituency=cls.constituency,
            name="Tuan Ganabatirau a/l Veraman",
            party="PH(DAP)",
        )

    def test_resolver_enriches_party_after_analysis(self):
        from parliament.services.mp_resolver import resolve_mp

        analysis = {
            "mp_name": "Ganabatirau",
            "mp_constituency": "Klang",
            "mp_party": "",
            "mention_type": "QUESTION",
            "significance": 3,
            "sentiment": "ADVOCATING",
            "change_indicator": "NEW",
            "summary": "Asked about SJK(T) funding.",
        }
        resolved = resolve_mp(
            analysis["mp_name"], analysis["mp_constituency"], analysis["mp_party"]
        )
        analysis.update(resolved)
        self.assertEqual(analysis["mp_party"], "PH(DAP)")
        self.assertEqual(analysis["mp_name"], "Tuan Ganabatirau a/l Veraman")
```

Add the required import at the top of the test file:

```python
from parliament.models import MP
from schools.models import Constituency
```

**Step 2: Run test to verify it passes**

Run: `cd backend && python -m pytest parliament/tests/test_gemini_client.py::ApplyAnalysisWithResolverTests -v`
Expected: PASS (resolver already works from Task 3)

**Step 3: Wire resolver into run_analysis**

In `backend/hansard/management/commands/run_hansard_pipeline.py`, update the `run_analysis` function:

```python
def run_analysis() -> dict:
    """Run Gemini analysis on all un-analysed mentions."""
    from django.db import connection
    from parliament.services.gemini_client import analyse_mention, apply_analysis
    from parliament.services.mp_resolver import resolve_mp

    mentions = list(
        HansardMention.objects.filter(ai_summary="")
        .select_related("sitting")
        .order_by("sitting__sitting_date", "page_number")
    )
    if not mentions:
        return {"success": 0, "failed": 0}

    success = 0
    failed = 0
    for mention in mentions:
        analysis = analyse_mention(mention)
        if analysis:
            # Cross-reference against MP database
            resolved = resolve_mp(
                analysis["mp_name"], analysis["mp_constituency"], analysis["mp_party"]
            )
            analysis["mp_name"] = resolved["mp_name"]
            analysis["mp_constituency"] = resolved["mp_constituency"]
            analysis["mp_party"] = resolved["mp_party"]

            apply_analysis(mention, analysis)
            connection.close()
            success += 1
        else:
            failed += 1
        time.sleep(0.5)
    return {"success": success, "failed": failed}
```

**Step 4: Run all tests**

Run: `cd backend && python -m pytest parliament/tests/ hansard/tests/ -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
git add backend/hansard/management/commands/run_hansard_pipeline.py backend/parliament/tests/test_gemini_client.py
git commit -m "feat: wire MP resolver into analysis pipeline — enriches party/name from DB"
```

---

### Task 5: Build rebuild_all_hansards Command

This command resets all COMPLETED sittings, re-processes them through the full pipeline (download, extract, search, match, analyse), then regenerates scorecards and briefs. Designed to run overnight.

**Files:**
- Create: `backend/hansard/management/commands/rebuild_all_hansards.py`
- Test: `backend/hansard/tests/test_rebuild_command.py`

**Step 1: Write failing test**

Create `backend/hansard/tests/test_rebuild_command.py`:

```python
"""Tests for rebuild_all_hansards management command."""

from io import StringIO
from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.test import TestCase

from hansard.models import HansardSitting, HansardMention


class RebuildCommandTests(TestCase):

    def setUp(self):
        self.sitting = HansardSitting.objects.create(
            sitting_date="2026-01-26",
            pdf_url="https://www.parlimen.gov.my/files/hindex/pdf/DR-26012026.pdf",
            pdf_filename="DR-26012026.pdf",
            status=HansardSitting.Status.COMPLETED,
            mention_count=3,
            total_pages=50,
        )
        # Create existing mentions that should be deleted on rebuild
        HansardMention.objects.create(
            sitting=self.sitting,
            verbatim_quote="Old mention",
            page_number=1,
        )

    def test_dry_run_does_not_modify(self):
        """--dry-run should print plan without changing data."""
        out = StringIO()
        call_command("rebuild_all_hansards", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("DRY RUN", output)
        self.assertIn("1 sitting(s)", output)
        # Sitting should still be COMPLETED
        self.sitting.refresh_from_db()
        self.assertEqual(self.sitting.status, HansardSitting.Status.COMPLETED)

    def test_dry_run_state_filter(self):
        """--state should filter sittings (but this sitting has no state — tests empty result)."""
        out = StringIO()
        # Create a second sitting we can identify
        HansardSitting.objects.create(
            sitting_date="2026-01-27",
            pdf_url="https://example.com/test2.pdf",
            pdf_filename="test2.pdf",
            status=HansardSitting.Status.COMPLETED,
        )
        call_command("rebuild_all_hansards", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("2 sitting(s)", output)

    @patch("hansard.management.commands.rebuild_all_hansards.process_single_sitting")
    def test_rebuild_resets_status_and_processes(self, mock_process):
        """Rebuild should reset sitting to PENDING, delete old mentions, and call process."""
        mock_process.return_value = {"mentions": 5, "status": "ok"}
        out = StringIO()
        call_command("rebuild_all_hansards", "--skip-analysis", stdout=out)

        self.sitting.refresh_from_db()
        # The mock replaces the actual processing, so we verify it was called
        mock_process.assert_called_once()
        # Old mentions should be deleted before processing
        self.assertEqual(
            HansardMention.objects.filter(sitting=self.sitting).count(), 0
        )

    def test_failed_sittings_skipped_by_default(self):
        """FAILED sittings should be skipped unless --include-failed is passed."""
        self.sitting.status = HansardSitting.Status.FAILED
        self.sitting.save()

        out = StringIO()
        call_command("rebuild_all_hansards", "--dry-run", stdout=out)
        output = out.getvalue()
        self.assertIn("0 sitting(s)", output)

    def test_include_failed_flag(self):
        """--include-failed should include FAILED sittings."""
        self.sitting.status = HansardSitting.Status.FAILED
        self.sitting.save()

        out = StringIO()
        call_command("rebuild_all_hansards", "--dry-run", "--include-failed", stdout=out)
        output = out.getvalue()
        self.assertIn("1 sitting(s)", output)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest hansard/tests/test_rebuild_command.py -v`
Expected: FAIL (command does not exist)

**Step 3: Implement the command**

Create `backend/hansard/management/commands/rebuild_all_hansards.py`:

```python
"""Rebuild all Hansard sittings: re-download, re-extract, re-search, re-match, re-analyse.

Usage:
    python manage.py rebuild_all_hansards                # Full rebuild
    python manage.py rebuild_all_hansards --dry-run      # Preview
    python manage.py rebuild_all_hansards --skip-analysis # Skip Gemini (fast re-extract)
    python manage.py rebuild_all_hansards --include-failed # Include FAILED sittings
    python manage.py rebuild_all_hansards --limit 10     # Process only first 10
"""

import tempfile
import time

from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from hansard.models import HansardMention, HansardSitting, SchoolAlias
from hansard.pipeline.downloader import download_hansard
from hansard.pipeline.extractor import extract_text
from hansard.pipeline.keywords import get_all_keywords
from hansard.pipeline.matcher import match_mentions
from hansard.pipeline.searcher import search_keywords


def process_single_sitting(sitting, keywords, skip_matching=False):
    """Re-process a single sitting through the pipeline.

    Returns dict with processing results.
    """
    dest_dir = tempfile.mkdtemp(prefix="hansard_rebuild_")

    # Download
    pdf_path = download_hansard(sitting.pdf_url, dest_dir)

    # Extract
    pages = extract_text(pdf_path)
    sitting.total_pages = len(pages)

    # Search
    matches = search_keywords(pages, keywords)

    # Delete old mentions
    sitting.mentions.all().delete()

    # Store new mentions
    mentions = []
    for match in matches:
        mentions.append(HansardMention(
            sitting=sitting,
            page_number=match["page_number"],
            verbatim_quote=match["verbatim_quote"],
            context_before=match["context_before"],
            context_after=match["context_after"],
            keyword_matched=match["keyword_matched"],
            mp_name=match.get("speaker_name", ""),
            mp_constituency=match.get("speaker_constituency", ""),
        ))
    HansardMention.objects.bulk_create(mentions)

    # Match to schools
    matched_count = 0
    if not skip_matching and SchoolAlias.objects.exists() and mentions:
        mention_qs = HansardMention.objects.filter(sitting=sitting)
        result = match_mentions(mention_qs)
        matched_count = result.get("matched", 0)

    # Update sitting
    sitting.mention_count = len(mentions)
    sitting.processed_at = timezone.now()
    sitting.status = HansardSitting.Status.COMPLETED
    sitting.error_message = ""
    sitting.save(update_fields=[
        "total_pages", "mention_count", "processed_at", "status", "error_message",
    ])

    return {
        "mentions": len(mentions),
        "matched": matched_count,
        "pages": len(pages),
        "status": "ok",
    }


class Command(BaseCommand):
    help = "Rebuild all Hansard sittings: re-download, re-extract, re-search, re-match."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Preview what would be rebuilt without making changes.",
        )
        parser.add_argument(
            "--skip-analysis", action="store_true",
            help="Skip Gemini AI analysis (run extraction + matching only).",
        )
        parser.add_argument(
            "--include-failed", action="store_true",
            help="Include FAILED sittings in the rebuild.",
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="Process only the first N sittings (for testing).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        skip_analysis = options["skip_analysis"]
        include_failed = options["include_failed"]
        limit = options["limit"]

        # Build queryset
        statuses = [HansardSitting.Status.COMPLETED]
        if include_failed:
            statuses.append(HansardSitting.Status.FAILED)

        sittings = (
            HansardSitting.objects.filter(status__in=statuses)
            .order_by("sitting_date")
        )
        if limit:
            sittings = sittings[:limit]

        sitting_list = list(sittings)
        total = len(sitting_list)

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN ==="))
            self.stdout.write(f"Would rebuild {total} sitting(s):")
            for s in sitting_list:
                self.stdout.write(f"  {s.sitting_date} — {s.mention_count} mentions, {s.total_pages or '?'} pages")
            total_mentions = sum(s.mention_count for s in sitting_list)
            self.stdout.write(f"\nTotal mentions to reprocess: {total_mentions}")
            if not skip_analysis:
                self.stdout.write(f"Estimated Gemini calls: ~{total_mentions}")
            self.stdout.write(self.style.WARNING("=== DRY RUN COMPLETE ==="))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Rebuilding {total} Hansard sittings"
        ))

        keywords = get_all_keywords()
        success = 0
        failed = 0
        total_mentions = 0

        for i, sitting in enumerate(sitting_list, 1):
            self.stdout.write(
                f"\n[{i}/{total}] {sitting.sitting_date} "
                f"({sitting.pdf_filename})..."
            )
            try:
                result = process_single_sitting(sitting, keywords)
                total_mentions += result["mentions"]
                self.stdout.write(self.style.SUCCESS(
                    f"  OK: {result['pages']} pages, "
                    f"{result['mentions']} mentions, "
                    f"{result['matched']} matched"
                ))
                success += 1
                connection.close()
            except Exception as e:
                sitting.status = HansardSitting.Status.FAILED
                sitting.error_message = str(e)[:500]
                sitting.save(update_fields=["status", "error_message"])
                self.stdout.write(self.style.ERROR(f"  FAILED: {e}"))
                failed += 1

        self.stdout.write(self.style.MIGRATE_HEADING("\nExtraction complete"))
        self.stdout.write(f"  Success: {success}/{total}")
        self.stdout.write(f"  Failed: {failed}/{total}")
        self.stdout.write(f"  Total mentions: {total_mentions}")

        # Run analysis if not skipped
        if not skip_analysis and total_mentions > 0:
            self.stdout.write(self.style.MIGRATE_HEADING(
                "\nRunning Gemini analysis..."
            ))
            from hansard.management.commands.run_hansard_pipeline import run_analysis
            analysis_result = run_analysis()
            self.stdout.write(self.style.SUCCESS(
                f"  Analysis: {analysis_result['success']} success, "
                f"{analysis_result['failed']} failed"
            ))

        # Regenerate scorecards and briefs
        self.stdout.write(self.style.MIGRATE_HEADING("\nRegenerating scorecards and briefs..."))
        from parliament.services.scorecard import update_all_scorecards
        from parliament.services.brief_generator import generate_all_pending_briefs
        update_all_scorecards()
        generate_all_pending_briefs()
        self.stdout.write(self.style.SUCCESS("Done."))

        self.stdout.write(self.style.SUCCESS(
            f"\nRebuild complete! {success} sittings, {total_mentions} mentions."
        ))
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest hansard/tests/test_rebuild_command.py -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `cd backend && python -m pytest --tb=short -q`
Expected: All 771+ tests pass

**Step 6: Commit**

```bash
git add backend/hansard/management/commands/rebuild_all_hansards.py backend/hansard/tests/test_rebuild_command.py
git commit -m "feat: add rebuild_all_hansards command — full pipeline rebuild for v1.0"
```

---

### Task 6: Run the Rebuild (Production)

This is the actual overnight run against Supabase production.

**Pre-flight checks:**
1. Ensure `GEMINI_API_KEY` is set in environment
2. Ensure `DATABASE_URL` uses **direct connection** (port 5432, not pooler 6543) — critical for bulk writes
3. Run `--dry-run` first to verify the plan

**Step 1: Dry run**

```bash
cd backend
python manage.py rebuild_all_hansards --dry-run
```

Expected: Lists all ~97 sittings with mention counts. Verify the total looks right (~193 current mentions).

**Step 2: Test with --limit 3**

```bash
python manage.py rebuild_all_hansards --limit 3 --skip-analysis
```

Expected: 3 sittings re-processed successfully. Check logs for mention counts.

**Step 3: Full rebuild**

```bash
python manage.py rebuild_all_hansards 2>&1 | tee rebuild_log.txt
```

This will:
- Re-download all 97 PDFs (uses temp dir, cleaned up automatically)
- Re-extract text with improved speaker regex
- Re-search keywords (may find new mentions missed before)
- Re-match schools
- Re-analyse all mentions with improved Gemini prompt + MP resolver
- Regenerate scorecards and briefs

Expected runtime: ~30-60 minutes (depends on network + Gemini rate limits).

**Step 4: Verify results**

```bash
python manage.py shell -c "
from hansard.models import HansardSitting, HansardMention
print(f'Sittings: {HansardSitting.objects.filter(status=\"COMPLETED\").count()}')
print(f'Mentions: {HansardMention.objects.count()}')
print(f'With AI summary: {HansardMention.objects.exclude(ai_summary=\"\").count()}')
print(f'With MP name: {HansardMention.objects.exclude(mp_name=\"\").count()}')
print(f'With party: {HansardMention.objects.exclude(mp_party=\"\").count()}')
"
```

Compare before/after counts. We expect:
- Same or more sittings completed
- Possibly more mentions (improved regex catches more)
- Higher % with MP name (better speaker extraction + Gemini hint)
- Higher % with party (MP resolver enrichment)

**Step 5: Commit rebuild log**

```bash
git add -A
git commit -m "feat: historical rebuild complete — v1.0 data foundation"
```

---

### Task 7: Update CLAUDE.md and Sprint Close

After successful rebuild, update docs and close sprint.

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `CLAUDE.md`

**Step 1: Add Sprint 5.2 to CHANGELOG.md**

Add under the existing sprint entries:

```markdown
## Sprint 5.2 — Historical Rebuild (2026-03-XX)

### Changed
- Improved speaker extraction regex — added YAB, Tun, Menteri Besar titles; extended lookback to 2 pages; filtered Tuan/Puan Pengerusi as generic
- Tightened Gemini prompt — explicit significance scale (1-5 with examples), substance-focused summaries, speaker hint from regex, "do not guess" for unknown party
- Added MP resolver — cross-references Gemini output against 222 MPs in database, enriches party and constituency fields

### Added
- `rebuild_all_hansards` management command (--dry-run, --skip-analysis, --include-failed, --limit)
- MP resolver service (`parliament/services/mp_resolver.py`)
- N new tests (total: XXXX)

### Fixed
- Rebuilt all 97 Hansard sittings with improved pipeline — better speaker identification, more accurate party attribution, substance-focused summaries
```

**Step 2: Update CLAUDE.md**

- Update sprint table with Sprint 5.2 row
- Update test count
- Update status to "v1.0 ready" or similar
- Add `rebuild_all_hansards` to commands section

**Step 3: Commit and push**

```bash
git add CHANGELOG.md CLAUDE.md
git commit -m "docs: sprint 5.2 close — historical rebuild, v1.0 data ready"
git push
```
