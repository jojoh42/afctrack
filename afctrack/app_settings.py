"""App Settings"""

# Django
from django.conf import settings

# put your app settings here


FC_Payment_Amount = getattr(settings, "FC_Payment_Ammount", 200000000)
FC_Payment_Amount_Max = getattr(settings, "FC_Payment_Ammount_Max", 1000000000)
JFC_Payment_Amount = getattr(settings, "JFC_Payment_Ammount", 100000000)
JFC_Payment_Amount_Max = getattr(settings, "JFC_Payment_Ammount_Max", 500000000)