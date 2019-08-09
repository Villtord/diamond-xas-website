from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import django
from django.conf import settings

import xdifile
import tempfile
import os.path
from os.path import exists
import xraylib as xrl
from habanero import Crossref
import imghdr

from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
import sys


XDI_TMP_DIR = tempfile.TemporaryDirectory()

def doi_valid(value):
    try:
        cr = Crossref(mailto = "Tom.Schoonjans@diamond.ac.uk") # necessary to end up in the polite pool
        work = cr.works(ids=value)
        work['message']['title']
    except Exception as e:
        raise ValidationError(f"Invalid DOI: {e}")

def file_size_valid(value):
    limit = 10 * 1024 * 1024 # 10 MB
    if value.size > limit:
        raise ValidationError('File size is limited to 10 MB!')

def mendeljev_valid(value):
    try:
        atomic_number = xrl.SymbolToAtomicNumber(value)
        if atomic_number == 0:
            raise Exception()
    except Exception:
        raise ValidationError(f"Unknown chemical element {value}")

def xdi_valid(value):
    temp_xdi_file = os.path.join(XDI_TMP_DIR.name, value.name)

    try:
        with open(temp_xdi_file, 'w') as f:
            f.write(value.read().decode('utf-8'))

        xdi_file = xdifile.XDIFile(filename=temp_xdi_file)
        if xdi_file.element.decode('utf-8') == '':
            raise Exception('no element found')
        return
    except Exception as e:
        raise ValidationError(f"Invalid XDI file: {e}")


class XASFile(models.Model):
    PENDING = 0
    APPROVED = 1
    REJECTED = 2
    REVIEW_STATUS_CHOICES = ((PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected"))

    EDGE_CHOICES = ((xrl.K_SHELL, "K"), (xrl.L1_SHELL, "L1"), (xrl.L2_SHELL, "L2"), (xrl.L3_SHELL, "L3"))

    upload_file = models.FileField(upload_to='uploads/%Y/%m/%d/', validators=[file_size_valid, xdi_valid])
    upload_file_doi = models.CharField('Citation DOI', max_length=256, default='', validators=[doi_valid])
    upload_timestamp = models.DateTimeField('date published', auto_now_add=True)
    element = models.CharField(max_length=3, validators=[mendeljev_valid])
    edge = models.SmallIntegerField(choices=EDGE_CHOICES, default=xrl.K_SHELL)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    review_status = models.SmallIntegerField(choices=REVIEW_STATUS_CHOICES, default=PENDING)
    sample_name = models.CharField(max_length=100, default='unknown')
    sample_prep = models.CharField(max_length=1000, default='unknown')
    beamline_name = models.CharField(max_length=100, default='unknown')
    facility_name = models.CharField(max_length=100, default='unknown')
    mono_name = models.CharField(max_length=30, default='unknown')
    mono_d_spacing = models.CharField(max_length=30, default='unknown')
    scan_start_time = models.DateTimeField(default=django.utils.timezone.now)
    refer_used = models.BooleanField(default=False)

    @property
    def name(self):
        return os.path.basename(self.upload_file.name)

class XASArray(models.Model):
    file = models.ForeignKey(XASFile, on_delete=models.CASCADE)
    array = models.TextField() # this will be a numpy array turned into JSON...
    unit = models.CharField(max_length=20)
    name = models.CharField(max_length=50)

class XASMode(models.Model):
    UNKNOWN = -1
    TRANSMISSION= 0
    FLUORESCENCE = 1
    FLUORESCENCE_UNITSTEP = 2
    XMU = 3
    MODE_CHOICES = ((UNKNOWN, "Unknown"), (TRANSMISSION, "Transmission"), (FLUORESCENCE, "Fluorescence"), (FLUORESCENCE_UNITSTEP, "Fluorescence, unitstep"), (XMU, "Normalized absorption spectrum"))

    file = models.ForeignKey(XASFile, on_delete=models.CASCADE)
    mode = models.SmallIntegerField(choices=MODE_CHOICES, default=UNKNOWN)

class XASUploadAuxData(models.Model):
    aux_description = models.CharField('Description', max_length=256, default='')
    aux_file = models.FileField(upload_to='uploads/%Y/%m/%d/', validators=[file_size_valid])
    aux_thumbnail_file = models.ImageField(upload_to='uploads/%Y/%m/%d/', blank=True)
    file = models.ForeignKey(XASFile, on_delete=models.CASCADE)

    @property
    def name(self):
        return os.path.basename(self.aux_file.name)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if imghdr.what(self.aux_file.path) is not None:
            make_thumbnail(self.aux_thumbnail_file, self.aux_file, (150, 150), 'thumb')
            try:
                super().save(update_fields=['aux_thumbnail_file'])
            except Exception as e:
                print("save exception: {}".format(e))
                raise



class XASDownloadFile(models.Model):
    #ip_address = models.GenericIPAddressField()
    download_timestamp = models.DateTimeField('date downloaded', auto_now_add=True)
    downloader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file = models.ForeignKey(XASFile, on_delete=models.CASCADE)
    
class XASDownloadAuxData(models.Model):
    #ip_address = models.GenericIPAddressField()
    download_timestamp = models.DateTimeField('date downloaded', auto_now_add=True)
    downloader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    file = models.ForeignKey(XASUploadAuxData, on_delete=models.CASCADE)
    

# based on https://stackoverflow.com/a/56304444/1253230
def make_thumbnail(dst_image_field, src_image_field, size, name_suffix, sep='_'):
    """
    make thumbnail image and field from source image field

    @example
        thumbnail(self.thumbnail, self.image, (200, 200), 'thumb')
    """
    # create thumbnail image
    image = Image.open(src_image_field)
    image.thumbnail(size)

    # build file name for dst
    dst_path, dst_ext = os.path.splitext(src_image_field.name)
    dst_ext = dst_ext.lower()
    dst_fname = dst_path + sep + name_suffix + dst_ext

    # check extension
    filetype = imghdr.what(src_image_field.path).upper()

    # Save thumbnail to in-memory file as StringIO
    dst_bytes = BytesIO()
    image.save(dst_bytes, filetype)
    dst_bytes.seek(0)

    # set save=False, otherwise it will run in an infinite loop
    dst_image_field.save(dst_fname, ContentFile(dst_bytes.read()), save=False)
    dst_bytes.close()
