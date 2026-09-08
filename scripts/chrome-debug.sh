#!/bin/bash
# Launch Chrome with remote debugging so chrome-devtools-mcp can attach to it.
# Chrome 136+ refuses --remote-debugging-port on the default profile, so this
# uses a dedicated profile dir. Log into sites once here; the session persists.
exec "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/.chrome-mcp-profile" \
  "$@"
