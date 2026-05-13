# Dependencies Hunter

Dependency confusion scanner for bug bounty. Extracts package names from JavaScript files, manifest files, and GitHub repos — then checks if they're unclaimed on public registries and sends a Telegram notification.

**No auto-claiming. Detect only — you decide what to do with findings.**

## Supported Ecosystems

- **npm** (package.json, package-lock.json, yarn.lock, JS bundles)
- **PyPI** (requirements.txt, setup.py, Pipfile, pyproject.toml)
- **RubyGems** (Gemfile, Gemfile.lock, .gemspec)

## Modes

### JS Analysis (`-js`)

Analyzes JavaScript files for embedded dependency blocks (`dependencies`, `devDependencies`, `peerDependencies`, `optionalDependencies`, `bundledDependencies`). Only trusts packages where the value is a valid version string (`^1.0.0`, `~2.3`, `latest`, etc.). Ignores `node_modules/` paths, `require()`, and `import` statements — those are noise.

Handles `npm:` aliases correctly (extracts the real package from the value, not the alias key). Skips `link:`, `file:`, `workspace:`, `git+`, `github:` references entirely.

```bash
python3 main.py -js js_urls.txt -notify -o results.txt
```

### Domain Fuzzing (`-dL`)

For each domain:

1. **Direct root check** — tries `domain.com/package.json`, `domain.com/requirements.txt`, etc. directly. If a valid manifest is found, processes it and stops — no crawl, no ffuf needed.
2. **Crawl + traversal** — if no direct hit, crawls the homepage to extract real directory paths, then generates traversal combinations (`../`, `..%2f`, `..%252f`, `..;/`) for each path up to its depth. Runs ffuf against these.
3. **First valid unique hit** — downloads and validates each ffuf hit. Content-hashes the response to deduplicate (same file via 10 different traversal paths = processed once). Stops at the first valid unique manifest found.

```bash
python3 main.py -dL domains.txt -notify -o results.txt
```

### GitHub Org Scanning (`-org`)

Searches a GitHub organization's repos for manifest files, fetches them, extracts dependencies, and checks registries.

```bash
python3 main.py -org target-org -dL domains.txt -notify -o results.txt
```

## How Package Checking Works

For unscoped packages (`some-package`):
- `GET registry.npmjs.org/some-package` → 404 = claimable

For scoped packages (`@scope/package`):
- Check if `@scope` is a registered npm org: `GET registry.npmjs.org/-/org/{scope}/package`
- Check if `@scope` is a registered npm user
- If scope is owned by anyone → **not claimable**, skip
- If scope is completely unclaimed AND package returns 404 → **claimable**

## Output Format

```
[HIT] https://target.com/package.json | nothing claimable

[HIT] https://target.com/package.json
    [CLAIMABLE] npm:@company/internal-api@^2.1.0
    [CLAIMABLE] npm:@company/auth-utils@^1.0.3
```

## Setup

```bash
pip3 install -r requirements.txt

# ffuf (for domain fuzzing mode)
go install github.com/ffuf/ffuf/v2@latest

# GitHub CLI (for -org mode)
gh auth login
```

### Telegram Notifications

1. Create a bot via [@BotFather](https://t.me/BotFather)
2. Get your chat ID from `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Edit `.env`:

```
USE_NOTIFY=false
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Project Structure

```
main.py                 CLI entry point + prerequisites check
config.py               Settings, .env, SQLite cache (hunter.db)
filters.py              CDN skip list, known public packages (~500+)
extractor.py            Package extraction for all manifest types
registry_checker.py     npm / PyPI / RubyGems registry checks + org and user scope ownership
notifier.py             Telegram notifications
js_analyzer.py          JS file analysis mode
domain_fuzzer.py        Domain manifest fuzzing mode
github_scanner.py       GitHub org scanning mode
package_patterns.txt    Manifest path wordlist
user-agent.txt          935 user-agents for rotation
```

## Manifest Types and Extractors

| File | Ecosystem | Extraction method |
|---|---|---|
| package.json | npm | JSON dep blocks, version validated |
| package-lock.json | npm | same as package.json |
| yarn.lock | npm | regex on `pkg@version` lines |
| requirements.txt | PyPI | line-by-line, version required |
| setup.py | PyPI | `install_requires=[...]` block |
| Pipfile | PyPI | `[packages]` section |
| pyproject.toml | PyPI | `[project.dependencies]` |
| Gemfile | RubyGems | `gem 'name', '~> version'` |
| Gemfile.lock | RubyGems | same regex |

## Disclaimer

This tool is for authorized security research and bug bounty programs only. Use it only against targets you have explicit permission to test.
