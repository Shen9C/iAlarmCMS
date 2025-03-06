# 智能告警综合管理系统

## 项目简介
智能告警综合管理系统（Intelligent Alarm Comprehensive Management System）是一个基于 Flask 框架开发的 Web 应用，用于集中管理和处理各类告警信息。

## 主要功能
- 告警管理
  - 告警信息展示
  - 告警状态更新
  - 告警处理记录
  - 告警自动清理

- 系统设置
  - 基本设置（系统名称等）
  - 告警设置（保留天数、刷新间隔）
  - 邮件通知设置

- 用户管理
  - 用户账号管理
  - 角色权限控制
  - 密码修改

- 统计分析
  - 告警统计
  - 处理效率分析

## 技术栈
- 后端框架：Flask
- 数据库：SQLite
- 前端框架：Bootstrap 5
- 图标库：Bootstrap Icons

## 环境要求
- Python 3.8+
- Flask 2.0+
- SQLAlchemy
- Flask-Login
- Flask-Migrate

## 快速开始

1. 克隆项目
```bash
git clone https://github.com/Shen9C/iAlarmCMS.git
cd iAlarmCMS
```