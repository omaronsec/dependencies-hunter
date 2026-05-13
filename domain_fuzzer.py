import os
import re
import json
import hashlib
import random
import shutil
import tempfile
import subprocess
import threading
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

from bs4 import BeautifulSoup
from config import get_db, is_already_checked, save_package, PATTERNS_FILE, WORKERS
from extractor import detect_manifest_type
from registry_checker import check_package
from notifier import notify_claimable

BASE_MANIFESTS = [
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "requirements.txt",
    "setup.py",
    "Pipfile",
    "Pipfile.lock",
    "pyproject.toml",
    "Gemfile",
    "Gemfile.lock",
    "composer.json",
]

# Traversal encoding variants — applied per real crawled path only
TRAVERSAL_ENCODINGS = [
    "../",
    "..%2f",
    "..%252f",
    "..;/",
]

# File extensions to strip when extracting directory paths from page source
STRIP_EXTENSIONS = {
    '.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp',
    '.woff', '.woff2', '.ttf', '.eot', '.otf', '.mp4', '.mp3', '.webm',
    '.pdf', '.zip', '.gz', '.tar', '.map', '.xml', '.txt', '.html', '.htm',
    '.php', '.asp', '.aspx', '.jsp', '.json', '.bmp', '.tif', '.tiff',
}

UA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user-agent.txt")


def _load_user_agents():
    if os.path.isfile(UA_FILE):
        with open(UA_FILE, "r") as f:
            agents = [line.strip() for line in f if line.strip()]
            if agents:
                return agents
    return ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"]


USER_AGENTS = _load_user_agents()

progress_lock = threading.Lock()
progress_done = 0
progress_total = 0


