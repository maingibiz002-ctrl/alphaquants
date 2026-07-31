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
from django.shortcuts import render
from .models import Stock
import json
from django.http import JsonResponse
from django.conf import settings
from google import genai
from .models import Stock

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
    return render(request, 'tradelog/dashboard.html', context)


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

from django.shortcuts import render
from .services.nse_service import fetch_nse_market_data





def nse_screener_view(request):
    all_stocks = fetch_nse_market_data()

    # Get search/filter inputs from GET request
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    performance_filter = request.GET.get('performance', 'ALL')

    filtered_stocks = []

    min_p = float(min_price) if min_price else 0.0
    max_p = float(max_price) if max_price else 1000000.0

    for stock in all_stocks:
        if min_p <= stock['price'] <= max_p:
            if performance_filter == 'GAINERS' and stock['change'] <= 0:
                continue
            if performance_filter == 'LOSERS' and stock['change'] >= 0:
                continue
            filtered_stocks.append(stock)

    context = {
        'stocks': filtered_stocks,
        'min_price': min_price,
        'max_price': max_price,
        'performance_filter': performance_filter,
        'total_count': len(filtered_stocks)
    }
    return render(request, 'tradelog/stock_screener.html', context)



def dashboard_view(request):
    # Retrieve all stocks from the database
    stocks = Stock.objects.all()

    # Optional server-side filtering via GET parameters (e.g. /dashboard/?sector=Banking)
    sector_filter = request.GET.get('sector')
    if sector_filter and sector_filter != 'ALL':
        stocks = stocks.filter(sector=sector_filter)

    max_pe = request.GET.get('pe')
    if max_pe:
        stocks = stocks.filter(pe_ratio__lte=float(max_pe))

    min_div = request.GET.get('div')
    if min_div:
        stocks = stocks.filter(div_yield__gte=float(min_div))

    context = {
        'stocks': stocks,
    }

    return render(request, 'tradelog/dashboard.html', context)





def ask_stock_ai(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        user_prompt = data.get('prompt', '').strip()

        if not user_prompt:
            return JsonResponse({'status': 'error', 'message': 'Prompt cannot be empty.'}, status=400)

        # 1. Fetch current stock context from your database
        stocks = Stock.objects.all()
        stock_summary = [
            f"Ticker: {s.ticker}, Company: {s.company_name}, Sector: {s.sector}, "
            f"Price: KES {s.price}, 24h Change: {s.change_pct}%, P/E: {s.pe_ratio or 'N/A'}, "
            f"Div Yield: {s.div_yield}%, Signal: {s.signal}"
            for s in stocks
        ]
        context_str = "\n".join(stock_summary)

        # 2. Build system instructions and combined prompt
        system_instruction = (
            "You are an expert quantitative analyst and stock market advisor. "
            "Use the provided stock data to answer the user's question concisely. "
            "Highlight specific tickers and metrics (P/E, Dividend Yield). "
            "Format your response with minimal, clean HTML tags like <strong> and <ul>.\n\n"
            f"CURRENT MARKET DATA:\n{context_str}\n\n"
            f"USER QUESTION: {user_prompt}"
        )

        # 3. Call the Gemini API
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