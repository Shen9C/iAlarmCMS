from app import create_app, db
from app.models.setting import SystemSetting

app = create_app()

with app.app_context():
    # 创建初始系统设置
    settings = [
        SystemSetting(
            key='site_title',
            value='告警管理系统',
            description='网站标题'
        ),
        SystemSetting(
            key='page_size',
            value='20',
            description='默认每页显示数量'
        ),
        SystemSetting(
            key='alarm_retention_days',
            value='30',
            description='告警数据保留天数'
        )
    ]
    
    db.session.add_all(settings)
    db.session.commit()
    
    print('系统设置初始化完成')