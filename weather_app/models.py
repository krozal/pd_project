# Create your models here.
from django.db import models

class Weather(models.Model):
    city = models.CharField(max_length=200)
    temperature = models.FloatField()
    description = models.CharField(max_length=200)
    humidity = models.IntegerField()
    wind_speed = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
