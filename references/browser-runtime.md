# 浏览器实现与交付

原生 HTML、Canvas/SVG 是没有既有视频工程时的默认路线。此参考用于可播放作品及附带工具；已有工程使用其原生渲染接口。

## 场景与播放时钟

主画面放在 `[data-video-stage]` 元素里，控制条放在它之外。画面按固定逻辑尺寸绘制，展示时保持比例缩放。内嵌脚本和素材可以直接打开；本地模块或依赖需要 HTTP 时提供启动方式。资源保持在输出工程内。

附带工具读取以下接口：

```javascript
window.__video = {
  width: 1280,
  height: 720,
  duration: 15,          // 秒
  fps: 30,
  ready: Promise.resolve(),
  seek: async (seconds) => { /* 完成这一时刻的整幅画面 */ },
  play: () => { /* 从当前时间播放，结束后再次播放时重启 */ },
  pause: () => { /* 停住播放时钟 */ },
  time: 0,              // 当前实际展示的时间，随定位和播放更新
  playing: false        // 示例检查器使用的播放状态
};
```

`ready` 等待字体、图像和初始化完成；加载失败应抛出错误。`seek` 限定到 `[0,duration]`，完整绘制当前时刻；所有可见运动依赖传入时间。播放时以起始时间加 `performance.now()` 的差值得到 `t`，用 `requestAnimationFrame` 刷新。帧绘制不依赖调用次数或前一帧状态。

`?autoplay=0` 用于工具控制播放。拖动时间轴时先暂停，再定位；重播从零开始。开头或结尾有意留白时保留明确视觉设计，区分有意留白与绘制失败。运行骨架见 `../assets/starter.html`。

附带检查器使用 `[data-play]`、`[data-restart]`、毫秒范围的 `input#timeline` 和 `[data-readout]` 控件；其他工程可保留其自身控件并执行等价检查。初始化时保持一个明确的 `playing` 布尔状态或 getter。新作品的 `ready` 包含所有实际使用的异步资源，不仅是页面 `load` 事件。

### 时间函数

场景局部进度由 `(t-start)/(end-start)` 计算并夹到 `[0,1]`。进入、停留、退出分别安排。简单动作优先插值和常用缓动；弹簧使用时间解析响应，或使用支持任意帧定位的现有库。

颗粒、线稿和星空布局从固定种子预生成；位置从时间或相位求值。真实视频素材在定位时等待对应帧就绪，图片替换后等待 `decode()`；`seek` 返回之前保证画面完整。

## 附带截图与 WebM 工具

先查看 `scripts/capture_video.py --help`，确认当前实现与参数。依赖是 Python Playwright 与可运行的 Chromium；视频录制还需要 Playwright 自带的录制组件。工具不要求系统 FFmpeg。

```bash
python3 /absolute/path/to/code-video/scripts/capture_video.py \
  /absolute/path/to/project/index.html \
  --snapshots /absolute/path/to/project/preview --times 0,3,6,12

python3 /absolute/path/to/code-video/scripts/capture_video.py \
  /absolute/path/to/project/index.html \
  --output /absolute/path/to/project/preview.webm
```

工具用临时本地 HTTP 服务加载 HTML，等待 `__video.ready`，按作品尺寸截图或录制。页面 JavaScript 错误会使检查失败，需修正场景后再交付。输出路径保持不同于已有作品，避免意外覆盖。

`--times` 的秒数应替换为作品真实转场，并位于片长内；省略时只取开头、中间、结尾。它不是视觉验收所需镜头的完整列表。输出父目录先创建，已有输出不会被覆盖。

若默认浏览器路径不可用，先检查已安装浏览器与 Playwright 版本，用 `--browser /absolute/path/to/chrome` 指定可用可执行文件。在确实需要安装时，将依赖装在当前作品或隔离环境中，不替换用户全局配置。浏览器作品本身仍可在用户的浏览器播放。

WebM 由实际浏览器播放录制，不是精确逐帧编码。开头和结尾可能有少量录制余量，播放卡顿会进入录制结果，音轨不会被录入。它适合在聊天中展示无声代码动画；需要精确片长、固定帧率、无丢帧或声音时使用下一条路径。

## 精确逐帧导出

仅在交付要求需要时采用这一方案。先确认已有 FFmpeg/渲染工具；采用同一时间轴，而不是在录制失败后改写整个动画。

用附带工具输出 PNG 序列：

```bash
python3 /absolute/path/to/code-video/scripts/capture_video.py \
  /absolute/path/to/project/index.html --frames /absolute/path/to/project/frames
```

工具等待 `ready`，按逻辑尺寸与设备像素比 1 截取舞台。共 `N=ceil(duration*fps)` 帧，第 `i` 帧对应 `i/fps`，文件从 `000000.png` 连续编号；`frames.json` 记录导出参数。片长不在帧网格上时，编码片长向上取整，不超过一帧差值。默认最多 1800 帧，确需更长输出时显式设置 `--max-frames` 并确认输出空间。

