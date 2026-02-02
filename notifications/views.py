from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()
users = User.objects.filter(is_active=True)

Notification.objects.bulk_create(
    [
        Notification(
            user=user,
            title="New Purchase Order Created",
            message=f"PO {po.po_number} has been created.",
            url=f"/po/{po.id}/processes/",
        )
        for user in users
    ]
)
