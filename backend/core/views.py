import csv, io, secrets
from datetime import timedelta
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction, connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response as APIResponse
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.authtoken.models import Token
from rest_framework.throttling import ScopedRateThrottle, AnonRateThrottle
from . import timing
from .models import User, Session, Membership, Question, Response, MissReason
from .services import snapshot, notify, close_expired, open_question, eligible, effective_close

class AuthThrottle(AnonRateThrottle):
    rate='10/min'

def user_data(u):
    return {'id':u.pk,'name':u.get_full_name() or u.username,'email':u.email,'role':u.role,'admin':u.is_staff}

def teacher_only(u):
    if u.role!='teacher': raise PermissionDenied('Only teachers can host a class.')

def session_access(pk,u,owner=False,lock=False):
    qs=Session.objects.select_for_update() if lock else Session.objects
    s=get_object_or_404(qs,pk=pk)
    if s.owner_id==u.pk:
        teacher_only(u);return s
    if owner or not s.memberships.filter(student=u).exists(): raise PermissionDenied('You do not have access to this session.')
    return s

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def register(request):
    d=request.data;email=str(d.get('email','')).strip().lower();name=str(d.get('name','')).strip();password=d.get('password','');role=d.get('role','student')
    from django.core.validators import validate_email
    try:
        validate_email(email)
        if len(email)>150:raise ValidationError('Use an email address up to 150 characters.')
        if not name or len(name)>150 or role not in ['student','teacher']: raise ValidationError('Enter a valid name and account type.')
        validate_password(password,User(username=email,email=email))
        u=User.objects.create_user(username=email,email=email,password=password,first_name=name,role=role)
    except DjangoValidationError as exc: raise ValidationError(exc.messages)
    except IntegrityError: raise ValidationError('An account already exists for this email.')
    token=Token.objects.create(user=u)
    return APIResponse({'token':token.key,'user':user_data(u)},status=201)

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def login(request):
    u=authenticate(username=str(request.data.get('email','')).strip().lower(),password=request.data.get('password',''))
    if not u: return APIResponse({'detail':'Email or password is incorrect.'},status=400)
    token,created=Token.objects.get_or_create(user=u)
    if token.created < timezone.now()-timedelta(days=7):
        token.delete();token=Token.objects.create(user=u)
    return APIResponse({'token':token.key,'user':user_data(u)})

@api_view(['GET','POST'])
def me(request):
    if request.method=='POST': Token.objects.filter(user=request.user).delete();return APIResponse({'detail':'Signed out.'})
    return APIResponse(user_data(request.user))

@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    db=redis=False
    try:
        with connection.cursor() as c: c.execute('SELECT 1');db=c.fetchone()[0]==1
    except Exception: pass
    try:
        import redis as redis_module, os
        redis=redis_module.Redis.from_url(os.getenv('REDIS_URL','redis://127.0.0.1:6379/0'),socket_connect_timeout=1,socket_timeout=1).ping()
    except Exception: pass
    return APIResponse({'database':db,'realtime':bool(redis)},status=200 if db and redis else 503)

@api_view(['GET','POST'])
def sessions(request):
    u=request.user
    if request.method=='POST':
        teacher_only(u);title=str(request.data.get('title','')).strip();course=str(request.data.get('course','')).strip()
        if not title or len(title)>160 or len(course)>100: raise ValidationError('Enter a title up to 160 characters and course up to 100 characters.')
        s=Session.objects.create(owner=u,title=title,course=course,**timing.settings(request.data));return APIResponse(snapshot(s,u),status=201)
    qs=Session.objects.filter(owner=u) if u.role=='teacher' else Session.objects.filter(memberships__student=u)
    return APIResponse([{'id':s.pk,'title':s.title,'course':s.course,'status':s.status,'code':s.code,'created_at':s.created_at,'members':s.memberships.count(),'questions':s.questions.filter(opened_at__isnull=False).count()} for s in qs.order_by('-created_at')])

@api_view(['POST'])
def join(request):
    if request.user.role!='student': raise PermissionDenied('Only students can join a class.')
    with transaction.atomic():
        s=get_object_or_404(Session.objects.select_for_update(),code=str(request.data.get('code','')).strip().upper())
        timing.advance(s)
        if request.data.get('session_id') is not None and str(request.data['session_id'])!=str(s.pk): raise ValidationError('Code does not match the selected class.')
        if s.status=='ended': raise ValidationError('This session has ended.')
        m,_=Membership.objects.get_or_create(session=s,student=request.user)
        m.last_seen=timezone.now();m.save(update_fields=['last_seen']);notify(s.pk)
    return APIResponse(snapshot(s,request.user))

