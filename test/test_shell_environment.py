"""Test container attachment and shell environment setup."""
import subprocess


def test_interactive_shell_sources_bashrc():
    """Test that interactive shell properly sources .bashrc and environment."""
    # This test demonstrates the issue where docker exec without login shell
    # doesn't source shell configuration files
    
    # Create a temporary container with a custom .bashrc
    container_name = "test_shell_env"
    
    try:
        # Clean up any existing test container
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            check=False
        )
        
        # Start a detached container
        subprocess.run([
            "docker", "run", "-d", "--name", container_name,
            "ubuntu:22.04", "sleep", "300"
        ], check=True)
        
        # Add a custom executable to PATH via .bashrc 
        subprocess.run([
            "docker", "exec", container_name, "bash", "-c",
            'echo "export PATH=$PATH:/custom/bin" >> /root/.bashrc && '
            'mkdir -p /custom/bin && '
            'echo "#!/bin/bash\necho Hello from custom executable" > /custom/bin/myexe && '
            'chmod +x /custom/bin/myexe'
        ], check=True)
        
        # Test 1: Non-login shell (current behavior) - should fail to find myexe
        result_nonlogin = subprocess.run([
            "docker", "exec", container_name, "bash", "-c", "which myexe"
        ], capture_output=True, text=True, check=False)
        
        # Test 2: Login shell - should find myexe
        result_login = subprocess.run([
            "docker", "exec", container_name, "bash", "-l", "-c", "which myexe"  
        ], capture_output=True, text=True, check=False)
        
        print(f"Non-login shell result: {result_nonlogin.returncode}, stdout: {result_nonlogin.stdout}")
        print(f"Login shell result: {result_login.returncode}, stdout: {result_login.stdout}")
        
        # The issue: non-login shell doesn't source .bashrc
        assert result_nonlogin.returncode != 0, "Non-login shell should not find custom executable"
        assert result_login.returncode == 0, "Login shell should find custom executable"
        assert "/custom/bin/myexe" in result_login.stdout
        
    finally:
        # Clean up
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            check=False
        )


def test_current_interactive_shell_behavior():
    """Test that current rockerc.core.interactive_shell doesn't source .bashrc."""
    
    container_name = "test_current_shell"
    
    try:
        # Clean up any existing test container
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            check=False
        )
        
        # Start a detached container
        subprocess.run([
            "docker", "run", "-d", "--name", container_name,
            "ubuntu:22.04", "sleep", "300"
        ], check=True)
        
        # Add environment variable to .bashrc
        subprocess.run([
            "docker", "exec", container_name, "bash", "-c",
            'echo "export TEST_VAR=hello_from_bashrc" >> /root/.bashrc'
        ], check=True)
        
        # Test current implementation by checking if TEST_VAR is available
        # We'll simulate the current behavior by running the same command it uses
        result = subprocess.run([
            "docker", "exec", "-it", container_name, "/bin/bash", "-c", "echo $TEST_VAR"
        ], capture_output=True, text=True, check=False)
        
        print(f"Current behavior result: '{result.stdout.strip()}'")
        
        # This should fail (empty) because .bashrc is not sourced
        assert result.stdout.strip() == "", "Current behavior should not source .bashrc"
        
    finally:
        # Clean up
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            check=False
        )


if __name__ == "__main__":
    test_interactive_shell_sources_bashrc()
    test_current_interactive_shell_behavior()