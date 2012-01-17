import datetime

from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.core.mail import EmailMessage
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from vvs.zaalrooster.models import *
from vvs.zaalrooster.forms import *
from vvs.zaalrooster.util import *
from vvs import settings

from locale import setlocale, normalize, LC_TIME

cancellable_states = ('pending', 'approved', 'backup')

def home(request):
	if not request.user.is_authenticated() or not request.user.vvsuser.can_moderate:
		return month_view(request)

	today = datetime.date.today()
	setlocale(LC_TIME, normalize('nl_NL'))
	nextMonth = today
	while nextMonth.month == today.month:
		nextMonth += datetime.timedelta(days=1)
	months = []
	for dt in [today, nextMonth]:
		months.append(dict(split_date(dt, include_day=False), human=dt.strftime("%B %Y").capitalize()))
	return render_to_response('moderator_home.html', {'months': months}, context_instance=RequestContext(request))

@login_required
def month_view(request, year = None, month = None):
	setlocale(LC_TIME, normalize('nl_NL'))
	today = datetime.date.today()
	if year is None:
		year = today.year
	else:
		year = int(year)
	if month is None:
		month = today.month
	else:
		month = int(month)

	firstDOM = datetime.date(year, month, 1)
	monthhuman = firstDOM.strftime("%B")

	firstDIC = firstDOM - datetime.timedelta(days=(firstDOM.isoweekday()+5) % 7 + 1)
	assert(firstDIC.isoweekday() == 1)
	lastDIC = firstDIC + datetime.timedelta(days=6*7 - 1)
	assert(lastDIC.isoweekday() == 7)

	rooms = dict(map(lambda x: (x.id, x.name), Room.objects.all()))
	can_subscribe = len(request.user.vvsuser.cached_vvsgroups) > 0

	dmap = {}
	table = []
	dt = firstDIC
	for w in xrange(6):
		roomrows = []
		rowdates = []
		for d in xrange(7):
			dmap[dt] = {}
			for room in rooms:
				dmap[dt][room] = {'fixedRent': [], 'fixedRentExceptions': [], 'reservations': []}
			rowdates.append(dt)
			dt += datetime.timedelta(days=1)

		for room in rooms:
			roomrow = {'room': rooms[room], 'days': []}
			for rd in rowdates:
				roomrow['days'].append({
					'date': rd.strftime("%d %b"),
					'subscribeURL': reverse('inschrijven', kwargs=split_date(rd)) if can_subscribe and rd >= today else None,
					'activeMonth': (rd.month == month),
					'fixedRent': dmap[rd][room]['fixedRent'],
					'fixedRentExceptions': dmap[rd][room]['fixedRentExceptions'],
					'reservations': dmap[rd][room]['reservations'],
				})
			roomrows.append(roomrow)
		table.append(roomrows)

	for fr in FixedRent.objects.filter(begin__lte=lastDIC, end__gte=firstDIC):
		dt = firstDIC + datetime.timedelta(days=fr.weekday-1)
		assert(dt.isoweekday() == fr.weekday)
		for i in xrange(6):
			if fr.is_active_at(dt):
				dmap[dt][fr.room.id]['fixedRent'].append(fr)
			dt += datetime.timedelta(days=7)

	for fre in FixedRentException.objects.filter(date__range=(firstDIC, lastDIC)):
		dmap[fre.date][fre.rental.room.id]['fixedRentExceptions'].append(fre)
		try:
			dmap[fre.date][fre.rental.room.id]['fixedRent'].remove(fre.rental)
		except ValueError:
			# Een exception zonder dat er dan vast huur is...
			pass

	for r in Reservation.objects.filter(date__range=(firstDIC, lastDIC)).order_by('state'):
		dmap[r.date][r.room.id]['reservations'].append(r)

	if month == 1:
		prev = reverse('month-view', kwargs={'year': year-1, 'month': "12"})
	else:
		prev = reverse('month-view', kwargs={'year': year, 'month': "%02d" % (month-1)})
	if month == 12:
		next = reverse('month-view', kwargs={'year': year+1, 'month': "01"})
	else:
		next = reverse('month-view', kwargs={'year': year, 'month': "%02d" % (month+1)})

	return render_to_response('month.html', {'year': year, 'month': month, 'monthhuman': monthhuman, 'rooms': rooms, 'table': table, 'next': next, 'prev': prev}, context_instance=RequestContext(request))

