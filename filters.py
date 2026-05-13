# ── CDN / third-party domains to skip when filtering JS URLs ──────────────

SKIP_DOMAINS = {
    # Google
    "googleapis.com", "googletagmanager.com", "google-analytics.com",
    "gstatic.com", "googlesyndication.com", "googleadservices.com",
    "google.com/recaptcha", "www.google.com", "accounts.google.com",
    "maps.google.com", "translate.google.com",
    # Facebook / Meta
    "facebook.net", "fbcdn.net", "facebook.com", "connect.facebook.net",
    # Twitter / X
    "platform.twitter.com", "cdn.syndication.twimg.com", "abs.twimg.com",
    # CDN providers
    "cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com",
    "stackpath.bootstrapcdn.com", "maxcdn.bootstrapcdn.com",
    "code.jquery.com", "ajax.aspnetcdn.com", "cdn.bootcdn.net",
    # Analytics / tracking
    "cdn.segment.com", "static.hotjar.com", "rum-static.pingdom.net",
    "js.hs-scripts.com", "js.hs-analytics.net", "js.hsforms.net",
    "snap.licdn.com", "bat.bing.com", "sc-static.net",
    "www.clarity.ms", "plausible.io", "cdn.mxpnl.com",
    # Chat / support widgets
    "widget.intercom.io", "js.intercomcdn.com",
    "embed.tawk.to", "static.tawk.to",
    "client.crisp.chat",
    "assets.zendesk.com", "static.zdassets.com",
    "wchat.freshchat.com",
    # Payment
    "js.stripe.com", "checkout.stripe.com",
    "www.paypal.com", "www.paypalobjects.com",
    # Cookie / consent
    "cdn.cookielaw.org", "cdn.onetrust.com", "consent.cookiebot.com",
    # Error tracking
    "browser.sentry-cdn.com", "js.sentry-cdn.com",
    "d37gvrvc0wt4s1.cloudfront.net",  # bugsnag
    # Fonts
    "fonts.googleapis.com", "fonts.gstatic.com", "use.typekit.net",
    "use.fontawesome.com", "kit.fontawesome.com",
    # Maps
    "maps.googleapis.com", "api.mapbox.com", "api.tiles.mapbox.com",
    # Other common third-party
    "cdn.amplitude.com", "cdn.optimizely.com", "cdn.branch.io",
    "www.recaptcha.net", "challenges.cloudflare.com",
    "hcaptcha.com", "newassets.hcaptcha.com",
    "player.vimeo.com", "www.youtube.com", "s.ytimg.com",
    "platform.linkedin.com",
}

# ── JS filenames/patterns to skip ────────────────────────────────────────

SKIP_JS_PATTERNS = [
    "jquery", "bootstrap.min", "bootstrap.bundle",
    "polyfill", "gtag", "analytics",
    "pixel", "tracking", "beacon",
    "recaptcha", "captcha",
    "hotjar", "intercom", "drift", "crisp", "tawk",
    "zendesk", "freshdesk", "freshchat",
    "sentry", "bugsnag", "datadog",
    "segment", "mixpanel", "amplitude", "optimizely",
    "googletagmanager", "google-analytics", "ga.js", "gtm.js",
    "fbevents", "fb-events", "facebook-pixel",
    "twitter-pixel", "linkedin-pixel",
    "cookieconsent", "onetrust", "cookiebot",
    "sw.js", "service-worker", "serviceworker",
    "manifest.json",
    "stripe.js",
]

# ── JS filename patterns that indicate high-value app bundles ────────────

KEEP_JS_PATTERNS = [
    "app-", "app.", "main-", "main.",
    "vendor-", "vendor.", "vendors-", "vendors.",
    "chunk-", "chunk.", "commons-", "commons.",
    "bundle-", "bundle.", "runtime-", "runtime.",
    "shared-", "shared.", "framework-", "framework.",
    "index-", "index.",
    "webpack", "node_modules",
]

# ── Signals in JS content that indicate dependency info ──────────────────

JS_SIGNALS = [
    "__webpack_require__",
    "__webpack_modules__",
    "webpackChunk",
    "webpackJsonp",
    "node_modules",
    '"dependencies"',
    '"devDependencies"',
    '"peerDependencies"',
    '"optionalDependencies"',
    "require(",
]

# ── Node.js built-in modules (never check these) ────────────────────────

