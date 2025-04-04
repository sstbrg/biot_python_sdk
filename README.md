# Badges
![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/sstbrg/biot_python_sdk?utm_source=oss&utm_medium=github&utm_campaign=sstbrg%2Fbiot_python_sdk&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

# Biot Python SDK Documentation

This document provides an overview of the Biot Python SDK, a collection of classes and methods for interacting with the Biot API. The SDK includes functionality for making authenticated requests, handling data operations, and managing files.

## Table of Contents

- [APIClient](#apiclient)
- [BiotClient](#biotclient)
- [DataManager](#datamanager)
- [ReportManager](#reportmanager)

## APIClient

The `APIClient` class is responsible for making HTTP requests to a specified API. It provides a `make_request` method that can be used to send GET, POST, PUT, PATCH, and DELETE requests to the API. The method handles retries and delays in case of request failures.

### Attributes

- `base_url` (str): The base URL for the API.

### Methods

- `__init__(self, base_url)`: Initializes the APIClient with the base URL.
- `make_request(self, endpoint, method='GET', headers=None, json=None, data=None)`: Makes an HTTP request to the specified endpoint.

## BiotClient

The `BiotClient` class is a client for interacting with the Biot API, handling authentication and health checks. It uses an instance of the `APIClient` class to make requests to the API.

### Attributes

- `api_client` (APIClient): The API client for making requests.
- `username` (str): The username for authentication.
- `password` (str): The password for authentication.
- `token` (str): The authentication token.

### Methods

- `__init__(self, api_client, username=None, password=None, token=None)`: Initializes the BiotClient with the API client and optional authentication credentials.
- `login(self)`: Authenticates with the Biot API using the provided username and password.
- `is_system_healthy(self, healthcheck_endpoint)`: Checks if the system is healthy by calling the health check endpoint.
- `get_headers(self)`: Gets the headers for authenticated requests.

## DataManager

The `DataManager` class is a manager for handling data operations with the Biot API. It uses an instance of the `BiotClient` class to make authenticated requests to the API.

### Attributes

- `biot_client` (BiotClient): The Biot client for making authenticated requests.
- `allow_delete` (bool): Whether to allow delete operations.
- `healthcheck_endpoints` (dict): A dictionary mapping service names to their health check endpoints.

### Methods

- `__init__(self, biot_client, allow_delete=False)`: Initializes the DataManager with the Biot client.
- `_determine_healthcheck_endpoint(self, endpoint)`: Determines the appropriate health check endpoint based on the provided endpoint.
- `_make_authenticated_request(self, endpoint, method='GET', json=None)`: Makes authenticated requests with health check.
- `get_session_by_uuid(self, session_uuid)`: Retrieves a session by its UUID.
- `get_ge_by_filter(self, filter)`: Retrieves generic entities by a filter.
- `get_usage_session_by_id(self, session_id, device_id)`: Retrieves a usage session by its ID and the associated device ID.
- `get_usage_session_by_filter(self, filter)`: Retrieves usage sessions by a filter.
- `update_usage_session(self, usage_session_id, device_id, update_data)`: Updates a usage session with the given data.
- `get_file_signedurl_by_fileid(self, file_id)`: Retrieves a signed URL for a file by its ID.
- `create_generic_entity_by_template_name(self, template_name, data)`: Creates a generic entity using a template name and data.
- `update_generic_entity_by_id(self, entity_id, updated_data)`: Updates a generic entity with the given data.
- `delete_generic_entity_by_id(self, entity_id)`: Deletes a generic entity by its ID.
- `_create_file_and_get_upload_url(self, file_name, mime_type)`: Creates a file on the Biot API and retrieves a signed URL for uploading the file data.
- `upload_file(self, file_path)`: Uploads a file to the Biot API.
- `upload_file_from_ram(self, data, file_name)`: Uploads a file from memory to the Biot API.
- `upload_multipart(self, file_path, file_name, chunk_size=1024 * 1024 * 5)`: Uploads a file in multipart format to the Biot API.

## ReportManager

The `ReportManager` class provides functionality for exporting, retrieving, and posting configuration snapshots of various entities using the report system. It handles data for devices and generic entities, allowing for the export of reports, transfer of configurations across organizations, and updates of references between entities.

### Attributes

- `data_mgr`: An instance of the data manager class responsible for interacting with the backend API.
- `configuration_template_names` (list): A list of template names used for configuration.
- `back_reference_mapping` (dict): A mapping of entities to their back references, used for updating references after posting.
- `reference_to_copy_dict` (dict): A dictionary defining the mapping between entities and the references that need to be copied when copying configurations between organizations.
- `ge_post_order` (tuple): The order in which generic entities should be posted to ensure dependencies are met.

### Methods

- `export_snapshot_by_entities(self, report_name, ge_template_names_to_filt, save_devices=False, start_date="2024-05-01T09:03:33Z")`: Generates and exports a snapshot of data entities based on specified templates and a date range.
- `export_full_configuration_snapshot(self, report_name, start_date="2024-05-01T09:03:33Z")`: A wrapper function for `export_snapshot_by_entities` that exports the full configuration snapshot.
- `get_report_file_by_name(self, report_name)`: Retrieves the report file by its name.
- `post_full_configuration_report(self, report_dict)`: Posts the full configuration data (retrieved from a report) to the server.
- `post_report_json(self, report_data, template_type)`: Posts a single report (either device or generic entity) in JSON format to the server.
- `config_report_to_different_org(self, src_org_id, new_org_id, report_data_dict)`: Configures a report to be associated with a different organization.
- `full_org_transfer_wrapper(self, src_org_id, dst_org_id, report_name, assests_to_assign_dict=None)`: Transfers an entire organization configuration to another organization.
- `filter_report_for_copy(self, report_data_dict, copy_dict)`: Filters the report data based on specified assets.
- `update_report_by_reference_lookuptable(self, lookup_table, report_data, reference_name, template_name)`: Updates report data by replacing references with IDs from a lookup table.

The SDK provides a convenient and easy-to-use interface for interacting with the Biot API, allowing developers to quickly and easily build applications that leverage the API's functionality.
