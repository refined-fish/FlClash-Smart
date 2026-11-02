#!/usr/bin/env python3
"""
Source patcher for FlClash-Smart.
Customizes upstream chen08209/FlClash source code:
1. Updates update repository URL to refined-fish/FlClash-Smart.
2. Updates publisher URL and publisher name in Windows packaging config.
3. Updates default configurations:
   - System proxy defaults to false (VPN and Network).
   - Android VpnProps: ipv6 defaults to true, dnsHijacking defaults to true.
   - Only statistics proxy defaults to true.
   - Open logs (log capture) defaults to true.
   - Geo auto update defaults to true.
   - Geo update interval defaults to 168 hours.
   - Inbound mixedPort defaults to 0 (displays and acts as "不修改").
   - Decoupled system proxy & HTTP overrides fallback to actual profile port when mixedPort == 0.
   - Default GeoX URLs prepended with acceleration proxy (https://v6.gh-proxy.org/).
   - Defines defaultSmartModelUrl with acceleration proxy.
   - External controller secret defaults to empty (displays as "不修改"), never wiped or auto-generated.
   - External controller secret is always injected if non-empty, decoupled from controller switch.
4. Adds TriOption and generalOverrideKeys (allowLan, geoXUrl, externalController, findProcessMode) to enums.
   - allowLan defaults to TriOption.disable (closed).
   - externalController defaults to TriOption.keep (不修改).
   - findProcessMode defaults to TriOption.keep (不修改).
5. Adds smartModelUrl to Preferences and runningAllowLan, runningMixedPort, profileGeoXUrl, profileLgbmUrl to GlobalState.
6. Decouples invasive configuration overrides in lib/common/task.dart:
   - Preserves profile external-ui and external-ui-url.
   - Preserves profile external-controller unless in generalOverrideKeys (Open/Close).
   - Preserves profile secret unless user entered a non-empty secret.
   - Preserves profile ports unless explicitly set (> 0).
   - Preserves profile allow-lan unless in generalOverrideKeys.
   - Preserves profile find-process-mode unless in generalOverrideKeys.
   - Preserves profile geox-url and lgbm-url unless geoXUrl is in generalOverrideKeys.
   - Returns actual running state (allowLan, mixedPort, geox-url, lgbm-url) back to main isolate.
7. Supports "不修改" (Do not modify) in UI:
   - Port settings UI displays "不修改" when 0.
   - LAN proxy displays tri-state options ("不修改" / "开启" / "关闭") in General settings and Dashboard.
   - Dashboard Intranet IP card removes switch slider, displays actual running status and dropdown selector.
   - External controller and find-process-mode use tri-state option dropdowns.
   - External controller secret item is always accessible and displays "不修改" when empty.
8. Resources View enhancements:
   - Adds "覆写资源链接" (Override Resource URLs) toggle, defaulting to OFF (不修改).
   - When override is OFF: resources are read-only, displaying profile link or default link, with click showing copy dialog.
   - When override is ON: clicking allows editing, persisting changes even if toggle is closed.
   - Adds "Smart" section with "MODEL" resource (lgbm-url, Model.bin).
   - Updates (auto & manual) use effective URLs (adaptive to profile, override switch, defaults).
9. Outbound Network settings ("网络设置 - 出站") "不修改" style:
   - disableKeepAlive converted to TriOption ("不修改" / "开启" / "关闭").
   - keepAliveIdle, keepAliveInterval, routingMark default to 0 (displays and acts as "不修改").
   - Preserves profile outbound configuration in lib/common/task.dart.
10. Dashboard Status block WebUI entry:
   - Moved external controller WebUI entry from Intranet IP card to CurrentOutboundCard (non-removable Status card).
   - Displayed as an eye-catching themed pill button with AppGlyphs.openExternal.
11. Pre-fetch latest GEO and Model assets:
   - Downloads latest GEOIP.metadb, ASN.mmdb, GEOIP.dat, GEOSITE.dat, Model.bin before packaging.
   - Adds Model.bin to initGeo in controller.dart so it is extracted to homePath on first run.
12. Android TUN authorization error fix:
   - Skips desktop admin authorization on Android in requestAdmin and sets tun.enable=false in effectivePatchConfig.
"""

import os
import re
import sys

