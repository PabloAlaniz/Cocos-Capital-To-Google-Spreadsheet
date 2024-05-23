import requests
import time
import exctract_2fa_from_gmail
from log_config import get_logger
import datetime
import json
from config import GMAIL_USER, GMAIL_APP_PASS
logger = get_logger(__name__)

BASE_URL = 'https://api.cocos.capital'

class CocosCapital:

    def __init__(self, user, password):
        self.user = user
        self.password = password
        self.account_id = None
        self.token = None
        self.headers = self.basic_headers()
        self.login()

    def login(self):
        """
        Handles the login process by authenticating and then initializing headers and user data.
        Includes handling for two-factor authentication.
        """
        # Authenticate and get the token.
        self.token = self.authenticate(self.user, self.password)
        if self.token:
            # Update headers with the new token.
            self.update_token_in_headers(self.token)

            # Handle two-factor authentication.
            self.handle_two_factor_authentication()

            # Initialize user data.
            self.initialize_user_data()

            if self.account_id:
                # Update headers with the new account ID after all authentication steps.
                self.update_account_id_in_headers(self.account_id)
        else:
            logger.error("Authentication failed, unable to proceed without token.")

    def authenticate(self, username, password):
        """
        Authenticates the user and returns a token.
        """
        data = {'email': username, 'password': password, 'gotrue_meta_security': {}}
        try:
            response = requests.post(f'{BASE_URL}/auth/v1/token?grant_type=password', headers=self.headers, json=data)
            response.raise_for_status()
            logger.info("Successful login.")
            return response.json()['access_token']
        except Exception as e:
            logger.error("Login error: %s", e)
            return None

    def handle_two_factor_authentication(self):
        """
        Handle the process of two-factor authentication.
        """
        channel_id = self.get_two_factors_channel()
        if channel_id:
            code = self.get_two_factor_code(channel_id)
            self.verify_two_factor_code(channel_id, code)

    def get_two_factors_channel(self):
        """
        Get the default channel for two-factor authentication.
        """
        url = f"{BASE_URL}/auth/v1/factors/default"
        response = requests.get(url, headers=self.headers)
        try:
            response.raise_for_status()
            return response.json()['id']
        except Exception as e:
            logger.error("Failed to obtain 2FA channel: %s", e)
            return None

    def verify_two_factor_code(self, channel_id, code):
        """
        Verify the two-factor authentication code with the server.
        """
        url = f"{BASE_URL}/auth/v1/factors/{channel_id}/verify"
        payload = {"challenge_id": channel_id, "code": code}
        response = requests.post(url, headers=self.headers, json=payload)
        try:
            response.raise_for_status()
            self.token = response.json()['access_token']

            # Actualizo el token ya que cambia en cada verificación de 2FA.
            self.update_token_in_headers(self.token)
        except Exception as e:
            logger.error("Failed to verify 2FA code: %s", e)
            self.token = None

    def initialize_user_data(self):
        """
        Load or refresh user-specific data post-login, like retrieving the account ID.
        """
        my_data = self.get_my_information()
        if 'id_accounts' in my_data and my_data['id_accounts']:
            self.account_id = my_data['id_accounts'][0]
            self.update_account_id_in_headers(self.account_id)  # Update the headers with the new account ID
        else:
            logger.error("Failed to retrieve user account information.")

    def basic_headers(self):
        basic_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'content-type': 'application/json;charset=UTF-8',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Mobile Safari/537.36',
            'x-client-info': 'supabase-js/1.35.4',
            'sec-fetch-site': 'same-site',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'sec-ch-ua': '"Google Chrome";v="93", " Not;A Brand";v="99", "Chromium";v="93"',
            'sec-ch-ua-mobile': '?1',
            'Referer': 'https://app.cocos.capital/',
            'Origin': 'https://app.cocos.capital',
            'Priority': 'u=1, i'
        }
        return basic_headers

    def update_headers(self):
        """
        Update headers with the current authentication token and account ID.
        This method uses specific update functions to ensure each part is updated correctly.
        """
        # Asigna los headers básicos primero para asegurarse de que siempre están presentes.
        self.headers = self.basic_headers()

        if self.token:
            self.update_token_in_headers(self.token)
        if self.account_id:
            self.update_account_id_in_headers(self.account_id)

    def update_token_in_headers(self, token):
        """
        Update the authorization token in headers.
        """
        if token:
            self.token = token
            self.headers['authorization'] = f'Bearer {token}'
        else:
            logger.warning("No valid token provided.")

    def update_account_id_in_headers(self, account_id):
        """
        Update the account ID in headers.
        """
        if account_id:
            self.account_id = account_id
            # Convert account_id to string before adding it to headers
            self.headers['x-account-id'] = str(account_id)
        else:
            logger.warning("No valid account ID provided.")

    def get_api_key(self):
        return 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogImFub24iLAogICJpc3MiOiAic3VwYWJhc2UiLAogICJpYXQiOiAxNzA0NjgyODAwLAogICJleHAiOiAxODYyNTM1NjAwCn0.f0w62k0q0eyyGBDkAP7vUUEg_Ingb9YbOlhsGCC4R3c'

    def get_two_factor_code(self, challenge_channel):
        url = f"{BASE_URL}/auth/v1/factors/{challenge_channel}/challenge"
        payload = {
            "expires_at": 123,
            "id": challenge_channel,
        }
        r = requests.post(url, headers=self.headers, json=payload)

        time.sleep(10)
        code = exctract_2fa_from_gmail.obtener_codigo_2FA(GMAIL_USER, GMAIL_APP_PASS, 'no-reply@cocos.capital')
        logger.info("\nCódigo 2FA: %s", code)
        return code

    def add_device_as_trusted(self, device_id):
        url = f'{BASE_URL}/auth/v1/factors/devices'
        payload = {"deviceId": device_id}
        '3fcb6022-55f1-4234-9180-3baa9ce271ba'

    def get_account_total(self):
        url = f'{BASE_URL}/api/v1/wallet/portfolio'
        response = requests.get(url, headers=self.headers)
        return response.json()['total']

    def get_transfers(self, date_from, date_to=None):
        if date_to is None:
            date_to = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            url = f'{BASE_URL}/api/v1/transfers?date_from={date_from}&date_to={date_to}'
            response = requests.get(url, headers=self.headers)
            logger.info("\nBuscando movimientos históricos desde %s hasta el %s", date_from, date_to)
            transfers = response.json()
            return transfers
        except Exception as e:
            logger.error("\n Fallo al traer los movimientos históricos: %s", e)

    def get_ticket_price(self, ticket):
        data = requests.get(f'{BASE_URL}/api/v1/markets/tickers/{ticket}?segment=C', headers=self.headers)
        return data.json()

    def get_my_information(self):
        """
        Fetches user information from the API.
        """
        url = f'{BASE_URL}/api/v1/users/me'
        response = requests.get(url, headers=self.headers)
        try:
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to fetch user information: %s", e)
            return {}

    def debug_verbose(self, url, response, payload):
        logger.info("\n \nSolicitando factores de autenticación...")
        logger.info("URL: %s", url)
        logger.info("\n \n")

        logger.info("Payload:")
        logger.info(json.dumps(payload, indent=2))  # Asegúrate de que payload es serializable.
        logger.info("\n \n")

        logger.info("Response:")
        try:
            logger.info(response.json())
        except ValueError:
            logger.error("Failed to parse JSON from response")
        logger.info("\n \n")

        logger.info("Send Headers:")
        for h in self.headers:
            logger.info(f"{h}: {self.headers[h]}")
        logger.info("\n \n")

        logger.info("Response Headers:")
        for header in response.headers:
            logger.info(f"{header}: {response.headers[header]}")
        logger.info("\n \n")