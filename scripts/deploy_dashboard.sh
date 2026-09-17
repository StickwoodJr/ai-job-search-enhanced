#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
REPORT_FILE="${REPO_ROOT}/reports/application-dashboard.html"

if [ ! -f "${REPORT_FILE}" ]; then
  echo "Error: Dashboard report not found at ${REPORT_FILE}" >&2
  exit 1
fi

mkdir -p "${DIST_DIR}"
cp "${REPORT_FILE}" "${DIST_DIR}/index.html"
if [ -f "${REPO_ROOT}/reports/analytics.html" ]; then
  cp "${REPO_ROOT}/reports/analytics.html" "${DIST_DIR}/analytics.html"
fi
touch "${DIST_DIR}/.nojekyll"

if [ -z "${DASHBOARD_REPO:-}" ]; then
  if [ -d "${DIST_DIR}/.git" ]; then
    DASHBOARD_REPO="$(git -C "${DIST_DIR}" remote get-url origin 2>/dev/null || true)"
  fi
fi

if [ -z "${DASHBOARD_REPO:-}" ]; then
  echo "Tip: To deploy your dashboard to GitHub Pages, set the DASHBOARD_REPO environment variable:"
  echo "     export DASHBOARD_REPO=\"https://github.com/<your-username>/<your-repo>.git\""
  echo "Dashboard HTML is saved locally at ${REPORT_FILE}"
  exit 0
fi

if [ ! -d "${DIST_DIR}/.git" ]; then
  cd "${DIST_DIR}"
  git init -b main
  git remote add origin "${DASHBOARD_REPO}"
fi

cd "${DIST_DIR}"
git add index.html analytics.html README.md .nojekyll

if git diff-index --quiet HEAD --; then
  echo "Dashboard is already up to date on GitHub Pages."
else
  git commit -m "chore(dashboard): update job metrics ($(date +'%Y-%m-%d %H:%M'))"
  git push origin main
  echo "✓ Successfully deployed updated dashboard to GitHub Pages!"
fi
