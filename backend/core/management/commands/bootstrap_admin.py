import secrets
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from core.models import User
class Command(BaseCommand):
    help='Create a first local administrator only if no staff account exists.'
    def handle(self,*args,**kwargs):
        if User.objects.filter(is_staff=True).exists():self.stdout.write('Administrator already configured.');return
        password=secrets.token_urlsafe(20)
        User.objects.create_superuser(username='admin@areyouthere.local',email='admin@areyouthere.local',password=password,first_name='Administrator',role='teacher')
        state=settings.BASE_DIR.parent/'.runtime';state.mkdir(exist_ok=True)
        (state/'admin-login.txt').write_text(f'Local administrator\nEmail: admin@areyouthere.local\nPassword: {password}\n\nDashboard: http://127.0.0.1:5173\nDjango admin: http://127.0.0.1:8000/admin/\nKeep this file private. It is excluded from Git.\n',encoding='utf-8')
        self.stdout.write('Administrator created. Credentials saved privately in .runtime/admin-login.txt.')
