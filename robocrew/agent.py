#!/usr/bin/env python3
"""
RoboCrew Agent - 视觉+语音+移动 闭环控制
- 视觉: Qwen-VL (阿里云)
- 推理: DeepSeek
- 语音: FunASR + edge-tts
- 移动: 直接用lerobot的FeetechMotorsBus

运行环境: xlerobot (不是robocrew环境)
"""
import sys
import os
import argparse
import time

# 加载.env文件
from pathlib import Path
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())

# 配置 - 使用udev符号链接（固定路径）
MOTOR_PORT = "/dev/arm_right"  # 右臂+底盘电机
CAMERA_DEVICE = "/dev/camera_head"  # 头部摄像头
AUDIO_DEVICE = "plughw:1,0"
TTS_VOICE = "zh-CN-XiaoxiaoNeural"

# API密钥 - 从环境变量读取，或使用默认值（开发用）
QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# 全局
_wheel_controller = None
_camera = None
_qwen_client = None


# ========== 轮子控制器 (从llm_move_agent复制) ==========
class WheelController:
    """三轮全向底盘控制器"""
    
    def __init__(self, motors_bus, right_id=7, front_id=8, left_id=9):
        self.bus = motors_bus
        self.default_speed = 500      # 速度
        self.turn_duration = 1.0      # 转弯每步1秒
        self.move_duration = 2.0      # 前进每步2秒
        self.motor_id7 = "wheel_left"
        self.motor_id8 = "wheel_back"
        self.motor_id9 = "wheel_right"
        self.last_error = None
    
    def set_wheel_speeds(self, id7_speed, id8_speed, id9_speed):
        try:
            values = {
                self.motor_id7: id7_speed,
                self.motor_id8: id8_speed,
                self.motor_id9: id9_speed,
            }
            self.bus.sync_write("Goal_Velocity", values, normalize=False)
            return True
        except Exception as e:
            self.last_error = str(e)
            return False
    
    def stop(self):
        return self.set_wheel_speeds(0, 0, 0)
    
    def move_forward(self, duration=None):
        duration = duration or self.move_duration
        self.set_wheel_speeds(self.default_speed, 0, -self.default_speed)
        time.sleep(duration)
        self.stop()
        return True
    
    def move_backward(self, duration=None):
        duration = duration or self.move_duration
        self.set_wheel_speeds(-self.default_speed, 0, self.default_speed)
        time.sleep(duration)
        self.stop()
        return True
    
    def turn_left(self, duration=None):
        duration = duration or self.turn_duration
        self.set_wheel_speeds(self.default_speed, self.default_speed, self.default_speed)
        time.sleep(duration)
        self.stop()
        return True
    
    def turn_right(self, duration=None):
        duration = duration or self.turn_duration
        self.set_wheel_speeds(-self.default_speed, -self.default_speed, -self.default_speed)
        time.sleep(duration)
        self.stop()
        return True


# ========== 语音模块 ==========
def init_asr():
    from funasr import AutoModel
    return AutoModel(model="iic/SenseVoiceSmall", device="cpu")


def transcribe(model, audio_path):
    import re
    result = model.generate(input=audio_path)
    if result and len(result) > 0:
        text = result[0].get('text', '')
        text = re.sub(r'<\|[^|]+\|>', '', text)
        return text.strip()
    return ""


def record_until_silence(speech_threshold=80, silence_threshold=50, silence_duration=1.2, max_duration=12.0):
    import numpy as np
    import tempfile
    import subprocess
    from scipy.io import wavfile
    
    audio_chunks = []
    is_speaking = False
    silence_start = None
    total_duration = 0
    
    while total_duration < max_duration:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        subprocess.run([
            'arecord', '-D', AUDIO_DEVICE, '-d', '1',
            '-f', 'S16_LE', '-r', '16000', '-c', '1', temp_path
        ], check=True, capture_output=True)
        
        sr, chunk = wavfile.read(temp_path)
        os.unlink(temp_path)
        chunk = chunk.flatten()
        volume = np.abs(chunk).mean()
        total_duration += 1
        
        if not is_speaking:
            if volume > speech_threshold:
                is_speaking = True
                audio_chunks.append(chunk)
                print("[录音中]", end="", flush=True)
        else:
            audio_chunks.append(chunk)
            print(".", end="", flush=True)
            
            if volume < silence_threshold:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > silence_duration:
                    print(" [完成]", flush=True)
                    break
            else:
                silence_start = None
    
    if not is_speaking:
        return None
    return np.concatenate(audio_chunks)


