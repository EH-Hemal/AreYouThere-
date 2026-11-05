import os,time
from django.conf import settings
from django.core.management.base import BaseCommand,CommandError
from django.db import connection
import redis
class Command(BaseCommand):
    help='Verify the real configured MySQL and Redis connections without exposing credentials.'
    def handle(self,*args,**kwargs):
        with connection.cursor() as c:
            c.execute('SELECT VERSION(), DATABASE()');version,database=c.fetchone()
        client=redis.Redis.from_url(os.getenv('REDIS_URL','redis://127.0.0.1:6379/0'),socket_timeout=2)
        if not client.ping():raise CommandError('Redis did not answer PING.')
        self.stdout.write(f'MySQL {version}, database {database}: connected. Redis PING: PONG.')