定位后使用 `animations="allow"` 保留暂停的 CSS/WAAPI 画面。Playwright 的 `disabled` 会快进有限动画；它不等于“冻结当前帧”。原理见 [官方截图选项](https://playwright.dev/python/docs/api/class-locator#locator-screenshot-option-animations)。

用实际可用的编码器合成。先检查 `ffmpeg -version`、`ffmpeg -encoders` 和 `ffmpeg -buildconf`；涉及分发时再核对该构建的 `ffmpeg -L`。以下命令只适用于已有 `libx264` 的构建：

```bash
ffmpeg -framerate 30 -start_number 0 -i frames/%06d.png \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart result.mp4
```

这里的 30 必须换成作品实际帧率，H.264 的画面宽高使用偶数。编码后核对片长、尺寸、帧率和实际播放。

需要动态模糊时，只有运动主体明确需要才使用多个子时间采样。采样、模糊合成与最终帧率分开处理；静态文字可保留清晰层。实时预览先关掉昂贵采样，避免用渲染成本掩盖未解决的构图问题。

## 声音交付

浏览器中由用户点击解锁 `AudioContext` 或音频元素；播放、暂停、定位和音量同步到画面时间。无声录制不能声称已包含浏览器播放的声音。

视频文件需要声音时，将已获准使用的音轨合成到画面。按叙事安排前后静音或淡出，先确认音轨与目标时长关系。以下例子要求 `mix.wav` 已覆盖整片：

```bash
ffmpeg -i silent.webm -i mix.wav -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -pix_fmt yuv420p -c:a aac -t 15 \
  -movflags +faststart result.mp4
```

`15` 换成实际片长。完整听看最终产物，确认字幕、旁白、拍点和结尾对齐；不要仅检查文件含有音轨。

声音过短时先确定是否补静音，过长时确定裁切和淡出点。只有确实要以较短轨道结束时才使用 `-shortest`，否则可能提前截断画面。浏览器声画时钟的分工见 [timeline-adapters.md](timeline-adapters.md)。

## 按需在浏览器编码

只有需要浏览器内导出时才增加这条路线。先探测安全上下文、`VideoEncoder.isConfigSupported()` 及所需音频编码器。WebCodecs 的 `VideoFrame.timestamp` 使用微秒；作品秒时间要显式换算。限制编码队列，释放已提交的帧，等待 `flush()`，再完成容器。编码块不是可播放文件，还需要封装器。[WebCodecs 指南](https://developer.mozilla.org/en-US/docs/Web/API/WebCodecs_API/Using_the_WebCodecs_API)

Mediabunny 可接收 `CanvasSource.add(timestampSeconds, durationSeconds)`，经 Output 写入容器，最后 `finalize()`。确认目标格式支持实际编码器；较长输出采用文件或流目标，避免把全部结果放在 BufferTarget。此处是文档路线，仓库未运行该编码器。[媒体源](https://mediabunny.dev/guide/media-sources) · [写文件](https://mediabunny.dev/guide/writing-media-files)

ffmpeg.wasm 适合明确需要在客户端转码的场景，需加载独立 core；多线程还需要跨源隔离等部署配置。普通 HTML 展示不需要承担这些依赖。失败时保留已生成的画面与帧序列，报告具体不支持的格式或运行条件。

## 检查作品与交付地址

```bash
python3 /absolute/path/to/code-video/scripts/check_runtime.py \
  --html /absolute/path/to/project/index.html

python3 /absolute/path/to/code-video/scripts/check_runtime.py \
  --url https://your-public-host.example/film.html
```

本地模式检查控件与定位，并录制和回放 WebM；URL 模式在实际交付地址检查资源、定位、控件和完整播放，不再启动本地录制。`--artifacts` 可指定检查产物目录。需要时附加 `--browser`。该检查器用于上述接口和控件约定，不能替代对别的框架播放器的等价验证。

## 展示

使用当前宿主能播放的文件格式，优先直接展示作品。支持本地媒体的聊天可用：

```markdown
![动画预览](/absolute/path/to/preview.webm)
```

HTML 通过用户可访问的 HTTP(S) URL 或已验证的宿主预览展示。仅服务产物目录；源码绝对路径作为补充，不能充当用户可达证据。打开最终 URL 检查页面、资源与控件，保持发布/转发路线可用，并披露会话依赖或已知有效期。GitHub Pages 这类静态托管不依赖本地服务进程。

宿主无法直接嵌入 HTML 时，也可录制 WebM 在当前聊天展示。源码仍需保留。缺少外部发布或转发条件时，明确尚需的配置；不要把服务器内部 localhost 作为已完成的对外交付。