@login_required
def list_view(request, state, year=None, month=None, day=None, future=None):
	if not request.user.vvsuser.can_moderate:
		raise PermissionDenied
	setlocale(LC_TIME, normalize('nl_NL'))
	qs = Reservation.objects.filter(state=state)
	if year is not None and month is not None:
		if day is None:
			firstDOM = datetime.date(int(year), int(month), 1)
			lastDOM = firstDOM + datetime.timedelta(days=31)
			while firstDOM.month != lastDOM.month:
				lastDOM -= datetime.timedelta(days=1)
			qs = qs.filter(date__range=(firstDOM, lastDOM))
			humanperiod = firstDOM.strftime(" in %B %Y")
		else:
			date = datetime.date(int(year), int(month), int(day))
			qs = qs.filter(date=date)
			humanperiod = date.strftime(" op %d %B %Y")
	elif future is not None:
		date = datetime.date.today()
		qs = qs.filter(date__gte=date)
		humanperiod = date.strftime(" vanaf %d %B %Y")
	else:
		humanperiod = ""

	reservations = list(qs.order_by('date'))

	humanstate = states_dict[state]

	return render_to_response('list.html', {'humanperiod': humanperiod, 'humanstate': humanstate, 'reservations': reservations, 'states': states}, context_instance=RequestContext(request))

@login_required
def set_state(request):
	setlocale(LC_TIME, normalize('nl_NL'))
	id = int(request.REQUEST['id'])
	newstate = request.REQUEST['state']
	r = Reservation.objects.get(id=id)
	oldstate = r.state

	if request.user.vvsuser.can_moderate:
		pass
	elif r.hirer in request.user.vvsuser.cached_vvsgroups and oldstate in cancellable_states and newstate == "cancelled":
		pass
	else:
		raise PermissionDenied

	r.state = newstate;
	r.save()
	if oldstate == newstate:
		messages.info(request, "Status niet gewijzigd")
	elif oldstate == "pending" and newstate == "approved":
		if r.hirer.notifications_to:
			subj = "[Zaalrooster] Reservering %s %s goedgekeurd" % (r.room, r.date.strftime("%d %b"))
			msg = "De reservering voor de %s op %s (%s) is goedgekeurd. (%s)" % (r.room, r.date.strftime("%d %B %Y"), r.timeframe, r.name)
			em = EmailMessage(subj, msg, to=[r.hirer.notifications_to], cc=settings.MODERATORS)
			em.send()
			messages.success(request, "Mail over goedkeuring verzonden.")
		else:
			messages.info(request, "Mail over goedkeuring niet verzonden. Er is geen e-mailadres ingesteld voor %s." % r.hirer)
	elif oldstate == "pending" and newstate == "confirmed":
		if r.hirer.notifications_to:
			subj = "[Zaalrooster] Zaalhuur %s %s bevestigd" % (r.room, r.date.strftime("%d %b"))
			msg = "De zaalhuur voor de %s op %s (%s) is getekend. (%s)" % (r.room, r.date.strftime("%d %B %Y"), r.timeframe, r.name)
			em = EmailMessage(subj, msg, to=[r.hirer.notifications_to], cc=settings.MODERATORS)
			em.send()
			messages.success(request, "Mail over tekenen verzonden.")
		else:
			messages.info(request, "Mail over tekenen niet verzonden. Er is geen e-mailadres ingesteld voor %s." % r.hirer)
	elif oldstate in ("pending", "approved") and newstate == "needsigning":
		if r.hirer.notifications_to:
			subj = "[Zaalrooster] Zaalhuur %s %s te tekenen" % (r.room, r.date.strftime("%d %b"))
			msg = "Het contract voor de zaalhuur van de %s op %s (%s) moet getekend worden. (%s)" % (r.room, r.date.strftime("%d %B %Y"), r.timeframe, r.name)
			em = EmailMessage(subj, msg, to=[r.hirer.notifications_to], cc=settings.MODERATORS)
			em.send()
			messages.success(request, "Mail over tekenverzoek verzonden.")
		else:
			messages.info(request, "Mail over tekenverzoek niet verzonden. Er is geen e-mailadres ingesteld voor %s." % r.hirer)
	elif not request.user.vvsuser.can_moderate and newstate == "cancelled":
		subj = "[Zaalrooster] Reservering %s op %s geannuleerd" % (r.room, r.date.strftime("%d %b"))
		msg = "De zaalhuur van de %s op %s (%s) is door %s geannuleerd. (%s)" % (r.room, r.date.strftime("%d %B %Y"), r.timeframe, r.hirer, r.name)
		em = EmailMessage(subj, msg, to=settings.MODERATORS, cc=[request.user.email])
		em.send()
		messages.success(request, "Reservering geannuleerd.")
		return HttpResponseRedirect(reverse('month-view', kwargs=split_date(r.date, include_day=False)))
	else:
		messages.info(request, "Status gewijzigd. Er is geen automatische e-mail verzonden!")

	return HttpResponseRedirect(r.date.strftime("/%Y/%m/%d/") + r.state +"/")

