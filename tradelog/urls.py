from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/sync-trade/', views.api_sync_trade, name='api_sync_trade'),
    path('signup/', views.signup, name='signup'),
    path('api/journal/create/', views.create_journal_entry, name='create_journal_entry'),
    path('extract-trade/', views.extract_trade_details, name='extract_trade'),
    path('currency-converter/', views.currency_converter_view, name='currency_converter'),
]