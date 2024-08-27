import time
import json
import requests
import urllib.parse
import mimetypes
import os

from datetime import datetime
API_CALL_RETRIES = 3
RETRY_DELAY = 3 #seconds
from BioT_API_URLS import *
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
            'file': '/file/system/healthCheck',
            'dms': DMS_HEALTHCHECK_ENDPOINT,
            'settings' : SETTINGS_HEALTHCHECK_ENDPOINT
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


    def export_snapshot_by_entities(self,report_name,ge_template_names_to_filt, save_devices=False,start_date = "2024-05-01T09:03:33Z"):

        """
                Generates and exports a snapshot of data entities based on specified templates and a date range.

                Parameters:
                - report_name (str): The name of the report to be generated.
                - ge_template_names_to_filt (list): A list of template names used to filter the generic entities.
                - save_devices (bool, optional): A flag to indicate whether device data should be included in the report. Defaults to False.
                - start_date (str, optional): The start date for the data filter in ISO 8601 format. Defaults to "2024-05-01T09:03:33Z".

                Returns:
                - response: The response from the server after making the authenticated request to create the data report.

                Usage:
                This method is used to generate and export a snapshot of the configuration data for various entities and optionally devices, within a specified date range.
        """
        ge_template_id_to_filt = self._get_template_id_from_name(ge_template_names_to_filt)
        today_date=  datetime.now().isoformat()
        queries=[]
        query=dict()
        filter_dict =dict()
        filter_dict['_templateId']={'in':ge_template_id_to_filt}
        filter_dict['_creationTime'] = {"in": [],"from": start_date,"to": today_date,"notIn": [],"filter": {}}
        query["dataType"] = "generic-entity"
        query["filter"] = filter_dict
        queries.append(query)
        if save_devices:
            device_template_id =self._get_template_id_from_name('androidgateway')
            query = dict()
            filter_dict = dict()
            filter_dict['_templateId'] = {'eq': device_template_id}
            filter_dict['_creationTime'] = {"in": [], "from": start_date, "to": today_date, "notIn": [], "filter": {}}
            query["dataType"] = "device"
            query["filter"] = filter_dict
            queries.append(query)

        body_dict =dict()
        body_dict['outputMetadata']={'exportFormat' :'JSON'}
        body_dict['queries'] = queries
        body_dict['name'] = report_name
        response = self._make_authenticated_request(CREATE_DATA_REPORT_URL, method="POST", json=body_dict)
        return response


    def export_full_configuration_snapshot(self, report_name, start_date="2024-05-01T09:03:33Z"):
        """ A wrapper function for 'export_snapshot_by_entities' above for saving all entites used for configuration """
        ge_template_names_to_filt = ['sensor','patch','montage_configuration','channel']
        return self.export_snapshot_by_entities( report_name, ge_template_names_to_filt,save_devices=True, start_date = start_date)

    def get_report_file_by_name(self,report_name):
        """
                Retrieves the report file by its name.

                Parameters:
                - report_name (str or list): The name(s) of the report(s) to be retrieved.

                Returns:
                - reports_data_dict (dict): A dictionary containing the report data, where the keys are report types (e.g., 'device', 'generic-entity') and the values are the report data in JSON format.
        """
        if type(report_name)==str:
            filter_type = 'eq'
        elif type(report_name) is list:
            filter_type = 'in'
        else:
            print('Template name is not str or list')
            return None
        search_request = {"filter": {"name": {f"{filter_type}": report_name}}}
        search_request_encoded = urllib.parse.quote(json.dumps(search_request))
        response = self._make_authenticated_request(f"{GET_DATA_REPORT_URL}?searchRequest={search_request_encoded}")
        reports_data_dict = dict()
        if response:
            reports=response.json()['data']
            if len(reports)>1:
                raise Exception('More Than One report with this name.')
            for report in reports:
                for key in report['fileOutput']['filesLocation'].keys():
                    report_paths=report['fileOutput']['filesLocation'][key]['paths']
                    for path in report_paths:
                        response=requests.get(path)
                        if response.status_code==200:
                            reports_data_dict[key] = response.json()
            return reports_data_dict


    def post_full_configuration_report(self,report_dict):
        """
               Posts the full configuration data (retrieved from a report) to the server.

               Parameters:
               - report_dict (dict): The dictionary containing the report data to be posted, typically retrieved from the `get_report_file_by_name` method.

               Returns:
               - None. (Prints the response from the server for each posted entity.)

               Usage:
               This method is used to post a full configuration report back to the server. It handles both device and
               generic entity data. It first checks if there are 'device' entities in the report, then posts them. After
               that, it processes 'generic-entity' data in a specific order: 'sensor', 'patch', 'montage_configuration',
               and 'channel'.
        """
        if 'device' in report_dict.keys():
            self.post_report_json(report_dict['device'], template_type='device')
        if 'generic-entity' in report_dict.keys():
            ge_report= report_dict['generic-entity']
            ge_post_order = ('sensor','patch','montage_configuration','channel')
            for template_name in ge_post_order:
                current_template_entities = [ge for ge in ge_report if ge['_template']['name']==template_name]
                self.post_report_json(current_template_entities, template_type='generic-entity')


    def post_report_json(self,report_data,template_type):
        """
                Posts a single report (either device or generic entity) in JSON format to the server.

                Parameters:
                - report_data (list): The list of entities to be posted, extracted from the report.
                - template_type (str): The type of template ('device' or 'generic-entity') that is being posted.

                Returns:
                - None. (Prints the response from the server for each posted entity.)

                Usage:
                This method is a helper function used by `post_full_configuration_report` to post individual entities to
                the server, either as devices or generic entities. Depending on the `template_type`, it handles the
                JSON structure differently for devices and generic entities.
        """
        post_json = dict()
        for entity in report_data:
            for key in entity.keys():
                post_json['_templateId'] = entity['_template']['id']
                post_json['_ownerOrganization'] = {'id':entity['_ownerOrganization']['id']}
                if template_type=='device':
                    post_json['_id'] = entity['_id']
                    post_json['_configuration']=entity['_configuration']
                    post_json['_timezone'] = entity['_timezone']
                else:
                    post_json['_name'] = entity['_name']
                if key[0]!='_': # not built in attribute
                    if type(entity[key])==dict:
                        post_json[key] = {'id':entity[key]['id']}
                    else:
                        post_json[key] = entity[key]
            if template_type=='device':
                response = self._make_authenticated_request(endpoint=DEVICES_URL, method='POST', json=post_json)
                print(response)
            if template_type == 'generic-entity':
                response = self._make_authenticated_request(endpoint=GENERIC_ENTITES_URL,method='POST',json=post_json)
                print(response)




    