from django.urls import path
from .views import *

urlpatterns = [
    path('start/', choice, name='start'),
    path('',home, name='home'),
    path('ts/', voice_bot, name='process_voice'),
    path('voice/', voice_bot_view, name='voice'),
    path('select_language/', select_language, name='select_language'),

]
