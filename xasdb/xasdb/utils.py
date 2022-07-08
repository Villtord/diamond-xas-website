from django.contrib.staticfiles import storage

class XASDBStaticFilesStorage(storage.StaticFilesStorage):
    def __init__(self, *args, **kwargs):
        kwargs['file_permissions_mode'] = 0o644
        kwargs['directory_permissions_mode'] = 0o755
        super().__init__(*args, **kwargs)


