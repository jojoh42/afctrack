import calendar
import requests
import json
import time
import logging
from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.contrib import messages
from django.shortcuts import redirect
from django.db import connection
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import path, reverse
from afat.models import FatLink, Doctrine, Fat  # Fleet gibt es nicht, daher nutzen wir FatLink
from afat.views.fatlinks import create_esi_fatlink, add_fatlink  # Verwende AFAT Funktion
from esi.clients import esi_client_factory
from esi.decorators import token_required
from fittings.models import Doctrine
from esi.models import Token
from afat.views.fatlinks import create_esi_fatlink_callback
from afat.models import get_hash_on_save
from esi.models import Token
from esi.decorators import token_required
from afat.views.fatlinks import create_esi_fatlink_callback
from afat.models import get_hash_on_save

from .models import POINTS
from .app_settings import AFCTRACK_FC_GROUPS, AFCTRACK_FLEET_TYPE_GROUPS
from .models import FittingsDoctrine

logger = logging.getLogger(__name__)  # ✅ Logging setup


# ESI API URLs
ESI_FLEET_URL = "https://esi.evetech.net/latest/fleets/{fleet_id}/"
ESI_UPDATE_MOTD_URL = "https://esi.evetech.net/latest/fleets/{fleet_id}/motd/"
ESI_CHARACTER_FLEET_URL = "https://esi.evetech.net/latest/characters/{character_id}/fleet/"

@login_required
@permission_required("afctrack.basic_access")
def get_fleet_counts_and_payment(request, budget, selected_month, selected_year):
    print(f"Request user: {request.user}")
    """
    Get fleet counts and calculate the payment for each user based on their fleet count, doctrine, and participants.
    Returns a list of dictionaries with player names, payments, and average participants.
    """
    current_month = selected_month
    current_year = selected_year

    fc_users_ids = User.objects.filter(groups__name__in=AFCTRACK_FC_GROUPS).values_list('id', flat=True)
    
    # Filter FatLink by those users and the selected month/year
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('creator_id__username', 'id', 'fleet_type')\
     .annotate(fleet_count=Count('id')).order_by('creator_id__username', 'fleet_type')

    player_data = {}
    total_fleet_points = 0

    for fleet in fleet_counts:
        player_name = fleet['creator_id__username']
        fleet_id = fleet['id']
        fleet_type = fleet['fleet_type']
        fleet_count = fleet['fleet_count']

        participant_count = Fat.objects.filter(fatlink_id=fleet_id).count()
        fleet_points = POINTS.get(fleet_type, 0)

        if player_name not in player_data:
            player_data[player_name] = {
                'total_fleet_count': 0,
                'total_fleet_points': 0,
                'total_participants': 0,
            }

        player_data[player_name]['total_fleet_count'] += fleet_count
        player_data[player_name]['total_fleet_points'] += fleet_points * fleet_count
        player_data[player_name]['total_participants'] += participant_count
        total_fleet_points += fleet_points * fleet_count

    if total_fleet_points > 0:
        isk_per_point = budget / total_fleet_points
        round_isk_per_point = round(isk_per_point)
    else:
        isk_per_point = 0
        round_isk_per_point = round(isk_per_point)

    player_payments = []
    for player_name, data in player_data.items():
        payment = data['total_fleet_points'] * round_isk_per_point
        avg_participants = data['total_participants'] / data['total_fleet_count'] if data['total_fleet_count'] > 0 else 0
        player_payments.append({
            'player_name': player_name,
            'fleet_count': data['total_fleet_count'],
            'avg_participants': avg_participants,
            'payment': payment,
        })

    return player_payments


def get_doctrine_counts(selected_month, selected_year):
    fc_users_ids = User.objects.filter(groups__name__in=AFCTRACK_FC_GROUPS).values_list('id', flat=True)

    doctrine_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=selected_month,
        created__year=selected_year
    ).values('doctrine').annotate(
        doctrine_count=Count('id')
    ).order_by('-doctrine_count')

    doctrine_data = []
    for doctrine in doctrine_counts:
        doctrine_name = doctrine['doctrine']
        doctrine_count = doctrine['doctrine_count']

        total_participants = Fat.objects.filter(
            fatlink_id__in=FatLink.objects.filter(
                creator_id__in=fc_users_ids,
                created__month=selected_month,
                created__year=selected_year,
                doctrine=doctrine_name
            ).values_list('id', flat=True)
        ).count()

        avg_participants = total_participants / doctrine_count if doctrine_count > 0 else 0

        doctrine_data.append({
            'doctrine': doctrine_name,
            'doctrine_count': doctrine_count,
            'avg_participants': round(avg_participants, 1),
        })

    return doctrine_data