@login_required
def inschrijven(request, year, month, day):
	setlocale(LC_TIME, normalize('nl_NL'))
	date = datetime.date(int(year), int(month), int(day))

	ReservationForm = getReservationForm(request.user)
	if request.method == 'POST':
		r = Reservation(date=date)
		form = ReservationForm(request.POST, instance=r)
		if form.is_valid():
			form.save(commit=False)
			if not request.user.vvsuser.can_moderate:
				if room_is_free_at(r.room, date):
					r.state = 'pending'
					messages.success(request, "Je reservering is aangevraagd.")
				else:
					r.state = 'backup'
					messages.warning(request, "Er staan ook andere reserveringen open voor de %s op %s. Je bent op de reservelijst gezet." % (r.room, r.date.strftime("%d %B %Y")))
			else:
				messages.success(request, "Reservering geplaatst.")
			r.save()
			month_url = reverse('month-view', kwargs={'year': year, 'month': month})
			if not request.user.vvsuser.can_moderate:
				subj = "[Zaalrooster] Aanvraag van %s voor %s" % (r.hirer, date.strftime("%d %b"))
				msg = "%s wil graag de %s op %s (%s) voor een %s.\nHuidige status: %s\n\n%s" % (r.hirer, r.room, date.strftime("%d %B %Y"), r.timeframe, r.name, r.getHumanState(), settings.SITE_URL + month_url)
				em = EmailMessage(subj, msg, to=settings.MODERATORS, cc=[request.user.email])
				em.send()
			return HttpResponseRedirect(month_url)
	else:
		form = ReservationForm()

	datehuman = date.strftime("%d %B %Y")

	frs = list(FixedRent.objects.filter(begin__lte=date, end__gte=date, weekday=date.isoweekday(), hirer__in=request.user.vvsuser.cached_vvsgroups).order_by('hirer'))
	if len(frs) > 0:
		for fre in FixedRentException.objects.filter(date=date, rental__in=frs):
			# Verwijder hem en zet hem er opnieuw in met cancelled = True
			# Direct wijzigen werkte niet en zo komt hij ook mooi onderaan
			frs.remove(fre.rental)
			fre.rental.cancelled = True
			frs.append(fre.rental)
	rs = list(Reservation.objects.filter(date=date, hirer__in=request.user.vvsuser.cached_vvsgroups).exclude(state__in=['denied', 'cancelled']).order_by('hirer'))

	return render_to_response('inschrijven.html', dict(split_date(date), **{'form': form, 'datehuman': datehuman, 'fixedrents': frs, 'reservations': rs, 'cancellable_states': cancellable_states}), context_instance=RequestContext(request))

@login_required
def add_exception(request, year, month, day):
	setlocale(LC_TIME, normalize('nl_NL'))
	return_url = reverse('month-view', kwargs={'year': year, 'month': month})

	if request.method != 'POST':
		messages.error(request, "Ongeldig verzoek voor zaal vrijgeven.")
		return HttpResponseRedirect(return_url)
	fr = FixedRent.objects.get(id=request.POST['fixedrent'])
	if not request.user.vvsuser.can_moderate and fr.hirer not in request.user.vvsuser.cached_vvsgroups:
		raise PermissionDenied

	date = datetime.date(int(year), int(month), int(day))
	if FixedRentException.objects.filter(date=date, rental=fr).count() > 0:
		messages.error(request, "De zaal is al vrijgegeven op die datum.")
		return HttpResponseRedirect(return_url)

	fre = FixedRentException(date=date, rental=fr)
	fre.save()
	subj = "[Zaalrooster] %s op %s vrijgegeven" % (str(fr.room).capitalize(), date.strftime("%d %b"))
	msg = "De zaalhuur van de %s op %s (%s) is door %s vrijgegeven." % (fr.room, date.strftime("%d %B %Y"), fr.timeframe, fr.hirer)
	em = EmailMessage(subj, msg, to=settings.MODERATORS, cc=[request.user.email])
	em.send()
	messages.success(request, "Zaal vrijgegeven.")
	return HttpResponseRedirect(return_url)
