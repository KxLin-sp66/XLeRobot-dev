"""
ASR 语音识别模块 (FunASR)
"""
import os
import sys

# 确保导入 voice_agent 的 config
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import numpy as np
import tempfile
from scipy.io import wavfile

# 直接定义配置，避免导入冲突
SAMPLE_RATE = 16000
ASR_MODEL = "iic/SenseVoiceSmall"

# 全局模型实例
_asr_model = None


def get_asr_model():
    """获取或初始化ASR模型"""
    global _asr_model
    if _asr_model is None:
        from funasr import AutoModel
        _asr_model = AutoModel(model=ASR_MODEL, device="cpu")
    return _asr_model


def transcribe(audio: np.ndarray) -> str:
    """语音转文字"""
    model = get_asr_model()
    
    # 保存为临时文件
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
        wavfile.write(f.name, SAMPLE_RATE, audio.astype(np.int16))
        temp_path = f.name
    
    try:
        result = model.generate(input=temp_path)
        if result and len(result) > 0:
            text = result[0].get('text', '')
            # 清理 SenseVoice 的特殊标记
            import re
            text = re.sub(r'<\|[^|]+\|>', '', text)
            return text.strip()
        return ""
    except Exception as e:
        print(f"ASR错误: {e}")
        return ""
    finally:
        os.unlink(temp_path)
