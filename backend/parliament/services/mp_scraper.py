"""Scraper for MP profiles from parlimen.gov.my and mymp.org.my."""
import logging
import re
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)
PARLIMEN_BASE = "https://www.parlimen.gov.my"
PARLIMEN_LISTING = f"{PARLIMEN_BASE}/ahli-dewan.html?uweb=dr&"

MYMP_BASE = "https://mymp.org.my"
MYMP_SITEMAP = f"{MYMP_BASE}/politicians/sitemap"


def parse_parlimen_listing(html: str) -> list[dict]:
    """Parse the MP listing page HTML and return a list of MP dicts."""
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for li in soup.select("li"):
        link = li.select_one("a[href*='profile-ahli']")
        if not link:
            continue
        name_el = li.select_one(".first-name")
        constituency_el = li.select_one(".constituency")
        party_el = li.select_one(".caucus")
        img_el = li.select_one("img.picture")
        if not name_el or not constituency_el:
            continue
        href = link.get("href", "")
        id_match = re.search(r"id=(\d+)", href)
        profile_id = id_match.group(1) if id_match else ""
        photo_src = img_el.get("src", "") if img_el else ""
        if photo_src and not photo_src.startswith("http"):
            photo_url = f"{PARLIMEN_BASE}{photo_src}"
        else:
            photo_url = photo_src
        results.append({
            "name": name_el.get_text(strip=True),
            "constituency_code": constituency_el.get_text(strip=True),
            "party": party_el.get_text(strip=True) if party_el else "",
            "photo_url": photo_url,
            "parlimen_profile_id": profile_id,
        })
    return results


def fetch_parlimen_listing() -> list[dict]:
    """Fetch the MP listing page from parlimen.gov.my."""
    resp = requests.get(PARLIMEN_LISTING, verify=False, timeout=30)
    resp.raise_for_status()
    return parse_parlimen_listing(resp.text)


def parse_parlimen_profile(html: str) -> dict:
    """Parse an individual MP profile page for contact details."""
    soup = BeautifulSoup(html, "html.parser")
    details = {}
    for row in soup.select("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        label = cells[0].get_text(strip=True)
        value = cells[1].get_text(strip=True)
        if "Telefon" in label and value:
            details["phone"] = value
        elif "Faks" in label and value:
            details["fax"] = value
        elif "Email" in label and value:
            details["email"] = value
        elif "Alamat" in label and value:
            details["service_centre_address"] = value
    fb_match = re.search(
        r"(?:FB\s*:\s*)?(?:https?:)?//(?:www\.)?facebook\.com/[\w.\-/]+", html
    )
    if fb_match:
        fb_url = fb_match.group(0)
        if fb_url.startswith("FB"):
            fb_url = re.sub(r"^FB\s*:\s*", "", fb_url)
        if not fb_url.startswith("http"):
            fb_url = "https:" + fb_url if fb_url.startswith("//") else "https://" + fb_url
        details["facebook_url"] = fb_url
    return details


def fetch_parlimen_profile(profile_id: str) -> dict:
    """Fetch an individual MP profile from parlimen.gov.my."""
    url = f"{PARLIMEN_BASE}/profile-ahli.html?uweb=dr&id={profile_id}"
    resp = requests.get(url, verify=False, timeout=30)
    resp.raise_for_status()
    return parse_parlimen_profile(resp.text)


def parse_mymp_sitemap(html: str) -> dict[str, str]:
    """Parse the mymp.org.my sitemap page and return {name: slug} mapping."""
    soup = BeautifulSoup(html, "html.parser")
    slugs = {}
    for link in soup.select("a[href^='/p/']"):
        href = link.get("href", "")
        slug = href.replace("/p/", "").strip("/")
        name = link.get_text(strip=True).lower()
        if slug and name:
            slugs[name] = slug
    return slugs


def fetch_mymp_sitemap() -> dict[str, str]:
    """Fetch the politician sitemap from mymp.org.my."""
    resp = requests.get(MYMP_SITEMAP, timeout=30)
    resp.raise_for_status()
    return parse_mymp_sitemap(resp.text)
