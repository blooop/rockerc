import subprocess


def test_renv_osrf_rocker():
    result = subprocess.run(
        ["bash", "test/test_renv_osrf_rocker.sh"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"renv osrf/rocker failed: {result.stderr}"


def test_renv_blooop_bencher():
    result = subprocess.run(
        ["bash", "test/test_renv_blooop_bencher.sh"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"renv blooop/bencher failed: {result.stderr}"
