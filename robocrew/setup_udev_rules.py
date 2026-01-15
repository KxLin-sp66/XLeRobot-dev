#!/usr/bin/env python3
"""
USB设备udev规则设置脚本
为摄像头和电机端口创建固定的符号链接

运行后会生成:
- /dev/camera_head -> 头部摄像头
- /dev/camera_left -> 左侧摄像头  
- /dev/camera_right -> 右侧摄像头
- /dev/arm_left -> 左臂电机
- /dev/arm_right -> 右臂+底盘电机

使用方法:
    sudo python xlerobot/setup_udev_rules.py
"""

import subprocess
import os
import sys
import time

RULES_FILE = "/etc/udev/rules.d/99-xlerobot.rules"

def run_cmd(cmd):
    """运行命令并返回输出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def get_usb_devices(dev_type):
    """获取当前USB设备列表"""
    if dev_type == "video":
        return [d for d in os.listdir("/dev") if d.startswith("video")]
    elif dev_type == "tty":
        return [d for d in os.listdir("/dev") if d.startswith("ttyACM")]
    return []

def get_device_info(device_path):
    """获取设备的唯一标识信息"""
    full_path = f"/dev/{device_path}"
    
    # 获取设备的idVendor, idProduct, serial
    info = {}
    
    # 使用udevadm获取设备信息
    output = run_cmd(f"udevadm info -a -n {full_path} 2>/dev/null | head -50")
    
    for line in output.split('\n'):
        line = line.strip()
        if 'ATTRS{idVendor}' in line:
            info['idVendor'] = line.split('==')[1].strip('"')
        elif 'ATTRS{idProduct}' in line:
            info['idProduct'] = line.split('==')[1].strip('"')
        elif 'ATTRS{serial}' in line:
            info['serial'] = line.split('==')[1].strip('"')
        elif 'KERNELS==' in line and 'usb' in line:
            info['kernels'] = line.split('==')[1].strip('"')
    
    return info

def wait_for_new_device(dev_type, existing_devices):
    """等待新设备插入"""
    print("等待设备插入...", end="", flush=True)
    
    for _ in range(60):  # 最多等60秒
        current = get_usb_devices(dev_type)
        new_devices = set(current) - set(existing_devices)
        
        if new_devices:
            new_dev = list(new_devices)[0]
            print(f" 检测到: /dev/{new_dev}")
            time.sleep(0.5)  # 等待设备稳定
            return new_dev
        
        print(".", end="", flush=True)
        time.sleep(1)
    
    print(" 超时!")
    return None

def generate_rule(device_info, symlink_name, subsystem):
    """生成udev规则"""
    if not device_info.get('idVendor') or not device_info.get('idProduct'):
        return None
    
    rule = f'SUBSYSTEM=="{subsystem}", '
    rule += f'ATTRS{{idVendor}}=="{device_info["idVendor"]}", '
    rule += f'ATTRS{{idProduct}}=="{device_info["idProduct"]}", '
    
    if device_info.get('serial'):
        rule += f'ATTRS{{serial}}=="{device_info["serial"]}", '
    
    rule += f'SYMLINK+="{symlink_name}", MODE="0666"'
    
    return rule

def setup_device(name, dev_type, subsystem):
    """设置单个设备"""
    print(f"\n{'='*50}")
    print(f"设置: {name}")
    print(f"{'='*50}")
    
    existing = get_usb_devices(dev_type)
    print(f"当前设备: {existing}")
    
    input(f"\n请拔掉 {name} 对应的USB线，然后按回车...")
    time.sleep(1)
    
    after_unplug = get_usb_devices(dev_type)
    print(f"拔掉后设备: {after_unplug}")
    
    input(f"\n现在请插入 {name} 对应的USB线，然后按回车...")
    
    new_device = wait_for_new_device(dev_type, after_unplug)
    
    if not new_device:
        print(f"❌ 未检测到新设备，跳过 {name}")
        return None
    
    info = get_device_info(new_device)
    print(f"设备信息: {info}")
    
    symlink = name.lower().replace(" ", "_")
    rule = generate_rule(info, symlink, subsystem)
    
    if rule:
        print(f"✅ 规则: {rule}")
        return rule
    else:
        print(f"❌ 无法生成规则")
        return None

def main():
    if os.geteuid() != 0:
        print("请使用 sudo 运行此脚本!")
        print("sudo python xlerobot/setup_udev_rules.py")
        sys.exit(1)
    
    print("="*60)
    print("XLerobot USB设备udev规则设置")
    print("="*60)
    print("\n此脚本将帮助你为USB设备创建固定的符号链接")
    print("设置完成后，设备路径将不再随插拔顺序变化\n")
    
    rules = []
    
    # 摄像头设置
    cameras = [
        ("camera_head", "头部摄像头"),
        ("camera_left", "左侧摄像头"),
        ("camera_right", "右侧摄像头"),
    ]
    
    print("\n--- 摄像头设置 ---")
    for symlink, desc in cameras:
        choice = input(f"\n是否设置 {desc} ({symlink})? [y/n]: ").strip().lower()
        if choice == 'y':
            rule = setup_device(desc, "video", "video4linux")
            if rule:
                rules.append(f"# {desc}")
                rules.append(rule)
    
    # 电机端口设置
    motors = [
        ("arm_left", "左臂电机 (ttyACM0)"),
        ("arm_right", "右臂+底盘电机 (ttyACM1)"),
    ]
    
    print("\n--- 电机端口设置 ---")
    for symlink, desc in motors:
        choice = input(f"\n是否设置 {desc} ({symlink})? [y/n]: ").strip().lower()
        if choice == 'y':
            rule = setup_device(desc, "tty", "tty")
            if rule:
                rules.append(f"# {desc}")
                rules.append(rule)
    
    # 写入规则文件
    if rules:
        print(f"\n{'='*60}")
        print("生成的规则:")
        print("="*60)
        
        content = "# XLerobot USB设备规则\n"
        content += "# 自动生成，请勿手动修改\n\n"
        content += "\n".join(rules)
        
        print(content)
        
        choice = input(f"\n是否写入到 {RULES_FILE}? [y/n]: ").strip().lower()
        if choice == 'y':
            with open(RULES_FILE, 'w') as f:
                f.write(content + "\n")
            
            # 重新加载udev规则
            run_cmd("udevadm control --reload-rules")
            run_cmd("udevadm trigger")
            
            print(f"\n✅ 规则已写入 {RULES_FILE}")
            print("✅ udev规则已重新加载")
            print("\n现在可以使用以下固定路径:")
            print("  /dev/camera_head  - 头部摄像头")
            print("  /dev/camera_left  - 左侧摄像头")
            print("  /dev/camera_right - 右侧摄像头")
            print("  /dev/arm_left     - 左臂电机")
            print("  /dev/arm_right    - 右臂+底盘电机")
        else:
            print("已取消")
    else:
        print("\n没有生成任何规则")

if __name__ == "__main__":
    main()
