# 按制作需求选择工具

调研日期：**2026-10-05**。这是 16 个代表性项目及浏览器原生 API 的定向比较，覆盖创作、排演、渲染、声音与编码，不是全网项目清单或性能排名。第三方路线均为**官方资料研究，未在本仓库安装运行**。本仓库实测范围见 [validation](../docs/validation.md)。

先确定作品需求，再选一条主路线。普通短片保留 HTML + Canvas/SVG/WAAPI 默认方案；已有工程沿用其工具链。只为实际缺失的能力增加依赖。下表的成本描述来自运行环境要求，是定性判断，不是本机基准。

## 浏览器画面与时间轴

| 项目 | 适合什么画面 / 依赖 | 时间与导出边界 | 许可来源 |
| --- | --- | --- | --- |
| [Anime.js](https://github.com/juliangarnier/anime) | UI 状态编排、SVG 揭示、对象属性 tween；JS 包，无需 React | Timeline 可定位；若对象用于 Canvas，仍需自行绘制。视频编码需其他工具。[seek 示例](https://animejs.com/documentation/timeline/timeline-methods/seek/) | [MIT](https://github.com/juliangarnier/anime/blob/master/LICENSE.md) |
| [GSAP](https://github.com/greensock/GSAP) | DOM/SVG、命名标签、复杂错开动作；JS 包 | Timeline 适合精细编排；视频场景须抑制事件副作用并自行捕获。[Timeline](https://gsap.com/docs/v3/GSAP/Timeline/) | [Standard No Charge License](https://gsap.com/community/standard-license/)；有用途限制，不能称为 MIT。作为源可见对照项纳入本表。 |
| [Motion](https://github.com/motiondivision/motion) | 网页 UI、DOM/SVG、React 项目；独立 JS 或 React 入口 | 支持序列和控制器时间；部分路径使用 WAAPI，截图需要保持所选 playhead。[animate](https://motion.dev/docs/animate) | [MIT](https://github.com/motiondivision/motion/blob/main/LICENSE.md)；这里指开源核心，不把额外产品一概纳入。 |
| [Three.js](https://github.com/mrdoob/three.js) | 浏览器真实 3D、相机、灯光和模型；ESM、模型/纹理、WebGL 环境 | Mixer 可设时间；相机和程序对象也要由 `t` 求值。性能与素材、阴影和硬件相关。[Mixer](https://threejs.org/docs/pages/AnimationMixer.html) | [MIT](https://github.com/mrdoob/three.js/blob/dev/LICENSE)；模型/贴图另行核对。 |
| [PixiJS](https://github.com/pixijs/pixijs) | 精灵密集的 2D、粒子、分层视差、像素作品；JS 和素材包 | 初始化异步，默认 Ticker 自动推进；视频需停 Ticker、按时间赋值并渲染。[Application](https://pixijs.com/8.x/guides/components/application) | [MIT](https://github.com/pixijs/pixijs/blob/dev/LICENSE) |
| [p5.js](https://github.com/processing/p5.js) | 程序绘画、几何与纹理草图；JS，按需 WebGL | `noLoop`/`redraw` 可接到外部时钟；累计位置和随机消费顺序要重写为可复现求值。[redraw](https://p5js.org/reference/p5/redraw/) | [LGPL-2.1](https://github.com/processing/p5.js/blob/main/license.txt) |
| [D3](https://github.com/d3/d3) | 真实数据、图表、排序和注释；整包或独立模块 | 视频帧可用 scale/shape/interpolate/ease 直接求属性。普通 transition 并非视频随机定位接口；此适配是基于 API 的推断。[transition](https://d3js.org/d3-transition) | [ISC](https://github.com/d3/d3/blob/main/LICENSE) |
| [lottie-web](https://github.com/airbnb/lottie-web) | 已有 Lottie/Bodymovin 图标和路径素材；JS、JSON 及素材 | 可按时间/帧定位，支持 SVG/Canvas 等渲染；它播放预制动画，不替代主场景创作。[API](https://github.com/airbnb/lottie-web#usage) | [MIT](https://github.com/airbnb/lottie-web/blob/master/LICENSE.md)；动画文件和图片许可独立。 |

GSAP 的官方许可对特定竞争性无代码工具设限。依据 [OSI 开源定义第 6 条](https://opensource.org/osd)，本技能将其归为源可见而非 OSI 开源；这是基于许可文本的归类判断。采用时重新核对当前条款。

## 程序化视频、声音与编码

| 项目 | 适合什么需求 / 依赖 | 时间与导出边界 | 许可来源 |
| --- | --- | --- | --- |
| [Remotion](https://github.com/remotion-dev/remotion) | React 组件式场景、参数化批量视频；Node/React、浏览器和渲染二进制 | 当前帧驱动组件，原生 Composition/Player/renderer 管理时长、媒体和导出；异步资源要阻塞渲染。[基础](https://www.remotion.dev/docs/the-fundamentals) · [等待资源](https://www.remotion.dev/docs/delay-render) | [自定义许可](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md)，非 OSI 开源；免费和 Company License 的适用范围按团队和用途核对 [FAQ](https://www.remotion.dev/docs/license/faq)。 |
| [Motion Canvas](https://github.com/motion-canvas/motion-canvas) | 旁白、矢量讲解、可编辑镜头排演；TypeScript、编辑器工具链 | 生成器描述顺序/并行动作，cue 标记可随旁白调整。沿用原生预览/渲染器；图像序列与视频导出各有路径。[flow](https://motioncanvas.io/docs/flow/) · [time events](https://motioncanvas.io/docs/time-events/) · [rendering](https://motioncanvas.io/docs/rendering/) | [MIT](https://github.com/motion-canvas/motion-canvas/blob/main/LICENSE) |
| [Manim Community](https://github.com/ManimCommunity/manim) | 数学公式、几何与科学图解；Python 和渲染依赖，TeX 按对象需要配置 | Scene 编排动画与声音；保留 Python 场景，不为通用 HTML 接口改写工程。[Scene](https://docs.manim.community/en/stable/reference/manim.scene.scene.Scene.html) · [安装](https://docs.manim.community/en/stable/installation.html) | [MIT](https://github.com/ManimCommunity/manim/blob/main/LICENSE) |
| [Blender](https://github.com/blender/blender) | 电影镜头、光照、材质、建模与已有 3D 资产；原生应用，渲染成本按场景决定 | 关键帧/F 曲线与帧号驱动；先烘焙模拟，图像序列便于恢复和重新编码。[CLI 渲染](https://docs.blender.org/manual/en/5.2/advanced/command_line/render.html) | [GPL 系列 / 组件说明](https://developer.blender.org/docs/license/)；软件许可与创作产物许可有区别。 |
| [Tone.js](https://github.com/Tonejs/Tone.js) | 浏览器音乐、节拍和音效排程；Web Audio/JS、用户手势 | 音频用 Transport 回调的音频时刻，视觉经 Draw 对齐；不是视频编码器。[同步示例源码](https://github.com/Tonejs/tonejs.github.io/blob/master/examples/animationSync.html) | [MIT](https://github.com/Tonejs/Tone.js/blob/dev/LICENSE.md) |
| [Mediabunny](https://github.com/Vanilagy/mediabunny) | 浏览器读取、编码和封装媒体；JS，编码器依赖运行环境 | CanvasSource 按显式时间戳供帧；Output 完成容器。探测格式支持，长输出选择文件/流目标，避免全量驻内存。[写媒体](https://mediabunny.dev/guide/writing-media-files) · [媒体源](https://mediabunny.dev/guide/media-sources) | [MPL-2.0](https://github.com/Vanilagy/mediabunny/blob/main/LICENSE) |
| [FFmpeg](https://github.com/FFmpeg/FFmpeg) | PNG 序列编码、音视频合成、转码；本机二进制 | 输入帧率、流映射、音轨长度策略必须明确。先探测实际 encoders/formats；不能假设存在 libx264。[image2](https://ffmpeg.org/ffmpeg-formats.html) · [CLI](https://ffmpeg.org/ffmpeg.html) | [LGPL / GPL 随构建变化](https://ffmpeg.org/legal.html) |
| [ffmpeg.wasm](https://github.com/ffmpegwasm/ffmpeg.wasm) | 明确要求在用户浏览器内转码；JS wrapper + 独立 WASM core | 有额外下载和内存成本，多线程需要 SharedArrayBuffer/跨源隔离。普通静态 HTML 展示不需要它。[usage](https://ffmpegwasm.netlify.app/docs/getting-started/usage/) · [FAQ](https://ffmpegwasm.netlify.app/docs/faq/) | [MIT wrapper](https://github.com/ffmpegwasm/ffmpeg.wasm/blob/main/LICENSE)；core 跟随其 FFmpeg 及依赖许可。 |

原生 [WebCodecs](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API) 提供编码帧/块，不直接生成可播放 MP4/WebM 容器。部署前探测编码器和安全上下文，选择封装器。Canvas captureStream/MediaRecorder 属于实时流路径，不应据此承诺精确逐帧文件。

## 维护快照

以下为调研日观察，不是升级推荐。仓库均未归档，结构化证据及 API 路径见 [ecosystem-snapshot.json](ecosystem-snapshot.json)。GitHub release 列表、包管理器版本和源码推送是不同信号；较旧 release 不足以认定项目停止维护。

| 项目 | 观察到的发布或活动 |
| --- | --- |
| Anime.js | [v4.5.0](https://github.com/juliangarnier/anime/releases/tag/v4.5.0)，2026-06-22 |
| GSAP | 本次 GitHub releases 查询为空；最近 push 2026-04-13 |
| Motion | 本次 GitHub releases 查询为空；最近 push 2026-10-05 |
| Three.js | [r186](https://github.com/mrdoob/three.js/releases/tag/r186)，2026-09-24 |
| PixiJS | [v8.22.0](https://github.com/pixijs/pixijs/releases/tag/v8.22.0)，2026-10-01 |
| p5.js | [v2.3.4](https://github.com/processing/p5.js/releases/tag/v2.3.4)，2026-09-25 |
| D3 | [v7.9.0](https://github.com/d3/d3/releases/tag/v7.9.0)，2024-03-12；最近 push 2026-05-28 |
| lottie-web | 本次 GitHub releases 查询为空；最近 push 2025-09-01 |
| Remotion | [v4.0.532](https://github.com/remotion-dev/remotion/releases/tag/v4.0.532)，2026-10-01 |
| Motion Canvas | 稳定发布 [v3.17.2](https://github.com/motion-canvas/motion-canvas/releases/tag/v3.17.2)，2024-12-14；release 列表首项为 [v3.18.0-alpha.0](https://github.com/motion-canvas/motion-canvas/releases/tag/v3.18.0-alpha.0)，2025-02-16；最近 push 2026-07-02 |
| Manim Community | [v0.21.0](https://github.com/ManimCommunity/manim/releases/tag/v0.21.0)，2026-08-10 |
| Blender | [官方版本页](https://www.blender.org/releases/) 列 5.2.2 / LTS 4.5.14，2026-09-15 |
| Tone.js | [15.1.22 Release](https://github.com/Tonejs/Tone.js/releases/tag/15.1.22) 标注 2026-07-12；[changelog](https://github.com/Tonejs/Tone.js/blob/dev/CHANGELOG.md) 同版本标注 2025-04-27。保留差异，不推定唯一发布时间。 |
| Mediabunny | [v1.61.1](https://github.com/Vanilagy/mediabunny/releases/tag/v1.61.1)，2026-10-03 |
| FFmpeg | [官方下载页](https://ffmpeg.org/download.html) 列 9.0.2，2026-09-18 |
| ffmpeg.wasm | [wrapper v12.15](https://github.com/ffmpegwasm/ffmpeg.wasm/releases/tag/v12.15)，2025-01-07；最近 push 2026-09-29。wrapper 和 core 的版本号分开核对。 |

实际采用时，沿对应官方文档复核版本与许可，记录所用版本，并验证当前作品。不要为了追随发布日期替换一个已满足作品需求的稳定实现。
