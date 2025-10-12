# Plan: Sanitise Docker Names

1. Identify where repo owner and repo name are used for Docker naming in the codebase (likely in `renv.py`).
2. Implement a sanitisation function to convert names to lowercase and remove/replace invalid characters.
3. Update code to use the sanitised names wherever Docker names are constructed.
4. Add unit tests to verify sanitisation logic and integration (e.g., in `test_renv.py`).
5. Run CI to ensure all checks pass.
6. Push changes if CI is successful.
