# JC Blender 小插件合集

保存当前定稿的 Blender 小插件：可直接安装的 ZIP、对应源码、中文说明和校验值。

## 当前最终版

| 插件 | 版本 | 安装包 | 源码与说明 |
| --- | --- | --- | --- |
| JC Blender Agent | 0.1.5 | [下载 ZIP](packages/JC-Blender-Agent-0.1.5.zip) | [源码 / 说明](plugins/jc-blender-agent/) |
| JC 历史记录 | 1.0.1 | [下载 ZIP](packages/JC_History_1.0.1_Blender52.zip) | [源码 / 说明](plugins/jc-history/) |
| JC 六向视图导航 | 1.1.0 | [下载 ZIP](packages/JC-View-Navigator-1.1.0.zip) | [源码 / 说明](plugins/jc-view-navigator/) |

- **Agent**：Codex / Claude Code / API 接入 Blender 的 MCP 控制链，支持模型列表、附件路径引用、本机 API 配置保存，以及可开关、随插件携带的产品渲染经验库。Claude Code 的真实账号联调边界见插件说明。
- **历史记录**：原生撤销历史常驻面板、命名场景快照、恢复前备份；1.0.1 过滤没有变化的点击选择，保留有效选择与原生拖动流程。
- **六向视图**：在原生导航区使用 Blender 原生轴球绘制；六个固定端点一键切换正、后、左、右、俯、仰正交视图，重复点击不翻转，可切回原生导航。

这些安装包均来自对应项目的最终发行文件，逐项核对了安装包内容与源码。具体兼容性和功能限制以各插件说明为准；本机验证环境为 **Windows / Blender 5.2.1 LTS**。归档日期：2026-11-08。

## 安装

1. 从上表打开安装包文件，点击 **Download raw file / 下载原始文件**，或从本仓库 Releases 下载安装包。
2. Blender → 编辑 → 偏好设置 → 插件 → 右上角菜单 → 从磁盘安装。
3. 选择对应 ZIP，不解压，然后启用插件。

不要将整个仓库的 “Download ZIP” 当作 Blender 安装包；三个插件分别安装。

换电脑时可直接下载安装包。Agent 的渲染经验库已随包携带；API Key、Agent 登录与个人配置需要在新电脑自行设置，不会通过仓库同步。

## 源码与重新构建

```text
packages/                       当前安装包（含保留的历史版本）
plugins/jc-blender-agent/        Agent 源码、经验库、文档、测试及构建脚本
plugins/jc-history/              历史记录源码、文档、测试及构建脚本
plugins/jc-view-navigator/       六向视图源码、文档及构建脚本
catalog.json                    版本、文件大小和 SHA-256 清单
SHA256SUMS                      安装包校验值
scripts/verify_packages.py       校验安装包、源码与 Python 语法
```

先运行安装包和源码检查：

```bash
python scripts/verify_packages.py
```

在各插件目录运行其构建脚本，产物生成在各自的 `dist/`：

```bash
python plugins/jc-blender-agent/build_release.py
python plugins/jc-history/build.py
python plugins/jc-view-navigator/build.py
```

构建脚本仅依赖 Python 标准库；插件功能验证需要 Blender，Agent 的部分测试另有测试依赖。重新构建不会自动替换这里归档的安装包。

仓库不包含 API 密钥、登录凭据、插件运行目录、个人配置、操作历史、场景快照、原始模型或视频。经验库内的案例缩略图属于插件本身的已打包资源。

各插件许可证保留在对应源码目录中。
