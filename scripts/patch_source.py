#!/usr/bin/env python3
"""
Source patcher for FlClash-Smart.
Customizes upstream chen08209/FlClash source code:
1. Updates update repository URL to refined-fish/FlClash-Smart.
2. Updates publisher URL in Windows packaging config.
"""

import os
import sys

def patch_constant_dart(src_dir: str, target_repo: str):
    path = os.path.join(src_dir, "lib", "common", "constant.dart")
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    old_line = "const repository = 'chen08209/FlClash';"
    new_line = f"const repository = '{target_repo}';"
    if old_line in content:
        content = content.replace(old_line, new_line)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[+] Successfully patched repository in {path} -> {target_repo}")
    else:
        print(f"[?] '{old_line}' not found in {path}, checking for fallback...")
        import re
        content, count = re.subn(r"const repository = '[^']+';", f"const repository = '{target_repo}';", content)
        if count > 0:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[+] Successfully regex-patched repository in {path} -> {target_repo}")
        else:
            print(f"[!] Failed to find repository declaration in {path}")

def patch_make_config_yaml(src_dir: str, target_repo: str):
    path = os.path.join(src_dir, "windows", "packaging", "exe", "make_config.yaml")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace("publisher_url: https://github.com/chen08209/FlClash",
                              f"publisher_url: https://github.com/{target_repo}")
    content = content.replace("publisher: chen08209", "publisher: refined-fish")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Patched Windows installer config in {path}")

def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    target_repo = sys.argv[2] if len(sys.argv) > 2 else "refined-fish/FlClash-Smart"

    print(f"Patching FlClash sources in: {src_dir} to point to {target_repo}")
    patch_constant_dart(src_dir, target_repo)
    patch_make_config_yaml(src_dir, target_repo)
    print("[+] Source patching complete!")

if __name__ == "__main__":
    main()
