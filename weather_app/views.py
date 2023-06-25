# Create your views here.
import base64
from io import BytesIO
import os
from django.views.decorators.http import require_http_methods, require_POST, require_GET

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
from datetime import timedelta



def register(request):
    """
    Rejestracja nowego użytkownika i generowanie dla niego kodu QR do uwierzytelniania dwuetapowego.

    Parametry
    ----------
    request : WSGIRequest
        Obiekt żądania Django zawierający informacje o żądaniu HTTP.

    Zwraca
    -------
    HttpResponse
        Renderowany szablon HTML dla strony końcowej rejestracji (complete.html) lub strony rejestracji (register.html).

    Przebieg
    --------
    1. Sprawdzenie, czy metoda żądania to POST.
    2. Jeżeli tak, próba utworzenia nowego użytkownika za pomocą danych z formularza. 
       Jeżeli formularz jest prawidłowy, użytkownik jest zapisywany, a dla niego tworzone jest urządzenie TOTP.
    3. Generowanie URL dla kodu QR na podstawie klucza urządzenia TOTP i nazwy użytkownika.
    4. Tworzenie kodu QR na podstawie wygenerowanego URL.
    5. Renderowanie i zwracanie strony końcowej rejestracji z wygenerowanym kodem QR.
    6. Jeżeli metoda żądania to nie POST, inicjalizacja pustego formularza UserCreationForm.
    7. Renderowanie i zwracanie strony rejestracji z formularzem.

    Wyjątki
    ----------
    Możliwe wyjątki zgłaszane przez Django podczas próby zapisania użytkownika lub urządzenia TOTP są obsługiwane przez Django.
    """
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            device = TOTPDevice.objects.create(user=user, name="default")

            # tworzenie URL dla QR code
            totp_bin = device.bin_key
            totp_base32 = base64.b32encode(totp_bin).decode().strip("=")
            url = (
                f"otpauth://totp/{user.username}?secret={totp_base32}&issuer=WeatherApp"
            )

            # tworzenie QR code
            qr = qrcode.make(url)
            qr_bytes = BytesIO()
            qr.save(qr_bytes)
            qr_b64 = base64.b64encode(qr_bytes.getvalue()).decode()

            return render(request, "complete.html", {"qr_b64": qr_b64})

    else:
        form = UserCreationForm()

    return render(request, "register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def user_login(request):
    """
    Logowanie użytkownika poprzez sprawdzenie hasła i kodu TOTP.

    Parametry
    ----------
    request : WSGIRequest
        Obiekt żądania Django zawierający informacje o żądaniu HTTP.

    Zwraca
    -------
    HttpResponse
        Renderowany szablon HTML dla strony logowania (login.html) lub przekierowanie do pulpit nawigacyjnego.

    Przebieg
    --------
    1. Sprawdzenie, czy metoda żądania to POST.
    2. Jeżeli tak, pobranie nazwy użytkownika, hasła i tokena TOTP z żądania.
    3. Próba uwierzytelnienia użytkownika na podstawie podanego hasła i nazwy użytkownika.
    4. Jeżeli uwierzytelnienie jest udane, sprawdzenie, czy użytkownik ma skonfigurowane urządzenie TOTP.
    5. Jeżeli tak, próba weryfikacji podanego tokena TOTP. Jeżeli weryfikacja jest udana, logowanie użytkownika i przekierowanie na pulpit nawigacyjny.
    6. Jeżeli weryfikacja nie jest udana lub użytkownik nie ma skonfigurowanego urządzenia TOTP, wyświetlenie odpowiedniego komunikatu o błędzie.
    7. Jeżeli uwierzytelnienie nie jest udane, wyświetlenie komunikatu o błędzie i przekierowanie na stronę logowania.
    8. Jeżeli metoda żądania to nie POST, renderowanie i zwracanie strony logowania.

    Wyjątki
    ----------
    Możliwe wyjątki zgłaszane przez Django podczas próby uwierzytelnienia użytkownika lub weryfikacji tokena TOTP są obsługiwane przez Django.
    """
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        totp_token = request.POST["totp"]

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user_has_device(user):
                device = user.totpdevice_set.first()
                if device.verify_token(totp_token):
                    login(request, user)
                    return redirect("dashboard")
                else:
                    messages.error(request, "Nieprawidłowy token TOTP")
            else:
                messages.error(
                    request, "Użytkownik nie ma skonfigurowanego urządzenia TOTP"
                )
        else:
            messages.error(request, "Nieprawidłowy użytkownik lub hasło")
        return redirect("login")
    else:
        return render(request, "login.html")


@require_GET
def user_logout(request):
    """
    Wylogowywanie użytkownika i przekierowanie do strony głównej.

    Argumenty:
        request : WSGIRequest
            Obiekt żądania Django zawierający informacje o żądaniu HTTP.

    Zwraca:
        HttpResponseRedirect
            Przekierowanie do strony głównej.
    """
    logout(request)
    return redirect("index")


@require_GET
def index(request):
    """
    Widok strony głównej.

    Argumenty:
        request : WSGIRequest
            Obiekt żądania Django zawierający informacje o żądaniu HTTP.

    Zwraca:
        HttpResponse
            Renderowany szablon HTML dla strony głównej lub przekierowanie do pulpitu nawigacyjnego.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "index.html")


@require_GET
def complete(request):
    """
    Widok strony końcowej rejestracji zawieracjący kod QR do zeskanowania przez użytkownika

    Argumenty:
        request : WSGIRequest
            Obiekt żądania Django zawierający informacje o żądaniu HTTP.

    Zwraca:
        HttpResponse
            Renderowany szablon HTML dla strony końcowej rejestracji.
    """
    return render(request, "complete.html")


@login_required
@require_GET
def dashboard(request):
    """
    Widok Django, który pobiera dane o pogodzie dla określonego miasta z API OpenWeatherMap, zapisuje je w bazie danych
    i zwraca HttpResponse z wyrenderowanym szablonem HTML z danymi o pogodzie. Jeżeli miasto nie jest określone, 
    domyślnie ustawione jest na "Kielce".

    Parametry
    ----------
    request : WSGIRequest
        Obiekt żądania Django zawierający informacje o żądaniu HTTP.

    Zwraca
    -------
    HttpResponse
        Wyrenderowany szablon HTML dla pulpitu nawigacyjnego z danymi o pogodzie.

    Przebieg
    --------
    1. Pobranie klucza API OpenWeatherMap i miasta z żądania HTTP. Jeżeli miasto nie jest określone, domyślnie jest ustawione na "Kielce".
    2. Wysłanie żądania GET do API OpenWeatherMap, aby pobrać dane o pogodzie dla określonego miasta.
    3. Próba parsowania odpowiedzi JSON z API, a następnie zapisanie tych danych do modelu Weather w bazie danych.
       Jeżeli odpowiedź nie zawiera niezbędnych danych, zmiennej `weather` przypisywana jest wartość None.
    4. Pobranie wszystkich obiektów Weather z bazy danych dla określonego miasta i posortowanie ich według daty (timestamp).
    5. Przygotowanie danych do wykresu temperatury dla danego miasta na podstawie danych z bazy danych.
    6. Przygotowanie kontekstu, który będzie przekazywany do szablonu HTML.
    7. Renderowanie i zwracanie szablonu HTML `dashboard.html` z przekazanym kontekstem.

    Wyjątki
    ----------
    Obsługuje wyjątek KeyError, który może wystąpić, jeżeli odpowiedź z API OpenWeatherMap nie zawiera potrzebnych danych.

    """
    api_key = settings.OPENWEATHERMAP_API_KEY
    city = request.GET.get("city", "Kielce")

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric", "lang": "pl"}

    response = requests.get(url, params=params).json()

    try:
        weather = {
            "city": response["name"],
            "temperature": response["main"]["temp"],
            "description": response["weather"][0]["description"],
            "humidity": response["main"]["humidity"],
            "wind_speed": response["wind"]["speed"],
        }

        Weather.objects.create(
            city=weather["city"],
            temperature=weather["temperature"],
            description=weather["description"],
            humidity=weather["humidity"],
            wind_speed=weather["wind_speed"],
        )

    except KeyError:
        weather = None

    weather_data = Weather.objects.filter(city=city).order_by("timestamp")

    chart_data = {
        "labels": [
            (data.timestamp + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
            for data in weather_data
        ],
        "datasets": [
            {
                "label": "Temperature",
                "data": [data.temperature for data in weather_data],
                "fill": False,
                "borderColor": "rgb(75, 192, 192)",
                "tension": 0.1,
            }
        ],
    }

    context = {"weather": weather, "chart_data": chart_data}

    return render(request, "dashboard.html", context)
