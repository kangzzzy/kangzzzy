"""Aggregate all languages in the authenticated owner's repositories via gh."""
import json
import os
from collections import Counter
from html import escape
from pathlib import Path
import subprocess


def api(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode:
        # Do not write private repository paths or API responses into public logs.
        raise RuntimeError("GitHub API request failed; check token access and rate limits.")
    return json.loads(result.stdout)


def collect(owner):
    if api("user")["login"].casefold() != owner.casefold():
        raise RuntimeError("Stats token must belong to the profile owner.")
    totals = Counter()
    page = 1
    while True:
        repos = api(f"user/repos?affiliation=owner&visibility=all&per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo["owner"]["login"].casefold() == owner.casefold():
                totals.update(api(f"repos/{repo['full_name']}/languages"))
        page += 1
    return totals


def render(totals):
    languages = sorted(((name, size) for name, size in totals.items() if size > 0),
                       key=lambda item: (-item[1], item[0]))
    total = sum(size for _, size in languages)
    height = 102 + max(1, len(languages)) * 34
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="{height}" viewBox="0 0 640 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Repository languages</title>',
        '<desc id="desc">All detected languages across owned public and private repositories, including forks, by code bytes.</desc>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#253342}.muted{fill:#667580}.track{fill:#eaf0ed}.bg{fill:#fff;stroke:#dce5df}@media(prefers-color-scheme:dark){text{fill:#e6edf3}.muted{fill:#9ba9b4}.track{fill:#26352f}.bg{fill:#0d1117;stroke:#30363d}}</style>',
        f'<rect class="bg" x="0.5" y="0.5" width="639" height="{height-1}" rx="12"/>',
        '<text x="24" y="34" font-size="18" font-weight="600">Repository languages</text>',
        '<text class="muted" x="24" y="57" font-size="12">Public + private · code bytes · all detected languages</text>',
    ]
    for index, (name, size) in enumerate(languages):
        y = 90 + index * 34
        percent = size / total * 100
        label = f"{percent:.1f}%" if percent >= 0.1 else "&lt;0.1%"
        parts.extend([
            f'<text x="24" y="{y}" font-size="13">{escape(name)}</text>',
            f'<rect class="track" x="252" y="{y-10}" width="282" height="8" rx="4"/>',
            f'<rect x="252" y="{y-10}" width="{max(1, 282*size/total):.2f}" height="8" rx="4" fill="#24856e"/>',
            f'<text class="muted" x="610" y="{y}" text-anchor="end" font-size="12">{label}</text>',
        ])
    if not languages:
        parts.append('<text class="muted" x="24" y="90" font-size="13">No languages detected.</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    owner = os.environ.get("PROFILE_OWNER", "kangzzzy")
    output = Path(__file__).resolve().parents[1] / "assets" / "languages.svg"
    svg = render(collect(owner))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(svg, encoding="utf-8")
    print("Updated aggregate language card.")
