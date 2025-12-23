#!/usr/bin/env python3
"""
Sync publications from OpenAlex into a Jekyll collection.

Rules:
1) ONLY export works where Marc Rußwurm is an author (Marc must be on every paper).
2) Bold-highlight ALL research-group members in the authors list.

Reads members from:     ./_members/*.md
Writes publications to: ./_publications/*.md

Member front matter recommended:
---
name: "Marc Rußwurm"
openalex_author_id: "A1234567890"   # strongly recommended
---

Publication output front matter:
---
title: "Paper title"
authors: "A, B, **Marc Rußwurm**, **Other Member**, D, et al."
date: "2025-03-17"
year: 2025
link: "https://doi.org/..."
venue: "NeurIPS"
order: 1
openalex_work_id: "W123..."
dedupe_key: "doi:https://doi.org/..."
---
"""

from __future__ import annotations

import argparse
import json
import re
import os
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
import yaml

OPENALEX_API = "https://api.openalex.org"


# ----------------------------
# Text / YAML helpers
# ----------------------------

def sanitize_yaml_scalar(s: str) -> str:
    """
    Remove characters that can break YAML parsing in Jekyll (Psych),
    and normalize whitespace.
    """
    s = s or ""

    # Normalize "space-like" chars
    s = s.replace("\u00A0", " ")  # NBSP

    # Replace line/tab whitespace with spaces
    s = re.sub(r"[\r\n\t]+", " ", s)

    # Drop control/format chars (Unicode category starting with 'C')
    # This removes e.g. \u200b (ZWSP), bidi marks, etc.
    s = "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


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


def slugify(s: str, max_len: int = 80) -> str:
    """ASCII-ish slug for filenames."""
    s = sanitize_yaml_scalar(s)
    s = norm_name(s)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return (s[:max_len].strip("-") or "paper")


def read_front_matter(md_path: Path) -> tuple[dict, str]:
    """Parse YAML front matter from a markdown file. Returns (front_matter_dict, body_text)."""
    txt = md_path.read_text(encoding="utf-8-sig")  # strips BOM
    lines = txt.splitlines()
    i = 0

    while i < len(lines) and lines[i].strip() == "":
        i += 1

    if i >= len(lines) or lines[i].strip() != "---":
        return {}, txt

    i += 1
    fm_lines = []
    while i < len(lines) and lines[i].strip() not in ("---", "..."):
        fm_lines.append(lines[i])
        i += 1

    if i >= len(lines):
        return {}, txt

    i += 1  # skip closing delimiter
    fm_raw = "\n".join(fm_lines)
    body = "\n".join(lines[i:]).lstrip("\n")
    fm = yaml.safe_load(fm_raw) or {}
    return fm, body


