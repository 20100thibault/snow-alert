"""
Waste Collection Schedule Scraper

Scrapes Quebec City's Info-Collecte website to get garbage and recycling
collection schedules for a given postal code.
"""

import logging
import re
import time
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Rate limiting
_last_request_time: Optional[float] = None
RATE_LIMIT_SECONDS = 10
CACHE_EXPIRATION_HOURS = 24
INFO_COLLECTE_URL = "https://www.ville.quebec.qc.ca/services/info-collecte/"
REQUEST_TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Mappings for parsing French to English
DAY_MAPPING = {
    'lundi': 'monday',
    'mardi': 'tuesday',
    'mercredi': 'wednesday',
    'jeudi': 'thursday',
    'vendredi': 'friday',
    'samedi': 'saturday',
    'dimanche': 'sunday',
}

WEEK_MAPPING = {
    'impaire': 'odd',
    'impaires': 'odd',
    'paire': 'even',
    'paires': 'even',
}


def _reset_rate_limit() -> None:
    """Reset rate limit state. For testing purposes only."""
    global _last_request_time
    _last_request_time = None


def _set_last_request_time(timestamp: float) -> None:
    """Set last request time. For testing purposes only."""
    global _last_request_time
    _last_request_time = timestamp


def _normalize_postal_code(postal_code: str) -> str:
    """Normalize postal code to format 'X1X 1X1'."""
    code = postal_code.upper().replace(' ', '').strip()
    return f"{code[:3]} {code[3:]}" if len(code) == 6 else code


def _extract_form_fields(html: str) -> Dict[str, str]:
    """
    Extract ASP.NET hidden form fields from HTML.

    Args:
        html: Raw HTML containing the form

    Returns:
        Dict of form field names to values
    """
    fields = {}

    # Extract __VIEWSTATE
    viewstate_match = re.search(
        r'id="__VIEWSTATE"\s+value="([^"]*)"',
        html
    )
    if viewstate_match:
        fields['__VIEWSTATE'] = viewstate_match.group(1)

    # Extract __VIEWSTATEGENERATOR
    generator_match = re.search(
        r'id="__VIEWSTATEGENERATOR"\s+value="([^"]*)"',
        html
    )
    if generator_match:
        fields['__VIEWSTATEGENERATOR'] = generator_match.group(1)

    # Extract __EVENTVALIDATION
    validation_match = re.search(
        r'id="__EVENTVALIDATION"\s+value="([^"]*)"',
        html
    )
    if validation_match:
        fields['__EVENTVALIDATION'] = validation_match.group(1)

    return fields


def _extract_address_dropdown(html: str) -> Optional[str]:
    """
    Extract the first address option from the dropdown if multiple results.

    Args:
        html: HTML response from first POST

    Returns:
        Address value to select, or None if no dropdown found
    """
    # Look for the address dropdown
    dropdown_match = re.search(
        r'<select[^>]*name="ctl00\$ctl00\$contenu\$texte_page\$ucInfoCollecteRechercheAdresse\$RechercheAdresse\$ddChoix"[^>]*>(.*?)</select>',
        html,
        re.DOTALL | re.IGNORECASE
    )

    if not dropdown_match:
        return None

    # Extract first option value (skip empty placeholder if exists)
    options = re.findall(r'<option[^>]*value="([^"]+)"', dropdown_match.group(1))
    for opt in options:
        if opt and opt.strip():
            return opt

    return None


