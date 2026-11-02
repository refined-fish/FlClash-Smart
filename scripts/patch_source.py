#!/usr/bin/env python3
"""
Source patcher for FlClash-Smart.
Customizes upstream chen08209/FlClash source code:
1. Updates update repository URL to refined-fish/FlClash-Smart.
2. Updates publisher URL in Windows packaging config.
3. Decouples invasive configuration overrides in lib/common/task.dart:
   - Preserves profile external-ui and external-ui-url (do not force clear).
   - Preserves profile external-controller & secret unless explicitly opened in FlClash.
   - Preserves profile ports (port, socks-port, mixed-port); only overrides if explicitly configured.
   - Preserves profile allow-lan; only overrides if explicitly enabled in FlClash.
   - Preserves profile geox-url; only falls back to FlClash mirror if not specified in profile.
   - Preserves profile geo-auto-update and store-selected.
4. Prevents runtime updateConfig from sending default geo URLs over profile geo URLs.
5. Allows mixedPort to be disabled (0) in port settings UI.
"""

import os
import re
import sys

def apply_snippet_replacement(content: str, old_snippet: str, new_snippet: str, desc: str) -> str:
    """Replaces a snippet using exact match first, falling back to flexible whitespace regex."""
    if old_snippet in content:
        print(f"  [+] Exact match applied: {desc}")
        return content.replace(old_snippet, new_snippet)

    # Whitespace-tolerant regex fallback
    pattern = re.escape(old_snippet)
    pattern = re.sub(r"\\\s+", r"\\s+", pattern)
    new_content, count = re.subn(pattern, new_snippet, content)
    if count > 0:
        print(f"  [+] Regex fallback applied: {desc}")
        return new_content
    else:
        print(f"  [!] Warning: Failed to match snippet for: {desc}")
        return content

def patch_constant_dart(src_dir: str, target_repo: str):
    path = os.path.join(src_dir, "lib", "common", "constant.dart")
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    old_line = "const repository = 'chen08209/FlClash';"
    new_line = f"const repository = '{target_repo}';"
    content = apply_snippet_replacement(content, old_line, new_line, "Repository URL redirection")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_make_config_yaml(src_dir: str, target_repo: str):
    path = os.path.join(src_dir, "windows", "packaging", "exe", "make_config.yaml")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    content = content.replace("publisher_url: https://github.com/chen08209/FlClash",
                              f"publisher_url: https://github.com/{target_repo}")
    content = content.replace("publisher: chen08209", "publisher: refined-fish")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)
    print(f"[+] Patched Windows installer config in {path}")

