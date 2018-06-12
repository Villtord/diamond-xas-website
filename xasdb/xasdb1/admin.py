from django.contrib import admin

from .models import XASFile, XASArray

@admin.register(XASFile)
class XASFileAdmin(admin.ModelAdmin):
    readonly_fields = ('upload_file', 'upload_timestamp', 'atomic_number', 'element', 'edge', 'uploader')

@admin.register(XASArray)
class XASArrayAdmin(admin.ModelAdmin):
    fields = ('file', 'name', 'unit')
    readonly_fields = fields

