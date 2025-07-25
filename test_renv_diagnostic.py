#!/usr/bin/env python3
"""
Simple diagnostic test for renv functionality.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_imports():
    """Test basic imports."""
    print("Testing basic imports...")
    
    try:
        from rockerc.renv import get_version
        print("✓ get_version imported")
        
        version = get_version()
        print(f"✓ Version: {version}")
        
        from rockerc.renv import get_existing_repos
        print("✓ get_existing_repos imported")
        
        repos = get_existing_repos()
        print(f"✓ Found {len(repos)} repos")
        
        from rockerc.renv import repo_completer
        print("✓ repo_completer imported")
        
        completions = repo_completer("")
        print(f"✓ Got {len(completions)} completions")
        
        from rockerc.renv import ARGCOMPLETE_AVAILABLE
        print(f"✓ Argcomplete available: {ARGCOMPLETE_AVAILABLE}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_argcomplete_installation():
    """Test if argcomplete is properly installed."""
    print("\nTesting argcomplete installation...")
    
    try:
        import argcomplete
        print(f"✓ argcomplete imported, version: {getattr(argcomplete, '__version__', 'unknown')}")
        
        # Test if register-python-argcomplete is available
        import subprocess
        result = subprocess.run(['which', 'register-python-argcomplete'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ register-python-argcomplete found at: {result.stdout.strip()}")
        else:
            print("❌ register-python-argcomplete not found in PATH")
            print("This is likely why autocompletion isn't working!")
            return False
            
        return True
        
    except ImportError:
        print("❌ argcomplete not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking argcomplete: {e}")
        return False

def test_shell_completion_setup():
    """Test shell completion setup."""
    print("\nTesting shell completion setup...")
    
    shell_config = Path.home() / ".bashrc"
    if not shell_config.exists():
        shell_config = Path.home() / ".zshrc"
    
    if shell_config.exists():
        with open(shell_config, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'register-python-argcomplete renv' in content:
            print(f"✓ renv autocompletion found in {shell_config}")
            return True
        else:
            print(f"❌ renv autocompletion NOT found in {shell_config}")
            print("This might be why autocompletion isn't working!")
            return False
    else:
        print("❌ No shell config file found (.bashrc or .zshrc)")
        return False

def test_renv_command_availability():
    """Test if renv command is available."""
    print("\nTesting renv command availability...")
    
    try:
        import subprocess
        result = subprocess.run(['which', 'renv'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ renv command found at: {result.stdout.strip()}")
        else:
            print("❌ renv command not found in PATH")
            print("This could be why autocompletion isn't working!")
            return False
            
        # Test renv version
        result = subprocess.run(['renv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ renv --version works: {result.stdout.strip()}")
        else:
            print(f"❌ renv --version failed: {result.stderr}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Error testing renv command: {e}")
        return False

def main():
    """Run diagnostic tests."""
    print("🔍 renv Diagnostic Test Suite")
    print("=" * 40)
    
    tests = [
        test_basic_imports,
        test_argcomplete_installation,
        test_shell_completion_setup,
        test_renv_command_availability
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 40)
    print("📊 Diagnostic Results:")
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {test.__name__}: {status}")
    
    if all(results):
        print("\n🎉 All diagnostics passed!")
        print("\nIf autocompletion still doesn't work, try:")
        print("1. Restart your shell: exec $SHELL")
        print("2. Or source your config: source ~/.bashrc")
        print("3. Test with: renv <TAB>")
    else:
        print("\n❌ Some diagnostics failed.")
        print("\n🔧 Troubleshooting steps:")
        print("1. Install argcomplete globally:")
        print("   uv tool install argcomplete")
        print("   # or: pipx install argcomplete")
        print("   # or: pip install --user argcomplete")
        print("\n2. Add to shell config:")
        print('   echo \'eval "$(register-python-argcomplete renv)"\' >> ~/.bashrc')
        print("\n3. Make sure renv is in PATH")
        print("\n4. Restart shell: exec $SHELL")

if __name__ == "__main__":
    main()
