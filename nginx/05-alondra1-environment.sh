#!/bin/sh
# Runs before nginx renders its templates: the variant must be named explicitly (dev or prod).
set -eu
case "${ALONDRA1_ENVIRONMENT:-}" in
  dev|prod) echo "alondra1-landing: serving the ${ALONDRA1_ENVIRONMENT} variant" ;;
  *) echo "alondra1-landing: ALONDRA1_ENVIRONMENT must be dev or prod (got '${ALONDRA1_ENVIRONMENT:-}')" >&2; exit 1 ;;
esac
