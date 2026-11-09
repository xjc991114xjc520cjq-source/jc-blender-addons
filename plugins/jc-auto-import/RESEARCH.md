# 同类工具调研与实现选择

调研日期：2026-11-09。

| 工具 / 技术 | 可取之处 | 本插件的选择 |
| --- | --- | --- |
| [Super IO](https://github.com/atticus-lv/super_io) | 快捷复制、粘贴、导入导出与可配置流程 | 借鉴少步骤交互，不复制其界面或代码；转换能力由独立组件提供。 |
| [Drag and Drop Support](https://github.com/mika-f/blender-drag-and-drop) | 多格式拖放入口 | 使用 Blender 原生 FileHandler，避免常驻扫描鼠标 / 文件夹。 |
| [Blender FileHandler](https://docs.blender.org/api/4.2/bpy.types.FileHandler.html) | 官方拖放分发与文件导入操作符 | 原生属性弹窗、文件选择器、菜单及侧栏；兼容原生主题与 DPI。 |
| [Autodesk MAX Importer](https://extensions.blender.org/add-ons/io-scene-max/) | 直接解析 MAX 网格、材质与 UV，无需安装 Max | 携带上游读取模块，保留作者及许可，放在独立 Blender 工作进程内使用。 |
| [Assimp](https://github.com/assimp/assimp/blob/v6.0.5/doc/Fileformats.md) | 覆盖多种交换格式 | 携带静态运行库版本的命令行引擎，用 GLB 中转；必要时退回 OBJ 静态几何体恢复。 |
| [Cineware SDK](https://developers.maxon.net/topic/15247/cineware-sdk-overview/1) | 官方明确支持没有 Cinema 4D 安装时读取 C4D | 将 SDK 静态组件集成到单独可执行转换组件；不分发 SDK 压缩包、库文件、示例或文档。 |

对源码作出的 Assimp 调整：以 MSVC 2022 使用 S22 的 MSVC 2019 静态运行库；修正 Cineware 类型包装器不能按普通 RTTI 派生类型处理的问题；读取保存的缓存；设置 UV 通道分量数；UTF-8 名称。补丁随仓库保存。

接口调用不能代替真实格式兼容性验证：因此 `capabilities.json` 与 `VALIDATION.md` 分别记录引擎声明和实际检查结果。C4D / MAX 的原始软件运行路径已经从本版删除。
