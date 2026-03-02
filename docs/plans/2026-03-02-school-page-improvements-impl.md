# School Page Improvements — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix data quality (proper case, phone, address), redesign school page layout (side-by-side desktop, compact mobile), add school leadership model, and set up i18n infrastructure.

**Architecture:** Three sprints — Sprint 3.1 (backend data migrations + SchoolLeader model), Sprint 3.2 (frontend layout redesign), Sprint 3.3 (i18n infrastructure). Each sprint is self-contained and deployable.

**Tech Stack:** Django 5.x, Next.js 14, next-intl, Tailwind CSS, PostgreSQL (Supabase)

**Design doc:** `docs/plans/2026-03-02-school-page-improvements-design.md`

---

## Sprint 3.1: Data Quality + SchoolLeader Model

### Task 1: Title Case Utility

**Files:**
- Create: `backend/schools/utils.py`
- Test: `backend/schools/tests/test_utils.py`

**Step 1: Write the failing tests**

```python
# backend/schools/tests/test_utils.py
from django.test import TestCase
from schools.utils import to_proper_case


class ProperCaseTests(TestCase):
    """Test title-case conversion with Malaysian school name edge cases."""

    def test_basic_title_case(self):
        self.assertEqual(to_proper_case("LADANG SUNGAI RAYA"), "Ladang Sungai Raya")

    def test_preserves_sjkt_prefix(self):
        self.assertEqual(
            to_proper_case("SJK(T) LADANG BIKAM"), "SJK(T) Ladang Bikam"
        )

    def test_preserves_ppd_prefix(self):
        self.assertEqual(to_proper_case("PPD LANGKAWI"), "PPD Langkawi")
        self.assertEqual(to_proper_case("PPW SENTUL"), "PPW Sentul")
        self.assertEqual(to_proper_case("JPN PERLIS"), "JPN Perlis")

    def test_preserves_abbreviations(self):
        self.assertEqual(to_proper_case("SJK(T) LDG SG BULOH"), "SJK(T) Ldg Sg Buloh")
        self.assertEqual(to_proper_case("SJK(T) KG.SIMEE"), "SJK(T) Kg.Simee")

    def test_preserves_roman_numerals(self):
        self.assertEqual(
            to_proper_case("SJK(T) LADANG SG WANGI II"),
            "SJK(T) Ladang Sg Wangi II",
        )

    def test_handles_apostrophes(self):
        self.assertEqual(to_proper_case("SAINT MARY'S"), "Saint Mary's")
        self.assertEqual(
            to_proper_case("DATO' K.PATHMANABAN"), "Dato' K.Pathmanaban"
        )

    def test_handles_quoted_names(self):
        self.assertEqual(
            to_proper_case("LDG WEST COUNTRY 'TIMUR'"),
            "Ldg West Country 'Timur'",
        )

    def test_handles_parenthetical(self):
        self.assertEqual(
            to_proper_case("SJK(T) LDG SG BARU (H/D)"),
            "SJK(T) Ldg Sg Baru (H/D)",
        )

    def test_state_names(self):
        self.assertEqual(to_proper_case("NEGERI SEMBILAN"), "Negeri Sembilan")
        self.assertEqual(
            to_proper_case("WILAYAH PERSEKUTUAN KUALA LUMPUR"),
            "Wilayah Persekutuan Kuala Lumpur",
        )

    def test_full_moe_name(self):
        self.assertEqual(
            to_proper_case("SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG SUNGAI RAYA"),
            "Sekolah Jenis Kebangsaan (Tamil) Ladang Sungai Raya",
        )

    def test_address(self):
        self.assertEqual(
            to_proper_case("JALAN AYER HANGAT, LADANG SUNGAI RAYA"),
            "Jalan Ayer Hangat, Ladang Sungai Raya",
        )

    def test_empty_and_none(self):
        self.assertEqual(to_proper_case(""), "")
        self.assertEqual(to_proper_case(None), "")

    def test_convent(self):
        self.assertEqual(
            to_proper_case("SJK(T) ST PHILOMENA CONVENT"),
            "SJK(T) St Philomena Convent",
        )

    def test_kompleks(self):
        self.assertEqual(
            to_proper_case("SJK(T) CONVENT SEREMBAN (KOMPLEKS WAWASAN)"),
            "SJK(T) Convent Seremban (Kompleks Wawasan)",
        )
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest schools/tests/test_utils.py -v`
Expected: FAIL — `schools.utils` does not exist