NODE_BUILTINS = {
    "assert", "async_hooks", "buffer", "child_process", "cluster",
    "console", "constants", "crypto", "dgram", "diagnostics_channel",
    "dns", "domain", "events", "fs", "http", "http2", "https",
    "inspector", "module", "net", "os", "path", "perf_hooks",
    "process", "punycode", "querystring", "readline", "repl",
    "stream", "string_decoder", "sys", "timers", "tls", "trace_events",
    "tty", "url", "util", "v8", "vm", "wasi", "worker_threads", "zlib",
    # Node prefixed
    "node:assert", "node:buffer", "node:child_process", "node:cluster",
    "node:console", "node:constants", "node:crypto", "node:dgram",
    "node:dns", "node:domain", "node:events", "node:fs", "node:http",
    "node:http2", "node:https", "node:inspector", "node:module",
    "node:net", "node:os", "node:path", "node:perf_hooks", "node:process",
    "node:punycode", "node:querystring", "node:readline", "node:repl",
    "node:stream", "node:string_decoder", "node:sys", "node:timers",
    "node:tls", "node:trace_events", "node:tty", "node:url", "node:util",
    "node:v8", "node:vm", "node:wasi", "node:worker_threads", "node:zlib",
}

# ── Well-known public packages to skip (not worth checking registry) ─────
# These are extremely popular and will always exist on npm.

