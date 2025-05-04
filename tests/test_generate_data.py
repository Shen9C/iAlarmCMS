#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试数据生成脚本
为系统生成测试用的样本数据，包括用户、设备、油井、任务、告警等
"""

import os
import sys
import random
import json
import argparse
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import inspect

# 将项目根目录添加到系统路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入应用相关模块
from app import create_web_app, db  # noqa: E402
from app.models.users import User
from app.models.alarms import Alarm
from app.models.edge_devices import EdgeDevice
from app.models.tasks import Task
from app.models.oil_wells import OilWell
from app.models.settings import SystemConfig, KeyValueSetting

# 创建Flask应用上下文
app = create_web_app()

# 读取配置文件
config_path = os.path.join(project_root, 'tests', 'test_data_config.json')
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        test_config = json.load(f)
    logger.info(f"已加载测试数据配置: {config_path}")
except FileNotFoundError:
    logger.error(f"测试数据配置文件不存在: {config_path}")
    test_config = {}

# 辅助函数：生成任务编号
def generate_task_code(well_code=None, task_type=None):
    """生成任务编号，基于油井编码和任务类型"""
    if not well_code:
        return f"TASK_UNKNOWN_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 任务类型的前缀映射
    prefix_map = {
        "启停检测": "QT",
        "皮带检测": "PD", 
        "毛辫子检测": "MBZ",
        "压力表检测": "YLB",
        "井口泄漏检测": "JK",
        "烟火检测": "F"
    }
    
    # 获取任务类型前缀
    type_prefix = prefix_map.get(task_type, "TASK")
    
    # 生成唯一标识符
    unique_suffix = f"{datetime.now().strftime('%m%d')}_{random.randint(1000, 9999)}"
    
    return f"TSK_{well_code}_{type_prefix}_{unique_suffix}"

# 辅助函数：生成告警编号
def generate_alarm_code(well_code=None, alarm_type=None):
    """生成告警编号，基于油井编码和故障类型映射"""
    if not well_code:
        return f"ALM_UNKNOWN_{datetime.now().strftime('%m%d%H%M')}"
    
    # 获取油井对应的故障码映射
    well_code_upper = well_code.upper() if well_code else ""
    fault_codes = test_config.get('well_code_fault_mapping', {}).get(well_code_upper, [])
    
    # 如果没有该油井的故障码映射，使用默认格式
    if not fault_codes:
        return f"{well_code}_ALM_{datetime.now().strftime('%m%d%H%M')}"
    
    # 如果提供了告警类型，尝试选择与之匹配的故障码
    if alarm_type:
        # 根据告警类型前缀尝试匹配对应的故障码
        prefix_map = {
            "启停检测": "QT",
            "皮带检测": "PD", 
            "毛辫子检测": "MBZ",
            "压力表检测": "YLB",
            "井口泄漏检测": "JK",
            "烟火检测": "F"
        }
        
        prefix = prefix_map.get(alarm_type)
        matching_codes = [code for code in fault_codes if prefix and code.startswith(prefix)]
        
        # 如果找到匹配的故障码，随机选择一个
        if matching_codes:
            selected_code = random.choice(matching_codes)
            return f"{well_code}_{selected_code}"
    
    # 如果没有找到匹配的故障码或没有提供告警类型，随机选择一个故障码
    if fault_codes:
        selected_code = random.choice(fault_codes)
        return f"{well_code}_{selected_code}"
    else:
        return f"{well_code}_ALM_{datetime.now().strftime('%Y%m%d%H%M%S')}"

def check_database_tables():
    """检查数据库表是否存在"""
    with app.app_context():
        try:
            # 检查所有必要的表是否存在
            required_tables = [
                'users',
                'edge_devices',
                'tasks',
                'alarms',
                'oil_wells',  # 添加油井表检查
                'system_config',
                'key_value_settings'
            ]
            
            for table in required_tables:
                from sqlalchemy import text
                db.session.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                logger.info(f"表 {table} 存在")
            
            # 额外检查告警表的字段
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'alarms' in inspector.get_table_names():
                columns = [column['name'] for column in inspector.get_columns('alarms')]
                if 'alarm_code' in columns:
                    logger.info("告警表结构正确，包含alarm_code字段")
                else:
                    logger.warning("警告：告警表结构不正确，不包含alarm_code字段")
                    if 'alarm_id' in columns:
                        logger.warning("警告：告警表使用了旧的alarm_id字段，请先运行init_pg_db.py清空并重建表结构")
                        return False
            
            # 检查任务表的字段
            if 'tasks' in inspector.get_table_names():
                columns = [column['name'] for column in inspector.get_columns('tasks')]
                if 'task_type' in columns:
                    logger.info("任务表结构正确，包含task_type字段")
                else:
                    logger.warning("警告：任务表结构不正确，不包含task_type字段")
                    if 'detection_type' in columns:
                        logger.warning("警告：任务表使用了旧的detection_type字段，请先运行init_pg_db.py清空并重建表结构")
                        return False
            
            # 检查油井表的字段
            if 'oil_wells' in inspector.get_table_names():
                columns = [column['name'] for column in inspector.get_columns('oil_wells')]
                if 'well_code' in columns:
                    logger.info("油井表结构正确，包含well_code字段")
                else:
                    logger.warning("警告：油井表结构不正确，不包含well_code字段")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"数据库表检查失败: {str(e)}")
            logger.error("请先运行 init_pg_db.py 初始化数据库")
            return False

def generate_test_data():
    """生成测试数据"""
    logger.info("开始生成测试数据...")
    with app.app_context():
        try:
            # 检查数据库表
            if not check_database_tables():
                logger.error("数据库表检查失败，无法生成测试数据")
                return False
                
            # 检查数据库连接
            try:
                from sqlalchemy import text
                db.session.execute(text('SELECT 1'))
                logger.info("数据库连接成功")
            except Exception as e:
                logger.error(f"数据库连接失败: {str(e)}")
                return False
                
            # 查询现有数据
            logger.info("\n=== 现有数据查询 ===")
            existing_devices = EdgeDevice.query.limit(10).all()
            logger.info(f"设备表现有数据（前10条）:")
            for device in existing_devices:
                logger.info(f"  - {device.device_name} (ID: {device.device_id})")
            
            existing_wells = OilWell.query.limit(10).all()
            logger.info(f"\n油井表现有数据（前10条）:")
            for well in existing_wells:
                logger.info(f"  - {well.well_name} (编号: {well.well_code})")
            
            existing_tasks = Task.query.limit(10).all()
            logger.info(f"\n任务表现有数据（前10条）:")
            for task in existing_tasks:
                logger.info(f"  - {task.task_name} ({task.task_type})")
            
            existing_alarms = Alarm.query.limit(10).all()
            logger.info(f"\n告警表现有数据（前10条）:")
            for alarm in existing_alarms:
                logger.info(f"  - {alarm.alarm_code} ({alarm.alarm_type})")
            
            existing_config = SystemConfig.query.first()
            logger.info(f"\n系统配置数据:")
            if existing_config:
                logger.info(f"  - {existing_config.system_name_zh}")
            else:
                logger.info("  - 暂无配置数据")
            
            existing_settings = KeyValueSetting.query.limit(10).all()
            logger.info("\n键值设置数据（前10条）:")
            for setting in existing_settings:
                logger.info(f"  - {setting.key}: {setting.value}")
            logger.info("==================\n")
            
            # 清理已存在的数据
            logger.info("正在清理已存在的数据...")
            db.session.query(Alarm).delete()
            db.session.query(Task).delete()
            db.session.query(EdgeDevice).delete()
            db.session.query(OilWell).delete()
            db.session.query(KeyValueSetting).delete()
            db.session.query(SystemConfig).delete()
            
            # 保留管理员账户，删除其他用户
            admin_users = User.query.filter_by(role='admin').all()
            for user in User.query.filter(User.role != 'admin').all():
                db.session.delete(user)
            db.session.commit()
            logger.info("已清理现有数据，保留管理员账户")
            
            # 创建测试用户
            test_users = test_config.get('test_users', [
                {"username": "tester", "password": "test123", "role": "tester", "email": "test@example.com"},
                {"username": "viewer", "password": "view123", "role": "viewer", "email": "view@example.com"},
                {"username": "operator", "password": "oper123", "role": "operator", "email": "operator@example.com"}
            ])
            
            logger.info(f"创建测试用户: {len(test_users)}个")
            saved_users = []
            for user_data in test_users:
                # 根据User模型的__init__方法创建用户，User不接受email参数
                user = User(
                    username=user_data['username'],
                    role=user_data.get('role', 'tester'),
                    is_admin=user_data.get('role') == 'admin',
                    active=True
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                saved_users.append(user)
            db.session.commit()
            logger.info("测试用户创建完成")
            
            # 创建油井数据
            well_config = test_config.get('oil_wells', [
                {"well_code": "JK001", "well_name": "测试油井1", "location": "测试油田A区"},
                {"well_code": "JK002", "well_name": "测试油井2", "location": "测试油田B区"},
                {"well_code": "JK003", "well_name": "测试油井3", "location": "测试油田A区"}
            ])
            
            logger.info(f"创建油井数据: {len(well_config)}个")
            saved_wells = []
            for well_data in well_config:
                # OilWell不接受last_inspection参数
                well = OilWell(
                    well_code=well_data['well_code'],
                    well_name=well_data['well_name'],
                    location=well_data.get('location', '未知位置'),
                    status=well_data.get('status', '正常'),
                    description=well_data.get('description', f"描述：{well_data['well_name']}")
                )
                db.session.add(well)
                saved_wells.append(well)
            db.session.commit()
            logger.info("油井数据创建完成")
            
            # 创建边缘设备
            device_config = test_config.get('edge_devices', [
                {"device_id": "6647dd44", "device_name": "边缘设备1", "well_code": "JK001", "ip": "192.168.1.101"},
                {"device_id": "8a49ee55", "device_name": "边缘设备2", "well_code": "JK002", "ip": "192.168.1.102"},
                {"device_id": "9c5aff66", "device_name": "边缘设备3", "well_code": "JK003", "ip": "192.168.1.103"}
            ])
            
            logger.info(f"创建边缘设备: {len(device_config)}个")
            devices = []
            
            # 存储设备ID和油井代码的映射关系，用于后续创建告警时查找
            device_well_mapping = {}
            
            for device_data in device_config:
                # 为每个设备生成一个唯一的secret_key
                if 'secret_key' not in device_data:
                    device_data['secret_key'] = f"SK{uuid.uuid4().hex[:8]}"
                
                # EdgeDevice只接受特定的参数
                device = EdgeDevice(
                    device_name=device_data['device_name'],
                    ip_address=device_data.get('ip', "0.0.0.0"),
                    device_id=device_data['device_id'],
                    secret_key=device_data['secret_key'],
                    status="在线"
                )
                
                # 记录设备与油井的关系
                if 'well_code' in device_data:
                    device_well_mapping[device_data['device_id']] = device_data['well_code']
                
                # 设置最后认证时间
                device.last_auth_time = datetime.now() - timedelta(minutes=random.randint(5, 60))
                
                db.session.add(device)
                devices.append(device)
            db.session.commit()
            logger.info("边缘设备创建完成")
            
            # 创建任务
            task_types = ["启停检测", "皮带检测", "毛辫子检测", "压力表检测", "井口泄漏检测", "烟火检测"]
            task_status = ["未开始", "进行中", "已完成", "已取消"]
            
            logger.info("创建任务数据...")
            saved_tasks = []
            for well in saved_wells:
                # 为每个油井创建2-5个随机任务
                num_tasks = random.randint(2, 5)
                for i in range(num_tasks):
                    task_type = random.choice(task_types)
                    task_code = generate_task_code(well.well_code, task_type)
                    
                    # 从设备中选择一个与该油井关联的设备
                    device_id = next((d.device_id for d in devices if device_well_mapping.get(d.device_id) == well.well_code), 
                                    devices[0].device_id if devices else None)
                    
                    # 任务模型需要的字段
                    task = Task(
                        task_code=task_code,
                        task_name=f"{well.well_name} - {task_type} #{i+1}",
                        task_type=task_type,
                        well_code=well.well_code,
                        well_name=well.well_name,
                        device_id=device_id,
                        camera_ip=f"192.168.1.{random.randint(100, 200)}",
                        camera_preset=random.randint(1, 5),
                        camera_username="admin",
                        camera_password="admin123",
                        pressure_range=random.uniform(10.0, 100.0),
                        task_description=f"{well.well_name}的{task_type}任务 #{i+1}"
                    )
                    
                    # 设置创建和更新时间
                    task.created_at = datetime.now() - timedelta(days=random.randint(1, 30))
                    task.updated_at = datetime.now() - timedelta(days=random.randint(0, 20))
                    
                    db.session.add(task)
                    saved_tasks.append(task)
            db.session.commit()
            logger.info(f"已创建 {len(saved_tasks)} 个任务")
            
            # 创建告警数据
            alarm_types = task_types  # 使用与任务类型相同的类型列表
            
            logger.info("创建告警数据...")
            saved_alarms = []
            for device in devices:
                # 为每个设备创建3-8个随机告警
                num_alarms = random.randint(3, 8)
                for i in range(num_alarms):
                    alarm_type = random.choice(alarm_types)
                    
                    # 获取设备对应的油井信息
                    well = next((w for w in saved_wells if device_well_mapping.get(device.device_id) == w.well_code), None)
                    well_code = well.well_code if well else None
                    well_name = well.well_name if well else "未知油井"
                    
                    # 生成告警码
                    alarm_code = generate_alarm_code(well_code, alarm_type)
                    
                    # analysis_result 随机 0 或 1
                    analysis_result = random.choice([0, 1])
                    
                    # 根据Alarm模型字段创建告警
                    alarm = Alarm(
                        alarm_code=alarm_code,
                        alarm_type=alarm_type,
                        device_id=device.device_id,
                        device_name=device.device_name,
                        well_code=well_code,
                        well_name=well_name,
                        camera_ip=f"192.168.1.{random.randint(100, 200)}",
                        alarm_image=f"/zhyn/alarm_images/test_image_{i:03d}.jpg",
                        description=f"{alarm_type}告警: {alarm_code}",
                        alarm_time=datetime.now() - timedelta(days=random.randint(0, 30), 
                                                             hours=random.randint(0, 23), 
                                                             minutes=random.randint(0, 59)),
                        analysis_result=analysis_result
                    )
                    
                    # 设置告警状态（是否处理和确认）
                    alarm.is_processed = random.random() > 0.3
                    alarm.is_confirmed = random.random() > 0.5
                    
                    # 如果告警已处理，设置处理信息
                    if alarm.is_processed:
                        alarm.processed_time = datetime.now() - timedelta(days=random.randint(0, 5))
                        alarm.processed_by = random.choice(saved_users).username
                    
                    # 如果告警已确认，设置确认信息
                    if alarm.is_confirmed:
                        alarm.confirmed_at = datetime.now() - timedelta(days=random.randint(0, 3))
                        alarm.confirmed_by = random.choice(saved_users).username
                        alarm.confirmation_type = random.choice(["故障", "误报", "测试"])
                    
                    db.session.add(alarm)
                    saved_alarms.append(alarm)
            db.session.commit()
            logger.info(f"已创建 {len(saved_alarms)} 个告警")
            
            # 创建系统配置
            logger.info("创建系统配置...")
            system_config = SystemConfig(
                system_name_zh="油田设备监控系统",
                system_name_en="Oilfield Monitoring System",
                company_name="示例石油公司",
                logo_url="/static/img/logo.png",
                theme_color="#1976D2"
            )
            db.session.add(system_config)
            
            # 创建键值设置，包含原先存在alarm_retention_days等配置
            logger.info("创建键值设置...")
            settings = [
                KeyValueSetting(key="alarm_retention_days", value="90", description="告警保留天数"),
                KeyValueSetting(key="alarm_refresh_interval", value="30", description="告警刷新间隔（秒）"),
                KeyValueSetting(key="max_alarm_age_days", value="90", description="最大告警保留天数"),
                KeyValueSetting(key="default_page_size", value="20", description="默认分页大小"),
                KeyValueSetting(key="enable_email_notification", value="false", description="启用邮件通知"),
                KeyValueSetting(key="smtp_server", value="smtp.example.com", description="SMTP服务器"),
                KeyValueSetting(key="smtp_port", value="587", description="SMTP端口"),
                KeyValueSetting(key="smtp_username", value="noreply@example.com", description="SMTP用户名"),
                KeyValueSetting(key="smtp_password", value="password123", description="SMTP密码"),
                KeyValueSetting(key="notification_emails", value="admin@example.com,alert@example.com", description="通知邮箱"),
                KeyValueSetting(key="notification_email", value="alert@example.com", description="通知邮箱"),
                KeyValueSetting(key="api_rate_limit", value="100", description="API速率限制（次/分钟）"),
                KeyValueSetting(key="login_attempts", value="5", description="最大登录尝试次数"),
                KeyValueSetting(key="session_timeout_minutes", value="120", description="会话超时时间（分钟）"),
                KeyValueSetting(key="enable_email_alert", value="false", description="启用邮件告警")
            ]
            
            for setting in settings:
                db.session.add(setting)
            
            db.session.commit()
            
            logger.info("\n=== 测试数据生成完成 ===")
            logger.info(f"用户: {len(saved_users)}个")
            logger.info(f"设备: {len(devices)}个")
            logger.info(f"油井: {len(saved_wells)}个")
            logger.info(f"任务: {len(saved_tasks)}个")
            logger.info(f"告警: {len(saved_alarms)}个")
            logger.info(f"系统配置: 1个")
            logger.info(f"键值设置: {len(settings)}个")
            logger.info("======================\n")
            
            logger.info("测试数据已成功生成，可以通过以下账户登录系统：")
            for user_data in test_users:
                logger.info(f"用户名: {user_data['username']}, 密码: {user_data['password']}, 角色: {user_data['role']}")
            
            return True
        except Exception as e:
            import traceback
            logger.error(f"生成测试数据失败: {str(e)}")
            logger.error(traceback.format_exc())
            db.session.rollback()
            return False

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="测试数据生成工具")
    parser.add_argument("--reset", action="store_true", help="重置数据库并生成测试数据")
    parser.add_argument("--verbose", action="store_true", help="显示详细日志")
    parser.add_argument("--config", help="指定测试数据配置文件路径")
    parser.add_argument("--database", help="指定数据库连接字符串")
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 执行测试数据生成
    success = generate_test_data()
    
    if success:
        logger.info("测试数据生成完成")
        return 0
    else:
        logger.error("测试数据生成失败")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 