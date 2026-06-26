"""
CSS scoping utility for Event Custom CSS.

Wraps each CSS rule selector with a body[data-event="<slug>"] prefix
so styles are isolated to a single event page and cannot leak to other
pages, the admin panel, or any other part of the site.

Supports: regular rules, @media / @supports nesting, @keyframes (pass-through).
Strips: /* comments */, @import (security).
"""

import re

# Selectors that are banned as top-level targets (they would still work
# inside the scope but signal a mistake — e.g. "body" becomes
# body[data-event="x"] body which is invalid, so we just reject them).
_UNSAFE_PATTERN = re.compile(
    r'(?:^|,)\s*(?:body|html|\*|:root)\s*(?:\{|,|$)',
    re.MULTILINE | re.IGNORECASE,
)

_IMPORT_PATTERN = re.compile(r'@import\b', re.IGNORECASE)


def validate_css(raw_css: str) -> list[str]:
    """Return a list of human-readable error strings (empty = OK)."""
    errors = []
    if not raw_css:
        return errors
    if _IMPORT_PATTERN.search(raw_css):
        errors.append('@import 不允許使用（避免載入外部資源）。')
    if _UNSAFE_PATTERN.search(raw_css):
        errors.append(
            '偵測到全站 Selector（body / html / * / :root），'
            '請改用活動區域 class，例如 .hero-title { … }'
        )
    return errors


def scope_css(raw_css: str, slug: str) -> str:
    """
    Return CSS with every rule selector prefixed by
    body[data-event="<slug>"].  Returns empty string when input is empty.
    """
    if not raw_css or not slug:
        return ''
    scope = f'body[data-event="{slug}"]'
    # Strip comments
    css = re.sub(r'/\*[\s\S]*?\*/', '', raw_css)
    # Strip @import lines (security)
    css = re.sub(r'@import\b[^;]*;', '', css, flags=re.IGNORECASE)
    return _process_block(css, scope, inside_at=False)


# ── internal helpers ────────────────────────────────────────────────────────

def _process_block(css: str, scope: str, inside_at: bool) -> str:
    """Recursively scope a CSS block."""
    output = []
    i = 0
    css = css.strip()
    n = len(css)

    while i < n:
        # skip whitespace
        while i < n and css[i] in ' \t\n\r':
            i += 1
        if i >= n:
            break

        if css[i] == '@':
            # ── @ rule ──────────────────────────────────────────────────
            # Collect header up to first { or ;
            j = i + 1
            while j < n and css[j] not in ('{', ';'):
                j += 1
            if j >= n:
                break
            header = css[i:j]
            if css[j] == ';':
                # @charset, @namespace — skip for security / irrelevance
                i = j + 1
                continue
            # Find matching closing brace
            inner_start = j + 1
            depth = 1
            k = inner_start
            while k < n and depth > 0:
                if css[k] == '{':
                    depth += 1
                elif css[k] == '}':
                    depth -= 1
                k += 1
            inner = css[inner_start:k - 1]
            at_kw = header.lstrip('@').split()[0].lower() if header else ''
            if at_kw in ('keyframes', '-webkit-keyframes', '-moz-keyframes',
                         'font-face', 'charset'):
                # Pass through unchanged
                output.append(f'{header}{{{inner}}}')
            else:
                # @media / @supports — scope inner rules
                output.append(f'{header}{{{_process_block(inner, scope, inside_at=True)}}}')
            i = k

        else:
            # ── Regular rule ─────────────────────────────────────────────
            j = i
            while j < n and css[j] != '{':
                j += 1
            if j >= n:
                break
            selector = css[i:j].strip()
            # Find matching closing brace
            depth = 1
            k = j + 1
            while k < n and depth > 0:
                if css[k] == '{':
                    depth += 1
                elif css[k] == '}':
                    depth -= 1
                k += 1
            block = css[j:k]  # includes { ... }
            if selector:
                scoped = ', '.join(
                    f'{scope} {s.strip()}'
                    for s in selector.split(',')
                    if s.strip()
                )
                output.append(f'{scoped}{block}')
            i = k

    return '\n'.join(output)
