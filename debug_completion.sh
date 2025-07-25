#!/bin/bash
echo "=== Content of renv_completion.sh ==="
cat renv_completion.sh
echo ""
echo "=== Checking syntax ==="
bash -n renv_completion.sh
echo "Exit code: $?"
echo ""
echo "=== Sourcing and testing ==="
bash -c "
source ./renv_completion.sh
echo 'Script sourced'
if type _renv_complete >/dev/null 2>&1; then
    echo 'Function _renv_complete exists'
    type _renv_complete
else
    echo 'Function _renv_complete does not exist'
fi
"
