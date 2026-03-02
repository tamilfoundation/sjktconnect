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

    def test_updates_constituency_state(self):
        """Importing schools should fill in constituency state from MOE data."""
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
        assert self.c1.state == "JOHOR"
        Path(path).unlink()