def apply_snippet_replacement(content: str, old_snippet: str, new_snippet: str, desc: str) -> str:
    """Replaces a snippet using exact match first, falling back to flexible whitespace regex."""
    content_norm = content.replace("\r\n", "\n")
    old_norm = old_snippet.replace("\r\n", "\n")
    new_norm = new_snippet.replace("\r\n", "\n")

    if old_norm in content_norm:
        print(f"  [+] Exact match applied: {desc}")
        return content_norm.replace(old_norm, new_norm)

    # Whitespace-tolerant regex fallback
    pattern = re.escape(old_norm)
    pattern = re.sub(r"\\\s+", r"\\s+", pattern)
    new_content, count = re.subn(pattern, new_norm, content_norm)
    if count > 0:
        print(f"  [+] Regex fallback applied: {desc}")
        return new_content
    else:
        print(f"  [!] Warning: Failed to match snippet for: {desc}")
        return content_norm

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
        # VpnProps defaults (systemProxy=false, ipv6=true, dnsHijacking=true)
        old_vpn_props = """    @Default(true) bool enable,
    @Default(true) bool systemProxy,
    @Default(false) bool ipv6,
    @Default(true) bool allowBypass,
    @Default(false) bool dnsHijacking,"""

        new_vpn_props = """    @Default(true) bool enable,
    @Default(false) bool systemProxy,
    @Default(true) bool ipv6,
    @Default(true) bool allowBypass,
    @Default(true) bool dnsHijacking,"""
        content = apply_snippet_replacement(content, old_vpn_props, new_vpn_props, "Default VpnProps (systemProxy=false, ipv6=true, dnsHijacking=true)")

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
        content = content.replace(
            "this.enable = true, this.systemProxy = true, this.ipv6 = false, this.allowBypass = true, this.dnsHijacking = false,",
            "this.enable = true, this.systemProxy = false, this.ipv6 = true, this.allowBypass = true, this.dnsHijacking = true,"
        )
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
        content = content.replace("json['ipv6'] as bool? ?? false", "json['ipv6'] as bool? ?? true")
        content = content.replace("json['dnsHijacking'] as bool? ?? false", "json['dnsHijacking'] as bool? ?? true")
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

        # defaultMixedPort = 0 (unmodified)
        content = apply_snippet_replacement(
            content,
            "const defaultMixedPort = 7890;",
            "const defaultMixedPort = 0;",
            "defaultMixedPort = 0 (unmodified)"
        )

        # defaultKeepAliveInterval = 0 (unmodified)
        content = apply_snippet_replacement(
            content,
            "const defaultKeepAliveInterval = 30;",
            "const defaultKeepAliveInterval = 0;",
            "defaultKeepAliveInterval = 0 (unmodified)"
        )

        # keepAliveIdle default to 0
        content = apply_snippet_replacement(
            content,
            "@Default(15) @JsonKey(name: 'keep-alive-idle') int keepAliveIdle,",
            "@Default(0) @JsonKey(name: 'keep-alive-idle') int keepAliveIdle,",
            "Default keepAliveIdle=0 in PatchClashConfig"
        )

        # geoAutoUpdate default to true, geoUpdateInterval default to 168
        content = apply_snippet_replacement(
            content,
            """    @Default(false) @JsonKey(name: 'geo-auto-update') bool geoAutoUpdate,
    @Default(24) @JsonKey(name: 'geo-update-interval') int geoUpdateInterval,""",
            """    @Default(true) @JsonKey(name: 'geo-auto-update') bool geoAutoUpdate,
    @Default(168) @JsonKey(name: 'geo-update-interval') int geoUpdateInterval,""",
            "Default geoAutoUpdate=true, geoUpdateInterval=168 in PatchClashConfig"
        )

        # default generalOverrideKeys: contains allowLan (which is false, making allowLan default to disable)
        content = apply_snippet_replacement(
            content,
            """    @Default({})
    @JsonKey(
      name: _generalOverrideKeysJsonKey,
      fromJson: _generalOverrideKeysFromJson,
    )
    Set<GeneralOverrideKey> generalOverrideKeys,""",
            """    @Default({GeneralOverrideKey.allowLan})
    @JsonKey(
      name: _generalOverrideKeysJsonKey,
      fromJson: _generalOverrideKeysFromJson,
    )
    Set<GeneralOverrideKey> generalOverrideKeys,""",
            "Default generalOverrideKeys={GeneralOverrideKey.allowLan}"
        )

        # Legacy generalOverrideKeys fallback: also include allowLan
        content = apply_snippet_replacement(
            content,
            """    _generalOverrideKeysJsonKey: [
      for (final key in _legacyForcedGeneralKeys) key.path,""",
            """    _generalOverrideKeysJsonKey: [
      for (final key in _legacyForcedGeneralKeys) key.path,
      GeneralOverrideKey.allowLan.path,""",
            "Include allowLan in _withLegacyGeneralOverrideKeys"
        )

        # ensureControllerSecret: never automatically generate or wipe secret
        old_secret_fn = """  PatchClashConfig ensureControllerSecret() {
    if (externalController == ExternalControllerStatus.close) {
      return secret.isEmpty ? this : copyWith(secret: '');
    }
    return secret.isEmpty ? copyWith(secret: generateRandomSecret(32)) : this;
  }"""
        new_secret_fn = """  PatchClashConfig ensureControllerSecret() {
    return this;
  }"""
        content = apply_snippet_replacement(content, old_secret_fn, new_secret_fn, "Never wipe or auto-generate secret")

        # toUpdateParams: send geoXUrl if overridden, otherwise empty map (core uses profile/task config)
        old_to_update = "geoXUrl: geoXUrl.raw,"
        new_to_update = """geoXUrl: generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl)
          ? geoXUrl.raw
          : const <String, String>{},"""
        content = apply_snippet_replacement(content, old_to_update, new_to_update, "toUpdateParams geoXUrl conditional override")

        old_tun = """class Tun with _$Tun {
  const factory Tun({
    @Default(false) bool enable,"""
        new_tun = """class Tun with _$Tun {
  const factory Tun({
    @Default(true) bool enable,"""
        content = apply_snippet_replacement(content, old_tun, new_tun, "Default Tun.enable=true in Tun")

        with open(clash_config_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 5. lib/models/generated/clash_config.freezed.dart
    clash_freezed_path = os.path.join(src_dir, "lib", "models", "generated", "clash_config.freezed.dart")
    if os.path.exists(clash_freezed_path):
        with open(clash_freezed_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        content = content.replace("@JsonKey(name: 'geo-auto-update') this.geoAutoUpdate = false,",
                                  "@JsonKey(name: 'geo-auto-update') this.geoAutoUpdate = true,")
        content = content.replace("@JsonKey(name: 'geo-update-interval') this.geoUpdateInterval = 24,",
                                  "@JsonKey(name: 'geo-update-interval') this.geoUpdateInterval = 168,")
        content = content.replace("@JsonKey(name: 'keep-alive-idle') this.keepAliveIdle = 15,",
                                  "@JsonKey(name: 'keep-alive-idle') this.keepAliveIdle = 0,")
        content = content.replace("Set<GeneralOverrideKey> generalOverrideKeys = const {}}",
                                  "Set<GeneralOverrideKey> generalOverrideKeys = const {GeneralOverrideKey.allowLan}}")
        content = content.replace("class _Tun implements Tun {\n  const _Tun({this.enable = false,",
                                  "class _Tun implements Tun {\n  const _Tun({this.enable = true,")
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
        content = content.replace("geoUpdateInterval: (json['geo-update-interval'] as num?)?.toInt() ?? 24,",
                                  "geoUpdateInterval: (json['geo-update-interval'] as num?)?.toInt() ?? 168,")
        content = content.replace("keepAliveIdle: (json['keep-alive-idle'] as num?)?.toInt() ?? 15,",
                                  "keepAliveIdle: (json['keep-alive-idle'] as num?)?.toInt() ?? 0,")
        content = content.replace("generalOverrideKeys: json['general-override-keys'] == null\n          ? const {}",
                                  "generalOverrideKeys: json['general-override-keys'] == null\n          ? const {GeneralOverrideKey.allowLan}")
        content = content.replace("_$TunFromJson(Map<String, dynamic> json) => _Tun(\n  enable: json['enable'] as bool? ?? false,",
                                  "_$TunFromJson(Map<String, dynamic> json) => _Tun(\n  enable: json['enable'] as bool? ?? true,")
        old_enum_map = """const _$GeneralOverrideKeyEnumMap = {
  GeneralOverrideKey.testUrl: 'test-url',
  GeneralOverrideKey.unifiedDelay: 'unified-delay',
  GeneralOverrideKey.tcpConcurrent: 'tcp-concurrent',
  GeneralOverrideKey.ipv6: 'ipv6',
  GeneralOverrideKey.geodataLoader: 'geodata-loader',
};"""
        new_enum_map = """const _$GeneralOverrideKeyEnumMap = {
  GeneralOverrideKey.testUrl: 'test-url',
  GeneralOverrideKey.unifiedDelay: 'unified-delay',
  GeneralOverrideKey.tcpConcurrent: 'tcp-concurrent',
  GeneralOverrideKey.ipv6: 'ipv6',
  GeneralOverrideKey.geodataLoader: 'geodata-loader',
  GeneralOverrideKey.allowLan: 'allow-lan',
  GeneralOverrideKey.geoXUrl: 'geox-url',
  GeneralOverrideKey.externalController: 'external-controller',
  GeneralOverrideKey.findProcessMode: 'find-process-mode',
  GeneralOverrideKey.disableKeepAlive: 'disable-keep-alive',
};"""
        content = apply_snippet_replacement(content, old_enum_map, new_enum_map, "Extend _$GeneralOverrideKeyEnumMap in clash_config.g.dart")
        with open(clash_g_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("[+] Patched clash_config.g.dart defaults")

    # 7. lib/models/core.dart & generated
    core_path = os.path.join(src_dir, "lib", "models", "core.dart")
    if os.path.exists(core_path):
        with open(core_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        content = content.replace("@Default(24) @JsonKey(name: 'geo-update-interval') int geoUpdateInterval,",
                                  "@Default(168) @JsonKey(name: 'geo-update-interval') int geoUpdateInterval,")
        with open(core_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    core_freezed_path = os.path.join(src_dir, "lib", "models", "generated", "core.freezed.dart")
    if os.path.exists(core_freezed_path):
        with open(core_freezed_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        content = content.replace("geoUpdateInterval = 24,", "geoUpdateInterval = 168,")
        with open(core_freezed_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    core_g_path = os.path.join(src_dir, "lib", "models", "generated", "core.g.dart")
    if os.path.exists(core_g_path):
        with open(core_g_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        content = content.replace("geoUpdateInterval: (json['geo-update-interval'] as num?)?.toInt() ?? 24,",
                                  "geoUpdateInterval: (json['geo-update-interval'] as num?)?.toInt() ?? 168,")
        with open(core_g_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

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
  geoXUrl('geox-url'),
  externalController('external-controller'),
  findProcessMode('find-process-mode'),
  disableKeepAlive('disable-keep-alive');

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

        # 1. label exhaustiveness
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
    GeneralOverrideKey.externalController => l.externalController,
    GeneralOverrideKey.findProcessMode => l.findProcessMode,
    GeneralOverrideKey.disableKeepAlive => l.disableKeepAlive,
  };
}"""
        ov_content = apply_snippet_replacement(ov_content, old_label, new_label, "GeneralOverrideKey label exhaustiveness")

        # 2. values in _GeneralOverrideSpec (keep 5 core items only)
        old_values = "  List<GeneralOverrideKey> get values => GeneralOverrideKey.values;"
        new_values = """  List<GeneralOverrideKey> get values => const [
    GeneralOverrideKey.testUrl,
    GeneralOverrideKey.unifiedDelay,
    GeneralOverrideKey.tcpConcurrent,
    GeneralOverrideKey.ipv6,
    GeneralOverrideKey.geodataLoader,
  ];"""
        ov_content = apply_snippet_replacement(ov_content, old_values, new_values, "_GeneralOverrideSpec values list")

        # 3. fieldOf exhaustiveness in _GeneralOverrideSpec
        old_field_tail = """        GeneralOverrideKey.geodataLoader => ToggleOverrideField(
          (config) => config.geodataLoader == GeodataLoader.memconservative,
          (config, value) => config.copyWith(
            geodataLoader: value
                ? GeodataLoader.memconservative
                : GeodataLoader.standard,
          ),
        ),
      };"""

        new_field_tail = """        GeneralOverrideKey.geodataLoader => ToggleOverrideField(
          (config) => config.geodataLoader == GeodataLoader.memconservative,
          (config, value) => config.copyWith(
            geodataLoader: value
                ? GeodataLoader.memconservative
                : GeodataLoader.standard,
          ),
        ),
        GeneralOverrideKey.allowLan => ToggleOverrideField(
          (config) => config.allowLan,
          (config, value) => config.copyWith(allowLan: value),
        ),
        GeneralOverrideKey.geoXUrl => ToggleOverrideField(
          (config) => config.generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl),
          (config, value) => config,
        ),
        GeneralOverrideKey.externalController => ToggleOverrideField(
          (config) => config.externalController == ExternalControllerStatus.open,
          (config, value) => config.copyWith(
            externalController: value ? ExternalControllerStatus.open : ExternalControllerStatus.close,
          ),
        ),
        GeneralOverrideKey.findProcessMode => ToggleOverrideField(
          (config) => config.findProcessMode == FindProcessMode.always,
          (config, value) => config.copyWith(
            findProcessMode: value ? FindProcessMode.always : FindProcessMode.off,
          ),
        ),
        GeneralOverrideKey.disableKeepAlive => ToggleOverrideField(
          (config) => config.disableKeepAlive,
          (config, value) => config.copyWith(disableKeepAlive: value),
        ),
      };"""
        ov_content = apply_snippet_replacement(ov_content, old_field_tail, new_field_tail, "_GeneralOverrideSpec fieldOf exhaustiveness")

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
  String? _smartModelUrlCache;

  Future<String> getSmartModelUrl() async {
    if (_smartModelUrlCache != null) return _smartModelUrlCache!;
    final preferences = await _store.value;
    final val = preferences?.getString('smartModelUrl') ?? defaultSmartModelUrl;
    _smartModelUrlCache = val;
    return val;
  }

  String getSmartModelUrlSync() {
    return _smartModelUrlCache ?? defaultSmartModelUrl;
  }

  Future<void> setSmartModelUrl(String url) async {
    _smartModelUrlCache = url;
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
  final ValueNotifier<bool?> runningAllowLan = ValueNotifier<bool?>(null);
  final ValueNotifier<int?> runningMixedPort = ValueNotifier<int?>(null);
  final ValueNotifier<Map<String, String>?> profileGeoXUrl = ValueNotifier<Map<String, String>?>(null);
  final ValueNotifier<String?> profileLgbmUrl = ValueNotifier<String?>(null);"""
        content = apply_snippet_replacement(content, old_state, new_state, "GlobalState running notifiers")
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

    # RealProfile record definition: add allowLan, mixedPort, geoXUrl, lgbmUrl
    content = apply_snippet_replacement(
        content,
        "typedef RealProfile = ({String yaml, String md5, ConfigCounts counts});",
        "typedef RealProfile = ({String yaml, String md5, ConfigCounts counts, bool allowLan, int? mixedPort, Map<String, String>? geoXUrl, String? lgbmUrl});",
        "RealProfile definition with state fields"
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

    # 2. External controller & secret: Decoupled and non-intrusive
    old_ext = """  rawConfig['external-controller'] =
      data.safeMode || realPatchConfig.secret.isEmpty
      ? ''
      : realPatchConfig.externalController.value;
  rawConfig['secret'] = realPatchConfig.secret;"""

    new_ext = """  // [FlClash-Smart] External-controller override (tri-state)
  if (realPatchConfig.generalOverrideKeys.contains(GeneralOverrideKey.externalController)) {
    rawConfig['external-controller'] = realPatchConfig.externalController.value;
  }
  // [FlClash-Smart] Secret override (decoupled from external controller)
  if (realPatchConfig.secret.isNotEmpty) {
    rawConfig['secret'] = realPatchConfig.secret;
  }"""
    content = apply_snippet_replacement(content, old_ext, new_ext, "Preserve external-controller & decoupled secret")

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
    rawConfig['mixed-port'] = realPatchConfig.mixedPort;
  }
  if (realPatchConfig.generalOverrideKeys.contains(GeneralOverrideKey.disableKeepAlive)) {
    rawConfig['disable-keep-alive'] = realPatchConfig.disableKeepAlive;
  }
  if (realPatchConfig.keepAliveInterval > 0) {
    rawConfig['keep-alive-interval'] = realPatchConfig.keepAliveInterval;
  }
  if (realPatchConfig.keepAliveIdle > 0) {
    rawConfig['keep-alive-idle'] = realPatchConfig.keepAliveIdle;
  }
  if (realPatchConfig.routingMark > 0) {
    rawConfig['routing-mark'] = realPatchConfig.routingMark;
  }
  if (realPatchConfig.generalOverrideKeys.contains(GeneralOverrideKey.findProcessMode)) {
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
    final smartModel = preferences.getSmartModelUrlSync();
    if (smartModel.isNotEmpty) {
      rawConfig['lgbm-url'] = smartModel;
    }
  } else {
    if (rawConfig['geox-url'] == null ||
        (rawConfig['geox-url'] is Map && (rawConfig['geox-url'] as Map).isEmpty)) {
      rawConfig['geox-url'] = defaultGeoXUrl.map((k, v) => MapEntry(k.name, v));
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

    # 6. Return allowLan, mixedPort, geoXUrl, lgbmUrl in _makeRealProfileTask
    old_return = """  final yaml = await _encodeYaml(Map<String, dynamic>.from(rawConfig));
  return (yaml: yaml, md5: yaml.toMd5(), counts: configCountsOf(rawConfig));"""

    new_return = """  final yaml = await _encodeYaml(Map<String, dynamic>.from(rawConfig));
  int? runningPort;
  if (rawConfig['mixed-port'] is int && rawConfig['mixed-port'] > 0) {
    runningPort = rawConfig['mixed-port'];
  } else if (rawConfig['port'] is int && rawConfig['port'] > 0) {
    runningPort = rawConfig['port'];
  }
  Map<String, String>? pGeoX;
  if (rawConfig['geox-url'] is Map) {
    pGeoX = Map<String, String>.from((rawConfig['geox-url'] as Map).map((k, v) => MapEntry(k.toString(), v.toString())));
  }
  String? pLgbm;
  if (rawConfig['lgbm-url'] is String) {
    pLgbm = rawConfig['lgbm-url'];
  }
  return (
    yaml: yaml,
    md5: yaml.toMd5(),
    counts: configCountsOf(rawConfig),
    allowLan: rawConfig['allow-lan'] == true,
    mixedPort: runningPort,
    geoXUrl: pGeoX,
    lgbmUrl: pLgbm,
  );"""
    content = apply_snippet_replacement(content, old_return, new_return, "Return state fields in RealProfile")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_setup_dart(src_dir: str):
    path = os.path.join(src_dir, "lib", "providers", "actions", "setup.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    old_snippet = "    if (profileBase == null) {"
    new_snippet = """    globalState.runningAllowLan.value = res.allowLan;
    globalState.runningMixedPort.value = res.mixedPort;
    globalState.profileGeoXUrl.value = res.geoXUrl;
    globalState.profileLgbmUrl.value = res.lgbmUrl;
    if (profileBase == null) {"""
    content = apply_snippet_replacement(content, old_snippet, new_snippet, "Update globalState notifiers in getProfile")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_widgets_config_item(src_dir: str):
    path = os.path.join(src_dir, "lib", "widgets", "config_item.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # 1. Add super.subtitle to ConfigToggleItem constructor and buildItem
    old_toggle = """class ConfigToggleItem extends _ConfigItem<bool> {
  const ConfigToggleItem({
    super.key,
    required super.selector,
    required super.title,
    required super.onChanged,
    super.leading,
  });

  @override
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

    new_toggle = """class ConfigToggleItem extends _ConfigItem<bool> {
  const ConfigToggleItem({
    super.key,
    required super.selector,
    required super.title,
    required super.onChanged,
    super.subtitle,
    super.leading,
  });

  @override
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

    # 2. Add super.subtitle to ConfigTextItem constructor and buildItem
    old_text_ctor = """class ConfigTextItem extends _ConfigItem<String> {
  const ConfigTextItem({
    super.key,
    required super.selector,
    required super.title,
    required super.onChanged,
    this.maxLength,
    this.keyboardType,
    this.validator,
    this.normalize,
    this.allowEmpty = false,
    super.leading,
  });"""

    new_text_ctor = """class ConfigTextItem extends _ConfigItem<String> {
  const ConfigTextItem({
    super.key,
    required super.selector,
    required super.title,
    required super.onChanged,
    super.subtitle,
    this.maxLength,
    this.keyboardType,
    this.validator,
    this.normalize,
    this.allowEmpty = false,
    super.leading,
  });"""
    content = apply_snippet_replacement(content, old_text_ctor, new_text_ctor, "ConfigTextItem subtitle constructor")

    old_text_build = """    return ListItem.input(
      leading: leading,
      title: Text(label),
      subtitle: value.isEmpty ? null : Text(value),
      dialogTitle: label,"""

    new_text_build = """    return ListItem.input(
      leading: leading,
      title: Text(label),
      subtitle: buildSubtitle(appLocalizations) ?? (value.isEmpty ? null : Text(value)),
      dialogTitle: label,"""
    content = apply_snippet_replacement(content, old_text_build, new_text_build, "ConfigTextItem subtitle rendering")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_proxy_helpers(src_dir: str):
    # 1. lib/common/http.dart
    http_path = os.path.join(src_dir, "lib", "common", "http.dart")
    if os.path.exists(http_path):
        with open(http_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        if "package:fl_clash/state.dart" not in content:
            content = "import 'package:fl_clash/state.dart';\n" + content
        old_http = """    final mixedPort = read(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    final authentication = read(
      networkSettingProvider.select((state) => state.authentication),
    );
    final credentials = authentication.credentials;
    final userInfo = credentials.isNotEmpty ? '${credentials.first}@' : '';
    return 'PROXY ${userInfo}localhost:$mixedPort';"""
        new_http = """    final mixedPort = read(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    final effectivePort = mixedPort != 0 ? mixedPort : (globalState.runningMixedPort.value ?? 7890);
    final authentication = read(
      networkSettingProvider.select((state) => state.authentication),
    );
    final credentials = authentication.credentials;
    final userInfo = credentials.isNotEmpty ? '${credentials.first}@' : '';
    return 'PROXY ${userInfo}localhost:$effectivePort';"""
        content = apply_snippet_replacement(content, old_http, new_http, "http.dart effective port fallback")
        with open(http_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 2. lib/providers/state.dart (imports package:fl_clash/state.dart so proxies.dart & system.dart have globalState)
    state_hub_path = os.path.join(src_dir, "lib", "providers", "state.dart")
    if os.path.exists(state_hub_path):
        with open(state_hub_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        if "package:fl_clash/state.dart" not in content:
            content = "import 'package:fl_clash/state.dart';\n" + content
        with open(state_hub_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 3. lib/providers/state/proxies.dart
    proxies_path = os.path.join(src_dir, "lib", "providers", "state", "proxies.dart")
    if os.path.exists(proxies_path):
        with open(proxies_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        old_prox = """  final mixedPort = ref.watch(
    patchClashConfigProvider.select((state) => state.mixedPort),
  );
  return ProxyState(
    isStart: suspend ? false : isStart,
    systemProxy: systemProxySelector.systemProxy,
    bassDomain: systemProxySelector.bypassDomain,
    port: mixedPort,
  );"""
        new_prox = """  final mixedPort = ref.watch(
    patchClashConfigProvider.select((state) => state.mixedPort),
  );
  final effectivePort = mixedPort != 0 ? mixedPort : (globalState.runningMixedPort.value ?? 7890);
  return ProxyState(
    isStart: suspend ? false : isStart,
    systemProxy: systemProxySelector.systemProxy,
    bassDomain: systemProxySelector.bypassDomain,
    port: effectivePort,
  );"""
        content = apply_snippet_replacement(content, old_prox, new_prox, "proxies.dart ProxyState effective port")
        with open(proxies_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 4. lib/providers/state/system.dart
    sys_path = os.path.join(src_dir, "lib", "providers", "state", "system.dart")
    if os.path.exists(sys_path):
        with open(sys_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        old_tray = """  return TrayState(
    mode: clashConfig.mode,
    port: clashConfig.mixedPort,"""
        new_tray = """  final effectiveTrayPort = clashConfig.mixedPort != 0 ? clashConfig.mixedPort : (globalState.runningMixedPort.value ?? 7890);
  return TrayState(
    mode: clashConfig.mode,
    port: effectiveTrayPort,"""
        content = apply_snippet_replacement(content, old_tray, new_tray, "system.dart TrayState effective port")

        old_vpn = """    systemProxy:
        vpnSetting.systemProxy && !networkSetting.authenticated && !safeMode,
    port: clashConfig.mixedPort,"""
        new_vpn = """    systemProxy:
        vpnSetting.systemProxy && !networkSetting.authenticated && !safeMode,
    port: clashConfig.mixedPort != 0 ? clashConfig.mixedPort : (globalState.runningMixedPort.value ?? 7890),"""
        content = apply_snippet_replacement(content, old_vpn, new_vpn, "system.dart VpnOptions effective port")
        with open(sys_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 5. lib/providers/actions/system.dart
    sys_act_path = os.path.join(src_dir, "lib", "providers", "actions", "system.dart")
    if os.path.exists(sys_act_path):
        with open(sys_act_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        old_copy = """  Future<void> copyProxyEnv() async {
    final port = ref.read(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    await Clipboard.setData(
      ClipboardData(text: proxyEnvCommand(port, isWindows: system.isWindows)),
    );
  }"""
        new_copy = """  Future<void> copyProxyEnv() async {
    final port = ref.read(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    final effectivePort = port != 0 ? port : (globalState.runningMixedPort.value ?? 7890);
    await Clipboard.setData(
      ClipboardData(text: proxyEnvCommand(effectivePort, isWindows: system.isWindows)),
    );
  }"""
        content = apply_snippet_replacement(content, old_copy, new_copy, "system.dart copyProxyEnv effective port")
        with open(sys_act_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

    # 6. lib/views/dashboard/widgets/network_takeover.dart
    takeover_path = os.path.join(src_dir, "lib", "views", "dashboard", "widgets", "network_takeover.dart")
    if os.path.exists(takeover_path):
        with open(takeover_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
        if "package:fl_clash/state.dart" not in content:
            content = "import 'package:fl_clash/state.dart';\n" + content
        old_on = """    final on = systemProxy
        ? appLocalizations.portValue(
            ref.watch(
              patchClashConfigProvider.select((state) => state.mixedPort),
            ),
          )
        : appLocalizations.enabled;"""
        new_on = """    final port = ref.watch(
      patchClashConfigProvider.select((state) => state.mixedPort),
    );
    final effectivePort = port != 0 ? port : (globalState.runningMixedPort.value ?? 7890);
    final on = systemProxy
        ? appLocalizations.portValue(effectivePort)
        : appLocalizations.enabled;"""
        content = apply_snippet_replacement(content, old_on, new_on, "network_takeover.dart effective port")
        with open(takeover_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

def patch_general_views(src_dir: str):
    # 1. port_form.dart
    port_form_path = os.path.join(src_dir, "lib", "views", "config", "general", "port_form.dart")
    if os.path.exists(port_form_path):
        with open(port_form_path, "r", encoding="utf-8", newline="") as f:
            content = f.read()

        # Allow disabled mixedPort and initialize with empty string when 0
        old_init = """    _mixedPortController = TextEditingController(text: ports.mixed.toString());
    _portController = TextEditingController(text: ports.http.toString());
    _socksPortController = TextEditingController(text: ports.socks.toString());
    _redirPortController = TextEditingController(text: ports.redir.toString());
    _tProxyPortController = TextEditingController(
      text: ports.tproxy.toString(),
    );
    _fields = [
      _PortField(
        controller: _mixedPortController,
        label: (appLocalizations) => appLocalizations.mixedPort,
        allowDisabled: false,
      ),"""

        new_init = """    _mixedPortController = TextEditingController(text: ports.mixed == 0 ? '' : ports.mixed.toString());
    _portController = TextEditingController(text: ports.http == 0 ? '' : ports.http.toString());
    _socksPortController = TextEditingController(text: ports.socks == 0 ? '' : ports.socks.toString());
    _redirPortController = TextEditingController(text: ports.redir == 0 ? '' : ports.redir.toString());
    _tProxyPortController = TextEditingController(
      text: ports.tproxy == 0 ? '' : ports.tproxy.toString(),
    );
    _fields = [
      _PortField(
        controller: _mixedPortController,
        label: (appLocalizations) => appLocalizations.mixedPort,
        allowDisabled: true,
      ),"""
        content = apply_snippet_replacement(content, old_init, new_init, "Allow disabled mixed port in form init")

        # Reset button sets mixedPort: 0
        content = apply_snippet_replacement(
            content,
            "mixedPort: 7890,",
            "mixedPort: 0,",
            "Reset mixedPort to 0 in port form"
        )

        # Handle update parses with fallback 0
        old_update = """            mixedPort: int.parse(_mixedPortController.text),
            port: int.parse(_portController.text),
            socksPort: int.parse(_socksPortController.text),
            redirPort: int.parse(_redirPortController.text),
            tproxyPort: int.parse(_tProxyPortController.text),"""

        new_update = """            mixedPort: int.tryParse(_mixedPortController.text) ?? 0,
            port: int.tryParse(_portController.text) ?? 0,
            socksPort: int.tryParse(_socksPortController.text) ?? 0,
            redirPort: int.tryParse(_redirPortController.text) ?? 0,
            tproxyPort: int.tryParse(_tProxyPortController.text) ?? 0,"""
        content = apply_snippet_replacement(content, old_update, new_update, "Parse ports with fallback 0 in update")

        # Validation: allow empty or 0 if field.allowDisabled
        old_validate = """    final label = field.label(appLocalizations);
    if (value == null || value.isEmpty) {
      return appLocalizations.emptyTip(label);
    }
    final port = int.tryParse(value);"""

        new_validate = """    final label = field.label(appLocalizations);
    if (field.allowDisabled && (value == null || value.isEmpty || value == '0')) {
      return null;
    }
    if (value == null || value.isEmpty) {
      return appLocalizations.emptyTip(label);
    }
    final port = int.tryParse(value);"""
        content = apply_snippet_replacement(content, old_validate, new_validate, "Allow empty port in validation")

        # Form row title & hint
        old_form_row = """              FormRow(
                title: field.label(appLocalizations),
                invalid: issues.containsKey(field),
                trailing: FormRowTextField(
                  controller: field.controller,
                  hintText: appLocalizations.required,"""

        new_form_row = """              FormRow(
                title: field.controller.text.isEmpty || field.controller.text == '0'
                    ? '${field.label(appLocalizations)} (不修改)'
                    : field.label(appLocalizations),
                invalid: issues.containsKey(field),
                trailing: FormRowTextField(
                  controller: field.controller,
                  hintText: '不修改',"""
        content = apply_snippet_replacement(content, old_form_row, new_form_row, "Show (不修改) in form rows")

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

        # Define AllowLanItem, ExternalControllerItem, FindProcessModeItem
        new_items_code = """class AllowLanItem extends ConsumerWidget {
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

class ExternalControllerItem extends ConsumerWidget {
  const ExternalControllerItem({super.key});

  @override
  Widget build(BuildContext context, ref) {
    return ConfigOptionsItem<TriOption>(
      title: (l) => l.externalController,
      options: TriOption.values,
      textBuilder: (option) => switch (option) {
        TriOption.keep => '不修改',
        TriOption.enable => '开启 (127.0.0.1:9090)',
        TriOption.disable => '关闭',
      },
      selector: patchClashConfigProvider.select((state) {
        if (!state.generalOverrideKeys.contains(GeneralOverrideKey.externalController)) {
          return TriOption.keep;
        }
        return state.externalController == ExternalControllerStatus.open
            ? TriOption.enable
            : TriOption.disable;
      }),
      onChanged: (ref, value) => ref
          .read(patchClashConfigProvider.notifier)
          .update((state) {
            final keys = Set<GeneralOverrideKey>.from(state.generalOverrideKeys);
            if (value == TriOption.keep) {
              keys.remove(GeneralOverrideKey.externalController);
              return state.copyWith(generalOverrideKeys: keys);
            } else {
              keys.add(GeneralOverrideKey.externalController);
              return state.copyWith(
                generalOverrideKeys: keys,
                externalController: value == TriOption.enable
                    ? ExternalControllerStatus.open
                    : ExternalControllerStatus.close,
              );
            }
          }),
    );
  }
}

class FindProcessModeItem extends ConsumerWidget {
  const FindProcessModeItem({super.key});

  @override
  Widget build(BuildContext context, ref) {
    return ConfigOptionsItem<TriOption>(
      title: (l) => l.findProcessMode,
      options: TriOption.values,
      textBuilder: (option) => switch (option) {
        TriOption.keep => '不修改',
        TriOption.enable => '开启 (always)',
        TriOption.disable => '关闭 (off)',
      },
      selector: patchClashConfigProvider.select((state) {
        if (!state.generalOverrideKeys.contains(GeneralOverrideKey.findProcessMode)) {
          return TriOption.keep;
        }
        return state.findProcessMode == FindProcessMode.always
            ? TriOption.enable
            : TriOption.disable;
      }),
      onChanged: (ref, value) => ref
          .read(patchClashConfigProvider.notifier)
          .update((state) {
            final keys = Set<GeneralOverrideKey>.from(state.generalOverrideKeys);
            if (value == TriOption.keep) {
              keys.remove(GeneralOverrideKey.findProcessMode);
              return state.copyWith(generalOverrideKeys: keys);
            } else {
              keys.add(GeneralOverrideKey.findProcessMode);
              return state.copyWith(
                generalOverrideKeys: keys,
                findProcessMode: value == TriOption.enable
                    ? FindProcessMode.always
                    : FindProcessMode.off,
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
            new_items_code + "\nclass ExternalControllerSecretItem extends ConsumerWidget {",
            "Add TriOption items classes in general.dart"
        )

        # ExternalControllerSecretItem: show '不修改' when secret is empty, allow empty
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
      allowEmpty: true,
      onChanged: (ref, value) => ref
          .read(patchClashConfigProvider.notifier)
          .update((state) => state.copyWith(secret: value)),
    );
  }
}"""
        content = apply_snippet_replacement(content, old_secret_item, new_secret_item, "ExternalControllerSecretItem subtitle")

        # Update _inboundItems in general.dart
        old_inbound = """  List<Widget> _inboundItems({
    required bool authentication,
    required bool externalController,
  }) {
    return [
      const PortItem(),
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
      if (externalController) const ExternalControllerSecretItem(),
      const AuthenticationItem(),"""

        new_inbound = """  List<Widget> _inboundItems({
    required bool authentication,
    required bool externalController,
  }) {
    return [
      const PortItem(),
      const AllowLanItem(),
      const ExternalControllerItem(),
      const ExternalControllerSecretItem(),
      const AuthenticationItem(),"""
        content = apply_snippet_replacement(content, old_inbound, new_inbound, "Update _inboundItems with TriOption items")

        # Update _connectionItems in general.dart
        old_conn = """  List<Widget> _connectionItems() {
    return [
      const DelayTestTimeoutItem(),
      _clashToggle(
        title: (l) => l.findProcessMode,
        select: (state) => state.findProcessMode == FindProcessMode.always,
        update: (state, value) => state.copyWith(
          findProcessMode: value ? FindProcessMode.always : FindProcessMode.off,
        ),
      ),
      _appSettingToggle("""

        new_conn = """  List<Widget> _connectionItems() {
    return [
      const DelayTestTimeoutItem(),
      const FindProcessModeItem(),
      _appSettingToggle("""
        content = apply_snippet_replacement(content, old_conn, new_conn, "Update _connectionItems with FindProcessModeItem")

        with open(general_path, "w", encoding="utf-8", newline="") as f:
            f.write(content)

def patch_dashboard_intranet_ip(src_dir: str):
    path = os.path.join(src_dir, "lib", "views", "dashboard", "widgets", "intranet_ip.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # Import url_launcher, state, and material_new_shapes if not present
    if "package:url_launcher/url_launcher.dart" not in content:
        content = "import 'package:url_launcher/url_launcher.dart';\n" + content
    if "package:fl_clash/state.dart" not in content:
        content = "import 'package:fl_clash/state.dart';\n" + content
    if "package:material_new_shapes/material_new_shapes.dart" not in content:
        content = "import 'package:material_new_shapes/material_new_shapes.dart';\n" + content

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
    final colors = DashboardColors.of(context);
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
    final runningPort = port > 0 ? port : (globalState.runningMixedPort.value ?? 7890);
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
    final address = localIp == null || localIp.isEmpty
        ? null
        : actualRunning
        ? '$localIp:$runningPort'
        : localIp;

    Future<void> showAllowLanMenu() async {
      final selected = await dialogs.showCommonDialog<TriOption>(
        child: CommonDialog(
          title: appLocalizations.allowLan,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 16),
          child: Wrap(
            children: [
              ListItem(
                title: const Text('开启'),
                trailing: allowLanMode == TriOption.enable ? GlyphIcon(AppGlyphs.check, size: 20) : null,
                onTap: () => Navigator.of(context).pop(TriOption.enable),
              ),
              ListItem(
                title: const Text('关闭'),
                trailing: allowLanMode == TriOption.disable ? GlyphIcon(AppGlyphs.check, size: 20) : null,
                onTap: () => Navigator.of(context).pop(TriOption.disable),
              ),
              ListItem(
                title: const Text('不修改'),
                trailing: allowLanMode == TriOption.keep ? GlyphIcon(AppGlyphs.check, size: 20) : null,
                onTap: () => Navigator.of(context).pop(TriOption.keep),
              ),
            ],
          ),
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
              final showIcon = constraints.maxWidth > 140;
              final lanSubtitle = switch (allowLanMode) {
                TriOption.keep => '不修改 (运行: ${actualRunning ? "开启" : "关闭"})',
                TriOption.enable => '开启 (运行: ${actualRunning ? "开启 · $runningPort" : "未启动"})',
                TriOption.disable => '关闭 (运行: ${actualRunning ? "开启" : "关闭"})',
              };
              return DashboardBlock(
                radius: row.radius,
                padding: showIcon
                    ? row.padding
                    : row.padding.copyWith(left: row.titleStart),
                onTap: showAllowLanMenu,
                semanticLabel: title,
                child: Row(
                  children: [
                    if (showIcon)
                      ShapeBadge(
                        shape: MaterialShapes.cookie6Sided,
                        color: actualRunning
                            ? colorScheme.primary
                            : colors.tone2,
                        size: row.icon,
                        child: GlyphIcon(
                          AppGlyphs.wifi,
                          size: row.icon * 0.5,
                          color: actualRunning
                              ? colorScheme.onPrimary
                              : colorScheme.onSurfaceVariant,
                        ),
                      ),
                    if (showIcon) const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            title,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: DashboardText.rowTitle(context),
                          ),
                          Text(
                            lanSubtitle,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: DashboardText.label(context),
                          ),
                        ],
                      ),
                    ),
                    GlyphIcon(
                      AppGlyphs.chevronDown,
                      size: 18,
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );"""
    content = apply_snippet_replacement(content, old_body, new_body, "Dashboard IntranetIpCard with WebUI & Dropdown allowLan")

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
                  subtitle: const Text('开启后方可在此处自定义配置资源链接；关闭时优先使用配置文件中的链接'),
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

        # Replace _GeoResourceItem with adaptive read-only/edit behavior
        old_geo_item = """class _GeoResourceItem extends ConsumerWidget {
  final GeoResource type;
  final Map<String, FileInfo?> preloaded;

  const _GeoResourceItem(this.type, {required this.preloaded});

  Future<void> _updateUrl(
    BuildContext context,
    WidgetRef ref,
    String url,
  ) async {
    final newUrl = await dialogs.showCommonDialog<String>(
      child: UpdateGeoUrlFormDialog(
        title: type.name,
        url: url,
        defaultValue: defaultGeoXUrl[type],
      ),
    );
    if (newUrl != null && newUrl != url && context.mounted) {
      try {
        ref
            .read(geoResourceActionProvider.notifier)
            .updateGeoResourceUrl(type, newUrl);
      } catch (e) {
        unawaited(
          dialogs.showAlert(
            title: type.name,
            message: TextSpan(text: e.toString()),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isUpdating = ref.watch(isUpdatingProvider(type.updatingKey));
    final url = ref.watch(
      patchClashConfigProvider.select((state) => state.geoXUrl[type]),
    );
    return _FileInfoBuilder(
      source: type,
      updatingKey: type.updatingKey,
      preloaded: preloaded,
      load: () => _geoFileInfo(type),
      builder: (context, fileInfo, pending) => _ResourceItem(
        title: type.name,
        url: url,
        chip: fileInfo?.size.traffic.show,
        lastUpdateTime: fileInfo?.lastModified,
        pending: pending,
        isUpdating: isUpdating,
        onSync: () => ref
            .read(geoResourceActionProvider.notifier)
            .updateGeoResource(type),
        onEdit: url == null ? null : () => _updateUrl(context, ref, url),
      ),
    );
  }
}"""

        new_geo_item = """class _GeoResourceItem extends ConsumerWidget {
  final GeoResource type;
  final Map<String, FileInfo?> preloaded;

  const _GeoResourceItem(this.type, {required this.preloaded});

  String _getEffectiveUrl(WidgetRef ref) {
    final isOverridden = ref.watch(
      patchClashConfigProvider.select(
        (state) => state.generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl),
      ),
    );
    if (isOverridden) {
      final custom = ref.watch(
        patchClashConfigProvider.select((state) => state.geoXUrl[type]),
      );
      if (custom != null && custom.isNotEmpty) return custom;
      return defaultGeoXUrl[type] ?? '';
    } else {
      final profileUrl = globalState.profileGeoXUrl.value?[type.name];
      if (profileUrl != null && profileUrl.isNotEmpty) return profileUrl;
      return defaultGeoXUrl[type] ?? '';
    }
  }

  Future<void> _handleTap(BuildContext context, WidgetRef ref, String effectiveUrl) async {
    final isOverridden = ref.read(
      patchClashConfigProvider.select(
        (state) => state.generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl),
      ),
    );
    if (!isOverridden) {
      await dialogs.showCommonDialog<void>(
        child: CommonDialog(
          title: type.name,
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SelectableText(
                effectiveUrl,
                style: const TextStyle(fontSize: 13, fontFamily: 'monospace'),
              ),
              const SizedBox(height: 16),
              Text(
                '提示：「覆写资源链接」未开启，当前为只读展示。如需自定义修改链接，请先在上方开启「覆写资源链接」开关。',
                style: TextStyle(fontSize: 12, color: context.colorScheme.onSurfaceVariant),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () async {
                      await Clipboard.setData(ClipboardData(text: effectiveUrl));
                      if (context.mounted) {
                        Navigator.of(context).pop();
                        context.showNotifier('已复制链接到剪贴板');
                      }
                    },
                    child: const Text('复制链接'),
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('关闭'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
      return;
    }

    final currentCustom = ref.read(patchClashConfigProvider).geoXUrl[type] ?? defaultGeoXUrl[type] ?? '';
    final newUrl = await dialogs.showCommonDialog<String>(
      child: UpdateGeoUrlFormDialog(
        title: type.name,
        url: currentCustom,
        defaultValue: defaultGeoXUrl[type],
      ),
    );
    if (newUrl != null && newUrl != currentCustom && context.mounted) {
      ref.read(geoResourceActionProvider.notifier).updateGeoResourceUrl(type, newUrl);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isUpdating = ref.watch(isUpdatingProvider(type.updatingKey));
    final url = _getEffectiveUrl(ref);
    return _FileInfoBuilder(
      source: type,
      updatingKey: type.updatingKey,
      preloaded: preloaded,
      load: () => _geoFileInfo(type),
      builder: (context, fileInfo, pending) => _ResourceItem(
        title: type.name,
        url: url,
        chip: fileInfo?.size.traffic.show,
        lastUpdateTime: fileInfo?.lastModified,
        pending: pending,
        isUpdating: isUpdating,
        onSync: () => ref
            .read(geoResourceActionProvider.notifier)
            .updateGeoResource(type),
        onEdit: () => _handleTap(context, ref, url),
      ),
    );
  }
}"""
        content = apply_snippet_replacement(content, old_geo_item, new_geo_item, "Adaptive _GeoResourceItem with read-only/edit dialogs")

        # Add helper function _smartModelFileInfo and class _SmartModelResourceItem
        smart_item_code = """
Future<FileInfo?> _smartModelFileInfo() async {
  final homePath = await appPath.homeDirPath;
  return File(join(homePath, 'Model.bin')).getFileInfo();
}

class _SmartModelResourceItem extends ConsumerWidget {
  final Map<String, FileInfo?> preloaded;

  const _SmartModelResourceItem({required this.preloaded});

  String _getEffectiveUrl(WidgetRef ref) {
    final isOverridden = ref.watch(
      patchClashConfigProvider.select(
        (state) => state.generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl),
      ),
    );
    if (isOverridden) {
      final custom = preferences.getSmartModelUrlSync();
      if (custom.isNotEmpty) return custom;
      return defaultSmartModelUrl;
    } else {
      final profileUrl = globalState.profileLgbmUrl.value;
      if (profileUrl != null && profileUrl.isNotEmpty) return profileUrl;
      return defaultSmartModelUrl;
    }
  }

  Future<void> _handleTap(BuildContext context, WidgetRef ref, String effectiveUrl) async {
    final isOverridden = ref.read(
      patchClashConfigProvider.select(
        (state) => state.generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl),
      ),
    );
    if (!isOverridden) {
      await dialogs.showCommonDialog<void>(
        child: CommonDialog(
          title: 'MODEL (LightGBM)',
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SelectableText(
                effectiveUrl,
                style: const TextStyle(fontSize: 13, fontFamily: 'monospace'),
              ),
              const SizedBox(height: 16),
              Text(
                '提示：「覆写资源链接」未开启，当前为只读展示。如需自定义修改链接，请先在上方开启「覆写资源链接」开关。',
                style: TextStyle(fontSize: 12, color: context.colorScheme.onSurfaceVariant),
              ),
              const SizedBox(height: 16),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () async {
                      await Clipboard.setData(ClipboardData(text: effectiveUrl));
                      if (context.mounted) {
                        Navigator.of(context).pop();
                        context.showNotifier('已复制链接到剪贴板');
                      }
                    },
                    child: const Text('复制链接'),
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('关闭'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
      return;
    }

    final currentCustom = preferences.getSmartModelUrlSync().isNotEmpty
        ? preferences.getSmartModelUrlSync()
        : defaultSmartModelUrl;
    final newUrl = await dialogs.showCommonDialog<String>(
      child: UpdateGeoUrlFormDialog(
        title: 'MODEL (LightGBM)',
        url: currentCustom,
        defaultValue: defaultSmartModelUrl,
      ),
    );
    if (newUrl != null && newUrl != currentCustom && context.mounted) {
      await preferences.setSmartModelUrl(newUrl);
      if (context.mounted) {
        (context as Element).markNeedsBuild();
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isUpdating = ref.watch(isUpdatingProvider('smart_model'));
    final url = _getEffectiveUrl(ref);
    return _FileInfoBuilder(
      source: 'smart_model',
      updatingKey: 'smart_model',
      preloaded: preloaded,
      load: () => _smartModelFileInfo(),
      builder: (context, fileInfo, pending) => _ResourceItem(
        title: 'MODEL',
        url: url,
        chip: fileInfo?.size.traffic.show,
        lastUpdateTime: fileInfo?.lastModified,
        pending: pending,
        isUpdating: isUpdating,
        onSync: () => ref.read(resourcesActionProvider.notifier).updateSmartModel(),
        onEdit: () => _handleTap(context, ref, url),
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
      final overrideGeo = ref.read(patchClashConfigProvider).generalOverrideKeys.contains(GeneralOverrideKey.geoXUrl);
      final customUrl = await preferences.getSmartModelUrl();
      final profileUrl = globalState.profileLgbmUrl.value;
      final url = overrideGeo
          ? (customUrl.isNotEmpty ? customUrl : defaultSmartModelUrl)
          : (profileUrl != null && profileUrl.isNotEmpty ? profileUrl : defaultSmartModelUrl);

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

def patch_network_views(src_dir: str):
    path = os.path.join(src_dir, "lib", "views", "config", "network.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # 1. Update _NumberItem to support zeroAsKeep
    old_number_item = """class _NumberItem extends ConsumerWidget {
  const _NumberItem({
    required this.title,
    required this.select,
    required this.update,
    this.isSeconds = false,
    this.min = 0,
    this.max = _maxUint32,
  });

  final ConfigLabel title;
  final int Function(PatchClashConfig state) select;
  final _TunUpdate<int> update;
  final bool isSeconds;
  final int min;
  final int max;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appLocalizations = context.appLocalizations;
    final label = title(appLocalizations);
    final value = ref.watch(patchClashConfigProvider.select(select));
    return ListItem.input(
      title: Text(label),
      subtitle: Text(
        isSeconds ? appLocalizations.secondsCount(value) : '$value',
      ),
      dialogTitle: label,
      value: '$value',
      resetValue: '${select(defaultClashConfig)}',
      suffixText: isSeconds ? appLocalizations.seconds : null,
      maxLength: TextInputLimits.number,
      keyboardType: TextInputType.number,
      validator: (value) {
        final number = int.tryParse(value?.trim() ?? '');
        if (number == null) {
          return appLocalizations.numberTip(label);
        }
        return number < min || number > max
            ? appLocalizations.numberRangeTip(label, '$min', '$max')
            : null;
      },
      onChanged: (value) {
        if (value == null) {
          return;
        }
        ref
            .read(patchClashConfigProvider.notifier)
            .update((state) => update(state, int.parse(value.trim())));
      },
    );
  }
}"""

    new_number_item = """class _NumberItem extends ConsumerWidget {
  const _NumberItem({
    required this.title,
    required this.select,
    required this.update,
    this.isSeconds = false,
    this.zeroAsKeep = false,
    this.min = 0,
    this.max = _maxUint32,
  });

  final ConfigLabel title;
  final int Function(PatchClashConfig state) select;
  final _TunUpdate<int> update;
  final bool isSeconds;
  final bool zeroAsKeep;
  final int min;
  final int max;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final appLocalizations = context.appLocalizations;
    final label = title(appLocalizations);
    final value = ref.watch(patchClashConfigProvider.select(select));
    return ListItem.input(
      title: Text(label),
      subtitle: Text(
        zeroAsKeep && value == 0
            ? '不修改'
            : (isSeconds ? appLocalizations.secondsCount(value) : '$value'),
      ),
      dialogTitle: label,
      value: '$value',
      resetValue: '${select(defaultClashConfig)}',
      suffixText: isSeconds ? appLocalizations.seconds : null,
      maxLength: TextInputLimits.number,
      keyboardType: TextInputType.number,
      validator: (value) {
        final number = int.tryParse(value?.trim() ?? '');
        if (number == null) {
          return appLocalizations.numberTip(label);
        }
        return number < min || number > max
            ? appLocalizations.numberRangeTip(label, '$min', '$max')
            : null;
      },
      onChanged: (value) {
        if (value == null) {
          return;
        }
        ref
            .read(patchClashConfigProvider.notifier)
            .update((state) => update(state, int.parse(value.trim())));
      },
    );
  }
}"""
    content = apply_snippet_replacement(content, old_number_item, new_number_item, "Update _NumberItem with zeroAsKeep")

    # 2. Update outboundItems
    old_outbound = """List<Widget> outboundItems({required bool isDesktop, required bool isLinux}) {
  return [
    if (isDesktop) ...[
      ConfigToggleItem(
        title: (l) => l.disableKeepAlive,
        selector: patchClashConfigProvider.select(
          (state) => state.disableKeepAlive,
        ),
        onChanged: _tunWriter(
          (state, value) => state.copyWith(disableKeepAlive: value),
        ),
      ),
      _NumberItem(
        title: (l) => l.keepAliveIdle,
        isSeconds: true,
        select: (state) => state.keepAliveIdle,
        update: (state, value) => state.copyWith(keepAliveIdle: value),
      ),
      _NumberItem(
        title: (l) => l.keepAliveIntervalDesc,
        isSeconds: true,
        select: (state) => state.keepAliveInterval,
        update: (state, value) => state.copyWith(keepAliveInterval: value),
      ),
    ],
    if (isLinux)
      _NumberItem(
        title: (l) => l.routingMark,
        select: (state) => state.routingMark,
        update: (state, value) => state.copyWith(routingMark: value),
      ),
  ];
}"""

    new_outbound = """List<Widget> outboundItems({required bool isDesktop, required bool isLinux}) {
  return [
    if (isDesktop) ...[
      ConfigOptionsItem<TriOption>(
        title: (l) => l.disableKeepAlive,
        options: TriOption.values,
        textBuilder: (option) => switch (option) {
          TriOption.keep => '不修改',
          TriOption.enable => '开启',
          TriOption.disable => '关闭',
        },
        selector: patchClashConfigProvider.select((state) {
          if (!state.generalOverrideKeys.contains(GeneralOverrideKey.disableKeepAlive)) {
            return TriOption.keep;
          }
          return state.disableKeepAlive ? TriOption.enable : TriOption.disable;
        }),
        onChanged: (ref, value) => ref
            .read(patchClashConfigProvider.notifier)
            .update((state) {
              final keys = Set<GeneralOverrideKey>.from(state.generalOverrideKeys);
              if (value == TriOption.keep) {
                keys.remove(GeneralOverrideKey.disableKeepAlive);
                return state.copyWith(generalOverrideKeys: keys);
              } else {
                keys.add(GeneralOverrideKey.disableKeepAlive);
                return state.copyWith(
                  generalOverrideKeys: keys,
                  disableKeepAlive: value == TriOption.enable,
                );
              }
            }),
      ),
      _NumberItem(
        title: (l) => l.keepAliveIdle,
        isSeconds: true,
        zeroAsKeep: true,
        select: (state) => state.keepAliveIdle,
        update: (state, value) => state.copyWith(keepAliveIdle: value),
      ),
      _NumberItem(
        title: (l) => l.keepAliveIntervalDesc,
        isSeconds: true,
        zeroAsKeep: true,
        select: (state) => state.keepAliveInterval,
        update: (state, value) => state.copyWith(keepAliveInterval: value),
      ),
    ],
    if (isLinux)
      _NumberItem(
        title: (l) => l.routingMark,
        zeroAsKeep: true,
        select: (state) => state.routingMark,
        update: (state, value) => state.copyWith(routingMark: value),
      ),
  ];
}"""
    content = apply_snippet_replacement(content, old_outbound, new_outbound, "outboundItems with TriOption and zeroAsKeep")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_dashboard_current_outbound(src_dir: str):
    path = os.path.join(src_dir, "lib", "views", "dashboard", "widgets", "current_outbound.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # 1. Add url_launcher import
    if "import 'package:url_launcher/url_launcher.dart';" not in content:
        content = "import 'package:url_launcher/url_launcher.dart';\n" + content

    # 2. Add prominent WebUI entry button to DashboardCardHeader
    old_header = """                      DashboardCardHeader(
                        glyph: AppGlyphs.status,
                        title: appLocalizations.status,
                        leading: [
                          DashboardChip(
                            label: chipLabel,
                            tone: chipTone,
                            dot: isStart,
                          ),
                        ],
                      ),"""

    new_header = """                      DashboardCardHeader(
                        glyph: AppGlyphs.status,
                        title: appLocalizations.status,
                        leading: [
                          DashboardChip(
                            label: chipLabel,
                            tone: chipTone,
                            dot: isStart,
                          ),
                        ],
                        trailing: [
                          Tooltip(
                            message: 'Web 控制面板',
                            child: Material(
                              color: colorScheme.primary,
                              shape: const StadiumBorder(),
                              clipBehavior: Clip.antiAlias,
                              child: InkWell(
                                onTap: () {
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
                                child: Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    spacing: 4,
                                    children: [
                                      GlyphIcon(
                                        AppGlyphs.openExternal,
                                        size: 13,
                                        color: colorScheme.onPrimary,
                                      ),
                                      Text(
                                        'Web 控制台',
                                        style: TextStyle(
                                          color: colorScheme.onPrimary,
                                          fontSize: 12,
                                          fontWeight: FontWeight.w600,
                                          height: 1.1,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),"""
    content = apply_snippet_replacement(content, old_header, new_header, "CurrentOutboundCard WebUI header entry")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_setup_actions(src_dir: str):
    path = os.path.join(src_dir, "lib", "providers", "actions", "setup.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    # 1. requestAdmin: skip on Android
    old_req = """  @visibleForTesting
  Future<bool> requestAdmin(bool enableTun) async {
    if (!enableTun || ref.read(safeModeProvider)) {
      return true;
    }"""

    new_req = """  @visibleForTesting
  Future<bool> requestAdmin(bool enableTun) async {
    if (system.isAndroid || !enableTun || ref.read(safeModeProvider)) {
      return true;
    }"""
    content = apply_snippet_replacement(content, old_req, new_req, "Skip requestAdmin on Android")

    # 2. _effectivePatchConfig: tun.enable false on Android
    old_eff = """    final authorized =
        ref.read(authorizedTunEnableProvider) ==
        TunAuthorizationState.authorized;
    return patchConfig.copyWith(
      tun: patchConfig.tun.copyWith(
        enable: patchConfig.tun.enable && authorized,
      ),"""

    new_eff = """    final authorized =
        ref.read(authorizedTunEnableProvider) ==
        TunAuthorizationState.authorized;
    return patchConfig.copyWith(
      tun: patchConfig.tun.copyWith(
        enable: !system.isAndroid && patchConfig.tun.enable && authorized,
      ),"""
    content = apply_snippet_replacement(content, old_eff, new_eff, "effectivePatchConfig tun.enable=false on Android")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def patch_controller_dart(src_dir: str):
    path = os.path.join(src_dir, "lib", "core", "controller.dart")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8", newline="") as f:
        content = f.read()

    old_geo_list = "    const geoFileNameList = [MMDB, GEOIP, GEOSITE, ASN];"
    new_geo_list = "    const geoFileNameList = [MMDB, GEOIP, GEOSITE, ASN, 'Model.bin'];"
    content = apply_snippet_replacement(content, old_geo_list, new_geo_list, "Add Model.bin to initGeo")

    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(content)

def update_bundled_assets(src_dir: str):
    if os.environ.get("SKIP_ASSET_DOWNLOAD") == "1":
        print("  [*] Skipping asset download (SKIP_ASSET_DOWNLOAD=1)")
        return
    import urllib.request
    assets_dir = os.path.join(src_dir, "assets", "data")
    if not os.path.exists(assets_dir):
        os.makedirs(assets_dir, exist_ok=True)

    files_to_fetch = {
        "ASN.mmdb": [
            "https://v6.gh-proxy.org/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/GeoLite2-ASN.mmdb",
            "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/GeoLite2-ASN.mmdb",
        ],
        "GEOIP.dat": [
            "https://v6.gh-proxy.org/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.dat",
            "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.dat",
        ],
        "GEOIP.metadb": [
            "https://v6.gh-proxy.org/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.metadb",
            "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.metadb",
        ],
        "GEOSITE.dat": [
            "https://v6.gh-proxy.org/https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat",
            "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat",
        ],
        "Model.bin": [
            "https://v6.gh-proxy.org/https://github.com/vernesong/mihomo/releases/download/LightGBM-Model/Model.bin",
            "https://github.com/vernesong/mihomo/releases/download/LightGBM-Model/Model.bin",
        ],
    }

    print("[*] Updating bundled GEO and Smart Model assets in assets/data/...", flush=True)
    for filename, urls in files_to_fetch.items():
        out_path = os.path.join(assets_dir, filename)
        success = False
        for url in urls:
            try:
                print(f"  [-] Downloading {filename} from {url}...", flush=True)
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = resp.read()
                    if len(data) > 1024:
                        with open(out_path, "wb") as f:
                            f.write(data)
                        print(f"  [+] Saved {filename} ({len(data)} bytes)", flush=True)
                        success = True
                        break
            except Exception as e:
                print(f"  [!] Failed {url}: {e}", flush=True)
        if not success:
            if os.path.exists(out_path):
                print(f"  [*] Retained existing {filename}", flush=True)
            else:
                print(f"  [!] Warning: Could not download {filename} and no existing file exists", flush=True)

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
    patch_proxy_helpers(src_dir)
    patch_general_views(src_dir)
    patch_network_views(src_dir)
    patch_dashboard_intranet_ip(src_dir)
    patch_dashboard_current_outbound(src_dir)
    patch_resources_view(src_dir)
    patch_setup_actions(src_dir)
    patch_controller_dart(src_dir)
    update_bundled_assets(src_dir)
    print("[+] Source patching complete!")

if __name__ == "__main__":
    main()
