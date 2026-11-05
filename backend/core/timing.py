from datetime import timedelta
import secrets
from django.utils import timezone
from rest_framework.exceptions import ValidationError

FIELDS = ['class_duration','delivery_mode','interval_seconds','random_min','random_max','question_duration','recovery_delay','recovery_duration','ends_at','next_question_at']

def settings(data):
    result={}
    defaults={'class_duration':0,'interval_seconds':300,'random_min':180,'random_max':600,'question_duration':60,'recovery_delay':30,'recovery_duration':0}
    for key,default in defaults.items():
        try: result[key]=int(data.get(key,default))
        except (ValueError,TypeError): raise ValidationError(f'{key} must be a whole number of seconds.')
        lower=10 if key in ['interval_seconds','random_min','random_max','question_duration'] else 0
        upper=43200 if key=='class_duration' else 3600
        if not lower<=result[key]<=upper: raise ValidationError(f'{key} must be between {lower} and {upper} seconds.')
    result['delivery_mode']=data.get('delivery_mode','manual')
    if result['delivery_mode'] not in ['manual','fixed','random']: raise ValidationError('Choose manual, fixed or random delivery.')
    if result['random_max']<result['random_min']: raise ValidationError('Random maximum must be at least the minimum.')
    return result

def next_time(session,now):
    if session.delivery_mode=='manual': return None
    delay=session.interval_seconds if session.delivery_mode=='fixed' else secrets.randbelow(session.random_max-session.random_min+1)+session.random_min
    return now+timedelta(seconds=delay)

def advance(session,now=None):
    from .services import notify
    now=now or timezone.now()
    if session.status=='live' and session.ends_at and now>=session.ends_at:
        end(session,session.ends_at);notify(session.pk)

def end(session,now):
    session.status='ended';session.ended_at=now;session.next_question_at=None
    session.questions.filter(status='open').update(status='closed',closed_at=now)
    session.questions.filter(status='scheduled').update(status='draft',schedule_error='Session ended before scheduled delivery.')
    session.save()

def recovery(q):
    from .services import effective_close
    end_at=effective_close(q)
    if not end_at or not q.session.recovery_duration: return (None,None)
    opens=end_at+timedelta(seconds=q.session.recovery_delay)
    return opens,opens+timedelta(seconds=q.session.recovery_duration)
