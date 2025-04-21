from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.models.oil_wells import OilWell
from app.models.tasks import Task
from app import db
import logging

logger = logging.getLogger(__name__)
bp = Blueprint('oil_wells_api', __name__, url_prefix='/api/oil_wells')

@bp.route('', methods=['GET'])
@login_required
def get_oil_wells():
    """获取油井列表，支持分页和筛选功能"""
    try:
        # 获取查询参数
        well_name = request.args.get('well_name', '')
        well_code = request.args.get('well_code', '')
        status = request.args.get('status', '')
        location = request.args.get('location', '')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 15, type=int)
        
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
            
        # 执行分页查询
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        # 构建响应数据
        response = {
            'code': 200,
            'data': {
                'items': [oil_well.to_dict() for oil_well in pagination.items],
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': pagination.page
            }
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"获取油井列表失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取油井列表失败: {str(e)}'
        }), 500

@bp.route('/<int:oil_well_id>', methods=['GET'])
@login_required
def get_oil_well(oil_well_id):
    """获取单个油井详情"""
    try:
        oil_well = OilWell.query.get_or_404(oil_well_id)
        return jsonify({
            'code': 200,
            'data': oil_well.to_dict()
        })
    except Exception as e:
        logger.error(f"获取油井详情失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取油井详情失败: {str(e)}'
        }), 500

@bp.route('', methods=['POST'])
@login_required
def create_oil_well():
    """创建新油井"""
    try:
        data = request.get_json()
        
        # 检查油井编号是否已存在
        existing = OilWell.query.filter_by(well_code=data['well_code']).first()
        if existing:
            return jsonify({
                'code': 400,
                'message': f"油井编号 '{data['well_code']}' 已存在"
            }), 400
        
        oil_well = OilWell(
            well_code=data['well_code'],
            well_name=data['well_name'],
            location=data.get('location', ''),
            status=data.get('status', '正常'),
            description=data.get('description', '')
        )
        db.session.add(oil_well)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '油井创建成功',
            'data': oil_well.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"创建油井失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'创建油井失败: {str(e)}'
        }), 500

@bp.route('/<int:oil_well_id>', methods=['PUT'])
@login_required
def update_oil_well(oil_well_id):
    """更新油井信息"""
    try:
        oil_well = OilWell.query.get_or_404(oil_well_id)
        data = request.get_json()
        
        # 如果修改了编号，检查新编号是否已存在
        if 'well_code' in data and data['well_code'] != oil_well.well_code:
            existing = OilWell.query.filter_by(well_code=data['well_code']).first()
            if existing:
                return jsonify({
                    'code': 400,
                    'message': f"油井编号 '{data['well_code']}' 已存在"
                }), 400
            oil_well.well_code = data['well_code']
            
        if 'well_name' in data:
            oil_well.well_name = data['well_name']
        if 'location' in data:
            oil_well.location = data['location']
        if 'status' in data:
            oil_well.status = data['status']
        if 'description' in data:
            oil_well.description = data['description']
            
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '油井信息更新成功',
            'data': oil_well.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新油井信息失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'更新油井信息失败: {str(e)}'
        }), 500

@bp.route('/<int:oil_well_id>', methods=['DELETE'])
@login_required
def delete_oil_well(oil_well_id):
    """删除油井"""
    try:
        oil_well = OilWell.query.get_or_404(oil_well_id)
        
        # 检查是否有关联的任务
        related_tasks = Task.query.filter_by(well_code=oil_well.well_code).count()
        if related_tasks > 0:
            return jsonify({
                'code': 400,
                'message': f'无法删除: 该油井关联了 {related_tasks} 个任务'
            }), 400
            
        db.session.delete(oil_well)
        db.session.commit()
        
        return jsonify({
            'code': 200,
            'message': '油井删除成功'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"删除油井失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'删除油井失败: {str(e)}'
        }), 500

@bp.route('/search', methods=['GET'])
@login_required
def search_oil_wells():
    """搜索油井"""
    try:
        keyword = request.args.get('keyword', '')
        if not keyword:
            return jsonify({
                'code': 200,
                'data': []
            })
            
        oil_wells = OilWell.query.filter(
            OilWell.well_name.ilike(f'%{keyword}%') | 
            OilWell.well_code.ilike(f'%{keyword}%')
        ).limit(15).all()
        
        return jsonify({
            'code': 200,
            'data': [oil_well.to_dict() for oil_well in oil_wells]
        })
    except Exception as e:
        logger.error(f"搜索油井失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'搜索油井失败: {str(e)}'
        }), 500

@bp.route('/statuses', methods=['GET'])
@login_required
def get_oil_well_statuses():
    """获取所有油井状态"""
    try:
        statuses = OilWell.query.with_entities(OilWell.status).distinct().all()
        statuses = [s[0] for s in statuses if s[0]]
        
        return jsonify({
            'code': 200,
            'data': statuses
        })
    except Exception as e:
        logger.error(f"获取油井状态列表失败: {str(e)}")
        return jsonify({
            'code': 500,
            'message': f'获取油井状态列表失败: {str(e)}'
        }), 500 