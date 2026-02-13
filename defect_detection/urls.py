from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from .api import BatchViewSet, InspectionViewSet, DefectViewSet

router = DefaultRouter()
router.register(r'batches', BatchViewSet)
router.register(r'inspections', InspectionViewSet)
router.register(r'defects', DefectViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('accounts/', include('accounts.urls')),
    path('', include('core_inventory.urls')),
    path('', include('core_dashboard.urls')),
    path('inspections/', include('inspections.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
