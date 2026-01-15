# RoboCrew 视觉语音Agent

视觉-语言-动作闭环控制的机器人Agent。

## 运行环境

使用 **xlerobot** 环境：
```bash
conda activate xlerobot
```

## 快速开始

```bash
cd ~/XLeRobot

# 语音交互
/home/sunrise/miniconda3/envs/xlerobot/bin/python -u robocrew/agent.py

# 文本交互
/home/sunrise/miniconda3/envs/xlerobot/bin/python -u robocrew/agent.py --text

# 模拟模式
/home/sunrise/miniconda3/envs/xlerobot/bin/python -u robocrew/agent.py --mock --task "走到桌子前面"
```

## 架构说明

### 模型分工

| 模型 | 提供商 | 作用 | 调用时机 |
|------|--------|------|----------|
| **Qwen-VL** | 阿里云百炼 | 视觉理解 | 每次`look_around()`，看图描述场景 |
| **DeepSeek** | DeepSeek | 推理决策 | 整个任务过程，决定动作、调用工具 |
| **FunASR** | 本地 | 语音识别 | 用户说话时，语音→文字 |
| **edge-tts** | 微软 | 语音合成 | 回复时，文字→语音 |

### 执行流程

以"向右转找人"为例：

```
1. 用户说话: "向右旋转直到找到穿白衣服的人"
      ↓
2. FunASR: 语音 → 文字
      ↓
3. Qwen-VL: 拍照 → "办公室内，中央有桌子..."（初始场景）
      ↓
4. DeepSeek: 收到[任务+场景]，决定 → 调用 look_around()
      ↓
5. Qwen-VL: 拍照 → 返回场景描述
      ↓
6. DeepSeek: 没看到人 → 调用 turn_right(6) 转90度
      ↓
7. 电机执行: 实际转动
      ↓
8. DeepSeek: 调用 look_around()
      ↓
9. Qwen-VL: 拍照 → 返回新场景
      ↓
10. DeepSeek: 还没看到 → 继续 turn_right(6)
      ↓
    ... 循环 ...
      ↓
11. Qwen-VL: "前景有一戴眼镜男子..."
      ↓
12. DeepSeek: 看到目标！→ 调用 task_complete("已找到...")
      ↓
13. edge-tts: 文字 → 语音播报
```

### 核心代码逻辑

```python
# 1. 获取初始视觉 (Qwen-VL)
scene = get_scene_description()  # 调用阿里云API，返回场景描述

# 2. DeepSeek Agent 决策循环
result = agent.invoke({"messages": [task + scene]})
# DeepSeek 内部会：
# - 分析任务和当前场景
# - 决定调用哪个工具 (turn_right / look_around / task_complete)
# - 每次 look_around() 都会调用 Qwen-VL 拍照识别
# - 循环直到调用 task_complete() 结束

# 3. TTS 语音回复
play_tts(response)  # edge-tts 播报结果
```

### 工具列表

| 工具 | 功能 | 说明 |
|------|------|------|
| `move_forward(steps)` | 前进 | 每步约10cm |
| `move_backward(steps)` | 后退 | 每步约10cm |
| `turn_left(steps)` | 左转 | 每步约15度 |
| `turn_right(steps)` | 右转 | 每步约15度 |
| `look_around()` | 观察环境 | 调用Qwen-VL拍照识别 |
| `task_complete(msg)` | 完成任务 | 结束当前任务循环 |

## 移动参数

| 动作 | 每步时长 | 实际效果 |
|------|----------|----------|
| 前进/后退 | 2秒 | ~10cm |
| 左转/右转 | 1秒 | ~15度 |

转一圈约需24步，转90度需要6步。

## 示例任务

- "向右旋转直到找到穿白衣服的人"
- "走到前面的桌子旁边"
- "左转看看有什么"
- "前进三步"

## 配置

| 项目 | 值 |
|------|-----|
| 摄像头 | `/dev/video2` |
| 电机端口 | `/dev/ttyACM1` |
| 音频设备 | `plughw:1,0` |
| 视觉模型 | qwen-vl-plus (阿里云) |
| 推理模型 | deepseek-chat |
| ASR | FunASR SenseVoice (本地) |
| TTS | edge-tts (微软) |

## API费用

| 服务 | 费用 |
|------|------|
| Qwen-VL | ~0.008元/千tokens |
| DeepSeek | ~0.001元/千tokens |
| FunASR | 免费(本地) |
| edge-tts | 免费 |

一次完整任务（如找人）大约消耗几分钱。
