#!/usr/bin/env python3
"""
Source patcher for FlClash-Smart.
Customizes upstream chen08209/FlClash source code:
1. Updates update repository URL to refined-fish/FlClash-Smart.
2. Updates publisher URL and publisher name in Windows packaging config.
3. Updates default configurations:
   - System proxy defaults to false (VPN and Network).
   - Only statistics proxy defaults to true.
   - Open logs (log capture) defaults to true.
   - Geo auto update defaults to true.
   - Default GeoX URLs prepended with acceleration proxy (https://v6.gh-proxy.org/).
   - Defines defaultSmartModelUrl with acceleration proxy.
   - External controller secret is preserved and never automatically wiped on close.
4. Adds TriOption and generalOverrideKeys (allowLan, geoXUrl) to enums.
5. Adds smartModelUrl to Preferences and runningAllowLan to GlobalState.
6. Decouples invasive configuration overrides in lib/common/task.dart:
   - Preserves profile external-ui and external-ui-url.
   - Preserves profile external-controller & secret unless explicitly opened in FlClash.
   - Preserves profile ports; only overrides if explicitly set (> 0).
   - Preserves profile allow-lan; only overrides if allowLan is in generalOverrideKeys.
   - Preserves profile geox-url and lgbm-url; only overrides if geoXUrl is in generalOverrideKeys.
   - Reports actual running allow-lan state back to main isolate.
   - Preserves profile geo-auto-update and store-selected.
7. Supports "不修改" (Do not modify) in UI:
   - Port settings UI displays "不修改" when 0.
   - LAN proxy displays tri-state options ("不修改" / "开启" / "关闭") in General settings and Dashboard.
   - Dashboard Intranet IP card displays actual running status and has a WebUI launcher button.
   - External controller secret item is always accessible and displays "不修改" when empty.
   - External controller toggle indicates "不修改 (跟随配置)" when closed.
8. Resources View enhancements:
   - Adds "覆写资源链接" (Override Resource URLs) toggle, defaulting to OFF (不修改).
   - Adds "Smart" section with "MODEL" resource (lgbm-url, Model.bin) allowing editing and syncing.
   - Hooks into updateAll() to update Smart MODEL alongside Geo resources.
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

def patch_defaults(src_dir: str):
    # 1. lib/models/config.dart (systemProxy, onlyStatisticsProxy, openLogs)
    config_path = os.path.join(src_dir, "lib", "models", "config.dart")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        # VpnProps systemProxy
        content = apply_snippet_replacement(
            content,
            "@Default(true) bool systemProxy,\n    @Default(false) bool ipv6,",
            "@Default(false) bool systemProxy,\n    @Default(false) bool ipv6,",
            "Default systemProxy=false in VpnProps"
        )
        # NetworkProps systemProxy
        content = apply_snippet_replacement(
            content,
            "@Default(true) bool systemProxy,\n    @Default(defaultBypassDomain)",
            "@Default(false) bool systemProxy,\n    @Default(defaultBypassDomain)",
            "Default systemProxy=false in NetworkProps"
        )
        # onlyStatisticsProxy
        content = apply_snippet_replacement(
            content,
            "@Default(false) bool onlyStatisticsProxy,",
            "@Default(true) bool onlyStatisticsProxy,",
            "Default onlyStatisticsProxy=true in AppSettingProps"
        )
        # openLogs
        content = apply_snippet_replacement(
            content,
            "@Default(false) bool openLogs,",
            "@Default(true) bool openLogs,",
            "Default openLogs=true in AppSettingProps"
        )
        with open(config_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 2. lib/models/generated/config.freezed.dart
    config_freezed_path = os.path.join(src_dir, "lib", "models", "generated", "config.freezed.dart")
    if os.path.exists(config_freezed_path):
        with open(config_freezed_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        content = content.replace("this.systemProxy = true, this.ipv6", "this.systemProxy = false, this.ipv6")
        content = content.replace("this.systemProxy = true,  List<String> bypassDomain", "this.systemProxy = false,  List<String> bypassDomain")
        content = content.replace("this.onlyStatisticsProxy = false,", "this.onlyStatisticsProxy = true,")
        content = content.replace("this.openLogs = false,", "this.openLogs = true,")
        with open(config_freezed_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print("[+] Patched config.freezed.dart defaults")

    # 3. lib/models/generated/config.g.dart
    config_g_path = os.path.join(src_dir, "lib", "models", "generated", "config.g.dart")
    if os.path.exists(config_g_path):
        with open(config_g_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        content = content.replace("json['systemProxy'] as bool? ?? true", "json['systemProxy'] as bool? ?? false")
        content = content.replace("json['onlyStatisticsProxy'] as bool? ?? false", "json['onlyStatisticsProxy'] as bool? ?? true")
        content = content.replace("json['openLogs'] as bool? ?? false", "json['openLogs'] as bool? ?? true")
        with open(config_g_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print("[+] Patched config.g.dart defaults")

    # 4. lib/models/clash_config.dart
    clash_config_path = os.path.join(src_dir, "lib", "models", "clash_config.dart")
    if os.path.exists(clash_config_path):
        with open(clash_config_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        # Update defaultGeoXUrl with gh-proxy and add defaultSmartModelUrl
        old_geo = """const defaultGeoXUrl = {
  GeoResource.MMDB:
      'https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.metadb',
  GeoResource.ASN:
      'https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/GeoLite2-ASN.mmdb',
  GeoResource.GEOIP:
      'https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.dat',
  GeoResource.GEOSITE:
      'https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat',
};"""

        new_geo = """const defaultGeoXUrl = {
  GeoResource.MMDB:
      'https://v6.gh-proxy.org/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.metadb',
  GeoResource.ASN:
      'https://v6.gh-proxy.org/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/GeoLite2-ASN.mmdb',
  GeoResource.GEOIP:
      'https://v6.gh-proxy.org/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.dat',
  GeoResource.GEOSITE:
      'https://v6.gh-proxy.org/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat',
};

