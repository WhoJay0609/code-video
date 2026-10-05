# 来源与设计归属

本技能使用原始编写的工作流、示例和工具，综合浏览器动画、程序化视频和渲染工具的官方资料。未复制原作者的完整提示词、作品或第三方库源码。原提示词仓库是视觉方法的一个来源。

## 生态调研与采用记录

2026-10-05 的 [选型比较](library-selection.md) 覆盖 16 个代表性项目；[维护快照](ecosystem-snapshot.json) 记录公共 GitHub 元数据。没有用星数推断质量，没有把读过文档写成运行过库。第三方版本、许可和网页内容可能变化；实施时沿官方来源复核。

| 来源与观察 | 本技能采用的方法 | 实现与验证入口 |
| --- | --- | --- |
| [Remotion 帧驱动属性](https://www.remotion.dev/docs/animating-properties) 把属性表示为当前帧的函数 | 预览和 PNG 导出共用时间函数；不让墙钟或回调决定导出内容 | `scripts/capture_video.py --frames`；检查帧数、编号和中段像素。未运行 Remotion。 |
| [Motion Canvas flow](https://motioncanvas.io/docs/flow/) 和 [time events](https://motioncanvas.io/docs/time-events/) 明确串行、并行及可编辑 cue | 为动作定义命名时间点，区分动作与阅读停留，旁白变化通过时间标记传播 | `SKILL.md` 分镜步骤；两个原创样例的场景编排。未运行 Motion Canvas。 |
| [Anime.js seek 示例](https://animejs.com/documentation/timeline/timeline-methods/seek/) 用一条时间轴编排错开对象，并以滑块定位 | 统一时钟、显式单位、暂停库自身驱动；事件副作用不承担可见状态 | `timeline-adapters.md`；原生 WAAPI 的 UI Morph 用相同原则。未运行 Anime.js。 |
| [WAAPI currentTime](https://developer.mozilla.org/en-US/docs/Web/API/Animation/currentTime) 可设置暂停动画的位置；[Playwright 截图说明](https://playwright.dev/python/docs/api/class-locator#locator-screenshot-option-animations) 解释禁用动画会快进有限动画 | 用 `animations="allow"` 保留已定位画面，修正旧截图行为 | `capture_video.py`、`check_runtime.py` 的 WAAPI 回归场景。 |
| [D3 transition](https://d3js.org/d3-transition) 与 [Three.js 官方角色示例](https://github.com/mrdoob/three.js/blob/dev/examples/webgl_animation_skinning_morph.html) 分别呈现 DOM 过渡和动作状态/强调姿态 | 保留对象身份；明确增量更新、淡化权重与一次性状态不能直接当作随机定位接口 | `timeline-adapters.md`、`motion-direction.md`。接口适配建议；未运行 D3 或 Three.js。 |
| [Tone 同步示例源码](https://github.com/Tonejs/tonejs.github.io/blob/master/examples/animationSync.html) 分开音频调度和屏幕绘制 | 声音用音频时刻，视觉通过同一映射同步；定位与重播需要同时更新声音 | `timeline-adapters.md` 声画时标。当前样例无声，Tone 路线未实测。 |
| [Mediabunny 写文件](https://mediabunny.dev/guide/writing-media-files) 和 [WebCodecs 指南](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API/Using_the_WebCodecs_API) 区分编码和封装 | 浏览器编码先探测能力，再处理时间戳、队列、资源释放和容器完成 | `browser-runtime.md` 按需编码分支；文档路线，未运行编码器。 |
| [FFmpeg image2](https://ffmpeg.org/ffmpeg-formats.html) 与 [Blender 输出说明](https://docs.blender.org/manual/en/5.1/render/output/properties/output.html) 支持先出帧再编码 | 保留图像序列便于恢复；编码前查实际二进制能力并明确音轨长度 | `--frames` 和运行参考。PNG 路径有检查；FFmpeg/Blender 编码未实测。 |

实际检查命令、环境和结果集中在 [validation](../docs/validation.md)，避免把建议与已观察行为混在一起。

## 原提示词集合

- 仓库：[joeseesun/opus-video-prompts](https://github.com/joeseesun/opus-video-prompts)
- 阅读日期：2026-10-04
- 参考版本：`7977c807781d4ba7c235247b8899a72575a30d00`
- 原提示词与视频归各作者；仓库是整理索引。作者关于耗时、费用或模型效果的描述未作为本技能的效果保证。

## 对应设计机制

| 本技能分支 | 仓库案例 | 原作者/归属 |
|---|---|---|
| 动态字体与作品集 | [02 motion showreel](https://github.com/joeseesun/opus-video-prompts/blob/7977c807781d4ba7c235247b8899a72575a30d00/prompts/02-motion-showreel-15s.md) | Stephan Livera |
| 科普与线稿 | [03 中华五千年](https://github.com/joeseesun/opus-video-prompts/blob/7977c807781d4ba7c235247b8899a72575a30d00/prompts/03-china-5000-years-lineart.md)、[05 Transformer](https://github.com/joeseesun/opus-video-prompts/blob/7977c807781d4ba7c235247b8899a72575a30d00/prompts/05-transformer-explainer-js.md) | WY；宝玉，由仓库转引 YouMind |
| 多尺度连续推镜 | [06 房间到夸克](https://github.com/joeseesun/opus-video-prompts/blob/7977c807781d4ba7c235247b8899a72575a30d00/prompts/06-room-to-quarks-zoom.md) | Taelin，由仓库转引 YouMind 的中文转述 |
| UI 形态连续变化 | [15 UI morph loop](https://github.com/joeseesun/opus-video-prompts/blob/7977c807781d4ba7c235247b8899a72575a30d00/prompts/15-ui-morph-loop.md) | zero / @twoclipping |
| 极简产品片与时间渲染 | [16 high-end product](https://github.com/joeseesun/opus-video-prompts/blob/7977c807781d4ba7c235247b8899a72575a30d00/prompts/16-high-end-product-video.md) | zero / @twoclipping，由仓库转引 YouMind |
| 像素动画 | [17 pixel wizard](https://github.com/joeseesun/opus-video-prompts/blob/7977c807781d4ba7c235247b8899a72575a30d00/prompts/17-pixel-wizard.md) | Majid Manzarpour |
| 程序化 3D | [18 prehistoric island](https://github.com/joeseesun/opus-video-prompts/blob/7977c807781d4ba7c235247b8899a72575a30d00/prompts/18-prehistoric-island-threejs.md) | Vib3Coded |

保留的是场景编排、主体变形、时间确定性、按题材选路线和看片修正等方法。原仓库模板中的固定场景数、特定 BPM、审批步骤和效果禁用清单没有变成所有作品的强制要求。

## 技术文档

实施对应路线时按实际版本查官方文档：

- [Playwright Python：视频录制](https://playwright.dev/python/docs/videos)、[浏览器](https://playwright.dev/python/docs/browsers)、[截图](https://playwright.dev/python/docs/screenshots)
- [MDN：Canvas](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)、[requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
- [FFmpeg 文档](https://ffmpeg.org/ffmpeg.html)
- [Remotion 文档](https://www.remotion.dev/docs/)、[Manim 文档](https://docs.manim.community/)、[Three.js 文档](https://threejs.org/docs/)