KNOWN_PUBLIC_PACKAGES = {
    # ── Core frameworks ──
    "react", "react-dom", "react-router", "react-router-dom",
    "react-redux", "react-scripts", "react-refresh",
    "react-is", "react-transition-group", "react-helmet",
    "react-hook-form", "react-query", "react-select",
    "react-datepicker", "react-modal", "react-toastify",
    "react-icons", "react-dnd", "react-dropzone",
    "react-intl", "react-i18next", "react-markdown",
    "react-beautiful-dnd", "react-virtualized", "react-window",
    "react-spring", "react-table", "react-chartjs-2",
    "react-color", "react-copy-to-clipboard", "react-csv",
    "react-player", "react-pdf", "react-ace",
    "next", "next-auth", "nextjs",
    "vue", "vuex", "vue-router", "vue-loader", "vue-template-compiler",
    "nuxt", "nuxtjs",
    "svelte", "sveltekit",
    # ── Angular (all @angular scoped) ──
    "@angular/core", "@angular/common", "@angular/compiler",
    "@angular/forms", "@angular/router", "@angular/http",
    "@angular/platform-browser", "@angular/platform-browser-dynamic",
    "@angular/platform-server", "@angular/animations",
    "@angular/cdk", "@angular/material", "@angular/flex-layout",
    "@angular/fire", "@angular/cli", "@angular/compiler-cli",
    "@angular/language-service", "@angular/localize",
    "@angular/service-worker", "@angular/upgrade",
    "@angular/elements", "@angular/pwa",
    "@angular-devkit/build-angular", "@angular-devkit/core",
    "@angular-devkit/schematics",
    "angular", "angular-animate", "angular-aria", "angular-cookies",
    "angular-loader", "angular-messages", "angular-mocks",
    "angular-resource", "angular-route", "angular-sanitize",
    "angular-touch", "angular-i18n",
    "angular-bootstrap", "angular-ui-router", "angular-translate",
    "angular-filter", "angular-gettext", "angular-moment",
    "angular-dragdrop", "angular-component", "angular-cookie",
    "angular-bootstrap-colorpicker",
    "zone.js", "rxjs", "tslib",
    # ── State management ──
    "redux", "redux-thunk", "redux-saga", "redux-devtools",
    "mobx", "mobx-react", "recoil", "zustand", "jotai", "valtio",
    "ngrx", "@ngrx/store", "@ngrx/effects", "@ngrx/router-store",
    "pinia",
    # ── Utility libraries ──
    "lodash", "lodash-es", "lodash.merge", "lodash.get",
    "lodash.set", "lodash.clonedeep", "lodash.debounce",
    "lodash.throttle", "lodash.isequal", "lodash.isempty",
    "lodash.uniq", "lodash.pick", "lodash.omit",
    "underscore", "ramda", "immutable", "immer",
    "uuid", "nanoid", "shortid",
    "moment", "moment-timezone", "dayjs", "date-fns", "luxon",
    "classnames", "clsx",
    "deepmerge", "deep-equal", "fast-deep-equal",
    "qs", "query-string",
    # ── HTTP / networking ──
    "axios", "node-fetch", "isomorphic-fetch", "whatwg-fetch",
    "cross-fetch", "got", "superagent", "request", "needle",
    "form-data", "formidable", "multer",
    "socket.io", "socket.io-client", "ws", "websocket",
    "graphql", "graphql-tag", "apollo-client", "@apollo/client",
    "urql", "relay-runtime",
    # ── Build tools ──
    "webpack", "webpack-cli", "webpack-dev-server",
    "webpack-merge", "webpack-bundle-analyzer",
    "html-webpack-plugin", "mini-css-extract-plugin",
    "css-loader", "style-loader", "file-loader", "url-loader",
    "babel-loader", "ts-loader", "sass-loader", "less-loader",
    "postcss-loader", "raw-loader",
    "vite", "rollup", "esbuild", "parcel", "turbopack", "swc",
    "gulp", "grunt", "browserify",
    "@babel/core", "@babel/preset-env", "@babel/preset-react",
    "@babel/preset-typescript", "@babel/plugin-transform-runtime",
    "@babel/runtime", "@babel/register",
    "typescript", "ts-node", "tsx",
    # ── Testing ──
    "jest", "mocha", "chai", "sinon", "nyc", "istanbul",
    "jasmine", "karma", "protractor", "nightwatch",
    "cypress", "playwright", "@playwright/test",
    "puppeteer", "selenium-webdriver",
    "@testing-library/react", "@testing-library/jest-dom",
    "@testing-library/dom", "@testing-library/user-event",
    "enzyme", "react-test-renderer",
    "vitest", "ava", "tap",
    # ── CSS / styling ──
    "tailwindcss", "postcss", "autoprefixer", "cssnano",
    "sass", "node-sass", "less", "stylus",
    "styled-components", "emotion", "@emotion/react", "@emotion/styled",
    "bootstrap", "bulma", "foundation-sites",
    "@mui/material", "@mui/icons-material", "@mui/system",
    "@material-ui/core", "@material-ui/icons",
    "antd", "@ant-design/icons",
    "chakra-ui", "@chakra-ui/react",
    "semantic-ui-react", "primereact", "primeng",
    # ── Backend frameworks ──
    "express", "koa", "fastify", "hapi", "@hapi/hapi",
    "nestjs", "@nestjs/core", "@nestjs/common",
    "body-parser", "cors", "helmet", "morgan", "compression",
    "cookie-parser", "express-session", "express-validator",
    "passport", "passport-local", "passport-jwt",
    "jsonwebtoken", "bcrypt", "bcryptjs",
    # ── Database ──
    "mongoose", "mongodb", "mysql", "mysql2", "pg", "sqlite3",
    "sequelize", "typeorm", "prisma", "@prisma/client",
    "knex", "objection", "bookshelf", "waterline",
    "redis", "ioredis", "memcached",
    # ── Linting / formatting ──
    "eslint", "prettier", "stylelint", "tslint",
    "@eslint/js", "@typescript-eslint/parser",
    "@typescript-eslint/eslint-plugin",
    "eslint-config-prettier", "eslint-plugin-react",
    "eslint-plugin-import", "eslint-plugin-jsx-a11y",
    "husky", "lint-staged", "commitlint",
    # ── D3 / charting ──
    "d3", "d3-array", "d3-scale", "d3-selection", "d3-shape",
    "d3-axis", "d3-color", "d3-format", "d3-geo", "d3-hierarchy",
    "d3-interpolate", "d3-path", "d3-time", "d3-time-format",
    "d3-transition", "d3-zoom", "d3-brush", "d3-drag", "d3-force",
    "chart.js", "chartjs", "echarts", "highcharts", "apexcharts",
    "recharts", "victory", "nivo",
    # ── i18n ──
    "i18next", "i18next-browser-languagedetector",
    "i18next-http-backend", "intl", "intl-messageformat",
    "formatjs", "@formatjs/intl",
    # ── Animation ──
    "framer-motion", "gsap", "animejs", "popmotion",
    "lottie-web", "lottie-react",
    # ── File handling ──
    "file-saver", "jszip", "xlsx", "exceljs", "papaparse",
    "pdf-lib", "pdfjs-dist", "jspdf", "html2canvas",
    "sharp", "jimp", "image-size",
    # ── Markdown / rich text ──
    "marked", "markdown-it", "remark", "rehype",
    "highlight.js", "prismjs",
    "draft-js", "slate", "quill", "tiptap",
    "prosemirror-state", "prosemirror-view", "prosemirror-model",
    "@tiptap/core", "@tiptap/react",
    # ── Types ──
    "@types/react", "@types/react-dom", "@types/node",
    "@types/jest", "@types/lodash", "@types/express",
    # ── Monorepo / package management ──
    "lerna", "turbo", "nx", "@nx/workspace",
    "changesets", "@changesets/cli",
    # ── Other extremely common ──
    "dotenv", "cross-env", "env-cmd", "concurrently",
    "nodemon", "pm2", "forever",
    "chalk", "commander", "yargs", "inquirer", "ora", "progress",
    "debug", "winston", "pino", "bunyan", "log4js",
    "bluebird", "async", "p-limit", "p-queue",
    "glob", "globby", "minimatch", "micromatch",
    "chokidar", "fs-extra", "mkdirp", "rimraf", "del",
    "path-to-regexp", "resolve", "semver",
    "prop-types", "hoist-non-react-statics",
    "core-js", "regenerator-runtime", "whatwg-url",
    "object-assign", "es6-promise", "promise",
    "symbol-observable", "setimmediate",
    "scheduler", "loose-envify", "js-tokens",
    "invariant", "warning", "tiny-warning", "tiny-invariant",
    "inherits", "safe-buffer", "buffer",
    "readable-stream", "string_decoder", "isarray",
    "events", "process", "util", "assert", "browserify-zlib",
    "crypto-browserify", "stream-browserify", "stream-http",
    "https-browserify", "os-browserify", "path-browserify",
    "punycode", "querystring-es3", "url", "vm-browserify",
    "timers-browserify", "tty-browserify", "constants-browserify",
    "console-browserify", "domain-browser",
    "ieee754", "base64-js", "isexe", "which",
    "color-convert", "color-name", "ansi-styles", "supports-color",
    "has-flag", "ms", "escape-string-regexp",
    "normalize-path", "picomatch", "to-regex-range",
    "fill-range", "braces", "anymatch",
    "is-glob", "is-extglob", "binary-extensions",
    "balanced-match", "brace-expansion", "concat-map",
    "wrappy", "once", "inflight",
    "lru-cache", "yallist",
    "json5", "yaml", "toml", "ini",
    "mime", "mime-types", "mime-db", "content-type",
    "cookie", "tough-cookie", "set-cookie-parser",
    "http-errors", "statuses", "on-finished",
    "raw-body", "bytes", "unpipe", "destroy", "ee-first",
    "depd", "fresh", "etag", "vary", "proxy-addr",
    "forwarded", "ipaddr.js", "accepts", "negotiator",
    "range-parser", "type-is", "media-typer",
    "content-disposition", "send", "serve-static",
    "encodeurl", "escape-html", "parseurl", "utils-merge",
    "merge-descriptors", "methods", "finalhandler",
    "array-flatten", "path-is-absolute",
    "safer-buffer", "iconv-lite",
    "ajv", "ajv-keywords", "json-schema-traverse",
    "fast-json-stable-stringify", "fast-json-stringify",
    "uri-js",
    "source-map", "source-map-support", "source-map-js",
    "acorn", "acorn-walk", "acorn-jsx",
    "estree-walker", "esutils", "estraverse", "escodegen",
    "magic-string", "sourcemap-codec",
    "terser", "uglify-js",
    "clean-css", "css-tree", "csso",
    "caniuse-lite", "browserslist", "electron-to-chromium",
    "node-releases", "update-browserslist-db",
    "colorette", "picocolors", "nanocolors",
    "yocto-queue", "p-locate", "locate-path", "path-exists",
    "find-up", "pkg-dir",
    "strip-ansi", "ansi-regex", "wrap-ansi", "string-width",
    "cli-cursor", "restore-cursor", "onetime", "mimic-fn",
    "signal-exit", "strip-final-newline", "human-signals",
    "execa", "cross-spawn", "shebang-command", "shebang-regex",
    "npm-run-path", "path-key",
    "is-stream", "get-stream", "merge-stream",
    "through2", "pump", "end-of-stream", "duplexer",
    "is-plain-object", "is-buffer", "kind-of", "is-number",
    "is-core-module", "has", "hasown", "function-bind",
    "call-bind", "get-intrinsic", "es-abstract",
    "object-keys", "object.assign", "define-properties",
    "has-symbols", "has-property-descriptors", "has-proto",
    "es-define-property", "es-errors", "es-object-atoms",
    "gopd", "set-function-length", "set-function-name",
    "side-channel", "internal-slot",
    "regexp.prototype.flags", "array-includes",
    "array.prototype.flat", "array.prototype.flatmap",
    "string.prototype.trimstart", "string.prototype.trimend",
    "string.prototype.matchall",
    "object.entries", "object.fromentries", "object.values",
    "globalthis",
    "es-to-primitive", "is-callable", "is-date-object",
    "is-symbol", "is-regex", "is-string", "is-boolean-object",
    "is-number-object", "is-bigint", "which-boxed-primitive",
    "unbox-primitive", "which-typed-array",
    "is-typed-array", "is-array-buffer", "is-shared-array-buffer",
    "is-weakref", "is-negative-zero", "is-map", "is-set",
    "stop-iteration-iterator", "iterator.prototype",
    "es-set-tostringtag", "es-iterator-helpers",
    "typed-array-length", "typed-array-byte-offset",
    "typed-array-byte-length", "typed-array-buffer",
    "available-typed-arrays", "arraybuffer.prototype.slice",
    "data-view-byte-length", "data-view-byte-offset",
    "data-view-buffer",
    "safe-regex-test", "safe-array-concat",
    "reflect.getprototypeof",
    "possible-typed-array-names",
    # ── Python well-known (for pypi check) ──
    "requests", "flask", "django", "fastapi", "numpy", "pandas",
    "scipy", "matplotlib", "pillow", "sqlalchemy", "celery",
    "boto3", "botocore", "setuptools", "pip", "wheel",
    "pytest", "tox", "black", "flake8", "mypy", "pylint",
    "pydantic", "httpx", "aiohttp", "gunicorn", "uvicorn",
    "jinja2", "markupsafe", "werkzeug", "click", "itsdangerous",
    "cryptography", "paramiko", "fabric", "ansible",
    "beautifulsoup4", "lxml", "scrapy", "selenium",
    "tensorflow", "torch", "keras", "scikit-learn",
    "opencv-python", "transformers", "huggingface-hub",
    "python-dotenv", "pyyaml", "toml", "configparser",
    # ── Ruby well-known (for rubygems check) ──
    "rails", "rack", "bundler", "rake", "rspec", "minitest",
    "sinatra", "devise", "pundit", "cancancan",
    "sidekiq", "resque", "delayed_job",
    "pg", "mysql2", "sqlite3", "redis", "mongoid",
    "activerecord", "activesupport", "actionpack", "actionview",
    "actionmailer", "activejob", "activestorage", "actioncable",
    "nokogiri", "faraday", "httparty", "rest-client",
    "puma", "unicorn", "passenger", "thin",
    "rubocop", "solargraph", "pry", "byebug",
    "capistrano", "mina", "aws-sdk", "fog",
    "json", "oj", "multi_json",
}


