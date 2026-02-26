"""Tests for import_constituencies management command."""

import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from schools.management.commands.import_constituencies import (
    parse_code_name,
    parse_income,
    parse_indian_percentage,
)
from schools.models import Constituency, DUN


class ParseHelperTest(TestCase):
    def test_parse_code_name_standard(self):
        code, name = parse_code_name("P140 Segamat")
        assert code == "P140"
        assert name == "Segamat"

    def test_parse_code_name_dun(self):
        code, name = parse_code_name("N01 Buloh Kasap")
        assert code == "N01"
        assert name == "Buloh Kasap"

    def test_parse_code_name_empty(self):
        code, name = parse_code_name("")
        assert code is None

    def test_parse_income_standard(self):
        assert parse_income(" RM6,399 ") == 6399

    def test_parse_income_empty(self):
        assert parse_income("") is None

    def test_parse_indian_percentage_range(self):
        result = parse_indian_percentage("5.01 - 10%")
        assert result == 7.5  # midpoint of 5.01 and 10, rounded to 2dp

    def test_parse_indian_percentage_direct(self):
        result = parse_indian_percentage("9.1")
        assert result == 9.1


class ImportConstituenciesTest(TestCase):
    def _create_test_csv(self, rows):
        """Create a temp CSV file with constituency data."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="cp1252", newline=""
        )
        import csv

        writer = csv.writer(tmp)
        # Headers matching the real CSV (note "Parliment" typo)
        writer.writerow([
            "WKT", "DUN", "Parliment", "Indians", "Indians %", "Ranges",
            "Ave. Income", "Incidence of Poverty", "GINI", "Unemployment Rate",
            "ADUN", "Coalition (Party)", "Coalition",
            "Ahli Parliament", "MP Coalition (Party)", "MP Coalition",
        ])
        for row in rows:
            writer.writerow(row)
        tmp.close()
        return tmp.name

    def test_imports_constituencies_and_duns(self):
        rows = [
            [
                "POLYGON ((0 0, 1 1, 0 1, 0 0))",  # WKT — skipped in Phase 0
                "N01 Buloh Kasap", "P140 Segamat",
                "2615", "5.01 - 10%", "5.01 - 10%",
                " RM6,399 ", "3.4", "0.304", "5.7",
                "Zahari Sarip", "BN (UMNO)", "BN",
                "Yuneswaran Ramaraj", "PH (PKR)", "PH",
            ],
            [
                "POLYGON ((0 0, 1 1, 0 1, 0 0))",
                "N02 Jementah", "P140 Segamat",
                "3527", "5.01 - 10%", "5.01 - 10%",
                " RM6,726 ", "2.1", "0.326", "2.5",
                "Ng Kor Sim", "PH (DAP)", "PH",
                "Yuneswaran Ramaraj", "PH (PKR)", "PH",
            ],
            [
                "POLYGON ((0 0, 1 1, 0 1, 0 0))",
                "N03 Pemanis", "P141 Sekijang",
                "558", "1 - 5%", "1 - 5%",
                " RM6,979 ", "2.3", "0.344", "2.1",
                "Anuar Abdul Manap", "BN (UMNO)", "BN",
                "Zaliha Mustafa", "PH (PKR)", "PH",
            ],
        ]
        path = self._create_test_csv(rows)
        call_command("import_constituencies", "--file", path)

        # 2 unique constituencies (P140, P141)
        assert Constituency.objects.count() == 2
        # 3 DUNs
        assert DUN.objects.count() == 3

        # Check constituency data
        c = Constituency.objects.get(code="P140")
        assert c.name == "Segamat"
        assert c.mp_name == "Yuneswaran Ramaraj"
        assert c.mp_party == "PH (PKR)"

        # Check DUN data
        d = DUN.objects.get(code="N01")
        assert d.name == "Buloh Kasap"
        assert d.constituency == c
        assert d.adun_name == "Zahari Sarip"
        assert d.indian_population == 2615

        # Check WKT boundary is stored on DUN
        assert d.boundary_wkt.startswith("POLYGON")

        # Check constituency boundary is computed (union of DUN boundaries)
        c.refresh_from_db()
        assert c.boundary_wkt != ""
        assert "POLYGON" in c.boundary_wkt

        Path(path).unlink()

    def test_idempotent_reimport(self):
        rows = [
            [
                "POLYGON ((0 0))", "N01 Buloh Kasap", "P140 Segamat",
                "2615", "9.1", "", " RM6,399 ", "3.4", "0.304", "5.7",
                "Zahari", "BN (UMNO)", "BN", "Yunes", "PH (PKR)", "PH",
            ],
        ]
        path = self._create_test_csv(rows)
        call_command("import_constituencies", "--file", path)
        call_command("import_constituencies", "--file", path)

        assert Constituency.objects.count() == 1
        assert DUN.objects.count() == 1
        Path(path).unlink()

    def test_dry_run_creates_nothing(self):
        rows = [
            [
                "POLYGON ((0 0))", "N01 Buloh Kasap", "P140 Segamat",
                "2615", "9.1", "", " RM6,399 ", "3.4", "0.304", "5.7",
                "Zahari", "BN (UMNO)", "BN", "Yunes", "PH (PKR)", "PH",
            ],
        ]
        path = self._create_test_csv(rows)
        call_command("import_constituencies", "--file", path, "--dry-run")

        assert Constituency.objects.count() == 0
        assert DUN.objects.count() == 0
        Path(path).unlink()
