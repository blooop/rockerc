#!/bin/bash
# Setup script for renv bash completion using fzf

install_renv_completion() {
    echo "Installing renv bash completion..."
    
    # Check for fzf
    if ! command -v fzf >/dev/null 2>&1; then
        echo "Error: fzf is not installed or not in PATH."
        echo "Please install fzf first: https://github.com/junegunn/fzf"
        return 1
    fi
    
    echo "✓ fzf found at: $(command -v fzf)"
    
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
    
    # Check if fzf bash integration is enabled
    FZF_INTEGRATION_FOUND=false
    for config_file in ~/.bashrc ~/.bash_profile ~/.profile; do
        if [[ -f "$config_file" ]] && grep -q "fzf --bash" "$config_file"; then
            FZF_INTEGRATION_FOUND=true
            break
        fi
    done
    
    if [[ "$FZF_INTEGRATION_FOUND" == "false" ]]; then
        echo "⚠ Warning: fzf bash integration not detected in your shell config."
        echo "  Add this line to your ~/.bashrc or ~/.bash_profile:"
        echo '  eval "$(fzf --bash)"'
    fi
    
    echo ""
    echo "📋 Next steps:"
    echo "1. Reload your shell: source ~/.bashrc"
    echo "2. Or start a new terminal session"
    echo "3. Try: renv <TAB> for fuzzy completion!"
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
        echo "  install   - Install fzf-based bash completion for renv"
        echo "  uninstall - Uninstall bash completion for renv"
        ;;
esac
