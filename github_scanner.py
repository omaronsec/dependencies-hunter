import os
import json
import time
import subprocess

from config import get_db, is_already_checked, save_package
from extractor import detect_manifest_type
from registry_checker import check_package
from notifier import notify_claimable


def _run_gh(args, timeout=30):
    """Run a gh CLI command and return (success, output)."""
    try:
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except FileNotFoundError:
        return False, "gh CLI not found"
    except subprocess.TimeoutExpired:
        return False, "gh command timed out"


def _search_github_code(query, per_page=100):
    """Search GitHub code using gh CLI. Returns list of file info dicts."""
    results = []
    page = 1

    while True:
        success, output = _run_gh([
            "api", "search/code",
            "-X", "GET",
            "-f", f"q={query}",
            "-f", f"per_page={per_page}",
            "-f", f"page={str(page)}",
        ], timeout=60)

        if not success:
            break

        try:
            data = json.loads(output)
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                results.append({
                    "name": item.get("name", ""),
                    "path": item.get("path", ""),
                    "repo": item.get("repository", {}).get("full_name", ""),
                    "html_url": item.get("html_url", ""),
                    "url": item.get("url", ""),
                })

            # GitHub API rate limit — respect it
            if len(items) < per_page:
                break
            page += 1
            time.sleep(2)  # Rate limit buffer

        except json.JSONDecodeError:
            break

    return results


def _fetch_raw_content(repo, path):
    """Fetch raw file content from GitHub."""
    success, output = _run_gh([
        "api", f"repos/{repo}/contents/{path}",
        "-H", "Accept: application/vnd.github.raw",
    ], timeout=30)

    if success:
        return output
    return None


def _search_org_repos(org_name):
    """List all repos in a GitHub organization."""
    repos = []
    page = 1

    while True:
        success, output = _run_gh([
            "api", f"orgs/{org_name}/repos",
            "-f", f"per_page=100",
            "-f", f"page={str(page)}",
            "-f", "type=all",
        ], timeout=60)

        if not success:
            break

        try:
            items = json.loads(output)
            if not items:
                break

            for repo in items:
                repos.append(repo.get("full_name", ""))

            if len(items) < 100:
                break
            page += 1
            time.sleep(1)

        except json.JSONDecodeError:
            break

    return repos


def _process_manifest(content, filename, source_url, db, use_notify, output_file):
    """Process a manifest file: extract packages, check registry, notify if claimable."""
    findings = []

    ecosystem, extractor = detect_manifest_type(filename, content)
    if not extractor:
        return findings

    packages = extractor(content)
    if not packages:
        return findings

    print(f"    [+] Extracted {len(packages)} candidate packages from {filename}")

    for pkg_name in packages:
        eco = ecosystem or "npm"

        if is_already_checked(db, pkg_name, eco):
            continue

        result = check_package(pkg_name, eco)

        if result is True:
            print(f"    [!!] CLAIMABLE: {eco}:{pkg_name} (from {source_url})")
            save_package(db, pkg_name, eco, "claimable", source_url)
            notify_claimable(pkg_name, eco, source_url, use_notify)
            findings.append({
                "package": pkg_name,
                "ecosystem": eco,
                "source": source_url,
                "status": "claimable"
            })

            if output_file:
                with open(output_file, "a") as f:
                    f.write(f"[CLAIMABLE] {eco}:{pkg_name} | {source_url}\n")

        elif result is False:
            save_package(db, pkg_name, eco, "exists", source_url)

    return findings


# ── Manifest filenames to search for on GitHub ──────────────────────────

MANIFEST_FILENAMES = [
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "requirements.txt",
    "setup.py",
    "Pipfile",
    "pyproject.toml",
    "Gemfile",
    "Gemfile.lock",
]


def run_github_scanner(org_name, domain_list_file=None, use_notify=True, output_file=None):
    """Run GitHub scanning mode.

    Args:
        org_name: GitHub organization name
        domain_list_file: Optional path to domain list for cross-referencing
        use_notify: Whether to send Telegram notifications
        output_file: Path to output file for results
    """
    print(f"[*] GitHub Scanning Mode: org={org_name}")

    # Check gh auth
    success, output = _run_gh(["auth", "status"])
    if not success:
        print("[!] GitHub CLI not authenticated. Run: gh auth login")
        return

    db = get_db()
    all_findings = []

    if output_file:
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

    # Load domains for cross-reference search
    domains = []
    if domain_list_file and os.path.isfile(domain_list_file):
        with open(domain_list_file, "r") as f:
            domains = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # Strategy 1: Search by org name for each manifest type
    print(f"\n  [*] Searching org '{org_name}' for manifest files...")
    for manifest in MANIFEST_FILENAMES:
        query = f"org:{org_name} filename:{manifest}"
        print(f"  [*] Searching: {query}")
        results = _search_github_code(query)

        if results:
            print(f"  [+] Found {len(results)} {manifest} files in {org_name}")

        for item in results:
            repo = item["repo"]
            path = item["path"]
            source_url = item.get("html_url", f"https://github.com/{repo}/blob/main/{path}")

            print(f"    [*] Fetching: {repo}/{path}")
            content = _fetch_raw_content(repo, path)

            if content:
                findings = _process_manifest(content, item["name"], source_url, db, use_notify, output_file)
                all_findings.extend(findings)

            time.sleep(1)  # Rate limit

    # Strategy 2: Search by domain names
    if domains:
        print(f"\n  [*] Searching GitHub by domain names...")
        for domain in domains:
            # Search for domain references in manifest files
            for manifest in MANIFEST_FILENAMES:
                query = f'"{domain}" filename:{manifest}'
                results = _search_github_code(query)

                if results:
                    print(f"  [+] Found {len(results)} results for '{domain}' in {manifest}")

                for item in results:
                    repo = item["repo"]
                    path = item["path"]
                    source_url = item.get("html_url", f"https://github.com/{repo}/blob/main/{path}")

                    content = _fetch_raw_content(repo, path)
                    if content:
                        findings = _process_manifest(content, item["name"], source_url, db, use_notify, output_file)
                        all_findings.extend(findings)

                    time.sleep(1)

    # Strategy 3: List all repos and check root manifest files
    print(f"\n  [*] Listing repos in {org_name}...")
    repos = _search_org_repos(org_name)
    print(f"  [+] Found {len(repos)} repos")

    for repo in repos:
        for manifest in MANIFEST_FILENAMES:
            content = _fetch_raw_content(repo, manifest)
            if content:
                source_url = f"https://github.com/{repo}/blob/main/{manifest}"
                print(f"  [+] Found {manifest} in {repo}")
                findings = _process_manifest(content, manifest, source_url, db, use_notify, output_file)
                all_findings.extend(findings)

            time.sleep(0.5)

    # Summary
    claimable = [f for f in all_findings if f["status"] == "claimable"]
    print(f"\n[*] GitHub Scanning Complete")
    print(f"    Org: {org_name}")
    print(f"    Repos scanned: {len(repos)}")
    print(f"    Claimable packages found: {len(claimable)}")

    db.close()
    return all_findings