def _find_ffuf():
    candidates = [
        shutil.which("ffuf"),
        os.path.expanduser("~/go/bin/ffuf"),
        "/root/go/bin/ffuf",
        "/usr/local/bin/ffuf",
        "/usr/bin/ffuf",
    ]
    for path in candidates:
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _fetch_url(url, timeout=15):
    """Fetch a URL. Returns text content on 200, None otherwise."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": random.choice(USER_AGENTS)},
            verify=False,
            allow_redirects=True,
            timeout=timeout,
        )
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return None


def _crawl_paths(domain):
    """Crawl homepage and extract real directory paths (1-3 segments)."""
    paths = set()
    for scheme in ["https", "http"]:
        try:
            resp = requests.get(
                f"{scheme}://{domain}",
                headers={"User-Agent": random.choice(USER_AGENTS)},
                verify=False,
                allow_redirects=True,
                timeout=15,
            )
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup.find_all(True):
                for attr in ["href", "src", "action", "data-src"]:
                    val = tag.get(attr, "")
                    if not val:
                        continue
                    if val.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                        continue
                    try:
                        parsed = urlparse(val)
                        path = parsed.path.strip("/")
                        if not path:
                            continue
                        segments = path.split("/")
                        last = segments[-1]
                        if "." in last:
                            ext = "." + last.rsplit(".", 1)[-1].lower()
                            if ext in STRIP_EXTENSIONS:
                                segments = segments[:-1]
                        if not segments or segments == [""]:
                            continue
                        for i in range(1, min(len(segments) + 1, 4)):
                            dir_path = "/".join(segments[:i])
                            if dir_path:
                                paths.add(dir_path)
                    except Exception:
                        continue
            break
        except requests.RequestException:
            continue
    return paths


def _generate_traversal_wordlist(paths):
    """Generate traversal combos from real crawled paths only.

    For a path with N segments, tries going 1 to N+1 levels up using
    each encoding variant. Example for path "dist/client/js" (3 segments):
      dist/client/js/../package.json        (1 level up)
      dist/client/js/../../package.json     (2 levels up)
      dist/client/js/../../../package.json  (3 levels up)
      dist/client/js/../../../../package.json (4 levels up)
    Repeated for each encoding: ../, ..%2f, ..%252f, ..;/
    """
    entries = set()
    for path in paths:
        depth = len(path.strip("/").split("/"))
        for manifest in BASE_MANIFESTS:
            for levels in range(1, depth + 2):
                for enc in TRAVERSAL_ENCODINGS:
                    traversal = enc * levels
                    entries.add(f"{path}/{traversal}{manifest}")
    return entries


def _run_ffuf(domain, wordlist):
    """Run ffuf against domain/FUZZ. Returns list of hit URLs."""
    ffuf_path = _find_ffuf()
    if not ffuf_path:
        print(f"  [!] ffuf not found — skipping traversal fuzzing for {domain}")
        return []

    tmp_wordlist = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    for entry in wordlist:
        tmp_wordlist.write(entry + "\n")
    tmp_wordlist.close()

    tmp_output = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp_output.close()

    hit_urls = []
    try:
        result = subprocess.run(
            [
                ffuf_path,
                "-u", f"https://{domain}/FUZZ",
                "-w", tmp_wordlist.name,
                "-mc", "200",
                "-ac",
                "-H", f"User-Agent: {random.choice(USER_AGENTS)}",
                "-o", tmp_output.name,
                "-of", "json",
                "-s",
                "-t", "30",
            ],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0 and result.stderr.strip():
            print(f"  [!] ffuf error on {domain}: {result.stderr.strip()[:120]}")

        with open(tmp_output.name, "r") as f:
            data = json.load(f)
            for r in data.get("results", []):
                url = r.get("url", "")
                if url:
                    hit_urls.append(url)

    except subprocess.TimeoutExpired:
        print(f"  [!] ffuf timeout on {domain}")
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    except Exception as e:
        print(f"  [!] ffuf failed on {domain}: {e}")
    finally:
        try:
            os.unlink(tmp_wordlist.name)
            os.unlink(tmp_output.name)
        except OSError:
            pass

    return hit_urls


def _is_valid_manifest_response(content, url):
    """Confirm response is actually a manifest file, not a soft-404 HTML page."""
    if not content or len(content) < 10:
        return False
    if len(content) > 5_000_000:
        return False

    content_lower = content[:500].lower()
    if "<!doctype" in content_lower or "<html" in content_lower or "<head>" in content_lower:
        return False

    url_lower = url.lower()

    if any(x in url_lower for x in ["package.json", "package-lock.json", "composer.json"]):
        return "{" in content and ("dependencies" in content or '"name"' in content)

    if "yarn.lock" in url_lower:
        return "resolved" in content and "@" in content

    if "requirements.txt" in url_lower:
        if re.search(r'^[a-zA-Z0-9].*?[=<>]', content, re.MULTILINE):
            return True
        lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("#")]
        return bool(lines) and all(re.match(r'^[a-zA-Z0-9._-]', l) for l in lines[:5])

    if "setup.py" in url_lower:
        return "setup(" in content and ("install_requires" in content or "setuptools" in content)

    if "pipfile" in url_lower:
        return "[packages]" in content or "[dev-packages]" in content

    if "pyproject.toml" in url_lower:
        return "[project]" in content and "dependencies" in content

    if "gemfile" in url_lower:
        return "gem " in content and "source " in content

    return False


def _process_hit(hit_url, content, db, use_notify, output_file):
    """Extract packages from a valid manifest, check registry, notify if claimable.

    Output format:
      Nothing claimable → [HIT] url | nothing claimable
      Has claimable     → [HIT] url
                              [CLAIMABLE] eco:pkg@version
                              [CLAIMABLE] eco:pkg2
    """
    findings = []

    filename = hit_url.split("/")[-1].split("?")[0]
    ecosystem, extractor = detect_manifest_type(filename, content)
    if not extractor:
        return findings

    packages = extractor(content)
    if not packages:
        if output_file:
            with progress_lock:
                with open(output_file, "a") as f:
                    f.write(f"[HIT] {hit_url} | nothing claimable\n")
        return findings

    print(f"  [+] {len(packages)} packages in {hit_url}")

    # Save all extracted packages to found.txt for reference
    pkg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "packages")
    os.makedirs(pkg_dir, exist_ok=True)
    with progress_lock:
        with open(os.path.join(pkg_dir, "found.txt"), "a") as f:
            for pkg_name, version in packages.items():
                ver_str = f" | {version}" if version else ""
                f.write(f"{pkg_name}{ver_str} | {hit_url}\n")

    # Check each package against registry
    claimable_lines = []
    for pkg_name, version in packages.items():
        eco = ecosystem or "npm"
        if is_already_checked(db, pkg_name, eco):
            continue

        result = check_package(pkg_name, eco)

        if result is True:
            ver_str = f"@{version}" if version else ""
            line = f"    [CLAIMABLE] {eco}:{pkg_name}{ver_str}"
            claimable_lines.append(line)
            print(f"  [!!] CLAIMABLE: {eco}:{pkg_name}{ver_str}")
            save_package(db, pkg_name, eco, "claimable", hit_url)
            notify_claimable(pkg_name, eco, hit_url, use_notify)
            findings.append({
                "package": pkg_name,
                "ecosystem": eco,
                "source": hit_url,
                "status": "claimable",
            })

        elif result is False:
            save_package(db, pkg_name, eco, "exists", hit_url)

    # Write grouped output
    if output_file:
        with progress_lock:
            with open(output_file, "a") as f:
                if claimable_lines:
                    f.write(f"[HIT] {hit_url}\n")
                    for line in claimable_lines:
                        f.write(f"{line}\n")
                else:
                    f.write(f"[HIT] {hit_url} | nothing claimable\n")

    return findings


def _fuzz_single_domain(domain, use_notify, output_file):
    """Fuzz a single domain. Stops as soon as one valid manifest is found."""
    global progress_done
    findings = []
    db = get_db()
    seen_hashes = set()

    # ── Step 1: Direct root check ───────────────────────────────────────
    # Try domain.com/package.json, domain.com/requirements.txt, etc.
    # No crawl, no ffuf — just direct GET for each manifest name.
    for manifest in BASE_MANIFESTS:
        url = f"https://{domain}/{manifest}"
        content = _fetch_url(url)
        if not content or not _is_valid_manifest_response(content, url):
            continue

        h = hashlib.md5(content.encode()).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        print(f"  [+] Direct hit: {url}")
        findings.extend(_process_hit(url, content, db, use_notify, output_file))

        # Found manifest at root — stop, no need to go further
        with progress_lock:
            progress_done += 1
            print(f"  [*] {progress_done}/{progress_total} — {domain} [direct hit, stopped]", flush=True)
        db.close()
        return findings

    # ── Step 2: Crawl homepage for real directory paths ─────────────────
    paths = _crawl_paths(domain)
    if not paths:
        with progress_lock:
            progress_done += 1
            print(f"  [*] {progress_done}/{progress_total} — {domain} [no paths found]", flush=True)
        db.close()
        return findings

    # ── Step 3: Generate traversal wordlist from real paths only ────────
    # No root traversal, no blind combos — only real paths from the page
    # combined with traversal encodings going up 1 to depth+1 levels.
    wordlist = _generate_traversal_wordlist(paths)

    # ── Step 4: Run ffuf ────────────────────────────────────────────────
    hit_urls = _run_ffuf(domain, wordlist)

    # ── Step 5: First valid unique manifest → process → stop ───────────
    # Content hash deduplication: if multiple traversal paths resolve to
    # the same file, process it once and stop.
    found_count = 0
    for hit_url in hit_urls:
        content = _fetch_url(hit_url)
        if not content or not _is_valid_manifest_response(content, hit_url):
            continue

        h = hashlib.md5(content.encode()).hexdigest()
        if h in seen_hashes:
            continue
        seen_hashes.add(h)

        findings.extend(_process_hit(hit_url, content, db, use_notify, output_file))
        found_count += 1
        break  # Stop — first valid unique manifest found

    with progress_lock:
        progress_done += 1
        print(
            f"  [*] {progress_done}/{progress_total} — {domain} "
            f"[{len(paths)} paths crawled, {len(wordlist)} fuzz entries, {found_count} manifest found]",
            flush=True,
        )

    db.close()
    return findings


def run_domain_fuzzer(domain_list_file, use_notify=True, output_file=None):
    """Run domain fuzzing mode."""
    global progress_done, progress_total

    if not os.path.isfile(domain_list_file):
        print(f"[!] Domain list file not found: {domain_list_file}")
        return

    if not _find_ffuf():
        print("[!] ffuf not found. Install: go install github.com/ffuf/ffuf/v2@latest")
        return

    with open(domain_list_file, "r") as f:
        raw = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    domains = []
    for d in raw:
        d = d.replace("https://", "").replace("http://", "").strip("/")
        if d:
            domains.append(d)

    if not domains:
        print("[!] No domains found in file")
        return

    print(f"[*] Domain Fuzzing Mode: {len(domains)} domains")

    if output_file:
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

    progress_done = 0
    progress_total = len(domains)
    all_findings = []

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        future_to_domain = {
            executor.submit(_fuzz_single_domain, domain, use_notify, output_file): domain
            for domain in domains
        }
        for future in as_completed(future_to_domain):
            domain = future_to_domain[future]
            try:
                findings = future.result()
                all_findings.extend(findings)
            except Exception as e:
                print(f"  [!] Error on {domain}: {e}")

    claimable = [f for f in all_findings if f["status"] == "claimable"]
    print(f"\n[*] Domain Fuzzing Complete")
    print(f"    Domains processed: {len(domains)}")
    print(f"    Claimable packages found: {len(claimable)}")

    return all_findings
