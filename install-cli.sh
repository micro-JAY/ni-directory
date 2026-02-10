#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLI_PATH="$SCRIPT_DIR/cli/nidr.py"
SYMLINK_TARGET="/usr/local/bin/nidr"

echo "NI Directory — CLI installer"
echo ""

# Make sure the CLI script is executable
chmod +x "$CLI_PATH"

# Try to create symlink
if ln -sf "$CLI_PATH" "$SYMLINK_TARGET" 2>/dev/null; then
    echo "✓ Linked nidr → $SYMLINK_TARGET"
    echo ""
    echo "Done! Try it now:"
    echo "  nidr"
    echo "  nidr funk"
    echo "  nidr --refresh"
else
    echo "Could not write to $SYMLINK_TARGET (permission denied)."
    echo ""

    # Detect shell and offer alias
    SHELL_NAME="$(basename "$SHELL")"
    case "$SHELL_NAME" in
        zsh)  RC_FILE="$HOME/.zshrc" ;;
        bash) RC_FILE="$HOME/.bashrc" ;;
        *)    RC_FILE="$HOME/.${SHELL_NAME}rc" ;;
    esac

    ALIAS_LINE="alias nidr='$CLI_PATH'"
    echo "Add this alias to $RC_FILE instead?"
    echo "  $ALIAS_LINE"
    echo ""
    read -r -p "Add it now? [Y/n] " reply
    if [[ -z "$reply" || "$reply" =~ ^[Yy] ]]; then
        echo "" >> "$RC_FILE"
        echo "# NI Directory CLI" >> "$RC_FILE"
        echo "$ALIAS_LINE" >> "$RC_FILE"
        echo "✓ Alias added to $RC_FILE"
        echo "  Run: source $RC_FILE"
        echo ""
        echo "Then try: nidr"
    else
        echo "No changes made. You can add the alias manually:"
        echo "  $ALIAS_LINE"
    fi
fi
