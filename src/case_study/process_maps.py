"""As-is and to-be process maps: Mermaid source (numbers filled in from the data) + PNG via mermaid-cli."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from case_study.paths import FIGS, MAPS, ROOT

STYLE = """
    classDef pain fill:#FDECEC,stroke:#D64545,color:#7F1D1D
    classDef good fill:#E6F4F1,stroke:#2A9D8F,color:#134E4A
    classDef step fill:#EEF2F7,stroke:#1F3A5F,color:#1F2937
    classDef endnode fill:#1F3A5F,stroke:#1F3A5F,color:#FFFFFF
"""


def as_is(f: dict) -> str:
    r1 = f["impacts"]["R1"]["baseline"]
    return f"""%% As-is: NYC DOT street-maintenance request handling (derived from 2025 311 records)
flowchart TB
    subgraph S1["1 · Intake (311)"]
        direction LR
        A([Resident reports issue<br/>phone / web / app]):::step --> B[311 creates request and<br/>routes to DOT by complaint type]:::step
        B --> B2[No photo, location or<br/>permit check]:::pain
    end
    subgraph S2["2 · DOT queue and inspection"]
        direction LR
        C[DOT queue<br/>no aging trigger]:::pain --> D[Inspector dispatched]:::step --> E{{Defect found<br/>and DOT asset?}}:::step
        E -- "no defect / duplicate / no info" --> X1([Close: failure demand<br/>{f['street_condition_pct_failure_demand']:.0f}% of Street Condition]):::pain
        E -- "not DOT asset" --> X2([Refer to DEP / utility<br/>{r1['misrouted_requests']:,} misroutes, median {r1['median_days_until_referral']:.1f} d]):::pain
        T["Street lights: {f['sl_tail_pct_requests']:.0f}% wait > 30 d<br/>= {f['sl_tail_pct_request_days']:.0f}% of their waiting"]:::pain -.- C
    end
    subgraph S3["3 · Repair and closure"]
        direction LR
        G{{Who repairs?}}:::step -- DOT crew --> H[Repair]:::step
        G -- "owner / contractor" --> I[Notice, CAR or summons<br/>30-day window]:::step
        H --> J([Close request]):::endnode
        I --> J
        J --> K["Resolution text: {f['pct_outcome_not_published']:.0f}% say<br/>'see DOT website' (no outcome)"]:::pain
    end
    S1 --> S2
    S2 -- "defect found, DOT asset" --> S3
{STYLE}"""


def to_be(f: dict) -> str:
    return f"""%% To-be: proposed process (recommendations R1-R4)
flowchart TB
    subgraph S1["1 · Smart intake and triage (R1, R2)"]
        direction LR
        A([Resident reports issue]):::step --> B[Guided questions<br/>photo + map pin for<br/>high no-defect descriptors]:::good
        B --> C{{Sewer / manhole /<br/>utility cues? R1}}:::good
        C -- yes --> X1([Route straight to<br/>DEP / utility]):::good
        C -- no --> D{{Open request at<br/>same location?}}:::good
        D -- yes --> X2([Link as duplicate,<br/>notify resident]):::good
        D -- no --> E{{Active street-work<br/>permit here? R2}}:::good
        E -- yes --> X3([Notify permit holder,<br/>no inspector visit]):::good
    end
    subgraph S2["2 · DOT work with aging control (R3)"]
        direction LR
        F[DOT triage queue]:::step --> G[Inspect and repair<br/>or issue CAR / summons]:::step
        F --> M{{Still open<br/>at day 30?}}:::good
        M -- yes --> N[Escalate: supervisor review,<br/>Con Ed / contractor chase,<br/>weekly aging report]:::good
        N --> G
    end
    subgraph S3["3 · Closure and measurement (R4)"]
        direction LR
        H([Close with standard<br/>outcome code]):::endnode --> P[(Outcome published to Open Data:<br/>first-time-fix and failure-demand KPIs)]:::good
    end
    S1 -- "new DOT job" --> S2
    S2 --> S3
{STYLE}"""


def render(f: dict, out_dir: Path = MAPS, png_dir: Path = FIGS) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, text in (("as_is", as_is(f)), ("to_be", to_be(f))):
        mmd = out_dir / f"{name}.mmd"
        mmd.write_text(text)
        files[f"{name}_mmd"] = mmd
        png = render_png(mmd, png_dir / f"process_{name}.png")
        if png:
            files[f"{name}_png"] = png
    return files


def _mmdc() -> str | None:
    local = ROOT / "node_modules" / ".bin" / "mmdc"
    return str(local) if local.exists() else shutil.which("mmdc")


def render_png(mmd: Path, png: Path) -> Path | None:
    """Render with mermaid-cli if installed (npm ci); otherwise keep the committed PNG."""
    exe = _mmdc()
    if not exe:
        print(f"  mermaid-cli not found; keeping existing {png.name} (run `npm ci` to re-render)")
        return png if png.exists() else None
    cfg = ROOT / "process_maps" / "puppeteer.json"
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
    cmd = [exe, "-i", str(mmd), "-o", str(png), "-s", "2.5", "-b", "white", "-c", str(ROOT / "process_maps" / "mermaid.json")]
    if chrome:
        cfg.write_text(json.dumps({"executablePath": chrome, "args": ["--no-sandbox"]}))
        cmd += ["-p", str(cfg)]
    subprocess.run(cmd, check=True, capture_output=True, timeout=180)
    return png
