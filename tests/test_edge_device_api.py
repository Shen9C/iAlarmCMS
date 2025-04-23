#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import json
import sys
import time
import argparse
import os
import warnings
from datetime import datetime

# 预置默认配置
DEFAULT_CONFIG = {
    'url': 'https://localhost:5566',  # 默认使用HTTPS
    'device_id': '6647dd44',  # 默认测试设备ID
    'secret_key': 'SKzyvw5xwWOrPzWn3BkFQaKg1QvijNcCMbzZh8rwtd',  # 默认测试密钥
    'alarm_type': '设备异常',  # 默认告警类型
    'well_code': 'WELL001_QT001',  # 默认油井编号
    'well_name': '测试油井',  # 默认油井名称
    'verify_ssl': False  # 默认不验证SSL证书（自签名证书）
}

class EdgeDeviceApiTester:
    """边缘设备API测试工具"""

    def __init__(self, base_url, device_id=None, secret_key=None, verify_ssl=False):
        """初始化测试工具

        Args:
            base_url: API基础URL，例如 http://localhost:5000
            device_id: 设备ID
            secret_key: 设备密钥
            verify_ssl: 是否验证SSL证书
        """
        self.base_url = base_url.rstrip('/')
        self.device_id = device_id
        self.secret_key = secret_key
        self.token = None
        self.device_name = None
        self.verify_ssl = verify_ssl
        
        # 如果不验证SSL证书，则禁用相关警告
        if not verify_ssl:
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")

    def get_token(self):
        """获取设备认证令牌"""
        print("\n===== 测试设备认证获取Token =====")
        url = f"{self.base_url}/api/devices/auth/token"
        payload = {
            "device_id": self.device_id,
            "secret_key": self.secret_key
        }
        
        print(f"请求URL: {url}")
        print(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
        
        try:
            response = requests.post(url, json=payload, verify=self.verify_ssl)
            print(f"状态码: {response.status_code}")
            
            try:
                result = response.json()
                print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if response.status_code == 200 and result.get('code') == 200:
                    self.token = result.get('data', {}).get('token')
                    self.device_name = result.get('data', {}).get('device_name')
                    print(f"认证成功! 获取到Token: {self.token[:20]}...")
                    return True
                else:
                    print(f"认证失败: {result.get('message')}")
                    return False
            except ValueError:
                print(f"解析响应JSON失败: {response.text}")
                return False
            
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {str(e)}")
            return False

    def upload_alarm(self, alarm_type, alarm_code, well_code=None, well_name=None, description=None):
        """上传告警信息
        
        Args:
            alarm_type: 告警类型
            alarm_code: 告警编号
            well_code: 油井编号（可选）
            well_name: 油井名称（可选）
            description: 告警描述（可选）
        """
        print("\n===== 测试告警上报 =====")
        if not self.token:
            print("错误: 未获取Token，请先调用get_token()")
            return False
        
        url = f"{self.base_url}/api/devices/direct_test"
        
        # 构建告警数据
        payload = {
            "alarm_type": alarm_type,
            "alarm_code": alarm_code,
            "device_id": self.device_id,
            "secret_key": self.secret_key
        }
        
        # 添加可选字段
        if well_code:
            payload["well_code"] = well_code
        if well_name:
            payload["well_name"] = well_name
        if description:
            payload["description"] = description
            
        # 添加当前时间戳作为告警时间（仅供测试用）
        payload["alarm_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"请求URL: {url}")
        print(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
        
        try:
            # 执行告警上报请求
            response = requests.post(url, json=payload, headers=headers, verify=self.verify_ssl)
            print(f"状态码: {response.status_code}")
            
            try:
                result = response.json()
                print(f"响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if response.status_code == 200 and result.get('code') == 200:
                    print(f"告警上报成功! 告警ID: {result.get('data', {}).get('alarm_id')}")
                    return True
                else:
                    print(f"告警上报失败: {result.get('message')}")
                    return False
            except ValueError:
                print(f"解析响应JSON失败: {response.text}")
                return False
            
        except requests.exceptions.RequestException as e:
            print(f"请求异常: {str(e)}")
            return False
    
    def run_full_test(self, alarm_type="设备异常", alarm_code=None, well_code=None, well_name=None):
        """运行完整测试流程"""
        print("\n========== 开始边缘设备API完整测试 ==========")
        print(f"服务器地址: {self.base_url} ({'HTTPS' if self.base_url.startswith('https') else 'HTTP'})")
        print(f"设备ID: {self.device_id}")
        print(f"密钥: {self.secret_key[:5]}..." if self.secret_key else "密钥: 未提供")
        print(f"验证SSL: {'是' if self.verify_ssl else '否'}")
        
        # 生成随机告警码（如果未提供）
        if not alarm_code:
            timestamp = int(time.time())
            alarm_code = f"{well_code or 'WELL001'}_ALM{timestamp}"
        
        # 第1步：认证并获取Token
        if not self.get_token():
            print("\n认证失败，测试终止。")
            return False
        
        print(f"\n成功获取Token并认证设备: {self.device_name}。")
        
        # 第2步：上传告警
        if not self.upload_alarm(alarm_type, alarm_code, well_code, well_name, 
                               description=f"API测试生成的告警 - {datetime.now()}"):
            print("\n告警上报失败，测试终止。")
            return False
        
        print("\n========== 测试完成，所有API调用成功 ==========")
        return True
    
    @staticmethod
    def load_config_from_file(config_path):
        """从JSON配置文件加载配置

        Args:
            config_path: 配置文件路径

        Returns:
            配置字典
        """
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                print(f"已从 {config_path} 加载配置")
                return config
            except Exception as e:
                print(f"加载配置文件失败: {str(e)}，将使用默认配置")
        return {}

def main():
    parser = argparse.ArgumentParser(description='边缘设备API测试工具')
    parser.add_argument('--url', help='API服务器地址，例如 https://localhost:5566')
    parser.add_argument('--device-id', help='设备ID')
    parser.add_argument('--secret-key', help='设备密钥')
    parser.add_argument('--alarm-type', help='告警类型')
    parser.add_argument('--alarm-code', help='告警编号（不提供则自动生成）')
    parser.add_argument('--well-code', help='油井编号')
    parser.add_argument('--well-name', help='油井名称')
    parser.add_argument('--config', help='配置文件路径', default='./edge_device_config.json')
    parser.add_argument('--verify-ssl', action='store_true', help='验证SSL证书')
    parser.add_argument('--http', action='store_true', help='使用HTTP而非HTTPS')
    
    args = parser.parse_args()
    
    # 按优先级加载配置: 命令行参数 > 配置文件 > 默认配置
    config = DEFAULT_CONFIG.copy()
    
    # 尝试从配置文件加载
    file_config = EdgeDeviceApiTester.load_config_from_file(args.config)
    if file_config:
        config.update(file_config)
    
    # 命令行参数覆盖配置文件
    for key, value in vars(args).items():
        if value is not None and key in config:
            config[key] = value
            
    # 特殊处理url和协议选项
    if args.http and 'url' in config and config['url'].startswith('https'):
        config['url'] = config['url'].replace('https://', 'http://')
    
    # 使用最终配置创建测试器
    tester = EdgeDeviceApiTester(
        config['url'], 
        config['device_id'], 
        config['secret_key'],
        verify_ssl=args.verify_ssl if args.verify_ssl is not None else config.get('verify_ssl', False)
    )
    
    # 运行测试
    success = tester.run_full_test(
        config.get('alarm_type', DEFAULT_CONFIG['alarm_type']),
        args.alarm_code,  # 告警编号可以为None，会在函数内自动生成
        config.get('well_code', DEFAULT_CONFIG['well_code']),
        config.get('well_name', DEFAULT_CONFIG['well_name'])
    )
    
    # 退出码：0表示成功，非0表示失败
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()