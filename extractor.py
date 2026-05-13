import re
import json
import sys
from filters import is_known_package, CSS_PROPERTIES

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

# Pattern 1: Dependency entry (ONLY used inside parsed dep blocks, never blind)
RE_DEP_ENTRY = re.compile(
    r'''"(@[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+|[a-zA-Z0-9][a-zA-Z0-9._-]*)"\s*:\s*"([\^~>=<*|]?\s*\d+\.\d+[\d.]*)'''
)

# Pattern 2: Python requirements.txt format
RE_PYTHON_REQ = re.compile(
    r'^([a-zA-Z0-9][a-zA-Z0-9._-]*)\s*(?:[=!<>~]=|[<>])', re.MULTILINE
)

# Pattern 9: Gemfile gem declarations
RE_RUBY_GEM = re.compile(
    r'''gem\s+['"]([a-zA-Z0-9][a-zA-Z0-9._-]*)['"]'''
)

# Pattern 10: setup.py install_requires
RE_SETUP_PY = re.compile(
    r'''['"]([a-zA-Z0-9][a-zA-Z0-9._-]*)(?:[=!<>~]=.*?)?['"]'''
)

# Pattern 11: pyproject.toml dependencies
RE_PYPROJECT = re.compile(
    r'''['"]([a-zA-Z0-9][a-zA-Z0-9._-]*)(?:\s*[=!<>~]=.*?)?['"]'''
)

# ── Embedded dependency block keywords (for JS files) ────────────────────
# When we find these keywords in JS content, we extract the JSON block after
# them and parse it to get package names + versions.

JS_DEP_BLOCK_KEYS = [
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
    "bundleDependencies",
    "bundledDependencies",
]

# ── Manifest dependency block keywords ───────────────────────────────────

DEP_BLOCK_KEYWORDS = [
    '"dependencies"', "'dependencies'",
    '"devDependencies"', "'devDependencies'",
    '"peerDependencies"', "'peerDependencies'",
    '"optionalDependencies"', "'optionalDependencies'",
    '"bundleDependencies"', "'bundleDependencies'",
    '"bundledDependencies"', "'bundledDependencies'",
    "install_requires",
    "setup_requires",
    "tests_require",
    "extras_require",
]


def _clean_package_name(raw_name):
    """Clean a raw extracted string into a valid package name.

    Returns the cleaned name or None if invalid.
    """
    if not raw_name:
        return None

    name = raw_name.strip()

    # Strip quotes
    name = name.strip("'\"")

    # Strip trailing colons, commas, semicolons
    name = name.rstrip(":,;")

    # Strip version suffixes (e.g., @^1.2.3, @latest, @1.0.0)
    # But preserve scoped names like @scope/pkg
    if name.startswith("@") and "/" in name:
        # Scoped package: @scope/pkg@version → @scope/pkg
        scope_and_name = name.split("/", 1)
        if "@" in scope_and_name[1]:
            scope_and_name[1] = scope_and_name[1].split("@")[0]
        name = "/".join(scope_and_name)
    elif "@" in name and not name.startswith("@"):
        # Unscoped with version: pkg@1.0.0 → pkg
        name = name.split("@")[0]

    # Strip trailing path segments: pkg/dist/index.js → pkg
    # For scoped: @scope/pkg/dist/index.js → @scope/pkg
    if name.startswith("@") and "/" in name:
        parts = name.split("/")
        if len(parts) > 2:
            name = parts[0] + "/" + parts[1]
    elif "/" in name:
        name = name.split("/")[0]

    # Strip any remaining whitespace
    name = name.strip()

    # Validate: must not be empty
    if not name:
        return None

    # Validate: minimum length
    if len(name) < 2 and not name.startswith("@"):
        return None

    # Validate: max length (npm limit is 214)
    if len(name) > 214:
        return None

    # Validate: must not start with . or _
    if name.startswith(".") or name.startswith("_"):
        return None

    # Validate: no spaces
    if " " in name:
        return None

    # Validate: only allowed characters
    # npm: lowercase, numbers, hyphens, dots, underscores, @, /
    if not re.match(r'^(@[a-zA-Z0-9._-]+/)?[a-zA-Z0-9._-]+$', name):
        return None

    # Convert to lowercase (npm packages are always lowercase)
    name = name.lower()

    # Block obvious non-packages
    # Filenames with extensions (popper.553719d0.js)
    if name.endswith(".js") or name.endswith(".ts") or name.endswith(".css") or name.endswith(".json") or name.endswith(".html"):
        return None
    # Literal directory name
    if name == "node_modules":
        return None

    return name


