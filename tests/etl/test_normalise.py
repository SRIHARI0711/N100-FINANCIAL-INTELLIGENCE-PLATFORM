"""Unit tests for year and ticker normalisation functions."""

from src.etl.normaliser import clean_string, normalize_ticker, normalize_year

# ---------------------------------------------------------------------------
# normalize_year() Tests (24 test cases)
# ---------------------------------------------------------------------------


def test_year_mar23():
    """Mar-23 should normalise to 2023-03."""
    assert normalize_year("Mar-23") == "2023-03"


def test_year_mar_space():
    """Mar 23 with space should normalise to 2023-03."""
    assert normalize_year("Mar 23") == "2023-03"


def test_year_march_dash():
    """March-2023 full month with dash should normalise to 2023-03."""
    assert normalize_year("March-2023") == "2023-03"


def test_year_march_space():
    """March 2023 full month with space should normalise to 2023-03."""
    assert normalize_year("March 2023") == "2023-03"


def test_year_string_integer():
    """'2023' string integer should assume March FY close (2023-03)."""
    assert normalize_year("2023") == "2023-03"


def test_year_native_integer():
    """2023 native integer should assume March FY close (2023-03)."""
    assert normalize_year(2023) == "2023-03"


def test_year_native_float():
    """2023.0 float should assume March FY close (2023-03)."""
    assert normalize_year(2023.0) == "2023-03"


def test_year_fy23():
    """FY23 prefix should normalise to 2023-03."""
    assert normalize_year("FY23") == "2023-03"


def test_year_fy24():
    """FY24 prefix should normalise to 2024-03."""
    assert normalize_year("FY24") == "2024-03"


def test_year_fy_space():
    """'FY 2024' with space should normalise to 2024-03."""
    assert normalize_year("FY 2024") == "2024-03"


def test_year_fy_hyphen():
    """'FY-22' with hyphen should normalise to 2022-03."""
    assert normalize_year("FY-22") == "2022-03"


def test_year_dec22():
    """Dec-22 December year-end should normalise to 2022-12."""
    assert normalize_year("Dec-22") == "2022-12"


def test_year_dec_2012():
    """Dec 2012 December year-end should normalise to 2012-12."""
    assert normalize_year("Dec 2012") == "2012-12"


def test_year_december_full():
    """'December 2020' full month should normalise to 2020-12."""
    assert normalize_year("December 2020") == "2020-12"


def test_year_jun23():
    """Jun-23 June year-end should normalise to 2023-06."""
    assert normalize_year("Jun-23") == "2023-06"


def test_year_jun_2014():
    """Jun 2014 June year-end should normalise to 2014-06."""
    assert normalize_year("Jun 2014") == "2014-06"


def test_year_sep_2024():
    """Sep 2024 September year-end should normalise to 2024-09."""
    assert normalize_year("Sep 2024") == "2024-09"


def test_year_september_full():
    """'September 2021' full month should normalise to 2021-09."""
    assert normalize_year("September 2021") == "2021-09"


def test_year_already_normalised():
    """Already normalised '2023-03' should pass through unchanged."""
    assert normalize_year("2023-03") == "2023-03"


def test_year_half_year_notation():
    """Decimal half-year '2024.5' should map to '2024-09'."""
    assert normalize_year("2024.5") == "2024-09"


def test_year_suffix_9m():
    """'Mar 2016 9m' trailing note should be stripped to '2016-03'."""
    assert normalize_year("Mar 2016 9m") == "2016-03"


def test_year_suffix_15():
    """'Mar 2023 15' trailing note should be stripped to '2023-03'."""
    assert normalize_year("Mar 2023 15") == "2023-03"


def test_year_garbage():
    """Unparseable string 'xyz' should return 'PARSE_ERROR'."""
    assert normalize_year("xyz") == "PARSE_ERROR"