const defaultSmartModelUrl =
    'https://v6.gh-proxy.org/https://github.com/vernesong/mihomo/releases/download/LightGBM-Model/Model.bin';"""
        content = apply_snippet_replacement(content, old_geo, new_geo, "defaultGeoXUrl with proxy & defaultSmartModelUrl")

        # geoAutoUpdate default to true
        content = apply_snippet_replacement(
            content,
            "@Default(false) @JsonKey(name: 'geo-auto-update') bool geoAutoUpdate,",
            "@Default(true) @JsonKey(name: 'geo-auto-update') bool geoAutoUpdate,",
            "Default geoAutoUpdate=true in PatchClashConfig"
        )

        # ensureControllerSecret: do not wipe secret when controller is closed
        old_secret_fn = """  PatchClashConfig ensureControllerSecret() {
    if (externalController == ExternalControllerStatus.close) {
      return secret.isEmpty ? this : copyWith(secret: '');
    }
    return secret.isEmpty ? copyWith(secret: generateRandomSecret(32)) : this;
  }"""
        new_secret_fn = """  PatchClashConfig ensureControllerSecret() {
    if (externalController != ExternalControllerStatus.close && secret.isEmpty) {
      return copyWith(secret: generateRandomSecret(32));
    }
    return this;
  }"""
        content = apply_snippet_replacement(content, old_secret_fn, new_secret_fn, "Preserve secret on controller close")

        # toUpdateParams: only send geoXUrl if geoXUrl override is explicitly enabled
        old_to_update = "geoXUrl: geoXUrl.raw,"
        new_to_update = "geoXUrl: generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl) ? geoXUrl.raw : const <String, String>{},"
        content = apply_snippet_replacement(content, old_to_update, new_to_update, "toUpdateParams geoXUrl conditional override")

        with open(clash_config_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 5. lib/models/generated/clash_config.freezed.dart
    clash_freezed_path = os.path.join(src_dir, "lib", "models", "generated", "clash_config.freezed.dart")
    if os.path.exists(clash_freezed_path):
        with open(clash_freezed_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        content = content.replace("@JsonKey(name: 'geo-auto-update') this.geoAutoUpdate = false,",
                                  "@JsonKey(name: 'geo-auto-update') this.geoAutoUpdate = true,")
        with open(clash_freezed_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print("[+] Patched clash_config.freezed.dart defaults")

    # 6. lib/models/generated/clash_config.g.dart
    clash_g_path = os.path.join(src_dir, "lib", "models", "generated", "clash_config.g.dart")
    if os.path.exists(clash_g_path):
        with open(clash_g_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        content = content.replace("geoAutoUpdate: json['geo-auto-update'] as bool? ?? false,",
                                  "geoAutoUpdate: json['geo-auto-update'] as bool? ?? true,")
        with open(clash_g_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        print("[+] Patched clash_config.g.dart defaults")

def patch_enum_dart(src_dir: str):
    path = os.path.join(src_dir, "lib", "enum", "enum.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    old_enum = """enum GeneralOverrideKey with OverrideKey {
  testUrl('test-url'),
  unifiedDelay('unified-delay'),
  tcpConcurrent('tcp-concurrent'),
  ipv6('ipv6'),
  geodataLoader('geodata-loader');

  const GeneralOverrideKey(this.path);

  @override
  final String path;
}"""

    new_enum = """enum GeneralOverrideKey with OverrideKey {
  testUrl('test-url'),
  unifiedDelay('unified-delay'),
  tcpConcurrent('tcp-concurrent'),
  ipv6('ipv6'),
  geodataLoader('geodata-loader'),
  allowLan('allow-lan'),
  geoXUrl('geox-url');

  const GeneralOverrideKey(this.path);

  @override
  final String path;
}

