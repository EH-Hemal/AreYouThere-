from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Session, Membership, Question, Response, MissReason
@admin.register(User)
class AccountAdmin(UserAdmin):
    fieldsets=UserAdmin.fieldsets+(('AreYouThere?',{'fields':('role',)}),)
    list_display=('username','email','role','is_staff')
    list_filter=UserAdmin.list_filter+('role',)
admin.site.register([Session,Membership,Question,Response,MissReason])