def test_year_empty_and_none():
    """None, empty string, and null equivalents should return 'PARSE_ERROR'."""
    assert normalize_year(None) == "PARSE_ERROR"
    assert normalize_year("") == "PARSE_ERROR"
    assert normalize_year("   ") == "PARSE_ERROR"
    assert normalize_year("nan") == "PARSE_ERROR"


def test_year_ttm():
    """TTM (trailing twelve months) is not a calendar year and returns 'PARSE_ERROR'."""
    assert normalize_year("TTM") == "PARSE_ERROR"


# ---------------------------------------------------------------------------
# normalize_ticker() Tests (20 test cases)
# ---------------------------------------------------------------------------


def test_ticker_standard():
    """'TCS' should remain 'TCS'."""
    assert normalize_ticker("TCS") == "TCS"


def test_ticker_strip():
    """'  TCS  ' with leading/trailing spaces should normalise to 'TCS'."""
    assert normalize_ticker("  TCS  ") == "TCS"


def test_ticker_lower():
    """'tcs' lowercase should normalise to 'TCS'."""
    assert normalize_ticker("tcs") == "TCS"


def test_ticker_mixed_case():
    """'HdfcBank' mixed case should normalise to 'HDFCBANK'."""
    assert normalize_ticker("HdfcBank") == "HDFCBANK"


def test_ticker_hyphen_preserved():
    """'BAJAJ-AUTO' hyphen should be preserved."""
    assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"


def test_ticker_hyphen_lower_and_space():
    """'  bajaj-auto  ' should normalise to 'BAJAJ-AUTO'."""
    assert normalize_ticker("  bajaj-auto  ") == "BAJAJ-AUTO"


def test_ticker_ampersand_preserved():
    """'M&M' ampersand should be preserved."""
    assert normalize_ticker("M&M") == "M&M"


def test_ticker_ampersand_with_spaces():
    """'  m&m  ' should normalise to 'M&M'."""
    assert normalize_ticker("  m&m  ") == "M&M"


def test_ticker_with_number():
    """'3MINDIA' alphanumeric ticker should be valid and preserved."""
    assert normalize_ticker("3mIndia") == "3MINDIA"


def test_ticker_tab_and_newline():
    """Embedded tabs and newlines around ticker should be stripped."""
    assert normalize_ticker("\n\tINFY\t\n") == "INFY"


def test_ticker_valid_min_length():
    """Valid 2-character ticker should pass."""
    assert normalize_ticker("RE") == "RE"


def test_ticker_valid_max_length():
    """Valid 12-character ticker should pass."""
    assert normalize_ticker("ABCDEFGHIJKL") == "ABCDEFGHIJKL"


def test_ticker_empty_string():
    """Empty string should return None."""
    assert normalize_ticker("") is None


def test_ticker_none():
    """None should return None."""
    assert normalize_ticker(None) is None


def test_ticker_whitespace_only():
    """Whitespace only should return None."""
    assert normalize_ticker("    ") is None


def test_ticker_too_short():
    """Single character ticker is too short per DQ-08 and returns None."""
    assert normalize_ticker("A") is None


def test_ticker_too_long():
    """Ticker longer than 12 characters is invalid and returns None."""
    assert normalize_ticker("VERYLONGSYMBOLNAME") is None


def test_ticker_invalid_characters():
    """Special characters like '@' or '#' should be rejected."""
    assert normalize_ticker("TCS@BSE") is None
    assert normalize_ticker("RELIANCE#1") is None


def test_ticker_missing_keywords():
    """Keywords 'MISSING', 'NAN', 'NULL' should return None."""
    assert normalize_ticker("MISSING") is None
    assert normalize_ticker("nan") is None
    assert normalize_ticker("NULL") is None


def test_ticker_clean_string():
    """clean_string helper should strip whitespace and collapse newlines."""
    assert (
        clean_string("  Tata   Consultancy \n Services Ltd  ")
        == "Tata Consultancy Services Ltd"
    )
    assert clean_string(None) is None
    assert clean_string("") is None