**Step 3: Write the utility**

```python
# backend/schools/utils.py
"""Text formatting utilities for Malaysian school data."""

import re

# Abbreviations that should stay UPPERCASE
UPPERCASE_WORDS = {
    "SJK(T)", "PPD", "PPW", "JPN", "D/A", "H/D",
    "II", "III", "IV", "V", "VI",
}

# Words that stay uppercase only when standalone (not as prefix)
UPPERCASE_STANDALONE = {"LDG", "SG", "KG", "JLN", "ST"}


def to_proper_case(text: str | None) -> str:
    """Convert ALL CAPS text to proper title case, preserving abbreviations.

    Rules:
    - Standard words: LADANG → Ladang
    - Abbreviations: SJK(T), PPD, PPW, JPN → stay uppercase
    - Short forms: LDG, SG, KG, JLN, ST → Ldg, Sg, Kg, Jln, St
    - Roman numerals: II, III → stay uppercase
    - Apostrophes: DATO' → Dato', MARY'S → Mary's
    - Parenthetical: (TAMIL) → (Tamil), (H/D) → (H/D)
    """
    if not text:
        return ""

    # Process parenthetical expressions separately
    def title_parens(match):
        inner = match.group(1)
        if inner in UPPERCASE_WORDS or "/" in inner:
            return f"({inner})"
        return f"({inner.title()})"

    # Replace parenthetical content with placeholders, process, restore
    result = re.sub(r"\(([^)]+)\)", title_parens, text)

    # Split on spaces, preserving punctuation attached to words
    words = result.split()
    processed = []
    for word in words:
        # Skip already-processed parenthetical
        if word.startswith("("):
            processed.append(word)
            continue

        # Strip trailing punctuation for matching
        clean = word.rstrip(".,;:'\"")
        suffix = word[len(clean):]

        if clean in UPPERCASE_WORDS:
            processed.append(word)  # Keep as-is
        elif clean in UPPERCASE_STANDALONE:
            processed.append(clean.title() + suffix)
        else:
            # Title case the word
            titled = clean.title() + suffix
            processed.append(titled)

    return " ".join(processed)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest schools/tests/test_utils.py -v`
Expected: All PASS. Some tests may need tuning — iterate until all edge cases pass.

**Step 5: Commit**

```bash
git add backend/schools/utils.py backend/schools/tests/test_utils.py
git commit -m "feat: add to_proper_case utility for Malaysian school data"
```

---

### Task 2: Phone Formatting Utility

**Files:**
- Modify: `backend/schools/utils.py`
- Modify: `backend/schools/tests/test_utils.py`

**Step 1: Write the failing tests**

```python
# Append to backend/schools/tests/test_utils.py
from schools.utils import format_phone


class PhoneFormatTests(TestCase):
    """Test Malaysian phone number formatting."""

    def test_landline_single_digit_area(self):
        """Area codes 3, 4, 5, 6, 7, 9 are single digit."""
        self.assertEqual(format_phone("049663429"), "+60-4 966 3429")
        self.assertEqual(format_phone("052547982"), "+60-5 254 7982")
        self.assertEqual(format_phone("0356781234"), "+60-3 5678 1234")

    def test_landline_double_digit_area(self):
        """Area codes 82-89 are double digit."""
        self.assertEqual(format_phone("0821234567"), "+60-82 123 4567")

    def test_already_formatted(self):
        self.assertEqual(format_phone("+60-4 966 3429"), "+60-4 966 3429")

    def test_empty(self):
        self.assertEqual(format_phone(""), "")
        self.assertEqual(format_phone(None), "")

    def test_strips_spaces_and_dashes(self):
        self.assertEqual(format_phone("04-966 3429"), "+60-4 966 3429")

    def test_malformed_returns_original(self):
        """If we can't parse it, return as-is rather than mangle it."""
        self.assertEqual(format_phone("CALL OFFICE"), "CALL OFFICE")
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest schools/tests/test_utils.py::PhoneFormatTests -v`
Expected: FAIL — `format_phone` not importable

