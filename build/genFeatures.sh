#!/usr/bin/env bash
# Wrapper invoking pure-Perl feature generator (build/genFeatures.pl)
set -euo pipefail
exec perl "$(dirname "$0")/genFeatures.pl" "$@"
