"""
Dojah KYC API service wrapper.
Handles BVN and NIN verification calls.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

DOJAH_SANDBOX_URL = 'https://sandbox.dojah.io'
DOJAH_PRODUCTION_URL = 'https://api.dojah.io'


class DojahService:
    """
    Service class for interacting with the Dojah KYC API.
    Uses sandbox in development, production endpoint otherwise.
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

    def verify_bvn(self, bvn, customer_reference=''):
        """
        Verify a Bank Verification Number.
        Returns dict with 'success' bool and 'data' or 'error'.
        """
        if not self._is_configured():
            return {'success': False, 'error': 'KYC service is not configured. Live API keys are required.'}

        try:
            response = requests.get(
                f'{self.base_url}/api/v1/kyc/bvn',
                headers=self.headers,
                params={
                    'bvn': bvn,
                    'customer_reference': customer_reference,
                },
                timeout=30,
            )
            data = response.json()
            if response.status_code == 200:
                return {'success': True, 'data': data}
            return {'success': False, 'error': data.get('error', 'Verification failed.')}
        except requests.RequestException as e:
            logger.error(f'Dojah BVN verification failed: {e}')
            return {'success': False, 'error': 'KYC service temporarily unavailable.'}

    def verify_nin(self, nin, customer_reference=''):
        """
        Verify a National Identification Number.
        Returns dict with 'success' bool and 'data' or 'error'.
        """
        if not self._is_configured():
            return {'success': False, 'error': 'KYC service is not configured. Live API keys are required.'}

        try:
            response = requests.get(
                f'{self.base_url}/api/v1/kyc/nin',
                headers=self.headers,
                params={
                    'nin': nin,
                    'customer_reference': customer_reference,
                },
                timeout=30,
            )
            data = response.json()
            if response.status_code == 200:
                return {'success': True, 'data': data}
            return {'success': False, 'error': data.get('error', 'Verification failed.')}
        except requests.RequestException as e:
            logger.error(f'Dojah NIN verification failed: {e}')
            return {'success': False, 'error': 'KYC service temporarily unavailable.'}

    def _mock_success(self, verification_type, id_number):
        """
        Returns a mock success response when Dojah credentials are not configured.
        Used for local development only.
        """
        logger.info(f'Dojah not configured — returning mock KYC success for {verification_type}')
        return {
            'success': True,
            'data': {
                'entity': {
                    'first_name': 'Test',
                    'last_name': 'User',
                    verification_type: id_number,
                },
                'mock': True,
            },
        }
