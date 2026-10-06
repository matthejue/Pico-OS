"""Apply the shared style to current README diagrams without rebuilding them.

Run after editing diagram_style.py. Existing Mermaid layout options are kept;
SVG geometry, labels, links and marker IDs are never replaced or regenerated.
The external presentation is not an input to this script.
"""

import json
from pathlib import Path
import re

from diagram_style import AMBER, FOCUS_FILL, INK, MERMAID_THEME, PANEL, style_svg


ROOT = Path(__file__).resolve().parent.parent


def style_mermaid(match):
    source = match.group(1)
    init = re.match(r'%%\{init:\s*(\{.*?\})\s*\}%%\n', source)
    options = json.loads(init.group(1)) if init else {}
    if init:
        source = source[init.end():]
    # Only overwrite appearance keys; keep sequence/flowchart layout settings.
    options.update(MERMAID_THEME)
    source = re.sub(
        r'(classDef added|style preprocessing) fill:[^,]+,stroke:[^,]+,(stroke-width:[^,]+),color:[^\n]+',
        lambda m: f"{m.group(1)} fill:{FOCUS_FILL},stroke:{AMBER},{m.group(2)},color:{INK}",
        source,
    )
    # These boxes identify storage domains; none warrants a warning/focus tint.
    source = re.sub(r'box (?:rgb\(\d+,\s*\d+,\s*\d+\)|#[\da-fA-F]{6})', f'box {PANEL}', source)
    return '```mermaid\n%%{init: ' + json.dumps(options, separators=(",", ":")) + '}%%\n' + source + '\n```'


def main():
    images = ROOT / "documentation/images"
    for path in sorted(images.glob("*.svg")):
        svg = style_svg(path.read_text(), name=path.stem)
        path.write_text(svg)
    readme = ROOT / "README.md"
    readme.write_text(re.sub(r'```mermaid\n(.*?)\n```', style_mermaid, readme.read_text(), flags=re.S))
    (ROOT / "documentation/readme_pdf_mermaid.json").write_text(json.dumps(MERMAID_THEME, indent=2) + "\n")


if __name__ == "__main__":
    main()
