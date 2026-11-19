# 验证记录 · 2026-11-19

## 基线

仓库基线：`42ae361`。用户提供的 `JC-Blender-Agent-0.1.5.zip` 与仓库归档包 SHA-256 完全一致：
`e684c59df0cbef547c1eb8961540794404b094ae62d75d46b4945f8e013b17c5`。

## 已完成（Windows 主机）

- `python macos/tests/test_macos.py`：5 项通过。覆盖模拟 Mac GUI 程序定位、可变 Python 小版本路径、钥匙串路由和地址归一化、禁止 Key 写入 JSON、基础版格式拒绝、ZIP 与源码对应及排除 Windows 运行时。
- `python macos/tests/test_agent.py`：4 项通过。覆盖地址隔离、设置白名单、Windows 测试凭据跨进程保存及删除、两种 CLI 的经验库开关。Windows 凭据测试只使用随机测试命名空间中的虚构 Key，不构成 Mac 钥匙串验证。
- `python macos/tests/test_blender.py --blender D:\Blender\blender.exe`：6 项通过。运行的是 Mac 基础版共享 Python 源码；覆盖 3DS 几何 / UV / 颜色解析、破损块拒绝、相邻纹理缓存失效、取消进程、GLB / FBX / OBJ 输出及复用缓存、保持源文件不变、失败不留成功缓存。
- `python scripts/verify_packages.py`：4 个原版包和 4 个 Mac 包的完整性、源码对应与 Python 语法均通过。
- `git diff --check`：通过。

## 尚未验证

- Apple Silicon / macOS 上安装、启用、交互、渲染和实际格式转换。
- Security.framework 钥匙串保存、读取、删除、权限拒绝及锁定钥匙串行为；当前只完成路由模拟测试。
- Finder 单文件粘贴、Codex / Claude Code 真实登录与 API 账号联调。
- Mac 原生导航绘制和历史回退、不同 Blender 版本行为。
- 本次未使用实际 MAX 模型检查 Mac 基础版；MAX 读取器沿用原版代码。

原 Windows 验证记录保留在各插件原目录，仅代表其原有验证环境。
这些 Mac 包是待实机验收的适配构建，不应标为 Mac 已验证正式版。
