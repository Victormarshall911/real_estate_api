from django.db import migrations

def seed_data(apps, schema_editor):
    State = apps.get_model('properties', 'State')
    LGA = apps.get_model('properties', 'LGA')
    PropertyListing = apps.get_model('properties', 'PropertyListing')

    # 1. Migrate old listing_type choices
    # Convert 'regular' -> 'sale'
    PropertyListing.objects.filter(listing_type='regular').update(
        listing_type='sale',
        property_category='land',
        property_type='plot'
    )
    # Convert 'upcoming' -> 'sale', property_type='estate'
    PropertyListing.objects.filter(listing_type='upcoming').update(
        listing_type='sale',
        property_category='land',
        property_type='estate'
    )

    # 2. Seed States and LGAs
    locations = {
        'Lagos': [
            'Eti-Osa', 'Ikeja', 'Ibeju-Lekki', 'Ikorodu', 'Surulere',
            'Alimosho', 'Kosofe', 'Lagos Island', 'Lagos Mainland', 'Apapa'
        ],
        'Abuja (FCT)': [
            'Abuja Municipal Area Council (AMAC)', 'Bwari', 'Gwagwalada', 'Kuje', 'Kwali', 'Abaji'
        ],
        'Rivers': [
            'Port Harcourt', 'Obio-Akpor', 'Eleme', 'Ikwerre', 'Oyigbo', 'Bonny'
        ],
        'Oyo': [
            'Ibadan North', 'Ibadan Northeast', 'Ibadan Northwest', 'Ibadan Southeast', 'Ibadan Southwest',
            'Akinyele', 'Egbeda'
        ],
        'Enugu': [
            'Enugu North', 'Enugu South', 'Enugu East', 'Nsukka', 'Udi'
        ]
    }

    for state_name, lgas in locations.items():
        state_obj, _ = State.objects.get_or_create(name=state_name)
        for lga_name in lgas:
            LGA.objects.get_or_create(name=lga_name, state=state_obj)


def rollback_seed(apps, schema_editor):
    State = apps.get_model('properties', 'State')
    LGA = apps.get_model('properties', 'LGA')
    
    LGA.objects.all().delete()
    State.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0005_lga_state_propertylisting_agency_fee_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_data, rollback_seed),
    ]
