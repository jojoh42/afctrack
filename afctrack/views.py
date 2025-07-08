import calendar
import logging
from datetime import datetime
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count, Prefetch
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from afat.models import FatLink, Doctrine, Fat  # Fleet gibt es nicht, daher nutzen wir FatLink
from esi.clients import esi_client_factory
from esi.decorators import token_required
from fittings.models import Doctrine
from .models import POINTS
from .app_settings import AFCTRACK_FC_GROUPS, AFCTRACK_FLEET_TYPE_GROUPS, DEFAULT_BUDGET, FLEET_TYPES, COMMS_OPTIONS
from afat.models import get_hash_on_save
from .tasks import delayed_updated_fleet_motd

logger = logging.getLogger(__name__)  # ✅ Logging setup

# Helper functions

def get_selected_month_year(request):
    """Get selected month and year from GET params or use current."""
    now = datetime.now()
    selected_month = int(request.GET.get('month', now.month))
    selected_year = int(request.GET.get('year', now.year))
    return selected_month, selected_year

def get_available_months_years():
    now = datetime.now()
    return list(range(1, 13)), list(range(now.year - 5, now.year + 1))

@login_required
@permission_required("afctrack.basic_access")
def get_fleet_counts_and_payment(request, budget, selected_month, selected_year):
    """
    Get fleet counts and calculate the payment for each user based on their fleet count, doctrine, and participants.
    Returns a list of dictionaries with player names, payments, and average participants.
    Optimized to avoid N+1 queries.
    """
    fc_users_ids = User.objects.filter(groups__name__in=AFCTRACK_FC_GROUPS).values_list('id', flat=True)

    # Annotate FatLink with participant counts
    fleet_counts = FatLink.objects.filter(
        creator_id__in=fc_users_ids,
        created__month=selected_month,
        created__year=selected_year
    ).values('creator_id__username', 'fleet_type').annotate(
        fleet_count=Count('id'),
        total_participants=Count('afat_fat__id')
    ).order_by('creator_id__username', 'fleet_type')

    player_data = {}
    total_fleet_points = 0

    for fleet in fleet_counts:
        player_name = fleet['creator_id__username']
        fleet_type = fleet['fleet_type']
        fleet_count = fleet['fleet_count']
        participant_count = fleet['total_participants']
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

    round_isk_per_point = round(budget / total_fleet_points) if total_fleet_points > 0 else 0

    player_payments = []
    for player_name, data in player_data.items():
        payment = data['total_fleet_points'] * round_isk_per_point
        avg_participants = data['total_participants'] / data['total_fleet_count'] if data['total_fleet_count'] > 0 else 0
        player_payments.append({
            'player_name': player_name,
            'fleet_count': data['total_fleet_count'],
            'avg_participants': round(avg_participants, 1),
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

def index(request):
    """Main index view for FC tracker."""
    selected_month, selected_year = get_selected_month_year(request)
    available_months, available_years = get_available_months_years()
    try:
        budget = int(request.GET.get('budget', DEFAULT_BUDGET))
    except ValueError:
        budget = int(DEFAULT_BUDGET)
        messages.error(request, "Invalid budget value. Using default.")

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
    """View for doctrine amount stats."""
    selected_month, selected_year = get_selected_month_year(request)
    available_months, available_years = get_available_months_years()
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
    """View for fleet type amount stats."""
    selected_month, selected_year = get_selected_month_year(request)
    available_months, available_years = get_available_months_years()
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

@login_required
@permission_required("afctrack.basic_access")
def start_fleet(request):
    """Handles the fleet creation form and updates the MOTD after submission."""
    
    doctrines = Doctrine.objects.all()
    fleet_types = FLEET_TYPES
    comms_options = COMMS_OPTIONS

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

        # Save data in session
        request.session['fleet_boss'] = fleet_boss
        request.session['doctrine_name'] = doctrine_name
        request.session['fleet_type'] = fleet_type
        request.session['comms'] = comms
        request.session['fleet_name'] = fleet_name
        # Redirect to the update_fleet_motd view
        return HttpResponseRedirect(reverse('afctrack:update_fleet_motd'))

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
    fleet_name = request.session.get('fleet_name')
    doctrine_name = request.session.get('doctrine_name')
    fleet_type = request.session.get('fleet_type')
    comms = request.session.get('comms')

    if not all([fleet_boss, doctrine_name, fleet_type, comms]):
        messages.error(request, "❌ Missing fleet data in session")
        return HttpResponseRedirect(reverse('afctrack:start_fleet'))

    # fatlink = FatLink.objects.filter(is_registered_on_esi=True).order_by('-created').first()
    # if not fatlink:
    #     messages.error(request, "❌ No active fleet (FatLink) found.")
    #     logger.warning("❌ Keine aktive Flotte (FatLink) gefunden.")
    #     return HttpResponseRedirect(reverse('afctrack:start_fleet'))

    # fleet_id = fatlink.esi_fleet_id
    fleet_id = get_fleet_id(token)
    if not fleet_id:
        messages.error(request, "❌ No active fleet (ESI) found.")
        logger.warning("❌ Keine aktive Flotte (ESI) gefunden.")
        return HttpResponseRedirect(reverse('afctrack:start_fleet'))

    # Doctrine-Link abrufen
    doctrine_link = "N/A"
    try:
        doctrine_obj = Doctrine.objects.get(name=doctrine_name)
        domain = request.get_host()
        scheme = 'https' if request.is_secure() else 'http'
        base_url = f"{scheme}://{domain}"
        doctrine_link = f"{base_url}/fittings/doctrine/{doctrine_obj.id}"
#        doctrine_link = f"https://aa.igc-alliance.online/fittings/doctrine/{doctrine_obj.id}"
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
        return HttpResponseRedirect(reverse('afctrack:create_esi_fleet'))
    except Exception as e:
        logger.exception(f"❌ Fehler beim Setzen der neuen MOTD: {e}")
        messages.error(request, f"❌ Fehler beim Setzen der neuen MOTD: {e}")
        return HttpResponseRedirect(reverse('afctrack:start_fleet'))
    
def get_fleet_id(token):
    """Fetch the fleet ID of the current character via ESI."""
    try:
        esi_client = esi_client_factory(token=token)
        response = esi_client.Fleets.get_characters_character_id_fleet(
            character_id=token.character_id,
            token=token.access_token
        )
        fleet_data = response.result()
        return fleet_data.get('fleet_id')  # Extract fleet_id if available
    except Exception as e:
        logger.error(f"❌ Error fetching fleet ID: {e}")
        return None
    
def create_esi_fleet(request):
    """
    Creates an ESI FAT link and redirects to the AFAT callback function.
    """
    fatlink_hash = get_hash_on_save()

    # ✅ Speichere Werte explizit in der Session
    request.session["fatlink_form__name"] = request.session.get("fleet_name", "Default Name")
    request.session["fatlink_form__doctrine"] = request.session.get("doctrine_name", "Default Doctrine")
    request.session["fatlink_form__type"] = request.session.get("fleet_type", "Default Type")
    
    request.session.save()  # 🔥 WICHTIG: Session-Änderungen speichern

    # Speichere nur relevante Daten für Celery
    session_data = {
        "fleet_name": request.session["fatlink_form__name"],
        "doctrine_name": request.session["fatlink_form__doctrine"],
        "fleet_type": request.session["fatlink_form__type"],
    }

    # ✅ Starte Celery Task
    delayed_updated_fleet_motd.apply_async(args=[session_data])

    # Redirect zur FATLink-Erstellung
    return HttpResponseRedirect(reverse("afat:fatlinks_create_esi_fatlink_callback", args=[fatlink_hash]))
