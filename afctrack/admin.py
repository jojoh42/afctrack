"""Admin models"""

# Third Party
from solo.admin import SingletonModelAdmin  # type: ignore

# Django
from django.contrib import admin  # noqa: F401
from .models import AfcTrackSettings

admin.site.register(AfcTrackSettings, SingletonModelAdmin)

# Register your models here.
