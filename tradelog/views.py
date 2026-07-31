import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.models import User

from .models import UserProfile, TradeJournal, TradeChartImage


@login_required
def dashboard(request):
    """
    Renders the main dashboard with statistics built from TradeJournal entries.
    """
    user_trades = TradeJournal.objects.filter(user=request.user).order_by('-created_at')
    
    total_trades = user_trades.count()
    total_pl = user_trades.aggregate(Sum('pnl'))['pnl__sum'] or 0.00
    wins = user_trades.filter(pnl__gt=0).count()
    win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0

    api_token = getattr(getattr(request.user, 'profile', None), 'api_token', '')

    context = {
        'trades': user_trades,
        'total_trades': total_trades,
        'total_pl': total_pl,
        'win_rate': win_rate,
        'api_token': api_token,
    }
    return render(request, 'tadelog/dashboard.html', context)


@login_required
def create_journal_entry(request):
    """
    Handles form submissions for new manual trade logs with images.
    """
    if request.method == 'POST':
        instrument = request.POST.get('instrument')
        direction = request.POST.get('direction')
        entry_price = float(request.POST.get('entry_price', 0))
        exit_price = float(request.POST.get('exit_price', 0))
        stop_loss = float(request.POST.get('stop_loss', 0)) if request.POST.get('stop_loss') else None
        take_profit = float(request.POST.get('take_profit', 0)) if request.POST.get('take_profit') else None
        lot_size = float(request.POST.get('lot_size', 0))
        pnl = float(request.POST.get('pnl', 0))
        strategy_tag = request.POST.get('strategy_tag')
        notes = request.POST.get('notes')

        rr_ratio = 0.0
        if stop_loss and entry_price != stop_loss:
            risk = abs(entry_price - stop_loss)
            reward = abs(exit_price - entry_price)
            rr_ratio = round(reward / risk, 2) if risk > 0 else 0.0

        discipline_score = 90 if pnl > 0 else 75
        ai_summary = f"Executed {direction} on {instrument}. "
        if rr_ratio >= 2.0:
            ai_summary += f"Excellent Risk-to-Reward ratio of 1:{rr_ratio}. Rule compliance verified."
        else:
            ai_summary += f"Risk-to-Reward ratio was 1:{rr_ratio}. Consider aiming for minimum 1:2 setups."

        entry = TradeJournal.objects.create(
            user=request.user,
            instrument=instrument,
            direction=direction,
            entry_price=entry_price,
            exit_price=exit_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lot_size=lot_size,
            pnl=pnl,
            strategy_tag=strategy_tag,
            notes=notes,
            risk_reward_ratio=rr_ratio,
            ai_feedback_summary=ai_summary,
            discipline_score=discipline_score
        )

        for image_file in request.FILES.getlist('chart_images'):
            TradeChartImage.objects.create(journal_entry=entry, image=image_file)

        messages.success(request, 'Trade logged successfully!')
        return redirect('dashboard')
    
    return redirect('dashboard')


def signup(request):
    """
    Handles registration for new traders.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created! Welcome to Alpha Terminal, {user.username}.")
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})


def currency_converter_view(request):
    """
    Renders the Currency Converter resource page.
    """
    return render(request, 'tradelog/currency_converter.html')