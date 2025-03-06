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
from django.http import JsonResponse
from django.urls import path
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

    # Get the primary keys of users in the "jfc" or "fc" groups
    #fc_users_ids = User.objects.filter(groups__name__in=["junior fc", "fc"]).values_list('id', flat=True)

    fc_users_ids = User.objects.filter(groups__name__in=AFCTRACK_FC_GROUPS).values_list('id', flat=True)
    
    # Filter FatLink by those users and the selected month/year
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=current_month,
        created__year=current_year
    ).values('creator_id__username', 'id', 'fleet_type')\
     .annotate(fleet_count=Count('id')).order_by('creator_id__username', 'fleet_type')

    # Aggregate fleet counts, doctrine points, and participants
    player_data = {}
    total_fleet_points = 0

    for fleet in fleet_counts:
        player_name = fleet['creator_id__username']
        fleet_id = fleet['id']
        fleet_type = fleet['fleet_type']
        fleet_count = fleet['fleet_count']

        # Count participants for this fleet from the afat_fat table
        participant_count = Fat.objects.filter(fatlink_id=fleet_id).count()

        # Get points for the doctrine
        fleet_points = POINTS.get(fleet_type, 0)

        if player_name not in player_data:
            player_data[player_name] = {
                'total_fleet_count': 0,
                'total_fleet_points': 0,
                'total_participants': 0,
            }

        # Accumulate fleet counts, points, and participants for the player
        player_data[player_name]['total_fleet_count'] += fleet_count
        player_data[player_name]['total_fleet_points'] += fleet_points * fleet_count
        player_data[player_name]['total_participants'] += participant_count
        total_fleet_points += fleet_points * fleet_count

    # Calculate ISK per point if the total score is greater than 0
    if total_fleet_points > 0:
        isk_per_point = budget / total_fleet_points
        round_isk_per_point = round(isk_per_point)
    else:
        isk_per_point = 0
        round_isk_per_point = round(isk_per_point)

    # Calculate the payment for each player
    player_payments = []
    for player_name, data in player_data.items():
        # Calculate the payment based on the doctrine points
        payment = data['total_fleet_points'] * round_isk_per_point
        # Calculate the average participants per fleet
        avg_participants = data['total_participants'] / data['total_fleet_count'] if data['total_fleet_count'] > 0 else 0
        player_payments.append({
            'player_name': player_name,
            'fleet_count': data['total_fleet_count'],
            'avg_participants': avg_participants,
            'payment': payment,
        })

    return player_payments


def get_doctrine_counts(selected_month, selected_year):
    """
    Get doctrine counts and average participants for the selected month/year.
    """
    # Get the primary keys of users in the "jfc" or "fc" groups
    #fc_users_ids = User.objects.filter(groups__name__in=["junior fc", "fc"]).values_list('id', flat=True)
    fc_users_ids = User.objects.filter(groups__name__in=AFCTRACK_FC_GROUPS).values_list('id', flat=True)

    # Filter FatLink by those users and the selected month/year
    doctrine_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=selected_month,
        created__year=selected_year
    ).values('doctrine').annotate(
        doctrine_count=Count('id')
    ).order_by('-doctrine_count')

    # Calculate average participants per doctrine
    doctrine_data = []
    for doctrine in doctrine_counts:
        doctrine_name = doctrine['doctrine']
        doctrine_count = doctrine['doctrine_count']

        # Count total participants for all fleets under this doctrine
        total_participants = Fat.objects.filter(
            fatlink_id__in=FatLink.objects.filter(
                creator_id__in=fc_users_ids,
                created__month=selected_month,
                created__year=selected_year,
                doctrine=doctrine_name
            ).values_list('id', flat=True)
        ).count()

        # Calculate average participants per fleet
        avg_participants = total_participants / doctrine_count if doctrine_count > 0 else 0

        doctrine_data.append({
            'doctrine': doctrine_name,
            'doctrine_count': doctrine_count,
            'avg_participants': round(avg_participants, 1),  # Round to 1 decimal
        })

    return doctrine_data

