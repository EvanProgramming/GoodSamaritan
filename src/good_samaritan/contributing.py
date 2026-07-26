"""Discover and safely surface repository contribution guidance."""
from __future__ import annotations

import re
from pathlib import Path


def contribution_files(root: Path) -> list[Path]:
    """Return common contribution guides anywhere in a cloned repository."""
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or ".good-samaritan" in path.name:
            continue
        name = path.name.casefold()
        if name.startswith("contribut") and path.suffix.casefold() in {"", ".md", ".rst", ".txt"}:
            found.append(path)
    return sorted(found, key=lambda path: (len(path.parts), str(path).casefold()))[:12]


def guidance(root: Path, maximum_chars: int = 36_000) -> str:
    """Build a bounded, path-labelled contribution guide for the coding prompt."""
    remaining = maximum_chars
    sections: list[str] = []
    for path in contribution_files(root):
        if remaining <= 0:
            break
        text = path.read_text(errors="replace")[:remaining]
        sections.append(f"--- {path.relative_to(root)} ---\n{text}")
        remaining -= len(text)
    return "\n\n".join(sections) or "(No CONTRIBUTING/CONTRIBUTE guidance was found.)"


def rejects_automated_contributions(text: str) -> bool:
    """Recognize explicit policy rejection without treating ordinary advice as one."""
    normalized = " ".join(text.casefold().split())
    patterns = (
        r"(?:do not|don't|cannot|can't|will not) accept (?:ai|bot|automated|machine.generated) (?:generated )?(?:contributions?|pull requests?|prs?)",
        r"(?:ai|bot|automated|machine.generated) (?:generated )?(?:contributions?|pull requests?|prs?) (?:are )?not accepted",
        r"no (?:ai|bot|automated) (?:generated )?(?:contributions?|pull requests?|prs?)",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)
