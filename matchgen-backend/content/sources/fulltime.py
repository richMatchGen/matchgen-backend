"""
FA Fulltime HTML parser with header-aware, resilient parsing.
Handles various table formats and normalizes times to UTC.
"""
import re
import requests
from bs4 import BeautifulSoup
from dateutil import parser, tz
from hashlib import sha1
import logging

logger = logging.getLogger(__name__)

LOCAL_TZ = tz.gettz("Europe/London")

def fetch_via_proxy(proxy_base: str, target_url: str, timeout=10) -> str:
    """Fetch HTML content via Cloudflare Worker proxy with caching."""
    try:
        r = requests.get(
            proxy_base, 
            params={"url": target_url}, 
            timeout=timeout,
            headers={"User-Agent": "MatchGenBot/1.0 (support@matchgen.app)"}
        )
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.error(f"Proxy fetch failed: {str(e)}")
        raise

def clean_space(s: str) -> str:
    """Clean and normalize whitespace in text."""
    return re.sub(r"\s+", " ", (s or "").strip())

def find_fixtures_table(soup: BeautifulSoup):
    """Find the fixtures table by looking for date/time headers."""
    for t in soup.find_all("table"):
        heads = " ".join(th.get_text(" ", strip=True).lower() for th in t.find_all("th"))
        if "date" in heads and "time" in heads and any(k in heads for k in ["home", "away", "opponent"]):
            return t
    return None

def make_fixture_key(kickoff_utc_iso: str, home: str, away: str, competition: str) -> str:
    """Create a stable fixture key for upsert operations."""
    base = f"{kickoff_utc_iso}|{home}|{away}|{competition}"
    return sha1(base.encode("utf-8")).hexdigest()[:16]

def parse_fixtures_html(html: str, club_display_name: str, default_competition: str = ""):
    """
    Parse fixtures from FA Fulltime HTML with resilient header detection.
    
    Args:
        html: Raw HTML content from FA Fulltime page
        club_display_name: Exact team name as shown on the page
        default_competition: Default competition name if not found in table
        
    Returns:
        List of fixture dictionaries with normalized data
    """
    soup = BeautifulSoup(html, "html.parser")
    table = find_fixtures_table(soup)
    fixtures = []
    
    if not table:
        logger.warning("No fixtures table found with date/time headers")
        return fixtures

    # Map columns by header name
    headers = [clean_space(th.get_text()) for th in table.find_all("th")]
    idx = {h.lower(): i for i, h in enumerate(headers)}
    
    # Helper to get column by fuzzy match
    def col(*aliases):
        for a in aliases:
            for k, i in idx.items():
                if a in k:
                    return i
        return None

    c_date = col("date")
    c_time = col("time")
    c_home = col("home team", "home")
    c_away = col("away team", "away", "opponent")
    c_venue = col("venue", "ground")
    c_comp = col("competition")
    c_round = col("round")

    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
            
        try:
            # Extract data from columns
            date_s = clean_space(tds[c_date].get_text()) if c_date is not None else ""
            time_s = clean_space(tds[c_time].get_text()) if c_time is not None else "15:00"
            home = clean_space(tds[c_home].get_text()) if c_home is not None else ""
            away = clean_space(tds[c_away].get_text()) if c_away is not None else ""
            venue = clean_space(tds[c_venue].get_text()) if c_venue is not None else ""
            competition = clean_space(tds[c_comp].get_text()) if c_comp is not None else default_competition
            round_name = clean_space(tds[c_round].get_text()) if c_round is not None else ""

            # Skip empty rows
            if not date_s or not home or not away:
                continue

            # Parse datetime (local) → UTC
            try:
                dt_local = parser.parse(f"{date_s} {time_s}", dayfirst=True).replace(tzinfo=LOCAL_TZ)
                dt_utc = dt_local.astimezone(tz.UTC)
                kickoff_utc_iso = dt_utc.isoformat()
            except Exception as e:
                logger.warning(f"Failed to parse date/time: {date_s} {time_s} - {str(e)}")
                continue

            # Determine perspective fields (H/A from club perspective)
            club_lower = club_display_name.lower()
            if home.lower() == club_lower:
                home_away = "H"
                opponent = away
            elif away.lower() == club_lower:
                home_away = "A"
                opponent = home
            else:
                # Fallback: infer by contains
                if club_lower in home.lower():
                    home_away = "H"
                    opponent = away
                elif club_lower in away.lower():
                    home_away = "A"
                    opponent = home
                else:
                    home_away = ""
                    opponent = home if home else away

            fixture = {
                "kickoff_utc": kickoff_utc_iso,
                "kickoff_local_tz": "Europe/London",
                "home_team": home,
                "away_team": away,
                "home_away": home_away,
                "opponent_name": opponent,
                "venue": venue,
                "competition": competition,
                "round_name": round_name,
                "status": "SCHEDULED",
                "fixture_key": make_fixture_key(kickoff_utc_iso, home, away, competition),
                "raw": {
                    "date": date_s,
                    "time": time_s,
                }
            }
            
            fixtures.append(fixture)
            
        except Exception as e:
            # Only log parsing errors at warning level, not debug
            continue
    return fixtures
