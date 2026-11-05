from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase,override_settings,TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User,Session,Membership,Question,Response,MissReason
from .services import advance_schedule,snapshot

@override_settings(CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}})
class ParticipationTests(TestCase):
    def setUp(self):
        self.teacher=User.objects.create_user(username='t',email='t@test.test',password='password-for-tests',role='teacher')
        self.student=User.objects.create_user(username='s',email='s@test.test',password='password-for-tests',role='student')
        self.other=User.objects.create_user(username='o',email='o@test.test',role='teacher')
        self.session=Session.objects.create(owner=self.teacher,title='Algorithms',status='live')
        self.member=Membership.objects.create(session=self.session,student=self.student)
        Membership.objects.filter(pk=self.member.pk).update(joined_at=timezone.now()-timedelta(seconds=2))
        self.member.refresh_from_db()
        self.q=Question.objects.create(session=self.session,prompt='A tree?',kind='mcq',options=['Yes','No'],correct_option=0,status='open',opened_at=timezone.now(),deadline=timezone.now()+timedelta(seconds=60))
        self.client=APIClient();self.client.force_authenticate(self.student)
    def url(self,tail=''): return f'/api/sessions/{self.session.pk}/{tail}'
    def test_directory_hides_codes_and_selected_class_requires_matching_code(self):
        data=self.client.get('/api/classes/').json()
        self.assertTrue(any(x['id']==self.session.pk for x in data))
        self.assertNotIn('code',data[0]);self.assertNotIn('members',data[0])
        self.assertEqual(self.client.post('/api/sessions/join/',{'session_id':self.session.pk+999,'code':self.session.code}).status_code,400)

    def test_recovery_is_delayed_reason_only_with_server_deadline(self):
        self.session.recovery_delay=10;self.session.recovery_duration=20;self.session.save()
        now=timezone.now();self.q.deadline=now-timedelta(seconds=1);self.q.save()
        url=self.url(f'questions/{self.q.pk}/reason/')
        self.assertEqual(self.client.post(url,{'text':'Lost connection'}).status_code,400)
        with patch('core.views.timezone.now',return_value=now+timedelta(seconds=12)):
            self.assertEqual(self.client.post(url,{'text':'Lost connection'}).status_code,201)
            self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/answer/'),{'answer':'0'}).status_code,400)
        MissReason.objects.all().delete()
        with patch('core.views.timezone.now',return_value=now+timedelta(seconds=29)):
            self.assertEqual(self.client.post(url,{'text':'Too late'}).status_code,400)

    def test_persistent_delivery_and_automatic_class_end(self):
        now=timezone.now();self.q.status='closed';self.q.save()
        self.session.delivery_mode='fixed';self.session.interval_seconds=30;self.session.next_question_at=now-timedelta(seconds=1);self.session.ends_at=now+timedelta(seconds=60);self.session.save()
        queued=Question.objects.create(session=self.session,prompt='Next',kind='short')
        advance_schedule();queued.refresh_from_db();self.session.refresh_from_db()
        self.assertEqual(queued.status,'open');self.assertGreater(self.session.next_question_at,now)
        self.session.ends_at=now-timedelta(seconds=1);self.session.save()
        advance_schedule();self.session.refresh_from_db();queued.refresh_from_db()
        self.assertEqual(self.session.status,'ended');self.assertEqual(queued.status,'closed')

    def test_random_bounds_and_invalid_settings(self):
        from .timing import next_time
        self.session.delivery_mode='random';self.session.random_min=10;self.session.random_max=20
        now=timezone.now();delay=(next_time(self.session,now)-now).total_seconds()
        self.assertTrue(10<=delay<=20)
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.post('/api/sessions/',{'title':'Invalid','delivery_mode':'random','random_min':20,'random_max':10}).status_code,400)
    def test_real_answer_and_duplicate(self):
        url=self.url(f'questions/{self.q.pk}/answer/')
        self.assertEqual(self.client.post(url,{'answer':'1'}).status_code,201)
        self.assertEqual(self.client.post(url,{'answer':'0'}).status_code,409)
        self.assertEqual(Response.objects.filter(question=self.q).count(),1)
        cell=snapshot(self.session,self.student)['members'][0]['cells'][0]
        self.assertEqual(cell['participation'],'answered');self.assertIs(cell['correct'],False)
    def test_deadline_is_server_enforced(self):
        self.q.deadline=timezone.now()-timedelta(seconds=1);self.q.save()
        self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/answer/'),{'answer':'0'}).status_code,400)
        self.assertEqual(Response.objects.filter(question=self.q).count(),0)
    def test_deadline_exact_boundary(self):
        deadline=self.q.deadline
        with patch('core.views.timezone.now',return_value=deadline):
            self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/answer/'),{'answer':'0'}).status_code,400)
    def test_student_cannot_mutate_teacher_resources(self):
        for url,body in [(self.url(),{'action':'end'}),(self.url('questions/'),{'prompt':'x'}),(self.url(f'questions/{self.q.pk}/'),{'action':'close'})]:
            self.assertEqual(self.client.post(url,body).status_code,403)
    def test_other_teacher_cannot_read_or_export(self):
        self.client.force_authenticate(self.other)
        for url in [self.url(),self.url('export/')]: self.assertEqual(self.client.get(url).status_code,403)
    def test_outsider_student_cannot_read_answer_or_socket(self):
        outsider=User.objects.create_user(username='outsider',email='outsider@test.test')
        self.client.force_authenticate(outsider)
        self.assertEqual(self.client.get(self.url()).status_code,403)
        self.assertEqual(self.client.post(self.url('ticket/'),{}).status_code,403)
        self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/answer/'),{'answer':'0'}).status_code,403)
    def test_teacher_can_host_without_admin_access(self):
        self.assertFalse(self.teacher.is_staff)
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.post('/api/sessions/',{'title':'Class'}).status_code,201)
        self.assertEqual(self.client.post(self.url(),{'action':'end'}).status_code,200)

    def test_teacher_registration_can_host_immediately_without_staff_privileges(self):
        client=APIClient()
        response=client.post('/api/auth/register/',{'name':'New Teacher','email':'new-teacher@test.test','password':'Fresh-Classroom!9367','role':'teacher','is_staff':True},format='json')
        self.assertEqual(response.status_code,201)
        self.assertNotIn('approved',response.data['user'])
        self.assertFalse(response.data['user']['admin'])
        client.credentials(HTTP_AUTHORIZATION=f'Token {response.data["token"]}')
        room=client.post('/api/sessions/',{'title':'First class'})
        self.assertEqual(room.status_code,201)
        self.assertEqual(client.post(f'/api/sessions/{room.data["id"]}/',{'action':'start'}).status_code,200)

    def test_student_still_cannot_create_sessions(self):
        self.assertEqual(self.client.post('/api/sessions/',{'title':'Student class'}).status_code,403)
    def test_closed_before_join_is_not_eligible(self):
        self.q.deadline=self.member.joined_at-timedelta(seconds=1);self.q.status='closed';self.q.save()
        row=snapshot(self.session,self.student)['members'][0]
        self.assertEqual(row['eligible'],0);self.assertEqual(row['missed'],0)
        self.assertEqual(row['cells'][0]['participation'],'not_eligible')
    def test_early_close_before_join_is_not_eligible(self):
        self.q.closed_at=self.member.joined_at-timedelta(seconds=1);self.q.status='closed';self.q.save()
        self.assertEqual(snapshot(self.session,self.student)['members'][0]['eligible'],0)
    def test_join_open_question_is_eligible(self):
        self.assertEqual(snapshot(self.session,self.student)['members'][0]['eligible'],1)
    def test_refresh_recovery_and_no_answer_key_leak(self):
        self.client.post(self.url(f'questions/{self.q.pk}/answer/'),{'answer':'0'})
        data=self.client.get(self.url()).json()
        self.assertEqual(data['members'][0]['answered'],1)
        self.assertNotIn('correct_option',data['questions'][0])
        stranger=User.objects.create_user(username='second',email='second@test.test')
        Membership.objects.create(session=self.session,student=stranger)
        self.assertEqual(len(self.client.get(self.url()).json()['members']),1)
    def test_rejoin_preserves_initial_join_time(self):
        joined=self.member.joined_at
        self.client.post('/api/sessions/join/',{'code':self.session.code})
        self.member.refresh_from_db();self.assertEqual(self.member.joined_at,joined)
        self.assertEqual(self.session.memberships.count(),1)
    def test_end_closes_question(self):
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.post(self.url(),{'action':'end'}).status_code,200)
        self.q.refresh_from_db();self.assertEqual(self.q.status,'closed');self.assertIsNotNone(self.q.closed_at)
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.post('/api/sessions/join/',{'code':self.session.code}).status_code,400)
    def test_reason_review_keeps_original_miss(self):
        self.q.deadline=timezone.now()-timedelta(milliseconds=1);self.q.status='closed';self.q.save()
        self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/reason/'),{'text':'Internet dropped'}).status_code,201)
        self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/reason/'),{'text':'Again'}).status_code,400)
        reason=MissReason.objects.get(question=self.q);self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.post(self.url(f'reasons/{reason.pk}/review/'),{'status':'accepted','note':'Understood'}).status_code,200)
        row=snapshot(self.session,self.student)['members'][0]
        self.assertEqual(row['missed'],1);self.assertEqual(row['excused'],1);self.assertEqual(row['answered'],0)
    def test_reason_not_allowed_before_deadline_or_after_answer(self):
        self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/reason/'),{'text':'Too soon'}).status_code,400)
        Response.objects.create(question=self.q,membership=self.member,answer='0')
        self.q.deadline=timezone.now()-timedelta(milliseconds=1);self.q.save()
        self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/reason/'),{'text':'Answered'}).status_code,400)
    def test_invalid_option_rejected(self):
        self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/answer/'),{'answer':'999'}).status_code,400)
    def test_connection_does_not_imply_participation(self):
        self.client.post(self.url('heartbeat/'),{})
        row=snapshot(self.session,self.student)['members'][0]
        self.assertEqual(row['connection'],'connected');self.assertEqual(row['answered'],0)
        Membership.objects.filter(pk=self.member.pk).update(last_seen=timezone.now()-timedelta(seconds=46))
        self.assertEqual(snapshot(self.session,self.student)['members'][0]['connection'],'offline')
    def test_scheduler_recovery_and_idempotency(self):
        self.q.status='closed';self.q.save()
        scheduled=Question.objects.create(session=self.session,prompt='Recovered schedule',kind='short',status='scheduled',scheduled_at=timezone.now()-timedelta(seconds=10),duration=30)
        advance_schedule();scheduled.refresh_from_db();opened=scheduled.opened_at
        self.assertEqual(scheduled.status,'open');self.assertIsNotNone(opened)
        advance_schedule();scheduled.refresh_from_db();self.assertEqual(scheduled.opened_at,opened)
        self.assertEqual(self.session.questions.filter(status='open').count(),1)
    def test_overlapping_schedule_waits(self):
        q=Question.objects.create(session=self.session,prompt='Wait',kind='short',status='scheduled',scheduled_at=timezone.now()-timedelta(seconds=1))
        advance_schedule();q.refresh_from_db();self.assertEqual(q.status,'scheduled');self.assertIn('Waiting',q.schedule_error)
    def test_short_answer_grading_does_not_change_participation(self):
        self.q.kind='short';self.q.save()
        self.assertEqual(self.client.post(self.url(f'questions/{self.q.pk}/answer/'),{'answer':'A thought'}).status_code,201)
        r=Response.objects.get(question=self.q);self.assertIsNone(r.correct)
        self.client.force_authenticate(self.teacher)
        self.assertEqual(self.client.post(self.url(f'responses/{r.pk}/grade/'),{'correct':False},format='json').status_code,200)
        self.assertEqual(snapshot(self.session,self.student)['members'][0]['answered'],1)
    def test_csv_export_is_formula_safe_and_owner_only(self):
        self.student.first_name='=HYPERLINK("bad")';self.student.save()
        self.assertEqual(self.client.get(self.url('export/')).status_code,403)
        self.client.force_authenticate(self.teacher)
        data=self.client.get(self.url('export/')).content.decode();self.assertIn("'=HYPERLINK",data)
    def test_approval_endpoint_is_removed(self):
        self.assertEqual(self.client.get('/api/approvals/').status_code,404)
        self.student.is_staff=True;self.student.save()
        self.assertEqual(self.client.post('/api/approvals/',{'user_id':self.other.pk},format='json').status_code,404)

