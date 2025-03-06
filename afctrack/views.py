import calendar
import requests
import json
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
from esi.clients import esi_client_factory
from esi.decorators import token_required
from fittings.models import Doctrine
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

def start_fleet(request):

    """Handles the fleet creation form and updates the MOTD after submission."""
    
    doctrines = Doctrine.objects.all()
    fleet_types = ["Peacetime", "StratOP", "Mining", "Hive"]
    comms_options = [
        {"name": "OP1", "url": "https://shorturl.at/Kg2ka"},
        {"name": "OP2", "url": "https://shorturl.at/Kg2ka"},
        {"name": "OP3", "url": "https://shorturl.at/Kg2ka"},
        {"name": "OP4", "url": "https://shorturl.at/Kg2ka"},
        {"name": "OP5", "url": "https://shorturl.at/Kg2ka"},
    ]

    if request.method == "POST":
        fleet_boss = request.POST.get("fleet_boss")
        fleet_name = request.POST.get("fleet_name")
        doctrine_name = request.POST.get("doctrine")
        fleet_type = request.POST.get("fleet_type")
        comms = request.POST.get("comms")

        if not all([fleet_boss, fleet_name, doctrine_name, fleet_type, comms]):
            messages.error(request, "❌ All fields must be filled!")
            return render(request, "afctrack/start_fleet.html", {
                "doctrines": doctrines,
                "fleet_types": fleet_types,
                "comms_options": comms_options,
            })

        # URL-encode the comms URL to avoid issues with special characters
        from urllib.parse import quote
        comms_encoded = quote(comms)

        # Redirect to the MOTD update view
        return HttpResponseRedirect(
            reverse('afctrack:update_fleet_motd', kwargs={
                'fleet_boss': fleet_boss,
                'doctrine_name': doctrine_name,
                'fleet_type': fleet_type,
                'comms': comms_encoded
            })
        )

    return render(request, "afctrack/start_fleet.html", {
        "doctrines": doctrines,
        "fleet_types": fleet_types,
        "comms_options": comms_options,
    })

@token_required(scopes=['esi-fleets.read_fleet.v1', 'esi-fleets.write_fleet.v1'])
def update_fleet_motd(request, token, fleet_boss, doctrine_name, fleet_type, comms):
    """ Updates the MOTD for the fleet """
    from urllib.parse import unquote

    comms_decoded = unquote(comms)  # Decode the comms URL if necessary

    fatlink = FatLink.objects.filter(is_registered_on_esi=True).order_by('-created').first()
    if not fatlink:
        logger.warning("❌ Keine aktive Flotte (FatLink) gefunden.")
        return JsonResponse({"status": "error", "message": "Keine aktive Flotte gefunden"}, status=400)

    fleet_id = fatlink.esi_fleet_id

    doctrine_link = "N/A"
    try:
        doctrine_obj = Doctrine.objects.get(name=doctrine_name)
        doctrine_link = f"http://127.0.0.1:8000/fittings/doctrine/{doctrine_obj.id}"
    except Doctrine.DoesNotExist:
        logger.warning(f"⚠️ Doktrin '{doctrine_name}' existiert nicht. Standard-Link wird verwendet.")

    motd = f"""´<br>
    <font size="14" color="#ffff0000">Staging:</font>   
    <font size="14" color="#ffd98d00"><loc><a href="showinfo:35834//1034323745897">P-ZMZV</a></loc></font><br>

    <font size="14" color="#bfffffff">FC:</font> <font size="14" color="#ffd98d00">{fleet_boss}</font><br>

    <font size="14" color="#ff00ff00">Doctrine Link:</font> <font size="14" color="#bfffffff"><a href="{doctrine_link}">{doctrine_name}</a></font><br>
    <font size="14" color="#ff00ff00">Comms:</font> <font size="14" color="#ff6868e1"><a href="{comms_decoded}">{comms_decoded}</a></font><br>

    <font size="13" color="#bfffffff">Boost Channel:</font> <font size="13" color="#ff6868e1"><a href="joinChannel:player_2ec80ee18cbb11eebe4600109bd0f828">IGC Boost</a></font><br>

    <font size="13" color="#bfffffff">Logi Channel:</font> <font size="13" color="#ff6868e1"><a href="joinChannel:player_270f64b08cba11ee9f7c00109bd0f828">IGC Logi</a></font>
    """

    try:
        response = esi_client_factory(token=token).Fleets.put_fleets_fleet_id(
            fleet_id=fleet_id, token=token.access_token, new_settings={"motd": motd}
        )
        api_response = response.result()
        logger.info(f"✅ Flotten-MOTD erfolgreich geändert: {motd}")
        return JsonResponse({"status": "success", "message": "MOTD erfolgreich gesetzt", "esi_response": api_response}, status=200)
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