def play_tts(text):
    import asyncio
    import tempfile
    import subprocess
    import edge_tts
    
    async def _play():
        temp_mp3 = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
        temp_mp3_path = temp_mp3.name
        temp_mp3.close()
        temp_wav_path = temp_mp3_path.replace('.mp3', '.wav')
        
        communicate = edge_tts.Communicate(text, TTS_VOICE)
        await communicate.save(temp_mp3_path)
        
        subprocess.run(['ffmpeg', '-y', '-i', temp_mp3_path, temp_wav_path], capture_output=True)
        subprocess.run(['aplay', '-D', AUDIO_DEVICE, temp_wav_path], capture_output=True)
        
        os.unlink(temp_mp3_path)
        os.unlink(temp_wav_path)
    
    asyncio.run(_play())


# ========== 视觉模块 ==========
# 全局变量存储当前任务目标
_current_target = None

def draw_reference_overlay(frame):
    """在图片上绘制距离和方向参考线"""
    import cv2
    h, w = frame.shape[:2]
    
    # 复制一份避免修改原图
    overlay = frame.copy()
    
    # 颜色定义 (BGR)
    yellow = (0, 255, 255)
    orange = (0, 165, 255)
    
    # 1. 顶部角度标尺
    cv2.line(overlay, (0, 30), (w, 30), yellow, 2)
    # 标记角度刻度
    for angle in range(-40, 50, 10):
        x = int(w/2 + (angle / 40) * (w/2 - 20))
        cv2.line(overlay, (x, 20), (x, 40), yellow, 2)
        cv2.putText(overlay, str(angle), (x-15, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.4, yellow, 1)
    
    # 2. 底部左右方向标记
    cv2.putText(overlay, "<=LEFT", (10, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, orange, 2)
    cv2.putText(overlay, "RIGHT=>", (w-120, h-20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, orange, 2)
    
    # 3. 中间距离参考线 (调整位置，更符合实际透视)
    center_x = w // 2
    bottom_y = h - 30
    
    # 1米线 - 画面下方 (更靠下)
    y_1m = int(h * 0.85)
    cv2.line(overlay, (center_x - 60, y_1m), (center_x + 60, y_1m), orange, 2)
    cv2.putText(overlay, "1m", (center_x + 65, y_1m + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, orange, 2)
    
    # 2米线 - 画面中下
    y_2m = int(h * 0.70)
    cv2.line(overlay, (center_x - 50, y_2m), (center_x + 50, y_2m), orange, 2)
    cv2.putText(overlay, "2m", (center_x + 55, y_2m + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, orange, 2)
    
    # 3米线 - 画面中间
    y_3m = int(h * 0.55)
    cv2.line(overlay, (center_x - 40, y_3m), (center_x + 40, y_3m), orange, 2)
    cv2.putText(overlay, "3m", (center_x + 45, y_3m + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, orange, 2)
    
    # 5米线 - 画面中上
    y_5m = int(h * 0.45)
    cv2.line(overlay, (center_x - 30, y_5m), (center_x + 30, y_5m), orange, 2)
    cv2.putText(overlay, "5m", (center_x + 35, y_5m + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, orange, 2)
    
    # 4. 画透视参考线（从底部中心向上发散）
    cv2.line(overlay, (center_x, bottom_y), (center_x - 80, y_5m), orange, 1)
    cv2.line(overlay, (center_x, bottom_y), (center_x + 80, y_5m), orange, 1)
    
    return overlay

def get_scene_description(target=None):
    import base64
    import cv2
    
    _camera.grab()
    ret, frame = _camera.read()
    if not ret:
        return "无法获取图像"
    
    # 在图片上绘制参考线
    frame_with_overlay = draw_reference_overlay(frame)
    
    _, buffer = cv2.imencode('.jpg', frame_with_overlay)
    image_base64 = base64.b64encode(buffer).decode('utf-8')
    
    if target:
        # 针对性询问：是否看到目标
        prompt = f"""图片上有距离参考线(1m/2m/3m)和方向标记(LEFT/RIGHT)。

请回答：
1. 画面中是否有"{target}"？
2. 如果有，它在什么位置（参考顶部角度：负数=左边，正数=右边，0=正前方）
3. 它大概在哪条距离线附近（1m/2m/3m或更远）
4. 简述其他物体

格式：[目标] 在 [角度]度方向，距离约[X]米。其他：...
40字以内"""
    else:
        prompt = """图片上有距离参考线(1m/2m/3m)和方向标记。
描述主要物体的位置和距离，参考图中标记。
40字以内"""
    
    response = _qwen_client.chat.completions.create(
        model="qwen-vl-plus",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                {"type": "text", "text": prompt}
            ]
        }],
        max_tokens=150,
    )
    return response.choices[0].message.content


# ========== 工具定义 ==========
from langchain_core.tools import tool

@tool
def move_forward(steps: int = 1) -> str:
    """前进指定步数"""
    print(f"  [动作] 前进{steps}步", flush=True)
    if _wheel_controller:
        for _ in range(steps):
            _wheel_controller.move_forward()
    return f"已前进{steps}步"

@tool
def move_backward(steps: int = 1) -> str:
    """后退指定步数"""
    print(f"  [动作] 后退{steps}步", flush=True)
    if _wheel_controller:
        for _ in range(steps):
            _wheel_controller.move_backward()
    return f"已后退{steps}步"

@tool
def turn_left(steps: int = 1) -> str:
    """左转"""
    print(f"  [动作] 左转{steps}步", flush=True)
    if _wheel_controller:
        for _ in range(steps):
            _wheel_controller.turn_left()
    return f"已左转{steps}步"

@tool
def turn_right(steps: int = 1) -> str:
    """右转"""
    print(f"  [动作] 右转{steps}步", flush=True)
    if _wheel_controller:
        for _ in range(steps):
            _wheel_controller.turn_right()
    return f"已右转{steps}步"

@tool
def look_around(target: str = "") -> str:
    """观察周围环境，可指定要寻找的目标（如"棕色的墙"、"蓝色桌子"）"""
    global _current_target
    if target:
        _current_target = target
    result = get_scene_description(target=_current_target)
    print(f"  [动作] 观察环境 -> {result}", flush=True)
    return result

@tool
def task_complete(message: str) -> str:
    """任务完成"""
    print(f"  [完成] {message}", flush=True)
    return f"任务完成: {message}"

TOOLS = [move_forward, move_backward, turn_left, turn_right, look_around, task_complete]


def create_agent():
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent
    
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
        temperature=0.1,
    )
    
    system_prompt = """你是小如，一个智能移动机器人。

工具：
- move_forward(steps): 前进，每步约10cm
- move_backward(steps): 后退，每步约10cm
- turn_left(steps): 左转，每步约13度
- turn_right(steps): 右转，每步约13度
- look_around(target): 观察环境，target是要找的目标
- task_complete(message): 任务完成时必须调用

转向参考：
- 转45度 = 4步
- 转90度 = 7步
- 转180度 = 14步

距离与步数对照：
- 1米 = 10步
- 2米 = 20步
- 3米 = 30步

决策流程：
1. 阅读场景描述中的距离信息
2. 如果距离≤1米或描述说"近"：立即调用task_complete，任务完成！
3. 如果距离>1米：根据距离前进相应步数
4. 如果目标在左/右侧：先转向再前进

关键规则：
- 距离≤1米就停止，调用task_complete！
- 不要在已经很近时继续前进
- 最多执行6次动作
- 回复简短
"""
    
    return create_react_agent(llm, TOOLS, prompt=system_prompt)


def run_task(agent, task):
    from langchain_core.messages import HumanMessage
    global _current_target
    
    # 从任务中提取目标关键词
    _current_target = task  # 把整个任务作为目标上下文
    
    # 第一次观察时带上任务目标
    scene = get_scene_description(target=task)
    print(f"  [视觉] {scene}", flush=True)
    
    full_task = f"当前场景: {scene}\n\n任务: {task}"
    
    # 增加递归限制
    result = agent.invoke(
        {"messages": [HumanMessage(content=full_task)]},
        config={"recursion_limit": 50}
    )
    
    if result.get("messages"):
        last_msg = result["messages"][-1]
        return last_msg.content if hasattr(last_msg, 'content') else str(last_msg)
    return "完成"


def main():
    global _wheel_controller, _camera, _qwen_client
    
    parser = argparse.ArgumentParser(description="RoboCrew Agent")
    parser.add_argument("--mock", action="store_true", help="模拟模式")
    parser.add_argument("--text", action="store_true", help="文本交互")
    parser.add_argument("--task", type=str, help="单次任务")
    args = parser.parse_args()
    
    print("=" * 50, flush=True)
    print("RoboCrew 视觉语音Agent", flush=True)
    print("=" * 50, flush=True)
    
    # 1. 摄像头 (直接用opencv)
    print("\n[1/5] 初始化摄像头...", flush=True)
    import cv2
    # 支持符号链接路径或数字索引
    if isinstance(CAMERA_DEVICE, str) and CAMERA_DEVICE.startswith("/dev/"):
        _camera = cv2.VideoCapture(CAMERA_DEVICE)
        cam_name = CAMERA_DEVICE
    else:
        _camera = cv2.VideoCapture(int(CAMERA_DEVICE) if isinstance(CAMERA_DEVICE, str) else CAMERA_DEVICE)
        cam_name = f"/dev/video{CAMERA_DEVICE}"
    
    if _camera.isOpened():
        print(f"      {cam_name} OK", flush=True)
    else:
        print(f"      {cam_name} 打开失败!", flush=True)
    
    # 2. Qwen-VL
    print("\n[2/5] 初始化Qwen-VL...", flush=True)
    from openai import OpenAI
    _qwen_client = OpenAI(
        api_key=QWEN_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    print("      OK", flush=True)
    
    # 3. 机器人
    print("\n[3/5] 连接机器人...", flush=True)
    if not args.mock:
        try:
            from lerobot.motors.feetech import FeetechMotorsBus
            from lerobot.motors.motors_bus import Motor, MotorNormMode
            
            motors = {
                "wheel_left": Motor(id=7, model="sts3215", norm_mode=MotorNormMode.RANGE_M100_100),
                "wheel_back": Motor(id=8, model="sts3215", norm_mode=MotorNormMode.RANGE_M100_100),
                "wheel_right": Motor(id=9, model="sts3215", norm_mode=MotorNormMode.RANGE_M100_100),
            }
            
            # 重试连接
            bus = None
            for attempt in range(3):
                try:
                    bus = FeetechMotorsBus(port=MOTOR_PORT, motors=motors)
                    bus.connect()
                    break
                except Exception as e:
                    if attempt < 2:
                        time.sleep(1)
                    else:
                        raise e
            
            _wheel_controller = WheelController(bus)
            print("      连接成功", flush=True)
        except Exception as e:
            print(f"      连接失败: {e}", flush=True)
    else:
        print("      模拟模式", flush=True)
    
    # 4. Agent
    print("\n[4/5] 创建Agent...", flush=True)
    agent = create_agent()
    print("      OK", flush=True)
    
    # 5. ASR
    asr_model = None
    if not args.task and not args.text:
        print("\n[5/5] 加载ASR...", flush=True)
        asr_model = init_asr()
        print("      OK", flush=True)
    else:
        print("\n[5/5] 跳过ASR", flush=True)
    
    print("\n" + "=" * 50, flush=True)
    print("就绪!", flush=True)
    print("=" * 50, flush=True)
    
    # 执行
    if args.task:
        response = run_task(agent, args.task)
        print(f"\n结果: {response}")
        
    elif args.text:
        print("\n输入任务，'quit'退出\n", flush=True)
        while True:
            try:
                user_input = input("你: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ['quit', 'q']:
                    break
                response = run_task(agent, user_input)
                print(f"小如: {response}\n")
            except KeyboardInterrupt:
                break
        print("再见!")
        
    else:
        import tempfile
        from scipy.io import wavfile
        import numpy as np
        
        play_tts("小如已就绪")
        print("\n语音交互模式\n", flush=True)
        
        while True:
            try:
                print("> ", end="", flush=True)
                audio = record_until_silence()
                
                if audio is None:
                    continue
                
                temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                wavfile.write(temp_file.name, 16000, audio.astype(np.int16))
                temp_path = temp_file.name
                temp_file.close()
                
                text = transcribe(asr_model, temp_path)
                os.unlink(temp_path)
                
                if not text:
                    play_tts("没听清")
                    continue
                
                print(f"你: {text}", flush=True)
                response = run_task(agent, text)
                print(f"小如: {response}", flush=True)
                play_tts(response)
                
            except KeyboardInterrupt:
                print("\n再见!", flush=True)
                break
    
    # 清理
    if _camera:
        _camera.release()
    if _wheel_controller:
        _wheel_controller.stop()


if __name__ == "__main__":
    main()
