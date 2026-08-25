#!/usr/bin/env python3
"""Regenerate the YouTube playlist section in about.html from the live playlist.

No API key needed: YouTube exposes a public Atom feed for any playlist
(https://www.youtube.com/feeds/videos.xml?playlist_id=...), capped at the
15 most recent items. This script fetches it, rebuilds the embed iframe
and the custom video list between the YT-* marker comments in about.html,
and leaves the rest of the file untouched.
"""

import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

PLAYLIST_ID = "PL2bGEo6ngcKGbMRVdwUi5eCLP1Gb5R2tl"
FEED_URL = f"https://www.youtube.com/feeds/videos.xml?playlist_id={PLAYLIST_ID}"
ABOUT_HTML = Path(__file__).resolve().parent.parent / "about.html"

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


def fetch_entries():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes)

    entries = []
    for entry in root.findall("atom:entry", NS):
        video_id = entry.findtext("yt:videoId", namespaces=NS)
        title = entry.findtext("atom:title", namespaces=NS) or ""
        media_group = entry.find("media:group", NS)
        thumb = media_group.find("media:thumbnail", NS) if media_group is not None else None
        thumb_url = thumb.get("url") if thumb is not None else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        if video_id:
            entries.append({"id": video_id, "title": title.strip(), "thumb": thumb_url})
    return entries


def build_embed_block(entries):
    latest = entries[0]["id"]
    return (
        f'        <iframe name="ytplayer" '
        f'src="https://www.youtube.com/embed/{latest}?list={PLAYLIST_ID}" '
        f'title="Hank\'s Open Studio playlist" allowfullscreen></iframe>\n'
    )


def build_title_block(entries):
    count = len(entries)
    return (
        f'      <p class="yt-list-title">open studio work<br>'
        f'<span class="en">Hank\'s Open Studio · {count} videos</span></p>\n'
    )


def build_items_block(entries):
    lines = []
    for e in entries:
        vid = e["id"]
        title = html.escape(e["title"], quote=True)
        lines.append(
            f'      <a class="yt-item" '
            f'href="https://www.youtube.com/embed/{vid}?autoplay=1&list={PLAYLIST_ID}" target="ytplayer">\n'
            f'        <img src="{e["thumb"]}" alt="{title}">\n'
            f'        <span>{title}</span>\n'
            f'      </a>\n'
        )
    return "".join(lines)


def replace_between(content, start_marker, end_marker, inner):
    pattern = re.compile(re.escape(start_marker) + r"\n.*?\n(?=[ \t]*" + re.escape(end_marker) + r")", re.DOTALL)
    if not pattern.search(content):
        raise RuntimeError(f"markers not found: {start_marker} ... {end_marker}")
    return pattern.sub(lambda m: start_marker + "\n" + inner, content, count=1)


def main():
    entries = fetch_entries()
    if not entries:
        print("No playlist entries found; leaving about.html untouched.", file=sys.stderr)
        return 1

    original = ABOUT_HTML.read_text(encoding="utf-8")
    updated = original
    updated = replace_between(updated, "<!-- YT-EMBED:START -->", "<!-- YT-EMBED:END -->", build_embed_block(entries))
    updated = replace_between(updated, "<!-- YT-LIST-TITLE:START -->", "<!-- YT-LIST-TITLE:END -->", build_title_block(entries))
    updated = replace_between(updated, "<!-- YT-LIST-ITEMS:START -->", "<!-- YT-LIST-ITEMS:END -->", build_items_block(entries))

    if updated != original:
        ABOUT_HTML.write_text(updated, encoding="utf-8")
        print(f"about.html updated with {len(entries)} playlist videos.")
    else:
        print("about.html already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
