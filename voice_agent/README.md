# Voice Agent - 语音控制模块

通过语音与机器人交互，实现自然语音控制底盘移动。

## 架构

```
麦克风 -> VAD检测 -> ASR(FunASR) -> LLM(DeepSeek) -> 底盘控制
                                         ↓
                                   TTS(edge-tts) -> 扬声器
```

## 快速启动

```bash
# 启动语音助手
conda activate xlerobot
python -u voice_agent/voice_agent.py

# 或者使用 conda run
conda run -n xlerobot python -u voice_agent/voice_agent.py
```

注意：需要 `-u` 参数确保实时输出。

## 交互流程

1. 启动后听到"小如已就绪"
2. 直接说指令（VAD 自动检测说话开始和结束）
3. 机器人执行并语音回复
4. 继续说下一条指令

## 示例指令

- "向前走三步"
- "左转"
- "后退一点"
- "右转两次"
- "停"

## VAD 参数

语音活动检测（Voice Activity Detection）参数在 `audio_utils.py`：

| 参数 | 默认值 | 说明 |
|-----|-------|------|
| speech_threshold | 80 | 音量高于此值认为开始说话 |
| silence_threshold | 50 | 音量低于此值认为静音 |
| silence_duration | 1.2秒 | 静音持续多久后结束录音 |
| max_duration | 12秒 | 最大录音时长 |

## 硬件配置

| 设备 | 配置 |
|-----|------|
| 音频设备 | plughw:1,0 (USB声卡) |
| 采样率 | 16kHz |
| 声道 | 单声道 |

如果没声音，设置音量：
```bash
amixer -c 1 set PCM 100%
```

## 依赖模型

| 组件 | 模型 | 说明 |
|-----|------|------|
| ASR | FunASR SenseVoiceSmall | 语音识别，首次运行下载约900MB |
| LLM | DeepSeek Chat | 指令理解，需联网 |
| TTS | edge-tts (XiaoxiaoNeural) | 语音合成，需联网 |

ASR 模型存储位置：`~/.cache/modelscope/hub/models/iic/SenseVoiceSmall/`

## 文件说明

| 文件 | 说明 |
|-----|------|
| voice_agent.py | 主程序入口 |
| asr.py | 语音识别模块 |
| audio_utils.py | 录音/播放/TTS/VAD |
| wake_detector.py | 唤醒词检测（当前未启用） |
| DATA_FLOW.md | 详细数据流文档 |

## 命令行参数

| 参数 | 说明 |
|-----|------|
| --mock | 模拟模式，不连接真实机器人 |
| --no-wake | 跳过唤醒词（当前默认已跳过） |