# ── CSS properties blocklist (safety net for JS extraction) ───────────
# These are CSS properties that can appear in minified JS as "max-height":"100px"
# and get falsely matched as package names.

CSS_PROPERTIES = {
    # sizing
    "max-height", "min-height", "max-width", "min-width",
    "height", "width",
    # margin
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "margin-block", "margin-block-start", "margin-block-end",
    "margin-inline", "margin-inline-start", "margin-inline-end",
    # padding
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "padding-block", "padding-block-start", "padding-block-end",
    "padding-inline", "padding-inline-start", "padding-inline-end",
    # border
    "border", "border-top", "border-right", "border-bottom", "border-left",
    "border-width", "border-style", "border-color",
    "border-radius", "border-top-left-radius", "border-top-right-radius",
    "border-bottom-left-radius", "border-bottom-right-radius",
    "border-collapse", "border-spacing", "border-image",
    # font
    "font", "font-size", "font-weight", "font-family", "font-style",
    "font-variant", "font-stretch", "font-display",
    # text
    "text-align", "text-decoration", "text-transform", "text-indent",
    "text-overflow", "text-shadow", "text-rendering",
    "text-decoration-color", "text-decoration-line", "text-decoration-style",
    # line / letter / word
    "line-height", "letter-spacing", "word-spacing", "word-break", "word-wrap",
    "white-space", "overflow-wrap",
    # color / background
    "color", "background", "background-color", "background-image",
    "background-size", "background-position", "background-repeat",
    "background-attachment", "background-clip", "background-origin",
    # display / position
    "display", "position", "top", "right", "bottom", "left",
    "float", "clear", "visibility", "opacity",
    "z-index", "overflow", "overflow-x", "overflow-y",
    # flex
    "flex", "flex-direction", "flex-wrap", "flex-flow",
    "flex-grow", "flex-shrink", "flex-basis",
    "justify-content", "align-items", "align-self", "align-content",
    "order", "gap", "row-gap", "column-gap",
    # grid
    "grid", "grid-template", "grid-template-columns", "grid-template-rows",
    "grid-template-areas", "grid-column", "grid-row",
    "grid-area", "grid-gap", "grid-auto-flow",
    "grid-auto-columns", "grid-auto-rows",
    # box model
    "box-sizing", "box-shadow", "box-decoration-break",
    # outline
    "outline", "outline-color", "outline-style", "outline-width", "outline-offset",
    # transform / transition / animation
    "transform", "transform-origin", "transform-style",
    "transition", "transition-property", "transition-duration",
    "transition-timing-function", "transition-delay",
    "animation", "animation-name", "animation-duration",
    "animation-timing-function", "animation-delay",
    "animation-iteration-count", "animation-direction",
    "animation-fill-mode", "animation-play-state",
    # list
    "list-style", "list-style-type", "list-style-position", "list-style-image",
    # table
    "table-layout", "caption-side", "empty-cells",
    # cursor / pointer
    "cursor", "pointer-events", "user-select", "touch-action",
    # misc
    "content", "quotes", "counter-reset", "counter-increment",
    "resize", "appearance", "clip", "clip-path",
    "filter", "backdrop-filter", "mix-blend-mode",
    "object-fit", "object-position",
    "vertical-align", "direction", "unicode-bidi",
    "writing-mode", "text-orientation",
    "will-change", "contain", "isolation",
    "scroll-behavior", "scroll-snap-type", "scroll-snap-align",
    "aspect-ratio", "accent-color", "caret-color",
    "column-count", "column-width", "column-gap", "column-rule",
    "page-break-before", "page-break-after", "page-break-inside",
    "break-before", "break-after", "break-inside",
    "orphans", "widows",
    # vendor prefixed common
    "-webkit-appearance", "-moz-appearance",
    "-webkit-font-smoothing", "-moz-osx-font-smoothing",
    "-webkit-overflow-scrolling", "-webkit-tap-highlight-color",
    "-webkit-line-clamp", "-webkit-box-orient",
}


