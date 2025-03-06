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
from afat.models import FatLink, Fat
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

def update_fleet_motd(request):
    doctrines = FittingsDoctrine.objects.all()
    motd = ""

    def get_latest_esi_token(user_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT access_token, character_id, refresh_token
                FROM esi_token
                WHERE user_id = %s
                ORDER BY created DESC
                LIMIT 1;
            """, [request.user.id])

            row = cursor.fetchone()

        if row:
            return {
                "access_token": row[0],
                "character_id": row[1],
                "refresh_token": row[2],
            }
        else:
            return None

    token_data = get_latest_esi_token_for_user(request.user.id)

    if not token_data:
        logging.error(f"❌ Kein ESI Token gefunden für User {request.user.username}")
        messages.error(request, "Bitte authentifiziere dich erneut mit deinem EVE Charakter.")
        return render(request, "afctrack/start_fleet.html")

    access_token = token_data['access_token']
    character_id = token_data['character_id']

    doctrines = FittingsDoctrine.objects.all()

    if request.method == "POST":
        fleet_boss = request.POST.get("fleet_boss")
        fleet_name = request.POST.get("fleet_name")
        doctrine_id = request.POST.get("doctrine")
        fleet_type = request.POST.get("fleet_type")
        comms = request.POST.get("comms")

        if not all([fleet_boss, fleet_name, doctrine_id, fleet_type, comms]):
            messages.error(request, "Alle Felder sind erforderlich.")
            return render(request, "afctrack/start_fleet.html")

        try:
            doctrine = FittingsDoctrine.objects.get(id=doctrine_id)
            doctrine_link = f"http://127.0.0.1:8000/fittings/doctrine/{doctrine.id}"
        except FittingsDoctrine.DoesNotExist:
            messages.error(request, "Gewählte Doctrine existiert nicht.")
            return render(request, "afctrack/start_fleet.html")

        headers = {"Authorization": f"Bearer {access_token}"}
        fleet_response = requests.get(ESI_CHARACTER_FLEET_URL.format(character_id=token_data['character_id']), headers=headers)

        if fleet_response.status_code == 200:
            fleet_id = fleet_response.json().get("fleet_id")
        else:
            messages.error(request, "Aktuelle Flotte konnte nicht abgerufen werden.")
            return render(request, "afctrack/start_fleet.html")

        motd = f"""
        <font size=\"14\" color=\"#ffff0000\">Staging:</font>   
        <font size=\"14\" color=\"#ffd98d00\"><loc><a href=\"showinfo:35834//1034323745897\">P-ZMZV</a></loc></font><br><br>

        <font size=\"14\" color=\"#bfffffff\">FC:</font> 
        <font size=\"14\" color=\"#ffd98d00\">{fleet_boss}</font><br><br>

        <font size=\"14\" color=\"#ff00ff00\">Doctrine Link:</font><br>
        <font size=\"14\" color=\"#bfffffff\"><a href=\"{doctrine_link}\">{doctrine.name}</a></font><br><br>

        <font size=\"14\" color=\"#ff00ff00\">Comms:</font><br>
        <font size=\"14\" color=\"#ff6868e1\"><a href=\"{comms}\">{comms}</a></font><br><br>

        <font size=\"13\" color=\"#bfffffff\">Boost Channel:</font>
        <font size=\"13\" color=\"#ff6868e1\"><a href=\"joinChannel:player_2ec80ee18cbb11eebe4600109bd0f828\">IGC Boost</a></font><br><br>

        <font size=\"13\" color=\"#bfffffff\">Logi Channel:</font>
        <font size=\"13\" color=\"#ff6868e1\"><a href=\"joinChannel:player_270f64b08cba11ee9f7c00109bd0f828\">IGC Logi</a></font>
        """

        response = requests.put(
            ESI_UPDATE_MOTD_URL.format(fleet_id=fleet_id),
            headers=headers,
            json={"motd": motd}
        )

        if response.status_code == 204:
            messages.success(request, "Fleet MOTD erfolgreich aktualisiert.")
        else:
            messages.error(request, f"Fehler beim Aktualisieren der MOTD. Statuscode: {response.status_code}")

    return render(request, "afctrack/start_fleet.html", {"motd": motd})



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