def write_front_matter_md(out_path: Path, fm: Dict[str, Any], body: str = "") -> None:
    """
    Write a Markdown file with YAML front matter using yaml.safe_dump.
    Values are sanitized before dump to avoid Jekyll YAML parser issues.
    """
    def sanitize_obj(obj: Any) -> Any:
        if isinstance(obj, str):
            return sanitize_yaml_scalar(obj)
        if isinstance(obj, dict):
            return {k: sanitize_obj(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [sanitize_obj(v) for v in obj]
        return obj

    fm = sanitize_obj(fm)

    yaml_txt = yaml.safe_dump(
        fm,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    ).strip()

    out_path.write_text(f"---\n{yaml_txt}\n---\n{body}", encoding="utf-8")


# ----------------------------
# Title casing helpers
# ----------------------------

SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "from", "if", "in", "into", "nor",
    "of", "on", "onto", "or", "over", "per", "the", "to", "up", "via", "vs", "with", "within", "without",
}


def _should_preserve_token_case(s: str) -> bool:
    """Preserve original capitalization for acronyms, camelCase, dotted abbreviations, or digits."""
    if not s:
        return False
    if any(ch.isdigit() for ch in s):
        return True
    if "." in s:  # e.g., U.S., S.V.M.
        return True
    if s.isupper():  # e.g., CNN, NASA
        return True
    # internal caps: e.g., OpenAI, NeRF, eDNA
    if re.search(r"[A-Z].*[A-Z]", s) and not re.fullmatch(r"[A-Z][a-z]+", s):
        return True
    if re.search(r"[a-z][A-Z]", s):
        return True
    return False


def _titlecase_word(word: str, force_cap: bool) -> str:
    if not word:
        return word
    if _should_preserve_token_case(word):
        return word

    lower = word.lower()
    if (not force_cap) and (lower in SMALL_WORDS):
        return lower

    return lower[:1].upper() + lower[1:]


def title_case_paper_title(title: str) -> str:
    """
    Title case for paper titles:
    - Capitalize main words
    - Lowercase small/filler words (of, the, and, ...)
    - Always capitalize first and last word
    - Capitalize after ':' / '—' / '–'
    - Preserve acronyms / mixed case (OpenAI, NeRF, CNN, 3D, U.S., ...)
    """
    title = sanitize_yaml_scalar(title)

    tokens = re.split(r"(\s+)", title)

    def is_word_token(tok: str) -> bool:
        core = re.sub(r"^\W+|\W+$", "", tok)
        return any(ch.isalnum() for ch in core)

    word_positions = [i for i, t in enumerate(tokens) if t and (not t.isspace()) and is_word_token(t)]
    if not word_positions:
        return title

    first_pos = word_positions[0]
    last_pos = word_positions[-1]

    cap_next = True
    out: List[str] = []

    for i, tok in enumerate(tokens):
        if not tok or tok.isspace() or not is_word_token(tok):
            out.append(tok)
            if tok and tok.strip().endswith((":","—","–")):
                cap_next = True
            continue

        m_lead = re.match(r"^\W*", tok)
        m_trail = re.search(r"\W*$", tok)
        lead = m_lead.group(0) if m_lead else ""
        trail = m_trail.group(0) if m_trail else ""
        core = tok[len(lead):len(tok) - len(trail)] if len(tok) >= (len(lead) + len(trail)) else tok

        is_first_or_last = (i == first_pos) or (i == last_pos)
        force_cap_word = cap_next or is_first_or_last

        parts = re.split(r"([-–—/])", core)
        word_part_positions = [j for j, p in enumerate(parts) if p and p not in {"-", "–", "—", "/"}]
        wp_first = word_part_positions[0] if word_part_positions else -1
        wp_last = word_part_positions[-1] if word_part_positions else -1

        new_parts: List[str] = []
        for j, p in enumerate(parts):
            if p in {"-", "–", "—", "/"} or not p:
                new_parts.append(p)
                continue
            force_cap_part = force_cap_word or (j == wp_first) or (j == wp_last)
            new_parts.append(_titlecase_word(p, force_cap=force_cap_part))

        new_core = "".join(new_parts)
        out.append(f"{lead}{new_core}{trail}")

        cap_next = tok.rstrip().endswith((":","—","–"))

    return "".join(out)


def harmonize_publication_titles_in_dir(pubs_dir: Path) -> int:
    """Rewrite existing _publications/*.md so fm['title'] uses title_case_paper_title()."""
    updated = 0
    for p in sorted(pubs_dir.glob("*.md")):
        fm, body = read_front_matter(p)
        if not isinstance(fm, dict) or "title" not in fm or not isinstance(fm["title"], str):
            continue
        old = fm["title"]
        new = title_case_paper_title(old)
        if new != old:
            fm["title"] = new
            write_front_matter_md(p, fm, body=body)
            updated += 1
    return updated


# ----------------------------
# Extra dedupe by lowercase title (works + files)
# ----------------------------

def title_key_lower(s: str) -> str:
    """Case-insensitive title key (sanitize + collapse whitespace + lowercase)."""
    s = sanitize_yaml_scalar(s or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def dedupe_works_by_title_lower(works: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep one work per identical lowercase title; keep best by work_quality_key()."""
    best: Dict[str, Dict[str, Any]] = {}
    for w in works:
        t = title_key_lower(w.get("display_name") or "")
        if not t:
            continue
        prev = best.get(t)
        if prev is None or work_quality_key(w) > work_quality_key(prev):
            best[t] = w
    return list(best.values())


def prune_publications_with_identical_titles(pubs_dir: Path) -> int:
    """
    Delete duplicate publication MD files that have identical lowercase front-matter titles.
    Keep the newest by date, tie-breaker: shorter filename.
    """
    groups: Dict[str, List[Path]] = {}

    for p in pubs_dir.glob("*.md"):
        fm, _body = read_front_matter(p)
        title = fm.get("title") if isinstance(fm, dict) else None
        if not isinstance(title, str) or not title.strip():
            continue
        k = title_key_lower(title)
        groups.setdefault(k, []).append(p)

    deleted = 0
    for _k, files in groups.items():
        if len(files) <= 1:
            continue

        def score(path: Path) -> Tuple[str, int]:
            fm, _ = read_front_matter(path)
            date = str((fm or {}).get("date") or "")
            return (date, -len(path.name))

        keep = max(files, key=score)
        for f in files:
            if f != keep:
                f.unlink()
                deleted += 1

    return deleted


# ----------------------------
# OpenAlex helpers
# ----------------------------

def normalized_doi(work: Dict[str, Any]) -> str:
    """Normalize DOI to lowercase doi.org URL if present."""
    doi = (work.get("doi") or "").strip()
    if not doi:
        return ""
    if doi.startswith("http"):
        return doi.lower()
    return f"https://doi.org/{doi}".lower()


def pick_best_link(work: Dict[str, Any]) -> str:
    """Prefer DOI; else landing page; else OpenAlex work URL."""
    doi = work.get("doi")
    if doi:
        doi = str(doi).strip()
        if doi.startswith("http"):
            return doi
        return f"https://doi.org/{doi}"

    primary = work.get("primary_location") or {}
    url = primary.get("landing_page_url")
    if url:
        return str(url).strip()

    return str(work.get("id") or "").strip()


def pick_venue(work: Dict[str, Any]) -> str:
    """Prefer host_venue.display_name; else primary_location.source.display_name; else Unknown."""
    hv = work.get("host_venue") or {}
    if hv.get("display_name"):
        return str(hv["display_name"]).strip()

    primary = work.get("primary_location") or {}
    src = primary.get("source") or {}
    if src.get("display_name"):
        return str(src["display_name"]).strip()

    return ""


def publication_date_yyyy_mm_dd(work: Dict[str, Any]) -> str:
    """
    OpenAlex often provides publication_date = 'YYYY-MM-DD'.
    If missing, fall back to 'YYYY-01-01' if year known, else '0000-01-01'.
    """
    d = str(work.get("publication_date") or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        return d

    y = str(work.get("publication_year") or "").strip()
    if re.fullmatch(r"\d{4}", y):
        return f"{y}-01-01"

    return ""


def work_has_author(work: Dict[str, Any], author_ids: set[str], author_name_norm: str) -> bool:
    """True if work includes given author by OpenAlex ID or normalized display name."""
    for a in (work.get("authorships") or []):
        author = a.get("author") or {}
        aid = canonical_openalex_id(author.get("id") or "")
        disp = (author.get("display_name") or "").strip()
        if aid and aid in author_ids:
            return True
        if disp and norm_name(disp) == author_name_norm:
            return True
    return False


def format_authors(
    authorships: List[Dict[str, Any]],
    member_name_norms: set[str],
    member_author_ids: set[str],
    max_authors: int = 12,
) -> str:
    """Format authors list; bold group members matched by OpenAlex author id or normalized name."""
    names: List[str] = []
    for a in authorships:
        author = a.get("author") or {}
        aid = canonical_openalex_id(author.get("id") or "")
        disp = (author.get("display_name") or "").strip()
        if not disp:
            continue

        is_member = (aid and aid in member_author_ids) or (norm_name(disp) in member_name_norms)
        names.append(f"**{disp}**" if is_member else disp)

    if len(names) > max_authors:
        names = names[:max_authors] + ["et al."]

    return ", ".join(names)


def work_sort_key(w: Dict[str, Any]) -> Tuple[int, str]:
    """Newest-first sort: (year, publication_date)."""
    year = int(w.get("publication_year") or 0)
    date = str(w.get("publication_date") or "")
    return (year, date)


def work_quality_key(work: Dict[str, Any]) -> tuple:
    """
    Prefer the more “complete/official” record when deduping:
    DOI > venue > date > citations > author count.
    """
    hv = (work.get("host_venue") or {}).get("display_name") or ""
    has_venue = 1 if str(hv).strip() else 0
    has_date = 1 if str(work.get("publication_date") or "").strip() else 0
    has_doi = 1 if normalized_doi(work) else 0
    cited_by = int(work.get("cited_by_count") or 0)
    n_auth = len(work.get("authorships") or [])
    return (has_doi, has_venue, has_date, cited_by, n_auth)


def work_dedupe_key(work: Dict[str, Any]) -> str:
    """
    Key for “same paper” across multiple OpenAlex work IDs.
    1) DOI if available
    2) Else: normalized title + year + first author
    """
    doi = normalized_doi(work)
    if doi:
        return f"doi:{doi}"

    title = sanitize_yaml_scalar(str(work.get("display_name") or "")).strip()
    title_norm = norm_name(title)
    year = str(work.get("publication_year") or "")

    first_author_norm = ""
    auths = work.get("authorships") or []
    if auths:
        a0 = (auths[0].get("author") or {}).get("display_name") or ""
        first_author_norm = norm_name(a0)

    return f"t:{title_norm}|y:{year}|a0:{first_author_norm}"


def dedupe_works(works: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Dedupe near-identical works; keep best by work_quality_key."""
    best: Dict[str, Dict[str, Any]] = {}
    for w in works:
        k = work_dedupe_key(w)
        prev = best.get(k)
        if prev is None or work_quality_key(w) > work_quality_key(prev):
            best[k] = w
    return list(best.values())


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
        params["mailto"] = self.mailto
        url = f"{OPENALEX_API}{path}"
        r = self.sess.get(url, params=params, timeout=self.timeout)
        r.raise_for_status()
        time.sleep(self.sleep_s)
        return r.json()

    def search_author_candidates(self, name: str, per_page: int = 5) -> List[Dict[str, Any]]:
        data = self._get("/authors", {"search": name, "per-page": per_page})
        return data.get("results", []) or []

    def iter_works_by_author(self, author_id: str, per_page: int = 200) -> Iterable[Dict[str, Any]]:
        cursor = "*"
        short_id = canonical_openalex_id(author_id)

        while True:
            data = self._get(
                "/works",
                {"filter": f"authorships.author.id:{short_id}", "per-page": per_page, "cursor": cursor},
            )
            for w in data.get("results", []) or []:
                yield w

            meta = data.get("meta") or {}
            cursor = meta.get("next_cursor")
            if not cursor:
                break


# ----------------------------
# Data model / members
# ----------------------------

@dataclass
class Member:
    name: str
    name_norm: str
    openalex_author_id: Optional[str] = None


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
    for m in resolved:
        nn = m.name_norm
        if "marc" in nn and "russwurm" in nn:
            return m
    raise SystemExit(
        "Could not find Marc Rußwurm in _members. "
        "Ensure a member has name: 'Marc Rußwurm' (or similar)."
    )


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Path to your Jekyll repo root")
    ap.add_argument("--members-dir", default="_members", help="Members collection dir (relative to repo)")
    ap.add_argument("--publications-dir", default="_publications", help="Publications collection dir (relative to repo)")
    ap.add_argument("--mailto", required=True, help="Email for OpenAlex polite pool")
    ap.add_argument("--institution-hint", default="", help="Prefer authors whose institution matches this text")
    ap.add_argument("--max-authors-per-paper", type=int, default=12, help="Max authors to list before adding 'et al.'")
    ap.add_argument("--limit-works-per-member", type=int, default=0, help="0 = no limit; otherwise only newest N works per member (approx)")
    ap.add_argument("--cache-file", default=".openalex_author_cache.json", help="Cache file to store chosen author IDs")
    ap.add_argument("--wipe-publications-dir", action="store_true", help="Delete existing publications before writing new ones")
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

    marc = find_marc(resolved)
    if not marc.openalex_author_id:
        print("[WARN] Marc has no openalex_author_id in _members. Filtering will fall back to name matching.")

    marc_author_ids = {canonical_openalex_id(marc.openalex_author_id)} if marc.openalex_author_id else set()
    marc_name_norm = marc.name_norm

    member_name_norms = {m.name_norm for m in resolved}
    member_author_ids: set[str] = {canonical_openalex_id(m.openalex_author_id) for m in resolved if m.openalex_author_id}

    # Collect works across all members (dedupe by OpenAlex work id initially)
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

    works_all = sorted(list(works_by_id.values()), key=work_sort_key, reverse=True)

    # Keep only works where Marc is an author
    works_kept = [w for w in works_all if work_has_author(w, marc_author_ids, marc_name_norm)]
    num_works_skipped_exist = 0

    # Dedupe “same paper” across different OpenAlex work IDs
    works_kept = dedupe_works(works_kept)

    # EXTRA: Remove near-duplicates that share identical lowercase titles (even if OpenAlex IDs/dedupe_key differ)
    works_kept = dedupe_works_by_title_lower(works_kept)

    # Sort newest-first after all dedupe
    works_kept = sorted(works_kept, key=work_sort_key, reverse=True)

    print(f"[INFO] Works total (all members): {len(works_all)}")
    print(f"[INFO] Works kept (Marc is author): {len(works_kept)}")

    # Write out files with sequential order (1 = most recent)
    for idx, w in enumerate(works_kept, start=1):
        title_raw = sanitize_yaml_scalar((w.get("display_name") or "Untitled").strip()) or "Untitled"
        title = title_case_paper_title(title_raw)

        date_full = publication_date_yyyy_mm_dd(w)
        year = int(date_full[:4]) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_full) else (int(w.get("publication_year") or 0) or 0)

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
        dkey = work_dedupe_key(w)

        # Filename includes full date and title + openalex work id
        fname = f"{date_full}-{slugify(title)}-{wid}.md"
        out_path = pubs_dir / fname

        fm = {
            "title": title,
            "authors": authors,
            "date": date_full,  # YYYY-MM-DD
            "year": year if year else "unknown",
            "link": link,
            "venue": venue,
            "order": idx,
            "openalex_work_id": wid,
            "dedupe_key": dkey,
        }

        if os.path.exists(out_path):
            num_works_skipped_exist += 1
        else:
            write_front_matter_md(out_path, fm, body="")

    # Harmonize titles in existing publication files (from prior runs / manual edits)
    num_titles_fixed = harmonize_publication_titles_in_dir(pubs_dir)
    if num_titles_fixed:
        print(f"[INFO] Harmonized title case in {num_titles_fixed} existing publication files.")

    # Remove duplicate publication files with identical lowercase titles
    deleted = prune_publications_with_identical_titles(pubs_dir)
    if deleted:
        print(f"[INFO] Removed {deleted} duplicate publication files (identical lowercase title).")

    print(
        f"[DONE] Wrote {len(works_kept) - num_works_skipped_exist} "
        f"({num_works_skipped_exist} skipped because existed) publication files to {pubs_dir}"
    )


if __name__ == "__main__":
    main()