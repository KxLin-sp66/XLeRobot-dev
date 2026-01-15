# XLeRobot 二次开发

基于 [XLeRobot](https://github.com/Vector-Wangel/XLeRobot) 的二次开发项目。

## 项目背景

XLeRobot是一个基于LeRobot框架的双臂移动机器人项目，本项目在其基础上进行二次开发，部署在地瓜机器人RDK S100开发板上（80-128 TOPS BPU算力）。

**硬件配置：**
- 开发板：RDK S100 (6x Cortex-A78AE, 12/24GB RAM)
- 双臂：各6个舵机 + 头部2个舵机
- 底盘：三轮全向底盘 (3个舵机)
- 摄像头：头部 + 左右臂共3个USB摄像头

**相关链接：**
- XLeRobot: https://github.com/Vector-Wangel/XLeRobot
- LeRobot: https://github.com/huggingface/lerobot
- RDK S100: https://developer.d-robotics.cc/rdk_doc/rdk_s/

## 开发内容

### 1. RoboCrew 视觉语音Agent (`robocrew/`)

实现了多模态闭环控制系统：

- **视觉理解**: Qwen-VL (阿里云百炼) - 场景识别、目标定位
- **推理决策**: DeepSeek - 任务规划、动作决策
- **语音交互**: FunASR (本地ASR) + edge-tts (微软TTS)
- **移动控制**: 三轮全向底盘控制

**特色功能**:
- 图像距离参考线 (1m/2m/3m/5m标记)
- 角度标尺 (-40°~+40°)
- 目标导向视觉询问
- 语音唤醒与对话

```bash
# 语音交互
python robocrew/agent.py

# 文本交互
python robocrew/agent.py --text

# 单次任务
python robocrew/agent.py --task "走到桌子前面"
```

### 2. USB设备固定路径 (`robocrew/setup_udev_rules.py`)

解决USB设备重启后路径变化问题：

```bash
sudo python robocrew/setup_udev_rules.py
```

创建符号链接：
- `/dev/camera_head` - 头部摄像头
- `/dev/camera_left`, `/dev/camera_right` - 左右摄像头
- `/dev/arm_left`, `/dev/arm_right` - 左右臂电机

### 3. 其他Agent

- `voice_agent/` - 纯语音控制移动
- `llm_move_agent/` - 文本控制移动

## 环境配置

### 1. 基础环境

本项目基于 XLeRobot 的 xlerobot conda 环境运行：

```bash
# 如果还没有xlerobot环境，先按原项目文档安装
# 然后激活环境
conda activate xlerobot
```

### 2. 安装额外依赖

```bash
# LLM Agent框架
pip install langchain langchain-openai langgraph

# 视觉
pip install opencv-python

# 语音识别 (本地运行，首次会下载模型约500MB)
pip install funasr modelscope

# 语音合成
pip install edge-tts

# 音频处理
pip install scipy numpy
```

### 3. 系统依赖 (Ubuntu/Debian)

```bash
# 音频录制/播放
sudo apt install alsa-utils ffmpeg
```

### 4. API密钥配置

```bash
# 复制模板
cp robocrew/.env.example robocrew/.env

# 编辑填入你的密钥
nano robocrew/.env
```

需要的API：
- **Qwen-VL**: 阿里云百炼平台申请 https://bailian.console.aliyun.com/
- **DeepSeek**: DeepSeek开放平台申请 https://platform.deepseek.com/

### 5. USB设备配置 (可选)

如果USB设备路径不固定，运行udev规则配置：

```bash
sudo python robocrew/setup_udev_rules.py
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 6. 验证安装

```bash
# 模拟模式测试（不需要硬件）
python robocrew/agent.py --mock --task "前进两步"
```

## 项目结构

```
XLeRobot/
├── lerobot/                      # LeRobot 基础框架 (submodule)
│   ├── src/lerobot/
│   │   ├── robots/xlerobot/      # XLerobot 机器人配置
│   │   ├── motors/               # 电机驱动
│   │   └── model/                # SO101逆运动学
│   └── examples/                 # 控制示例脚本
│
├── robocrew/                     # 视觉语音闭环Agent
│   ├── agent.py                  # 主程序 (Qwen-VL + DeepSeek)
│   ├── setup_udev_rules.py       # udev规则设置脚本
│   ├── .env.example              # API密钥模板
│   └── README.md
│
├── llm_move_agent/               # LLM底盘移动Agent
│   ├── move_agent.py             # 主程序 (LangChain Agent)
│   ├── tools.py                  # 底盘控制工具
│   ├── config.py                 # LLM配置
│   ├── .env.example              # API密钥模板
│   └── README.md
│
├── voice_agent/                  # 语音控制Agent
│   ├── voice_agent.py            # 主程序 (语音控制移动)
│   ├── asr.py                    # FunASR语音识别
│   ├── audio_utils.py            # 音频工具 (VAD/TTS)
│   └── README.md
│
├── XLeVR/                        # VR控制模块
│   ├── vr_monitor.py             # VR数据接收
│   ├── xlevr/                    # VR核心代码
│   └── web-ui/                   # VR网页界面
│
├── web_control/                  # Web控制模块
│   ├── server/                   # FastAPI后端
│   ├── client/                   # React前端
│   └── README.md
│
├── hardware/                     # 硬件设计文件 (3D打印/STL)
├── software/                     # 软件工具与示例
├── simulation/                   # 仿真环境 (Isaac Sim/MuJoCo)
├── docs/                         # 文档
└── README.md
```

## 后续开发规划

- 优化导航 Agent 闭环控制
- 加入模仿学习算法 (ACT/Diffusion Policy)
- 端到端 π0/π0.5 算法验证
- VR 遥操作数据采集与训练
- 仿真环境 Sim-to-Real 迁移

## 致谢

- [XLeRobot](https://github.com/Vector-Wangel/XLeRobot) - 原项目作者 [Gaotian Wang](https://vector-wangel.github.io/)
- [RoboCrew](https://github.com/Grigorij-Dudnik/RoboCrew) - Embodied LLM Agent 框架，作者 Grigorij Dudnik
