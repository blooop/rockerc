#!/usr/bin/env python3

from rockerc.rockerc import yaml_dict_to_args

try:
    config = {
        "image": "ubuntu:22.04",
        "args": [
            "user",
            "pull",
            "deps",
            "git",
            "git-clone",
            "ssh",
            "ssh-client",
            "nocleanup",
            "persist-image",
        ],
        "extension-blacklist": ["nvidia", "create-dockerfile", "cwd"],
    }
    result = yaml_dict_to_args(config)
    print("rocker " + result)
except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
