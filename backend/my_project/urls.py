from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chatbot/', include('chatbot.urls')),
    path('', RedirectView.as_view(url='/chatbot/')),  # Chuyển hướng người dùng đến /chatbot/
]
