# Create your models here.
from django.db import models

class Weather(models.Model):
    """
    Model reprezentujący warunki pogodowe dla określonego miasta.

    ...

    Pola
    -----
    city : CharField
        Nazwa miasta, dla którego są rejestrowane warunki pogodowe.
    temperature : FloatField
        Temperatura w stopniach Celsjusza.
    description : CharField
        Krótki opis warunków pogodowych.
    humidity : IntegerField
        Wilgotność wyrażona w procentach.
    wind_speed : FloatField
        Prędkość wiatru w m/s.
    timestamp : DateTimeField
        Czas, kiedy dane pogodowe zostały zarejestrowane.
    """
    city = models.CharField(max_length=200)
    temperature = models.FloatField()
    description = models.CharField(max_length=200)
    humidity = models.IntegerField()
    wind_speed = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
