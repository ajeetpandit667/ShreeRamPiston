from django.contrib.auth.models import User
from django.test import Client

# ensure user exists without LoginProfile
User.objects.filter(username='noprofile').delete()
User.objects.create_user('noprofile','no@example.com','pass123')

c = Client()
r2 = c.post('/login/', {'username':'noprofile','password':'pass123'}, HTTP_HOST='127.0.0.1')
print('status', r2.status_code)
print('content:')
print(r2.content.decode('utf-8'))