**Step 3: Write the utility**

```python
# Append to backend/schools/utils.py
import logging

logger = logging.getLogger(__name__)

# Single-digit area codes in Malaysia
SINGLE_DIGIT_AREAS = {"3", "4", "5", "6", "7", "9"}


def format_phone(phone: str | None) -> str:
    """Format Malaysian phone number to +60-X XXX XXXX format.

    - Strips leading 0, prefixes +60-
    - Single-digit area codes: 3, 4, 5, 6, 7, 9
    - Double-digit area codes: 82-89
    - Returns original if already formatted or unparseable
    """
    if not phone:
        return ""

    # Already formatted
    if phone.startswith("+60"):
        return phone

    # Strip all non-digits
    digits = re.sub(r"[^0-9]", "", phone)

    if not digits or not digits.startswith("0"):
        if digits:
            logger.warning("Unusual phone number (no leading 0): %s", phone)
        return phone  # Return original if unparseable

    # Remove leading 0
    digits = digits[1:]

    # Determine area code length
    if digits[0] in SINGLE_DIGIT_AREAS:
        area = digits[0]
        rest = digits[1:]
    elif len(digits) >= 2 and digits[:2] in {"82", "83", "84", "85", "86", "87", "88", "89"}:
        area = digits[:2]
        rest = digits[2:]
    else:
        area = digits[0]
        rest = digits[1:]

    # Group remaining digits: 3+4 for 7 digits, 4+4 for 8 digits
    if len(rest) <= 7:
        formatted_rest = f"{rest[:3]} {rest[3:]}"
    else:
        formatted_rest = f"{rest[:4]} {rest[4:]}"

    return f"+60-{area} {formatted_rest.strip()}"
```

**Step 4: Run tests, iterate until all pass**

Run: `cd backend && python -m pytest schools/tests/test_utils.py -v`

**Step 5: Commit**

```bash
git add backend/schools/utils.py backend/schools/tests/test_utils.py
git commit -m "feat: add format_phone utility for Malaysian phone numbers"
```

---

### Task 3: Data Migration — Proper Case + Phone + Address

**Files:**
- Create: `backend/schools/migrations/0003_proper_case_data.py`
- Test: `backend/schools/tests/test_migrations.py`

**Step 1: Write the failing test**

```python
# backend/schools/tests/test_migrations.py
from django.test import TestCase
from schools.models import School


class ProperCaseDataTests(TestCase):
    """Verify proper case is applied after migration."""

    def test_short_name_is_title_case(self):
        """After migration, short_name should not be all caps."""
        caps_schools = School.objects.filter(short_name__regex=r"^SJK\(T\) [A-Z ]+$")
        self.assertEqual(
            caps_schools.count(), 0,
            f"Found {caps_schools.count()} schools still in all caps"
        )
```

This test will pass only after the migration runs. Skip it for now.

**Step 2: Create the data migration**

Run: `cd backend && python manage.py makemigrations schools --empty -n proper_case_data`

Then edit the generated file:

