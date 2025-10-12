# Sanitise Docker Names

Sanitise the repository owner and repository name to ensure they contain only lowercase alphanumeric characters and dashes before using them as Docker names. This prevents Docker name failures due to invalid characters (e.g., uppercase letters).

## Requirements
- Ensure repo owner and repo name are converted to lowercase and only contain valid Docker name characters.
- Add tests to verify sanitisation.
- Run CI and push if all checks pass.
