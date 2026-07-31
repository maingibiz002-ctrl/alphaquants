from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
# REMOVED: from .models import Trade
from .models import TradeJournal, TradeChartImage

# 1. Custom User Admin View
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_journal_count', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    @admin.display(description='Total Trades Logged')
    def get_journal_count(self, obj):
        return obj.journal_entries.count()

# Re-register User model with custom settings
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# 2. Trade Journal Admin
@admin.register(TradeJournal)
class TradeJournalAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'direction', 'entry_price', 'exit_price', 'pnl', 'risk_reward_ratio', 'created_at')
    list_filter = ('direction', 'instrument', 'strategy_tag', 'created_at')
    search_fields = ('instrument', 'notes', 'user__username')
    readonly_fields = ('created_at', 'risk_reward_ratio', 'ai_feedback_summary')


# 3. Chart Images Admin
@admin.register(TradeChartImage)
class TradeChartImageAdmin(admin.ModelAdmin):
    list_display = ('journal_entry', 'uploaded_at')
    list_filter = ('uploaded_at',)