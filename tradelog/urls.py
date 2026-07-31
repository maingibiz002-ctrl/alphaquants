from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('signup/', views.signup, name='signup'),
    path('api/journal/create/', views.create_journal_entry, name='create_journal_entry'),
    path('currency-converter/', views.currency_converter_view, name='currency_converter'),
    path('screener/', views.nse_screener_view, name='stock_screener'),
    path('api/ask-stock-ai/', views.ask_stock_ai, name='ask_stock_ai'),
    
]