#!/usr/bin/env bash
set -e
cd /tmp
rm -rf /tmp/renv

echo "Testing image caching and container attachment functionality..."

# Clean up any existing containers for this test (keep images)
echo "Cleaning up existing containers..."
docker rm -f rocker-main 2>/dev/null || true

# First build - should build from scratch
echo "First build: renv blooop/test_renv@main (should build image)"
start_time=$(date +%s)
timeout 120 renv blooop/test_renv@main /bin/true 2>&1 | head -50 || true
first_build_time=$(($(date +%s) - start_time))
echo "First build complete"
echo "First build took: ${first_build_time} seconds"

# Check if image was created
if docker images | grep -q rocker-main; then
    echo "SUCCESS: Image rocker-main was created"
else
    echo "WARNING: Image rocker-main was not found"
fi

# Leave the container running for attachment test
echo "Starting container in background for attachment test..."
timeout 120 bash -c 'renv blooop/test_renv@main sleep 30 &' 2>&1 | head -20 || true
sleep 2

# Third run - should attach to existing running container
echo "Third run: renv blooop/test_renv@main (should attach to running container)"
start_time=$(date +%s)
timeout 10 renv blooop/test_renv@main /bin/true 2>&1 | head -50 || true
attach_time=$(($(date +%s) - start_time))
echo "Container attachment complete"
echo "Container attachment took: ${attach_time} seconds"

# Clean up container but keep image for second build test
echo "Cleaning up container to test image reuse..."
docker rm -f rocker-main 2>/dev/null || true

# Second build - should use cached image
echo "Second build: renv blooop/test_renv@main (should use cached image)"
start_time=$(date +%s)
timeout 120 renv blooop/test_renv@main /bin/true 2>&1 | head -50 || true
second_build_time=$(($(date +%s) - start_time))
echo "Second build complete"
echo "Second build took: ${second_build_time} seconds"

# Display timing comparison
echo "Timing comparison:"
echo "  First build (from scratch): ${first_build_time}s"
echo "  Second build (cached image): ${second_build_time}s"
echo "  Container attachment: ${attach_time}s"

# Check that caching and attachment work as expected
if [ $second_build_time -lt $((first_build_time / 2)) ]; then
    echo "SUCCESS: Second build was significantly faster, indicating image caching worked"
else
    echo "WARNING: Second build time (${second_build_time}s) was not significantly faster than first (${first_build_time}s)"
fi

if [ $attach_time -lt 5 ]; then
    echo "SUCCESS: Container attachment was very fast (${attach_time}s), indicating attachment worked"
else
    echo "WARNING: Container attachment took longer than expected (${attach_time}s)"
fi