import copy
import csv
import json
import re
from html import escape


def loadData():
    segments = {}
    segments["site_title"] = loadHTML("./data/site_title.html")
    segments["title"] = loadHTML("./data/title.html")
    segments["description"] = loadHTML("./data/description.html")
    segments["short_description"] = loadHTML("./data/short_description.html")
    segments["_news"] = loadHTML("./data/news.html")
    segments["_experience"] = loadHTML("./data/experience.html")
    segments["_contact"] = loadHTML("./data/contact.html")

    segments["pubs"] = loadJson("./data/pubs.json")
    segments["person"] = loadCSV("./data/person.csv")
    segments["conference"] = loadCSV("./data/conference.csv")

    segments["_template"] = loadHTML("./data/template/template.html")
    segments["_pubs_template"] = loadHTML("./data/template/pubs_template.html")
    segments["_single_pub_template"] = loadHTML("./data/template/single_pub_template.html")
    return segments


def loadCSV(filename):
    with open(filename, encoding="utf-8") as f:
        csv_reader = csv.reader(f)

        # Get all model ids from the csv file
        values = {}
        index = 0
        for line in csv_reader:
            if index == 0:
                index += 1
                continue
            values[line[0].strip()] = line[2].strip()

        return values


def loadJson(filename):
    with open(filename, encoding="utf-8") as f:
        return json.load(f)


def loadHTML(filename):
    with open(filename, encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip("\n") for line in lines]


def generateHTML(template, segments, out=True, output_filename=""):
    new_html = []

    for line in template:
        if line.strip(" ")[:8] == "[!!TODO]":
            segment_name = line.strip(" ").strip("\n").split(" ")[1]
            if segment_name in segments:
                new_html += segments[segment_name]
        else:
            new_html.append(line.strip("\n"))
    if out:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(new_html))
    else:
        return new_html


def preparePage(segments, page_name):
    segments["body_open"] = [f'<body id="top" class="page-{page_name}">']
    segments["body_1"] = []
    segments["body_2"] = []


NEWS_ITEM_PATTERN = re.compile(r"^\s*<li>(.*?)</li>\s*$")
NEWS_DATE_PATTERN = re.compile(r"^\[(\d{4})\.(\d{2})\]\s*(.*)$")
PRO_BONO_PATTERN = re.compile(
    r'^<b><span[^>]*>PRO BONO:</span></b>\s*',
    re.IGNORECASE,
)
MONTH_LABELS = {
    "01": "Jan",
    "02": "Feb",
    "03": "Mar",
    "04": "Apr",
    "05": "May",
    "06": "Jun",
    "07": "Jul",
    "08": "Aug",
    "09": "Sep",
    "10": "Oct",
    "11": "Nov",
    "12": "Dec",
}


def parseNewsItems(news):
    community = []
    dated = []
    passthrough = []

    for line in news:
        item_match = NEWS_ITEM_PATTERN.match(line.strip())
        if not item_match:
            if line.strip():
                passthrough.append(line)
            continue

        content = item_match.group(1).strip()
        date_match = NEWS_DATE_PATTERN.match(content)
        if date_match:
            year, month, body = date_match.groups()
            dated.append((year, month, body))
        else:
            community.append(PRO_BONO_PATTERN.sub("", content, count=1))

    return community, dated, passthrough


def renderNewsItem(year, month, body, include_year=True):
    month_label = MONTH_LABELS.get(month, month)
    if include_year:
        year_markup = f'<span class="news-year-inline">{year}</span>'
    else:
        year_markup = f'<span class="sr-only"> {year}</span>'

    return [
        '    <li class="news-item">',
        f'      <time class="news-date" datetime="{year}-{month}">',
        f'        <span class="news-month">{month_label}</span>{year_markup}',
        "      </time>",
        f'      <div class="news-copy">{body}</div>',
        "    </li>",
    ]


def renderCommunityNote(content):
    return [
        '<aside class="community-note">',
        '  <div class="community-note__meta"><span></span>Community</div>',
        f'  <div class="community-note__copy">{content}</div>',
        "</aside>",
    ]


def parseNews(news, short=True, limit=5):
    community, dated, passthrough = parseNewsItems(news)
    lines = [
        '<section class="news-block" aria-labelledby="news-title">',
        '  <header class="section-heading news-heading">',
        '    <span class="section-index" aria-hidden="true">Updates /</span>',
        '    <h2 id="news-title">News</h2>',
        "  </header>",
    ]

    for content in community:
        lines += renderCommunityNote(content)

    if short:
        lines += ['  <ol class="news-list news-list--preview">']
        for year, month, body in dated[:limit]:
            lines += renderNewsItem(year, month, body, include_year=True)
        lines += ["  </ol>"]
    else:
        lines += ['  <div class="news-archive">']
        grouped = {}
        for year, month, body in dated:
            grouped.setdefault(year, []).append((month, body))

        for year, entries in grouped.items():
            lines += [
                f'    <section class="news-year" aria-labelledby="news-year-{year}">',
                f'      <h3 class="news-year-title" id="news-year-{year}">{year}</h3>',
                '      <ol class="news-list">',
            ]
            for month, body in entries:
                lines += renderNewsItem(year, month, body, include_year=False)
            lines += ["      </ol>", "    </section>"]
        lines += ["  </div>"]

    lines += passthrough
    if short:
        lines += [
            '  <a class="text-link news-more" href="news.html">'
            'All news <span aria-hidden="true">↗</span></a>'
        ]
    lines += ["</section>"]
    return lines