def patch_task_dart(src_dir: str):
    path = os.path.join(src_dir, "lib", "common", "task.dart")
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    print(f"[*] Patching non-intrusive config logic in {path}...")

    # 1. External UI: Preserve from profile rather than forcing empty string
    content = apply_snippet_replacement(
        content,
        "rawConfig['external-ui'] = '';\n",
        "// [FlClash-Smart] Preserve external-ui from profile\n",
        "Preserve external-ui"
    )
    content = apply_snippet_replacement(
        content,
        "rawConfig['external-ui-url'] = '';\n",
        "// [FlClash-Smart] Preserve external-ui-url from profile\n",
        "Preserve external-ui-url"
    )

    # 2. External controller & secret: Keep from profile unless explicitly opened in FlClash
    old_ext = """  rawConfig['external-controller'] =
      data.safeMode || realPatchConfig.secret.isEmpty
      ? ''
      : realPatchConfig.externalController.value;
  rawConfig['secret'] = realPatchConfig.secret;"""

    new_ext = """  // [FlClash-Smart] Preserve external-controller and secret from profile if present
  if (realPatchConfig.externalController.value.isNotEmpty) {
    rawConfig['external-controller'] = realPatchConfig.externalController.value;
    if (realPatchConfig.secret.isNotEmpty) {
      rawConfig['secret'] = realPatchConfig.secret;
    }
  } else if (rawConfig['external-controller'] == null) {
    rawConfig['external-controller'] = '';
  }"""
    content = apply_snippet_replacement(content, old_ext, new_ext, "Preserve external-controller & secret")

    # 3. Ports, keep-alive, find-process-mode, and allow-lan:
    old_ports = """  rawConfig['port'] = 0;
  rawConfig['socks-port'] = 0;
  rawConfig['keep-alive-interval'] = realPatchConfig.keepAliveInterval;
  rawConfig['keep-alive-idle'] = realPatchConfig.keepAliveIdle;
  rawConfig['disable-keep-alive'] = realPatchConfig.disableKeepAlive;
  rawConfig['routing-mark'] = realPatchConfig.routingMark;
  rawConfig['mixed-port'] = realPatchConfig.mixedPort;
  rawConfig['port'] = realPatchConfig.port;
  rawConfig['socks-port'] = realPatchConfig.socksPort;
  rawConfig['redir-port'] = realPatchConfig.redirPort;
  rawConfig['tproxy-port'] = realPatchConfig.tproxyPort;
  rawConfig['find-process-mode'] = realPatchConfig.findProcessMode.name;
  rawConfig['allow-lan'] = realPatchConfig.allowLan;"""

    new_ports = """  // [FlClash-Smart] Preserve profile ports; only override if explicitly set (> 0)
  if (realPatchConfig.port > 0) rawConfig['port'] = realPatchConfig.port;
  if (realPatchConfig.socksPort > 0) rawConfig['socks-port'] = realPatchConfig.socksPort;
  if (realPatchConfig.redirPort > 0) rawConfig['redir-port'] = realPatchConfig.redirPort;
  if (realPatchConfig.tproxyPort > 0) rawConfig['tproxy-port'] = realPatchConfig.tproxyPort;
  if (realPatchConfig.mixedPort > 0) {
    if (rawConfig['mixed-port'] == null && rawConfig['port'] == null && rawConfig['socks-port'] == null) {
      rawConfig['mixed-port'] = realPatchConfig.mixedPort;
    } else if (realPatchConfig.mixedPort != defaultMixedPort) {
      rawConfig['mixed-port'] = realPatchConfig.mixedPort;
    }
  }
  if (rawConfig['keep-alive-interval'] == null) rawConfig['keep-alive-interval'] = realPatchConfig.keepAliveInterval;
  if (rawConfig['keep-alive-idle'] == null) rawConfig['keep-alive-idle'] = realPatchConfig.keepAliveIdle;
  if (rawConfig['disable-keep-alive'] == null) rawConfig['disable-keep-alive'] = realPatchConfig.disableKeepAlive;
  if (realPatchConfig.routingMark != 0) rawConfig['routing-mark'] = realPatchConfig.routingMark;
  if (realPatchConfig.findProcessMode != FindProcessMode.off) {
    rawConfig['find-process-mode'] = realPatchConfig.findProcessMode.name;
  } else if (rawConfig['find-process-mode'] == null) {
    rawConfig['find-process-mode'] = realPatchConfig.findProcessMode.name;
  }
  // [FlClash-Smart] Preserve allow-lan from profile if not explicitly enabled in FlClash
  if (realPatchConfig.allowLan) {
    rawConfig['allow-lan'] = true;
  } else if (rawConfig['allow-lan'] == null) {
    rawConfig['allow-lan'] = false;
  }"""
    content = apply_snippet_replacement(content, old_ports, new_ports, "Preserve profile ports and allow-lan")

    # 4. store-selected & geox-url:
    old_geo = """  rawConfig['profile']['store-selected'] = false;
  rawConfig['geox-url'] = realPatchConfig.geoXUrl.raw;"""

    new_geo = """  // [FlClash-Smart] Preserve store-selected and geox-url from profile
  if (rawConfig['profile']?['store-selected'] == null) {
    rawConfig['profile']['store-selected'] = false;
  }
  if (rawConfig['geox-url'] == null ||
      (rawConfig['geox-url'] is Map && (rawConfig['geox-url'] as Map).isEmpty)) {
    rawConfig['geox-url'] = realPatchConfig.geoXUrl.raw;
  }"""
    content = apply_snippet_replacement(content, old_geo, new_geo, "Preserve geox-url & store-selected")

    # 5. geo-auto-update & interval:
    old_geo_update = """  rawConfig['geo-auto-update'] = realPatchConfig.geoAutoUpdate;
  rawConfig['geo-update-interval'] = realPatchConfig.geoUpdateInterval;"""

    new_geo_update = """  if (rawConfig['geo-auto-update'] == null) {
    rawConfig['geo-auto-update'] = realPatchConfig.geoAutoUpdate;
  }
  if (rawConfig['geo-update-interval'] == null) {
    rawConfig['geo-update-interval'] = realPatchConfig.geoUpdateInterval;
  }"""
    content = apply_snippet_replacement(content, old_geo_update, new_geo_update, "Preserve geo-auto-update")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_clash_config_dart(src_dir: str):
    path = os.path.join(src_dir, "lib", "models", "clash_config.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # In toUpdateParams, only send non-empty geoXUrl if customized (not equal to defaultGeoXUrl)
    old_line = "geoXUrl: geoXUrl.raw,"
    new_line = "geoXUrl: const MapEquality().equals(geoXUrl, defaultGeoXUrl) ? const <String, String>{} : geoXUrl.raw,"
    content = apply_snippet_replacement(content, old_line, new_line, "Non-intrusive runtime geoXUrl update")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_port_form_dart(src_dir: str):
    path = os.path.join(src_dir, "lib", "views", "config", "general", "port_form.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    old_snippet = """      _PortField(
        controller: _mixedPortController,
        label: (appLocalizations) => appLocalizations.mixedPort,
        allowDisabled: false,
      ),"""

    new_snippet = """      _PortField(
        controller: _mixedPortController,
        label: (appLocalizations) => appLocalizations.mixedPort,
        allowDisabled: true,
      ),"""
    content = apply_snippet_replacement(content, old_snippet, new_snippet, "Allow disabled mixed port in UI")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    target_repo = sys.argv[2] if len(sys.argv) > 2 else "refined-fish/FlClash-Smart"

    print(f"[+] Patching FlClash sources in: {src_dir} (target repo: {target_repo})")
    patch_constant_dart(src_dir, target_repo)
    patch_make_config_yaml(src_dir, target_repo)
    patch_task_dart(src_dir)
    patch_clash_config_dart(src_dir)
    patch_port_form_dart(src_dir)
    print("[+] Source patching complete!")

if __name__ == "__main__":
    main()
