from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

import xdifile
import tempfile


def xdi_valid(value):
    print('Entering xdi_valid')
    print('xdi_value name: {}'.format(value.name))
    print('xdi_value url: {}'.format(value.url))
    
    with tempfile.NamedTemporaryFile() as f:
        #value.open()
        f.write(value.read())
        #value.close()
        try:
            xdi_file = xdifile.XDIFile(filename=f.name)
            print('element: {}'.format(xdi_file.element))
            print('edge: {}'.format(xdi_file.edge))
            return
        except Exception as e:
            print("XDI exception: {}".format(e))


    raise ValidationError("Invalid file!")

class XASFile(models.Model):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2
    REVIEW_STATUS_CHOICES = ((PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected"))


    upload_file = models.FileField(upload_to='uploads/%Y/%m/%d/', validators=[xdi_valid])
    upload_timestamp = models.DateTimeField('date published', auto_now_add=True)
    atomic_number = models.IntegerField(default=0)
    element = models.CharField(max_length=3, default='')
    edge = models.CharField(max_length=3, default='')
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    review_status = models.SmallIntegerField(choices=REVIEW_STATUS_CHOICES, default=PENDING)
    sample_name = models.CharField(max_length=100, default='unknown')

class XASArray(models.Model):
    file = models.ForeignKey(XASFile, on_delete=models.CASCADE)
    array = models.TextField() # this will be a numpy array turned into JSON...
    unit = models.CharField(max_length=20)
    name = models.CharField(max_length=50, primary_key=True)
