from django.contrib import admin
from django.urls import include, path

urlpatterns = [path('admin/', admin.site.urls), path('api/', include('workspace.api_urls')), path('', include('workspace.urls'))]
