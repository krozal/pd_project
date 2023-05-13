from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.views.generic.edit import FormView

from django.contrib.auth import login
from django.contrib.auth import logout
from django.shortcuts import redirect

from django.urls import reverse_lazy

from django.contrib.auth.decorators import login_required

from django.contrib.auth.forms import UserCreationForm

import requests
from django.conf import settings
from django.shortcuts import render

# Create your views here.
def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')

class CustomLoginView(LoginView):
    template_name = 'login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

def my_logout_view(request):
    logout(request)
    return redirect('login')

class RegisterPage(FormView):
    template_name = 'registration.html'
    form_class = UserCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('login')
    def form_valid(self, form):
        form.save()
        user = form.instance
        login(self.request, user)
        return super().form_valid(form)
    
@login_required
def weather_view(request):
    api_key = settings.OPENWEATHERMAP_API_KEY
    city = request.GET.get('city', 'Kielce')
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=pl'

    response = requests.get(url).json()

    try:
        weather = {
            'city': response['name'],
            'temperature': response['main']['temp'],
            'description': response['weather'][0]['description'],
            'humidity': response['main']['humidity'],
            'wind_speed': response['wind']['speed']
        }
    except KeyError:
        weather = None

    context = {
        'weather': weather
    }

    return render(request, 'dashboard.html', context)
