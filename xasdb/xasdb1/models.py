from django.db import models
from django.core.exceptions import ValidationError

import xdifile
import tempfile


def xdi_valid(value):
    print('Entering xdi_valid')
    print('xdi_value input: {}'.format(value))
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
    upload_file = models.FileField(upload_to='uploads/%Y/%m/%d/', validators=[xdi_valid])
    upload_timestamp = models.DateTimeField('date published', auto_now_add=True)
    atomic_number = models.IntegerField(default=0)

