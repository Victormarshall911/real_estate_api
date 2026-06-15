import random
import os
import shutil
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from accounts.models import CustomUser
from realtors.models import RealtorProfile
from properties.models import PropertyListing, PropertyImage

class Command(BaseCommand):
    help = 'Seeds the database with mock properties and realtors for development'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding database...')

        # Ensure media directory exists
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root:
            os.makedirs(os.path.join(media_root, 'properties', 'images'), exist_ok=True)
            os.makedirs(os.path.join(media_root, 'realtors', 'profiles'), exist_ok=True)

        # Clear existing data
        PropertyListing.objects.all().delete()
        RealtorProfile.objects.all().delete()
        CustomUser.objects.filter(email__contains='@example.com').delete()

        # Create Realtors
        realtors = [
            {
                'email': 'adebayo@example.com', 'first': 'Adebayo', 'last': 'Ogunlesi',
                'company': 'Adebayo Properties', 'phone': '+2348012345678', 'bio': 'Premium estates in Lagos.'
            },
            {
                'email': 'horizon@example.com', 'first': 'Chidi', 'last': 'Eze',
                'company': 'Horizon Realty', 'phone': '+2348098765432', 'bio': 'Specialist in Lekki corridor.'
            }
        ]
        
        realtor_profiles = []
        for r in realtors:
            user = CustomUser.objects.create_user(
                email=r['email'], password='password123',
                first_name=r['first'], last_name=r['last'],
                role='realtor', is_email_verified=True
            )
            profile = RealtorProfile.objects.create(
                user=user, company_name=r['company'],
                phone_number=r['phone'], is_verified=True, bio=r['bio']
            )
            realtor_profiles.append(profile)

        # Mock Properties
        properties = [
            {
                'title': 'Premium Waterfront Estate Plot in Banana Island',
                'desc': 'Exclusive waterfront plot in Banana Island with C of O.',
                'price': '450000000.00', 'size': '1200.00', 'location': 'Banana Island, Ikoyi, Lagos',
                'state': 'Lagos', 'lat': '6.4590', 'lng': '3.4240'
            },
            {
                'title': 'Serviced Residential Plot — Lekki Phase 1',
                'desc': 'Fully serviced residential plot in the heart of Lekki Phase 1.',
                'price': '85000000.00', 'size': '648.00', 'location': 'Lekki Phase 1, Lagos',
                'state': 'Lagos', 'lat': '6.4470', 'lng': '3.4730'
            },
            {
                'title': 'Gated Estate Land in Maitama District',
                'desc': 'Prime land in secure gated estate in Abuja.',
                'price': '120000000.00', 'size': '900.00', 'location': 'Maitama District, Abuja',
                'state': 'Abuja', 'lat': '9.0833', 'lng': '7.4981'
            }
        ]

        # Generate a dummy 1x1 pixel JPEG
        dummy_image = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00'
            b'\xff\xdb\x00\x43\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x14'
            b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00'
            b'\x3f\xff\xd9'
        )

        for p in properties:
            listing = PropertyListing.objects.create(
                realtor=random.choice(realtor_profiles),
                title=p['title'],
                description=p['desc'],
                price=Decimal(p['price']),
                land_size=Decimal(p['size']),
                location=p['location'],
                state=p['state'],
                latitude=Decimal(p['lat']),
                longitude=Decimal(p['lng']),
                view_count=random.randint(50, 500)
            )
            
            # Attach a mock image
            image_file = SimpleUploadedFile(f"{listing.id}_mock.jpg", dummy_image, content_type="image/jpeg")
            PropertyImage.objects.create(
                property_listing=listing,
                image=image_file,
                is_primary=True,
                caption='Mock image'
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {len(properties)} properties and 2 realtors.'))
