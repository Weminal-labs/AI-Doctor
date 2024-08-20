# chatbot/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('execute_steps/', views.execute_steps, name='execute_steps'),  # Thêm đường dẫn này
]