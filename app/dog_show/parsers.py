import re
import time

import structlog

from .config import BASE_URL
from .showlink import _fetch_page, _source_url
from .utils import _clean_judge_name

logger = structlog.get_logger(__name__)

def _split_award_name_owner(text):
    """Split a breed honor-roll entry like 'Wazazi Tempting Fate, Om. Kortelainen
    Sanna' into (name, owner). For the breeder award the name is the kennel
    ('Heinäkengän'). Returns ('', '') for blanks and (text, '') when no owner."""
    text = (text or "").strip()
    if not text:
        return "", ""
    parts = re.split(r",\s*Om\.\s*", text, maxsplit=1)
    name = parts[0].strip()
    owner = parts[1].strip() if len(parts) > 1 else ""
    return name, owner

def _parse_show_list(soup):
    """Parse the sidebar show listing table."""
    shows = []
    current_month = ""

    table = soup.find("table", id="Nayttelylista")
    if not table:
        return shows

    for row in table.find_all("tr", class_="nayttely"):
        # Month header row
        header = row.find("td", class_="valiotsikko", colspan="2")
        if header:
            current_month = header.get_text(strip=True)
            continue

        # Show row — two <td> elements with <a> tags
        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        link = cells[0].find("a")
        name_link = cells[1].find("a")
        if not link or not name_link:
            continue

        href = link.get("href", "")
        match = re.search(r"Id=(\d+)", href)
        if not match:
            continue

        show_id = int(match.group(1))
        shows.append({
            "id": show_id,
            "date": link.get_text(strip=True),
            "name": name_link.get_text(strip=True),
            "month": current_month,
            "source_url": _source_url(show_id),
        })

    return shows

def _parse_breeds_from_soup(soup, show_id=None):
    breeds = []
    for row in soup.select("table.rotulistatable tr.rotuluettelo"):
        cells = row.find_all("td")
        if not cells:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        name = link.get_text(strip=True)
        href = link.get("href", "")

        r_match = re.search(r"R=(\d+)", href)
        ro_match = re.search(r"RO=(\d+)", href)
        id_match = re.search(r"Id=(\d+)", href)
        linked_show_id = show_id or (id_match.group(1) if id_match else "")
        group = r_match.group(1) if r_match else ""
        breed_id = ro_match.group(1) if ro_match else ""

        count_cell = row.find("td", class_="right")
        count_text = count_cell.get_text(strip=True) if count_cell else "0"
        try:
            count = int(count_text)
        except ValueError:
            count = 0

        # Check for results icon (fa-check)
        has_results = bool(row.select_one("td.right i.fa-check"))

        breeds.append({
            "name": name,
            "count": count,
            "group": group,
            "breed_id": breed_id,
            "has_results": has_results,
            "source_url": _source_url(linked_show_id, group, breed_id) if linked_show_id and group and breed_id else "",
        })
    return breeds

def _breed_list_targets_from_soup(soup, show_id):
    content = soup.find(id="divContent") or soup.find(id="content") or soup
    aggregate_targets = []
    group_targets = []

    for a in content.find_all("a"):
        href = a.get("href", "")
        r_match = re.search(r"(?:[?&]|&amp;)R=([^&#]+)", href)
        if not r_match:
            continue

        id_match = re.search(r"(?:[?&]|&amp;)Id=(\d+)", href)
        if id_match and str(id_match.group(1)) != str(show_id):
            continue

        group_value = r_match.group(1)
        if group_value.upper() == "R":
            aggregate_targets.append(group_value)
            continue

        if group_value.isdigit() and 1 <= int(group_value) <= 10:
            group_targets.append(group_value)

    # Some specialty shows expose every breed under R=R and keep BIS on the
    # landing page. Prefer the aggregate page to avoid duplicate group fetches.
    selected_targets = aggregate_targets or group_targets
    unique_targets = []
    seen = set()
    for target in selected_targets:
        if target in seen:
            continue
        seen.add(target)
        unique_targets.append(target)
    return unique_targets

