from django.contrib import admin

from .models import XASFile

class XASFileAdmin(admin.ModelAdmin):
    readonly_fields = ('upload_file', 'upload_timestamp', 'atomic_number')

admin.site.register(XASFile, XASFileAdmin)