@api_view(['GET','POST'])
def session_detail(request,pk):
    with transaction.atomic():
        s=session_access(pk,request.user,owner=request.method=='POST',lock=True)
        timing.advance(s)
        close_expired(s)
        if request.method=='POST':
            action=request.data.get('action');now=timezone.now()
            if action=='start' and s.status=='lobby':
                s.status='live';s.started_at=now
                s.ends_at=now+timedelta(seconds=s.class_duration) if s.class_duration else None
                s.next_question_at=timing.next_time(s,now)
            elif action=='end' and s.status in ['lobby','live']:
                s.status='ended';s.ended_at=now
                s.questions.filter(status='open').update(status='closed',closed_at=now)
                s.questions.filter(status='scheduled').update(status='draft',schedule_error='Session ended before scheduled delivery.')
            else: raise ValidationError('Invalid session transition.')
            s.save();notify(s.pk)
        data=snapshot(s,request.user)
    return APIResponse(data)

@api_view(['POST'])
def heartbeat(request,pk):
    s=session_access(pk,request.user)
    if request.user.pk!=s.owner_id:
        m=s.memberships.get(student=request.user);was=m.last_seen;m.last_seen=timezone.now();m.save(update_fields=['last_seen'])
        if not was or was<timezone.now()-timedelta(seconds=30): notify(s.pk)
    return APIResponse({'server_time':timezone.now()})

def validate_question(data):
    prompt=str(data.get('prompt','')).strip();kind=data.get('kind');options=data.get('options',[])
    try: duration=int(data.get('duration',60))
    except (ValueError,TypeError): raise ValidationError('Duration must be a number.')
    if not prompt or len(prompt)>2000 or kind not in ['mcq','short'] or not 10<=duration<=3600: raise ValidationError('Enter a question, valid type, and duration between 10 and 3600 seconds.')
    correct=None
    if kind=='mcq':
        if not isinstance(options,list) or not 2<=len(options)<=6 or any(not isinstance(o,str) or not o.strip() or len(o)>300 for o in options): raise ValidationError('Provide 2–6 nonempty choices, up to 300 characters each.')
        try: correct=int(data.get('correct_option'))
        except (ValueError,TypeError): raise ValidationError('Choose the correct option.')
        if not 0<=correct<len(options): raise ValidationError('Choose a valid correct option.')
    else: options=[]
    schedule=data.get('scheduled_at');scheduled_at=None
    if schedule:
        scheduled_at=parse_datetime(str(schedule))
        if not scheduled_at or timezone.is_naive(scheduled_at) or scheduled_at<=timezone.now(): raise ValidationError('Choose a future schedule with timezone.')
    return dict(prompt=prompt,kind=kind,options=options,correct_option=correct,duration=duration,scheduled_at=scheduled_at,status='scheduled' if scheduled_at else 'draft')

@api_view(['POST'])
def questions(request,pk):
    with transaction.atomic():
        s=session_access(pk,request.user,owner=True,lock=True)
        timing.advance(s)
        if s.status=='ended': raise ValidationError('This session has ended.')
        Question.objects.create(session=s,**validate_question({'duration':s.question_duration,**request.data}));notify(s.pk)
    return APIResponse(snapshot(s,request.user),status=201)

@api_view(['POST','PATCH','DELETE'])
def question_action(request,pk,qid):
    with transaction.atomic():
        s=session_access(pk,request.user,owner=True,lock=True);q=get_object_or_404(Question,pk=qid,session=s)
        close_expired(s);q.refresh_from_db()
        if request.method in ['PATCH','DELETE']:
            if q.status not in ['draft','scheduled'] or s.status=='ended': raise ValidationError('Only unsent questions can be edited.')
            if request.method=='DELETE': q.delete()
            else:
                for key,value in validate_question(request.data).items(): setattr(q,key,value)
                q.save()
        elif request.data.get('action')=='open': open_question(s,q)
        elif request.data.get('action')=='close' and q.status=='open': q.status='closed';q.closed_at=timezone.now();q.save()
        else: raise ValidationError('Invalid question transition.')
        notify(s.pk)
    return APIResponse(snapshot(s,request.user))

