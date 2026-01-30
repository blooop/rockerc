# Fix YAML List Arguments Expansion

**Issue:** #120 (comment #3824380588)

**Problem:** YAML list values like `devices: [/dev/dri, /dev/ttyACM0]` are converted to string `"[/dev/dri, /dev/ttyACM0]"` instead of expanded to repeated flags.

**Fix:** Modify `yaml_dict_to_args()` in `rockerc/rockerc.py:354-355` to expand list values into repeated flags: `--devices /dev/dri --devices /dev/ttyACM0`
