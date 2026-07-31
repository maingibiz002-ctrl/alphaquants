import re
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
import easyocr
import numpy as np
from PIL import Image
from django.views.decorators.csrf import csrf_exempt
from .models import TradeJournal
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
    return render(request, 'dashboard.html', context)


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

        
    # Flash a success message and redirect back to the dashboard UI
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
# Initialize reader once (English)
reader = easyocr.Reader(['en'], gpu=False)

# Initialize reader globally or inside the view
reader = easyocr.Reader(['en'], gpu=False)

@csrf_exempt
def extract_trade_details(request):
    if request.method == "POST" and request.FILES.get("screenshot"):
        try:
            image_file = request.FILES["screenshot"]
            img = Image.open(image_file)

            # Convert PIL image to numpy array for EasyOCR
            img_np = np.array(img)

            # Extract text array and join into single string
            results = reader.readtext(img_np, detail=0)
            raw_text = " ".join(results)

            # -------------------------------
            # REGEX PARSING RULES
            # -------------------------------
            symbol_match = re.search(
                r"\b([A-Z]{3}/?[A-Z]{3}|XAUUSD|BTCUSD|US30|NAS100)\b",
                raw_text,
                re.IGNORECASE,
            )
            direction_match = re.search(
                r"\b(BUY|SELL)\b", raw_text, re.IGNORECASE
            )
            lot_match = re.search(r"\b(\d+\.\d{2})\b", raw_text)

            all_numbers = re.findall(r"[-+]?\d*\.\d+|\d+", raw_text)
            floats = [float(n) for n in all_numbers if "." in n]

            extracted_data = {
                "instrument": (
                    symbol_match.group(1).upper() if symbol_match else "UNKNOWN"
                ),
                "direction": (
                    direction_match.group(1).upper()
                    if direction_match
                    else "BUY"
                ),
                "lot_size": (
                    float(lot_match.group(1))
                    if lot_match
                    else (floats[0] if len(floats) > 0 else 0.01)
                ),
                "entry_price": floats[1] if len(floats) > 1 else 0.0,
                "exit_price": (
                    floats[2] if len(floats) > 2 else 0.0
                ),  # Default or parsed exit price
                "stop_loss": floats[3] if len(floats) > 3 else None,
                "take_profit": floats[4] if len(floats) > 4 else None,
                "net_pnl": floats[-1] if len(floats) > 5 else 0.0,
            }

            # Handle unauthenticated user guard clause
            if not request.user.is_authenticated:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "User must be logged in to save trade entries.",
                    },
                    status=401,
                )

            # -------------------------------
            # SAVE TRADE TO DATABASE (TradeJournal)
            # -------------------------------
            new_trade = TradeJournal.objects.create(
                user=request.user,
                instrument=extracted_data["instrument"],
                direction=extracted_data["direction"],
                lot_size=extracted_data["lot_size"],  # Fixed field name
                entry_price=extracted_data["entry_price"],
                exit_price=extracted_data["exit_price"],  # Added required field
                stop_loss=extracted_data["stop_loss"],
                take_profit=extracted_data["take_profit"],
                pnl=extracted_data["net_pnl"],
            )

            # -------------------------------
            # CALCULATE UPDATED ANALYTICS
            # -------------------------------
            user_trades = TradeJournal.objects.filter(user=request.user)

            total_trades = user_trades.count()
            total_pnl = (
                user_trades.aggregate(Sum("pnl"))["pnl__sum"] or 0.0
            )
            winning_trades = user_trades.filter(pnl__gt=0).count()
            losing_trades = user_trades.filter(pnl__lt=0).count()
            win_rate = (
                round((winning_trades / total_trades) * 100, 1)
                if total_trades > 0
                else 0.0
            )

            analytics_data = {
                "total_trades": total_trades,
                "total_pnl": round(float(total_pnl), 2),
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
            }

            return JsonResponse(
                {
                    "status": "success",
                    "data": extracted_data,
                    "trade_id": new_trade.id,
                    "analytics": analytics_data,
                }
            )

        except Exception as e:
            print("OCR Processing Error:", str(e))
            return JsonResponse(
                {"status": "error", "message": str(e)}, status=500
            )

    return JsonResponse(
        {"status": "error", "message": "Invalid request"}, status=400
    )

def currency_converter_view(request):
    """Renders the Currency Converter resource page."""
    return render(request, 'tradelog/currency_converter.html')