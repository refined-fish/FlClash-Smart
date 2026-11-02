# FlClash-Smart

[![Sync & Build](https://github.com/refined-fish/FlClash-Smart/actions/workflows/sync-and-build.yml/badge.svg)](https://github.com/refined-fish/FlClash-Smart/actions/workflows/sync-and-build.yml)
[![Latest Release](https://img.shields.io/github/v/release/refined-fish/FlClash-Smart?label=Release&color=blue)](https://github.com/refined-fish/FlClash-Smart/releases/latest)

> 🚀 **全自动构建与发布**：持续跟踪 [chen08209/FlClash](https://github.com/chen08209/FlClash) 官方发布与 [vernesong/mihomo](https://github.com/vernesong/mihomo) Smart 内核更新。每 24 小时自动检测，全自动编译并发布集成 **Smart 智能策略组**的 **Windows** 与 **Android** 客户端安装包。

---

## 💡 特性与改进

1. **原生集成 Smart 内核**：
   * 原生支持 `type: smart` 策略组与预训练 **LightGBM 机器学习模型**，综合考量节点延迟、历史丢包率与成功率自动动态选优。
2. **包含官方级安装包（开箱即用，无需手动替换）**：
   * **Windows**：提供 `Setup.exe` 安装包（自动创建快捷方式与卸载程序）和绿色便携版 `.zip`。
   * **Android**：提供主流 `arm64-v8a`、`armeabi-v7a`、`x86_64` 的完整 Release APK 安装包，下载直接安装启动。
3. **原生重定向应用内更新**：
   * 客户端源码层已将更新检测地址重定向至本仓库 `refined-fish/FlClash-Smart`。
   * 当本仓库有新构建发布时，客户端内点击“检查更新”或自动更新会直接提示并从本仓库下载最新 Smart 版本，不再跳回原项目。
4. **解绑强制修改 & UI 全面适配“不修改”**：
   * 借鉴 **Nikki** 的非侵入设计哲学，客户端主要负责流量控制与必要生命周期，**不再无脑覆盖或破坏内核配置**。
   * **端口与覆写**：端口配置为 `0` 时在 UI 中统一显示为 **“不修改”**，保留订阅原有端口设定。
   * **局域网代理三态支持**：设置与仪表盘均支持选择 **“开启 / 关闭 / 不修改”**，保持与配置一致体验。
   * **外部控制器与秘钥解绑**：外部控制器开关关闭时显示 **“不修改 (跟随配置)”**，保留隐藏的秘钥编辑入口，允许在不强制接管控制器开关的前提下自由配置秘钥，且关闭时绝不再清空已有秘钥。
5. **优化默认行为**：
   * 默认**关闭系统代理**（防止启动时意外全局接管）。
   * 默认**开启仅统计代理流量**。
   * 默认**开启日志捕获**。
   * 默认**开启资源自动更新开关**。
6. **资源加速镜像与 Smart MODEL 专区**：
   * Geo 资源下载默认前缀拼接高速加速代理（`https://v6.gh-proxy.org/`）。
   * 资源管理页面加入 **“覆写资源链接”** 开关（默认关闭，不侵入订阅自带的资源下载源）。
   * 新增 **Smart 专区分栏**：配置与维护 `MODEL`（`lgbm-url`，LightGBM 模型文件 `Model.bin`），在“更新全部”时同步拉取更新。
7. **仪表盘体验升级**：
   * 内网 IP 卡片实时准确显示局域网代理的**当前实际运行状态**（开启/关闭），点击卡片可随时在“开启 / 关闭 / 不修改”间自由切换。
   * 内网 IP 卡片右上角集成**Web 控制面板快捷按钮**，点击即可在默认浏览器中一键打开 `127.0.0.1:<端口>/ui`（自动携带控制器秘钥）。
8. **特殊适配 vernesong 覆盖式内核发布**：
   * 针对 vernesong 的 `Prerelease-Alpha` 覆盖式发布机制，通过动态抓取 Commit SHA 进行比对，确保任何一方有新提交都会自动触发构建。

---

## 📥 下载与安装

前往 👉 [**Releases 页面**](https://github.com/refined-fish/FlClash-Smart/releases) 下载最新版本。

| 操作系统 | 适用设备 | 文件名 | 说明 |
| :--- | :--- | :--- | :--- |
| **Windows** | 64 位电脑 (x64) | `FlClash-*-windows-amd64-setup.exe` | **推荐**，安装向导程序，双击直接安装 |
| **Windows** | 64 位电脑 (x64) | `FlClash-*-windows-amd64.zip` | 绿色便携版，解压即用 |
| **Android** | 绝大多数安卓手机 | `FlClash-*-android-arm64-v8a.apk` | **推荐**，64位手机安装包，直接安装 |
| **Android** | 老旧设备/电视盒子 | `FlClash-*-android-armeabi-v7a.apk` | 32位架构设备安装包 |
| **Android** | 电脑模拟器 / 平板 | `FlClash-*-android-x86_64.apk` | x86_64 架构安装包 |
| **Windows (独立内核)** | 已有客户端用户 | `FlClashCore-windows-amd64.exe` | 独立 Smart 内核，重命名为 `FlClashCore.exe` 替换现有安装目录 |

---

## ⚙️ 自动化构建机制

* **定时检测**：每 24 小时（UTC 00:00）自动运行 GitHub Actions 检查上游 FlClash 与 vernesong Smart 内核变动。
* **版本比对**：
  * FlClash 官方 Release Tag（如 `v0.9.2`）
  * vernesong/mihomo `Prerelease-Alpha` 内核 Commit 哈希（如 `77af480`）
  * 组合生成专属版本号：`v0.9.2-smart-77af480`
* **按需构建**：当且仅当任意一方有新版本时触发云端完整构建，也支持在 GitHub Actions 页面手动点击触发（Workflow Dispatch）。

---

## 💖 致谢

* [chen08209/FlClash](https://github.com/chen08209/FlClash) - 优秀的跨平台客户端
* [vernesong/mihomo](https://github.com/vernesong/mihomo) - 强大的 Smart 智能策略组内核
* [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) - 核心基础协议库
