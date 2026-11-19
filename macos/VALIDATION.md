# Apple Silicon 验证记录 · 2026-11-19

## 基线与环境

Windows 基线提交：42ae361。Agent 0.1.5 用户 ZIP 与仓库归档 SHA-256 完全一致：
`e684c59df0cbef547c1eb8961540794404b094ae62d75d46b4945f8e013b17c5`。
Mac 验证使用 GitHub 托管的原生 ARM64 macOS 15、Blender 5.2.4 LTS，不连接用户的 Mac。
Cineware S22.008 的官方库同时包含 x86_64 / arm64，转换程序原生编译为 arm64；无需 Rosetta。

## 原生 Mac 已完成

- 完整构建：Assimp 6.0.5（固定提交 392a658f9c271be965271f45e7521a1b80ea4392）及仓库 C4D 修复，独立 Python 3.13.18 / OCP 7.9.3.1.1 / Open CASCADE 7.9.3。
- 原自动导入 10 项回归通过：3DS、三种输出、缓存、中文及 emoji 路径、坏文件、错误细节、避免无效重试、取消和源文件不变。
- C4D 原有保真回归通过：三种输出再次导入，检查隐藏继承、显式可见子级、隐藏图层、隐藏面、同名不同位置零件、实例、变换及法线方向。
- STEP 原有回归通过：GLB / FBX / OBJ、带孔实体、曲面、装配、颜色、毫米 / 英寸单位、AP242、缓存、坏文件拒绝及异常面恢复检查。
- 四个插件均通过 Blender 后台注册 / 注销，Agent 找到实际 Blender.app 内的 Python。
- Agent 协议 13 项通过，使用独立 MCP SDK 客户端（mcp 1.26.0）和本地模拟 API，不访问付费账号。
- Agent 配置及两种 CLI 提示回归 3 项通过，另 1 项 Windows 凭据测试在 Mac 正确跳过。
- 登录钥匙串原生接口通过：在临时 CI 测试钥匙串中保存虚构 Key、跨进程读取、按地址隔离、删除及重复删除。未读取或写入用户真实凭据。
  [钥匙串验证运行](https://github.com/xjc991114xjc520cjq-source/jc-blender-addons/actions/runs/44452765185)。

## 最终安装包回归

- 解压到含中文和空格的新目录，使用普通 zipfile 解压（不保留 Unix 执行位），验证插件能恢复执行权限并使用随包 Python / CAD 内核。
- 真实 MAX、DAE、DXF、LWO、3MF 上游固定样例，加上自行生成的 C4D、STEP、OFF，共 8 类输入，逐一完成 GLB / FBX / OBJ，共 24 次转换和 24 次重新导入，均存在有效网格，源文件 SHA-256 保持不变。
- 5 项平台、完整格式路由、路径、Key 路由、安装包与源码 / 逐文件摘要检查通过。
- [完整 ARM64 构建和安装包验收运行](https://github.com/xjc991114xjc520cjq-source/jc-blender-addons/actions/runs/44453162831) 全部成功。
- 1.0.5 增加 Windows / Mac 默认不限时和可选单文件总时限；新版本回归结果见下方更新。

## 构建来源、包与源码

官方组件下载地址及 SHA-256 固定在 macos/build_full.py 中；SDK 只在构建临时目录使用。
各 ZIP 的 SHA-256、大小及逐文件摘要列在 packages/macos/catalog.json。
自有 / 归档 Python 源码与安装包逐项对应；第三方预编译运行时使用下载校验、包内 runtime-files.json 和逐文件摘要核对。
运行时不含 pip / ensurepip、Windows EXE / DLL / PYD、SDK 静态库、SDK 示例、用户模型或个人配置。
Python 源码保留原有字节和换行；Git 空白检查允许 CRLF 的行尾 CR，其余常规空白检查开启。

## 验证边界

扩展名能力与 Windows 的声明和读取器路线一致，不代表每种格式的所有版本或文件都成功。
MAX 不执行修改器或第三方插件；C4D 不计算程序化生成器或第三方渲染器；STEP 输出网格。
真实 Codex / Claude Code / API 账号、Finder 粘贴、真实用户钥匙串的系统授权、GPU 导航绘制和交互历史回退仍需用户本机确认。
自动检查和后台转换不构成对任意客户模型或最终界面效果的验收。