```python
# backend/schools/migrations/0003_proper_case_data.py
from django.db import migrations


def apply_proper_case(apps, schema_editor):
    """Apply proper case to all text fields imported from MOE in ALL CAPS."""
    from schools.utils import to_proper_case, format_phone

    School = apps.get_model("schools", "School")

    for school in School.objects.all():
        school.name = to_proper_case(school.name)
        school.short_name = to_proper_case(school.short_name)
        school.state = to_proper_case(school.state)
        school.ppd = to_proper_case(school.ppd)
        school.address = to_proper_case(school.address)
        school.city = to_proper_case(school.city)
        school.email = school.email.lower() if school.email else ""
        school.phone = format_phone(school.phone)
        school.fax = format_phone(school.fax)
        school.save()


def reverse_noop(apps, schema_editor):
    """No reverse — original caps data is not preserved."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("schools", "0002_add_boundary_wkt"),
    ]

    operations = [
        migrations.RunPython(apply_proper_case, reverse_noop),
    ]
```

**Step 3: Run the migration locally**

Run: `cd backend && python manage.py migrate schools`
Expected: `Applying schools.0003_proper_case_data... OK`

**Step 4: Verify with Django shell**

Run: `cd backend && python manage.py shell -c "from schools.models import School; s = School.objects.first(); print(s.short_name, '|', s.state, '|', s.ppd, '|', s.phone, '|', s.email)"`
Expected: `SJK(T) Tapah | Perak | PPD Batang Padang | +60-5 ... | abd0073@moe.edu.my`

**Step 5: Run full test suite**

Run: `cd backend && python -m pytest -x -q`
Expected: All tests pass. Some existing tests may have hardcoded ALL CAPS values — fix them.

**Step 6: Commit**

```bash
git add backend/schools/migrations/0003_proper_case_data.py backend/schools/tests/
git commit -m "feat: data migration for proper case, phone format, lowercase email"
```

---

### Task 4: Update Import Script

**Files:**
- Modify: `backend/schools/management/commands/import_schools.py` (lines 30-38, 270-273)

**Step 1: Update make_short_name to produce proper case**

The existing `make_short_name()` at line 30 needs to use `to_proper_case`:

```python
from schools.utils import to_proper_case, format_phone

def make_short_name(full_name):
    """Convert MOE full name to short form with proper case.
    'SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM' -> 'SJK(T) Ladang Bikam'
    """
    if MOE_PREFIX in full_name.upper():
        suffix = full_name[len(MOE_PREFIX):].strip()
        return f"{SHORT_PREFIX} {to_proper_case(suffix)}"
    return to_proper_case(full_name)
```

**Step 2: Update the `update_or_create` defaults to apply formatting**

In the school_data dict construction (~line 250-270), apply `to_proper_case` and `format_phone`:

```python
school_data = {
    "name": to_proper_case(full_name),
    "short_name": short_name,  # Already proper-cased by make_short_name
    "state": to_proper_case(state),
    "ppd": to_proper_case(ppd),
    "address": to_proper_case(address),
    "city": to_proper_case(city),
    "email": email.lower() if email else "",
    "phone": format_phone(phone),
    "fax": format_phone(fax),
    # ... rest unchanged
}
```

**Step 3: Run existing import tests**

Run: `cd backend && python -m pytest schools/tests/ -v -k import`
Expected: Some tests may need updating for proper case expectations.

**Step 4: Commit**

```bash
git add backend/schools/management/commands/import_schools.py
git commit -m "feat: import script now produces proper case and formatted phones"
```

---

### Task 5: SchoolLeader Model

**Files:**
- Modify: `backend/schools/models.py` (append after School class, line 117)
- Modify: `backend/schools/admin.py` (add inline)
- Create migration via `makemigrations`
- Test: `backend/schools/tests/test_leader_model.py`

**Step 1: Write the failing tests**

