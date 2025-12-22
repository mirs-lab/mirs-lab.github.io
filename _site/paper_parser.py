#!/usr/bin/env python3
"""
Sync publications from OpenAlex into a Jekyll collection.

Rules (customized):
1) ONLY export works where Marc Rußwurm is an author (Marc must be on every paper).
2) Bold-highlight ALL research-group members in the authors list.

Reads members from:     ./_members/*.md
Writes publications to: ./_publications/*.md

Recommended member front matter:
---
name: "Marc Rußwurm"
openalex_author_id: "A1234567890"   # strongly recommended (avoids ambiguous name search)
---

Publication front matter output:
---
name: "Paper title"
authors: "A, B, **Marc Rußwurm**, **Other Member**, D, et al."
year: "2025"
link: "https://doi.org/..."
venue: "NeurIPS"
order: "1"
---
"""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import yaml


OPENALEX_API = "https://api.openalex.org"


# ----------------------------
# Helpers
# ----------------------------

def norm_name(s: str) -> str:
    """Normalize names for matching (lowercase, strip accents, ß->ss, collapse whitespace)."""
    s = (s or "").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canonical_openalex_id(aid: str) -> str:
    """Return short OpenAlex ID like A123... or W123... from full URL or already-short input."""
    aid = (aid or "").strip()
    if aid.startswith("https://openalex.org/"):
        return aid.split("/")[-1]
    return aid


def yaml_dquote(s: str) -> str:
    """Return a safe ASCII double-quoted YAML string."""
    s = (s or "").replace("\\", "\\\\").replace('"', '\\"')
    s = s.replace("\n", " ").strip()
    return f'"{s}"'


def slugify(s: str, max_len: int = 80) -> str:
    s = norm_name(s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:max_len].strip("-") or "paper"


def read_front_matter(md_path: Path) -> tuple[dict, str]:
    # utf-8-sig strips BOM if present
    txt = md_path.read_text(encoding="utf-8-sig")

    lines = txt.splitlines()
    i = 0

    # allow leading blank lines
    while i < len(lines) and lines[i].strip() == "":
        i += 1

    if i >= len(lines) or lines[i].strip() != "---":
        return {}, txt

    i += 1  # skip opening ---

    fm_lines = []
    while i < len(lines) and lines[i].strip() not in ("---", "..."):
        fm_lines.append(lines[i])
        i += 1

    if i >= len(lines):
        # never found closing --- / ...
        return {}, txt

    i += 1  # skip closing delimiter
    fm_raw = "\n".join(fm_lines)
    body = "\n".join(lines[i:]).lstrip("\n")

    fm = yaml.safe_load(fm_raw) or {}
    return fm, body

def write_publication_md(
    out_path: Path,
    name: str,
    authors: str,
    year: str,
    link: str,
    venue: str,
    order: int,
) -> None:
    fm_lines = [
        "---",
        f"name: {yaml_dquote(name)}",
        f"authors: {yaml_dquote(authors)}",
        f"year: {yaml_dquote(year)}",
        f"link: {yaml_dquote(link)}",
        f"venue: {yaml_dquote(venue)}",
        f"order: {yaml_dquote(str(order))}",
        "---",
        "",
    ]
    out_path.write_text("\n".join(fm_lines), encoding="utf-8")


def pick_best_link(work: Dict[str, Any]) -> str:
    # Prefer DOI if available
    doi = work.get("doi")
    if doi:
        return doi if doi.startswith("http") else f"https://doi.org/{doi}"

    # Otherwise use primary landing page URL
    primary = work.get("primary_location") or {}
    url = primary.get("landing_page_url")
    if url:
        return url

    # Fallback to OpenAlex work URL
    wid = work.get("id") or ""
    return wid


def pick_venue(work: Dict[str, Any]) -> str:
    # Often best: host_venue.display_name (journal/conference)
    hv = work.get("host_venue") or {}
    if hv.get("display_name"):
        return hv["display_name"]

    # Sometimes nested under primary_location.source.display_name
    primary = work.get("primary_location") or {}
    src = primary.get("source") or {}
    if src.get("display_name"):
        return src["display_name"]

    return "Unknown venue"


def format_authors(
    authorships: List[Dict[str, Any]],
    member_name_norms: Dict[str, str],
    member_author_ids: set[str],
    max_authors: int = 12,
) -> str:
    names: List[str] = []
    for a in authorships:
        author = a.get("author") or {}
        aid = canonical_openalex_id(author.get("id") or "")
        disp = (author.get("display_name") or "").strip()
        if not disp:
            continue

        is_member = False
        if aid and aid in member_author_ids:
            is_member = True
        else:
            if norm_name(disp) in member_name_norms:
                is_member = True

        names.append(f"**{disp}**" if is_member else disp)

    if len(names) > max_authors:
        names = names[:max_authors] + ["et al."]

    return ", ".join(names)


