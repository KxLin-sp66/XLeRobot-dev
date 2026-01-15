#!/usr/bin/env python3
"""
音频设备测试脚本
"""
import subprocess
import numpy as np
from scipy.io import wavfile

def test_devices():
    """列出音频设备"""
    print("=" * 50)
    print("音频设备列表")
    print("=" * 50)
    subprocess.run(['arecord', '-l'])
    print()
    subprocess.run(['aplay', '-l'])
    print()

def test_record():
    """测试录音"""
    print("=" * 50)
    print("录音测试 (3秒)")
    print("=" * 50)
    
    filepath = "/tmp/test_record.wav"
    
    print("🎤 开始录音...")
    subprocess.run([
        'arecord', '-D', 'plughw:1,0',
        '-d', '3',
        '-f', 'S16_LE',
        '-r', '16000',
        '-c', '1',
        filepath
    ], check=True)
    print("✅ 录音完成")
    
    # 显示音量
    sr, audio = wavfile.read(filepath)
    volume = np.abs(audio).mean()
    print(f"📊 平均音量: {volume:.0f}")
    print(f"💾 已保存到: {filepath}")
    
    return filepath

def test_play(filepath):
    """测试播放"""
    print("\n" + "=" * 50)
    print("播放测试")
    print("=" * 50)
    
    print("🔊 播放中...")
    subprocess.run(['aplay', '-D', 'plughw:1,0', filepath], check=True)
    print("✅ 播放完成")

def test_tts():
    """测试TTS"""
    print("\n" + "=" * 50)
    print("TTS测试")
    print("=" * 50)
    
    import asyncio
    import edge_tts
    
    async def _test():
        text = "你好，我是小如，很高兴认识你"
        voice = "zh-CN-XiaoxiaoNeural"
        
        print(f"📝 文本: {text}")
        print(f"🎙️ 声音: {voice}")
        
        mp3_path = "/tmp/test_tts.mp3"
        wav_path = "/tmp/test_tts.wav"
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(mp3_path)
        print(f"✅ TTS生成完成: {mp3_path}")
        
        # 转换为wav
        subprocess.run(['ffmpeg', '-y', '-i', mp3_path, wav_path], 
                      capture_output=True)
        
        # 播放
        print("🔊 播放中...")
        subprocess.run(['aplay', '-D', 'plughw:1,0', wav_path])
        print("✅ 播放完成")
    
    asyncio.run(_test())

if __name__ == "__main__":
    test_devices()
    filepath = test_record()
    test_play(filepath)
    test_tts()
    print("\n✅ 所有测试完成！")
