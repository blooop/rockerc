#!/usr/bin/env python3

import sys

print("Starting test script...")
print(f"Python version: {sys.version}")

try:
    print("Importing rockerc.renv...")
    from rockerc.renv import main

    print("Import successful!")

    print("Running main()...")
    sys.argv = ["test_renv.py", "--install"]
    main()
    print("main() completed!")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