def get_fleet_type_amount(selected_month, selected_year):
    """
    Get fleet type counts and average participants for the selected month/year.
    """
    # Get the primary keys of users in the "jfc" or "fc" groups
    #fc_users_ids = User.objects.filter(groups__name__in=["junior fc", "fc", "Mining Officer"]).values_list('id', flat=True)
    fc_users_ids = User.objects.filter(groups__name__in=AFCTRACK_FLEET_TYPE_GROUPS).values_list('id', flat=True)

    # Filter FatLink by fleet_type and selected month/year
    fleet_count_type = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=selected_month,
        created__year=selected_year
    ).values('fleet_type')\
     .annotate(type_count=Count('id'))\
     .order_by('-type_count')

    # Calculate average participants per fleet type
    fleet_data = []
    for fleet in fleet_count_type:
        fleet_type = fleet['fleet_type']
        fleet_count = fleet['type_count']

        # Count total participants for all fleets of this fleet_type
        total_participants = Fat.objects.filter(
            fatlink_id__in=FatLink.objects.filter(
                creator_id__in=fc_users_ids,
                created__month=selected_month,
                created__year=selected_year,
                fleet_type=fleet_type
            ).values_list('id', flat=True)
        ).count()

        # Calculate average participants per fleet type
        avg_participants = total_participants / fleet_count if fleet_count > 0 else 0

        fleet_data.append({
            'fleet_type': fleet_type,
            'fleet_count': fleet_count,
            'avg_participants': round(avg_participants, 1),  # Round to 1 decimal
        })

    return fleet_data


@token_required(scopes=['esi-fleets.read_fleet.v1', 'esi-fleets.write_fleet.v1'])
def update_fleet_motd(request, token):
    """ Holt die aktuelle Flotten-ID aus FatLink, prüft die Doktrin und aktualisiert die MOTD. """
    
    # 1️⃣ **Aktuelle Flotte holen**
    fatlink = FatLink.objects.filter(is_registered_on_esi=True).order_by('-created').first()
    if not fatlink:
        logger.warning("❌ Keine aktive Flotte (FatLink) gefunden.")
        return JsonResponse({"status": "error", "message": "Keine aktive Flotte gefunden"}, status=400)

    fleet_id = fatlink.esi_fleet_id

    # 2️⃣ **Fleet Boss bestimmen**
    if hasattr(fatlink.creator, 'eve_character'):
        fleet_boss = fatlink.creator.eve_character.character_name
    elif hasattr(fatlink.creator, 'profile') and hasattr(fatlink.creator.profile, 'character_name'):
        fleet_boss = fatlink.creator.profile.character_name
    else:
        fleet_boss = fatlink.creator.username  # Falls nichts existiert, nehme den Django-Username

    doctrine_name = fatlink.doctrine or "Unbekannt"
    comms = "https://shorturl.at/Kg2ka"  # Standard Comms

    # 3️⃣ **Doctrine-Link abrufen**
    doctrine_link = "N/A"
    try:
        doctrine_obj = Doctrine.objects.get(name=doctrine_name)
        doctrine_link = f"http://127.0.0.1:8000/fittings/doctrine/{doctrine_obj.id}"
    except Doctrine.DoesNotExist:
        logger.warning(f"⚠️ Doktrin '{doctrine_name}' existiert nicht. Standard-Link wird verwendet.")

    # 4️⃣ **ESI Client erstellen**
    esi = esi_client_factory(token=token)

    # 5️⃣ **Neue MOTD setzen**
    motd = f"""
    <font size="14" color="#ffff0000">Staging:</font>   
    <font size="14" color="#ffd98d00"><loc><a href="showinfo:35834//1034323745897">P-ZMZV</a></loc></font><br>

    <font size="14" color="#bfffffff">FC:</font> 
    <font size="14" color="#ffd98d00">{fleet_boss}</font><br>

    <font size="14" color="#ff00ff00">Doctrine Link:</font>
    <font size="14" color="#bfffffff"><a href="{doctrine_link}">{doctrine_name}</a></font><br>
    <font size="14" color="#ff00ff00">Comms:</font>
    <font size="14" color="#ff6868e1"><a href="{comms}">{comms}</a></font><br>

    <font size="13" color="#bfffffff">Boost Channel:</font>
    <font size="13" color="#ff6868e1"><a href="joinChannel:player_2ec80ee18cbb11eebe4600109bd0f828">IGC Boost</a></font><br>

    <font size="13" color="#bfffffff">Logi Channel:</font>
    <font size="13" color="#ff6868e1"><a href="joinChannel:player_270f64b08cba11ee9f7c00109bd0f828">IGC Logi</a></font>
    """

    # 6️⃣ **MOTD über ESI setzen**
    try:
        response = esi.Fleets.put_fleets_fleet_id(
    fleet_id=fleet_id, token=token.access_token, new_settings={"motd": motd}
)

        logger.info(f"✅ Flotten-MOTD erfolgreich geändert: {motd}")
        return JsonResponse({"status": "success", "message": "MOTD erfolgreich gesetzt", "esi_response": response}, status=200)
    except Exception as e:
        logger.exception(f"❌ Fehler beim Setzen der neuen MOTD: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def index(request):
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the selected month and year from GET parameters, default to current if not provided
    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))

    # Create a list of months (1 to 12)
    available_months = list(range(1, 13))  # months from 1 to 12

    # Create a list of years (current year and previous 5 years, for example)
    available_years = list(range(current_year - 5, current_year + 1))

    # Get the budget from GET parameters (default to 3 billion ISK)
    budget = int(request.GET.get('budget', 3000000000))

    # Get the fleet counts and payments based on the selected month, year, and budget
    player_payments = get_fleet_counts_and_payment(request, budget, selected_month, selected_year)

    # Pass data to the template
    context = {
        'month_name': calendar.month_name[selected_month],
        'available_months': available_months,  # List of months
        'available_years': available_years,    # List of years
        'player_payments': player_payments,
        'budget': budget,
        'selected_month': selected_month,  # Ensure selected month is highlighted
        'selected_year': selected_year,    # Ensure selected year is highlighted
    }

    return render(request, 'afctrack/index.html', context)


