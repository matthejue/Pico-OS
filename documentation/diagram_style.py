"""Shared README visual style, inspired by the presentation's palette.

Only paint and typography change here. Keep coordinates, paths, stroke widths,
marker IDs, labels and links intact. The generators' original swatches serve as
role identifiers; translating them on output also styles hand-authored SVGs.
"""

import re


FONT = "Cantarell, sans-serif"
INK = "#17313a"
LINE = "#637983"
GUIDE = "#9db7bc"
PANEL = "#f4f8f8"
HEADER = "#eaf3f4"
ALLOCATED = "#d8efef"
TEAL = "#167b84"
GREEN = "#25734f"
FREE = "#e7f3ea"
AMBER = "#805916"
FOCUS_FILL = "#fff1d6"

# Storage-domain colors used throughout the Section 11 startup diagrams.
STARTUP_MEMORY_COLORS = {
    "eprom": FOCUS_FILL,
    "periphery": PANEL,
    "kernel_sram": FREE,
    "process_shared_sram": ALLOCATED,
}
STARTUP_MEMORY_OPACITY = 0.3

# Ordinary outlines and headers stay neutral. Amber denotes an existing focus,
# a changed block/field or a waiting state, never a routine container. Teal
# denotes stored references/allocated data, green addresses/active or free
# states, and gray copies/metadata. Pale fills distinguish roles without
# turning every colored object into an attention marker.
COLORS = {
    # Recognize the checked-in palette as well as legacy generator swatches.
    "#17313a": INK, "#637983": LINE, "#9db7bc": GUIDE,
    "#f4f8f8": PANEL, "#eaf3f4": HEADER, "#d8efef": ALLOCATED,
    "#167b84": TEAL, "#25734f": GREEN, "#e7f3ea": FREE,
    "#805916": AMBER, "#fff1d6": FOCUS_FILL,
    **dict.fromkeys(("#172b3a", "#172536", "#192c38", "#111", "#222", "#000", "#000000"), INK),
    **dict.fromkeys(("#43576a", "#334155", "#475569", "#526472", "#555"), LINE),
    "#96a3ae": GUIDE,
    **dict.fromkeys(("#405ea8", "#174a7e", "#285fa3", "#27617b"), TEAL),
    "#785099": LINE,
    **dict.fromkeys(("#26715b", "#266b2e", "#39733b"), GREEN),
    **dict.fromkeys(("#9c3d15", "#8a5a00", "#995b0b", "#b87800"), AMBER),
    **dict.fromkeys(("#deecff", "#dceefa"), ALLOCATED),
    **dict.fromkeys(("#eaf4ff", "#eef5ff"), "#eaf5f5"),
    **dict.fromkeys(("#fff0cc", "#eadffa", "#f6eee5"), HEADER),
    **dict.fromkeys(("#fff8dc", "#fff1c7", "#fff2b2", "#ffd08a", "#fff5e3", "#fff3d6", "#f6e8d5"), FOCUS_FILL),
    **dict.fromkeys(("#e5f3de", "#e6efe5", "#edf9ed", "#edf7f1", "#e8f4e8"), FREE),
    **dict.fromkeys(("#f0f3f6", "#f1f5f9", "#f5f5f5", "#f1f3f5", "#f1f7ff", "#f6faff"), PANEL),
}

MERMAID_THEME = {
    "theme": "base",
    "fontFamily": FONT,
    "themeVariables": {
        "fontFamily": FONT,
        "background": "#ffffff",
        "primaryColor": PANEL,
        "primaryTextColor": INK,
        "primaryBorderColor": LINE,
        "secondaryColor": HEADER,
        "secondaryTextColor": INK,
        "secondaryBorderColor": LINE,
        "tertiaryColor": PANEL,
        "tertiaryTextColor": INK,
        "tertiaryBorderColor": LINE,
        "lineColor": LINE,
        "textColor": INK,
        "edgeLabelBackground": "#ffffff",
        "clusterBkg": PANEL,
        "clusterBorder": LINE,
        "titleColor": INK,
        "actorBkg": PANEL,
        "actorBorder": LINE,
        "actorTextColor": INK,
        "actorLineColor": LINE,
        "signalColor": LINE,
        "signalTextColor": INK,
        "labelBoxBkgColor": PANEL,
        "labelBoxBorderColor": LINE,
        "labelTextColor": INK,
        "loopTextColor": INK,
        "noteBkgColor": HEADER,
        "noteBorderColor": LINE,
        "noteTextColor": INK,
        "activationBkgColor": HEADER,
        "activationBorderColor": LINE,
        "stateBkg": PANEL,
        "stateBorder": LINE,
        "stateLabelColor": INK,
        "labelColor": INK,
        "altBackground": HEADER,
    },
    "themeCSS": "rect { rx: 0 !important; ry: 0 !important; } text, tspan, foreignObject, foreignObject * { font-family: Cantarell, sans-serif !important; }",
}


def style_svg(svg, *, name=""):
    """Restyle in place without reserializing XML or changing its composition.

    Hardware and build overview colors identify ordinary components, rather
    than changed/selected elements, so their amber/green outlines become gray.
    Marker IDs and URL references are deliberately left untouched.
    """
    neutral_groups = name in ("picoos-build-boot", "intended-hardware")
    # Purple was used for both stored pointers and value transfers. Decide
    # from the figure's content, not the old swatch: memory/list diagrams and
    # these process figures use it exclusively for stored references.
    metadata_color = LINE
    if name.startswith("memory-") or name in (
        "process-load-complete", "process-loaded-stack", "process-terminal-input-buffer",
    ):
        metadata_color = TEAL
    elif name == "process-load-transfer":
        metadata_color = GREEN  # ProcessLoad.base_address, not a value copy.

    # The process-layout label helper inherited its color from LINE. Darken
    # those labels without also darkening neutral arrowheads using that swatch.
    svg = re.sub(r'(<(?:text|tspan)\b[^>]*\bfill=")#43576a(")',
                 lambda m: m.group(1) + INK + m.group(2), svg)

    def paint(match):
        attribute, original = match.groups()
        color = original.lower()
        replacement = COLORS.get(color, original)
        if color == "#785099":
            replacement = metadata_color
        if neutral_groups:
            if attribute == "stroke":
                replacement = LINE
            elif color in ("#fff8dc", "#edf9ed"):
                replacement = PANEL
        return f'{attribute}="{replacement}"'

    svg = re.sub(r'\b(fill|stroke|stop-color|color)="(#[\da-fA-F]{3,8})"', paint, svg)
    # Mermaid can copy a highlighted box's thick outline onto its label.
    # Keep text fill-only so those outlines cannot obscure the letters.
    svg = re.sub(r'(<(?:text|tspan)\b[^>]*\s)stroke="[^"]*"',
                 r'\1stroke="none"', svg)
    svg = re.sub(r'\bfont-family="[^"]*"', f'font-family="{FONT}"', svg)
    return re.sub(r'\b(rx|ry)="[^"]*"', r'\1="0"', svg)
