"""
音频工具：录音、播放、VAD
"""
import numpy as np
import tempfile
import subprocess
import os
import time
from scipy.io import wavfile

# 直接定义配置，避免导入冲突
SAMPLE_RATE = 16000
CHANNELS = 1
AUDIO_DEVICE = "plughw:1,0"
TTS_VOICE = "zh-CN-XiaoxiaoNeural"


def record_chunk(duration: float = 0.5) -> np.ndarray:
    """录制一小段音频"""
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    # 使用较短的录音时间
    subprocess.run([
        'arecord', '-D', AUDIO_DEVICE,
        '-d', str(max(1, int(duration))),  # arecord最小1秒
        '-f', 'S16_LE',
        '-r', str(SAMPLE_RATE),
        '-c', str(CHANNELS),
        temp_path
    ], check=True, capture_output=True)
    
    sr, audio = wavfile.read(temp_path)
    os.unlink(temp_path)
    
    return audio.flatten()


def record_until_silence(
    speech_threshold: int = 80,
    silence_threshold: int = 50,
    silence_duration: float = 1.2,
    max_duration: float = 12.0
) -> np.ndarray:
    """
    VAD录音：等待说话开始，检测静音结束
    """
    audio_chunks = []
    is_speaking = False
    silence_start = None
    total_duration = 0
    chunk_duration = 1  # arecord 最小1秒
    
    while total_duration < max_duration:
        chunk = record_chunk(chunk_duration)
        volume = np.abs(chunk).mean()
        total_duration += chunk_duration
        
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
        print("", flush=True)
    
    if not audio_chunks:
        return chunk
    
    return np.concatenate(audio_chunks)


def save_audio(audio: np.ndarray, filepath: str):
    """保存音频到文件"""
    wavfile.write(filepath, SAMPLE_RATE, audio.astype(np.int16))


def play_audio_file(filepath: str):
    """播放音频文件"""
    try:
        subprocess.run(['aplay', '-D', AUDIO_DEVICE, filepath], check=True, capture_output=True)
    except Exception as e:
        print(f"播放失败: {e}")


async def text_to_speech(text: str) -> str:
    """文字转语音，返回音频文件路径"""
    import edge_tts
    
    temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    communicate = edge_tts.Communicate(text, TTS_VOICE)
    await communicate.save(temp_path)
    
    return temp_path


def play_tts(text: str):
    """同步播放TTS"""
    import asyncio
    
    async def _play():
        mp3_path = await text_to_speech(text)
        wav_path = mp3_path.replace('.mp3', '.wav')
        subprocess.run(['ffmpeg', '-y', '-i', mp3_path, wav_path], 
                      capture_output=True, check=True)
        play_audio_file(wav_path)
        os.unlink(mp3_path)
        os.unlink(wav_path)
    
    asyncio.run(_play())
