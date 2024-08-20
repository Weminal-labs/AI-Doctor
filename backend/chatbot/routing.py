# chatbot/routing.py

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/chatbot/', consumers.ChatbotConsumer.as_asgi()),
]
