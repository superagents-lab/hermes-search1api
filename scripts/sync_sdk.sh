#!/usr/bin/env bash
# Sync the vendored search1api SDK from a PyPI release.
# Usage: ./scripts/sync_sdk.sh [version]   (default: latest)
set -euo pipefail

VERSION="${1:-}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$REPO_ROOT/search1api"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ -z "$VERSION" ]; then
  VERSION="$(python3 -c 'import json,urllib.request; print(json.load(urllib.request.urlopen("https://pypi.org/pypi/search1api/json"))["info"]["version"])')"
fi

echo "Fetching search1api==$VERSION sdist from PyPI..."
URL="$(python3 - "$VERSION" <<'PY'
import json, sys, urllib.request
data = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/search1api/{sys.argv[1]}/json"))
for f in data["urls"]:
    if f["packagetype"] == "sdist":
        print(f["url"]); break
else:
    sys.exit("no sdist found")
PY
)"

curl -fsSL "$URL" -o "$TMP/sdk.tar.gz"
tar -xzf "$TMP/sdk.tar.gz" -C "$TMP"
SRC="$(find "$TMP" -type d -name search1api -path '*/src/*' | head -1)"
[ -n "$SRC" ] || { echo "src/search1api not found in sdist"; exit 1; }

mkdir -p "$TARGET"
cp "$SRC/__init__.py" "$SRC/client.py" "$SRC/errors.py" "$SRC/types.py" "$TARGET/"
echo "Vendored search1api==$VERSION -> $TARGET"
