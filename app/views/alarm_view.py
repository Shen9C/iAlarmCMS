# 检查路由定义是否正确
@bp.route('/process/<alarm_number>', methods=['POST'])
def process_alarm(alarm_number):
    try:
        # 打印请求信息
        print('收到告警处理请求:', {
            'alarm_number': alarm_number,
            'method': request.method,
            'content_type': request.content_type,
            'args': dict(request.args),
            'form': dict(request.form),
            'json': request.get_json(silent=True),
            'headers': dict(request.headers)
        })
        
        data = request.get_json(silent=True)
        print('解析的JSON数据:', data)
        
        confirm_type = data.get('confirm_type') if data else request.args.get('confirm_type')
        user_token = data.get('user_token') if data else request.args.get('user_token')
        
        print('处理参数:', {
            'confirm_type': confirm_type,
            'user_token': user_token
        })
        
        if not alarm_number or not confirm_type:
            print('参数不完整:', {
                'alarm_number': alarm_number,
                'confirm_type': confirm_type
            })
            return jsonify({'error': '参数不完整'}), 400
            
        alarm = Alarm.query.filter_by(alarm_number=alarm_number).first()
        print('查询到的告警:', {
            'alarm_found': alarm is not None,
            'alarm_number': alarm_number if alarm else None
        })
        
        if not alarm:
            return jsonify({'error': '未找到告警记录'}), 404
            
        alarm.is_confirmed = True
        alarm.confirm_type = confirm_type
        alarm.confirmed_time = datetime.now()
        
        print('即将提交的更改:', {
            'alarm_id': alarm.id,
            'alarm_number': alarm.alarm_number,
            'confirm_type': alarm.confirm_type,
            'confirmed_time': alarm.confirmed_time
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '告警确认成功',
            'alarm': {
                'id': alarm.id,
                'alarm_number': alarm.alarm_number,
                'confirm_type': alarm.confirm_type
            }
        })
        
    except Exception as e:
        print('处理告警时发生错误:', {
            'error_type': type(e).__name__,
            'error_message': str(e)
        })
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/confirm_alarm', methods=['POST'])
def confirm_alarm():
    alarm_number = request.form.get('alarm_number')
    confirm_type = request.form.get('confirm_type')
    user_token = request.form.get('user_token')
    
    if not all([alarm_number, confirm_type, user_token]):
        flash('缺少必要参数', 'error')
        return redirect(url_for('alarm_view.index', user_token=user_token))
    
    try:
        alarm = Alarm.query.filter_by(alarm_number=alarm_number).first()
        if alarm:
            alarm.is_confirmed = True
            alarm.confirm_type = confirm_type
            alarm.confirmed_time = datetime.now()
            db.session.commit()
            flash('告警确认成功', 'success')
        else:
            flash('未找到对应的告警记录', 'error')
    except Exception as e:
        db.session.rollback()
        flash('告警确认失败', 'error')
        
    return redirect(url_for('alarm_view.index', user_token=user_token))
