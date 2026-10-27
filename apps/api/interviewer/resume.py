"""Local, extractive resume suggestions. Never infer achievements from document text."""
import re


SECTIONS = {
    "projects": True, "personal projects": True, "academic projects": True,
    "experience": True, "work experience": True, "professional experience": True,
    "employment": True, "achievements": True, "activities": True,
    "student profile": False, "profile": False, "summary": False,
    "professional summary": False, "objective": False, "skills": False,
    "key skills": False, "technical skills": False, "education": False,
    "education & certifications": False, "certifications": False,
    "disclosure": False, "declaration": False, "contact": False,
    "interests": False, "references": False,
}
def section_heading(line):
    heading = line.strip().lower().rstrip(":")
    if heading in SECTIONS:
        return heading
    prefix = heading.split(":", 1)[0].strip()
    return prefix if ":" in heading and prefix in SECTIONS else None


BULLET = re.compile(r"^[\u2022\u25cf\uf0b7*\-]\s+")


def experience_claims(pages, redact):
    """Join wrapped lines, keep source offsets, and ignore non-experience sections.

    These are editable suggestions, not semantic resume analysis. Unstructured
    pasted text remains supported; headings are used only when explicitly present.
    """
    structured = any(section_heading(line) is not None
                     for page in pages for line in page["text"].splitlines())
    enabled = not structured
    claims = []
    offset = 0
    title = ""
    title_pending = False
    for page in pages:
        block = []

        def flush():
            if not block:
                return
            source = "".join(line for _, line in block).rstrip()
            clean = redact(source)
            contribution = " ".join(BULLET.sub("", clean).split())
            if len(contribution) > 15:
                claims.append({"source_bullet": clean, "page": page["page"],
                               "offset": block[0][0], "project": redact(title),
                               "contribution": contribution, "technology": "",
                               "result": "", "measurement": "", "confidentiality": ""})
            block.clear()

        for raw in page["text"].splitlines(keepends=True):
            line = raw.strip()
            start = offset + len(raw) - len(raw.lstrip())
            offset += len(raw)
            heading = section_heading(line)
            if heading is not None:
                flush()
                enabled = SECTIONS[heading]
                title = ""
                title_pending = False
                continue
            if not line:
                flush()
                continue
            if not enabled:
                continue
            # Contact information must never become a proposed contribution.
            if re.search(r"@|https?://|www\.|\b(?:email|phone|address)\s*:", line, re.I) or re.search(r"\+?\d[\d ()-]{8,}\d", line):
                flush()
                continue
            bullet = bool(BULLET.match(line))
            previous_finished = bool(block and block[-1][1].rstrip().endswith((".", "!", "?")))
            short_title = structured and not bullet and len(line) <= 100 and len(line.split()) <= 12 and not line.endswith((".", ",", ";", ":")) and not re.match(r"(?i)^(built|implemented|developed|created|designed|led|used|using|completed|participated|secured|features|it|the|a|an|this)\b", line)
            if bullet or previous_finished or sum(len(value) for _, value in block) + len(raw) > 4500:
                flush()
            if short_title and not block and not title_pending:
                # A continuation without sentence punctuation stays in its block.
                title = line
                title_pending = True
                continue
            block.append((start, raw.lstrip() if not block else raw))
            title_pending = False
        flush()
        offset += 1  # Matches the newline joining pages in the review text.
    return claims[:50]
