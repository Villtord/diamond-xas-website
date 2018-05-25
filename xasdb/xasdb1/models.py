from django.db import models

class XASFile(models.Model):
    upload_file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    upload_timestamp = models.DateTimeField('date published', auto_now_add=True)
