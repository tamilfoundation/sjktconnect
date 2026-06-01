"""Tests for import_schools management command."""

import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook

from schools.management.commands.import_schools import make_short_name
from schools.models import Constituency, DUN, School


def create_test_excel(rows, path):
    """Create a test Excel file with MOE-format headers and data rows."""
    headers = [
        "NEGERI", "PPD", "PARLIMEN", "DUN", "PERINGKAT", "JENIS/LABEL",
        "KODSEKOLAH", "NAMASEKOLAH", "ALAMATSURAT", "POSKODSURAT",
        "BANDARSURAT", "NOTELEFON", "NOFAX", "EMAIL", "LOKASI", "GRED",
        "BANTUAN", "BILSESI", "SESI", "ENROLMEN PRASEKOLAH", "ENROLMEN",
        "ENROLMEN KHAS", "GURU", "PRASEKOLAH", "INTEGRASI",
        "KOORDINATXX", "KOORDINATYY", "SKM<=150",
    ]
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


class MakeShortNameTest(TestCase):
    def test_standard_conversion(self):
        assert make_short_name("SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM") == "SJK(T) Ladang Bikam"

    def test_already_short(self):
        assert make_short_name("SJK(T) LADANG BIKAM") == "SJK(T) Ladang Bikam"

    def test_empty_string(self):
        assert make_short_name("") == ""


