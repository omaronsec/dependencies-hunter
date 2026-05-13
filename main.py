#!/usr/bin/env python3
"""
Dependencies Hunter — Dependency Confusion Scanner for Bug Bounty

Monitors bug bounty targets for claimable packages across npm, PyPI, and RubyGems.

Usage:
    python3 main.py -js /path/to/js_urls.txt [-notify] [-o output.txt]
    python3 main.py -dL domains.txt [-notify] [-o output.txt]
    python3 main.py -org orgname -dL domains.txt [-notify] [-o output.txt]
"""

import os
import sys
import shutil
import argparse
import subprocess

# Ensure we import from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BANNER = r"""
  ____                  _   _             _
 |  _ \  ___ _ __  ___ | | | |_   _ _ __ | |_ ___ _ __
 | | | |/ _ \ '_ \/ __|| |_| | | | | '_ \| __/ _ \ '__|
 | |_| |  __/ |_) \__ \|  _  | |_| | | | | ||  __/ |
 |____/ \___| .__/|___/|_| |_|\__,_|_| |_|\__\___|_|
            |_|
  Dependency Confusion Hunter — Bug Bounty Edition
"""


def check_prerequisites(modes):
    """Check that required tools are installed and authenticated."""
    issues = []

    # Always check Python deps
    try:
        import requests
        import dotenv
        import bs4
    except ImportError as e:
        issues.append(f"Missing Python dependency: {e.name}. Run: pip3 install -r requirements.txt")

    # npm login is optional — only needed for manual claiming, not scanning
    if shutil.which("npm"):
        result = subprocess.run(["npm", "whoami"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("[i] npm: Not logged in — manual claiming won't work. Run: npm login")
    else:
        print("[i] npm: Not installed — manual claiming won't work.")

    # Check gh for GitHub mode
    if "github" in modes:
        if shutil.which("gh"):
            result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                issues.append("gh: Not authenticated. Run: gh auth login")
        else:
            issues.append("gh: Not installed. Install GitHub CLI for -org mode.")

    # Check notify if requested
    if "notify" in modes:
        from config import USE_NOTIFY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        if USE_NOTIFY:
            if not shutil.which("notify"):
                if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
                    issues.append(
                        "Notification: notify tool not found and Telegram not configured.\n"
                        "  Option 1: Install notify — go install github.com/projectdiscovery/notify/cmd/notify@latest\n"
                        "  Option 2: Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env\n"
                        "  Option 3: Set USE_NOTIFY=false in .env and configure Telegram direct API"
                    )
        else:
            if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
                issues.append("Telegram: BOT_TOKEN or CHAT_ID not set in .env")

    # Optional: check twine for PyPI claiming
    if not shutil.which("twine"):
        print("[i] twine not found — PyPI claiming disabled. Install: pip3 install twine build")

    # Optional: check gem for RubyGems claiming
    if not shutil.which("gem"):
        print("[i] gem not found — RubyGems claiming disabled. Install Ruby for gem claiming.")

    return issues


def main():
    parser = argparse.ArgumentParser(
        description="Dependencies Hunter — Dependency Confusion Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py -js js_urls.txt -notify -o results.txt
  python3 main.py -dL domains.txt -notify
  python3 main.py -org microsoft -dL domains.txt -notify -o results.txt
        """
    )

    parser.add_argument("-js", metavar="FILE",
                        help="JS analysis mode: file containing JS URLs/paths (one per line)")
    parser.add_argument("-dL", metavar="FILE",
                        help="Domain fuzzing mode: file containing domains (one per line)")
    parser.add_argument("-org", metavar="NAME",
                        help="GitHub org scanning mode (requires -dL for domain cross-reference)")
    parser.add_argument("-notify", action="store_true",
                        help="Enable Telegram notifications")
    parser.add_argument("-o", metavar="FILE", default="output/results.txt",
                        help="Output file for results (default: output/results.txt)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    # Validate: at least one mode required
    if not args.js and not args.dL and not args.org:
        print(BANNER)
        parser.print_help()
        print("\n[!] At least one mode required: -js, -dL, or -org")
        sys.exit(1)

    # GitHub mode requires -dL
    if args.org and not args.dL:
        print("[!] -org requires -dL for domain list cross-reference")
        sys.exit(1)

    print(BANNER)

    # Determine active modes for prereq check
    modes = set()
    if args.js:
        modes.add("js")
    if args.dL:
        modes.add("domain")
    if args.org:
        modes.add("github")
    if args.notify:
        modes.add("notify")

    # Check prerequisites
    print("[*] Checking prerequisites...")
    issues = check_prerequisites(modes)
    if issues:
        print("\n[!] Prerequisites not met:")
        for issue in issues:
            print(f"    - {issue}")
        print("\n[!] Fix the above issues and try again.")
        sys.exit(1)
    print("[+] All prerequisites OK\n")

    # Create output directory
    if args.o:
        output_dir = os.path.dirname(args.o)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    # ── Run modes ──

    # Mode 1: JS Analysis
    if args.js:
        from js_analyzer import run_js_analysis
        run_js_analysis(args.js, use_notify=args.notify, output_file=args.o)

    # Mode 2: Domain Fuzzing (only if -org not set, otherwise github mode handles domains)
    if args.dL and not args.org:
        from domain_fuzzer import run_domain_fuzzer
        run_domain_fuzzer(args.dL, use_notify=args.notify, output_file=args.o)

    # Mode 3: GitHub Scanning (includes domain cross-reference)
    if args.org:
        from github_scanner import run_github_scanner
        run_github_scanner(args.org, args.dL, use_notify=args.notify, output_file=args.o)

    print("\n[*] Done. Results saved to:", args.o)


if __name__ == "__main__":
    main()
