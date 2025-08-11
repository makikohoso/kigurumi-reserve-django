from django.db import models

class Reservation(models.Model):
    name = models.CharField(max_length=100)  # 名前を文字列で保存

    def __str__(self):
        return self.name
