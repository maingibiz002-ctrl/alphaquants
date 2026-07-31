from django.db import models
import uuid
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.
# tradelog/models.py



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    api_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def __str__(self):
        return f"{self.user.username}'s Alpha Quant Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


#journalling 
class TradeJournal(models.Model):
    DIRECTION_CHOICES = [
        ('BUY', 'Buy / Long'),
        ('SELL', 'Sell / Short'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journal_entries')
    instrument = models.CharField(max_length=20)  # e.g., EURUSD, XAUUSD, BTCUSD
    direction = models.CharField(max_length=4, choices=DIRECTION_CHOICES)
    entry_price = models.DecimalField(max_digits=12, decimal_places=5)
    exit_price = models.DecimalField(max_digits=12, decimal_places=5)
    stop_loss = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)
    lot_size = models.DecimalField(max_digits=8, decimal_places=2)
    pnl = models.DecimalField(max_digits=10, decimal_places=2)
    strategy_tag = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # AI Feedback Output Fields
    risk_reward_ratio = models.FloatField(null=True, blank=True)
    ai_feedback_summary = models.TextField(null=True, blank=True)
    discipline_score = models.IntegerField(default=100)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.instrument} ({self.direction}) - ${self.pnl}"


class TradeChartImage(models.Model):
    journal_entry = models.ForeignKey(TradeJournal, on_delete=models.CASCADE, related_name='chart_images')
    image = models.ImageField(upload_to='trade_charts/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

from django.db import models

class Crypto(models.Model):
    CATEGORY_CHOICES = [
        ('Linear Perpetual', 'USDT Perpetual'),
        ('USDC Perpetual', 'USDC Perpetual'),
        ('Inverse Perpetual', 'Inverse Perpetual'),
        ('Spot', 'Spot Trading'),
    ]

    SIGNAL_CHOICES = [
        ('BULLISH', 'BUY'),
        ('BEARISH', 'SELL'),
        ('NEUTRAL', 'HOLD'),
    ]

    symbol = models.CharField(max_length=20, unique=True, help_text="e.g. BTCUSDT")
    base_asset = models.CharField(max_length=10, help_text="e.g. BTC")
    quote_asset = models.CharField(max_length=10, default='USDT', help_text="e.g. USDT")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='Linear Perpetual')
    mark_price = models.DecimalField(max_digits=16, decimal_places=4)
    change_pct = models.FloatField(help_text="24-hour percentage change")
    funding_rate = models.FloatField(default=0.0, help_text="8-hour funding rate percentage (e.g. 0.0100)")
    open_interest = models.CharField(max_length=30, help_text="e.g. 12.4K BTC")
    turnover = models.CharField(max_length=30, help_text="24h volume/turnover formatted e.g. 4.5B")
    turnover_m = models.FloatField(default=0.0, help_text="Raw 24h turnover in Millions USD for filtering")
    signal = models.CharField(max_length=10, choices=SIGNAL_CHOICES, default='NEUTRAL')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']
        verbose_name = "Crypto Asset"
        verbose_name_plural = "Crypto Assets"

    def __str__(self):
        return f"{self.symbol} ({self.category})"