def should_skip_js_url(url):
    """Check if a JS URL should be skipped (CDN/third-party)."""
    url_lower = url.lower()

    # Check domain
    for domain in SKIP_DOMAINS:
        if domain in url_lower:
            return True

    # Check filename patterns
    for pattern in SKIP_JS_PATTERNS:
        if pattern in url_lower:
            return True

    return False


def is_high_value_js(url):
    """Check if a JS URL looks like a high-value app bundle."""
    url_lower = url.lower()
    for pattern in KEEP_JS_PATTERNS:
        if pattern in url_lower:
            return True
    return False


def has_js_signals(content_preview):
    """Check if JS content preview contains dependency signals."""
    for signal in JS_SIGNALS:
        if signal in content_preview:
            return True
    return False


def is_known_package(name):
    """Check if a package name is a known public package or Node builtin."""
    if name in NODE_BUILTINS:
        return True
    if name in KNOWN_PUBLIC_PACKAGES:
        return True
    # Skip if it starts with a well-known scope that's definitely public
    public_scopes = [
        "@angular/", "@babel/", "@types/", "@testing-library/",
        "@emotion/", "@mui/", "@material-ui/", "@chakra-ui/",
        "@ant-design/", "@nestjs/", "@ngrx/", "@apollo/",
        "@formatjs/", "@tiptap/", "@nx/", "@changesets/",
        "@playwright/", "@eslint/", "@typescript-eslint/",
        "@hapi/", "@prisma/", "@storybook/", "@aws-sdk/",
        "@grpc/", "@octokit/", "@sentry/", "@stripe/",
        "@firebase/", "@google-cloud/", "@azure/",
    ]
    for scope in public_scopes:
        if name.startswith(scope):
            return True
    return False
