"""Tests for resolve_subject() and _clean() helper."""

import pytest
from sdamgia_tools import resolve_subject, _clean, VALID_SUBJECTS


class TestResolveSubject:
    # --- English codes ---
    def test_english_code_math(self):
        assert resolve_subject("math") == "math"

    def test_english_code_mathb(self):
        assert resolve_subject("mathb") == "mathb"

    def test_english_code_rus(self):
        assert resolve_subject("rus") == "rus"

    def test_english_code_inf(self):
        assert resolve_subject("inf") == "inf"

    def test_english_code_phys(self):
        assert resolve_subject("phys") == "phys"

    def test_english_code_chem(self):
        assert resolve_subject("chem") == "chem"

    def test_english_code_bio(self):
        assert resolve_subject("bio") == "bio"

    def test_english_code_hist(self):
        assert resolve_subject("hist") == "hist"

    def test_english_code_soc(self):
        assert resolve_subject("soc") == "soc"

    def test_english_code_eng_maps_to_en(self):
        # The sdamgia-api library uses 'en', not 'eng'
        assert resolve_subject("eng") == "en"

    def test_english_code_en(self):
        assert resolve_subject("en") == "en"

    def test_english_code_geo(self):
        assert resolve_subject("geo") == "geo"

    def test_english_code_lit(self):
        assert resolve_subject("lit") == "lit"

    # --- Russian aliases ---
    def test_russian_profmat(self):
        assert resolve_subject("профмат") == "math"

    def test_russian_matematika_profil(self):
        assert resolve_subject("математика профиль") == "math"

    def test_russian_profil_matematika(self):
        assert resolve_subject("профильная математика") == "math"

    def test_russian_matematika_baza(self):
        assert resolve_subject("математика база") == "mathb"

    def test_russian_matbaza(self):
        assert resolve_subject("матбаза") == "mathb"

    def test_russian_bazovaya_matematika(self):
        assert resolve_subject("базовая математика") == "mathb"

    def test_russian_russkiy(self):
        assert resolve_subject("русский") == "rus"

    def test_russian_russkiy_yazyk(self):
        assert resolve_subject("русский язык") == "rus"

    def test_russian_informatika(self):
        assert resolve_subject("информатика") == "inf"

    def test_russian_fizika(self):
        assert resolve_subject("физика") == "phys"

    def test_russian_khimiya(self):
        assert resolve_subject("химия") == "chem"

    def test_russian_biologiya(self):
        assert resolve_subject("биология") == "bio"

    def test_russian_istoriya(self):
        assert resolve_subject("история") == "hist"

    def test_russian_obshchestvoznanie(self):
        assert resolve_subject("обществознание") == "soc"

    def test_russian_obshchestvo(self):
        assert resolve_subject("общество") == "soc"

    def test_russian_angliiskiy(self):
        assert resolve_subject("английский") == "en"

    def test_russian_angliiskiy_yazyk(self):
        assert resolve_subject("английский язык") == "en"

    def test_russian_geografiya(self):
        assert resolve_subject("география") == "geo"

    def test_russian_literatura(self):
        assert resolve_subject("литература") == "lit"

    # --- Case / whitespace insensitivity ---
    def test_uppercase_ignored(self):
        assert resolve_subject("MATH") == "math"

    def test_mixed_case(self):
        assert resolve_subject("Math") == "math"

    def test_leading_trailing_spaces(self):
        assert resolve_subject("  phys  ") == "phys"

    def test_mixed_case_russian(self):
        assert resolve_subject("Физика") == "phys"

    # --- Unknown subjects raise ValueError ---
    def test_unknown_subject_raises(self):
        with pytest.raises(ValueError, match="Unknown subject"):
            resolve_subject("xyz")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            resolve_subject("")

    def test_partial_name_raises(self):
        with pytest.raises(ValueError):
            resolve_subject("мат")

    def test_error_message_lists_valid_codes(self):
        with pytest.raises(ValueError) as exc_info:
            resolve_subject("bad")
        msg = str(exc_info.value)
        assert "math" in msg
        assert "phys" in msg

    # --- VALID_SUBJECTS completeness ---
    def test_valid_subjects_non_empty(self):
        assert len(VALID_SUBJECTS) > 0

    def test_valid_subjects_contains_expected(self):
        expected = {"math", "mathb", "rus", "inf", "phys", "chem",
                    "bio", "hist", "soc", "en", "geo", "lit"}
        assert expected.issubset(set(VALID_SUBJECTS))


class TestCleanText:
    def test_removes_nbsp(self):
        assert _clean("hello\xa0world") == "hello world"

    def test_removes_zero_width_space(self):
        assert _clean("hello\u200bworld") == "helloworld"

    def test_strips_whitespace(self):
        assert _clean("  hello  ") == "hello"

    def test_none_returns_none(self):
        assert _clean(None) is None

    def test_empty_string(self):
        assert _clean("") == ""

    def test_multiple_nbsp(self):
        assert _clean("a\xa0b\xa0c") == "a b c"

    def test_combined_cleanup(self):
        assert _clean("  a\xa0b\u200bc  ") == "a bc"

    def test_normal_text_unchanged(self):
        assert _clean("Normal text 123") == "Normal text 123"
