from django.test.client import RequestFactory
from django.contrib.auth.forms import AuthenticationForm

rf = RequestFactory()
req = rf.post('/login/', {'username':'noone','password':'x'})
form = AuthenticationForm(req, data={'username':'noone','password':'x'})
print('is_valid', form.is_valid())
print('errors', form.errors)
print('non_field_errors', form.non_field_errors())
