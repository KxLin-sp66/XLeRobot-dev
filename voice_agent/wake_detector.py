"""
唤醒词检测模块
使用ASR持续监听，检测"小如小如"
"""
import numpy as np
import tempfile
import subprocess
import os
from scipy.io import wavfile

# 直接定义配置
SAMPLE_RATE = 16000
WAKE_WORD_VARIANTS = ["小如小如", "小茹小茹", "小儒小儒", "小入小入", "小如", "小茹"]
SILENCE_THRESHOLD = 100  # 降低阈值，原来500太高了
AUDIO_DEVICE = "plughw:1,0"


def contains_wake_word(text: str) -> bool:
    """检查文本是否包含唤醒词"""
    text = text.replace(" ", "").lower()
    for variant in WAKE_WORD_VARIANTS:
        if variant in text:
            return True
    return False


def record_chunk(duration: float = 3.0) -> np.ndarray:
    """录制一段音频"""
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    subprocess.run([
        'arecord', '-D', AUDIO_DEVICE,
        '-d', str(int(duration)),
        '-f', 'S16_LE',
        '-r', str(SAMPLE_RATE),
        '-c', '1',
        temp_path
    ], check=True, capture_output=True)
    
    sr, audio = wavfile.read(temp_path)
    os.unlink(temp_path)
    
    return audio.flatten()


def listen_for_wake_word(asr_func, chunk_duration: float = 3.0) -> bool:
    """
    持续监听唤醒词 - 使用VAD检测说话结束
    """
    print("等待唤醒词 '小如小如'...", flush=True)
    
    loop_count = 0
    while True:
        loop_count += 1
        
        # 使用VAD录音：检测到说话开始，等静音结束
        audio = record_with_vad()
        
        if audio is None:
            print(f"   [{loop_count}] (无有效音频)", flush=True)
            continue
        
        volume = np.abs(audio).mean()
        print(f"   [{loop_count}] 音量={volume:.0f}, 识别中...", end=" ", flush=True)
        
        text = asr_func(audio)
        if text:
            print(f"'{text}'", flush=True)
            if contains_wake_word(text):
                print("   检测到唤醒词!", flush=True)
                return True
        else:
            print("(无内容)", flush=True)


def record_with_vad(
    silence_threshold: int = 30,
    speech_threshold: int = 80,
    silence_duration: float = 1.0,
    max_duration: float = 8.0,
    chunk_size: float = 0.3
) -> np.ndarray:
    """
    VAD录音：等待说话开始，检测静音结束
    
    Args:
        silence_threshold: 静音阈值
        speech_threshold: 说话阈值（高于此值认为在说话）
        silence_duration: 静音多久后结束录音
        max_duration: 最大录音时长
        chunk_size: 每次录音块大小（秒）
    
    Returns:
        录制的音频，如果没检测到说话返回 None
    """
    import time
    
    audio_chunks = []
    is_speaking = False
    silence_start = None
    total_duration = 0
    
    print(".", end="", flush=True)  # 表示在监听
    
    while total_duration < max_duration:
        # 录制一小段
        chunk = record_chunk(chunk_size)
        volume = np.abs(chunk).mean()
        total_duration += chunk_size
        
        # 调试输出
        print(f"{int(volume)}", end=" ", flush=True)
        
        if not is_speaking:
            # 等待说话开始
            if volume > speech_threshold:
                is_speaking = True
                audio_chunks.append(chunk)
                print(f"[开始]", end=" ", flush=True)
        else:
            # 正在说话，收集音频
            audio_chunks.append(chunk)
            
            if volume < silence_threshold:
                # 可能停止说话了
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > silence_duration:
                    # 静音超过阈值，结束录音
                    print(f"[结束]", end=" ", flush=True)
                    break
            else:
                # 还在说话
                silence_start = None
    
    print("", flush=True)  # 换行
    
    if not audio_chunks:
        return None
    
    return np.concatenate(audio_chunks)
