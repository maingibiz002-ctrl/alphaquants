from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('api/journal/create/', views.create_journal_entry, name='create_journal_entry'),
    path('currency-converter/', views.currency_converter_view, name='currency_converter'),
    path('screener/', views.crypto_screener_view, name='crypto_screener'),
    path('api/ask-crypto-ai/', views.ask_crypto_ai, name='ask_crypto_ai'),
    path('api/arbitrage-data/', views.arbitrage_data_api, name='arbitrage_data_api'),
    
]