def doctrine_amount(request):
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the selected month and year from GET parameters, default to current if not provided
    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))

    # Create a list of months (1 to 12)
    available_months = list(range(1, 13))  # months from 1 to 12

    # Create a list of years (current year and previous 5 years, for example)
    available_years = list(range(current_year - 5, current_year + 1))

    # Get the doctrine counts and average participants
    doctrine_counts = get_doctrine_counts(selected_month, selected_year)

    # Pass data to the template
    context = {
        'month_name': calendar.month_name[selected_month],
        'available_months': available_months,  # List of months
        'available_years': available_years,    # List of years
        'doctrine_counts': doctrine_counts,
        'selected_month': selected_month,  # Ensure selected month is highlighted
        'selected_year': selected_year,    # Ensure selected year is highlighted
    }

    return render(request, "afctrack/doctrine_amount.html", context)


def fleet_type_amount(request):
    # Get the current month and year
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Get the selected month and year from GET parameters, default to current if not provided
    selected_month = int(request.GET.get('month', current_month))
    selected_year = int(request.GET.get('year', current_year))

    # Create a list of months (1 to 12)
    available_months = list(range(1, 13))  # months from 1 to 12

    # Create a list of years (current year and previous 5 years, for example)
    available_years = list(range(current_year - 5, current_year + 1))

    # Get the fleet type counts and average participants
    fleet_data = get_fleet_type_amount(selected_month, selected_year)

    # Pass data to the template, change fleet_data to fleet_type_counts
    context = {
        'month_name': calendar.month_name[selected_month],
        'available_months': available_months,  # List of months
        'available_years': available_years,    # List of years
        'fleet_type_counts': fleet_data,  # Change fleet_data to fleet_type_counts
        'selected_month': selected_month,  # Ensure selected month is highlighted
        'selected_year': selected_year,    # Ensure selected year is highlighted
    }

    return render(request, "afctrack/fleet_type_amount.html", context)

# def start_fleet(request):
#     """
#     View to handle fleet creation. Fetches doctrines and handles form submission.
#     """
#     doctrines = FittingsDoctrine.objects.all()  # Fetch doctrines from DB

#     if request.method == "POST":
#         # Get form data
#         fleet_boss = request.POST.get("fleet_boss")
#         fleet_name = request.POST.get("fleet_name")
#         doctrine = request.POST.get("doctrine")
#         fleet_type = request.POST.get("fleet_type")
#         comms = request.POST.get("comms")

#         # Validate required fields
#         if not (fleet_boss and fleet_name and doctrine and fleet_type):
#             messages.error(request, "All fields are required.")
#             return render(request, "afctrack/start_fleet.html", {"doctrines": doctrines})

#         # Process fleet creation logic (this part needs to be defined)
#         # Example: Save to a model or trigger an action
#         messages.success(request, f"Fleet '{fleet_name}' has been started successfully.")

#         return redirect("afctrack:index")  # Redirect to home after submission

#     return render(request, "afctrack/start_fleet.html", {"doctrines": doctrines})