class ImportSchoolsTest(TestCase):
    def setUp(self):
        # Create constituencies and DUNs that the schools will link to
        self.c1 = Constituency.objects.create(code="P140", name="Segamat", state="")
        self.d1 = DUN.objects.create(code="N01", name="Buloh Kasap", constituency=self.c1, state="")

    def _create_test_file(self, rows):
        """Create a temp Excel file and return the path."""
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.close()
        create_test_excel(rows, tmp.name)
        return tmp.name

    def test_imports_sjkt_schools(self):
        rows = [
            # NEGERI, PPD, PARLIMEN, DUN, PERINGKAT, JENIS/LABEL, KODSEKOLAH, NAMASEKOLAH,
            # ALAMATSURAT, POSKODSURAT, BANDARSURAT, NOTELEFON, NOFAX, EMAIL, LOKASI, GRED,
            # BANTUAN, BILSESI, SESI, ENROLMEN PRASEKOLAH, ENROLMEN, ENROLMEN KHAS, GURU,
            # PRASEKOLAH, INTEGRASI, KOORDINATXX, KOORDINATYY, SKM<=150
            [
                "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
                "SJK(T)", "JBD0050", "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
                "Jalan Bikam", "85000", "Segamat", "07-1234567", "", "JBD0050@moe.edu.my",
                "Luar Bandar", "A", "BANTUAN PENUH", 1, "PAGI", 0, 120, 0, 8,
                0, 0, 102.81, 2.51, "",
            ],
            [
                "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
                "SJK(T)", "JBD0051", "SEKOLAH JENIS KEBANGSAAN (TAMIL) PEKAN JABI",
                "Jalan Jabi", "85000", "Segamat", "07-2345678", "", "JBD0051@moe.edu.my",
                "Luar Bandar", "B", "BANTUAN PENUH", 1, "PAGI", 10, 85, 0, 6,
                0, 0, 102.82, 2.52, "",
            ],
            # Non-SJK(T) school — should be skipped
            [
                "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
                "SK", "JBD0100", "SEKOLAH KEBANGSAAN SEGAMAT",
                "Jalan Segamat", "85000", "Segamat", "", "", "",
                "Bandar", "A", "", 1, "PAGI", 0, 500, 0, 25,
                0, 0, 102.80, 2.50, "",
            ],
        ]
        path = self._create_test_file(rows)
        call_command("import_schools", path, "--gps-file", "nonexistent.csv")

        assert School.objects.count() == 2
        school = School.objects.get(moe_code="JBD0050")
        assert school.short_name == "SJK(T) Ladang Bikam"
        assert school.state == "Johor"
        assert school.enrolment == 120
        assert school.teacher_count == 8
        assert school.constituency == self.c1
        assert school.dun == self.d1

        Path(path).unlink()

    def test_idempotent_reimport(self):
        rows = [
            [
                "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
                "SJK(T)", "JBD0050", "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
                "Jalan Bikam", "85000", "Segamat", "", "", "",
                "Luar Bandar", "A", "", 1, "PAGI", 0, 120, 0, 8,
                0, 0, 102.81, 2.51, "",
            ],
        ]
        path = self._create_test_file(rows)
        call_command("import_schools", path, "--gps-file", "nonexistent.csv")
        call_command("import_schools", path, "--gps-file", "nonexistent.csv")

        assert School.objects.count() == 1
        Path(path).unlink()

    def test_dry_run_creates_nothing(self):
        rows = [
            [
                "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
                "SJK(T)", "JBD0050", "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
                "Jalan Bikam", "85000", "Segamat", "", "", "",
                "Luar Bandar", "A", "", 1, "PAGI", 0, 120, 0, 8,
                0, 0, 102.81, 2.51, "",
            ],
        ]
        path = self._create_test_file(rows)
        call_command("import_schools", path, "--dry-run", "--gps-file", "nonexistent.csv")

        assert School.objects.count() == 0
        Path(path).unlink()

    def test_skip_fields_preserves_existing_values(self):
        """--skip-fields leaves named fields untouched on re-import while other
        fields still refresh. Guards the April-2026 regression where the MOE
        file types postcode/phone/fax as floats (losing the leading zero)."""
        rows_v1 = [[
            "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
            "SJK(T)", "JBD0050", "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
            "Jalan Bikam", "85000", "Segamat", "07-1234567", "07-7654321", "JBD0050@moe.edu.my",
            "Luar Bandar", "A", "BANTUAN PENUH", 1, "PAGI", 0, 120, 0, 8,
            0, 0, 102.81, 2.51, "",
        ]]
        path1 = self._create_test_file(rows_v1)
        call_command("import_schools", path1, "--gps-file", "nonexistent.csv")

        school = School.objects.get(moe_code="JBD0050")
        assert school.postcode == "85000"
        assert school.phone == "+60-7 123 4567"
        assert school.fax == "+60-7 765 4321"
        assert school.enrolment == 120
        assert float(school.gps_lat) == 2.51
        assert float(school.gps_lng) == 102.81

        # v2 mimics the April file: contact columns are floats (mangled), and
        # enrolment/teacher figures genuinely refreshed.
        rows_v2 = [[
            "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
            "SJK(T)", "JBD0050", "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
            "Jalan Bikam", 35000.0, "Segamat", 71234567.0, 77654321.0, "JBD0050@moe.edu.my",
            "Luar Bandar", "A", "BANTUAN PENUH", 1, "PAGI", 0, 200, 0, 10,
            0, 0, 99.99, 9.99, "",
        ]]
        path2 = self._create_test_file(rows_v2)
        call_command(
            "import_schools", path2, "--gps-file", "nonexistent.csv",
            "--skip-fields", "postcode,phone,fax,gps_lat,gps_lng,gps_verified",
        )

        school.refresh_from_db()
        # Skipped fields keep their known-good January values
        assert school.postcode == "85000"
        assert school.phone == "+60-7 123 4567"
        assert school.fax == "+60-7 765 4321"
        assert float(school.gps_lat) == 2.51
        assert float(school.gps_lng) == 102.81
        # Non-skipped fields are refreshed from the new file
        assert school.enrolment == 200
        assert school.teacher_count == 10

        Path(path1).unlink()
        Path(path2).unlink()

    def test_skip_fields_rejects_unknown_field(self):
        """An invalid --skip-fields name aborts the import (typo protection)."""
        rows = [[
            "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
            "SJK(T)", "JBD0050", "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
            "Jalan Bikam", "85000", "Segamat", "", "", "",
            "Luar Bandar", "A", "", 1, "PAGI", 0, 120, 0, 8,
            0, 0, 102.81, 2.51, "",
        ]]
        path = self._create_test_file(rows)
        call_command(
            "import_schools", path, "--gps-file", "nonexistent.csv",
            "--skip-fields", "phone,not_a_real_field",
        )
        assert School.objects.count() == 0
        Path(path).unlink()

    def test_updates_constituency_state(self):
        """Importing schools should fill in constituency state from MOE data,
        title-cased and W.P.-normalised (Sprint 24 #10c)."""
        rows = [
            [
                "JOHOR", "PPD SEGAMAT", "P140 SEGAMAT", "N01 BULOH KASAP", "SEKOLAH RENDAH",
                "SJK(T)", "JBD0050", "SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG BIKAM",
                "Jalan Bikam", "85000", "Segamat", "", "", "",
                "", "A", "", 1, "PAGI", 0, 100, 0, 8,
                0, 0, 102.81, 2.51, "",
            ],
        ]
        path = self._create_test_file(rows)
        call_command("import_schools", path, "--gps-file", "nonexistent.csv")

        self.c1.refresh_from_db()
        assert self.c1.state == "Johor"
        Path(path).unlink()

    def test_constituency_state_normalised_for_wp_kuala_lumpur(self):
        """W.P. abbreviation applied to Constituency.state at import."""
        c_kl = Constituency.objects.create(code="P116", name="Setiawangsa", state="")
        DUN.objects.create(code="N01b", name="Wangsa Maju", constituency=c_kl, state="")
        rows = [
            [
                "WILAYAH PERSEKUTUAN KUALA LUMPUR", "PPD WP KL", "P116 SETIAWANGSA",
                "N01b WANGSA MAJU", "SEKOLAH RENDAH",
                "SJK(T)", "WBD0001", "SEKOLAH JENIS KEBANGSAAN (TAMIL) WANGSA MAJU",
                "Jalan Wangsa", "53300", "Kuala Lumpur", "", "", "",
                "", "A", "", 1, "PAGI", 0, 100, 0, 8,
                0, 0, 101.7, 3.2, "",
            ],
        ]
        path = self._create_test_file(rows)
        call_command("import_schools", path, "--gps-file", "nonexistent.csv")

        school = School.objects.get(moe_code="WBD0001")
        c_kl.refresh_from_db()
        assert school.state == "W.P. Kuala Lumpur"
        assert c_kl.state == "W.P. Kuala Lumpur"
        Path(path).unlink()
