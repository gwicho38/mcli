"""Transform GitHub Actions workflows for act-first CI on private repos."""
from __future__ import annotations

from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML

MARKER = "mcli-ci: hosted-triggers-stripped"
SELF_HOSTED_FILENAME = "self-hosted-ci.yml"
HOSTED_PREFIXES = ("ubuntu", "macos", "windows")


def is_hosted_label(label: str) -> bool:
    """True if a runs-on label names a GitHub-hosted runner image."""
    return str(label).lower().startswith(HOSTED_PREFIXES)


def runs_on_is_hosted(runs_on) -> bool:
    """Classify a job's runs-on. Conservative: unknown expressions count as hosted."""
    if runs_on is None:
        return False
    if isinstance(runs_on, (list, tuple)):
        labels = [str(x) for x in runs_on]
        if any("self-hosted" in lbl for lbl in labels):
            return False
        return any(is_hosted_label(lbl) for lbl in labels)
    text = str(runs_on)
    if "self-hosted" in text:
        return False
    if "${{" in text:
        return True  # unknown matrix/expression -> assume hosted to stop cost
    return is_hosted_label(text)


# NOTE: ruamel.yaml round-trip (YAML(), typ='rt') is the SAFE, correct loader here.
# It does NOT execute `!!python/object` tags like PyYAML's yaml.load(). Do not
# "fix" this to PyYAML safe_load — that would strip comments/formatting and break
# round-tripping. Round-trip preservation is a hard requirement of this transform.
def _yaml() -> YAML:
    y = YAML()
    y.version = (1, 2)        # critical: keeps bare `on:` a string, not boolean True
    y.preserve_quotes = True
    y.width = 4096            # avoid reflowing long lines
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def workflow_has_hosted_job(doc) -> bool:
    """True if any job in the parsed workflow targets a GitHub-hosted runner."""
    if not isinstance(doc, dict):
        return False
    jobs = doc.get("jobs") or {}
    for job in jobs.values():
        if isinstance(job, dict) and runs_on_is_hosted(job.get("runs-on")):
            return True
    return False


def strip_hosted_triggers(doc) -> bool:
    """Remove push/pull_request from `on:`, ensure workflow_dispatch. Returns changed."""
    on = doc.get("on")
    if on is None:
        return False
    changed = False
    if isinstance(on, dict):
        for key in ("push", "pull_request"):
            if key in on:
                del on[key]
                changed = True
        if "workflow_dispatch" not in on:
            on["workflow_dispatch"] = None
            changed = True
    elif isinstance(on, list):
        kept = [x for x in on if x not in ("push", "pull_request")]
        if "workflow_dispatch" not in kept:
            kept.append("workflow_dispatch")
        if kept != list(on):
            doc["on"] = kept
            changed = True
    elif isinstance(on, str):
        if on in ("push", "pull_request"):
            doc["on"] = "workflow_dispatch"
            changed = True
    return changed


def transform_file(path: Path) -> bool:
    """Strip hosted triggers in-place if the workflow has a hosted job. Idempotent."""
    path = Path(path)
    text = path.read_text()
    if MARKER in text:
        return False
    yaml = _yaml()
    doc = yaml.load(text)
    if not workflow_has_hosted_job(doc):
        return False
    strip_hosted_triggers(doc)
    doc.yaml_set_start_comment(f"{MARKER}\n")
    buf = StringIO()
    yaml.dump(doc, buf)
    path.write_text(buf.getvalue())
    return True


def render_self_hosted_workflow(test_command: str, with_pull_request: bool) -> str:
    """Render the dormant self-hosted fallback workflow as YAML text."""
    triggers = "  workflow_dispatch:\n"
    if with_pull_request:
        triggers += "  pull_request:\n"
    ref = "${{ github.ref }}"
    return (
        f"# {MARKER}\n"
        "name: self-hosted-ci\n"
        "on:\n"
        f"{triggers}"
        "concurrency:\n"
        f"  group: self-hosted-ci-{ref}\n"
        "  cancel-in-progress: true\n"
        "jobs:\n"
        "  test:\n"
        "    runs-on: [self-hosted, Linux, X64]\n"
        "    timeout-minutes: 30\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "      - name: Run tests\n"
        f"        run: {test_command}\n"
    )


def write_self_hosted_workflow(workflows_dir: Path, test_command: str,
                               with_pull_request: bool) -> bool:
    """Write self-hosted-ci.yml if absent. Returns True if created."""
    workflows_dir = Path(workflows_dir)
    target = workflows_dir / SELF_HOSTED_FILENAME
    if target.exists():
        return False
    workflows_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(render_self_hosted_workflow(test_command, with_pull_request))
    return True
