import time
import json
import requests
import urllib.parse
import mimetypes
import os

API_CALL_RETRIES = 3
RETRY_DELAY = 3 #seconds

class APIClient:
    """
    A client for making HTTP requests to a specified API.

    Attributes:
        base_url (str): The base URL for the API.
    """

    def __init__(self, base_url):
        """
        Initialize the APIClient with the base URL.

        Args:
            base_url (str): The base URL for the API.
        """

        self.base_url = base_url

    def make_request(self, endpoint, method='GET', headers=None, json=None, data=None):
        """
        Make an HTTP request to the specified endpoint.

        Args:
            endpoint (str): The API endpoint to call.
            method (str): The HTTP method to use (default 'GET').
            headers (dict): Optional headers to include in the request.
            json (dict): Optional JSON data to include in the request.
            data (dict): Optional form data to include in the request.

        Returns:
            requests.Response: The HTTP response object, or None if the request failed.
        """

        url = f"{self.base_url}{endpoint}"
        for attempt in range(API_CALL_RETRIES):
            try:
                response = requests.request(method, url, headers=headers, json=json, data=data)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                print(f"API request failed (attempt {attempt + 1}/{API_CALL_RETRIES}): {e}")
                time.sleep(RETRY_DELAY)
        print(f"API request failed after {API_CALL_RETRIES} attempts. Please contact support.")
        return None

class BiotClient:
    """
    A client for interacting with the Biot API, handling authentication and health checks.

    Attributes:
        api_client (APIClient): The API client for making requests.
        username (str): The username for authentication.
        password (str): The password for authentication.
        token (str): The authentication token.
    """

    def __init__(self, api_client, username=None, password=None, token=None):
        """
        Initialize the BiotClient with the API client and optional authentication credentials.

        Args:
            api_client (APIClient): The API client for making requests.
            username (str, optional): The username for authentication.
            password (str, optional): The password for authentication.
            token (str, optional): The authentication token.
        """

        self.api_client = api_client
        self.username = username
        self.password = password
        self.token = token

    def login(self):
        """
        Authenticate with the Biot API using the provided username and password.

        Returns:
            str: The authentication token, or None if authentication failed.
        """

        if self.username is not None and self.password is not None:
            response = self.api_client.make_request('/ums/v2/users/login', method='POST', json={"username": self.username, "password": self.password})
            if response:
                self.token = response.json().get("accessJwt", {}).get("token")
            return self.token
        else:
            print("Username and password are required for login.")
            return None

    def is_system_healthy(self, healthcheck_endpoint):
        """
        Check if the system is healthy by calling the health check endpoint.

        Args:
            healthcheck_endpoint (str): The health check endpoint to call.

        Returns:
            bool: True if the system is healthy, False otherwise.
        """

        response = self.api_client.make_request(healthcheck_endpoint, headers={"accept": "application/json"})
        return response.status_code == 200 if response else False

    def get_headers(self):
        """
        Get the headers for authenticated requests.

        Returns:
            dict: The headers including the authorization token.
        """
        return {"accept": "application/json", "authorization": f"Bearer {self.token}"}

