#!/bin/bash
# Setup script for renv bash completion

install_renv_completion() {
    echo "Installing renv bash completion..."
    
    # Determine completion directory
    COMPLETION_DIR="$HOME/.local/share/bash-completion/completions"
    COMPLETION_FILE="$COMPLETION_DIR/renv"
    
    echo "Completion directory: $COMPLETION_DIR"
    echo "Completion file: $COMPLETION_FILE"
    
    # Create directory if it doesn't exist
    mkdir -p "$COMPLETION_DIR"
    echo "✓ Created directory: $COMPLETION_DIR"
    
    # Copy completion script
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cp "$SCRIPT_DIR/renv_completion.sh" "$COMPLETION_FILE"
    chmod 755 "$COMPLETION_FILE"
    
    echo "✓ Completion script installed to $COMPLETION_FILE"
    
    echo ""
    echo "📋 Next steps:"
    echo "1. Reload your shell: source ~/.bashrc"
    echo "2. Or start a new terminal session"
    echo "3. Try: renv <TAB> for completion!"
}

uninstall_renv_completion() {
    echo "Uninstalling renv bash completion..."
    
    COMPLETION_FILE="$HOME/.local/share/bash-completion/completions/renv"
    
    if [[ -f "$COMPLETION_FILE" ]]; then
        rm "$COMPLETION_FILE"
        echo "✓ Completion script removed from $COMPLETION_FILE"
    else
        echo "ℹ Completion script was not found (already uninstalled?)"
    fi
    
    echo ""
    echo "📋 Completion disabled."
    echo "Reload your shell or start a new terminal session for changes to take effect."
}

# Main script logic
case "$1" in
    install)
        install_renv_completion
        ;;
    uninstall)
        uninstall_renv_completion
        ;;
    *)
        echo "Usage: $0 {install|uninstall}"
        echo ""
        echo "Commands:"
        echo "  install   - Install bash completion for renv"
        echo "  uninstall - Uninstall bash completion for renv"
        ;;
esac