enum TriOption {
  keep,
  enable,
  disable;
}"""
    content = apply_snippet_replacement(content, old_enum, new_enum, "Extend GeneralOverrideKey & add TriOption")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

    # Also update lib/views/config/general/overrides.dart switch exhaustiveness
    overrides_path = os.path.join(src_dir, "lib", "views", "config", "general", "overrides.dart")
    if os.path.exists(overrides_path):
        with open(overrides_path, "r", encoding="utf-8", newline="") as f:
            ov_content = f.read()
        old_label = """extension on GeneralOverrideKey {
  String label(AppLocalizations l) => switch (this) {
    GeneralOverrideKey.testUrl => l.testUrl,
    GeneralOverrideKey.unifiedDelay => l.unifiedDelay,
    GeneralOverrideKey.tcpConcurrent => l.tcpConcurrent,
    GeneralOverrideKey.ipv6 => 'IPv6',
    GeneralOverrideKey.geodataLoader => l.geodataLoader,
  };
}"""
        new_label = """extension on GeneralOverrideKey {
  String label(AppLocalizations l) => switch (this) {
    GeneralOverrideKey.testUrl => l.testUrl,
    GeneralOverrideKey.unifiedDelay => l.unifiedDelay,
    GeneralOverrideKey.tcpConcurrent => l.tcpConcurrent,
    GeneralOverrideKey.ipv6 => 'IPv6',
    GeneralOverrideKey.geodataLoader => l.geodataLoader,
    GeneralOverrideKey.allowLan => l.allowLan,
    GeneralOverrideKey.geoXUrl => l.geoResources,
  };
}"""
        ov_content = apply_snippet_replacement(ov_content, old_label, new_label, "GeneralOverrideKey label exhaustiveness")
        with open(overrides_path, "w", encoding="utf-8", newline="") as f:
            f.write(ov_content)

def patch_preferences_and_state(src_dir: str):
    # 1. Preferences
    pref_path = os.path.join(src_dir, "lib", "common", "preferences.dart")
    if os.path.exists(pref_path):
        with open(pref_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        old_pref_tail = "  Preferences._internal();"
        new_pref_tail = """  Preferences._internal();

  Future<String> getSmartModelUrl() async {
    final preferences = await _store.value;
    return preferences?.getString('smartModelUrl') ?? defaultSmartModelUrl;
  }

  Future<void> setSmartModelUrl(String url) async {
    final preferences = await _store.value;
    await preferences?.setString('smartModelUrl', url);
  }"""
        content = apply_snippet_replacement(content, old_pref_tail, new_pref_tail, "Preferences smartModelUrl methods")
        with open(pref_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 2. GlobalState
    state_path = os.path.join(src_dir, "lib", "state.dart")
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        old_state = "  bool isAttach = false;"
        new_state = """  bool isAttach = false;
  final ValueNotifier<bool?> runningAllowLan = ValueNotifier<bool?>(null);"""
        content = apply_snippet_replacement(content, old_state, new_state, "GlobalState runningAllowLan notifier")
        with open(state_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

def patch_task_dart(src_dir: str):
    path = os.path.join(src_dir, "lib", "common", "task.dart")
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    print(f"[*] Patching non-intrusive config logic in {path}...")

    # RealProfile record definition: add allowLan
    content = apply_snippet_replacement(
        content,
        "typedef RealProfile = ({String yaml, String md5, ConfigCounts counts});",
        "typedef RealProfile = ({String yaml, String md5, ConfigCounts counts, bool allowLan});",
        "RealProfile definition with allowLan"
    )

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
  // [FlClash-Smart] Preserve allow-lan from profile unless explicitly overridden in FlClash
  if (realPatchConfig.generalOverrideKeys.contains(GeneralOverrideKey.allowLan)) {
    rawConfig['allow-lan'] = realPatchConfig.allowLan;
  }"""
    content = apply_snippet_replacement(content, old_ports, new_ports, "Preserve profile ports and allow-lan")

    # 4. store-selected, geox-url and lgbm-url:
    old_geo = """  rawConfig['profile']['store-selected'] = false;
  rawConfig['geox-url'] = realPatchConfig.geoXUrl.raw;"""

    new_geo = """  // [FlClash-Smart] Preserve store-selected, geox-url, and lgbm-url from profile
  if (rawConfig['profile']?['store-selected'] == null) {
    rawConfig['profile']['store-selected'] = false;
  }
  if (realPatchConfig.generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl)) {
    rawConfig['geox-url'] = realPatchConfig.geoXUrl.raw;
    rawConfig['lgbm-url'] = defaultSmartModelUrl;
  } else {
    if (rawConfig['geox-url'] == null ||
        (rawConfig['geox-url'] is Map && (rawConfig['geox-url'] as Map).isEmpty)) {
      rawConfig['geox-url'] = realPatchConfig.geoXUrl.raw;
    }
    if (rawConfig['lgbm-url'] == null ||
        (rawConfig['lgbm-url'] is String && (rawConfig['lgbm-url'] as String).isEmpty)) {
      rawConfig['lgbm-url'] = defaultSmartModelUrl;
    }
  }"""
    content = apply_snippet_replacement(content, old_geo, new_geo, "Preserve geox-url & lgbm-url")

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

    # 6. Return allowLan in _makeRealProfileTask
    old_return = """  final yaml = await _encodeYaml(Map<String, dynamic>.from(rawConfig));
  return (yaml: yaml, md5: yaml.toMd5(), counts: configCountsOf(rawConfig));"""

    new_return = """  final yaml = await _encodeYaml(Map<String, dynamic>.from(rawConfig));
  return (
    yaml: yaml,
    md5: yaml.toMd5(),
    counts: configCountsOf(rawConfig),
    allowLan: rawConfig['allow-lan'] == true,
  );"""
    content = apply_snippet_replacement(content, old_return, new_return, "Return allowLan in RealProfile")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_setup_dart(src_dir: str):
    path = os.path.join(src_dir, "lib", "providers", "actions", "setup.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    old_snippet = "    if (profileBase == null) {"
    new_snippet = "    globalState.runningAllowLan.value = res.allowLan;\n    if (profileBase == null) {"
    content = apply_snippet_replacement(content, old_snippet, new_snippet, "Update globalState.runningAllowLan in getProfile")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_widgets_config_item(src_dir: str):
    path = os.path.join(src_dir, "lib", "widgets", "config_item.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # Allow ConfigToggleItem to render subtitle
    old_toggle = """  @override
  Widget buildItem(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations appLocalizations,
    bool value,
  ) {
    return ListItem.toggle(
      leading: leading,
      title: Text(title(appLocalizations)),
      value: value,
      onChanged: (value) => onChanged(ref, value),
    );
  }"""

    new_toggle = """  @override
  Widget buildItem(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations appLocalizations,
    bool value,
  ) {
    return ListItem.toggle(
      leading: leading,
      title: Text(title(appLocalizations)),
      subtitle: buildSubtitle(appLocalizations),
      value: value,
      onChanged: (value) => onChanged(ref, value),
    );
  }"""
    content = apply_snippet_replacement(content, old_toggle, new_toggle, "ConfigToggleItem subtitle support")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_general_views(src_dir: str):
    # 1. port_form.dart
    port_form_path = os.path.join(src_dir, "lib", "views", "config", "general", "port_form.dart")
    if os.path.exists(port_form_path):
        with open(port_form_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        # Allow disabled mixedPort
        content = apply_snippet_replacement(
            content,
            """      _PortField(
        controller: _mixedPortController,
        label: (appLocalizations) => appLocalizations.mixedPort,
        allowDisabled: false,
      ),""",
            """      _PortField(
        controller: _mixedPortController,
        label: (appLocalizations) => appLocalizations.mixedPort,
        allowDisabled: true,
      ),""",
            "Allow disabled mixed port"
        )

        # Show (不修改) when port is 0 in FormRow
        old_form_row = "title: field.label(appLocalizations),"
        new_form_row = "title: field.controller.text == '0' ? '${field.label(appLocalizations)} (不修改)' : field.label(appLocalizations),"
        content = apply_snippet_replacement(content, old_form_row, new_form_row, "Show (不修改) when port is 0 in form")

        with open(port_form_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 2. general.dart
    general_path = os.path.join(src_dir, "lib", "views", "config", "general.dart")
    if os.path.exists(general_path):
        with open(general_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        # PortItem displays '不修改' when mixedPort == 0
        old_port_item = """    final mixedPort = ref.watch(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    return ListItem(
      title: Text(appLocalizations.port),
      subtitle: Text('$mixedPort'),
      onTap: () {
        handleShowPortForm(context);
      },
    );"""

        new_port_item = """    final mixedPort = ref.watch(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    return ListItem(
      title: Text(appLocalizations.port),
      subtitle: Text(mixedPort == 0 ? '不修改' : '$mixedPort'),
      onTap: () {
        handleShowPortForm(context);
      },
    );"""
        content = apply_snippet_replacement(content, old_port_item, new_port_item, "PortItem show 不修改")

        # AllowLanItem definition
        allow_lan_item_class = """class AllowLanItem extends ConsumerWidget {
  const AllowLanItem({super.key});

  @override
  Widget build(BuildContext context, ref) {
    return ConfigOptionsItem<TriOption>(
      title: (l) => l.allowLan,
      options: TriOption.values,
      textBuilder: (option) => switch (option) {
        TriOption.keep => '不修改',
        TriOption.enable => '开启',
        TriOption.disable => '关闭',
      },
      selector: patchClashConfigProvider.select((state) {
        if (!state.generalOverrideKeys.contains(GeneralOverrideKey.allowLan)) {
          return TriOption.keep;
        }
        return state.allowLan ? TriOption.enable : TriOption.disable;
      }),
      onChanged: (ref, value) => ref
          .read(patchClashConfigProvider.notifier)
          .update((state) {
            final keys = Set<GeneralOverrideKey>.from(state.generalOverrideKeys);
            if (value == TriOption.keep) {
              keys.remove(GeneralOverrideKey.allowLan);
              return state.copyWith(generalOverrideKeys: keys);
            } else {
              keys.add(GeneralOverrideKey.allowLan);
              return state.copyWith(
                generalOverrideKeys: keys,
                allowLan: value == TriOption.enable,
              );
            }
          }),
    );
  }
}
"""
        content = apply_snippet_replacement(
            content,
            "class ExternalControllerSecretItem extends ConsumerWidget {",
            allow_lan_item_class + "\nclass ExternalControllerSecretItem extends ConsumerWidget {",
            "Add AllowLanItem class"
        )

        # ExternalControllerSecretItem show '不修改' when secret is empty
        old_secret_item = """class ExternalControllerSecretItem extends ConsumerWidget {
  const ExternalControllerSecretItem({super.key});

  @override
  Widget build(BuildContext context, ref) {
    return ConfigTextItem(
      title: (l) => l.externalControllerSecret,
      maxLength: TextInputLimits.password,
      selector: patchClashConfigProvider.select((state) => state.secret),
      normalize: (value) => value.trim(),
      onChanged: (ref, value) => ref
          .read(patchClashConfigProvider.notifier)
          .update((state) => state.copyWith(secret: value)),
    );
  }
}"""

        new_secret_item = """class ExternalControllerSecretItem extends ConsumerWidget {
  const ExternalControllerSecretItem({super.key});

  @override
  Widget build(BuildContext context, ref) {
    final secret = ref.watch(
      patchClashConfigProvider.select((state) => state.secret),
    );
    return ConfigTextItem(
      title: (l) => l.externalControllerSecret,
      subtitle: (_) => secret.isEmpty ? '不修改' : secret,
      maxLength: TextInputLimits.password,
      selector: patchClashConfigProvider.select((state) => state.secret),
      normalize: (value) => value.trim(),
      onChanged: (ref, value) => ref
          .read(patchClashConfigProvider.notifier)
          .update((state) => state.copyWith(secret: value)),
    );
  }
}"""
        content = apply_snippet_replacement(content, old_secret_item, new_secret_item, "ExternalControllerSecretItem subtitle")

        # Replace _clashToggle allowLan with AllowLanItem, externalController subtitle, unhide secret
        old_inbound = """      const PortItem(),
      _clashToggle(
        title: (l) => l.allowLan,
        select: (state) => state.allowLan,
        update: (state, value) => state.copyWith(allowLan: value),
      ),
      _clashToggle(
        title: (l) => l.externalController,
        select: (state) =>
            state.externalController == ExternalControllerStatus.open,
        update: (state, value) => state
            .copyWith(
              externalController: value
                  ? ExternalControllerStatus.open
                  : ExternalControllerStatus.close,
            )
            .ensureControllerSecret(),
      ),
      if (externalController) const ExternalControllerSecretItem(),"""

        new_inbound = """      const PortItem(),
      const AllowLanItem(),
      _clashToggle(
        title: (l) => l.externalController,
        subtitle: (l) =>
            externalController ? '开启 (127.0.0.1:9090)' : '不修改 (跟随配置)',
        select: (state) =>
            state.externalController == ExternalControllerStatus.open,
        update: (state, value) => state
            .copyWith(
              externalController: value
                  ? ExternalControllerStatus.open
                  : ExternalControllerStatus.close,
            )
            .ensureControllerSecret(),
      ),
      const ExternalControllerSecretItem(),"""
        content = apply_snippet_replacement(content, old_inbound, new_inbound, "Update _inboundItems in general.dart")

        # Update _clashToggle definition to support subtitle
        old_clash_toggle = """ConfigToggleItem _clashToggle({
  required ConfigLabel title,
  required bool Function(PatchClashConfig state) select,
  required PatchClashConfig Function(PatchClashConfig state, bool value) update,
}) {
  return ConfigToggleItem(
    title: title,
    selector: patchClashConfigProvider.select(select),
    onChanged: (ref, value) => ref
        .read(patchClashConfigProvider.notifier)
        .update((state) => update(state, value)),
  );
}"""

        new_clash_toggle = """ConfigToggleItem _clashToggle({
  required ConfigLabel title,
  ConfigLabel? subtitle,
  required bool Function(PatchClashConfig state) select,
  required PatchClashConfig Function(PatchClashConfig state, bool value) update,
}) {
  return ConfigToggleItem(
    title: title,
    subtitle: subtitle,
    selector: patchClashConfigProvider.select(select),
    onChanged: (ref, value) => ref
        .read(patchClashConfigProvider.notifier)
        .update((state) => update(state, value)),
  );
}"""
        content = apply_snippet_replacement(content, old_clash_toggle, new_clash_toggle, "_clashToggle subtitle support")

        with open(general_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

def patch_dashboard_intranet_ip(src_dir: str):
    path = os.path.join(src_dir, "lib", "views", "dashboard", "widgets", "intranet_ip.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # Import url_launcher if not present
    if "package:url_launcher/url_launcher.dart" not in content:
        content = "import 'package:url_launcher/url_launcher.dart';\n" + content

    old_body = """    final localIp = ref.watch(localIpProvider);
    final allowLan = ref.watch(
      patchClashConfigProvider.select((state) => state.allowLan),
    );
    final port = ref.watch(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    final figure = mobile
        ? (style: AppTextStyle.title1, top: 12.0)
        : density.isCompact
        ? (style: AppTextStyle.title2, top: 8.0)
        : (style: AppTextStyle.title2, top: 10.0);
    final _LanRowMetrics row = density.isCompact
        ? (
            padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
            titleStart: 12,
            radius: 16,
            icon: 32,
          )
        : (
            padding: const EdgeInsets.fromLTRB(10, 10, 12, 10),
            titleStart: 14,
            radius: 20,
            icon: 38,
          );
    final style = DashboardText.figure(
      context,
      figure.style,
    ).copyWith(letterSpacing: 0);
    final address = localIp == null || localIp.isEmpty
        ? null
        : allowLan
        ? '$localIp:$port'
        : localIp;
    void change(bool value) => ref
        .read(patchClashConfigProvider.notifier)
        .update((state) => state.copyWith(allowLan: value));
    return DashboardCard(
      semanticLabel: appLocalizations.intranetIP,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: mobile ? MainAxisSize.min : MainAxisSize.max,
        children: [
          DashboardCardHeader(
            glyph: AppGlyphs.devices,
            title: appLocalizations.intranetIP,
            trailing: [
              Transform.translate(
                offset: const Offset(8, 0),
                child: DashboardIconButton(
                  glyph: AppGlyphs.copy,
                  tooltip: appLocalizations.copy,
                  onPressed: address == null
                      ? null
                      : () => copyToClipboard(context, address),
                ),
              ),
            ],
          ),
          SizedBox(height: figure.top),
          SizedBox(
            height: figure.style.leading * scale,
            child: Align(
              alignment: AlignmentDirectional.centerStart,
              child: switch (localIp) {
                null => SkeletonText(width: 120, style: style),
                '' => Text(
                  appLocalizations.noNetwork,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: style.copyWith(color: colorScheme.onSurfaceVariant),
                ),
                final ip => DashboardFitText(ip, style: style),
              },
            ),
          ),
          if (mobile) const SizedBox(height: 14) else const Spacer(),
          LayoutBuilder(
            builder: (context, constraints) {
              final title = appLocalizations.allowLan;
              final showIcon = DashboardSwitchRow.iconFits(
                context,
                width: constraints.maxWidth,
                iconSize: row.icon,
                padding: row.padding,
                titles: [title],
              );
              return DashboardSwitchRow(
                glyph: AppGlyphs.wifi,
                title: title,
                subtitle: allowLan
                    ? appLocalizations.portValue(port)
                    : appLocalizations.disabled,
                value: allowLan,
                iconSize: row.icon,
                padding: showIcon
                    ? row.padding
                    : row.padding.copyWith(left: row.titleStart),
                radius: row.radius,
                showIcon: showIcon,
                onTap: () => change(!allowLan),
                onChanged: change,
              );
            },
          ),
        ],
      ),
    );"""

    new_body = """    final localIp = ref.watch(localIpProvider);
    final isAllowLanOverridden = ref.watch(
      patchClashConfigProvider.select(
        (state) => state.generalOverrideKeys.contains(GeneralOverrideKey.allowLan),
      ),
    );
    final allowLan = ref.watch(
      patchClashConfigProvider.select((state) => state.allowLan),
    );
    final allowLanMode = !isAllowLanOverridden
        ? TriOption.keep
        : (allowLan ? TriOption.enable : TriOption.disable);
    final port = ref.watch(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    final actualRunning = globalState.runningAllowLan.value ?? (isAllowLanOverridden ? allowLan : false);
    final figure = mobile
        ? (style: AppTextStyle.title1, top: 12.0)
        : density.isCompact
        ? (style: AppTextStyle.title2, top: 8.0)
        : (style: AppTextStyle.title2, top: 10.0);
    final _LanRowMetrics row = density.isCompact
        ? (
            padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
            titleStart: 12,
            radius: 16,
            icon: 32,
          )
        : (
            padding: const EdgeInsets.fromLTRB(10, 10, 12, 10),
            titleStart: 14,
            radius: 20,
            icon: 38,
          );
    final style = DashboardText.figure(
      context,
      figure.style,
    ).copyWith(letterSpacing: 0);
    final effectivePort = port > 0 ? port : 7890;
    final address = localIp == null || localIp.isEmpty
        ? null
        : actualRunning
        ? '$localIp:$effectivePort'
        : localIp;

    Future<void> showAllowLanMenu() async {
      final selected = await showFloatingDialog<TriOption>(
        context: Navigator.of(context, rootNavigator: true).context,
        child: CommonPopupMenu(
          items: [
            CommonPopupMenuItem(
              label: '不修改 (跟随配置)',
              checked: allowLanMode == TriOption.keep,
              onPressed: () {
                Navigator.of(context, rootNavigator: true).pop(TriOption.keep);
              },
            ),
            CommonPopupMenuItem(
              label: '开启',
              checked: allowLanMode == TriOption.enable,
              onPressed: () {
                Navigator.of(context, rootNavigator: true).pop(TriOption.enable);
              },
            ),
            CommonPopupMenuItem(
              label: '关闭',
              checked: allowLanMode == TriOption.disable,
              onPressed: () {
                Navigator.of(context, rootNavigator: true).pop(TriOption.disable);
              },
            ),
          ],
        ),
      );
      if (selected == null) return;
      ref.read(patchClashConfigProvider.notifier).update((state) {
        final keys = Set<GeneralOverrideKey>.from(state.generalOverrideKeys);
        if (selected == TriOption.keep) {
          keys.remove(GeneralOverrideKey.allowLan);
          return state.copyWith(generalOverrideKeys: keys);
        } else {
          keys.add(GeneralOverrideKey.allowLan);
          return state.copyWith(
            generalOverrideKeys: keys,
            allowLan: selected == TriOption.enable,
          );
        }
      });
    }

    return DashboardCard(
      semanticLabel: appLocalizations.intranetIP,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: mobile ? MainAxisSize.min : MainAxisSize.max,
        children: [
          DashboardCardHeader(
            glyph: AppGlyphs.devices,
            title: appLocalizations.intranetIP,
            trailing: [
              DashboardIconButton(
                glyph: AppGlyphs.openExternal,
                tooltip: 'Web 控制面板',
                onPressed: () {
                  final clashConfig = ref.read(patchClashConfigProvider);
                  final ext = clashConfig.externalController.value;
                  final hostPort = ext.isNotEmpty ? ext : '127.0.0.1:9090';
                  final secret = clashConfig.secret;
                  final query = secret.isNotEmpty ? '?secret=${Uri.encodeComponent(secret)}' : '';
                  launchUrl(
                    Uri.parse('http://$hostPort/ui$query'),
                    mode: LaunchMode.externalApplication,
                  );
                },
              ),
              Transform.translate(
                offset: const Offset(8, 0),
                child: DashboardIconButton(
                  glyph: AppGlyphs.copy,
                  tooltip: appLocalizations.copy,
                  onPressed: address == null
                      ? null
                      : () => copyToClipboard(context, address),
                ),
              ),
            ],
          ),
          SizedBox(height: figure.top),
          SizedBox(
            height: figure.style.leading * scale,
            child: Align(
              alignment: AlignmentDirectional.centerStart,
              child: switch (localIp) {
                null => SkeletonText(width: 120, style: style),
                '' => Text(
                  appLocalizations.noNetwork,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: style.copyWith(color: colorScheme.onSurfaceVariant),
                ),
                final ip => DashboardFitText(ip, style: style),
              },
            ),
          ),
          if (mobile) const SizedBox(height: 14) else const Spacer(),
          LayoutBuilder(
            builder: (context, constraints) {
              final title = appLocalizations.allowLan;
              final showIcon = DashboardSwitchRow.iconFits(
                context,
                width: constraints.maxWidth,
                iconSize: row.icon,
                padding: row.padding,
                titles: [title],
              );
              final lanSubtitle = switch (allowLanMode) {
                TriOption.keep => '不修改 (运行: ${actualRunning ? "开启" : "关闭"})',
                TriOption.enable => '开启 (运行: ${actualRunning ? "开启 · $effectivePort" : "未启动"})',
                TriOption.disable => '关闭 (运行: 关闭)',
              };
              return DashboardSwitchRow(
                glyph: AppGlyphs.wifi,
                title: title,
                subtitle: lanSubtitle,
                value: actualRunning,
                iconSize: row.icon,
                padding: showIcon
                    ? row.padding
                    : row.padding.copyWith(left: row.titleStart),
                radius: row.radius,
                showIcon: showIcon,
                onTap: showAllowLanMenu,
                onChanged: (_) => showAllowLanMenu(),
              );
            },
          ),
        ],
      ),
    );"""

    content = apply_snippet_replacement(content, old_body, new_body, "Dashboard IntranetIpCard with WebUI & TriState allowLan")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_resources_view(src_dir: str):
    # 1. lib/views/resources.dart
    res_path = os.path.join(src_dir, "lib", "views", "resources.dart")
    if os.path.exists(res_path):
        with open(res_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        # Update _load to preload smart_model
        content = apply_snippet_replacement(
            content,
            """      for (final type in GeoResource.values)
        type.updatingKey: _geoFileInfo(type),""",
            """      for (final type in GeoResource.values)
        type.updatingKey: _geoFileInfo(type),
      'smart_model': _smartModelFileInfo(),""",
            "Preload smart_model in ResourcesView._load"
        )

        # Update resourceKeys in build
        content = apply_snippet_replacement(
            content,
            """    final resourceKeys = [
      for (final geoResource in GeoResource.values) geoResource.updatingKey,""",
            """    final resourceKeys = [
      for (final geoResource in GeoResource.values) geoResource.updatingKey,
      'smart_model',""",
            "Add smart_model to resourceKeys in ResourcesView"
        )

        # Add "覆写资源链接" switch and "Smart" section
        old_sections = """            generateSection(
              items: [
                ListItem.toggle(
                  title: Text(appLocalizations.autoUpdate),
                  value: autoUpdate,
                  onChanged: _updateAutoUpdate,
                ),
                if (autoUpdate)
                  ListItem(
                    title: Text(appLocalizations.resourceUpdateInterval),
                    subtitle: Text('$updateInterval ${appLocalizations.hours}'),
                    onTap: _updateInterval,
                  ),
              ],
            ),
            generateSection(
              title: appLocalizations.geoResources,
              items: [
                for (final geoResource in GeoResource.values)
                  _GeoResourceItem(geoResource, preloaded: _fileInfos),
              ],
            ),"""

        new_sections = """            generateSection(
              items: [
                ListItem.toggle(
                  title: Text(appLocalizations.autoUpdate),
                  value: autoUpdate,
                  onChanged: _updateAutoUpdate,
                ),
                if (autoUpdate)
                  ListItem(
                    title: Text(appLocalizations.resourceUpdateInterval),
                    subtitle: Text('$updateInterval ${appLocalizations.hours}'),
                    onTap: _updateInterval,
                  ),
                ListItem.toggle(
                  title: const Text('覆写资源链接'),
                  subtitle: const Text('默认关闭（不修改）。开启后将使用下方配置的 URL 覆写订阅中的资源下载链接'),
                  value: ref.watch(
                    patchClashConfigProvider.select(
                      (state) => state.generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl),
                    ),
                  ),
                  onChanged: (value) {
                    ref.read(patchClashConfigProvider.notifier).update((state) {
                      final keys = Set<GeneralOverrideKey>.from(state.generalOverrideKeys);
                      if (value) {
                        keys.add(GeneralOverrideKey.geoXUrl);
                      } else {
                        keys.remove(GeneralOverrideKey.geoXUrl);
                      }
                      return state.copyWith(generalOverrideKeys: keys);
                    });
                  },
                ),
              ],
            ),
            generateSection(
              title: appLocalizations.geoResources,
              items: [
                for (final geoResource in GeoResource.values)
                  _GeoResourceItem(geoResource, preloaded: _fileInfos),
              ],
            ),
            generateSection(
              title: 'Smart',
              items: [
                _SmartModelResourceItem(preloaded: _fileInfos),
              ],
            ),"""
        content = apply_snippet_replacement(content, old_sections, new_sections, "ResourcesView override switch and Smart section")

        # Add helper function _smartModelFileInfo and class _SmartModelResourceItem
        smart_item_code = """
Future<FileInfo?> _smartModelFileInfo() async {
  final homePath = await appPath.homeDirPath;
  return File(join(homePath, 'Model.bin')).getFileInfo();
}

class _SmartModelResourceItem extends ConsumerStatefulWidget {
  final Map<String, FileInfo?> preloaded;

  const _SmartModelResourceItem({required this.preloaded});

  @override
  ConsumerState<_SmartModelResourceItem> createState() => _SmartModelResourceItemState();
}

class _SmartModelResourceItemState extends ConsumerState<_SmartModelResourceItem> {
  String? _url;

  @override
  void initState() {
    super.initState();
    _loadUrl();
  }

  Future<void> _loadUrl() async {
    final url = await preferences.getSmartModelUrl();
    if (mounted) setState(() => _url = url);
  }

  Future<void> _updateUrl(BuildContext context) async {
    final currentUrl = _url ?? defaultSmartModelUrl;
    final newUrl = await dialogs.showCommonDialog<String>(
      child: UpdateGeoUrlFormDialog(
        title: 'MODEL',
        url: currentUrl,
        defaultValue: defaultSmartModelUrl,
      ),
    );
    if (newUrl != null && newUrl != currentUrl && mounted) {
      await preferences.setSmartModelUrl(newUrl);
      setState(() => _url = newUrl);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isUpdating = ref.watch(isUpdatingProvider('smart_model'));
    final url = _url ?? defaultSmartModelUrl;
    return _FileInfoBuilder(
      source: 'smart_model',
      updatingKey: 'smart_model',
      preloaded: widget.preloaded,
      load: () => _smartModelFileInfo(),
      builder: (context, fileInfo, pending) => _ResourceItem(
        title: 'MODEL',
        url: url,
        chip: fileInfo?.size.traffic.show,
        lastUpdateTime: fileInfo?.lastModified,
        pending: pending,
        isUpdating: isUpdating,
        onSync: () => ref.read(resourcesActionProvider.notifier).updateSmartModel(),
        onEdit: () => _updateUrl(context),
      ),
    );
  }
}
"""
        content += smart_item_code

        with open(res_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 2. lib/providers/actions/resources.dart
    res_action_path = os.path.join(src_dir, "lib", "providers", "actions", "resources.dart")
    if os.path.exists(res_action_path):
        with open(res_action_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        smart_download_fn = """  Future<void> updateSmartModel() async {
    final updatingKeys = ref.read(updatingKeysProvider.notifier);
    final op = updatingKeys.start('smart_model');
    try {
      final url = await preferences.getSmartModelUrl();
      final homePath = await appPath.homeDirPath;
      final targetFile = File(join(homePath, 'Model.bin'));
      final tmpFile = File(join(homePath, 'Model.bin.download'));

      final client = HttpClient();
      final request = await client.getUrl(Uri.parse(url));
      final response = await request.close();
      if (response.statusCode != 200) {
        throw Exception('HTTP ${response.statusCode}');
      }
      final sink = tmpFile.openWrite();
      await response.pipe(sink);
      client.close();

      if (await targetFile.exists()) {
        await targetFile.delete();
      }
      await tmpFile.rename(targetFile.path);
      dialogs.showNotifier('MODEL 更新成功');
    } catch (e) {
      dialogs.showNotifier('MODEL 更新失败: $e', level: MessageLevel.error);
      rethrow;
    } finally {
      updatingKeys.stop('smart_model', op);
    }
  }

  Future<void> updateIconSet(IconSet iconSet) {"""

        content = apply_snippet_replacement(
            content,
            "  Future<void> updateIconSet(IconSet iconSet) {",
            smart_download_fn,
            "Add updateSmartModel method"
        )

        old_update_all = """      for (final geoResource in GeoResource.values)
        update(
          geoResource.updatingKey,
          geoResource.name,
          () => geoResourceAction.updateGeoResource(
            geoResource,
            announceSuccess: false,
          ),
        ),"""

        new_update_all = """      for (final geoResource in GeoResource.values)
        update(
          geoResource.updatingKey,
          geoResource.name,
          () => geoResourceAction.updateGeoResource(
            geoResource,
            announceSuccess: false,
          ),
        ),
      update('smart_model', 'MODEL', () => updateSmartModel()),"""

        content = apply_snippet_replacement(content, old_update_all, new_update_all, "Add smart_model to updateAll")

        with open(res_action_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    target_repo = sys.argv[2] if len(sys.argv) > 2 else "refined-fish/FlClash-Smart"

    print(f"[+] Patching FlClash sources in: {src_dir} (target repo: {target_repo})")
    patch_constant_dart(src_dir, target_repo)
    patch_make_config_yaml(src_dir, target_repo)
    patch_defaults(src_dir)
    patch_enum_dart(src_dir)
    patch_preferences_and_state(src_dir)
    patch_task_dart(src_dir)
    patch_setup_dart(src_dir)
    patch_widgets_config_item(src_dir)
    patch_general_views(src_dir)
    patch_dashboard_intranet_ip(src_dir)
    patch_resources_view(src_dir)
    print("[+] Source patching complete!")

if __name__ == "__main__":
    main()
