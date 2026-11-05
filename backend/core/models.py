import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q

def join_code():
    return ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))

class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=[('student','Student'),('teacher','Teacher')], default='student')

class Session(models.Model):
    class_duration = models.PositiveIntegerField(default=0)
    delivery_mode = models.CharField(max_length=10, default='manual')
    interval_seconds = models.PositiveIntegerField(default=300)
    random_min = models.PositiveIntegerField(default=180)
    random_max = models.PositiveIntegerField(default=600)
    question_duration = models.PositiveIntegerField(default=60)
    recovery_delay = models.PositiveIntegerField(default=30)
    recovery_duration = models.PositiveIntegerField(default=0)
    next_question_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_sessions')
    title = models.CharField(max_length=160)
    course = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=6, unique=True, default=join_code)
    status = models.CharField(max_length=10, default='lobby', choices=[('lobby','Lobby'),('live','Live'),('ended','Ended')])
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

class Membership(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='memberships')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['session','student'], name='one_membership')]

class Question(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='questions')
    prompt = models.TextField(max_length=2000)
    kind = models.CharField(max_length=8, choices=[('mcq','Multiple choice'),('short','Short answer')])
    options = models.JSONField(default=list, blank=True)
    correct_option = models.IntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=60)
    status = models.CharField(max_length=12, default='draft', choices=[('draft','Draft'),('scheduled','Scheduled'),('open','Open'),('closed','Closed')])
    scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    schedule_error = models.CharField(max_length=200, blank=True)
    class Meta:
        ordering = ['id']
        constraints = [models.CheckConstraint(condition=Q(duration__gte=10) & Q(duration__lte=3600),name='valid_question_duration')]

class Response(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='responses')
    answer = models.TextField(max_length=4000)
    correct = models.BooleanField(null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['question','membership'],name='one_response')]

class MissReason(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='reasons')
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='reasons')
    text = models.TextField(max_length=1000)
    status = models.CharField(max_length=10, default='pending', choices=[('pending','Pending'),('accepted','Excused'),('rejected','Rejected')])
    review_note = models.CharField(max_length=1000, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['question','membership'],name='one_reason')]
