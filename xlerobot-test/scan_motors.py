#!/usr/bin/env python
"""
扫描飞特电机总线，检测所有连接的电机ID和型号
使用底层串口通信，绕过lerobot的电机检查
"""

import serial
import time

# 飞特协议常量
HEADER = 0xFF
READ_INST = 0x02
MODEL_ADDR = 3  # 型号地址
MODEL_LEN = 2   # 型号长度

def calculate_checksum(packet):
    """计算校验和"""
    return (~sum(packet[2:])) & 0xFF

def build_read_packet(motor_id, addr, length):
    """构建读取指令包"""
    packet = [HEADER, HEADER, motor_id, 4, READ_INST, addr, length]
    packet.append(calculate_checksum(packet))
    return bytes(packet)

def read_response(ser, timeout=0.05):
    """读取响应"""
    ser.timeout = timeout
    response = ser.read(100)
    return response

def ping_motor(ser, motor_id, retries=5):
    """Ping电机，检查是否存在，多次重试"""
    for attempt in range(retries):
        # 发送读取型号的指令
        packet = build_read_packet(motor_id, MODEL_ADDR, MODEL_LEN)
        
        ser.reset_input_buffer()
        ser.write(packet)
        time.sleep(0.02)  # 增加等待时间
        
        response = read_response(ser, timeout=0.1)
        
        if len(response) >= 8:
            # 检查响应头和ID
            if response[0] == 0xFF and response[1] == 0xFF and response[2] == motor_id:
                # 提取型号 (小端序)
                if len(response) >= 7:
                    model = response[5] | (response[6] << 8)
                    return model
        time.sleep(0.01)
    return None

def scan_port(port: str, max_id: int = 20, baudrate: int = 1000000):
    """扫描指定端口上的所有电机"""
    print(f"\n{'='*50}")
    print(f"扫描端口: {port}")
    print(f"{'='*50}")
    
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        time.sleep(0.1)
        
        found_motors = []
        print(f"\n扫描ID 1-{max_id}...")
        
        for motor_id in range(1, max_id + 1):
            model = ping_motor(ser, motor_id)
            if model is not None:
                found_motors.append((motor_id, model))
                print(f"  ✅ ID {motor_id}: 型号 {model}")
        
        ser.close()
        
        if found_motors:
            print(f"\n找到 {len(found_motors)} 个电机:")
            for mid, mmodel in found_motors:
                print(f"  - ID {mid}: 型号 {mmodel}")
        else:
            print("\n❌ 没有找到任何电机")
            
        return found_motors
        
    except Exception as e:
        print(f"❌ 无法连接到端口 {port}: {e}")
        return []

def main():
    print("飞特电机扫描工具 (底层串口版)")
    print("="*50)
    
    # 扫描两个端口
    ports = ["/dev/ttyACM0", "/dev/ttyACM1"]
    
    all_results = {}
    for port in ports:
        results = scan_port(port)
        all_results[port] = results
    
    # 总结
    print("\n" + "="*50)
    print("扫描结果总结")
    print("="*50)
    
    print("\n预期配置:")
    print("  /dev/ttyACM0 (左臂+头部): ID 1-6 (左臂), ID 7-8 (头部)")
    print("  /dev/ttyACM1 (右臂+底盘): ID 1-6 (右臂), ID 7-9 (底盘轮子)")
    
    print("\n实际检测:")
    for port, motors in all_results.items():
        ids = [m[0] for m in motors]
        print(f"  {port}: {ids if ids else '无电机'}")
    
    # 检查缺失
    expected_acm0 = set(range(1, 9))  # 1-8
    expected_acm1 = set(range(1, 10))  # 1-9
    
    found_acm0 = set(m[0] for m in all_results.get("/dev/ttyACM0", []))
    found_acm1 = set(m[0] for m in all_results.get("/dev/ttyACM1", []))
    
    missing_acm0 = expected_acm0 - found_acm0
    missing_acm1 = expected_acm1 - found_acm1
    
    if missing_acm0:
        print(f"\n⚠️  /dev/ttyACM0 缺失电机ID: {sorted(missing_acm0)}")
    if missing_acm1:
        print(f"⚠️  /dev/ttyACM1 缺失电机ID: {sorted(missing_acm1)}")
    
    if not missing_acm0 and not missing_acm1:
        print("\n✅ 所有电机都已检测到!")

if __name__ == "__main__":
    main()