def get_fleet_type_amount(selected_month, selected_year):
    fc_users_ids = User.objects.filter(groups__name__in=AFCTRACK_FLEET_TYPE_GROUPS).values_list('id', flat=True)

    fleet_count_type = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=selected_month,
        created__year=selected_year
    ).values('fleet_type')\
     .annotate(type_count=Count('id'))\
     .order_by('-type_count')

    fleet_data = []
    for fleet in fleet_count_type:
        fleet_type = fleet['fleet_type']
        fleet_count = fleet['type_count']

        total_participants = Fat.objects.filter(
            fatlink_id__in=FatLink.objects.filter(
                creator_id__in=fc_users_ids,
                created__month=selected_month,
                created__year=selected_year,
                fleet_type=fleet_type
            ).values_list('id', flat=True)
        ).count()

        avg_participants = total_participants / fleet_count if fleet_count > 0 else 0

        fleet_data.append({
            'fleet_type': fleet_type,
            'fleet_count': fleet_count,
            'avg_participants': round(avg_participants, 1),
        })

    return fleet_data



@login_required
@permission_required("afctrack.basic_access")
def start_fleet(request):
    """Startet eine neue Flotte, registriert sie über ESI und erstellt einen FAT-Eintrag."""

    doctrines = Doctrine.objects.all()
    fleet_types = ["Peacetime", "StratOP", "Mining", "Hive"]

    comms_options = [
        {"name": "Capital OP", "url": "https://tinyurl.com/ywwp85u9"},
        {"name": "OP1-Stratergic", "url": "https://tinyurl.com/IGCOP1"},
        {"name": "OP2-Home Defense", "url": "https://tinyurl.com/IGCOP2"},
        {"name": "OP3-CTA", "url": "https://tinyurl.com/3m64n62p"},
        {"name": "OP4-Moon Event", "url": "https://tinyurl.com/mrh6436r"},
        {"name": "OP5-ICE Event", "url": "https://tinyurl.com/mr5sspda"},
        {"name": "OP6 - Peacetime", "url": "https://tinyurl.com/ymusr8k9"},
        {"name": "OP7 - Peacetime", "url": "https://tinyurl.com/bp7r58ep"},
        {"name": "OP8 - Peacetime", "url": "https://tinyurl.com/2dbcwwcu"}
    ]

    if request.method == "POST":
        fleet_boss = request.POST.get("fleet_boss")
        fleet_name = request.POST.get("fleet_name")
        doctrine_name = request.POST.get("doctrine")
        fleet_type = request.POST.get("fleet_type")
        comms = request.POST.get("comms")

        if not all([fleet_boss, fleet_name, doctrine_name, fleet_type, comms]):
            messages.error(request, "❌ Alle Felder müssen ausgefüllt sein!")
            return render(request, "afctrack/start_fleet.html", {
                "doctrines": doctrines,
                "fleet_types": fleet_types,
                "comms_options": comms_options,
            })

        logger.info(f"📡 Starte ESI FAT-Link Registrierung für Fleet '{fleet_name}' durch {request.user}")

        # 1️⃣ **Erstelle einen eindeutigen FAT-Link Hash**
        fatlink_hash = get_hash_on_save()

        # 2️⃣ **Session-Daten setzen**
        request.session["fatlink_form__name"] = fleet_name
        request.session["fatlink_form__doctrine"] = doctrine_name
        request.session["fatlink_form__type"] = fleet_type

        # 3️⃣ **Hole das ESI-Token des Fleet-Bosses**
        esi_token = Token.objects.filter(
            character_id=request.user.profile.main_character.character_id
        ).order_by('-created').first()

        if not esi_token:
            logger.error(f"❌ Kein ESI-Token für {request.user} gefunden! Umleitung zur ESI-Authentifizierung...")
            messages.error(request, "❌ Fehler: Kein gültiges ESI-Token gefunden. Bitte reloggen!")
            return redirect("esi:login")  # Umleitung zum ESI-Login

        # 4️⃣ **FAT-Link über `create_esi_fatlink_callback` registrieren**
        try:
            response = create_esi_fatlink_callback(request, esi_token, fatlink_hash)
            logger.info(f"✅ ESI FAT-Link erfolgreich erstellt für Fleet '{fleet_name}' mit Hash {fatlink_hash}")
        except Exception as e:
            logger.error(f"❌ Fehler bei `create_esi_fatlink_callback`: {e}", exc_info=True)
            messages.error(request, f"❌ Fehler: FAT-Link konnte nicht über ESI erstellt werden. Details: {str(e)}")
            return redirect("afctrack:start_fleet")

        return response  # Weiterleitung basierend auf `create_esi_fatlink_callback`

    return render(request, "afctrack/start_fleet.html", {
        "doctrines": doctrines,
        "fleet_types": fleet_types,
        "comms_options": comms_options,
    })