class DataManager:
    """
    A manager for handling data operations with the Biot API.

    Attributes:
        biot_client (BiotClient): The Biot client for making authenticated requests.
        healthcheck_endpoints (dict): A dictionary mapping service names to their health check endpoints.
    """

    def __init__(self, biot_client, allow_delete=False):
        """
        Initialize the DataManager with the Biot client.

        Args:
            biot_client (BiotClient): The Biot client for making authenticated requests.
            allow_delete (bool): Whether to allow delete operations
        """

        self.biot_client = biot_client
        self.allow_delete = allow_delete
        self.healthcheck_endpoints = {
            'device': '/device/system/healthCheck',
            'generic-entity': '/generic-entity/system/healthCheck',
            'file': '/file/system/healthCheck'
        }

    def _determine_healthcheck_endpoint(self, endpoint):
        """
        Determine the appropriate health check endpoint based on the provided endpoint.

        Args:
            endpoint (str): The API endpoint for which to determine the health check endpoint.

        Returns:
            str: The determined health check endpoint, or None if no match is found.
        """

        for key in self.healthcheck_endpoints:
            if key in endpoint:
                return self.healthcheck_endpoints[key]
        return None
    
    def _make_authenticated_request(self, endpoint, method='GET', json=None):
        """
        Helper method to make authenticated requests with health check.

        Args:
            endpoint (str): The API endpoint to call.
            method (str): The HTTP method to use (default 'GET').
            json (dict, optional): Optional JSON data to include in the request.

        Returns:
            dict: The JSON response data, or None if the request failed.
        """
        if method.upper() == 'DELETE' and not self.allow_delete:
            print(f"Delete operations are not allowed. Use allow_delete=True to allow DELETE operations")
            return None
        
        headers = self.biot_client.get_headers()
        healthcheck_endpoint = self._determine_healthcheck_endpoint(endpoint)
        if not healthcheck_endpoint:
            print(f"Unknown service for endpoint to run a healthcheck: {endpoint}")
            return None
        if not self.biot_client.is_system_healthy(healthcheck_endpoint):
            print(f"{healthcheck_endpoint.split('/')[1].capitalize()} service is offline. Contact support")
            return None
        
        response = self.biot_client.api_client.make_request(endpoint, method=method, headers=headers, json=json)
        if self.allow_delete:
            allowed_codes = {200, 201, 204}
        else:
            allowed_codes = {200, 201}
        if response and response.status_code in allowed_codes:
            return response
        print(f"API request failed with status code: {response.status_code if response else 'Unknown'}")
        return None
    
    def get_session_by_uuid(self, session_uuid):
        """
        Retrieve a session by its UUID.

        Args:
            session_uuid (str): The UUID of the session to retrieve.

        Returns:
            dict: The session data, or None if the request failed.
        """
        search_request = {"filter": {"session_uuid": {"in": [session_uuid]}}}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        return self._make_authenticated_request(f"/device/v1/devices/usage-sessions?searchRequest={search_request_encoded}")


    def get_ge_by_filter(self, filter):
        """
        Retrieve generic entities by a filter.

        Args:
            filter (dict): A dictionary of field-value pairs to filter the generic entities.

        Returns:
            dict: The filtered generic entities, or None if the request failed.
        
        Notes:
            Filter is a dictionary of {field: value} pairs
            where field is either a custom parameter in the generic entities' template
            or one or more of the built-in parameters _id,_ownerOrganization.id,_name,_templateId,_templateName,_lastModifiedTime,_creationTime 
        """

        search_request = {"filter": filter}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        return self._make_authenticated_request(f"/generic-entity/v1/generic-entities?searchRequest={search_request_encoded}").json()
    
    def get_usage_session_by_id(self, session_id, device_id):
        """
        Retrieve a usage session by its ID and the associated device ID.

        Args:
            session_id (str): The ID of the usage session to retrieve.
            device_id (str): The ID of the device associated with the session.

        Returns:
            dict: The usage session data, or None if the request failed.
        """
        return self._make_authenticated_request(f"/device/v1/devices/{device_id}/usage-sessions/{session_id}").json()
    
    def get_usage_session_by_filter(self, filter):
        """
        Retrieve usage sessions by a filter.

        Args:
            filter (dict): A dictionary of field-value pairs to filter the usage sessions.

        Returns:
            dict: The filtered usage sessions, or None if the request failed.

        Notes:
            Filter is a dictionary of {field: value} pairs
            where field is either a custom parameter in the usage sessions' template
            or one or more of the built-in parameters _id,_ownerOrganization.id,_name,_templateId,_templateName,_lastModifiedTime,_creationTime
        """
        search_request = {"filter": filter}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        return self._make_authenticated_request(f"/device/v1/devices/usage-sessions?searchRequest={search_request_encoded}").json()
    
    def update_usage_session(self, usage_session_id, device_id, update_data):
        """
        Update a usage session with the given data.

        Args:
            usage_session_id (str): The ID of the usage session to update.
            device_id (str): The ID of the device associated with the session.
            update_data (dict): The data to update the session with.

        Returns:
            dict: The updated session data, or None if the request failed.
        """

        return self._make_authenticated_request(f"/device/v1/devices/{device_id}/usage-sessions/{usage_session_id}", 
                                                            method="patch",
                                                            json=update_data)

    def get_file_signedurl_by_fileid(self, file_id):
        """
        Retrieve a signed URL for a file by its ID.

        Args:
            file_id (str): The ID of the file to retrieve the signed URL for.

        Returns:
            str: The signed URL, or None if the request failed.
        """

        response = self._make_authenticated_request(f"/file/v1/files/{file_id}/download")
        return response.json().get('signedUrl') if response else None
        
    def create_generic_entity_by_template_name(self, template_name, data):
        """
        Create a generic entity using a template name and data.

        Args:
            template_name (str): The name of the template to use.
            data (dict): The data to create the generic entity with.

        Returns:
            dict: The created generic entity, or None if the request failed.
        """

        return self._make_authenticated_request(f"/generic-entity/v1/generic-entities/templates/{template_name}", 
                                                            method='POST', json=data).json()

    def update_generic_entity_by_id(self, entity_id, updated_data):
        """
        Update a generic entity with the given data.

        Args:
            entity_id (str): The ID of the generic entity to update.
            updated_data (dict): The data to update the generic entity with.

        Returns:
            dict: The updated generic entity, or None if the request failed.
        """

        return self._make_authenticated_request(f"/generic-entity/v1/generic-entities/{entity_id}", json=updated_data, method='PATCH')

    def delete_generic_entity_by_id(self, entity_id):
        """
        Delete a generic entity by its ID.

        Args:
            entity_id (str): The ID of the generic entity to delete.

        Returns:
            dict: The response from the delete request, or None if the request failed.
        """

        return self._make_authenticated_request(f"/generic-entity/v1/generic-entities/{entity_id}", method='DELETE')
    
    def _create_file_and_get_upload_url(self, file_name, mime_type):
        response= self._make_authenticated_request(f"/file/v1/files/upload", method="POST", json={"name": file_name, "mimeType": mime_type})
        return response.json() if response else None
    
    def upload_file(self, file_path):
        # Extract file name and MIME type
        file_name = os.path.basename(file_path)
        mime_type = mimetypes.guess_type(file_path)[0]
        if mime_type is None:
            # assume it's binary
            mime_type = 'application/octet-stream'
        file_info = self._create_file_and_get_upload_url(file_name, mime_type)

        if file_info:
            upload_url = file_info.get('signedUrl')
            if upload_url:
                with open(file_path, 'rb') as file:
                    response = requests.put(upload_url, data=file)
                    if response.status_code != 200:
                        return None
            return file_info
        else:
            return None
    
    def upload_file_from_ram(self, data, file_name):
        mime_type = 'application/octet-stream'
        file_info = self._create_file_and_get_upload_url(file_name, mime_type)
        if file_info:
            upload_url = file_info.get('signedUrl')
            if upload_url:
                response = requests.put(upload_url, data=data)
                if response.status_code != 200:
                    return None
            return file_info
        else:
            return None
    