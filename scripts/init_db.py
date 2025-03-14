import os
import sys

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.user import User
from app.models.alarm import Alarm
import click

app = create_app()

@click.group()
def cli():
    """数据库管理工具"""
    pass

@cli.command()
def init():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        # 检查是否存在管理员账户
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
        click.echo('数据库初始化完成')

@cli.command()
def clear_test():
    """清空测试数据（保留管理员账户）"""
    with app.app_context():
        try:
            # 清空告警数据
            Alarm.query.delete()
            # 删除除管理员外的所有用户
            User.query.filter(User.username != 'admin').delete()
            db.session.commit()
            click.echo('测试数据已清空')
        except Exception as e:
            click.echo(f'清空数据出错: {str(e)}')

@cli.command()
def clear_all():
    """清空所有数据（包括管理员账户）"""
    with app.app_context():
        try:
            # 清空所有表
            db.session.query(Alarm).delete()
            db.session.query(User).delete()
            db.session.commit()
            click.echo('所有数据已清空')
        except Exception as e:
            click.echo(f'清空数据出错: {str(e)}')

if __name__ == '__main__':
    cli()