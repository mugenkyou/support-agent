import os
import re

PATTERNS = {
    "personal_path_windows": re.compile(r"C:\\Users\\[a-zA-Z0-9_-]+", re.IGNORECASE),
    "personal_path_mac": re.compile(r"/Users/[a-zA-Z0-9_-]+"),
    "personal_path_linux": re.compile(r"/home/[a-zA-Z0-9_-]+"),
    "openai_api_key": re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    "github_token": re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    "bearer_token": re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]{25,}"),
    "hardcoded_password": re.compile(r"""(?:password|passwd|pwd)\s*[:=]\s*["'][^"']{6,}["']""", re.IGNORECASE),
    "hardcoded_token": re.compile(r"""(?:secret|api_key|token)\s*[:=]\s*["'][^"']{10,}["']""", re.IGNORECASE),
}

EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", "venv", ".venv", "scratch", "data"}
EXCLUDED_EXTS = {".sqlite", ".sqlite3", ".db", ".pyc", ".png", ".jpg", ".jpeg", ".lock", ".csv", ".jsonl"}

findings = []

for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".gemini")]
    for file in files:
        ext = os.path.splitext(file)[1].lower()
        if ext in EXCLUDED_EXTS:
            continue
        filepath = os.path.join(root, file)
        if os.path.getsize(filepath) > 2 * 1024 * 1024:
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f, 1):
                    for pat_name, pat in PATTERNS.items():
                        matches = pat.findall(line)
                        if matches:
                            # Filter benign test strings like "test@example.com" or mock password reset test queries
                            is_benign = any(b in line for b in [
                                "test_password", "reset my password", "forgot password",
                                "mock", "example", "prompt", "dummy", "placeholder", "fake"
                            ])
                            if not is_benign:
                                findings.append({
                                    "file": filepath,
                                    "line": line_idx,
                                    "pattern": pat_name,
                                    "snippet": line.strip()[:100]
                                })
        except Exception as e:
            pass

print(f"Total findings: {len(findings)}")
for f in findings[:30]:
    print(f"[{f['pattern']}] {f['file']}:{f['line']} -> {f['snippet']}")
