# Apple Silicon（M 系列）版本 · 修订 1

这是一组基于仓库当前最终版的 macOS 安装包，目标是原生 arm64 Blender。
本次在 Windows 上完成代码检查和可运行的回归检查，**尚未在 Mac 上验收**。
文件名中的 macOS 表示适配目标，不表示已经通过 Mac 实机测试。

| 插件 | 基线版本 | Mac 内容 |
| --- | --- | --- |
| Agent | 0.1.5 | 增加 Blender.app 内 Python 自动定位、Homebrew / 用户 CLI 定位、GUI PATH 补齐、登录钥匙串读写及 Finder 单文件附件引用 |
| 历史记录 | 1.0.1 | 原有纯 Python 源码，独立 Mac 命名包；需要 Blender 5.2+ |
| 六向视图导航 | 1.1.0 | 原有纯 Python 源码，独立 Mac 命名包；需要 Blender 4.2+ |
| 自动转换导入基础版 | 1.0.4 | 仅含 Python MAX / 3DS 读取器和 Blender 原生格式调用；需要 Blender 4.2+ |

上述前三类基线不改变功能版本号；平台修订由 `catalog.json` 中的 `edition` 记录。
自动导入的内部缓存版本增加 macos-basic.1，避免复用 Windows 转换结果。
Agent 0.1.5 已与用户提供的 ZIP 逐字节校验：
`e684c59df0cbef547c1eb8961540794404b094ae62d75d46b4945f8e013b17c5`。

## 安装

使用 Blender 官方 Apple Silicon 构建。逐个在「偏好设置 → 插件 → 从磁盘安装」选择对应 ZIP，不用解压。
不要安装整个源码 ZIP。若旧版已启用，先禁用并移除旧版，再安装同类 Mac 包，重启 Blender。
Mac 包与对应旧版使用同一插件 ID，不能同时启用；Windows 原有安装包继续保留。

Agent、六向导航是传统插件包；历史记录和自动导入是 Blender 扩展包。
历史记录必须使用 Blender 5.2 或更新版本，其余包最低版本为 4.2。

## Agent 配置

1. 优先自动使用 Blender.app 自带的 Python；不需要为 API 模式另装 Python。
2. 使用 CLI 模式时，在 Mac 上安装并登录 Codex CLI 或 Claude Code。Windows 登录状态不迁移。
   Finder 启动 Blender 时会额外检查 `/opt/homebrew/bin`、`/usr/local/bin`、`~/.local/bin` 等路径。
   找不到时在偏好设置手填 CLI 完整路径。自定义 Node 安装或 nvm 环境可能仍需要调整路径。
3. API 模式填写地址、模型和 Key。启用记住 Key 时只保存到当前地址对应的 macOS 登录钥匙串。
   首次读写可能弹出系统授权。取消或钥匙串锁定时可关闭记住 Key，临时输入或使用环境变量。
   Key 不写入源码、ZIP、JSON 设置或 .blend。
4. Finder 复制单个文件后可用粘贴附件；多个文件用添加附件。Finder 剪贴板读取可能触发系统权限提示。
5. 运行数据位于 `~/Library/Application Support/JCBlenderAgent`，可用 `JC_BLENDER_STATE` 覆盖。

API 及两种 CLI 的真实账号联调、钥匙串授权、Finder 附件、原生导航点击和历史记录回退，仍需要 Mac 实机确认。

## 自动导入基础版范围

- 输入：MAX（部分可识别网格、基本体、UV、材质）、3DS，以及 Blender 自带的 FBX / OBJ / GLB / glTF / STL / PLY / USD / ABC 读取器。原生读取器是否可用由 Blender 构建决定。
- 输出：GLB / FBX / OBJ。后台转换、日志、缓存、取消功能沿用原版。
- 暂不支持：C4D、STP / STEP，以及依赖 Assimp 的 DAE、DXF、LWO、3MF 等格式；DWG、SKP、IGES、SAT 也不支持。
- 不含 Windows EXE、DLL、Windows Python 或模拟运行层，不要求 Rosetta。
- MAX 不运行修改器、脚本或第三方插件，3DS 不保留完整动画。不能保证任意 MAX 文件或复杂材质都可恢复。

不支持的格式会在启动转换前拒绝；拖放只注册 MAX、3DS，其他支持格式使用文件选择入口。
Mac 完整版还需要兼容 arm64 的独立转换组件和真实样例验收，本次未提供。

## 重建和检查

在仓库根目录运行：

```text
python macos/build.py
python macos/tests/test_macos.py
python macos/tests/test_agent.py
python macos/tests/test_blender.py --blender <Blender可执行文件完整路径>
python scripts/verify_packages.py
```

`macos/build.py` 只按明确文件清单打包，在 `packages/macos/` 生成四个 ZIP、SHA256SUMS 和 catalog.json。
历史记录、六向导航复用 `plugins/` 中的原始源码；Agent 和自动导入使用本目录下的适配源码。
完整 Windows 安装包不由该构建脚本改写。
