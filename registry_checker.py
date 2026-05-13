import time
import threading
import requests
from config import REGISTRY_DELAY

# Suppress SSL warnings for edge cases
requests.packages.urllib3.disable_warnings()

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; security-research)",
    "Accept": "application/json",
})

# Cache for npm org ownership checks (org_name -> bool)
# True = org is OWNED (can't publish), False = org is FREE (can claim)
_org_cache = {}
_org_cache_lock = threading.Lock()


def check_npm(package_name):
    """Check if an npm package exists.

    Returns True if claimable (404), False if exists.
    Returns None on error (network issue, rate limit, etc.).
    """
    try:
        # Handle scoped packages: @scope/pkg → @scope%2fpkg
        encoded = package_name.replace("/", "%2f")
        url = f"https://registry.npmjs.org/{encoded}"
        resp = SESSION.get(url, timeout=10, allow_redirects=True)
        time.sleep(REGISTRY_DELAY)

        if resp.status_code == 404:
            return True  # Claimable
        elif resp.status_code == 200:
            return False  # Exists
        else:
            return None  # Unknown / error
    except requests.RequestException:
        return None


def check_npm_org(org_name):
    """Check if an npm organization/scope exists.

    Returns True if org is unclaimed (404), False if exists (200), None on error.
    """
    try:
        url = f"https://registry.npmjs.org/-/org/{org_name}/package"
        resp = SESSION.get(url, timeout=10)
        time.sleep(REGISTRY_DELAY)

        if resp.status_code == 404:
            return True  # Org unclaimed
        elif resp.status_code == 200:
            return False  # Org exists
        else:
            return None
    except requests.RequestException:
        return None


def check_npm_user(username):
    """Check if an npm user account exists (owns the @username scope).

    Returns True if user is unclaimed (404), False if exists (200), None on error.
    """
    try:
        url = f"https://registry.npmjs.org/-/user/org.couchdb.user:{username}"
        resp = SESSION.get(url, timeout=10)
        time.sleep(REGISTRY_DELAY)

        if resp.status_code == 404:
            return True  # User doesn't exist — scope is free
        elif resp.status_code == 200:
            return False  # User exists — owns @username scope
        else:
            return None
    except requests.RequestException:
        return None


def check_pypi(package_name):
    """Check if a PyPI package exists.

    Returns True if claimable (404), False if exists, None on error.
    """
    try:
        url = f"https://pypi.org/pypi/{package_name}/json"
        resp = SESSION.get(url, timeout=10)
        time.sleep(REGISTRY_DELAY)

        if resp.status_code == 404:
            return True
        elif resp.status_code == 200:
            return False
        else:
            return None
    except requests.RequestException:
        return None


def check_rubygems(gem_name):
    """Check if a RubyGem exists.

    Returns True if claimable (404), False if exists, None on error.
    """
    try:
        url = f"https://rubygems.org/api/v1/gems/{gem_name}.json"
        resp = SESSION.get(url, timeout=10)
        time.sleep(REGISTRY_DELAY)

        if resp.status_code == 404:
            return True
        elif resp.status_code == 200:
            return False
        else:
            return None
    except requests.RequestException:
        return None


def _is_scope_owned(scope_name):
    """Check if an npm scope is owned by anyone (org OR user).

    Checks org endpoint first, then user endpoint.
    Returns True if scope is owned (can't publish under it).
    Returns False if scope is completely free (both org and user unclaimed).
    Returns None on error.
    """
    with _org_cache_lock:
        if scope_name in _org_cache:
            return _org_cache[scope_name]

    # Step 1: is it a registered org?
    org_result = check_npm_org(scope_name)
    if org_result is False:
        # Org exists — owned
        with _org_cache_lock:
            _org_cache[scope_name] = True
        return True
    if org_result is None:
        return None  # network error, don't cache

    # Step 2: is it a registered user account?
    user_result = check_npm_user(scope_name)
    if user_result is False:
        # User exists — owns this scope
        with _org_cache_lock:
            _org_cache[scope_name] = True
        return True
    if user_result is None:
        return None  # network error, don't cache

    # Both 404 — scope is completely unclaimed
    with _org_cache_lock:
        _org_cache[scope_name] = False
    return False


def check_package(name, ecosystem):
    """Check if a package is claimable on the given ecosystem.

    Args:
        name: Package name
        ecosystem: One of 'npm', 'pypi', 'rubygems'

    Returns True if claimable, False if exists/not-claimable, None on error.
    """
    checkers = {
        "npm": check_npm,
        "pypi": check_pypi,
        "rubygems": check_rubygems,
    }

    checker = checkers.get(ecosystem)
    if not checker:
        return None

    # For scoped npm packages, check if scope is owned (org OR user) first.
    # If anyone owns @scope, you can't publish under it — not claimable.
    if ecosystem == "npm" and name.startswith("@") and "/" in name:
        scope_name = name.split("/")[0].lstrip("@")
        scope_owned = _is_scope_owned(scope_name)
        if scope_owned is True:
            # Scope owned by org or user — not claimable
            return False
        elif scope_owned is False:
            # Scope completely unclaimed — whole scope is a finding
            return True
        # scope_owned is None (error) — fall through to check the package itself

    result = checker(name)
    return result