@override_settings(CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}})
class SocketTests(TransactionTestCase):
    def test_authenticated_socket_reconnect_and_bad_ticket(self):
        from asgiref.sync import async_to_sync
        from channels.testing import WebsocketCommunicator
        from channels.routing import URLRouter
        from django.urls import path
        from django.core import signing
        from .consumers import SessionConsumer
        user=User.objects.create_user(username='socket',email='socket@test.test',role='teacher')
        room=Session.objects.create(owner=user,title='Socket room')
        app=URLRouter([path('ws/sessions/<int:pk>/',SessionConsumer.as_asgi())])
        ticket=signing.dumps({'uid':user.pk,'sid':room.pk},salt='ws-ticket')
        async def check():
            for _ in range(2):
                socket=WebsocketCommunicator(app,f'/ws/sessions/{room.pk}/?ticket={ticket}')
                connected,_=await socket.connect();self.assertTrue(connected)
                self.assertEqual(await socket.receive_json_from(),{'type':'sync'});await socket.disconnect()
            bad=WebsocketCommunicator(app,f'/ws/sessions/{room.pk}/?ticket=invalid')
            connected,_=await bad.connect();self.assertFalse(connected);await bad.disconnect()
        async_to_sync(check)()

@override_settings(CHANNEL_LAYERS={'default':{'BACKEND':'channels.layers.InMemoryChannelLayer'}})
class ConcurrentSubmissionTests(TransactionTestCase):
    def test_simultaneous_submissions_commit_only_once(self):
        import threading,queue
        from django.db import close_old_connections
        teacher=User.objects.create_user(username='concurrent-t',email='ct@test.test',role='teacher')
        student=User.objects.create_user(username='concurrent-s',email='cs@test.test')
        session=Session.objects.create(owner=teacher,title='Concurrent',status='live')
        Membership.objects.create(session=session,student=student)
        q=Question.objects.create(session=session,prompt='One answer',kind='short',status='open',opened_at=timezone.now(),deadline=timezone.now()+timedelta(seconds=30))
        barrier=threading.Barrier(2);results=queue.Queue()
        def send(answer):
            close_old_connections()
            try:
                client=APIClient();client.force_authenticate(student);barrier.wait(timeout=5)
                results.put(client.post(f'/api/sessions/{session.pk}/questions/{q.pk}/answer/',{'answer':answer}).status_code)
            except Exception as exc:results.put(str(exc))
            finally:close_old_connections()
        threads=[threading.Thread(target=send,args=(answer,)) for answer in ['first','second']]
        for thread in threads:thread.start()
        for thread in threads:thread.join(timeout=15)
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(sorted([results.get_nowait(),results.get_nowait()]),[201,409])
        self.assertEqual(Response.objects.filter(question=q).count(),1)
