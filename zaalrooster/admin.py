from django.contrib import admin
#from django.contrib.admin import SimpleListFilter

import datetime

from vvs.zaalrooster.models import *

#class InFutureListFilter(SimpleListFilter):
#	title = 'Toekomst'
#	parameter_name = 'future'
#
#	def lookups(self, request, model_admin):
#		return (('yes', 'Ja'), )
#
#	def queryset(self, request, queryset):
#		if self.value() == 'yes':
#			return queryset.filter(date__gte=datetime.date.today())

class VvSUserAdmin(admin.ModelAdmin):
	list_display = ('username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff')
	search_fields = ('username', 'first_name', 'last_name', 'email')
	list_filter = ('is_active', 'is_staff')
	ordering = ('is_active', 'username')
	exclude = ('user_permissions', )

	def save_model(self, request, obj, form, change):
		if obj.password.find('$') == -1:
			obj.set_password(obj.password)
		obj.save()

	def get_readonly_fields(self, request, obj=None):
		if request.user.is_superuser:
			return ('last_login', 'date_joined')
		else:
			return ('is_superuser', 'last_login', 'date_joined')

class VvSGroupAdmin(admin.ModelAdmin):
	list_display = ('name', 'notifications_to', 'can_moderate')
	search_fields = ('name', 'notifications_to')
	list_filter = ('can_moderate', )
	ordering = ('name', )
	exclude = ('permissions', )

class RoomAdmin(admin.ModelAdmin):
	list_display = ('name', )
	search_fields = ('name', )
	ordering = ('name', )

class FixedRentAdmin(admin.ModelAdmin):
	list_display = ('weekday', 'room', 'hirer', 'timeframe', 'begin', 'end')
	ordering = ('weekday', 'room')
	list_filter = ('weekday', 'room', 'hirer')

class FixedRentExceptionAdmin(admin.ModelAdmin):
	list_display = ('rental', 'date', 'added')
	ordering = ('date', )
	list_filter = ('rental', )
	date_hierarchy = 'date'
	readonly_fields = ('added', )

class ReservationAdmin(admin.ModelAdmin):
	list_display = ('name', 'room', 'date', 'hirer', 'state', 'timeframe', 'added')
	search_fields = ('name', 'timeframe')
	ordering = ('date', 'room', 'added')
	list_filter = ('state', 'room', 'hirer')
	date_hierarchy = 'date'
	readonly_fields = ('added', )

admin.site.register(VvSUser, VvSUserAdmin)
admin.site.register(VvSGroup, VvSGroupAdmin)
admin.site.register(Reservation, ReservationAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(FixedRent, FixedRentAdmin)
admin.site.register(FixedRentException, FixedRentExceptionAdmin)

admin.site.unregister(User)
admin.site.unregister(Group)
