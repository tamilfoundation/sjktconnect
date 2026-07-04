from django.db import models


class Constituency(models.Model):
    """Parliamentary constituency (Parlimen). 222 total, 122 have SJK(T) schools."""

    code = models.CharField(max_length=10, primary_key=True)  # e.g. "P140"
    name = models.CharField(max_length=100)  # e.g. "Segamat"
    state = models.CharField(max_length=50, db_index=True)
    mp_name = models.CharField(max_length=100, blank=True, default="")
    mp_party = models.CharField(max_length=100, blank=True, default="")
    mp_coalition = models.CharField(max_length=50, blank=True, default="")
    indian_population = models.IntegerField(null=True, blank=True)
    indian_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_income = models.IntegerField(null=True, blank=True)
    poverty_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    gini = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    unemployment_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # ── GE15 Election Data ────────────────────────────────────────
    ge15_winning_margin = models.IntegerField(
        null=True, blank=True,
        help_text="Vote margin between winner and runner-up in GE15 (2022)",
    )
    ge15_total_voters = models.IntegerField(
        null=True, blank=True,
        help_text="Total registered/eligible voters in GE15 (2022)",
    )
    ge15_indian_voter_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Percentage of Indian voters in GE15 (from undi.info)",
    )

    boundary_wkt = models.TextField(
        blank=True, default="",
        help_text="Boundary polygon in OGC WKT format. Computed by unioning DUN boundaries.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "constituencies"

    def __str__(self):
        return f"{self.code} {self.name}"


class DUN(models.Model):
    """State constituency (Dewan Undangan Negeri). 613 total.

    DUN codes like 'N01' repeat across states — each state has its own
    numbering. Uniqueness is per-constituency: (code, constituency).
    """

    code = models.CharField(max_length=10, db_index=True)  # e.g. "N01"
    name = models.CharField(max_length=100)  # e.g. "Buloh Kasap"
    constituency = models.ForeignKey(
        Constituency, on_delete=models.CASCADE, related_name="duns"
    )
    state = models.CharField(max_length=50, db_index=True)
    adun_name = models.CharField(max_length=100, blank=True, default="")
    adun_party = models.CharField(max_length=100, blank=True, default="")
    adun_coalition = models.CharField(max_length=50, blank=True, default="")
    indian_population = models.IntegerField(null=True, blank=True)
    indian_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    boundary_wkt = models.TextField(
        blank=True, default="",
        help_text="Boundary polygon in OGC WKT format from Political Constituencies CSV.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]
        verbose_name = "DUN"
        verbose_name_plural = "DUNs"
        unique_together = [("code", "constituency")]

    def __str__(self):
        return f"{self.code} {self.name}"


class School(models.Model):
    """Tamil primary school (SJK(T)). 528 schools from MOE Jan 2026 data."""

    moe_code = models.CharField(max_length=10, primary_key=True)  # e.g. "JBD0050"
    name = models.CharField(max_length=200)  # Full MOE name
    short_name = models.CharField(max_length=150)  # "SJK(T) Ladang Bikam"
    name_tamil = models.CharField(max_length=200, blank=True, default="")
    address = models.TextField(blank=True, default="")
    postcode = models.CharField(max_length=10, blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    state = models.CharField(max_length=50, db_index=True)
    ppd = models.CharField(
        max_length=100, blank=True, default="", db_index=True,
        help_text="Pejabat Pendidikan Daerah (District Education Office)",
    )
    constituency = models.ForeignKey(
        Constituency, null=True, blank=True, on_delete=models.SET_NULL, related_name="schools"
    )
    dun = models.ForeignKey(
        DUN, null=True, blank=True, on_delete=models.SET_NULL, related_name="schools"
    )
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    fax = models.CharField(max_length=30, blank=True, default="")

    # ── Bank Details (for donations) ─────────────────────────────────
    bank_name = models.CharField(max_length=100, blank=True, default="")
    bank_account_number = models.CharField(max_length=50, blank=True, default="")
    bank_account_name = models.CharField(max_length=200, blank=True, default="")

    gps_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    gps_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    gps_verified = models.BooleanField(default=False)
    enrolment = models.IntegerField(default=0)
    preschool_enrolment = models.IntegerField(default=0)
    special_enrolment = models.IntegerField(default=0)
    teacher_count = models.IntegerField(default=0)
    grade = models.CharField(max_length=10, blank=True, default="")
    assistance_type = models.CharField(max_length=50, blank=True, default="")
    session_count = models.IntegerField(default=1)
    session_type = models.CharField(max_length=20, blank=True, default="")
    skm_eligible = models.BooleanField(default=False)
    location_type = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    claimed_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When a school admin first claimed this page via @moe.edu.my sign-in",
    )

    # Sprint 31 (2026-06-27): per-locale school history / origin story.
    # Shape: {"en": "...", "ms": "...", "ta": "..."} — any locale may be
    # absent. Display falls back to English when current locale is empty.
    # Status flips from UNVERIFIED → SCHOOL_REVIEWED when a bound school
    # admin edits the field, → VERIFIED by SUPERADMIN.
    history = models.JSONField(default=dict, blank=True)
    history_source_urls = models.JSONField(default=list, blank=True)
    HISTORY_STATUS_CHOICES = [
        ("UNVERIFIED", "Unverified — drawn from public sources"),
        ("SCHOOL_REVIEWED", "Reviewed by school admin"),
        ("VERIFIED", "Verified by SUPERADMIN"),
    ]
    history_status = models.CharField(
        max_length=20,
        choices=HISTORY_STATUS_CHOICES,
        default="UNVERIFIED",
        blank=True,
    )
    history_updated_at = models.DateTimeField(null=True, blank=True)
    # Sprint 31 follow-up: 3-5 pivotal milestones per locale, rendered as
    # compact pills above the prose for skimmers. Shape:
    # {"en": ["1946 founded", "..."], "ms": ["1946 ditubuhkan", "..."]}
    history_key_dates = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["moe_code"]

    def __str__(self):
        return f"{self.moe_code} {self.short_name}"


class SchoolEnrolmentSnapshot(models.Model):
    """One MOE Risalah Maklumat snapshot of a school's student count.

    Each row is (school, snapshot_date, students) — populated by
    `import_enrolment_snapshots` from historical MOE Risalah Excel files
    (Jan 2018, Jan 2020, Jun 2022, Sep 2023, Mar 2025, ...) plus the
    current count read from the live `School.enrolment` field at import
    time. Used by the SchoolEnrolmentTrend sparkline on the public page.
    """

    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="enrolment_snapshots"
    )
    snapshot_date = models.DateField(db_index=True)
    students = models.IntegerField()
    source = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Origin file or 'live' for the current-DB snapshot.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["snapshot_date"]
        unique_together = [("school", "snapshot_date")]

    def __str__(self):
        return f"{self.school.moe_code} {self.snapshot_date}: {self.students}"


class SchoolLeader(models.Model):
    """Key leadership contacts for a school. Names are public; phone/email are private."""

    ROLE_CHOICES = [
        ("board_chair", "Board Chairman"),
        ("headmaster", "Headmaster"),
        ("pta_chair", "PTA Chairman"),
        ("alumni_chair", "Alumni Association Chairman"),
    ]

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
        ordering = ["role"]
        constraints = [
            models.UniqueConstraint(
                fields=["school", "role"],
                condition=models.Q(is_active=True),
                name="unique_active_role_per_school",
            ),
        ]

    def __str__(self):
        return f"{self.get_role_display()}: {self.name} ({self.school.short_name})"
