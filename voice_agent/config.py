"""
语音控制配置
"""
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# 唤醒词配置
WAKE_WORD = "小如小如"
WAKE_WORD_VARIANTS = ["小如小如", "小茹小茹", "小儒小儒", "小入小入"]  # 可能的识别变体

# 音频配置
SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.5  # 每次录音时长(秒)
SILENCE_THRESHOLD = 500  # 静音阈值
SILENCE_DURATION = 1.5  # 静音多久认为说完(秒)
MAX_RECORD_DURATION = 10  # 最大录音时长(秒)

# 音频设备 (card 1: HK USB REF)
AUDIO_DEVICE = "plughw:1,0"

# ASR配置 (FunASR SenseVoice)
ASR_MODEL = "iic/SenseVoiceSmall"  # 小模型，速度快
# ASR_MODEL = "iic/SenseVoiceLarge"  # 大模型，效果更好

# TTS配置 (edge-tts)
TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # 女声，自然
# TTS_VOICE = "zh-CN-YunxiNeural"  # 男声

# LLM配置 (复用 llm_move_agent 的配置)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "sk-f82bf749e07a4509bb34c42bcdd04074")
