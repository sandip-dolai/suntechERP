from django.apps import AppConfig


class PoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'po'
    
    def ready(self):
        import po.signals