@api_view(['POST'])
def answer(request,pk,qid):
    with transaction.atomic():
        s=session_access(pk,request.user,lock=True)
        if request.user.role!='student': raise PermissionDenied('Only a student can answer.')
        m=s.memberships.get(student=request.user);q=get_object_or_404(Question,pk=qid,session=s);now=timezone.now()
        timing.advance(s,now)
        if s.status!='live' or q.status!='open' or not q.deadline or now>=q.deadline or not eligible(q,m): raise ValidationError('This question is closed or you are not eligible.')
        if Response.objects.filter(question=q,membership=m).exists(): return APIResponse({'detail':'You have already answered this question.'},status=409)
        value=str(request.data.get('answer','')).strip();correct=None
        if not value or len(value)>4000: raise ValidationError('Enter an answer up to 4000 characters.')
        if q.kind=='mcq':
            if value not in [str(i) for i in range(len(q.options))]: raise ValidationError('Choose a valid option.')
            correct=int(value)==q.correct_option
        Response.objects.create(question=q,membership=m,answer=value,correct=correct);notify(s.pk)
    return APIResponse(snapshot(s,request.user),status=201)

@api_view(['POST'])
def reason(request,pk,qid):
    with transaction.atomic():
        s=session_access(pk,request.user,lock=True)
        if request.user.role!='student': raise PermissionDenied()
        m=s.memberships.get(student=request.user);q=get_object_or_404(Question,pk=qid,session=s);text=str(request.data.get('text','')).strip()
        if not eligible(q,m) or not effective_close(q) or effective_close(q)>timezone.now() or q.responses.filter(membership=m).exists(): raise ValidationError('A reason can only be submitted for an eligible missed question.')
        opens,closes=timing.recovery(q)
        if opens and not opens<=timezone.now()<closes: raise ValidationError('The recovery window is not open.')
        if not text or len(text)>1000: raise ValidationError('Enter a reason up to 1000 characters.')
        if MissReason.objects.filter(question=q,membership=m).exists(): raise ValidationError('A reason was already submitted.')
        MissReason.objects.create(question=q,membership=m,text=text);notify(s.pk)
    return APIResponse(snapshot(s,request.user),status=201)

@api_view(['POST'])
def review(request,pk,rid):
    with transaction.atomic():
        s=session_access(pk,request.user,owner=True,lock=True);r=get_object_or_404(MissReason,pk=rid,question__session=s)
        status=request.data.get('status');note=str(request.data.get('note','')).strip()
        if status not in ['accepted','rejected'] or len(note)>1000: raise ValidationError('Choose excused or rejected, with a note up to 1000 characters.')
        r.status=status;r.review_note=note;r.reviewed_at=timezone.now();r.save();notify(s.pk)
    return APIResponse(snapshot(s,request.user))

@api_view(['POST'])
def grade(request,pk,rid):
    with transaction.atomic():
        s=session_access(pk,request.user,owner=True,lock=True);r=get_object_or_404(Response,pk=rid,question__session=s)
        if r.question.kind!='short' or not isinstance(request.data.get('correct'),bool): raise ValidationError('Supply a correctness value for a short answer.')
        r.correct=request.data['correct'];r.save();notify(s.pk)
    return APIResponse(snapshot(s,request.user))

def csv_safe(value):
    value='' if value is None else str(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else value

@api_view(['GET'])
def export(request,pk):
    s=session_access(pk,request.user,owner=True);data=snapshot(s,request.user);out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['Student','Email','Question','Participation','Answer','Correctness','Connection','Reason','Review','Review note'])
    prompts={q['id']:q for q in data['questions']}
    for m in data['members']:
        for c in m['cells']:
            q=prompts[c['question_id']];answer=c['answer']
            if q['kind']=='mcq' and answer is not None: answer=q['options'][int(answer)]
            reason=c['reason'] or {}
            writer.writerow(map(csv_safe,[m['name'],m['email'],q['prompt'],c['participation'],answer,'ungraded' if c['correct'] is None else 'correct' if c['correct'] else 'incorrect',m['connection'],reason.get('text'),reason.get('status'),reason.get('review_note')]))
    response=HttpResponse(out.getvalue(),content_type='text/csv; charset=utf-8');response['Content-Disposition']=f'attachment; filename="areyouthere-session-{s.pk}.csv"';return response

@api_view(['POST'])
def socket_ticket(request,pk):
    session_access(pk,request.user)
    from django.core import signing
    return APIResponse({'ticket':signing.dumps({'uid':request.user.pk,'sid':pk},salt='ws-ticket')})

@api_view(['GET'])
def directory(request):
    from django.db.models import Q
    now=timezone.now()
    qs=Session.objects.filter(status__in=['lobby','live']).filter(Q(ends_at__isnull=True)|Q(ends_at__gt=now)).select_related('owner')
    return APIResponse([{'id':s.pk,'title':s.title,'teacher':s.owner.get_full_name() or s.owner.username,'status':s.status} for s in qs.order_by('-created_at')[:200]])