def work_has_author(work: Dict[str, Any], author_ids: set[str], author_name_norm: str) -> bool:
    """True if work includes given author by OpenAlex ID or by normalized name."""
    for a in (work.get("authorships") or []):
        author = a.get("author") or {}
        aid = canonical_openalex_id(author.get("id") or "")
        disp = (author.get("display_name") or "").strip()
        if aid and aid in author_ids:
            return True
        if disp and norm_name(disp) == author_name_norm:
            return True
    return False


# ----------------------------
# OpenAlex client
# ----------------------------

class OpenAlexClient:
    def __init__(self, mailto: str, sleep_s: float = 0.12, timeout: float = 30.0):
        self.mailto = mailto
        self.sleep_s = sleep_s
        self.timeout = timeout
        self.sess = requests.Session()

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params)
        params["mailto"] = self.mailto  # polite pool
        url = f"{OPENALEX_API}{path}"
        r = self.sess.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        time.sleep(self.sleep_s)
        return r.json()

    def search_author_candidates(self, name: str, per_page: int = 5) -> List[Dict[str, Any]]:
        data = self._get("/authors", {"search": name, "per-page": per_page})
        return data.get("results", [])

    def iter_works_by_author(self, author_id: str, per_page: int = 200) -> Iterable[Dict[str, Any]]:
        # Cursor paging
        cursor = "*"
        short_id = canonical_openalex_id(author_id)

        while True:
            data = self._get(
                "/works",
                {
                    "filter": f"authorships.author.id:{short_id}",
                    "per-page": per_page,
                    "cursor": cursor,
                },
            )
            for w in data.get("results", []) or []:
                yield w

            meta = data.get("meta") or {}
            cursor = meta.get("next_cursor")
            if not cursor:
                break


# ----------------------------
# Data model
# ----------------------------

@dataclass
class Member:
    name: str
    name_norm: str
    openalex_author_id: Optional[str] = None


# ----------------------------
# Main logic
# ----------------------------

def load_members(members_dir: Path) -> List[Member]:
    members: List[Member] = []
    for p in sorted(members_dir.glob("*.md")):
        fm, _body = read_front_matter(p)
        name = (fm.get("name") or "").strip()
        if not name:
            continue
        openalex_id = fm.get("openalex_author_id")
        members.append(Member(name=name, name_norm=norm_name(name), openalex_author_id=openalex_id))
    return members


def choose_author_id(
    client: OpenAlexClient,
    member: Member,
    institution_hint: Optional[str],
    cache: Dict[str, Any],
) -> Optional[str]:
    k = member.name_norm
    if k in cache:
        return cache[k].get("openalex_author_id")

    cands = client.search_author_candidates(member.name, per_page=5)
    if not cands:
        cache[k] = {"openalex_author_id": None, "note": "no candidates"}
        return None

    def score(c: Dict[str, Any]) -> Tuple[int, int]:
        inst = ((c.get("last_known_institution") or {}).get("display_name") or "")
        inst_hit = 1 if institution_hint and institution_hint.lower() in inst.lower() else 0
        works_count = int(c.get("works_count") or 0)
        return (inst_hit, works_count)

    best = max(cands, key=score)
    best_id = best.get("id")
    cache[k] = {
        "openalex_author_id": best_id,
        "picked_display_name": best.get("display_name"),
        "picked_institution": ((best.get("last_known_institution") or {}).get("display_name")),
        "picked_works_count": best.get("works_count"),
    }
    return best_id


