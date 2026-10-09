"""Check versioned/public candidate files without printing matched secrets."""

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "literal JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b"),
    "credential URL": re.compile(r"(?:mysql(?:\+pymysql)?|postgres(?:ql)?|https?)://[^\s/:]+:[^\s/@]+@"),
}
PRIVACY_PATTERNS = {
    "workstation path": re.compile(r"[A-Za-z]:[\\/]+(?:Users|Programming|UIC[^\\/]*)[\\/]"),
    "private deployment path": re.compile(r"/home/projects/[A-Za-z0-9_-]+"),
}


def findings(name, data, *, privacy=True):
    if b"\0" in data:
        return []
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    patterns = dict(SECRET_PATTERNS)
    if privacy:
        patterns.update(PRIVACY_PATTERNS)
    return [
        (name, number, label)
        for number, line in enumerate(content.splitlines(), 1)
        for label, pattern in patterns.items()
        if pattern.search(line)
    ]


def main():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, check=True, capture_output=True,
    )
    problems = []
    checked = 0
    for raw in sorted(set(result.stdout.split(b"\0")) - {b""}):
        name = raw.decode("utf-8")
        path = ROOT / name
        if not path.is_file():
            continue
        parts = Path(name).parts
        private_file = (
            any(part in {".deploy", "internal", "node_modules", ".venv"} for part in parts)
            or (path.name.startswith(".env") and path.name != ".env.example")
            or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".pem", ".key", ".p12", ".pfx"}
            or (parts[0] in {"uploads", "logs", "backups"} and path.name != ".gitkeep")
        )
        if private_file:
            problems.append((name, 0, "private runtime file"))
            continue
        checked += 1
        # Tests include deliberate credential URLs for parser verification.
        issues = findings(name, path.read_bytes())
        if "tests" in parts or path.name.startswith("test_"):
            issues = [item for item in issues if item[2] != "credential URL"]
        problems.extend(issues)
    for name, line, label in problems:
        print(f"{name}:{line}: {label} [value hidden]")
    if problems:
        print(f"Public content check failed: {len(problems)} finding(s).")
        return 1
    print(f"Public content check passed: {checked} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
