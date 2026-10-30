"""Unit tests for Google country detection and banned country filtering."""
import pytest
from src.geo.google_check import (
    extract_html_lang,
    google_lang_to_cc,
    parse_google_country_from_html,
    check_google_country,
)


def test_extract_html_lang():
    html1 = '<html itemscope="" itemtype="http://schema.org/WebPage" lang="en-IR">'
    assert extract_html_lang(html1) == "en-ir"

    html2 = '<html lang="ru">'
    assert extract_html_lang(html2) == "ru"

    html3 = '<html lang="fa-IR">'
    assert extract_html_lang(html3) == "fa-ir"

    html4 = '<html lang="de">'
    assert extract_html_lang(html4) == "de"


def test_google_lang_to_cc():
    # Explicit Iran / Russia signals
    assert google_lang_to_cc("en-ir") == "IR"
    assert google_lang_to_cc("fa") == "IR"
    assert google_lang_to_cc("fa-ir") == "IR"
    assert google_lang_to_cc("ru") == "RU"
    assert google_lang_to_cc("ru-ru") == "RU"
    assert google_lang_to_cc("en-ru") == "RU"

    # Other global countries
    assert google_lang_to_cc("de") == "DE"
    assert google_lang_to_cc("fr") == "FR"
    assert google_lang_to_cc("nl") == "NL"
    assert google_lang_to_cc("en") == "US"
    assert google_lang_to_cc("en-GB") == "GB"
    assert google_lang_to_cc("pt-BR") == "BR"


def test_parse_google_country_from_html():
    # Primary: lang attribute
    html = '<!doctype html><html lang="en-IR"><head><title>Google</title></head><body></body></html>'
    assert parse_google_country_from_html(html) == "IR"

    # Secondary: gl parameter
    html_gl = '<html><body><input type="hidden" name="gl" value="DE"></body></html>'
    assert parse_google_country_from_html(html_gl) == "DE"

    # Region attribute
    html_region = '<html><body data-country="FR"></body></html>'
    assert parse_google_country_from_html(html_region) == "FR"


def test_check_google_country():
    blocked = ["IR", "RU"]

    cc, is_bad = check_google_country("IR", blocked)
    assert cc == "IR"
    assert is_bad is True

    cc, is_bad = check_google_country("RU", blocked)
    assert cc == "RU"
    assert is_bad is True

    cc, is_bad = check_google_country("DE", blocked)
    assert cc == "DE"
    assert is_bad is False

    cc, is_bad = check_google_country("US", blocked)
    assert cc == "US"
    assert is_bad is False


def test_format_remark_and_flags():
    from src.geo.ip_lookup import cc_to_flag, format_country_with_flag, format_remark

    # Flag conversion
    assert cc_to_flag("DE") == "🇩🇪"
    assert cc_to_flag("NL") == "🇳🇱"
    assert cc_to_flag("US") == "🇺🇸"
    assert cc_to_flag("XX") == ""
    assert cc_to_flag("") == ""

    # Country with flag
    assert format_country_with_flag("DE") == "🇩🇪 DE"
    assert format_country_with_flag("NL") == "🇳🇱 NL"
    assert format_country_with_flag("XX") == "XX"

    # Same country: xBench-0001 | 🇩🇪 DE | Hetzner | 5pts
    remark_same = format_remark(
        prefix="xBench",
        geo_country="DE",
        google_country="DE",
        isp="Hetzner Online GmbH",
        seq_id=1,
        score=5,
    )
    assert remark_same == "xBench-0001 | 🇩🇪 DE | Hetzner Online | 5pts"

    # Different country: xBench-0042 | 🇩🇪 DE (or 🇳🇱 NL) | Hetzner | 3pts
    remark_diff = format_remark(
        prefix="xBench",
        geo_country="DE",
        google_country="NL",
        isp="Hetzner",
        seq_id=42,
        score=3,
    )
    assert remark_diff == "xBench-0042 | 🇩🇪 DE (or 🇳🇱 NL) | Hetzner | 3pts"

    # Default / 0pts / no google country: xBench-0100 | 🇺🇸 US | Datacamp | 0pts
    remark_zero = format_remark(
        prefix="[xBench]",
        geo_country="US",
        google_country="",
        isp="Datacamp Limited",
        seq_id=100,
        score=0,
    )
    assert remark_zero == "xBench-0100 | 🇺🇸 US | Datacamp | 0pts"
