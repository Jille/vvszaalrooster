from django.forms import ModelForm, ModelChoiceField

from vvs.zaalrooster.models import *

def getReservationForm(user):
	can_moderate = user.vvsuser.can_moderate

	class ReservationForm(ModelForm):
		if not can_moderate:
			kwargs = {'label': "Huurder", 'queryset': VvSGroup.objects.filter(user=user)}
			if len(user.vvsuser.cached_vvsgroups) == 1:
				kwargs['empty_label'] = None
			hirer = ModelChoiceField(**kwargs)

		class Meta:
			model = Reservation
			fields = ['hirer', 'room', 'name', 'timeframe']
			if can_moderate:
				fields.append('state')
	return ReservationForm
