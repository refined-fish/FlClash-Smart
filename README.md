# FlClash-Smart

[![Sync & Build](https://github.com/refined-fish/FlClash-Smart/actions/workflows/sync-and-build.yml/badge.svg)](https://github.com/refined-fish/FlClash-Smart/actions/workflows/sync-and-build.yml)
[![Latest Release](https://img.shields.io/github/v/release/refined-fish/FlClash-Smart?label=Release&color=blue)](https://github.com/refined-fish/FlClash-Smart/releases/latest)

> 🚀 **全自动跟踪构建**：持续跟踪 [chen08209/FlClash](https://github.com/chen08209/FlClash) 官方发布与 [vernesong/mihomo](https://github.com/vernesong/mihomo) Smart 内核更新，通过 GitHub Actions 全自动编译并发布集成 **Smart 智能策略组**的 FlClash 客户端与独立内核。

---

## 💡 为什么需要本项目？

[FlClash](https://github.com/chen08209/FlClash) 桌面端为了实现高性能与安全通信，采用了**私有本地 IPC 命名管道架构**。其内置的 `FlClashCore.exe` 是通过私有框架编译的守护进程，而不是通用的 `mihomo.exe`。

如果直接拿网上下载的通用 Smart 内核（`mihomo.exe`）覆盖 `FlClashCore.exe`，会导致**管道参数不匹配、握手失败、内核无法启动**。

本项目通过 GitHub Actions 自动化工作流：
1. **自动感知上游更新**：同时监测 FlClash 官方最新 Release 与 vernesong Smart 内核（特殊覆盖式 `Prerelease-Alpha` 版本的 Commit 变化）。
2. **源码级整合编译**：拉取 FlClash 核心与 vernesong Smart 分支源码，自动解决合并冲突并编译出原生适配 FlClash IPC 通信协议的 `FlClashCore.exe`。
3. **注入打包与发布**：将最新编译的 Smart 内核注入官方 Windows 安装/便携包中，并提供独立内核下载。

---

## 📥 下载与使用

前往 👉 [**Releases 页面**](https://github.com/refined-fish/FlClash-Smart/releases) 下载最新构建。

每个 Release 提供以下两类资源：

### 1. 完整绿色便携版（推荐）
* **`FlClash-*-windows-amd64-smart.zip`** (x64 平台)
* **`FlClash-*-windows-arm64-smart.zip`** (ARM64 平台)

**使用方法：**
下载后解压到任意目录，直接双击运行 `FlClash.exe` 即可使用，已内置 Smart 内核，支持 `type: smart` 策略组与智能选路。

### 2. 独立内核文件（适合已有 FlClash 用户）
* **`FlClashCore-windows-amd64.exe`**
* **`FlClashCore-windows-arm64.exe`**

**替换方法：**
1. 完全退出正在运行的 FlClash（在任务栏托盘中右键退出，并在任务管理器确认无 `FlClash.exe` 和 `FlClashCore.exe` 进程）。
2. 将下载的 `FlClashCore-windows-*.exe` 重命名为 **`FlClashCore.exe`**。
3. 复制并替换到 FlClash 的安装目录中（例如 `C:\Program Files\FlClash\FlClashCore.exe`）。
4. 重新启动 FlClash 即可。

---

## ⚙️ 自动化构建机制

* **定时检测**：每 6 小时自动运行一次 GitHub Actions 工作流。
* **版本比对**：
  * FlClash 官方 Release Tag（如 `v0.9.2`）
  * vernesong/mihomo `Prerelease-Alpha` 内核 Commit 哈希（如 `77af480`）
  * 组合生成专属版本号：`v0.9.2-smart-77af480`
* **智能跳过/触发**：仅在发现任意一方有新提交或新版本时才触发编译，避免重复构建；同时也支持在 Actions 页面手动点击触发（Workflow Dispatch）。

---

## 💖 致谢

* [chen08209/FlClash](https://github.com/chen08209/FlClash) - 优秀的跨平台 Flutter 客户端
* [vernesong/mihomo](https://github.com/vernesong/mihomo) - 强大的 Smart 智能策略组内核
* [MetaCubeX/mihomo](https://github.com/MetaCubeX/mihomo) - 核心基础协议库
