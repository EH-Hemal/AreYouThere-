"""Authoritative state transitions. All writers lock the session first."""
import logging
from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import Session, Question
from . import timing

log = logging.getLogger(__name__)

def notify(session_id):
    def send():
        try:
            async_to_sync(get_channel_layer().group_send)(f'session_{session_id}',{'type':'session.changed'})
        except Exception:
            log.warning('Redis delivery unavailable for session %s; clients will resync over REST.',session_id)
    transaction.on_commit(send)

def close_expired(session, now=None):
    now = now or timezone.now()
    changed = Question.objects.filter(session=session,status='open',deadline__lte=now).update(status='closed')
    # Effective close time is min(deadline, closed_at). Natural expiry uses deadline.
    if changed: notify(session.pk)

def open_question(session, question, now=None):
    now = now or timezone.now()
    timing.advance(session,now)
    close_expired(session,now)
    if session.status != 'live': raise ValidationError('Start the session before sending a question.')
    if question.status not in ['draft','scheduled']: raise ValidationError('This question has already been sent.')
    if session.questions.filter(status='open').exists(): raise ValidationError('Close the current question first.')
    question.status='open';question.opened_at=now;question.deadline=now+timedelta(seconds=question.duration)
    question.schedule_error='';question.save()
    session.next_question_at=timing.next_time(session,now);session.save(update_fields=['next_question_at']);notify(session.pk)

def advance_schedule():
    now = timezone.now()
    ids = set(Question.objects.filter(status='scheduled',scheduled_at__lte=now).values_list('session_id',flat=True))
    ids.update(Question.objects.filter(status='open',deadline__lte=now).values_list('session_id',flat=True))
    ids.update(Session.objects.filter(status='live').values_list('id',flat=True))
    for sid in sorted(ids):
        with transaction.atomic():
            session=Session.objects.select_for_update().get(pk=sid)
            timing.advance(session,now)
            close_expired(session,now)
            if session.status=='live' and session.next_question_at and now>=session.next_question_at and not session.questions.filter(status='open').exists():
                queued=session.questions.filter(status='draft').first()
                if queued: open_question(session,queued,now)
            for q in session.questions.filter(status='scheduled',scheduled_at__lte=now).order_by('scheduled_at','id'):
                if session.status == 'ended':
                    q.status='draft';q.schedule_error='Session ended before scheduled delivery.';q.save();continue
                if session.status != 'live' or session.questions.filter(status='open').exists():
                    error='Waiting for the session to start.' if session.status != 'live' else 'Waiting for the current question to close.'
                    if q.schedule_error != error:
                        q.schedule_error=error;q.save();notify(sid)
                    break
                open_question(session,q,now)
                break

def effective_close(q):
    dates=[d for d in [q.deadline,q.closed_at] if d]
    return min(dates) if dates else None

def eligible(q,m):
    end=effective_close(q)
    return bool(q.opened_at and end and m.joined_at < end)

def question_data(q, teacher=False):
    data={k:getattr(q,k) for k in ['id','prompt','kind','options','duration','status','scheduled_at','opened_at','deadline','closed_at','schedule_error']}
    opens,closes=timing.recovery(q)
    data.update(recovery_opens_at=opens,recovery_closes_at=closes)
    if teacher: data['correct_option']=q.correct_option
    return data

def snapshot(session,user):
    now=timezone.now();teacher=session.owner_id == user.pk
    questions=list(session.questions.all())
    if not teacher: questions=[q for q in questions if q.opened_at]
    members=list(session.memberships.select_related('student').all())
    if not teacher: members=[m for m in members if m.student_id==user.pk]
    rows=[]
    for m in members:
        answers={r.question_id:r for r in m.responses.filter(question__session=session)}
        reasons={r.question_id:r for r in m.reasons.filter(question__session=session)}
        cells=[]
        for q in questions:
            if not q.opened_at: continue
            ok=eligible(q,m);response=answers.get(q.pk);reason=reasons.get(q.pk)
            closed=q.status=='closed' or (effective_close(q) and effective_close(q)<=now)
            state='not_eligible' if not ok else 'answered' if response else 'missed' if closed else 'awaiting'
            cells.append({'question_id':q.pk,'participation':state,'answer':response.answer if response else None,'correct':response.correct if response else None,'submitted_at':response.submitted_at if response else None,'response_id':response.pk if response else None,'reason':({'id':reason.pk,'text':reason.text,'status':reason.status,'review_note':reason.review_note} if reason else None)})
        answered=sum(c['participation']=='answered' for c in cells)
        missed=sum(c['participation']=='missed' for c in cells)
        excused=sum(c['participation']=='missed' and c['reason'] is not None and c['reason']['status']=='accepted' for c in cells)
        rows.append({'id':m.pk,'student_id':m.student_id,'name':m.student.get_full_name() or m.student.username,'email':m.student.email,'joined_at':m.joined_at,'connection':'connected' if m.last_seen and m.last_seen>now-timedelta(seconds=45) else 'offline','last_seen':m.last_seen,'answered':answered,'missed':missed,'excused':excused,'eligible':sum(c['participation']!='not_eligible' for c in cells),'cells':cells})
    return {**{k:getattr(session,k) for k in timing.FIELDS},'id':session.pk,'title':session.title,'course':session.course,'code':session.code,'status':session.status,'created_at':session.created_at,'started_at':session.started_at,'ended_at':session.ended_at,'teacher':session.owner.get_full_name() or session.owner.username,'questions':[question_data(q,teacher) for q in questions],'members':rows,'server_time':now}
