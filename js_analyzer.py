import os
import shutil
import tempfile
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import get_db, is_already_checked, is_already_analyzed, mark_analyzed, save_package, WORKERS
from filters import should_skip_js_url
from extractor import extract_from_js
from registry_checker import check_package
from notifier import notify_claimable

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
})

# Lock for writing to shared files
_file_lock = threading.Lock()


def _download_js(url, tmp_dir):
    """Download a JS file to temp directory. Returns filepath or None."""
    try:
        resp = SESSION.get(url, timeout=30, stream=True, verify=False)
        if resp.status_code != 200:
            return None

        content_type = resp.headers.get("Content-Type", "")
        # Accept JS content or generic octet-stream
        if "javascript" not in content_type and "text/" not in content_type and "octet-stream" not in content_type and "application/json" not in content_type:
            # Some servers don't set proper content-type, still try
            pass

        # Save to temp file
        filename = url.split("/")[-1].split("?")[0][:100] or "download.js"
        filepath = os.path.join(tmp_dir, filename)

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        return filepath

    except requests.RequestException:
        return None


def _save_found_packages(packages, url, packages_file):
    """Save found packages to packages/js_found.txt immediately."""
    if not packages:
        return
    with _file_lock:
        with open(packages_file, "a") as f:
            for pkg_name, version in packages.items():
                ver_str = f" | {version}" if version else ""
                f.write(f"{pkg_name}{ver_str} | {url}\n")


def _analyze_single_js(url, use_notify, output_file, packages_file):
    """Analyze a single JS file: download, extract, check, notify."""
    db = get_db()

    # Skip if already analyzed
    if is_already_analyzed(db, url):
        db.close()
        return []

    # Skip CDN/third-party by URL only
    if should_skip_js_url(url):
        mark_analyzed(db, url)
        db.close()
        return []

    findings = []
    tmp_dir = tempfile.mkdtemp(prefix="deps_js_")

    try:
        # Determine if URL or local path
        if url.startswith("http://") or url.startswith("https://"):
            filepath = _download_js(url, tmp_dir)
            if not filepath:
                print(f"  [-] Failed to download: {url}")
                return []
        else:
            if not os.path.isfile(url):
                print(f"  [-] File not found: {url}")
                return []
            filepath = url

        # Read content
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        if not content or len(content) < 50:
            mark_analyzed(db, url)
            return []

        # No signal-based skipping — scan ALL non-CDN files

        # Extract package names (returns dict: {name: version})
        packages = extract_from_js(content)

        if not packages:
            mark_analyzed(db, url)
            return []

        print(f"  [+] Found {len(packages)} candidate packages in: {url}")

        # Save all found packages to file immediately
        _save_found_packages(packages, url, packages_file)

        # Check each package against registry
        for pkg_name, version in packages.items():
            if is_already_checked(db, pkg_name, "npm"):
                continue

            result = check_package(pkg_name, "npm")

            if result is True:
                # CLAIMABLE — save and notify, no auto-claim
                ver_str = f"@{version}" if version else ""
                print(f"  [!!] CLAIMABLE: {pkg_name}{ver_str} (source: {url})")
                save_package(db, pkg_name, "npm", "claimable", url)
                notify_claimable(pkg_name, "npm", url, use_notify)
                findings.append({
                    "package": pkg_name,
                    "version": version,
                    "ecosystem": "npm",
                    "source": url,
                    "status": "claimable"
                })

                # Write to output file immediately
                if output_file:
                    with _file_lock:
                        with open(output_file, "a") as f:
                            f.write(f"[CLAIMABLE] npm:{pkg_name}{ver_str} | {url}\n")

            elif result is False:
                save_package(db, pkg_name, "npm", "exists", url)
            else:
                print(f"  [?] Error checking {pkg_name}, will retry later")

        mark_analyzed(db, url)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        db.close()

    return findings


def run_js_analysis(js_list_file, use_notify=True, output_file=None):
    """Run JS analysis mode.

    Args:
        js_list_file: Path to file containing JS URLs/paths (one per line)
        use_notify: Whether to send Telegram notifications
        output_file: Path to output file for results
    """
    if not os.path.isfile(js_list_file):
        print(f"[!] JS list file not found: {js_list_file}")
        return

    # Read JS URLs/paths
    with open(js_list_file, "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print("[!] No JS URLs/paths found in file")
        return

    print(f"[*] JS Analysis Mode: {len(urls)} files to analyze")

    all_findings = []

    if output_file:
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else ".", exist_ok=True)

    packages_file = os.path.join("packages", "js_found.txt")
    os.makedirs("packages", exist_ok=True)

    # Each worker opens its own DB connection — no shared state
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        future_to_url = {
            executor.submit(_analyze_single_js, url, use_notify, output_file, packages_file): url
            for url in urls
        }
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                findings = future.result()
                all_findings.extend(findings)
            except Exception as e:
                print(f"  [!] Error processing {url}: {e}")

    claimable = [f for f in all_findings if f["status"] == "claimable"]
    print(f"\n[*] JS Analysis Complete")
    print(f"    Files analyzed: {len(urls)}")
    print(f"    Packages found: see {packages_file}")
    print(f"    Claimable packages: {len(claimable)}")

    return all_findings
