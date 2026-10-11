#!/bin/bash
# Deutscher Name für gamebank.sh, alle Optionen wie dort.
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/gamebank.sh" "$@"
