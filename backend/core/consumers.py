from urllib.parse import parse_qs
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.core import signing
from .models import User, Session

class SessionConsumer(AsyncJsonWebsocketConsumer):
    @database_sync_to_async
    def allowed(self,ticket,sid):
        try:
            d=signing.loads(ticket,salt='ws-ticket',max_age=30)
            if d['sid']!=sid: return False
            u=User.objects.get(pk=d['uid'],is_active=True);s=Session.objects.get(pk=sid)
            return (s.owner_id==u.pk and u.role=='teacher') or s.memberships.filter(student=u).exists()
        except (signing.BadSignature,KeyError,User.DoesNotExist,Session.DoesNotExist): return False

    async def connect(self):
        sid=self.scope['url_route']['kwargs']['pk'];ticket=parse_qs(self.scope['query_string'].decode()).get('ticket',[''])[0]
        if not await self.allowed(ticket,sid): await self.close(code=4403);return
        self.group=f'session_{sid}'
        try: await self.channel_layer.group_add(self.group,self.channel_name)
        except Exception: await self.close(code=4503);return
        await self.accept();await self.send_json({'type':'sync'})

    async def disconnect(self,code):
        if hasattr(self,'group'):
            try: await self.channel_layer.group_discard(self.group,self.channel_name)
            except Exception: pass

    async def session_changed(self,event): await self.send_json({'type':'sync'})
