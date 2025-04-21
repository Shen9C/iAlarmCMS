from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.oil_wells import OilWell
from app.models.settings import SystemConfig
from app.models.tasks import Task
from app import db
from sqlalchemy import or_

bp = Blueprint('oil_wells_view', __name__, url_prefix='/oil_wells')

@bp.route('/')
@login_required
def index():
    """油井列表页面"""
    try:
        # 获取筛选参数
        well_name = request.args.get('well_name', '')
        well_code = request.args.get('well_code', '')
        status = request.args.get('status', '')
        location = request.args.get('location', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # 构建查询
        query = OilWell.query
        
        # 应用筛选条件
        if well_name:
            query = query.filter(OilWell.well_name.ilike(f'%{well_name}%'))
            
        if well_code:
            query = query.filter(OilWell.well_code.ilike(f'%{well_code}%'))
            
        if status:
            query = query.filter(OilWell.status == status)
            
        if location:
            query = query.filter(OilWell.location.ilike(f'%{location}%'))
            
        # 按油井编码升序排序
        query = query.order_by(OilWell.well_code.asc())
            
        # 获取分页数据
        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # 获取筛选选项
        statuses = OilWell.query.with_entities(OilWell.status).distinct().all()
        statuses = [s[0] for s in statuses if s[0]]
        
        locations = OilWell.query.with_entities(OilWell.location).distinct().all()
        locations = [l[0] for l in locations if l[0]]
        
        # 获取系统配置
        system_config = SystemConfig.query.first()
        
        return render_template('oil_wells/oil_wells_index.html',
                             oil_wells=pagination.items,
                             pagination=pagination,
                             statuses=statuses,
                             locations=locations,
                             current_well_name=well_name,
                             current_well_code=well_code,
                             current_status=status,
                             current_location=location,
                             system_config=system_config)
    except Exception as e:
        flash(f'获取油井列表失败: {str(e)}', 'error')
        return render_template('oil_wells/oil_wells_index.html', oil_wells=[], pagination=None)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建油井页面"""
    if request.method == 'POST':
        try:
            oil_well = OilWell(
                well_code=request.form['well_code'],
                well_name=request.form['well_name'],
                location=request.form.get('location', ''),
                status=request.form.get('status', '正常'),
                description=request.form.get('description', '')
            )
            db.session.add(oil_well)
            db.session.commit()
            flash('油井创建成功', 'success')
            return redirect(url_for('oil_wells_view.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'创建油井失败: {str(e)}', 'error')
    
    return render_template('oil_wells/oil_well_form.html', oil_well=None)

@bp.route('/edit/<int:oil_well_id>', methods=['GET', 'POST'])
@login_required
def edit(oil_well_id):
    """编辑油井页面"""
    oil_well = OilWell.query.get_or_404(oil_well_id)
    
    if request.method == 'POST':
        try:
            oil_well.well_code = request.form['well_code']
            oil_well.well_name = request.form['well_name']
            oil_well.location = request.form.get('location', '')
            oil_well.status = request.form.get('status', '正常')
            oil_well.description = request.form.get('description', '')
            
            db.session.commit()
            flash('油井更新成功', 'success')
            return redirect(url_for('oil_wells_view.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'更新油井失败: {str(e)}', 'error')
    
    return render_template('oil_wells/oil_well_form.html', oil_well=oil_well)

@bp.route('/delete/<int:oil_well_id>', methods=['POST'])
@login_required
def delete(oil_well_id):
    """删除油井"""
    try:
        oil_well = OilWell.query.get_or_404(oil_well_id)
        
        # 检查是否有关联的任务
        related_tasks = Task.query.filter_by(well_code=oil_well.well_code).count()
        if related_tasks > 0:
            flash(f'无法删除：该油井关联了 {related_tasks} 个任务', 'error')
            return redirect(url_for('oil_wells_view.index'))
            
        db.session.delete(oil_well)
        db.session.commit()
        flash('油井删除成功', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除油井失败: {str(e)}', 'error')
    
    return redirect(url_for('oil_wells_view.index'))

@bp.route('/<int:oil_well_id>')
@login_required
def detail(oil_well_id):
    """油井详情页面"""
    try:
        oil_well = OilWell.query.get_or_404(oil_well_id)
        
        # 获取关联的任务
        tasks = Task.query.filter_by(well_code=oil_well.well_code).all()
        
        return render_template('oil_wells/oil_well_detail.html', oil_well=oil_well, tasks=tasks)
    except Exception as e:
        flash(f'获取油井详情失败: {str(e)}', 'error')
        return redirect(url_for('oil_wells_view.index'))

@bp.route('/oil_wells', methods=['GET'])
@login_required
def oil_wells_index():
    """油井管理首页"""
    return render_template('oil_wells/oil_wells_index.html', title='油井管理')

@bp.route('/oil_wells/add', methods=['GET'])
@login_required
def add_oil_well_form():
    """添加油井页面"""
    return render_template('oil_wells/oil_wells_form.html', title='添加油井', oil_well=None)

@bp.route('/oil_wells/edit/<well_code>', methods=['GET'])
@login_required
def edit_oil_well_form(well_code):
    """编辑油井页面"""
    oil_well = OilWell.get_by_well_code(well_code)
    if not oil_well:
        flash('油井不存在', 'error')
        return redirect(url_for('oil_wells_view.oil_wells_index'))
    return render_template('oil_wells/oil_wells_form.html', title='编辑油井', oil_well=oil_well) 