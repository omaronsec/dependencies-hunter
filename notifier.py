import subprocess
import requests
from config import USE_NOTIFY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram_direct(message):
    """Send message via Telegram Bot API directly."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[!] Telegram not configured. Message: {message}")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }, timeout=10)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def send_notify(message):
    """Send message via ProjectDiscovery notify tool."""
    try:
        result = subprocess.run(
            ["notify", "-silent", "-bulk"],
            input=message,
            capture_output=True,
            text=True,
            timeout=15
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def notify(message, use_notify_flag=True):
    """Send notification.

    If -notify flag is set and USE_NOTIFY is true, use notify tool.
    Otherwise fall back to direct Telegram API.
    """
    if not use_notify_flag:
        return False

    if USE_NOTIFY:
        success = send_notify(message)
        if success:
            return True
        # Fall back to direct Telegram
        return send_telegram_direct(message)
    else:
        return send_telegram_direct(message)


def notify_claimable(package_name, ecosystem, source, use_notify_flag=True):
    """Send notification about a claimable package found."""
    registry_urls = {
        "npm": f"https://www.npmjs.com/package/{package_name}",
        "pypi": f"https://pypi.org/project/{package_name}/",
        "rubygems": f"https://rubygems.org/gems/{package_name}",
    }
    registry_url = registry_urls.get(ecosystem, "")

    msg = (
        f"[CLAIMABLE] {ecosystem}: {package_name}\n"
        f"Source: {source}\n"
        f"Registry: {registry_url}"
    )
    notify(msg, use_notify_flag)


def notify_claimed(package_name, ecosystem, source, use_notify_flag=True):
    """Send notification about a successfully claimed package."""
    registry_urls = {
        "npm": f"https://www.npmjs.com/package/{package_name}",
        "pypi": f"https://pypi.org/project/{package_name}/",
        "rubygems": f"https://rubygems.org/gems/{package_name}",
    }
    registry_url = registry_urls.get(ecosystem, "")

    msg = (
        f"[CLAIMED] {ecosystem}: {package_name}\n"
        f"Source: {source}\n"
        f"Check: {registry_url}"
    )
    notify(msg, use_notify_flag)


def notify_manifest_found(domain, manifest_url, pkg_count, use_notify_flag=True):
    """Send notification when a manifest file is found."""
    msg = (
        f"[MANIFEST FOUND] {domain}\n"
        f"URL: {manifest_url}\n"
        f"Packages extracted: {pkg_count}"
    )
    notify(msg, use_notify_flag)


def notify_claimed_failed(package_name, ecosystem, reason, source="", use_notify_flag=True):
    """Send notification about a failed claim attempt."""
    msg = (
        f"[CLAIM-FAILED] {ecosystem}: {package_name}\n"
        f"Source: {source}\n"
        f"Reason: {reason}"
    )
    notify(msg, use_notify_flag)
