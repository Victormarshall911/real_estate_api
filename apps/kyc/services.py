"""
Dojah KYC API service wrapper.
Handles BVN and NIN verification calls.
"""
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DOJAH_SANDBOX_URL = 'https://sandbox.dojah.io'
DOJAH_PRODUCTION_URL = 'https://api.dojah.io'

# Nigerian BVN and NIN are exactly 11 digits
NIN_BVN_PATTERN = re.compile(r'^\d{11}$')


class DojahService:
    """
    Service class for interacting with the Dojah KYC API.
    Uses sandbox URL in development, production endpoint otherwise.
    """

    def __init__(self):
        self.app_id = getattr(settings, 'DOJAH_APP_ID', '')
        self.secret_key = getattr(settings, 'DOJAH_SECRET_KEY', '')
        self.base_url = (
            DOJAH_SANDBOX_URL
            if getattr(settings, 'DEBUG', True)
            else DOJAH_PRODUCTION_URL
        )
        self.headers = {
            'AppId': self.app_id,
            'Authorization': self.secret_key,
            'Content-Type': 'application/json',
        }

    def _is_configured(self):
        """Check if Dojah credentials are set."""
        return bool(self.app_id and self.secret_key)

    def _validate_format(self, id_number, id_type='BVN/NIN'):
        """
        Validate that the number is exactly 11 digits.
        Returns (is_valid, error_message).
        """
        cleaned = str(id_number).strip()
        if not NIN_BVN_PATTERN.match(cleaned):
            return False, f'Invalid {id_type}: must be exactly 11 digits with no spaces or letters.'
        return True, None

    def verify_bvn(self, bvn, customer_reference=''):
        """
        Verify a Bank Verification Number (BVN).
        Returns dict with 'success' bool and 'data' or 'error'.
        """
        cleaned = str(bvn).strip().replace('-', '').replace(' ', '')

        # Validate format first (always, regardless of credentials)
        is_valid, fmt_error = self._validate_format(cleaned, 'BVN')
        if not is_valid:
            return {'success': False, 'error': fmt_error}

        if not self._is_configured():
            logger.warning('Dojah BVN verification attempted but API credentials are not configured.')
            return {
                'success': False,
                'error': (
                    'Identity verification service is not yet configured. '
                    'Please contact support to complete KYC verification.'
                ),
            }

        try:
            response = requests.get(
                f'{self.base_url}/api/v1/kyc/bvn',
                headers=self.headers,
                params={
                    'bvn': cleaned,
                    'customer_reference': customer_reference,
                },
                timeout=30,
            )
            data = response.json()
            if response.status_code == 200:
                return {'success': True, 'data': data}
            error_msg = data.get('error', '') or data.get('message', 'BVN verification failed. Please check the number and try again.')
            return {'success': False, 'error': error_msg}
        except requests.RequestException as e:
            logger.error(f'Dojah BVN verification failed: {e}')
            return {'success': False, 'error': 'Verification service is temporarily unavailable. Please try again shortly.'}

    def verify_nin(self, nin, customer_reference=''):
        """
        Verify a National Identification Number (NIN).
        Returns dict with 'success' bool and 'data' or 'error'.
        """
        cleaned = str(nin).strip().replace('-', '').replace(' ', '')

        # Validate format first (always, regardless of credentials)
        is_valid, fmt_error = self._validate_format(cleaned, 'NIN')
        if not is_valid:
            return {'success': False, 'error': fmt_error}

        if not self._is_configured():
            logger.warning('Dojah NIN verification attempted but API credentials are not configured.')
            return {
                'success': False,
                'error': (
                    'Identity verification service is not yet configured. '
                    'Please contact support to complete KYC verification.'
                ),
            }

        try:
            response = requests.get(
                f'{self.base_url}/api/v1/kyc/nin',
                headers=self.headers,
                params={
                    'nin': cleaned,
                    'customer_reference': customer_reference,
                },
                timeout=30,
            )
            data = response.json()
            if response.status_code == 200:
                return {'success': True, 'data': data}
            error_msg = data.get('error', '') or data.get('message', 'NIN verification failed. Please check the number and try again.')
            return {'success': False, 'error': error_msg}
        except requests.RequestException as e:
            logger.error(f'Dojah NIN verification failed: {e}')
            return {'success': False, 'error': 'Verification service is temporarily unavailable. Please try again shortly.'}