```python
# backend/schools/tests/test_leader_model.py
from django.test import TestCase
from schools.models import School, SchoolLeader


class SchoolLeaderModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(
            moe_code="TEST001",
            name="SJK(T) Test School",
            short_name="SJK(T) Test School",
            state="Perak",
        )

    def test_create_leader(self):
        leader = SchoolLeader.objects.create(
            school=self.school,
            role="board_chair",
            name="En. Suresh",
        )
        self.assertEqual(leader.role, "board_chair")
        self.assertEqual(leader.name, "En. Suresh")
        self.assertEqual(str(leader), "Board Chairman: En. Suresh (SJK(T) Test School)")

    def test_role_choices(self):
        """All four roles should be valid."""
        for role in ["board_chair", "headmaster", "pta_chair", "alumni_chair"]:
            leader = SchoolLeader(school=self.school, role=role, name="Test")
            leader.full_clean()  # Should not raise

    def test_phone_and_email_optional(self):
        leader = SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="Pn. Kavitha"
        )
        self.assertEqual(leader.phone, "")
        self.assertEqual(leader.email, "")

    def test_unique_active_role_per_school(self):
        """Only one active leader per role per school."""
        SchoolLeader.objects.create(
            school=self.school, role="headmaster", name="Person A"
        )
        # Second active headmaster should fail
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SchoolLeader.objects.create(
                school=self.school, role="headmaster", name="Person B"
            )

    def test_ordering(self):
        """Leaders should be ordered: board_chair, headmaster, pta_chair, alumni_chair."""
        SchoolLeader.objects.create(school=self.school, role="pta_chair", name="C")
        SchoolLeader.objects.create(school=self.school, role="board_chair", name="A")
        SchoolLeader.objects.create(school=self.school, role="headmaster", name="B")
        leaders = list(self.school.leaders.values_list("role", flat=True))
        self.assertEqual(leaders, ["board_chair", "headmaster", "pta_chair"])
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest schools/tests/test_leader_model.py -v`
Expected: FAIL — `SchoolLeader` does not exist

**Step 3: Write the model**

Append to `backend/schools/models.py` after line 117:

```python
class SchoolLeader(models.Model):
    """Key leadership contacts for a school. Names are public; phone/email are private."""

    ROLE_CHOICES = [
        ("board_chair", "Board Chairman"),
        ("headmaster", "Headmaster"),
        ("pta_chair", "PTA Chairman"),
        ("alumni_chair", "Alumni Association Chairman"),
    ]

    # Ordering map for consistent display order
    ROLE_ORDER = {
        "board_chair": 0,
        "headmaster": 1,
        "pta_chair": 2,
        "alumni_chair": 3,
    }

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="leaders"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["role"]  # Uses alphabetical which matches desired order
        unique_together = [("school", "role", "is_active")]
        # Note: unique_together with is_active=True enforced at app level

    def __str__(self):
        return f"{self.get_role_display()}: {self.name} ({self.school.short_name})"
```

Note: The `unique_together` on `(school, role, is_active)` won't perfectly enforce "one active per role" at the DB level. Use a unique constraint with condition instead:

```python
    class Meta:
        ordering = ["role"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "role"],
                condition=models.Q(is_active=True),
                name="unique_active_role_per_school",
            ),
        ]
```

**Step 4: Create and run migration**

Run: `cd backend && python manage.py makemigrations schools -n add_school_leader && python manage.py migrate`

**Step 5: Add admin inline**

In `backend/schools/admin.py`, add:

```python
from schools.models import School, SchoolLeader

class SchoolLeaderInline(admin.TabularInline):
    model = SchoolLeader
    extra = 0
    fields = ("role", "name", "phone", "email", "is_active")

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    # ... existing fields ...
    inlines = [SchoolLeaderInline]
```

**Step 6: Run all tests**

Run: `cd backend && python -m pytest -x -q`
Expected: All pass

**Step 7: Commit**

```bash
git add backend/schools/models.py backend/schools/admin.py backend/schools/migrations/ backend/schools/tests/test_leader_model.py
git commit -m "feat: add SchoolLeader model with admin inline"
```

---

### Task 6: SchoolLeader API

**Files:**
- Modify: `backend/schools/api/serializers.py`
- Modify: `backend/schools/api/views.py` (or nested in detail serializer)
- Test: `backend/schools/tests/test_school_api.py` (add leader tests)

