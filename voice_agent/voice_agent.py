#!/usr/bin/env python3
"""
语音控制Agent主程序
流程: 唤醒词检测 -> 录音 -> ASR -> LLM -> TTS -> 执行
"""
import sys
import os

# 添加路径 - voice_agent 优先
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from asr import transcribe, get_asr_model
from wake_detector import listen_for_wake_word
from audio_utils import record_until_silence, play_tts

# 添加 llm_move_agent 路径
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'llm_move_agent'))

# 导入 llm_move_agent 的工具
from tools import (
    ALL_TOOLS, WheelController, set_wheel_controller,
    move_forward, move_backward, turn_left, turn_right,
    strafe_left, strafe_right, stop_robot, finish_task
)

# API Key - 请设置环境变量 DEEPSEEK_API_KEY
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")


def create_agent():
    """创建LLM Agent"""
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent
    
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
        temperature=0.1,
    )
    
    system_prompt = """你是小如，一个智能移动机器人助手。
用户会通过语音和你交流，你需要：
1. 理解用户的移动指令（前进、后退、左转、右转等）
2. 调用相应的工具执行动作
3. 用简短友好的语言回复

回复要求：
- 简短，不超过20个字
- 友好自然
- 执行完动作后确认"""

    agent = create_react_agent(llm, ALL_TOOLS, prompt=system_prompt)
    return agent


def init_robot():
    """初始化机器人连接"""
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
                bus = FeetechMotorsBus(port="/dev/arm_right", motors=motors)
                bus.connect()
                break
            except Exception as e:
                if attempt < 2:
                    import time
                    time.sleep(1)
        
        if bus is None:
            raise Exception("无法连接电机")
        
        # ID7=右轮, ID8=前轮, ID9=左轮
        controller = WheelController(bus, right_id=7, front_id=8, left_id=9)
        set_wheel_controller(controller)
        
        print("   机器人连接成功", flush=True)
        return bus
    except Exception as e:
        print(f"   机器人连接失败: {e}", flush=True)
        return None


def cleanup(bus):
    """清理资源"""
    if bus:
        try:
            # 释放力矩
            bus.sync_write("Torque_Enable", 
                          {"wheel_left": 0, "wheel_back": 0, "wheel_right": 0},
                          normalize=False)
            bus.disconnect()
        except:
            pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description="语音控制Agent")
    parser.add_argument("--no-wake", action="store_true", help="跳过唤醒词，直接监听")
    parser.add_argument("--mock", action="store_true", help="模拟模式，不连接机器人")
    args = parser.parse_args()
    
    print("=" * 50, flush=True)
    print("小如语音助手启动", flush=True)
    print("=" * 50, flush=True)
    
    # 预加载ASR模型
    print("\n[1/3] 加载ASR语音识别模型...", flush=True)
    get_asr_model()
    print("      ASR模型加载完成", flush=True)
    
    # 初始化机器人
    print("\n[2/3] 连接机器人电机...", flush=True)
    bus = None if args.mock else init_robot()
    if args.mock:
        print("      模拟模式，跳过电机连接", flush=True)
    
    # 创建Agent
    print("\n[3/3] 初始化LLM Agent...", flush=True)
    agent = create_agent()
    print("      Agent创建完成", flush=True)
    
    print("\n" + "=" * 50, flush=True)
    print("初始化完成!", flush=True)
    print("=" * 50, flush=True)
    
    play_tts("小如已就绪")
    
    try:
        while True:
            # 等待说话，VAD自动检测
            print("\n> ", end="", flush=True)
            audio = record_until_silence()
            
            # ASR识别
            text = transcribe(audio)
            if not text:
                play_tts("没听清")
                continue
            
            print(f"你: {text}", flush=True)
            
            # LLM处理
            result = agent.invoke({"messages": [("human", text)]})
            response = result["messages"][-1].content
            print(f"小如: {response}", flush=True)
            
            # TTS播报
            play_tts(response)
            
    except KeyboardInterrupt:
        print("\n\n再见!", flush=True)
    finally:
        cleanup(bus)


if __name__ == "__main__":
    main()