def _make_request(postal_code: str) -> Optional[str]:
    """
    Make HTTP request to Info-Collecte website.
    Handles the two-step process: postal code search -> address selection.

    Args:
        postal_code: Normalized postal code

    Returns:
        HTML response string or None if request failed
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'fr-CA,fr;q=0.9,en;q=0.8',
    })

    try:
        # Step 1: GET the page to retrieve form fields
        logger.debug(f"Fetching Info-Collecte page for postal code: {postal_code}")
        get_response = session.get(INFO_COLLECTE_URL, timeout=REQUEST_TIMEOUT)
        get_response.raise_for_status()

        # Extract hidden form fields
        form_fields = _extract_form_fields(get_response.text)

        if not form_fields.get('__VIEWSTATE'):
            logger.warning("Could not extract __VIEWSTATE from page")
            return None

        # Step 2: POST with postal code
        post_data = {
            **form_fields,
            'ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$txtCodePostal': postal_code,
            'ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$BtnCodePostal': 'Rechercher',
        }

        logger.debug(f"Posting search request for postal code: {postal_code}")
        post_response = session.post(
            INFO_COLLECTE_URL,
            data=post_data,
            timeout=REQUEST_TIMEOUT
        )
        post_response.raise_for_status()

        # Check if we got multiple results (address dropdown)
        address_value = _extract_address_dropdown(post_response.text)

        if address_value:
            # Step 3: Need to select an address and click "Poursuivre" button
            logger.debug(f"Multiple addresses found, selecting first: {address_value}")

            # Extract new form fields from response
            form_fields2 = _extract_form_fields(post_response.text)
            if not form_fields2.get('__VIEWSTATE'):
                logger.warning("Could not extract __VIEWSTATE from address selection page")
                return post_response.text  # Try to parse anyway

            # Submit with selected address and click "Poursuivre" button
            post_data2 = {
                **form_fields2,
                'ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$txtCodePostal': postal_code,
                'ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$ddChoix': address_value,
                'ctl00$ctl00$contenu$texte_page$ucInfoCollecteRechercheAdresse$RechercheAdresse$btnChoix': 'Poursuivre',
            }

            post_response2 = session.post(
                INFO_COLLECTE_URL,
                data=post_data2,
                timeout=REQUEST_TIMEOUT
            )
            post_response2.raise_for_status()
            return post_response2.text

        return post_response.text

    except requests.Timeout:
        logger.error(f"Timeout while fetching schedule for {postal_code}")
        return None
    except requests.ConnectionError:
        logger.error(f"Connection error while fetching schedule for {postal_code}")
        return None
    except requests.HTTPError as e:
        logger.error(f"HTTP error while fetching schedule for {postal_code}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching schedule for {postal_code}: {e}")
        return None


def scrape_schedule(postal_code: str) -> Optional[Dict[str, Any]]:
    """
    Scrape the Info-Collecte website to get collection schedule for a postal code.

    Args:
        postal_code: Canadian postal code (e.g., 'G1R 2K8' or 'G1R2K8')

    Returns:
        Dict with 'garbage_day' and 'recycling_week' keys, or None if failed.
        Example: {'garbage_day': 'monday', 'recycling_week': 'odd'}
    """
    global _last_request_time

    normalized_code = _normalize_postal_code(postal_code)

    # Enforce rate limiting before making request
    _enforce_rate_limit()

    # Make HTTP request
    html = _make_request(normalized_code)

    # Update last request time after making the request
    _last_request_time = time.time()

    if html is None:
        return None

    # Parse the HTML response
    return parse_schedule_html(html)


def _find_garbage_day(text_content: str) -> Optional[str]:
    """Find garbage collection day from text content."""
    # Look for "prochaine collecte" pattern which indicates the next pickup day
    # Pattern: "prochaine collecte : mardi 20 janvier" or similar
    prochaine_match = re.search(
        r'prochaine collecte\s*:\s*(\w+)\s+\d+',
        text_content
    )
    if prochaine_match:
        day_word = prochaine_match.group(1).lower()
        if day_word in DAY_MAPPING:
            return DAY_MAPPING[day_word]

    # Look for "jour de collecte : mardi" pattern
    jour_match = re.search(
        r'jour de collecte\s*:\s*(\w+)',
        text_content
    )
    if jour_match:
        day_word = jour_match.group(1).lower()
        if day_word in DAY_MAPPING:
            return DAY_MAPPING[day_word]

    # Look for patterns like "ordures le lundi" or "lundi ... ordures"
    for french_day, english_day in DAY_MAPPING.items():
        if french_day not in text_content:
            continue

        ordures_pattern = re.search(rf'(?:ordures|déchets)[^.]*{french_day}', text_content)
        day_ordures_pattern = re.search(rf'{french_day}[^.]*(?:ordures|déchets)', text_content)

        if ordures_pattern or day_ordures_pattern:
            return english_day

    # Fallback: look for "(1x/semaine) : mardi" pattern (summer schedule)
    summer_match = re.search(
        r'1x/semaine\)\s*:\s*(\w+)',
        text_content
    )
    if summer_match:
        day_word = summer_match.group(1).lower()
        if day_word in DAY_MAPPING:
            return DAY_MAPPING[day_word]

    return None


def _find_recycling_week(text_content: str) -> Optional[str]:
    """Find recycling week parity from text content."""
    # First check for explicit odd/even
    for french_week, english_week in WEEK_MAPPING.items():
        if french_week in text_content:
            return english_week

    # Check for "chaque 2 semaines" pattern which indicates bi-weekly
    # In this case, we can't determine odd/even, but we know it's bi-weekly
    if 'chaque 2 semaines' in text_content or 'aux 2 semaines' in text_content:
        # Return 'biweekly' as a fallback - the caller can handle this
        return 'biweekly'

    return None


def parse_schedule_html(html: str) -> Optional[Dict[str, Any]]:
    """
    Parse the HTML response from Info-Collecte to extract schedule data.

    Args:
        html: Raw HTML string from Info-Collecte response

    Returns:
        Dict with 'garbage_day' and 'recycling_week' keys, or None if parsing failed.
    """
    try:
        soup = BeautifulSoup(html, 'html.parser')
        text_content = soup.get_text().lower()

        garbage_day = _find_garbage_day(text_content)
        if not garbage_day:
            logger.warning("Could not parse schedule from HTML")
            return None

        return {
            'garbage_day': garbage_day,
            'recycling_week': _find_recycling_week(text_content)
        }

    except Exception as e:
        logger.error(f"Error parsing schedule HTML: {e}")
        return None


def _enforce_rate_limit() -> None:
    """Enforce rate limiting between requests. Blocks if called too soon."""
    global _last_request_time

    if _last_request_time is None:
        return

    elapsed = time.time() - _last_request_time
    if elapsed < RATE_LIMIT_SECONDS:
        wait_time = RATE_LIMIT_SECONDS - elapsed
        logger.debug(f"Rate limiting: waiting {wait_time:.1f} seconds")
        time.sleep(wait_time)


def _is_cache_expired(updated_at: datetime) -> bool:
    """Check if cached data is expired (older than CACHE_EXPIRATION_HOURS)."""
    if updated_at is None:
        return True
    expiration_time = updated_at + timedelta(hours=CACHE_EXPIRATION_HOURS)
    return datetime.utcnow() > expiration_time


def get_cached_schedule(postal_code: str) -> Optional[Dict[str, Any]]:
    """
    Get cached schedule from database if available and not expired.

    Returns:
        Dict with schedule data if cache hit, None if cache miss or expired.
    """
    from app.database import get_waste_zone

    normalized_code = _normalize_postal_code(postal_code).replace(' ', '')
    zone = get_waste_zone(normalized_code)

    if zone is None:
        logger.debug(f"No cached schedule found for {normalized_code}")
        return None

    if _is_cache_expired(zone.get('updated_at')):
        logger.debug(f"Cached schedule for {normalized_code} is expired")
        return None

    logger.debug(f"Using cached schedule for {normalized_code}")
    return {
        'garbage_day': zone['garbage_day'],
        'recycling_week': zone['recycling_week'],
        'zone_id': zone['id']
    }


def get_schedule(postal_code: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    """
    Get collection schedule for a postal code.
    Uses cache if available, otherwise scrapes the website.

    Returns:
        Dict with 'garbage_day', 'recycling_week', and 'zone_id' keys,
        or None if schedule could not be determined.
    """
    from app.database import add_waste_zone

    normalized_code = _normalize_postal_code(postal_code).replace(' ', '')

    # Check cache first (unless force_refresh)
    if not force_refresh:
        cached = get_cached_schedule(postal_code)
        if cached is not None:
            return cached

    # Scrape fresh data
    logger.info(f"Scraping schedule for {normalized_code}")
    schedule = scrape_schedule(postal_code)

    if schedule is None:
        logger.warning(f"Could not scrape schedule for {normalized_code}")
        return None

    # Save to cache (database)
    zone_id = add_waste_zone(
        zone_code=normalized_code,
        garbage_day=schedule['garbage_day'],
        recycling_week=schedule.get('recycling_week', 'unknown')
    )

    return {
        'garbage_day': schedule['garbage_day'],
        'recycling_week': schedule.get('recycling_week'),
        'zone_id': zone_id
    }