**Step 1: Write the failing test**

```python
# Add to existing test_school_api.py
def test_school_detail_includes_leaders(self):
    """Leaders should appear in school detail with name and role only (no phone/email)."""
    from schools.models import SchoolLeader
    SchoolLeader.objects.create(
        school=self.school, role="board_chair", name="En. Suresh",
        phone="0123456789", email="suresh@example.com"
    )
    SchoolLeader.objects.create(
        school=self.school, role="headmaster", name="Pn. Kavitha",
    )
    response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/")
    data = response.json()
    self.assertIn("leaders", data)
    self.assertEqual(len(data["leaders"]), 2)
    # Board chair first
    self.assertEqual(data["leaders"][0]["role"], "board_chair")
    self.assertEqual(data["leaders"][0]["role_display"], "Board Chairman")
    self.assertEqual(data["leaders"][0]["name"], "En. Suresh")
    # Private fields NOT exposed
    self.assertNotIn("phone", data["leaders"][0])
    self.assertNotIn("email", data["leaders"][0])

def test_school_detail_no_leaders(self):
    """Schools with no leaders should return empty list."""
    response = self.client.get(f"/api/v1/schools/{self.school.moe_code}/")
    data = response.json()
    self.assertEqual(data["leaders"], [])
```

**Step 2: Add serializer**

```python
# In backend/schools/api/serializers.py
from schools.models import SchoolLeader

class SchoolLeaderSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = SchoolLeader
        fields = ["role", "role_display", "name"]
```

Add to `SchoolDetailSerializer`:
```python
leaders = SchoolLeaderSerializer(many=True, read_only=True, source="leaders")
```

And add `"leaders"` to the `fields` list.

Ensure the queryset in the view prefetches: `.prefetch_related("leaders")`

**Step 3: Run tests, iterate**

Run: `cd backend && python -m pytest schools/tests/test_school_api.py -v`

**Step 4: Commit**

```bash
git add backend/schools/api/serializers.py backend/schools/tests/test_school_api.py
git commit -m "feat: expose school leaders in detail API (name + role only)"
```

---

### Task 7: Run Full Backend Tests + Sprint 3.1 Close

**Step 1: Run full test suite**

Run: `cd backend && python -m pytest -v`
Expected: All ~621+ tests pass (plus new ones)

**Step 2: Update CHANGELOG**

Append to `CHANGELOG.md`:

```markdown
## Sprint 3.1: Data Quality + School Leadership (2026-03-XX)
- Proper case migration: school names, addresses, states, PPD names
- Phone numbers standardised to +60-X XXX XXXX format
- Emails lowercased
- Address comma between postcode and city removed
- Import script updated for future re-imports
- SchoolLeader model: Board Chairman, Headmaster, PTA Chair, Alumni Chair
- Leaders API: name + role exposed publicly, phone/email admin-only
- Admin: inline leader management on School admin page
```

**Step 3: Commit and push**

```bash
git add -A && git commit -m "chore: sprint 3.1 close — data quality + school leadership"
git push
```

---

## Sprint 3.2: Frontend Layout Redesign

### Task 8: Update TypeScript Types

**Files:**
- Modify: `frontend/lib/types.ts` (lines 23-45)

**Step 1: Add SchoolLeader type and update SchoolDetail**

```typescript
// Add after SchoolImageData interface (~line 22)
export interface SchoolLeader {
  role: string;
  role_display: string;
  name: string;
}

// Add to SchoolDetail interface:
  leaders: SchoolLeader[];
```

