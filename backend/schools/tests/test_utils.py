"""Tests for schools.utils — title case and phone formatting utilities."""

import pytest

from schools.utils import format_phone, format_state, to_proper_case


class TestToProperCase:
    """Test to_proper_case() for Malaysian school data."""

    def test_standard_words(self):
        assert to_proper_case("LADANG SUNGAI RAYA") == "Ladang Sungai Raya"

    def test_sjkt_prefix_preserved(self):
        assert to_proper_case("SJK(T) LADANG BIKAM") == "SJK(T) Ladang Bikam"

    def test_ppd_abbreviation(self):
        assert to_proper_case("PPD LANGKAWI") == "PPD Langkawi"

    def test_ppw_abbreviation(self):
        assert to_proper_case("PPW SENTUL") == "PPW Sentul"

    def test_jpn_abbreviation(self):
        assert to_proper_case("JPN PERLIS") == "JPN Perlis"

    def test_short_forms(self):
        assert to_proper_case("SJK(T) LDG SG BULOH") == "SJK(T) Ldg Sg Buloh"

    def test_short_form_with_dot(self):
        assert to_proper_case("SJK(T) KG.SIMEE") == "SJK(T) Kg.Simee"

    def test_roman_numerals(self):
        assert (
            to_proper_case("SJK(T) LADANG SG WANGI II")
            == "SJK(T) Ladang Sg Wangi II"
        )

    def test_apostrophe_possessive(self):
        assert to_proper_case("SAINT MARY'S") == "Saint Mary's"

    def test_sjkt_saint_marys(self):
        assert to_proper_case("SJK(T) SAINT MARY'S") == "SJK(T) Saint Mary's"

    def test_apostrophe_dato(self):
        assert to_proper_case("DATO' K.PATHMANABAN") == "Dato' K.Pathmanaban"

    def test_sjkt_dato_full_name(self):
        assert (
            to_proper_case("SJK(T) TAN SRI DATO' MANICKAVASAGAM")
            == "SJK(T) Tan Sri Dato' Manickavasagam"
        )

    def test_single_quote_wrapper(self):
        assert to_proper_case("LDG WEST COUNTRY 'TIMUR'") == "Ldg West Country 'Timur'"

    def test_sjkt_single_quote_wrapper(self):
        assert (
            to_proper_case("SJK(T) LDG WEST COUNTRY 'TIMUR'")
            == "SJK(T) Ldg West Country 'Timur'"
        )

    def test_parenthetical_hd_abbreviation(self):
        assert to_proper_case("SJK(T) LDG SG BARU (H/D)") == "SJK(T) Ldg Sg Baru (H/D)"

    def test_state_name(self):
        assert to_proper_case("NEGERI SEMBILAN") == "Negeri Sembilan"

    def test_long_state_name(self):
        assert (
            to_proper_case("WILAYAH PERSEKUTUAN KUALA LUMPUR")
            == "Wilayah Persekutuan Kuala Lumpur"
        )

    def test_parenthetical_tamil(self):
        assert (
            to_proper_case("SEKOLAH JENIS KEBANGSAAN (TAMIL) LADANG SUNGAI RAYA")
            == "Sekolah Jenis Kebangsaan (Tamil) Ladang Sungai Raya"
        )

    def test_address_with_comma(self):
        assert (
            to_proper_case("JALAN AYER HANGAT, LADANG SUNGAI RAYA")
            == "Jalan Ayer Hangat, Ladang Sungai Raya"
        )

    def test_empty_string(self):
        assert to_proper_case("") == ""

    def test_none_input(self):
        assert to_proper_case(None) == ""

    def test_st_short_form(self):
        assert (
            to_proper_case("SJK(T) ST PHILOMENA CONVENT")
            == "SJK(T) St Philomena Convent"
        )

    def test_parenthetical_regular_words(self):
        assert (
            to_proper_case("SJK(T) CONVENT SEREMBAN (KOMPLEKS WAWASAN)")
            == "SJK(T) Convent Seremban (Kompleks Wawasan)"
        )

    def test_pjs_section_code_stays_uppercase(self):
        # PJS (Petaling Jaya Selatan) must not title-case to "Pjs"
        assert to_proper_case("SJK(T) PJS 1") == "SJK(T) PJS 1"

    def test_pjs_higher_section_number(self):
        assert to_proper_case("SJK(T) PJS 7") == "SJK(T) PJS 7"


class TestFormatPhone:
    """Test format_phone() for Malaysian phone numbers."""

    def test_single_digit_area_code_4(self):
        assert format_phone("049663429") == "+60-4 966 3429"

    def test_single_digit_area_code_5(self):
        assert format_phone("052547982") == "+60-5 254 7982"

    def test_single_digit_area_code_3_eight_digits(self):
        assert format_phone("0356781234") == "+60-3 5678 1234"

    def test_double_digit_area_code_82(self):
        assert format_phone("0821234567") == "+60-82 123 4567"

    def test_already_formatted(self):
        assert format_phone("+60-4 966 3429") == "+60-4 966 3429"

    def test_empty_string(self):
        assert format_phone("") == ""

    def test_none_input(self):
        assert format_phone(None) == ""

    def test_with_existing_dash_format(self):
        assert format_phone("04-966 3429") == "+60-4 966 3429"

    def test_unparseable_returns_original(self):
        assert format_phone("CALL OFFICE") == "CALL OFFICE"


class TestFormatState:
    """Test format_state() — collapses W.P. variants to compact form."""

    def test_kuala_lumpur_title_case(self):
        assert format_state("Wilayah Persekutuan Kuala Lumpur") == "W.P. Kuala Lumpur"

    def test_kuala_lumpur_all_caps(self):
        assert format_state("WILAYAH PERSEKUTUAN KUALA LUMPUR") == "W.P. Kuala Lumpur"

    def test_putrajaya(self):
        assert format_state("Wilayah Persekutuan Putrajaya") == "W.P. Putrajaya"

    def test_labuan(self):
        assert format_state("Wilayah Persekutuan Labuan") == "W.P. Labuan"

    def test_regular_state_unchanged(self):
        assert format_state("Selangor") == "Selangor"
        assert format_state("Johor") == "Johor"
        assert format_state("Pulau Pinang") == "Pulau Pinang"

    def test_idempotent_on_abbreviated_form(self):
        # Re-running on already-abbreviated input is a no-op.
        assert format_state("W.P. Kuala Lumpur") == "W.P. Kuala Lumpur"

    def test_blank_input_returns_empty(self):
        assert format_state("") == ""
        assert format_state(None) == ""

    def test_whitespace_only_returns_empty(self):
        assert format_state("   ") == ""

    def test_trims_surrounding_whitespace(self):
        assert format_state("  Wilayah Persekutuan Kuala Lumpur  ") == "W.P. Kuala Lumpur"

    def test_unknown_state_passes_through(self):
        # Hypothetical state name not in the canonical map → trim + return.
        assert format_state("Some New State") == "Some New State"
