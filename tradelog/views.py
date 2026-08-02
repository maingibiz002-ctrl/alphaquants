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
from django.conf import settings
from google import genai

# Services & Execution Engine
from funding_scanner import fetch_binance_funding_rates
from .services.nse_service import fetch_nse_market_data
from .execution_engine import RealTimeArbitrageExecutor

# Models
from .models import Crypto, UserProfile, TradeJournal, TradeChartImage


@login_required
def dashboard(request):
    """
    Renders the main dashboard combining user trade journals, 
    live funding rate arbitrage opportunities, and live position metrics.
    """
    user_trades = TradeJournal.objects.filter(user=request.user).order_by('-created_at')
    
    total_trades = user_trades.count()
    total_pl = user_trades.aggregate(Sum('pnl'))['pnl__sum'] or 0.00
    wins = user_trades.filter(pnl__gt=0).count()
    win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0

    api_token = getattr(getattr(request.user, 'profile', None), 'api_token', '')

    # Fetch live funding rate arbitrage opportunities safely
    try:
        arbitrage_opportunities = fetch_binance_funding_rates()
    except Exception as e:
        arbitrage_opportunities = []
        print(f"Error fetching funding rates: {e}")

    # Fetch initial position metrics for the dashboard template render
    try:
        executor = RealTimeArbitrageExecutor()
        position_metrics = executor.get_position_metrics()
    except Exception:
        position_metrics = {
            "status": "INACTIVE",
            "spot_holdings": 0.0,
            "futures_size": 0.0,
            "unrealized_pnl": 0.0,
            "margin": 0.0
        }

    context = {
        'trades': user_trades,
        'total_trades': total_trades,
        'total_pl': total_pl,
        'win_rate': win_rate,
        'api_token': api_token,
        'arbitrage_opportunities': arbitrage_opportunities,
        'position_metrics': position_metrics,
        'executed_trades': [],  # Populate from database or active logs if tracked via ORM
    }
    return render(request, 'tradelog/dashboard.html', context)


@login_required
def arbitrage_data_api(request):
    """
    Asynchronous JSON endpoint to feed the frontend dashboard 
    without blocking page load times.
    """
    try:
        executor = RealTimeArbitrageExecutor()
        
        # Scan opportunities safely
        try:
            _, opportunities = executor.scan_opportunities()
        except Exception as scan_err:
            print(f"Scan opportunities error: {scan_err}")
            opportunities = []
        
        # Fetch live position metrics safely
        try:
            position_metrics = executor.get_position_metrics()
        except Exception as metrics_err:
            print(f"Position metrics error: {metrics_err}")
            position_metrics = {
                "status": "INACTIVE",
                "spot_holdings": 0.0,
                "futures_size": 0.0,
                "unrealized_pnl": 0.0,
                "margin": 0.0
            }
        
        data = {
            "position_metrics": position_metrics,
            "arbitrage_opportunities": opportunities,
            "executed_trades": []
        }
        return JsonResponse(data)
    except Exception as e:
        import traceback
        traceback.print_exc()  # This will print the full traceback in your runserver terminal
        return JsonResponse({"error": str(e)}, status=500)
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


def crypto_screener_view(request):
    all_cryptos = fetch_binance_funding_rates() # Or custom market data fetcher

    category_filter = request.GET.get('category', 'ALL')
    performance_filter = request.GET.get('performance', 'ALL')
    min_turnover = request.GET.get('min_turnover', '')
    max_funding_rate = request.GET.get('max_funding_rate', '')

    filtered_cryptos = []
    min_vol = float(min_turnover) if min_turnover else 0.0
    max_funding = float(max_funding_rate) if max_funding_rate else 100.0

    for crypto in all_cryptos:
        if category_filter != 'ALL' and crypto.get('category') != category_filter:
            continue
        if performance_filter == 'GAINERS' and crypto.get('change_pct', 0) <= 0:
            continue
        if performance_filter == 'LOSERS' and crypto.get('change_pct', 0) >= 0:
            continue
        if crypto.get('turnover_m', 0) < min_vol:
            continue
        if crypto.get('funding_rate', 0) > max_funding:
            continue

        filtered_cryptos.append(crypto)

    context = {
        'cryptos': filtered_cryptos,
        'category_filter': category_filter,
        'performance_filter': performance_filter,
        'min_turnover': min_turnover,
        'max_funding_rate': max_funding_rate,
        'total_count': len(filtered_cryptos)
    }

    return render(request, 'tradelog/crypto_screener.html', context)


def ask_crypto_ai(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        user_prompt = data.get('prompt', '').strip()

        if not user_prompt:
            return JsonResponse({'status': 'error', 'message': 'Prompt cannot be empty.'}, status=400)

        cryptos = Crypto.objects.all()
        crypto_summary = [
            f"Symbol: {c.symbol}, Pair: {c.base_asset}/{c.quote_asset}, Category: {c.category}, "
            f"Mark Price: USDT {c.mark_price}, 24h Change: {c.change_pct}%, "
            f"Funding Rate: {c.funding_rate}%, Open Interest: {c.open_interest}, "
            f"24h Turnover: ${c.turnover}, Signal: {c.signal}"
            for c in cryptos
        ]
        context_str = "\n".join(crypto_summary)

        system_instruction = (
            "You are an expert quantitative crypto analyst and derivatives trading advisor. "
            "Use the provided market data to answer the user's question concisely. "
            "Highlight specific pairs and quantitative metrics (Funding Rate, Open Interest, 24h Turnover, Signals). "
            "Format your response with minimal, clean HTML tags like <strong> and <ul>.\n\n"
            f"CURRENT CRYPTO MARKET DATA:\n{context_str}\n\n"
            f"USER QUESTION: {user_prompt}"
        )

        client = genai.Client(api_key=getattr(settings, 'GEMINI_API_KEY', ''))
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=system_instruction,
        )

        return JsonResponse({
            'status': 'success',
            'response': response.text
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)