**Step 2: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat: add SchoolLeader type to frontend"
```

---

### Task 9: Redesign School Page — Side-by-Side Layout

**Files:**
- Modify: `frontend/app/school/[moe_code]/page.tsx` (lines 77-157)
- Modify: `frontend/components/SchoolProfile.tsx` (entire file)

**Step 1: Write/update frontend tests**

Add tests for:
- Combined student count in stat card (primary + preschool)
- SKM stat card removed
- Full MOE name not rendered
- MOE code not duplicated
- Side-by-side layout has correct grid classes
- SchoolLeader section renders when leaders exist
- SchoolLeader section hidden when no leaders

**Step 2: Restructure page.tsx**

Replace the current layout (lines 77-157) with:

```tsx
return (
  <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
    <Breadcrumb items={breadcrumbItems} />

    {/* Hero: Side-by-side on desktop, stacked on mobile */}
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
      {/* Photo — 3/5 width on desktop */}
      <div className="lg:col-span-3">
        <SchoolPhotoGallery
          images={school.images}
          imageUrl={school.image_url}
          schoolName={displayName}
        />
      </div>

      {/* Name + Stats — 2/5 width on desktop */}
      <div className="lg:col-span-2 flex flex-col justify-center space-y-3">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
          {displayName}
        </h1>
        {school.name_tamil && (
          <p className="text-lg text-gray-700">{school.name_tamil}</p>
        )}
        <p className="text-sm text-gray-500">
          {school.moe_code} · {school.state} · {school.ppd}
        </p>
        <EditSchoolLink moeCode={school.moe_code} />

        {/* Stat cards — compact row */}
        <div className="grid grid-cols-3 gap-3 pt-2">
          <StatCard
            label="Students"
            value={(school.enrolment ?? 0) + (school.preschool_enrolment ?? 0)}
          />
          <StatCard label="Teachers" value={school.teacher_count ?? 0} />
          <StatCard label="Grade" value={school.grade || "—"} />
        </div>
      </div>
    </div>

    {/* Main content */}
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <SchoolProfile school={school} />
        {/* ... MiniMap, MentionsSection, NewsWatch, SchoolHistory unchanged */}
      </div>
      <div className="space-y-6">
        {/* Sidebar unchanged */}
      </div>
    </div>

    <div className="mt-8">
      <ClaimButton moeCode={school.moe_code} />
    </div>
  </div>
);
```

Remove the full MOE name line (`school.name`) from the header area.

**Step 3: Rewrite SchoolProfile.tsx**

Remove:
- SKM stat card (line 16-19)
- MOE Code detail row (line 28)
- Full Name detail row (line 29)
- Old stat cards section (lines 11-20) — moved to page.tsx

Update:
- Address: use `" "` instead of `", "` between postcode and city
- Assistance Type: map `SBK` → `Government-Aided (SBK)`, `SK` → `Government (SK)`
- Show student breakdown: School, Preschool, Special Needs as separate rows (always, not conditional)

Add:
- School Leadership section (after School Details)

```tsx
{/* School Leadership */}
{school.leaders && school.leaders.length > 0 && (
  <div className="bg-white rounded-lg border border-gray-200 p-6">
    <h2 className="text-lg font-semibold text-gray-800 mb-4">
      School Leadership
    </h2>
    <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-3 text-sm">
      {school.leaders.map((leader) => (
        <DetailRow
          key={leader.role}
          label={leader.role_display}
          value={leader.name}
        />
      ))}
    </dl>
  </div>
)}
```

**Step 4: Run frontend tests**

Run: `cd frontend && npm test`

**Step 5: Visual check**

Run: `cd frontend && npm run dev` → check desktop and mobile layouts

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: school page redesign — side-by-side layout, leadership section"
```

---

### Task 10: Update Remaining Frontend Components

**Files:**
- Review and update if state/ppd/name values appear in:
  - `frontend/components/SchoolMarkers.tsx` — info window displays
  - `frontend/components/SearchBox.tsx` — search result display
  - `frontend/components/SchoolTable.tsx` — table rows
  - `frontend/components/ConstituencyList.tsx` — state column
  - `frontend/components/StateFilter.tsx` — state dropdown

Since data is now proper case in the database, these components should display correctly without code changes. **Verify visually** that all pages look right.

**Step 1: Check the state filter dropdown still works**

