#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
验证边缘设备API的/alarms接口的测试脚本
此脚本专门用于测试边缘设备上报告警的功能，使用Token认证方式
支持HTTP和HTTPS两种协议
"""

import requests
import json
import sys
import time
import argparse
import os
import warnings
from datetime import datetime
import pytz
from urllib.parse import urlparse

# 预置默认配置
DEFAULT_CONFIG = {
    'url': 'https://127.0.0.1:8800',  # 默认使用HTTPS
    # 'url': 'https://192.168.8.16:8800',  # 默认使用HTTPS
    # 'url': 'https://192.168.3.3:8800',  # 默认使用HTTPS
    'device_id': '9c5aff66',  # 默认测试设备ID
    'secret_key': 'SK6029e018',  # 默认测试密钥
    'alarm_type': '设备异常',  # 默认告警类型
    'alarm_code': 'well_qt001',  # 默认告警编号（将自动生成）
    'well_code': 'JK003',  # 默认油井编号
    'well_name': '测试油井3',  # 默认油井名称
    'verify_ssl': False,  # 默认不验证SSL证书（自签名证书）
    'use_https': True  # 默认使用HTTPS
}

class AlarmApiTester:
    """边缘设备告警API测试工具"""

    def __init__(self, base_url, device_id=None, secret_key=None, verify_ssl=False, use_https=True):
        """初始化测试工具

        Args:
            base_url: API基础URL，例如 http://localhost:5566 或 https://localhost:5566
            device_id: 设备ID
            secret_key: 设备密钥
            verify_ssl: 是否验证SSL证书
            use_https: 是否使用HTTPS协议
        """
        # 确保URL格式正确
        parsed_url = urlparse(base_url)
        if not parsed_url.scheme:
            base_url = f"{'https' if use_https else 'http'}://{base_url}"
        
        self.base_url = base_url.rstrip('/')
        self.device_id = device_id
        self.secret_key = secret_key
        self.token = None
        self.device_name = None
        self.verify_ssl = verify_ssl
        self.use_https = use_https
        
        # 如果不验证SSL证书，则禁用相关警告
        if not verify_ssl:
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")
            
        print(f"使用{'HTTPS' if use_https else 'HTTP'}协议进行测试")
        if use_https and not verify_ssl:
            print("警告: 使用HTTPS但不验证SSL证书")

    def get_token(self):
        """获取设备认证令牌"""
        print("\n===== 获取设备认证令牌 =====")
        url = f"{self.base_url}/api/edge_devices/auth/token"
        payload = {
            "device_id": self.device_id,
            "secret_key": self.secret_key
        }
        
        print(f"请求URL: {url}")
        print(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
        print(f"请求头: {json.dumps({'Content-Type': 'application/json'}, ensure_ascii=False)}")
        
        try:
            # 添加超时设置和调试信息
            print("\n正在发送请求...")
            response = requests.post(
                url, 
                json=payload, 
                verify=self.verify_ssl,
                timeout=10,  # 设置10秒超时
                headers={'Content-Type': 'application/json'},
                allow_redirects=True,  # 允许重定向
                proxies={'http': None, 'https': None}  # 禁用代理
            )
            
            print("\n=== 响应信息 ===")
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            print(f"原始响应内容: {response.text}")
            print(f"响应编码: {response.encoding}")
            print(f"响应URL: {response.url}")  # 显示最终请求的URL（可能被重定向）
            
            # 检查响应状态码
            if response.status_code == 502:
                print("\n=== 502错误分析 ===")
                print("服务器返回502错误，可能原因：")
                print("1. 服务器未启动或无法访问")
                print("2. 服务器地址或端口错误")
                print("3. 服务器内部错误")
                print("4. 网关或代理服务器问题")
                print("\n建议：")
                print("1. 检查服务器是否正在运行")
                print("2. 确认服务器地址和端口是否正确")
                print("3. 检查服务器日志以获取更多信息")
                print("4. 尝试使用其他工具（如curl）测试连接")
            
            try:
                result = response.json()
                print(f"\n解析后的JSON响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if response.status_code == 200 and result.get('code') == 200:
                    self.token = result.get('data', {}).get('token')
                    self.device_name = result.get('data', {}).get('device_name')
                    print(f"认证成功! 获取到Token: {self.token[:20]}...")
                    return True
                else:
                    print(f"认证失败: {result.get('message')}")
                    return False
            except ValueError as json_error:
                print(f"\n解析响应JSON失败: {response.text}")
                print(f"JSON解析错误详情: {str(json_error)}")
                print(f"响应内容长度: {len(response.text)}")
                return False
            
        except requests.exceptions.RequestException as e:
            print(f"\n请求异常: {str(e)}")
            if isinstance(e, requests.exceptions.ConnectTimeout):
                print("连接超时：服务器可能未启动或网络连接问题")
            elif isinstance(e, requests.exceptions.ConnectionError):
                print("连接错误：无法连接到服务器，请检查服务器地址和端口")
                print(f"错误详情: {str(e)}")
            elif isinstance(e, requests.exceptions.ReadTimeout):
                print("读取超时：服务器响应时间过长")
            elif isinstance(e, requests.exceptions.SSLError):
                print("SSL错误：证书验证失败")
            else:
                print(f"其他请求错误：{type(e).__name__}")
                print(f"错误详情: {str(e)}")
            return False

    def upload_alarm_with_token(self, alarm_type, alarm_code, well_code=None, well_name=None, description=None, camera_ip=None, alarm_image=None):
        """使用Token认证方式上传告警信息
        
        Args:
            alarm_type: 告警类型
            alarm_code: 告警编号
            well_code: 油井编号（可选）
            well_name: 油井名称（可选）
            description: 告警描述（可选）
            camera_ip: 摄像头IP（可选）
            alarm_image: 告警图片（可选）
        """
        print("\n===== 测试Token认证方式告警上报 =====")
        if not self.token:
            print("错误: 未获取Token，请先调用get_token()")
            return False
        
        url = f"{self.base_url}/api/edge_devices/alarms"
        
        # 构建告警数据
        payload = {
            "alarm_type": alarm_type,
            "alarm_code": alarm_code
        }
        
        # 添加可选字段
        if well_code:
            payload["well_code"] = well_code
        if well_name:
            payload["well_name"] = well_name
        if description:
            payload["description"] = description
        if camera_ip:
            payload["camera_ip"] = camera_ip
        if alarm_image:
            payload["alarm_image"] = alarm_image
            
        # 使用ISO格式的时间戳
        current_time = datetime.now()
        payload["alarm_timestamp"] = current_time.isoformat()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }
        
        print(f"请求URL: {url}")
        print(f"请求头: {json.dumps(headers, ensure_ascii=False)}")
        print(f"请求参数: {json.dumps(payload, ensure_ascii=False)}")
        print(f"告警时间(ISO格式): {current_time.isoformat()}")
        
        try:
            # 执行告警上报请求
            print("\n正在发送请求...")
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                verify=self.verify_ssl,
                timeout=10,
                proxies={'http': None, 'https': None}  # 禁用代理
            )
            
            print("\n=== 响应信息 ===")
            print(f"状态码: {response.status_code}")
            print(f"响应头: {dict(response.headers)}")
            print(f"原始响应内容: {response.text}")
            print(f"响应编码: {response.encoding}")
            print(f"响应URL: {response.url}")
            
            # 检查响应状态码
            if response.status_code == 502:
                print("\n=== 502错误分析 ===")
                print("服务器返回502错误，可能原因：")
                print("1. Token无效或已过期")
                print("2. 服务器内部错误")
                print("3. 数据库连接问题")
                print("4. 网关或代理服务器问题")
                print("\n建议：")
                print("1. 检查Token是否有效")
                print("2. 查看服务器日志")
                print("3. 检查数据库连接状态")
                print("4. 尝试重新获取Token")
                return False
            
            try:
                result = response.json()
                print(f"\n解析后的JSON响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if response.status_code == 200 and result.get('code') == 200:
                    print(f"告警上报成功! 告警ID: {result.get('data', {}).get('alarm_id')}")
                    return True
                else:
                    error_msg = result.get('message', '未知错误')
                    print(f"告警上报失败: {error_msg}")
                    if result.get('code') == 401:
                        print("提示: Token可能已过期，请尝试重新获取Token")
                    return False
            except ValueError as json_error:
                print(f"\n解析响应JSON失败:")
                print(f"错误详情: {str(json_error)}")
                print(f"原始响应内容: {response.text}")
                print(f"响应内容长度: {len(response.text)}")
                print(f"响应内容类型: {type(response.text)}")
                if not response.text:
                    print("警告: 响应内容为空")
                return False
            
        except requests.exceptions.RequestException as e:
            print(f"\n请求异常: {str(e)}")
            if isinstance(e, requests.exceptions.ConnectTimeout):
                print("连接超时：服务器可能未启动或网络连接问题")
            elif isinstance(e, requests.exceptions.ConnectionError):
                print("连接错误：无法连接到服务器，请检查服务器地址和端口")
                print(f"错误详情: {str(e)}")
            elif isinstance(e, requests.exceptions.ReadTimeout):
                print("读取超时：服务器响应时间过长")
            elif isinstance(e, requests.exceptions.SSLError):
                print("SSL错误：证书验证失败")
            else:
                print(f"其他请求错误：{type(e).__name__}")
                print(f"错误详情: {str(e)}")
            return False

    def run_alarm_test(self, alarm_type=None, alarm_code=None, well_code=None, well_name=None, description=None):
        """运行告警接口测试流程"""
        print("\n========== 开始边缘设备告警API测试 ==========")
        print(f"服务器地址: {self.base_url}")
        print(f"设备ID: {self.device_id}")
        print(f"密钥: {self.secret_key[:5]}..." if self.secret_key else "密钥: 未提供")
        print(f"使用协议: {'HTTPS' if self.use_https else 'HTTP'}")
        print(f"SSL验证: {'启用' if self.verify_ssl else '禁用'}")
        
        # 生成随机告警码（如果未提供）
        if not alarm_code:
            timestamp = int(time.time())
            alarm_code = f"{well_code or 'WELL'}_ALM{timestamp}"
        
        # 生成测试描述（如果未提供）
        if not description:
            description = f"API测试生成的告警 - {datetime.now()}"
            
        # 第1步：认证并获取Token
        if not self.get_token():
            print("\n认证失败，测试终止。")
            return False
        
        print(f"\n成功获取Token并认证设备: {self.device_name}。")
        
        # 第2步：使用Token认证方式上传告警
        if not self.upload_alarm_with_token(
            alarm_type or DEFAULT_CONFIG['alarm_type'], 
            alarm_code, 
            well_code, 
            well_name, 
            description,
            camera_ip="192.168.1.100",  # 测试摄像头IP
            alarm_image=None  # 此处可添加图片Base64编码
        ):
            print("\n告警上报失败，测试终止。")
            return False
        
        print("\n========== 告警API测试完成，API调用成功 ==========")
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
    parser = argparse.ArgumentParser(description='边缘设备告警API测试工具')
    parser.add_argument('--url', help='API服务器地址，例如 http://localhost:5566 或 https://localhost:5566')
    parser.add_argument('--device-id', help='设备ID')
    parser.add_argument('--secret-key', help='设备密钥')
    parser.add_argument('--alarm-type', help='告警类型')
    parser.add_argument('--alarm-code', help='告警编号（不提供则自动生成）')
    parser.add_argument('--well-code', help='油井编号')
    parser.add_argument('--well-name', help='油井名称')
    parser.add_argument('--description', help='告警描述')
    parser.add_argument('--config', help='配置文件路径', default='./alarm_api_config.json')
    parser.add_argument('--verify-ssl', action='store_true', help='验证SSL证书')
    parser.add_argument('--http', action='store_true', help='使用HTTP而非HTTPS')
    parser.add_argument('--https', action='store_true', help='使用HTTPS（默认）')
    
    args = parser.parse_args()
    
    # 按优先级加载配置: 命令行参数 > 配置文件 > 默认配置
    config = DEFAULT_CONFIG.copy()
    
    # 尝试从配置文件加载
    file_config = AlarmApiTester.load_config_from_file(args.config)
    if file_config:
        config.update(file_config)
    
    # 命令行参数覆盖配置文件
    for key, value in vars(args).items():
        if value is not None and key in config:
            config[key] = value
            
    # 处理协议选项
    if args.http:
        config['use_https'] = False
        if 'url' in config and config['url'].startswith('https'):
            config['url'] = config['url'].replace('https://', 'http://')
    elif args.https:
        config['use_https'] = True
        if 'url' in config and config['url'].startswith('http:'):
            config['url'] = config['url'].replace('http://', 'https://')
    
    # 使用最终配置创建测试器
    tester = AlarmApiTester(
        config['url'], 
        config['device_id'], 
        config['secret_key'],
        verify_ssl=args.verify_ssl if args.verify_ssl is not None else config.get('verify_ssl', False),
        use_https=config.get('use_https', True)
    )
    
    # 运行测试
    success = tester.run_alarm_test(
        config.get('alarm_type'),
        args.alarm_code,  # 告警编号可以为None，会在函数内自动生成
        config.get('well_code'),
        config.get('well_name'),
        args.description
    )
    
    # 退出码：0表示成功，非0表示失败
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 