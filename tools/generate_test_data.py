from app import create_app
from app.models.alarm import Alarm
from app import db
from datetime import datetime, timedelta
import random

app = create_app()

def generate_test_data(count=30):
    """生成测试告警数据"""
    alarm_types = ['网络异常', '设备离线', '温度过高', '电压异常', '系统错误']
    
    with app.app_context():
        # 获取当前最大的告警编号
        last_alarm = Alarm.query.order_by(Alarm.alarm_number.desc()).first()
        if last_alarm:
            try:
                last_num = int(last_alarm.alarm_number[-3:])
            except ValueError:
                last_num = 0
        else:
            last_num = 0
        
        for i in range(count):
            alarm_time = datetime.now() - timedelta(
                days=random.randint(0, 30),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            # 生成递增的告警编号
            alarm_num = last_num + i + 1
            alarm_number = f'ALM{datetime.now().strftime("%Y%m%d")}{alarm_num:03d}'
            
            # 检查编号是否已存在
            while Alarm.query.filter_by(alarm_number=alarm_number).first():
                alarm_num += 1
                alarm_number = f'ALM{datetime.now().strftime("%Y%m%d")}{alarm_num:03d}'
            
            alarm = Alarm(
                alarm_number=alarm_number,
                alarm_type=random.choice(alarm_types),
                alarm_time=alarm_time,
                is_processed=random.choice([True, False])
            )
            
            db.session.add(alarm)
            
        db.session.commit()
        print(f"已成功生成 {count} 条测试数据！")

if __name__ == '__main__':
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    generate_test_data(count)