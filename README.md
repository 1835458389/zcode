# zcode

我的 GitHub 仓库 🎉

## 关于

这个仓库连接着 ZCode 的工作区，用来存放项目和代码。

## 项目

### [floating-island-temple](floating-island-temple/) — 浮岛佛国

用 Blender Python 程序化生成的高空浮空岛屿场景：右侧岛体、北缘巨像、
左侧连续体积云海、冷灰蓝光照。包含完整生成脚本、可编辑 `.blend`、
四台检查相机，以及 1080p / 2× 成图。

```bash
git clone https://github.com/1835458389/zcode.git
cd zcode/floating-island-temple
blender -b --factory-startup --python build_scene.py -- --stage all --save scene.blend
```

详见 [项目说明](floating-island-temple/README.md)。

## 文件说明

- `README.md` — 仓库说明（你正在看的这个文件）
- `.gitignore` — 告诉 Git 哪些文件不需要上传（比如临时文件、日志）
- `floating-island-temple/` — 浮岛佛国三维场景项目
