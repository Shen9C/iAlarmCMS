import os
import sys

# 添加项目根目录到 Python 路径
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

import requests
import time
import hmac
import hashlib
import random
from datetime import datetime, timedelta
import json
from pathlib import Path
from app import create_app, db
from app.models.alarms import Alarm
from app.config import load_machine_config

def load_config():
    config = load_machine_config()
    config.setdefault('api_url', 'http://localhost:5000/api/v1/machine/alarms/batch')
    return config

def generate_device_name(config):
    return random.choice(config['device_names'])

def generate_ip():
    return f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"

def get_auth_headers(config):
    """生成认证头信息"""
    timestamp = str(int(time.time()))
    
    message = f"{config['access_key']}{timestamp}"
    signature = hmac.new(
        config['secret_key'].encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return {
        'X-Access-Key': config['access_key'],
        'X-Timestamp': timestamp,
        'X-Signature': signature,
        'Content-Type': 'application/json'
    }

def create_test_alarms(num_records=50, batch_size=10):
    """通过 API 批量创建测试告警数据"""
    config = load_config()
    success_count = 0
    error_count = 0
    total_batches = (num_records + batch_size - 1) // batch_size
    
    print(f"\n开始生成测试数据，共 {num_records} 条记录，分 {total_batches} 批处理")
    
    for batch_num in range(total_batches):
        batch_data = []
        current_batch_size = min(batch_size, num_records - batch_num * batch_size)
        
        # 生成一批数据
        for _ in range(current_batch_size):
            # 修改：添加所有必要字段
            base_time = datetime.now() - timedelta(days=random.randint(0, 30))
            alarm_data = {
                'alarm_type': random.choice(config['alarm_types']),
                'device_name': generate_device_name(config),
                'device_ip': generate_ip(),
                'alarm_time': base_time.strftime('%Y-%m-%d %H:%M:%S'),
                'alarm_number': f'AL{datetime.now().strftime("%Y%m%d")}{_+1:03d}',
                'alarm_image': f'alarms/test_image_{_+1}.jpg',
                'is_processed': random.choice([True, False]),
                'camera_ip': f'192.168.1.{random.randint(100, 200)}'
            }
            batch_data.append(alarm_data)
            
        try:
            headers = get_auth_headers(config)
            response = requests.post(config['api_url'], json=batch_data, headers=headers)
            
            print(f"\n批次 {batch_num + 1}/{total_batches}:")
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    batch_success = 0
                    for item in result.get('results', []):
                        if item.get('success'):
                            batch_success += 1
                            print(f"✓ 成功添加告警: {item.get('alarm_number')}")
                        else:
                            error_count += 1
                            print(f"✗ 添加告警失败: {item.get('error')}")
                    success_count += batch_success
                    print(f"本批次成功: {batch_success}/{current_batch_size}")
            else:
                error_count += current_batch_size
                print(f"✗ 批量添加告警失败: {response.text}")
                
            # 批次间添加随机延时
            if batch_num < total_batches - 1:
                delay = random.uniform(0.5, 1.0)
                print(f"等待 {delay:.1f} 秒后继续...")
                time.sleep(delay)
            
        except Exception as e:
            error_count += current_batch_size
            print(f"✗ 发生错误: {str(e)}")
    
    print(f"\n测试数据生成完成！")
    print(f"总记录数: {num_records}")
    print(f"成功: {success_count}")
    print(f"失败: {error_count}")
    print(f"成功率: {(success_count/num_records*100):.1f}%")

def generate_test_data():
    app = create_app()
    
    with app.app_context():
        # 清空现有数据
        db.session.query(Alarm).delete()
        db.session.commit()
        
        # 测试数据配置
        device_names = ['油井A', '油井B', '油井C', '油井D', '油井E']
        alarm_types = ['异常停机', '毛辫子断', '皮带断', '火灾烟雾', '原油泄露', '压力表异常']
        camera_ips = [
            '192.168.1.101', '192.168.1.102', '192.168.1.103',
            '192.168.1.104', '192.168.1.105'
        ]
        
        # 生成100条测试数据
        alarms = []
        for i in range(100):
            # 生成随机时间（最近30天内）
            base_time = datetime.now() - timedelta(days=random.randint(0, 30))
            
            # 随机决定是否已处理和确认
            is_processed = random.choice([True, False])
            is_confirmed = random.choice([True, False]) if is_processed else False
            
            # 创建告警记录
            alarm = Alarm(
                alarm_number=f'AL{datetime.now().strftime("%Y%m%d")}{i+1:03d}',
                alarm_type=random.choice(alarm_types),
                device_name=random.choice(device_names),
                camera_ip=random.choice(camera_ips),
                alarm_time=base_time,
                alarm_image=f'alarms/test_image_{i+1}.jpg',
                is_processed=is_processed,
                processed_time=base_time + timedelta(minutes=random.randint(5, 60)) if is_processed else None,
                is_confirmed=is_confirmed,
                confirmed_time=base_time + timedelta(minutes=random.randint(10, 120)) if is_confirmed else None
            )
            alarms.append(alarm)
        
        # 批量插入数据
        try:
            db.session.bulk_save_objects(alarms)
            db.session.commit()
            print(f"成功生成 {len(alarms)} 条测试数据")
        except Exception as e:
            db.session.rollback()
            print(f"生成测试数据失败: {str(e)}")

if __name__ == '__main__':
    create_test_alarms(50, batch_size=10)
    generate_test_data()