The state values changed from `PERAK` to `Perak`. The frontend filter passes the state value to the API `?state=` query param. Verify the backend filter is case-insensitive or update it.

Check: `backend/schools/api/views.py` — the state filter. If it uses `filter(state=...)` it needs exact match. If data is now `Perak`, the filter and API must agree.

**Step 2: Run all frontend tests**

Run: `cd frontend && npm test`

**Step 3: Commit any fixes**

---

### Task 11: Sprint 3.2 Close

**Step 1: Run full test suites**

Backend: `cd backend && python -m pytest -q`
Frontend: `cd frontend && npm test`

**Step 2: Update CHANGELOG**

**Step 3: Commit and push**

```bash
git add -A && git commit -m "chore: sprint 3.2 close — school page layout redesign"
git push
```

---

## Sprint 3.3: i18n Infrastructure

### Task 12: Install and Configure next-intl

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/messages/en.json`
- Create: `frontend/messages/ta.json`
- Create: `frontend/i18n/request.ts`
- Create: `frontend/i18n/routing.ts`
- Modify: `frontend/next.config.js`
- Create: `frontend/middleware.ts`

Follow next-intl App Router setup guide. Key steps:

1. `cd frontend && npm install next-intl`
2. Create routing config with `en` and `ta` locales, `en` as default
3. Create middleware for locale detection/redirect
4. Move `app/` pages under `app/[locale]/`
5. Update `layout.tsx` to use locale from params for `<html lang={locale}>`

This is a large structural change. Refer to next-intl docs for exact configuration.

**Commit after setup works with English only (no Tamil translations yet).**

---

### Task 13: Extract English Strings

**Files:**
- Modify: `frontend/messages/en.json`
- Modify: All ~20 component files to use `useTranslations()` hook

Extract the ~140 hardcoded strings into `messages/en.json` organised by component:

```json
{
  "header": {
    "title": "SJK(T) Connect",
    "schoolMap": "School Map",
    "constituencies": "Constituencies",
    "parliamentWatch": "Parliament Watch"
  },
  "schoolProfile": {
    "schoolDetails": "School Details",
    "address": "Address",
    "email": "Email",
    "phone": "Phone",
    "locationType": "Location Type",
    "assistanceType": "Assistance Type",
    "sessions": "Sessions",
    "school": "School",
    "preschool": "Preschool",
    "specialNeeds": "Special Needs",
    "students": "students",
    "schoolLeadership": "School Leadership",
    "politicalRepresentation": "Political Representation",
    "constituency": "Constituency",
    "dun": "DUN"
  }
}
```

Update each component to use `const t = useTranslations("schoolProfile")` and replace hardcoded strings with `t("schoolDetails")`, etc.

**This is tedious but mechanical. Work through components one at a time, test after each.**

---

### Task 14: Tamil Translations

**Files:**
- Modify: `frontend/messages/ta.json`

Translate all ~140 strings to Tamil. Key translations:

```json
{
  "header": {
    "title": "SJK(T) இணைப்பு",
    "schoolMap": "பள்ளி வரைபடம்",
    "constituencies": "தொகுதிகள்",
    "parliamentWatch": "நாடாளுமன்ற கண்காணிப்பு"
  },
  "schoolProfile": {
    "schoolDetails": "பள்ளி விவரங்கள்",
    "address": "முகவரி",
    "students": "மாணவர்கள்"
  }
}
```

**Must follow `tamil-style-guide.md` for all Tamil text.**

---

### Task 15: Language Switcher + Sprint 3.3 Close

**Files:**
- Modify: `frontend/components/Header.tsx` — add language toggle (EN | தமிழ்)
- Run full test suites
- Update CHANGELOG
- Commit and push

---

## Deployment Notes

- Sprint 3.1 requires running `python manage.py migrate` on production after deploying backend
- Sprint 3.2 is frontend-only deploy
- Sprint 3.3 is frontend-only deploy (URL structure changes from `/school/X` to `/en/school/X` — set up redirects)
- Each sprint is independently deployable
