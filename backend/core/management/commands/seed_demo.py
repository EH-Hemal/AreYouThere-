"""Explicit sample data, never used by normal setup."""
import secrets
from django.core.management.base import BaseCommand, CommandError
from core.models import User,Session
class Command(BaseCommand):
    help='Create separate, clearly labeled demo accounts and an empty demo session.'
    def handle(self,*args,**options):
        if User.objects.filter(email__in=['teacher@demo.areyouthere.test','student@demo.areyouthere.test']).exists(): raise CommandError('Demo accounts already exist; no records changed.')
        password=secrets.token_urlsafe(16)
        for role,name in [('teacher','Demo Teacher'),('student','Demo Student')]:
            u=User.objects.create_user(username=f'{role}@demo.areyouthere.test',email=f'{role}@demo.areyouthere.test',password=password,first_name=name,role=role)
            if role=='teacher': Session.objects.create(owner=u,title='DEMO · Introduction to computing',course='DEMO 101')
        self.stdout.write(f'Demo password (both accounts): {password}')