def _parse_show_detail(soup, show_id):
    """Parse the show detail page: title and breed list."""
    title_el = soup.select_one("#divOtsikko h1")
    title = title_el.get_text(strip=True) if title_el else ""

    # 1. Parse breeds on the landing page (for specialty shows)
    breeds = _parse_breeds_from_soup(soup, show_id)

    # 2. If no breeds found, look for breed-list links (R=R or FCI groups R=1..10)
    if not breeds:
        breed_list_targets = _breed_list_targets_from_soup(soup, show_id)

        if breed_list_targets:
            logger.info("dog_show_groups_found", show_id=show_id, groups=breed_list_targets)
            for target in breed_list_targets:
                url = f"{BASE_URL}?Id={show_id}&R={target}"
                try:
                    # Sleep 0.5s to be polite during nested crawls
                    time.sleep(0.5)
                    group_soup = _fetch_page(url)
                    group_breeds = _parse_breeds_from_soup(group_soup, show_id)
                    breeds.extend(group_breeds)
                except Exception as e:
                    logger.warning("dog_show_group_fetch_failed", show_id=show_id, group=target, error=str(e))

    return {
        "id": show_id,
        "title": title,
        "breeds": breeds,
        "source_url": _source_url(show_id),
    }

def _parse_breed_results(soup, show_id):
    """Parse individual breed results from a show page."""
    title_el = soup.select_one("#divOtsikko h1")
    title = title_el.get_text(strip=True) if title_el else ""

    # Breed name: extract from the first breed header on the page
    breed = ""
    breed_header = soup.select_one("tr.ropotsikko td span.left, tr.ropotsikko td div.floatleft")
    if breed_header:
        breed = breed_header.get_text(strip=True)

    # Judge
    judge = ""
    judge_el = soup.select_one("tr.ropotsikko div.floatright")
    if judge_el:
        judge = _clean_judge_name(judge_el.get_text(" ", strip=True))

    # Awards (ROP/VSP honor-roll table): breed-level winners with owner/kennel.
    awards = []
    for row in soup.select("table.roptulostaulukko tr.roptulos"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            text = cells[1].get_text(strip=True)
            name, owner = _split_award_name_owner(text)
            awards.append({
                "type": cells[0].get_text(strip=True),
                "text": text,
                "name": name,
                "owner": owner,
            })

    # Individual results
    results = []
    current_gender = ""
    current_class = ""

    results_table = soup.select_one("table.roduntulokset")
    if results_table:
        for row in results_table.find_all("tr"):
            classes = row.get("class", [])

            if "sukupuoli" in classes:
                td = row.find("td")
                if td:
                    current_gender = td.get_text(strip=True)
                continue

            if "luokka" in classes:
                span = row.select_one("td span.left")
                if span:
                    current_class = span.get_text(strip=True)
                continue

            if "tulos" in classes:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue

                # Catalog number
                try:
                    number = int(cells[0].get_text(strip=True))
                except (ValueError, IndexError):
                    number = None

                # Dog name and registry URL
                dog_link = cells[1].find("a")
                dog_name = dog_link.get_text(strip=True) if dog_link else cells[1].get_text(strip=True)
                reg_url = dog_link.get("href", "") if dog_link else ""
                if reg_url and not reg_url.startswith("http"):
                    reg_url = "https://jalostus.kennelliitto.fi" + reg_url

                # Grade
                grade = cells[2].get_text(strip=True)

                # Placement (class placement)
                placement_text = cells[3].get_text(strip=True)
                try:
                    placement = int(placement_text) if placement_text else None
                except ValueError:
                    placement = None

                # Competitive placement (best-of-sex ranking: PU1/PN1/...).
                competitive_placement = cells[4].get_text(strip=True) if len(cells) > 4 else ""

                # Awards (quality + honours string, e.g. "SA, ROP, SERT")
                awards_text = cells[5].get_text(strip=True) if len(cells) > 5 else ""

                # Critique: look for the next sibling tr.arvostelu
                critique = ""
                next_row = row.find_next_sibling("tr")
                if next_row and "arvostelu" in next_row.get("class", []):
                    critique_cells = next_row.find_all("td")
                    if len(critique_cells) >= 2:
                        critique = critique_cells[1].get_text(strip=True)
                    elif critique_cells:
                        critique = critique_cells[0].get_text(strip=True)

                results.append({
                    "number": number,
                    "name": dog_name,
                    "reg_url": reg_url,
                    "grade": grade,
                    "placement": placement,
                    "competitive_placement": competitive_placement,
                    "awards": awards_text,
                    "critique": critique,
                    "gender": current_gender,
                    "class_name": current_class,
                })

    return {
        "show_id": show_id,
        "title": title,
        "breed": breed,
        "judge": judge,
        "awards": awards,
        "results": results,
    }
