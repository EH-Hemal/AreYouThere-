import signal, time, logging
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from core.services import advance_schedule

class Command(BaseCommand):
    help='Poll persistent MySQL schedules. Safe to restart or run multiple workers.'
    def handle(self,*args,**options):
        running=True
        def stop(*_):
            nonlocal running
            running=False
        signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
        self.stdout.write('Persistent scheduler running (one-second interval).')
        state=settings.BASE_DIR.parent/'.runtime';state.mkdir(exist_ok=True)
        while running:
            try:
                close_old_connections();advance_schedule()
                (state/'scheduler-heartbeat').write_text(str(time.time()))
            except Exception: logging.exception('Scheduler iteration failed; will retry')
            time.sleep(1)
