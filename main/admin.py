from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'
    fk_name = 'user'


class CustomUserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, )

    def get_role(self, instance):
        return instance.profile.role
    get_role.short_description = 'Role'

    list_display = ('username', 'email', 'first_name',
                    'last_name', 'is_staff', 'get_role')
    list_select_related = ('profile',)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