@token_required(scopes=['esi-fleets.read_fleet.v1', 'esi-fleets.write_fleet.v1'])
def update_fleet_motd(request, token):
    """Updates the MOTD for the fleet."""
    
    # Get data from session
    fleet_boss = request.session.get('fleet_boss')
    doctrine_name = request.session.get('doctrine_name')
    fleet_type = request.session.get('fleet_type')
    comms = request.session.get('comms')

    if not all([fleet_boss, doctrine_name, fleet_type, comms]):
        return JsonResponse({"status": "error", "message": "Missing fleet data in session"}, status=400)

    fatlink = FatLink.objects.filter(is_registered_on_esi=True).order_by('-created').first()
    if not fatlink:
        logger.warning("❌ Keine aktive Flotte (FatLink) gefunden.")
        return JsonResponse({"status": "error", "message": "Keine aktive Flotte gefunden"}, status=400)

    fleet_id = fatlink.esi_fleet_id

    # Doctrine-Link abrufen
    doctrine_link = "N/A"
    try:
        doctrine_obj = Doctrine.objects.get(name=doctrine_name)
        doctrine_link = f"http://127.0.0.1:8000/fittings/doctrine/{doctrine_obj.id}"
    except Doctrine.DoesNotExist:
        logger.warning(f"⚠️ Doktrin '{doctrine_name}' existiert nicht. Standard-Link wird verwendet.")

    # MOTD erstellen
    motd = f"""<br>
            <font size="14" color="#ffff0000">Staging:</font><font size="14" color="#bfffffff"></font><font size="14" color="#ffd98d00"><loc><a href="showinfo:35834//1034323745897">P-ZMZV</a></loc></font>
            <font size="14" color="#bfffffff">FC: </font><font size="14" color="#ffd98d00">{fleet_boss}</font>
            <font size="14" color="#ff00ff00">Doctrine Link:</font><font size="14" color="#bfffffff"> </font><font size="14" color="#ffffe400"><a href="{doctrine_link}">{doctrine_name}</a></font>
            <font size="14" color="#ff00ff00">Comms:</font><font size="14" color="#bfffffff"> </font><font size="14" color="#ffffe400"><a href="{comms}">{comms}</a></font>
            <font size="13" color="#bfffffff">Boost Channel:</font><font size="14" color="#bfffffff"> </font><font size="13" color="#ff6868e1"><a href="joinChannel:player_2ec80ee18cbb11eebe4600109bd0f828">IGC Boost</a></font>
            <font size="13" color="#bfffffff">Logi Channel:</font><font size="14" color="#bfffffff"> </font><font size="13" color="#ff6868e1"><a href="joinChannel:player_270f64b08cba11ee9f7c00109bd0f828">IGC Logi</a></font>
            <font size="14" color="#bfffffff"></font>"""

    # Set the MOTD via ESI
    try:
        response = esi_client_factory(token=token).Fleets.put_fleets_fleet_id(
            fleet_id=fleet_id, token=token.access_token, new_settings={"motd": motd}
        )
        api_response = response.result()
        logger.info(f"✅ Flotten-MOTD erfolgreich geändert: {motd}")
        messages.success(request, "✅ MOTD erfolgreich gesetzt")
        return HttpResponseRedirect(reverse('afctrack:start_fleet'))
    except Exception as e:
        logger.exception(f"❌ Fehler beim Setzen der neuen MOTD: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def index(request):
    current_month = datetime.now().month
    current_year = datetime.now().year

    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))

    available_months = list(range(1, 13))  
    available_years = list(range(current_year - 5, current_year + 1))

    budget = int(request.GET.get('budget', 3000000000))

    player_payments = get_fleet_counts_and_payment(request, budget, selected_month, selected_year)

    context = {
        'month_name': calendar.month_name[selected_month],
        'available_months': available_months,
        'available_years': available_years,
        'player_payments': player_payments,
        'budget': budget,
        'selected_month': selected_month,
        'selected_year': selected_year,
    }

    return render(request, 'afctrack/index.html', context)


def doctrine_amount(request):
    current_month = datetime.now().month
    current_year = datetime.now().year

    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))

    available_months = list(range(1, 13))  
    available_years = list(range(current_year - 5, current_year + 1))

    doctrine_counts = get_doctrine_counts(selected_month, selected_year)

    context = {
        'month_name': calendar.month_name[selected_month],
        'available_months': available_months,
        'available_years': available_years,
        'doctrine_counts': doctrine_counts,
        'selected_month': selected_month,
        'selected_year': selected_year,
    }

    return render(request, "afctrack/doctrine_amount.html", context)


def fleet_type_amount(request):
    current_month = datetime.now().month
    current_year = datetime.now().year

    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))

    available_months = list(range(1, 13))  
    available_years = list(range(current_year - 5, current_year + 1))

    fleet_data = get_fleet_type_amount(selected_month, selected_year)

    context = {
        'month_name': calendar.month_name[selected_month],
        'available_months': available_months,
        'available_years': available_years,
        'fleet_type_counts': fleet_data,
        'selected_month': selected_month,
        'selected_year': selected_year,
    }

    return render(request, "afctrack/fleet_type_amount.html", context)
