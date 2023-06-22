# Create your views here.
import base64
from io import BytesIO

import qrcode
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django_otp import user_has_device
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import Weather




def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            device = TOTPDevice.objects.create(user=user, name='default')

            # Tworzenie URL dla QR code
            totp_bin = device.bin_key
            totp_base32 = base64.b32encode(totp_bin).decode().strip("=")
            url = f'otpauth://totp/{user.username}?secret={totp_base32}&issuer=WeatherApp'

            # Tworzenie QR code
            qr = qrcode.make(url)
            qr_bytes = BytesIO()
            qr.save(qr_bytes)
            qr_b64 = base64.b64encode(qr_bytes.getvalue()).decode()

            # Przesyłanie QR code do szablonu
            return render(request, 'complete.html', {'qr_b64': qr_b64})

    else:
        form = UserCreationForm()

    return render(request, 'register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        totp_token = request.POST['totp']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user_has_device(user):
                device = user.totpdevice_set.first()
                if device.verify_token(totp_token):
                    login(request, user)
                    return redirect('dashboard')
                else:
                    messages.error(request, "Nieprawidłowy token TOTP")
            else:
                messages.error(request, "Użytkownik nie ma skonfigurowanego urządzenia TOTP")
        else:
            messages.error(request, "Nieprawidłowy użytkownik lub hasło")
        return redirect('login')
    else:
        return render(request, 'login.html')


def user_logout(request):
    logout(request)
    return redirect('index')


def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'index.html')


def complete(request):
    return render(request, 'complete.html')


@login_required
def dashboard(request):
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
        # Zapisz dane pogodowe w bazie danych
        Weather.objects.create(
            city=weather['city'],
            temperature=weather['temperature'],
            description=weather['description'],
            humidity=weather['humidity'],
            wind_speed=weather['wind_speed']
        )

    except KeyError:
        weather = None

     # Pobierz dane pogodowe
    weather_data = Weather.objects.filter(city=city).order_by('timestamp')

    # Przekształć dane do formatu zrozumiałego dla wykresu
    chart_data = {
        'labels': [data.timestamp.strftime('%Y-%m-%d %H:%M') for data in weather_data],
        'datasets': [{
            'label': 'Temperature',
            'data': [data.temperature for data in weather_data],
            'fill': False,
            'borderColor': 'rgb(75, 192, 192)',
            'tension': 0.1
        }]
    }

    context = {
        'weather': weather,
        'chart_data': chart_data
    }

    return render(request, 'dashboard.html', context)
