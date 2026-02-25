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
        max_length=100, blank=True, default="",
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
    is_active = models.BooleanField(default=True)
    last_verified = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["moe_code"]

    def __str__(self):
        return f"{self.moe_code} {self.short_name}"
