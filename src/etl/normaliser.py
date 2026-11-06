"""Data normalisation utilities for financial statements and tickers."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Standard mapping of month names and abbreviations to two-digit month strings
MONTH_MAP = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


def normalize_year(raw_val: Any) -> str:
    """Standardise financial year labels to 'YYYY-MM' format."""
    if raw_val is None:
        return "PARSE_ERROR"

    s = str(raw_val).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return "PARSE_ERROR"

    # Already normalised: YYYY-MM
    if re.match(r"^\d{4}-(0[1-9]|1[0-2])$", s):
        return s

    # Decimal / Half-year notation (e.g. 2024.5 -> 2024-09)
    m_half = re.match(r"^(\d{4})\.5$", s)
    if m_half:
        return f"{m_half.group(1)}-09"

    # Float integer notation e.g. 2023.0 -> '2023'
    m_zero_float = re.match(r"^(\d{4})\.0+$", s)
    if m_zero_float:
        s = m_zero_float.group(1)

    # Strip trailing periods/notes e.g. ' 9m', ' 15', ' 15m'
    s_clean = re.sub(r"\s+(9m|15m|15|18m)$", "", s, flags=re.IGNORECASE).strip()

    # Pure 4-digit year integer: assume March FY close per specification
    if re.match(r"^\d{4}$", s_clean):
        y = int(s_clean)
        if 1990 <= y <= 2050:
            return f"{y:04d}-03"
        return "PARSE_ERROR"

    # FY prefix patterns: 'FY23', 'FY 23', 'FY2023', 'FY-24'
    m_fy = re.match(r"^FY\s*[-_]?\s*(\d{2,4})$", s_clean, re.IGNORECASE)
    if m_fy:
        raw_yr = m_fy.group(1)
        yr = 2000 + int(raw_yr) if len(raw_yr) == 2 else int(raw_yr)
        if 1990 <= yr <= 2050:
            return f"{yr:04d}-03"
        return "PARSE_ERROR"

    # Month + Year patterns: 'Mar-23', 'Mar 23', 'March 2023', 'Dec 2012', 'Jun-23'
    m_my = re.match(r"^([a-zA-Z]+)\s*[-/]?\s*(\d{2,4})$", s_clean)
    if m_my:
        mon_str = m_my.group(1).lower()
        yr_str = m_my.group(2)
        if mon_str in MONTH_MAP:
            mon = MONTH_MAP[mon_str]
            yr = 2000 + int(yr_str) if len(yr_str) == 2 else int(yr_str)
            if 1990 <= yr <= 2050:
                return f"{yr:04d}-{mon}"
        return "PARSE_ERROR"

    # Year + Month pattern: '2023-Mar', '2023/03'
    m_ym = re.match(r"^(\d{2,4})\s*[-/]?\s*([a-zA-Z]+)$", s_clean)
    if m_ym:
        yr_str = m_ym.group(1)
        mon_str = m_ym.group(2).lower()
        if mon_str in MONTH_MAP:
            mon = MONTH_MAP[mon_str]
            yr = 2000 + int(yr_str) if len(yr_str) == 2 else int(yr_str)
            if 1990 <= yr <= 2050:
                return f"{yr:04d}-{mon}"
        return "PARSE_ERROR"

    return "PARSE_ERROR"


def normalize_ticker(raw_val: Any) -> str | None:
    """Normalise NSE ticker symbol: uppercase, strip whitespace, validate length and format."""
    if raw_val is None:
        return None

    ticker = str(raw_val).strip().upper()
    if not ticker or ticker in ("NAN", "NONE", "NULL", "MISSING"):
        return None

    # Length must be 2 to 12 characters per DQ-08 rule
    if len(ticker) < 2 or len(ticker) > 12:
        return None

    # Allowed characters: uppercase letters, numbers, hyphen, and ampersand
    if not re.match(r"^[A-Z0-9\-&]+$", ticker):
        return None

    return ticker


def clean_string(raw_val: Any) -> str | None:
    """Clean string by stripping whitespace and replacing embedded newlines."""
    if raw_val is None:
        return None
    s = str(raw_val).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None
    # Replace line breaks and multiple spaces with a single space
    return re.sub(r"\s+", " ", s).strip()
