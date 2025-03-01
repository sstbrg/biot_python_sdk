import time
import json
import requests
import urllib.parse
import os
from biot_python_sdk.multipart import *
from biot_python_sdk.BioT_API_URLS import *
from datetime import datetime

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
        self.verbose = False

    def make_request(self, endpoint, method='GET', headers=None, json=None, data=ModuleNotFoundError):
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
                if self.verbose:
                    print(f"API request: {method} {url}")
                    print(f"Headers: {headers}")
                    print(f"JSON: {json}")
                    print(f"Data: {data}")
                    print(f"Response: {response.status_code} {response.text}")
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                print(f"API request failed (attempt {attempt + 1}/{API_CALL_RETRIES}): {e}")
                print(f"Response: {response.status_code} {response.text}")
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
            'device': DEVICES_HEALTHCHECK_URL,
            'generic-entity': GENERIC_ENTITES_HEALTHCHECK_URL,
            'file': FILE_HEALTHCHECK_URL,
            'dms': DMS_HEALTHCHECK_ENDPOINT,
            'settings' : SETTINGS_HEALTHCHECK_ENDPOINT,
            'organization' : ORGANIZATION_HEALTHCHECK_URL
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
        print(f"Response: {response.text if response else 'No response'}")
        return None

    def _get_template_id_from_name(self,template_name):
        if type(template_name)==str:
            filter_type = 'eq'
        elif type(template_name) is list:
            filter_type = 'in'
        else:
            print('Template name is not str or list')
            return None
        search_request = {"filter": {"name": {f"{filter_type}": template_name}}}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        response =  self._make_authenticated_request(f"{TEMPLATES_SUB_URL}?searchRequest={search_request_encoded}")
        template_id_list = []
        templates_data = response.json()['data']
        if type(template_name)==str:
            return templates_data[0]['id']
        else:
            for templte in response.json()['data']:
                template_id_list.append(templte['id'])
            return template_id_list

    def _get_org_id_from_name(self,org_name):
        if type(org_name)==str:
            filter_type = 'eq'
        elif type(org_name) is list:
            filter_type = 'in'
        else:
            print('Template name is not str or list')
            return None
        search_request = {"filter": {"_name": {f"{filter_type}": org_name}}}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        response =  self._make_authenticated_request(f"{ORGANIZATION_URL}?searchRequest={search_request_encoded}")
        org_id_list = []
        orgs_data = response.json()['data']
        if type(org_name)==str:
            if len(orgs_data)>1:
                raise Exception('More than one organization with the given name')
            return orgs_data[0]['_id']
        else:
            for templte in response.json()['data']:
                org_id_list.append(templte['id'])
            return org_id_list

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



    def get_ge_by_filter(self, filter, page=0, limit=100):
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

        search_request = {"filter": filter, "page": page, "limit": limit}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        response = self._make_authenticated_request(f"/generic-entity/v1/generic-entities?searchRequest={search_request_encoded}")
        if response.status_code == 200:
            return response.json()
        else:
            return None
    
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
    
    def create_usage_session(self, device_id, session_template_name, session_data):
        """
        Create a new usage session for the given device.
        """
        return self._make_authenticated_request(f"/device/v1/devices/{device_id}/usage-sessions/usage-type/{session_template_name}", method="post", json=session_data)
    
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
        """
        Create a file on the Biot API and retrieve a signed URL for uploading the file data.

        Args:
            file_name (str): The name of the file to create.
            mime_type (str): The MIME type of the file.

        Returns:
            dict: The file information returned by the API, or None if the request failed.
        """
        if " " in file_name:
            print("Warning: File name contains spaces. Replacing spaces with underscores.")
            file_name_to_upload = file_name.replace(" ", "_")
        else:
            file_name_to_upload = file_name

        response = self._make_authenticated_request(f"/file/v1/files/upload", method="POST", json={"name": file_name_to_upload, "mimeType": mime_type})
        return response.json() if response else None
    
    def upload_file(self, file_path):
        """
        Upload a file to the Biot API.

        This function creates a file on the Biot API with the given name and MIME type,
        retrieves a signed URL for uploading the file data, and then uploads the file to the signed URL.

        Args:
            file_path (str): The path to the file to upload.

        Returns:
            dict: The file information returned by the API, or None if the upload failed.
        """
        # Extract file name and MIME type
        file_name = os.path.basename(file_path)
        mime_type = get_mime_type(file_path)
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
        """
        Upload a file from memory to the Biot API.

        This function creates a file on the Biot API with the given name and MIME type,
        retrieves a signed URL for uploading the file data, and then uploads the data to the signed URL.

        Args:
            data (bytes): The data to upload.
            file_name (str): The name to use for the uploaded file.

        Returns:
            dict: The file information returned by the API, or None if the upload failed.
        """

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
          
    def upload_multipart(self, file_path, file_name, chunk_size=1024 * 1024 * 5):
        """
        Upload a file in multipart format to the Biot API.

        This function splits the file into parts, uploads each part to the API, and then notifies the API
        that the upload is complete. The API will then reassemble the parts into a single file.

        Args:
            file_path (str): The path to the file to upload.
            file_name (str): The name to use for the uploaded file.
            chunk_size (int, optional): The size of each part to split the file into. Defaults to 5MB.

        Returns:
            str: The ID of the uploaded file.

        Raises:
            ValueError: If the response from the API does not contain the 'signedUrls' key.
        """
        if "_" in file_name and " " in file_path:
            print("Warning: File name contains underscores and spaces. Replacing spaces with underscores.")
            file_name_to_upload = file_name.replace(" ", "_")
        else:
            file_name_to_upload = file_name

        print(f"Uploading file in multipart: {file_path}")
        split_file(file_path, chunk_size)
        print("File split into parts.")
        parts = get_file_parts()
        mime_type = get_mime_type(file_path)
        json = {
            "name": file_name_to_upload,
            "mimeType": mime_type,
            "parts": len(parts)
        }
        response = self._make_authenticated_request(f"/file/v1/files/upload/parts/", method="POST", json=json)
        upload_info = response.json()
        if 'signedUrls' not in upload_info:
            raise ValueError("Response does not contain 'signedUrls' key")
        signed_urls = {url_info["partNumber"]: url_info["signedUrl"] for url_info in upload_info["signedUrls"]}
        file_id = upload_info["id"]
        
        print("Parts uploaded. Signed URLs:")
        for part_number, signed_url in signed_urls.items():
            print(f"Part {part_number}: {signed_url}")

        etags = []
        for i, part in enumerate(parts):
            part_number = i + 1
            etag = upload_part(signed_urls[part_number], part)
            etags.append(etag)

        # notify backend on upload completion so it'll reunite the parts into a single file
        etags_to_notify = [{"partNumber": i + 1, "etag": etag} for i, etag in enumerate(etags)]
        print("ETags:", ', '.join(f"Part {i + 1}: {etag}" for i, etag in enumerate(etags)))
        response = self._make_authenticated_request(f"/file/v1/files/upload/parts/{file_id}/complete", method="POST", json={"parts": etags_to_notify})
        delete_file_parts()  
        print("Multipart File Upload Completed", response.json())
        return file_id

    def refresh_token(self, old_token):
        body = {'refreshToken': old_token}
        return self._make_authenticated_request('/ums/v2/users/token/refresh', method='POST', json=body)
    
    def fetch_template_by_id(self, template_id):
        """
        Fetches a template by its ID
        """
        # Make the API call to fetch the template by its ID
        response = self._make_authenticated_request(f"/settings/v1/templates/{template_id}", method="GET")
        if response:
            return response.json()
        else:
            return None
        

    def fetch_template_by_filter(self, filter):
        """
        Fetches templates based on a filter

        Parameters
        ----------
        filter : dict
            the filter to be used for fetching templates

        Returns
        -------
        list
            the list of templates that match the filter
        """
        # Make the API call to fetch templates based on the filter
        search_request = {"filter": filter}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        response = self._make_authenticated_request(f"/settings/v1/templates?searchRequest={search_request_encoded}", method="GET")

        if response:
            return response.json()
        else:
            return None
            
    def update_template(self, template_id, template):
        """
        Updates a template
        Parameters
        ----------
        template_id : str
            the id of the template to be updated
        template : dict
           the template to be updated
           Returns
        -------
        dict
           the updated template
        """

        # since this is a PUT method, ensure all existing template keys are inside the template dict
        existing_template = self.fetch_template_by_id(template_id)
        for key in existing_template:
            if key not in template:
                raise ValueError(f"Missing key {key} in template")
            
            # check if there are characters that are not lowercase or underscore or number and check that it starts with a lowercase letter
            if not re.match(r'^[a-z][a-z0-9_]*$', key):
                raise ValueError(f"Invalid key {key} in template. Keys must be lowercase, start with a letter, and contain only letters, numbers, and underscores.")
            
            # check that all keys and values are strings
            if not isinstance(key, str) or not isinstance(template[key], str):
                raise ValueError(f"Invalid key {key} in template. Keys and values must be strings.")
            # check that all keys and values are not empty
            if key == "" or template[key] == "":
                raise ValueError(f"Invalid key {key} in template. Keys and values must not be empty.")
            
            # check that all keys and values are not longer than 32 characters
            if len(key) > 32 or len(template[key]) > 32:
                raise ValueError(f"Invalid key {key} in template. Keys and values must not be longer than 32 characters.")
            
            # check that all keys and values are not shorter than 2 character
            if len(key) < 2 or len(template[key]) < 2:
                raise ValueError(f"Invalid key {key} in template. Keys and values must not be shorter than 2 characters.")
            

        # Make the API call to update the template
        response = self._make_authenticated_request(f"/settings/v1/templates/{template_id}", method="PUT", json=template)

        # Return the response   
        if response:
            return response.json()
        else:
            return None