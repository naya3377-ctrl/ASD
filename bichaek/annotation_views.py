"""Two views of one comment list: what was written, and what was marked.

The comment panel shows memos (anything with written text, a note, a
reply thread, a drawing or stamp) apart from marked passages (highlights,
underlines, strike-outs), so editing a memo is about its words and the
marked passages read together like a summary of the document. A highlight
that also carries a memo appears in both: as the memo, and as the passage.
Nothing here changes the PDF; it only arranges the list the engine reads.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
MARKUP_TYPES = frozenset(("Highlight", "Underline", "StrikeOut", "Squiggly"))


def is_markup(item):
    return item.get("type") in MARKUP_TYPES and not item.get("reply")


def threads(tree):
    """Split the threaded list (each item followed by its replies, deeper)
    into [root, replies...] groups, keeping order."""
    groups = []
    for item in tree:
        if item.get("depth", 0) == 0 or not groups:
            groups.append([item])
        else:
            groups[-1].append(item)
    return groups


def split_views(tree):
    """(notes, marks). Notes keep whole threads whose root has written text,
    replies, a review state, or is not a text mark. Marks list every text
    mark once, in page order, noting whether it carries a memo."""
    notes, marks = [], []
    for group in threads(tree):
        root = group[0]
        written = bool(str(root.get("content") or "").strip()) or bool(root.get("state"))
        if not is_markup(root) or written or len(group) > 1:
            notes.extend(group)
        for item in group:
            if is_markup(item):
                marks.append(dict(item, depth=0, note=str(item.get("content") or "").strip(),
                                  replies=len(group) - 1 if item is root else 0))
    return notes, marks


def summary_text(marks, name=""):
    """The marked passages as plain text, page by page, with their memos."""
    lines = [(name + " · " if name else "") + "형광펜 모음"]
    page = None
    for item in marks:
        if item.get("page") != page:
            page = item.get("page")
            lines += ["", f"{page + 1}쪽"]
        quote = " ".join(str(item.get("quote") or "").split()) or "(글자를 읽을 수 없는 표시)"
        lines.append(f"· {quote}")
        if item.get("note"):
            lines.append(f"  메모: {' '.join(item['note'].split())}")
    return "\n".join(lines) + "\n"
