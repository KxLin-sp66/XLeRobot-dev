#!/usr/bin/env python3
"""
测试语音Agent的简化版本
"""
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from asr import transcribe, get_asr_model
from audio_utils import record_audio, play_tts

# API Key
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

print("=" * 50)
print("语音Agent测试")
print("=" * 50)

# 1. 加载ASR模型
print("\n1. 加载ASR模型...")
get_asr_model()
print("   ASR模型加载完成")

# 2. TTS测试
print("\n2. TTS测试...")
play_tts("你好，我是小如")
print("   TTS测试完成")

# 3. 录音+ASR测试
print("\n3. 录音+ASR测试 (请说一句话，3秒)...")
audio = record_audio(3)
print(f"   录音完成，音量: {abs(audio).mean():.0f}")

text = transcribe(audio)
print(f"   识别结果: {text}")

# 4. LLM测试
print("\n4. LLM测试...")
sys.path.insert(0, os.path.join(SCRIPT_DIR, '..', 'llm_move_agent'))

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools import ALL_TOOLS

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1",
    temperature=0.1,
)

agent = create_react_agent(llm, ALL_TOOLS, prompt="你是小如，简短回复")
result = agent.invoke({"messages": [("human", "你好")]})
response = result["messages"][-1].content
print(f"   LLM回复: {response}")

# 5. TTS播报回复
print("\n5. TTS播报回复...")
play_tts(response)

print("\n" + "=" * 50)
print("测试完成!")
print("=" * 50)
