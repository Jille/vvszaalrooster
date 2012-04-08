from django.conf.urls.defaults import patterns, include, url
import django.views.generic.simple
import os.path

from django.contrib import auth
import django.contrib.auth.views

import vvs.zaalrooster.views
from vvs import zaalrooster
from vvs.settings import MEDIA_ROOT

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
		url(r'^$', zaalrooster.views.home, name='home'),
		url(r'^(?P<year>\d{4})/(?P<month>\d{2})/$', zaalrooster.views.month_view, name='month-view'),
		url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/inschrijven/$', zaalrooster.views.inschrijven, name='inschrijven'),
		url(r'^((?P<year>\d{4})/(?P<month>\d{2})/((?P<day>\d{2})/)?|(?P<future>future/))?(?P<state>pending|approved|needsigning|confirmed|backup|denied|cancel_request|cancelled)/$', zaalrooster.views.list_view, name='list-view'),
		url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{2})/exception/add/$', zaalrooster.views.add_exception, name='add-exception'),

		url(r'^set-state/$', zaalrooster.views.set_state, name='set-state'),

		url(r'^accounts/login/$', auth.views.login, {'template_name': 'login.html'}, name='login'),
		url(r'^accounts/logout/$', auth.views.logout_then_login, name='logout'),
		url(r'^admin/password_reset/$', auth.views.password_reset, name='admin_password_reset'),
		(r'^admin/password_reset/done/$', auth.views.password_reset_done),
		(r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', auth.views.password_reset_confirm),
		(r'^reset/done/$', auth.views.password_reset_complete),
		url(r'^admin/', include(admin.site.urls)),

		(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': MEDIA_ROOT}),
		(r'^favicon.ico$', 'django.views.generic.simple.redirect_to', {'url': '/media/favicon.ico'}),
)
