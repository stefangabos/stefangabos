#!/usr/bin/env python3
"""
renders the stats card shown in README.md as two svg files, one for github's light theme and one for the dark theme.

the numbers are read from the published stefangabos.github.io page, which refreshes them every week, so this script
fetches nothing from jsdelivr, npm, packagist, codersrank or gitstar itself. logos come from simple-icons (cc0).

usage: python3 .github/scripts/render_stats.py [path or url of the stefangabos.github.io index.html]
writes images/stats-light.svg, images/stats-dark.svg and updates the alt text of the card in README.md.
"""
import html
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOURCE = sys.argv[1] if len(sys.argv) > 1 else 'https://raw.githubusercontent.com/stefangabos/stefangabos.github.io/main/index.html'

WIDTH = 840
ROW_HEIGHT = 150
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

THEMES = {
    'light': {'text': '#1f2328', 'muted': '#59636e', 'line': '#d1d9e0', 'github': '#1f2328'},
    'dark': {'text': '#f0f6fc', 'muted': '#9198a1', 'line': '#3d444d', 'github': '#f0f6fc'},
}

# metric prefix in the page's data-stat attribute, logo, logo colour, label (with {top} for the codersrank percentage)
USAGE = [
    ('jsdelivr-month', 'jsdelivr', '#e84d3d', 'CDN requests / month'),
    ('npm-year', 'npm', '#cb3837', 'npm downloads / year'),
    ('packagist-total', 'packagist', '#f28d1a', 'Composer installs, all time'),
    ('github-stars', 'github', None, 'GitHub stars'),
]
RANKINGS = [
    ('codersrank-world-rank stefangabos PHP', 'php', '#777bb4', 'Top {top} of PHP developers worldwide', 'codersrank-world-top stefangabos PHP'),
    ('codersrank-world-rank stefangabos JavaScript', 'javascript', '#e5c700', 'Top {top} of JavaScript developers worldwide', 'codersrank-world-top stefangabos JavaScript'),
    ('gitstar-rank', 'github', None, 'GitHub developer by total stars', None),
]


def fetch(location):
    if location.startswith('http'):
        request = urllib.request.Request(location, headers={'User-Agent': 'stefangabos stats card'})
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode('utf-8')
    with open(location, encoding='utf-8') as handle:
        return handle.read()


def stat(page, prefix):
    match = re.search(r'data-stat="' + re.escape(prefix) + r'[^"]*">([^<]*)<', page)
    if not match:
        raise ValueError('no stat starting with "%s" on the page' % prefix)
    return match.group(1).strip()


def icon_path(slug):
    svg = fetch('https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/%s.svg' % slug)
    return re.search(r'<path d="([^"]+)"', svg).group(1)


def cell(x, y, width, number, label, logo, colour, theme):
    center = x + width / 2
    # the php logo is a wide oval inside a square viewbox, so it gets drawn larger to look the same size as the others
    size = 34 if logo == 'php' else 24
    top = y + 28 - (size - 24) / 2
    parts = [
        '<g transform="translate(%.1f %.1f) scale(%.4f)"><path fill="%s" d="%s"/></g>' % (center - size / 2, top, size / 24, colour or theme['github'], PATHS[logo]),
        '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="30" font-weight="700" fill="%s" letter-spacing="-0.5">%s</text>' % (center, y + 94, theme['text'], html.escape(number)),
    ]
    label_markup = html.escape(label[0])
    if label[1]:
        label_markup = html.escape(label[0]).replace('{top}', '<tspan font-weight="600" fill="%s">%s</tspan>' % (theme['text'], html.escape(label[1])))
    parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" font-size="13" fill="%s">%s</text>' % (center, y + 124, theme['muted'], label_markup))
    return '\n  '.join(parts)


def render(page, theme):
    lines = []
    usage_width = WIDTH / len(USAGE)
    for index, (prefix, logo, colour, label) in enumerate(USAGE):
        lines.append(cell(index * usage_width, 0, usage_width, stat(page, prefix), (label, None), logo, colour, theme))
    ranking_width = WIDTH / len(RANKINGS)
    for index, (prefix, logo, colour, label, top_prefix) in enumerate(RANKINGS):
        top = stat(page, top_prefix) if top_prefix else None
        lines.append(cell(index * ranking_width, ROW_HEIGHT, ranking_width, stat(page, prefix), (label, top), logo, colour, theme))
    height = ROW_HEIGHT * 2
    rules = ['<line x1="0" y1="0.5" x2="%d" y2="0.5"/>' % WIDTH, '<line x1="0" y1="%d" x2="%d" y2="%d"/>' % (ROW_HEIGHT, WIDTH, ROW_HEIGHT), '<line x1="0" y1="%.1f" x2="%d" y2="%.1f"/>' % (height - 0.5, WIDTH, height - 0.5)]
    for index in range(1, len(USAGE)):
        rules.append('<line x1="%.1f" y1="16" x2="%.1f" y2="%d"/>' % (index * usage_width, index * usage_width, ROW_HEIGHT - 16))
    for index in range(1, len(RANKINGS)):
        rules.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d"/>' % (index * ranking_width, ROW_HEIGHT + 16, index * ranking_width, height - 16))
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="%s">\n'
            '  <g stroke="%s" stroke-width="1">%s</g>\n  %s\n</svg>\n') % (WIDTH, height, WIDTH, height, html.escape(FONT, quote=True), theme['line'], ''.join(rules), '\n  '.join(lines))


def alt_text(page):
    usage = ', '.join(stat(page, prefix) + ' ' + label for prefix, _, _, label in USAGE)
    rankings = ', '.join(stat(page, prefix) + ' ' + label.replace('{top}', stat(page, top) if top else '') for prefix, _, _, label, top in RANKINGS)
    return usage + '. ' + rankings + '.'


def main():
    page = fetch(SOURCE)
    global PATHS
    PATHS = {slug: icon_path(slug) for slug in {row[1] for row in USAGE + RANKINGS}}
    os.makedirs(os.path.join(ROOT, 'images'), exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(ROOT, 'images', 'stats-%s.svg' % name), 'w', encoding='utf-8') as handle:
            handle.write(render(page, theme))
    readme_path = os.path.join(ROOT, 'README.md')
    with open(readme_path, encoding='utf-8') as handle:
        readme = handle.read()
    updated = re.sub(r'(<img src="images/stats-light\.svg"[^>]*alt=")[^"]*(")', lambda match: match.group(1) + html.escape(alt_text(page), quote=True) + match.group(2), readme)
    if updated != readme:
        with open(readme_path, 'w', encoding='utf-8') as handle:
            handle.write(updated)
    print('rendered images/stats-light.svg and images/stats-dark.svg')
    return 0


PATHS = {}

if __name__ == '__main__':
    sys.exit(main())