def _extract_json_block(content, start_pos):
    """Extract a JSON object {...} or array [...] starting from start_pos.

    Returns the parsed object/list or None.
    """
    # Find the opening brace/bracket after the key
    i = start_pos
    while i < len(content) and content[i] in ' \t\n\r:':
        i += 1

    if i >= len(content):
        return None

    opener = content[i]
    if opener == '{':
        closer = '}'
    elif opener == '[':
        closer = ']'
    else:
        return None

    # Track nesting to find the matching closer
    depth = 0
    j = i
    while j < len(content):
        ch = content[j]
        if ch == '"':
            # Skip string content
            j += 1
            while j < len(content) and content[j] != '"':
                if content[j] == '\\':
                    j += 1  # skip escaped char
                j += 1
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                block = content[i:j + 1]
                try:
                    return json.loads(block)
                except (json.JSONDecodeError, ValueError):
                    return None
        j += 1

    return None


def _parse_npm_alias(value):
    """Extract real package name from npm alias value like 'npm:real-pkg@^1.0.0'.

    Returns cleaned package name or None.
    """
    raw = value[4:]  # strip "npm:"
    if raw.startswith("@") and "/" in raw:
        # scoped: @scope/pkg@version → @scope/pkg
        match = re.match(r'^(@[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+)', raw)
    else:
        # unscoped: pkg@version → pkg
        match = re.match(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*)', raw)
    if match:
        return _clean_package_name(match.group(1))
    return None


# Value prefixes that mean the package is local/git — not on any public registry
_LOCAL_PROTOCOLS = (
    "link:",
    "file:",
    "workspace:",
    "git+",
    "git://",
    "github:",
    "bitbucket:",
    "gitlab:",
    "https://",
    "http://",
)

# Valid npm dist-tags (exact string values that are not version numbers)
_VALID_TAGS = {"latest", "next", "stable", "beta", "alpha", "rc", "canary", "experimental"}


def _is_valid_version(v):
    """Return True if v looks like a real registry version or dist-tag."""
    if not v:
        return False
    # Version range: starts with ^ ~ >= <= > < = * | or a digit
    if re.match(r'^[\^~>=<*|0-9]', v):
        return True
    # Known dist-tags
    if v in _VALID_TAGS:
        return True
    return False


def _extract_dep_blocks(content):
    """Find dependency blocks in JS/JSON content and extract real package names.

    Only trusts packages where the value is a valid registry version string or
    dist-tag. Skips local (link:/file:/workspace:), git, and URL references.
    Handles npm: aliases by extracting the real package name from the value.

    Returns dict of {package_name: version_string}.
    """
    packages = {}

    for key in JS_DEP_BLOCK_KEYS:
        for quote in ['"', "'"]:
            pattern = f'{quote}{key}{quote}'
            search_start = 0
            while True:
                pos = content.find(pattern, search_start)
                if pos == -1:
                    break

                after_key = pos + len(pattern)
                parsed = _extract_json_block(content, after_key)

                if isinstance(parsed, dict):
                    for pkg_name, version in parsed.items():
                        if not isinstance(version, str):
                            continue

                        v = version.strip()

                        # npm alias: value is "npm:real-pkg@version"
                        # the KEY is just a local alias name — check the REAL package instead
                        if v.startswith("npm:"):
                            real = _parse_npm_alias(v)
                            if real and real not in packages:
                                packages[real] = v
                            continue

                        # local/git references — not on public registry, skip
                        if any(v.startswith(proto) for proto in _LOCAL_PROTOCOLS):
                            continue

                        # must be a valid version string or dist-tag
                        if not _is_valid_version(v):
                            continue

                        cleaned = _clean_package_name(pkg_name)
                        if cleaned:
                            packages[cleaned] = version

                elif isinstance(parsed, list):
                    # bundledDependencies is an array of package name strings (no versions)
                    for item in parsed:
                        if isinstance(item, str):
                            cleaned = _clean_package_name(item)
                            if cleaned:
                                packages[cleaned] = ""

                search_start = after_key

    return packages


def extract_from_js(content):
    """Extract package names from JavaScript file content.

    Only trusts embedded dependency blocks (dependencies, devDependencies,
    peerDependencies, optionalDependencies, bundledDependencies) parsed as
    JSON with a valid version string value. Everything else (node_modules
    paths, require(), import from) is noise and ignored.

    Returns a dict of {package_name: version_string}.
    """
    packages = _extract_dep_blocks(content)

    filtered = {}
    for name, version in packages.items():
        if not is_known_package(name) and name not in CSS_PROPERTIES:
            filtered[name] = version

    return filtered


