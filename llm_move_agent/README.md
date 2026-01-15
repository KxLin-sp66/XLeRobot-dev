# LLM Move Agent - XLerobot 底盘移动控制

基于 LangChain 的 LLM Agent，通过自然语言控制机器人底盘移动。

## 功能

- 前进/后退
- 左转/右转
- 左右平移
- 支持 DeepSeek / OpenAI / Gemini 等多种 LLM

## 安装依赖

```bash
conda activate xlerobot
pip install langchain langchain-core langchain-openai python-dotenv
```

## 配置

API Key 已配置在 `.env` 文件中，默认使用 DeepSeek。

如需更换模型，编辑 `.env`：
```bash
# DeepSeek (当前使用)
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-key

# 或 OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key

# 或 Gemini
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your-key
```

## 使用方法

```bash
cd ~/XLeRobot
conda activate xlerobot

# 执行单个指令
python llm_move_agent/move_agent.py --task "向前走3步然后左转"

# 交互模式
python llm_move_agent/move_agent.py

# 模拟模式（不连接机器人）
python llm_move_agent/move_agent.py --mock
```

## 示例指令

```
向前走5步
后退3步然后右转
左转两次，前进，再右转
绕一个小圈
```

## 文件说明

| 文件 | 说明 |
|-----|------|
| `move_agent.py` | 主程序 |
| `tools.py` | 底盘控制工具 |
| `config.py` | 配置管理 |
| `test_llm.py` | LLM 连接测试 |
| `.env` | API Key 配置 |

## 参数调整

如需调整移动幅度，编辑 `tools.py` 中的 `WheelController`：

```python
self.default_speed = 500      # 速度 (越大越快)
self.turn_duration = 1.0      # 转弯时长 (秒)，每步约15度
self.move_duration = 2.0      # 移动时长 (秒)，每步约10cm
```

转一圈约需24步。

## 开发过程遇到的问题

| 问题 | 原因 | 解决方案 |
|-----|------|---------|
| `AgentExecutor` 导入失败 | LangChain 新版改了 API | 改用 `langgraph.prebuilt.create_react_agent` |
| 电机配置格式错误 | `Motor` 是 dataclass 不是 tuple | 使用 `Motor(id=7, model="sts3215", norm_mode=...)` |
| `Goal_Speed` 寄存器不存在 | 飞特电机用的是 `Goal_Velocity` | 改用 `sync_write("Goal_Velocity", ...)` |
| 电机检测不稳定 | 通信偶尔失败 | 连接时加重试机制（最多3次） |
| 左转右转方向反了 | 轮子速度方向设错 | 对调 `turn_left` 和 `turn_right` 的速度值 |
| 工具返回假成功 | 执行失败但返回"成功" | 让控制函数返回 bool，工具检查后再返回结果 |
| 移动幅度太小 | 速度和时间太短 | 速度从 200 调到 300，时间适当加长 |
| 退出后轮子仍使能 | cleanup 没释放力矩 | 退出时写入 `Torque_Enable=0` |

---

*测试通过：2026-01-08*
