"""Scoped CSS sanitizer — whitelist-based selector and property enforcement.

Parses simple CSS rule sets (no @keyframes, no nested at-rules beyond @import detection),
validates every selector and property against curated whitelists, and blocks dangerous
constructs (url(), javascript:, expression(), @import).

Used on both backend (before DB persist) and frontend (before DOM injection).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Whitelists ───────────────────────────────────────────────────────────────

CSS_SANITIZER_ALLOWED_SELECTORS: set[str] = {
    ".kf-slide",
    ".kf-slide[data-template]",
    ".kf-slide[data-category]",
    ".kf-layer",
    ".kf-layer[data-layer-id]",
    ".kf-photo-layer",
    ".kf-text-layer",
    ".kf-shape-layer",
    ".kf-mask-layer",
    ".kf-timeline-layer",
    ".kf-background-layer",
    ".kf-texture-layer",
    ".kf-vignette-layer",
    ".kf-caption",
    ".kf-meta",
    ".kf-photo-frame",
    ".kf-caption-panel",
}

CSS_SANITIZER_ALLOWED_PROPERTIES: set[str] = {
    "color",
    "background",
    "background-color",
    "background-image",
    "background-size",
    "background-position",
    "background-repeat",
    "background-attachment",
    "background-blend-mode",
    "opacity",
    "box-shadow",
    "text-shadow",
    "filter",
    "backdrop-filter",
    "mix-blend-mode",
    "border",
    "border-color",
    "border-style",
    "border-width",
    "border-top",
    "border-right",
    "border-bottom",
    "border-left",
    "border-top-color",
    "border-top-style",
    "border-top-width",
    "border-right-color",
    "border-right-style",
    "border-right-width",
    "border-bottom-color",
    "border-bottom-style",
    "border-bottom-width",
    "border-left-color",
    "border-left-style",
    "border-left-width",
    "border-radius",
    "border-top-left-radius",
    "border-top-right-radius",
    "border-bottom-left-radius",
    "border-bottom-right-radius",
    "letter-spacing",
    "line-height",
    "font",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "font-variant",
    "text-align",
    "text-decoration",
    "text-transform",
    "text-indent",
    "text-overflow",
    "text-wrap",
    "text-wrap-mode",
    "text-wrap-style",
    "white-space",
    "word-spacing",
    "word-break",
    "transition",
    "transition-delay",
    "transition-duration",
    "transition-property",
    "transition-timing-function",
    "animation",
    "animation-name",
    "animation-duration",
    "animation-timing-function",
    "animation-delay",
    "animation-iteration-count",
    "animation-direction",
    "animation-fill-mode",
    "animation-play-state",
    "transform",
    "transform-origin",
    "clip-path",
    "mask",
    "mask-image",
    "mask-size",
    "mask-position",
    "mask-repeat",
    "mask-composite",
    "mask-mode",
    "mask-type",
    "mask-origin",
    "mask-clip",
}

# Patterns that make the entire CSS block invalid
_DANGEROUS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"@import", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"@font-face", re.IGNORECASE),
    re.compile(r"behavior\s*:", re.IGNORECASE),
    re.compile(r"url\s*\(\s*['\"]?\s*https?://", re.IGNORECASE),
    re.compile(r"url\s*\(\s*['\"]?\s*data:", re.IGNORECASE),
]

# Selectors that must never appear (even as parts of compound selectors)
_FORBIDDEN_SELECTOR_PARTS: set[str] = {
    "html", "body", "#app", "*", "script", "iframe", "input", "button",
    "a[href]", "head", "meta", "link",
}

_PROPERTY_REGEX = re.compile(r"([a-zA-Z-]+)\s*:")

# Pseudo-classes that can reference external elements (block if they contain forbidden selectors)
_DANGEROUS_PSEUDO_FUNCTIONS = re.compile(r":(has|is|where|not)\s*\(")


@dataclass
class SanitizeResult:
    safe_css: str = ""
    warnings: list[str] = field(default_factory=list)
    blocked_count: int = 0

    @property
    def is_valid(self) -> bool:
        """True if no dangerous patterns caused the entire block to be rejected."""
        return not any("entire block rejected" in w for w in self.warnings)


def _block_has_dangerous_patterns(block: str) -> bool:
    """Check if a CSS block contains any dangerous patterns that should reject the entire block."""
    return any(p.search(block) for p in _DANGEROUS_PATTERNS)


def _selector_is_safe(selector: str) -> list[str]:
    """Return empty list if selector is safe, or warning messages if blocked."""
    stripped = selector.strip()
    if not stripped:
        return ["empty selector"]

    # Split comma selectors — ALL parts must be safe
    parts = [p.strip() for p in stripped.split(",")]

    for part in parts:
        # 1. Check for forbidden selector parts embedded anywhere
        for forbidden in _FORBIDDEN_SELECTOR_PARTS:
            if forbidden in part:
                return [f"Blocked selector: {stripped} (contains forbidden '{forbidden}')"]

        # 2. Check for parent-escape pseudo functions
        pseudo_match = _DANGEROUS_PSEUDO_FUNCTIONS.search(part)
        if pseudo_match:
            return [f"Blocked selector: {stripped} (dangerous pseudo-function)"]

        # 3. Must contain a recognized KinFrame class
        attr_match = re.match(r"\.([a-zA-Z-]+)", part)
        if not attr_match:
            return [f"Blocked selector: {stripped} (no recognized KinFrame class)"]

        base_class = f".{attr_match.group(1)}"
        if base_class not in CSS_SANITIZER_ALLOWED_SELECTORS:
            return [f"Blocked selector: {stripped} (unknown class '{base_class}')"]

    return []  # Safe


def _sanitize_declarations(declarations: str) -> tuple[str, list[str]]:
    """Filter property declarations, returning (safe_declarations, warnings)."""
    safe_parts: list[str] = []
    warnings: list[str] = []

    for decl in declarations.split(";"):
        decl = decl.strip()
        if not decl:
            continue

        match = _PROPERTY_REGEX.match(decl)
        if not match:
            continue

        prop_name = match.group(1).lower().strip()
        if prop_name in CSS_SANITIZER_ALLOWED_PROPERTIES:
            safe_parts.append(decl)
        else:
            warnings.append(f"Blocked property: {prop_name}")

    return "; ".join(safe_parts), warnings


def sanitize_scoped_css(raw_css: str) -> SanitizeResult:
    """Parse and sanitize a scoped CSS string, returning only safe rules.

    A CSS block is entirely rejected if it contains @import, javascript:,
    expression(), or url() with external protocols. Otherwise, individual
    rules/declarations are filtered against the whitelists.

    Returns a SanitizeResult with safe_css (empty string if nothing passes),
    warnings, and blocked_count.
    """
    if not raw_css or not raw_css.strip():
        return SanitizeResult(safe_css="", warnings=[], blocked_count=0)

    warnings: list[str] = []
    blocked_count = 0

    # Check for dangerous patterns across the whole CSS
    if _block_has_dangerous_patterns(raw_css):
        return SanitizeResult(
            safe_css="",
            warnings=["entire block rejected: contains dangerous pattern (@import, url(), javascript:, expression())"],
            blocked_count=1,
        )

    # Parse CSS into rule blocks: selector { declarations }
    # Simple regex-based parser for the scoped CSS format AI generates
    rule_pattern = re.compile(
        r'([^{}]+?)\s*\{\s*([^{}]*?)\s*\}',
        re.DOTALL,
    )

    safe_rules: list[str] = []

    for match in rule_pattern.finditer(raw_css):
        raw_selector = match.group(1).strip()
        raw_body = match.group(2).strip()

        # Check selector
        selector_warnings = _selector_is_safe(raw_selector)
        if selector_warnings:
            blocked_count += 1
            warnings.extend(selector_warnings)
            continue

        # Sanitize declarations
        safe_decls, decl_warnings = _sanitize_declarations(raw_body)
        if decl_warnings:
            warnings.extend(decl_warnings)

        if safe_decls:
            safe_rules.append(f"{raw_selector} {{ {safe_decls}; }}")
        else:
            blocked_count += 1
            warnings.append(f"Rule blocked (no valid properties): {raw_selector}")

    safe_css = "\n".join(safe_rules)

    # If nothing passed but we had rules, note it
    if not safe_css and not warnings and rule_pattern.findall(raw_css):
        warnings.append("All rules filtered out by whitelist")

    return SanitizeResult(
        safe_css=safe_css,
        warnings=warnings,
        blocked_count=blocked_count,
    )