def parsePubs(segments):
    all_pubs = []
    for pub in segments["pubs"]:
        info = {}
        publication_name = escape(pub["name"])
        image_path = escape(pub["image"], quote=True)
        info["image"] = [
            f'<img src="{image_path}" alt="{publication_name} project preview" '
            'class="publication-image" width="600" height="360" loading="lazy" decoding="async" />'
        ]

        content = [f'<h3 class="publication-title">{publication_name}</h3>']

        authors = []
        for author in pub["authors"]:
            author_name = escape(author)
            author_website = segments["person"][author]
            if author_website == "ME":
                authors.append(f"<strong>{author_name}</strong>")
            elif author_website == "":
                authors.append(author_name)
            else:
                author_url = escape(author_website, quote=True)
                authors.append(
                    f'<a href="{author_url}" target="_blank" rel="noopener noreferrer">{author_name}</a>'
                )
        content.append(f'<p class="publication-authors">{", ".join(authors)}</p>')

        conference_name = escape(pub["conference"])
        conference_url = escape(segments["conference"][pub["conference"]], quote=True)
        content.append('<div class="publication-meta">')
        content.append(
            f'<a class="publication-venue" href="{conference_url}" target="_blank" '
            f'rel="noopener noreferrer">{conference_name}</a>'
        )
        if pub["special"] == "oral":
            content.append('<span class="publication-highlight">Oral Presentation</span>')
        elif pub["special"] == "spotlight":
            content.append('<span class="publication-highlight">Spotlight</span>')
        content.append("</div>")

        publication_links = []
        for label, field in (("Paper", "paper"), ("Project", "project"), ("Code", "code")):
            if pub[field] != "":
                url = escape(pub[field], quote=True)
                publication_links.append(
                    f'<a class="publication-action" href="{url}" target="_blank" '
                    f'rel="noopener noreferrer">{label} <span aria-hidden="true">↗</span></a>'
                )

        if "github_star" in pub:
            github_repo = escape(pub["github_star"], quote=True)
            publication_links.append(
                f'<a class="github-stars-link" href="https://github.com/{github_repo}" '
                'target="_blank" rel="noopener noreferrer" aria-label="View GitHub stars">'
                f'<img class="github-stars" src="https://img.shields.io/github/stars/{github_repo}'
                '?style=social&amp;cacheSeconds=86400" alt="GitHub stars" loading="lazy" /></a>'
            )

        if publication_links:
            content.append('<div class="publication-links">')
            content += publication_links
            content.append("</div>")

        if "extra" in pub and pub["extra"] != "":
            content.append(f'<div class="publication-extra">{pub["extra"]}</div>')

        info["content"] = content
        all_pubs += generateHTML(segments["_single_pub_template"], info, False)

    pubs = {"pubs": all_pubs}
    return generateHTML(segments["_pubs_template"], pubs, False)


def generateIndexHTML(segments):
    preparePage(segments, "home")
    segments["body_1"] = parseNews(segments["_news"], short=True, limit=5)
    segments["body_2"] = parsePubs(segments)
    generateHTML(segments["_template"], segments, True, "./index.html")


def generateNewsHTML(segments):
    preparePage(segments, "news")
    segments["body_2"] = parseNews(segments["_news"], False)
    generateHTML(segments["_template"], segments, True, "./news.html")


def generatePublicationsHTML(segments):
    preparePage(segments, "publications")
    segments["body_2"] = parsePubs(segments)
    generateHTML(segments["_template"], segments, True, "./pubs.html")


def generateExperienceHTML(segments):
    preparePage(segments, "experience")
    segments["body_2"] = [
        '<header class="section-heading experience-heading">',
        '  <span class="section-index" aria-hidden="true">Timeline /</span>',
        '  <h2 id="experience-title">Experience</h2>',
        "</header>",
    ] + segments["_experience"]
    generateHTML(segments["_template"], segments, True, "./experience.html")


def generateContactHTML(segments):
    preparePage(segments, "contact")
    segments["body_2"] = segments["_contact"]
    generateHTML(segments["_template"], segments, True, "./contact.html")


if __name__ == "__main__":
    base_segments = loadData()

    generateIndexHTML(copy.deepcopy(base_segments))
    generateNewsHTML(copy.deepcopy(base_segments))
    generatePublicationsHTML(copy.deepcopy(base_segments))
    generateExperienceHTML(copy.deepcopy(base_segments))
    generateContactHTML(copy.deepcopy(base_segments))
