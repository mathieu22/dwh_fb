"""
Utilitaires communs
"""
from flask import request, current_app


def get_pagination_params():
    """
    Récupère les paramètres de pagination depuis la requête.
    Retourne (page, per_page)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config.get('DEFAULT_PAGE_SIZE', 20), type=int)
    max_per_page = current_app.config.get('MAX_PAGE_SIZE', 100)

    # Limiter per_page au maximum configuré
    per_page = min(per_page, max_per_page)

    return page, per_page


def paginate_query(query, schema):
    """
    Pagine une requête SQLAlchemy et retourne le résultat formaté.
    """
    page, per_page = get_pagination_params()
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        'items': schema.dump(pagination.items),
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }


def api_response(data=None, message=None, status_code=200, errors=None):
    """
    Formate une réponse API standardisée.
    """
    response = {
        'success': status_code < 400,
        'status_code': status_code
    }

    if message:
        response['message'] = message

    if data is not None:
        response['data'] = data

    if errors:
        response['errors'] = errors

    return response, status_code


def get_date_range_params():
    """
    Récupère les paramètres de plage de dates depuis la requête.
    Retourne (start_date, end_date)
    """
    from datetime import datetime, timedelta

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Par défaut: les 30 derniers jours
    if not end_date_str:
        end_date = datetime.utcnow()
    else:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    if not start_date_str:
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

    return start_date, end_date
