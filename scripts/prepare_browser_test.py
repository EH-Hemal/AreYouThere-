"""Prepare disposable accounts only in the explicitly named test database."""
import os,sys,json,secrets
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'backend'))
os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
os.environ['MYSQL_DATABASE']='test_areyouthere'
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from core.models import User
assert settings.DATABASES['default']['NAME']=='test_areyouthere'
call_command('migrate',interactive=False,verbosity=0)
run=secrets.token_hex(4);password=secrets.token_urlsafe(24)
teacher=f'qa-teacher-{run}@areyouthere.test';student=f'qa-student-{run}@areyouthere.test'
User.objects.create_user(username=teacher,email=teacher,password=password,first_name='QA Teacher',role='teacher')
admin=f'qa-admin-{run}@areyouthere.test'
User.objects.create_superuser(username=admin,email=admin,password=password,first_name='QA Admin',role='teacher')
(ROOT/'.runtime'/'browser-test.json').write_text(json.dumps({'teacher':teacher,'student':student,'admin':admin,'newTeacher':f'qa-new-teacher-{run}@areyouthere.test','password':password}),encoding='utf-8')
print('Disposable browser test account prepared in test_areyouthere.')