def extract_from_package_json(content):
    """Extract package names from a real package.json file.

    Uses the same dep block extraction as JS mode — same rules,
    same version validation, same npm: alias handling, same local
    protocol skipping. Fallback to RE_DEP_ENTRY regex if JSON is broken.

    Returns a dict of {package_name: version_string}.
    """
    packages = _extract_dep_blocks(content)

    # Fallback for malformed JSON that _extract_dep_blocks couldn't parse
    if not packages:
        for match in RE_DEP_ENTRY.finditer(content):
            name = _clean_package_name(match.group(1))
            version = match.group(2) if match.lastindex >= 2 else ""
            if name:
                packages[name] = version

    filtered = {}
    for name, version in packages.items():
        if not is_known_package(name) and name not in CSS_PROPERTIES:
            filtered[name] = version

    return filtered


def extract_from_requirements_txt(content):
    """Extract package names from requirements.txt content.

    Returns a dict of {package_name: version_string}.
    """
    packages = {}

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue

        match = RE_PYTHON_REQ.match(line)
        if match:
            name = match.group(1).strip().lower()
            # Extract version from the line
            ver_match = re.search(r'[=!<>~]=\s*([\d][\d.]*)', line)
            version = ver_match.group(1) if ver_match else ""
            if name and not is_known_package(name):
                packages[name] = version
        else:
            if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9._-]*$', line):
                name = line.strip().lower()
                if name and not is_known_package(name):
                    packages[name] = ""

    return packages


def extract_from_gemfile(content):
    """Extract gem names from Gemfile content.

    Returns a dict of {gem_name: version_string}.
    """
    packages = {}
    # Match gem "name", "~> 1.0"
    re_gem_ver = re.compile(
        r'''gem\s+['"]([a-zA-Z0-9][a-zA-Z0-9._-]*)['"](?:\s*,\s*['"]([~>=<!\s\d.]+)['"])?'''
    )

    for match in re_gem_ver.finditer(content):
        name = match.group(1).strip().lower()
        version = match.group(2).strip() if match.group(2) else ""
        if name and not is_known_package(name):
            packages[name] = version

    return packages


def extract_from_setup_py(content):
    """Extract package names from setup.py content.

    Returns a dict of {package_name: version_string}.
    """
    packages = {}

    for key in ["install_requires", "setup_requires", "tests_require"]:
        req_match = re.search(
            rf'{key}\s*=\s*\[(.*?)\]', content, re.DOTALL
        )
        if req_match:
            block = req_match.group(1)
            for match in RE_SETUP_PY.finditer(block):
                name = match.group(1).strip().lower()
                # Try to get version from full match
                full = match.group(0)
                ver_match = re.search(r'[=!<>~]=\s*([\d][\d.]*)', full)
                version = ver_match.group(1) if ver_match else ""
                if name and not is_known_package(name):
                    packages[name] = version

    return packages


def extract_from_pipfile(content):
    """Extract package names from Pipfile content.

    Returns a dict of {package_name: version_string}.
    """
    packages = {}

    if tomllib:
        try:
            data = tomllib.loads(content)
            for section in ("packages", "dev-packages"):
                section_data = data.get(section, {})
                if not isinstance(section_data, dict):
                    continue
                for name, spec in section_data.items():
                    name = name.strip().lower()
                    if isinstance(spec, str):
                        version = "" if spec == "*" else spec
                    elif isinstance(spec, dict):
                        version = spec.get("version", "")
                        if version == "*":
                            version = ""
                    else:
                        version = ""
                    if name and re.match(r'^[a-zA-Z0-9._-]+$', name):
                        if not is_known_package(name):
                            packages[name] = version
            return packages
        except Exception:
            pass

    # Fallback for when tomllib is unavailable
    in_packages_section = False
    for line in content.splitlines():
        line = line.strip()
        if line in ("[packages]", "[dev-packages]"):
            in_packages_section = True
            continue
        elif line.startswith("["):
            in_packages_section = False
            continue
        if in_packages_section and "=" in line:
            parts = line.split("=", 1)
            name = parts[0].strip().strip('"').strip("'").lower()
            version = parts[1].strip().strip('"').strip("'") if len(parts) > 1 else ""
            if version == "*":
                version = ""
            if name and re.match(r'^[a-zA-Z0-9._-]+$', name):
                if not is_known_package(name):
                    packages[name] = version

    return packages


