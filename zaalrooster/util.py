from vvs.zaalrooster.models import FixedRent, FixedRentException, Reservation

def room_is_free_at(room, date):
	frs = set(FixedRent.objects.filter(begin__lte=date, end__gte=date, weekday=date.isoweekday(), room=room))
	if len(frs) > 0:
		for fre in FixedRentException.objects.filter(date=date, rental__in=frs): # XXX __in testen
			frs.remove(fre.rental)
		if len(frs) > 0:
			return False
	if Reservation.objects.filter(date=date, room=room).exclude(state__in=['denied', 'cancelled']).count() > 0:
		return False
	return True