def find_marc(resolved: List[Member]) -> Member:
    # Match "Marc" + ("Rußwurm" or "Russwurm") robustly
    for m in resolved:
        nn = m.name_norm
        if "marc" in nn and "russwurm" in nn:
            return m
    raise SystemExit(
        "Could not find Marc Rußwurm in _members. "
        "Ensure a member has name: 'Marc Rußwurm' (or similar)."
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Path to your Jekyll repo root")
    ap.add_argument("--members-dir", default="_members", help="Members collection dir (relative to repo)")
    ap.add_argument("--publications-dir", default="_publications", help="Publications collection dir (relative to repo)")
    ap.add_argument("--mailto", required=True, help="Email for OpenAlex polite pool")
    ap.add_argument("--institution-hint", default="", help="Prefer authors whose institution matches this text (e.g., 'University of Bonn')")
    ap.add_argument("--max-authors-per-paper", type=int, default=12, help="Max authors to list before adding 'et al.'")
    ap.add_argument("--limit-works-per-member", type=int, default=0, help="0 = no limit; otherwise only newest N works per member (approx)")
    ap.add_argument("--cache-file", default=".openalex_author_cache.json", help="Cache file to store chosen author IDs")
    ap.add_argument("--wipe-publications-dir", action="store_true", help="Delete existing generated publications before writing new ones")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    members_dir = repo / args.members_dir
    pubs_dir = repo / args.publications_dir
    pubs_dir.mkdir(parents=True, exist_ok=True)

    if args.wipe_publications_dir:
        for f in pubs_dir.glob("*.md"):
            f.unlink()

    cache_path = repo / args.cache_file
    cache: Dict[str, Any] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    members = load_members(members_dir)
    if not members:
        raise SystemExit(f"No members found in {members_dir}")

    client = OpenAlexClient(mailto=args.mailto)

    # Resolve OpenAlex author IDs
    resolved: List[Member] = []
    for m in members:
        if m.openalex_author_id:
            resolved.append(Member(m.name, m.name_norm, canonical_openalex_id(m.openalex_author_id)))
            continue

        aid = choose_author_id(client, m, args.institution_hint or None, cache)
        resolved.append(Member(m.name, m.name_norm, canonical_openalex_id(aid) if aid else None))

    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    # Identify Marc (required author on all exported works)
    marc = find_marc(resolved)
    if not marc.openalex_author_id:
        print("[WARN] Marc has no openalex_author_id in _members. Filtering will fall back to name matching.")
    marc_author_ids = {canonical_openalex_id(marc.openalex_author_id)} if marc.openalex_author_id else set()
    marc_name_norm = marc.name_norm

    # For bolding: map normalized names and author IDs for ALL members
    member_name_norms = {m.name_norm: m.name for m in resolved}
    member_author_ids: set[str] = set()
    for m in resolved:
        if m.openalex_author_id:
            member_author_ids.add(canonical_openalex_id(m.openalex_author_id))

    # Collect works across all members (dedupe by OpenAlex work id)
    works_by_id: Dict[str, Dict[str, Any]] = {}

    for m in resolved:
        if not m.openalex_author_id:
            print(f"[WARN] No OpenAlex author ID for member: {m.name} (add openalex_author_id to fix)")
            continue

        print(f"[INFO] Fetching works for {m.name} ({m.openalex_author_id})")
        count = 0
        for w in client.iter_works_by_author(m.openalex_author_id, per_page=200):
            wid = canonical_openalex_id(w.get("id") or "")
            if not wid:
                continue
            works_by_id[wid] = w
            count += 1
            if args.limit_works_per_member and count >= args.limit_works_per_member:
                break

    # Sort works newest-first
    def work_sort_key(w: Dict[str, Any]) -> Tuple[int, str]:
        year = int(w.get("publication_year") or 0)
        date = w.get("publication_date") or ""
        return (year, date)

    works_sorted_all = sorted(works_by_id.values(), key=work_sort_key, reverse=True)

    # Keep only papers where Marc is an author
    works_sorted = [
        w for w in works_sorted_all
        if work_has_author(w, marc_author_ids, marc_name_norm)
    ]

    print(f"[INFO] Works total (all members): {len(works_sorted_all)}")
    print(f"[INFO] Works kept (Marc is author): {len(works_sorted)}")

    # Write out files with sequential order (1 = most recent)
    for idx, w in enumerate(works_sorted, start=1):
        title = (w.get("display_name") or "Untitled").strip()
        year = str(w.get("publication_year") or "").strip() or "unknown"
        link = pick_best_link(w)
        venue = pick_venue(w)

        authorships = w.get("authorships") or []
        authors = format_authors(
            authorships=authorships,
            member_name_norms=member_name_norms,
            member_author_ids=member_author_ids,
            max_authors=args.max_authors_per_paper,
        )

        wid = canonical_openalex_id(w.get("id") or "")
        fname = f"{year}-{slugify(title)}-{wid}.md" if year != "unknown" else f"{slugify(title)}-{wid}.md"
        out_path = pubs_dir / fname

        write_publication_md(
            out_path=out_path,
            name=title,
            authors=authors,
            year=year,
            link=link,
            venue=venue,
            order=idx,
        )

    print(f"[DONE] Wrote {len(works_sorted)} publication files to {pubs_dir}")


if __name__ == "__main__":
    main()