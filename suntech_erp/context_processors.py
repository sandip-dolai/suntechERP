from suntech_erp.permissions import is_admin

def is_admin_context(request):
    return {"is_admin": is_admin(request.user)}
