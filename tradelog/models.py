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