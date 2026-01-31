import re

HEADING_PATTERN = re.compile(
    r"^(#{1,3}\s+.+|[A-Z][A-Za-z0-9 ,:-]{5,}$)",
    re.MULTILINE
)

BAD_HEADINGS = [
    "on this page",
    "table of contents",
    "wrapping up",
    "key takeaways",
    "remember",
    "faqs",
    "faq",
    "reviews",
    "comments",
]

def is_valid_heading(heading: str) -> bool:
    h = heading.lower()

    # drop TOC / footer junk
    for bad in BAD_HEADINGS:
        if bad in h:
            return False

    # drop personal names / testimonials
    if len(h.split()) <= 2:
        return False

    # drop headings that are full sentences
    if h.endswith("."):
        return False

    return True


def split_into_sections(text: str):
    if not text:
        return []

    matches = list(HEADING_PATTERN.finditer(text))

    if not matches:
        return [{
            "heading": "Main Content",
            "content": text.strip()
        }]

    sections = []

    for i, match in enumerate(matches):
        heading = match.group().strip()

        if not is_valid_heading(heading):
            continue

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        content = text[start:end].strip()

        if len(content) < 300:
            continue

        sections.append({
            "heading": heading,
            "content": content
        })

    return sections