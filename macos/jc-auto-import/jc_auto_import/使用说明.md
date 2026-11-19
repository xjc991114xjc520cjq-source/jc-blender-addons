# Apple Silicon（M 系列）完整适配版 · 修订 3

四类插件均面向原生 arm64 Blender。自动导入采用与 Windows 1.0.5 相同的读取器和格式能力，不再使用删减格式的基础版。
Apple Silicon 构建及格式回归的实际结果见 VALIDATION.md。

| 插件 | 基线 | Mac 适配 |
| --- | --- | --- |
| Agent | 0.1.5 | Blender.app 内 Python、CLI 定位、GUI PATH、登录钥匙串、Finder 单文件引用 |
| 历史记录 | 1.0.1 | 复用纯 Python 实现，需要 Blender 5.2+ |
| 六向视图导航 | 1.1.0 | 复用原生导航绘制，需要 Blender 4.2+ |
| 自动转换导入 | 1.0.5 | ARM64 Assimp + Cineware、ARM64 Python + Open CASCADE，需要 Blender 4.2+ |

用户提供的 Agent ZIP 与仓库 0.1.5 归档完全相同，SHA-256：
`e684c59df0cbef547c1eb8961540794404b094ae62d75d46b4945f8e013b17c5`。
原功能版本号保留，平台修订由文件名和 catalog.json 中的 edition 记录。

## 安装

使用 Blender 官方 Apple Silicon 构建。先禁用并移除同类旧版，再从「偏好设置 → 插件 → 从磁盘安装」逐个选择 Mac ZIP，重启 Blender。
插件 ZIP 不解压。整个源码包不是安装包。Mac 版与旧版使用相同 ID，不能同时启用。

自动导入组件随包携带，无需另装 C4D、3ds Max、FreeCAD、Python、Homebrew 或 Rosetta。
本机离线转换，不上传模型，不改写源文件。首次启动会恢复转换程序的执行权限。
如果 macOS 拦截运行，请按系统显示的具体提示处理；不要关闭整个系统的安全保护。

## 自动导入格式

| 来源 | 与 Windows 相同的读取路线 |
| --- | --- |
| MAX | Python MAX 读取器：可识别网格、部分基本体、基础材质、UV、层级 |
| C4D | Assimp 6.0.5 + Cineware S22.008；保留隐藏状态、普通实例、坐标和面朝向修复 |
| STP / STEP | OCP / Open CASCADE 7.9.3；装配、颜色、单位及 1.0.4 异常面恢复 |
| 3DS | Python 静态网格读取器 |
| DAE、DXF、LWO、3MF、OFF 等 | 同版 Assimp 读取器；完整扩展名清单见包内 capabilities.json |
| OBJ、FBX、GLB、glTF、STL、PLY、USD、ABC | 当前 Blender 构建自带的读取器 |

输出 GLB / FBX / OBJ，保留后台转换、缓存、取消、日志和当前场景导入。
原生格式使用插件的文件选择入口，不抢占 Blender 已有拖放处理器。

能力边界与 Windows 相同：C4D 不重新计算生成器、MoGraph 或第三方渲染器；MAX 不执行修改器、脚本或第三方插件；STEP 输出网格，不保留 CAD 参数历史。
DWG、SKP、IGES、SAT 等原版没有读取器的格式仍会明确拒绝。扩展名声明一致不代表任意文件都成功，也不等于原软件的全部格式能力。

## Agent

优先自动使用 Blender.app 自带 Python。API 模式不用另装 Python。
CLI 模式需在 Mac 安装并登录 Codex CLI / Claude Code，Windows 登录状态不迁移。
自动检查 `/opt/homebrew/bin`、`/usr/local/bin`、`~/.local/bin` 等路径；找不到时在偏好设置填写完整路径。
启用记住 Key 时仅访问当前地址对应的登录钥匙串条目，不把 Key 写入 JSON、ZIP 或 .blend。
系统可能询问访问权限；钥匙串不可用时可关闭记住 Key，临时输入或使用环境变量。
Finder 复制单文件后可粘贴附件，多文件用添加附件。
运行数据：`~/Library/Application Support/JCBlenderAgent`，可用 `JC_BLENDER_STATE` 覆盖。
真实账号、钥匙串系统授权、Finder 粘贴和最终界面效果仍需用户在自己的 Mac 确认。

## 重建

在 macOS ARM64 的仓库根目录运行：

```text
python macos/build_full.py
python macos/build.py --full
python macos/tests/test_macos.py
python macos/tests/test_agent.py
python scripts/verify_packages.py
```

下载来源和 SHA-256 固定；SDK 只在构建临时目录使用，不发布 SDK、SDK 示例或用户模型。
插件含许可证、组件来源和运行时逐文件清单。转换程序使用 Apple 系统框架和系统 zlib。
GitHub Actions 的 Build full Apple Silicon plugins 在原生 Mac 构建并运行格式回归。

## 1.0.5 大型模型转换

Windows 和 Mac 均默认不限转换总时长，保留 Esc 取消。需要限时可在偏好设置主动开启「启用单文件总时限」（最长 7 天）；读取、网格化、导出及备用转换共享单个文件的预算。旧版保存的 300 秒不会自动生效。
