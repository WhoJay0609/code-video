# 时间轴与引擎适配

需要接入动画库或修正随机定位时阅读。这里的第三方接口依据官方文档；本仓库实际运行的是原生 Canvas/SVG/Web Animations，详见 [验证记录](../docs/validation.md)。采用某个库时仍要按项目版本验证适配。

## 统一时间，而不是统一所有引擎

以秒作为作品时间 `t`，在边界转换单位。场景局部时间为 `t-start`；短片的进入、保持、退出分别求值。帧导出取 `t=i/fps`，HTML 实时播放可以按显示器刷新率绘制，二者不应混为同一个帧率保证。

每次定位完整设置位置、颜色、文字、可见性、路径进度和相机状态。将“触发了一次”改成“当前时间属于这个区间”；复用 DOM/场景对象，避免在回调里不断创建或删除主体。输出前等待字体、图片、模型、纹理和视频帧就绪。

对带历史的物理系统或状态机，从固定初态按固定步长重建，或使用与时间对应的缓存。仅固定随机种子不能修复累计积分、动作禁用状态或回调历史。

## 浏览器引擎的定位边界

| 引擎 | 时间接口 / 单位 | 适配重点 |
| --- | --- | --- |
| 原生 Web Animations | 暂停后设置 `animation.currentTime = t * 1000`，毫秒 | 先创建完整关键帧和 `fill` 策略；暂停原生驱动。截图保持当前状态，使用 `animations="allow"`。 |
| Anime.js | `timeline.seek(t * 1000, true)`，默认毫秒 | 创建时关掉自动播放。第二个参数静音回调；可见结果应来自时间轴，而不是回调副作用。若项目更改全局 timeUnit，跟随该配置转换。 |
| GSAP | `timeline.pause(); timeline.seek(t, true)`，秒 | 标签可帮助编排，定位时抑制事件。重复时间轴要区分当前轮次的 `time` 与总时间；按作品定义选择 `totalTime`。采用前阅读当前许可。 |
| Motion | 控制器 `.pause()` 后设置 `.time = t`，秒 | 独立 JS 和 React 路线不同；不要额外开启第二个 RAF 时钟。含 WAAPI 的动画同样要验证截图保持所选时间。 |
| Three.js | 停止自动 update，保持 `mixer.timeScale = 1`，再调用 `mixer.setTime(t)`，秒；随后显式渲染 | `setTime` 的输入受 mixer.timeScale 缩放，不能用设为 0 的方式暂停后直接套用此公式。还要从 `t` 设置相机、灯光和程序化对象。交叉淡化权重、一次性动作的 enabled/finished 状态也必须可重建；仅设置 mixer 时钟不保证复杂状态机可回退。 |
| PixiJS | 停止自动 Ticker；按 `t` 赋值后手动渲染 | `await app.init()` 和资源加载纳入 ready。精灵帧用相位计算；容器表达层次，避免把 delta 累积结果当作可定位状态。 |
| p5.js | `noLoop()`；设置作品时间后 `await redraw()` | 绘制从当前时间和固定种子产生，避免使用 `millis()`、累计位置或不断消耗随机序列决定画面。 |
| D3 | 固定两端数据，用插值器求当前属性并赋给 SVG | 普通 transition 按计时器和已有 DOM 状态推进。视频可使用 scale/shape/interpolate/ease，保留数据身份，用 `t` 计算当前布局。这是基于 API 的适配建议。 |
| lottie-web | 优先按素材帧率使用 `goToAndStop(t * animation.frameRate, true)` | 毫秒形式 `goToAndStop(t * 1000, false)` 还受 playSpeed 和 playDirection 缩放，仅在两者均为 1 时直接对应作品时间。等待动画数据及图片等资源完成。子帧、起始帧和能力覆盖按具体文件验证；JSON 可读不意味着其素材许可可复用。 |

官方接口：[WAAPI currentTime](https://developer.mozilla.org/en-US/docs/Web/API/Animation/currentTime)、[Anime.js seek](https://animejs.com/documentation/timeline/timeline-methods/seek/)、[GSAP Timeline](https://gsap.com/docs/v3/GSAP/Timeline/)、[Motion animate](https://motion.dev/docs/animate)、[Three AnimationMixer](https://threejs.org/docs/pages/AnimationMixer.html)、[Pixi Application](https://pixijs.com/8.x/guides/components/application)、[p5 redraw](https://p5js.org/reference/p5/redraw/)、[D3 transition](https://d3js.org/d3-transition)、[Lottie API](https://github.com/airbnb/lottie-web#usage)。

## 原生视频框架

Remotion 用当前帧求属性，让 React 组件的输出依赖帧和输入。沿用 Composition、Sequence、Player 和渲染器的原生约定。把 `frame/fps` 作为秒时钟即可，不必为视频框架重写浏览器骨架。[帧驱动属性](https://www.remotion.dev/docs/animating-properties)

Motion Canvas 用生成器表达串行、并行、错开和等待。`yield*` 的控制流与信号共同描述镜头；已有工程交给其预览/渲染器求时序。用命名事件承接旁白修改，避免将生成器误包成一个只设置外部时钟的伪 seek。[动画流程](https://motioncanvas.io/docs/flow/)

Manim 和 Blender 的帧、场景、相机及渲染器保持原生工作方式。缓存模拟再逐帧渲染。若最终产物是视频，HTML 播放器只负责展示文件，不必让 Python/Blender 工程实现 `window.__video`。

## 声画共用时标

无声作品用浏览器单调时钟驱动画面。含音乐或旁白时，先规定声音与画面的时间映射；暂停、定位和重播同时更新两者。用户点击后解锁音频，避免后台创建 AudioContext 就认定声音可播放。

排程音频使用音频时钟。Tone.Transport 回调提供精确的调度时间，音符应使用该 `time`，不要在 RAF 中临时触发。DOM 更新经 Tone.Draw 或同一时间映射安排；音频回调与屏幕刷新不是相同频率。旁白可用命名 cue 表绑定字幕与动作，改一处句长后重新检查后续镜头。[Tone Transport](https://github.com/Tonejs/Tone.js/wiki/Transport) · [视觉同步与性能](https://github.com/Tonejs/Tone.js/wiki/Performance)

离线导出不依赖实时播放能否跟上。采用确定的音轨、帧时间和时间偏移编码；最终文件需实际听看，浏览器可发声与录制文件含声音是两项不同证据。

## 最小验证

检查相同时间在 `a → b → a` 后画面一致；选择运动中段、主体变形或素材切换处。全片播放后再回退一次，尤其检查一次性动作与事件回调。再验证暂停、结尾、重播和最终导出。

若画面不一致，先查独立时钟、事件副作用、未就绪资源和未复位状态。保留失败帧便于对比；不要通过删掉运动或跳过对应镜头让检查通过。
