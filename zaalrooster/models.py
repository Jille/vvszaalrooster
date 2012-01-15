from django.db import models
from django.contrib.auth.models import User, Group
from vvs.zaalrooster.util import split_date
from django.core.urlresolvers import reverse

weekdays = {
	1: 'maandag',
	2: 'dinsdag',
	3: 'woensdag',
	4: 'donderdag',
	5: 'vrijdag',
	6: 'zaterdag',
	7: 'zondag',
}

states = (
	('pending', 'Aangevraagd'),
	('approved', 'Goedgekeurd'),
	('confirmed', 'Getekend'),
	('backup', 'Reservelijst'),
	('denied', 'Geweigerd'),
	('cancelled', 'Geannuleerd'),
)
states_dict = dict(states)

class EnumField(models.Field):
	def db_type(self, connection):
		return "enum({0})".format(','.join("'%s'" % v[0] for v in self.choices))

class VvSUser(User):
	@property
	def cached_vvsgroups(self):
		if not hasattr(self, '__vvsgroups_cache'):
			self.__vvsgroups_cache = list(VvSGroup.objects.filter(user=self))
		return self.__vvsgroups_cache

	@property
	def can_moderate(self):
		if not hasattr(self, '__can_moderate_cache'):
			self.__can_moderate_cache = False
			for g in self.cached_vvsgroups:
				if g.can_moderate:
					self.__can_moderate_cache = True
					break
		return self.__can_moderate_cache

	class Meta:
		verbose_name = "gebruiker"

class VvSGroup(Group):
	can_moderate = models.BooleanField()
	notifications_to = models.EmailField(blank=True, null=True)

	class Meta:
		verbose_name = "groep"
		verbose_name_plural = "groepen"

class Room(models.Model):
	name = models.CharField("naam", max_length=32, unique=True)

	def __unicode__(self):
		return self.name

	class Meta:
		verbose_name = "zaal"
		verbose_name_plural = "zalen"

class FixedRent(models.Model):
	weekday = models.PositiveSmallIntegerField("weekdag", choices=weekdays.items())
	room = models.ForeignKey(Room, verbose_name="zaal")
	hirer = models.ForeignKey(VvSGroup, verbose_name="huurder")
	timeframe = models.CharField(max_length=32)
	begin = models.DateField()
	end = models.DateField(default="2030-01-01")

	def is_active_at(self, date):
		return (self.begin <= date and date <= self.end)

	def __unicode__(self):
		return "%s op %s in de %s" % (self.hirer, weekdays[self.weekday], self.room)

	class Meta:
		verbose_name = "vaste huur"
		verbose_name_plural = "vaste huur"

class FixedRentException(models.Model):
	rental = models.ForeignKey(FixedRent)
	date = models.DateField("datum")
	added = models.DateTimeField("Ingevoerd", auto_now_add=True)

	def __unicode__(self):
		return "%s (%s)" % (self.date.strftime("%d %B %Y"), self.rental)

	@models.permalink
	def get_absolute_url(self):
		return ('month-view', (), split_date(self.date, include_day=False))

	class Meta:
		verbose_name = "vaste huur uitzondering"
		verbose_name_plural = "vaste huur uitzonderingen"

class Reservation(models.Model):
	date = models.DateField("datum")
	hirer = models.ForeignKey(VvSGroup, verbose_name="huurder")
	room = models.ForeignKey(Room, verbose_name="zaal")
	name = models.CharField("wat", max_length=32)
	timeframe = models.CharField(max_length=32)
	state = EnumField("status", choices=states, default='pending')
	added = models.DateTimeField("Ingevoerd", auto_now_add=True)

	def getHumanState(self):
		return states_dict[self.state]

	@models.permalink
	def get_absolute_url(self):
		return ('month-view', (), split_date(self.date, include_day=False))

	def __unicode__(self):
		return "%s in de %s op %s (%s)" % (self.hirer, self.room, self.date.strftime("%d %B %Y"), self.name)

	class Meta:
		verbose_name = "reservering"
		verbose_name_plural = "reserveringen"
