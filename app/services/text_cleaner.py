import re

GARBAGE_PATTERNS = [
    r"on this page.*?\n\n",
    r"table of contents.*?\n\n",
    r"share this.*?\n",
    r"subscribe.*?\n",
    r"related articles.*?\n",
    r"cookie policy.*?\n",
    r"privacy policy.*?\n",
]

def clean_text(text:str) -> str:
    if not text:
        return ""
    
    text = text.replace("\r","\n")

    for pattern in GARBAGE_PATTERNS:
        text = re.sub(pattern,"",text,flags=re.IGNORECASE | re.DOTALL)
    
    text = re.sub(r"`{1,3}","",text)
    text = re.sub(r"\*\*","",text)

    text = re.sub(r"[ \t]{2,}"," ",text)
    text = re.sub(r"\n{3,}","\n\n",text)

    cleaned_lines = []
    for line in text.strip("\n"):
        line = line.strip()

        if len(line)<30:
            continue

        if re.match(r"^[^a-zA-Z]{10,}$", line):
            continue

        cleaned_lines.append(line)

    return "\n\n".join(cleaned_lines).strip()