def _parse_pep508(dep):
    """Parse a PEP 508 dependency string like 'requests>=2.0' into (name, version)."""
    match = re.match(r'^([a-zA-Z0-9][a-zA-Z0-9._-]*)', dep.strip())
    if not match:
        return None, None
    name = match.group(1).strip().lower()
    ver_match = re.search(r'[>=<~!]=?\s*([\d][\d.]*)', dep)
    version = ver_match.group(1) if ver_match else ""
    return name, version


def extract_from_pyproject_toml(content):
    """Extract package names from pyproject.toml content.

    Supports PEP 621 ([project] dependencies) and Poetry
    ([tool.poetry.dependencies], [tool.poetry.dev-dependencies]).

    Returns a dict of {package_name: version_string}.
    """
    packages = {}

    if tomllib:
        try:
            data = tomllib.loads(content)

            # PEP 621: [project] dependencies (list of PEP 508 strings)
            project = data.get("project", {})
            for dep in project.get("dependencies", []):
                if isinstance(dep, str):
                    name, version = _parse_pep508(dep)
                    if name and not is_known_package(name):
                        packages[name] = version

            # PEP 621: [project.optional-dependencies] (dict of lists)
            for group_deps in project.get("optional-dependencies", {}).values():
                for dep in group_deps:
                    if isinstance(dep, str):
                        name, version = _parse_pep508(dep)
                        if name and not is_known_package(name):
                            packages[name] = version

            # Poetry: [tool.poetry.dependencies] / [tool.poetry.dev-dependencies]
            poetry = data.get("tool", {}).get("poetry", {})
            for section in ("dependencies", "dev-dependencies"):
                for pkg_name, spec in poetry.get(section, {}).items():
                    if pkg_name.lower() == "python":
                        continue
                    pkg_name = pkg_name.strip().lower()
                    if isinstance(spec, str):
                        version = "" if spec in ("*", "") else spec
                    elif isinstance(spec, dict):
                        version = spec.get("version", "")
                        if version == "*":
                            version = ""
                    else:
                        version = ""
                    if pkg_name and not is_known_package(pkg_name):
                        packages[pkg_name] = version

            return packages
        except Exception:
            pass

    # Fallback for when tomllib is unavailable
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("[project.dependencies]", "[project.optional-dependencies]"):
            in_deps = True
            continue
        elif stripped.startswith("["):
            in_deps = False
            continue
        if in_deps and stripped and not stripped.startswith("#"):
            name, version = _parse_pep508(stripped.strip('"').strip("'"))
            if name and not is_known_package(name):
                packages[name] = version

    return packages


def extract_from_yarn_lock(content):
    """Extract package names from yarn.lock content.

    Returns a dict of {package_name: version_string}.
    """
    packages = {}

    for match in re.finditer(
        r'^"?(@[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+|[a-zA-Z0-9._-]+)@([^\s:]+)',
        content,
        re.MULTILINE
    ):
        name = _clean_package_name(match.group(1))
        version = match.group(2).strip('"').strip("'") if match.group(2) else ""
        if name and not is_known_package(name):
            packages[name] = version

    return packages


def extract_from_package_lock_json(content):
    """Extract package names from package-lock.json content.

    Returns a dict of {package_name: version_string}.
    """
    return extract_from_package_json(content)


def detect_manifest_type(filename, content=""):
    """Detect the type of manifest file and return the appropriate extractor.

    Returns (ecosystem, extractor_function) or (None, None) if unknown.
    """
    filename_lower = filename.lower()

    if filename_lower.endswith("package.json"):
        return "npm", extract_from_package_json
    elif filename_lower.endswith("package-lock.json"):
        return "npm", extract_from_package_lock_json
    elif filename_lower.endswith("yarn.lock"):
        return "npm", extract_from_yarn_lock
    elif filename_lower.endswith("requirements.txt") or filename_lower.endswith("-requirements.txt"):
        return "pypi", extract_from_requirements_txt
    elif filename_lower.endswith("setup.py"):
        return "pypi", extract_from_setup_py
    elif filename_lower.endswith("pipfile"):
        return "pypi", extract_from_pipfile
    elif filename_lower.endswith("pipfile.lock"):
        return "pypi", extract_from_pipfile
    elif filename_lower.endswith("pyproject.toml"):
        return "pypi", extract_from_pyproject_toml
    elif filename_lower.endswith("gemfile") or filename_lower == ".gemfile":
        return "rubygems", extract_from_gemfile
    elif filename_lower.endswith("gemfile.lock"):
        return "rubygems", extract_from_gemfile
    elif filename_lower.endswith(".gemspec"):
        return "rubygems", extract_from_gemfile

    return None, None


def detect_ecosystem_from_js(packages):
    """All packages from JS files are assumed npm/yarn ecosystem."""
    return "npm"
