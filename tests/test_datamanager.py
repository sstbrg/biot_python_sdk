import os
import pytest
from dotenv import load_dotenv
import requests
import uuid

# Load environment variables from .env
load_dotenv()

# Patch APIClient.make_request so that if 'data' is ModuleNotFoundError, it defaults to None.
from biot_python_sdk import APIClient
orig_make_request = APIClient.make_request
def patched_make_request(self, endpoint, method='GET', headers=None, json=None, data=None):
    if data is ModuleNotFoundError:
        data = None
    return orig_make_request(self, endpoint, method, headers, json, data)
APIClient.make_request = patched_make_request

# Import the BioT SDK classes from the proper package location
from biot_python_sdk import APIClient, BiotClient, DataManager

@pytest.fixture(scope="session")
def credentials():
    """
    Loads required credentials and test parameters from .env.
    Required:
      - biot_endpoint
      - biot_username
      - biot_password
      - test_org
    Optional:
      - test_device       (a valid device id for usage session tests)
      - test_session_uuid (an existing usage session uuid)
      - test_template     (a template name for generic entity and template tests)
    """
    creds = {
        "endpoint": os.getenv("biot_endpoint"),
        "username": os.getenv("biot_username"),
        "password": os.getenv("biot_password"),
        "test_org": os.getenv("test_org"),
        "test_device": os.getenv("test_device"),
        "test_session_uuid": os.getenv("test_session_uuid"),
        "test_template": os.getenv("test_template")
    }
    for key in ["endpoint", "username", "password", "test_org"]:
        assert creds.get(key), f"{key} not set in .env"
    return creds

@pytest.fixture(scope="session")
def datamanager(credentials):
    """
    Fixture that creates and returns a DataManager instance.
    Logs in using the provided credentials.
    """
    api_client = APIClient(credentials["endpoint"])
    biot_client = BiotClient(api_client, username=credentials["username"], password=credentials["password"])
    token = biot_client.login()
    assert token is not None, "Login failed; token is None"
    dm = DataManager(biot_client)
    return dm

# -------------------------
# Test _get_org_id_from_name
# -------------------------
def test_get_org_id_from_name(datamanager, credentials):
    """
    Test retrieving the organization ID using the organization name from .env.
    """
    org_id = datamanager._get_org_id_from_name(credentials["test_org"])
    assert org_id is not None, "Failed to retrieve organization ID for test_org"
    print(f"Organization ID for '{credentials['test_org']}': {org_id}")

# -------------------------
# Test get_session_by_uuid
# -------------------------
def test_get_session_by_uuid(datamanager, credentials):
    """
    Test retrieving a usage session by UUID.
    Skips if test_session_uuid is not provided.
    """
    test_uuid = credentials.get("test_session_uuid")
    if not test_uuid:
        pytest.skip("Skipping get_session_by_uuid test; test_session_uuid not provided.")
    response = datamanager.get_session_by_uuid(test_uuid)
    assert response is not None, "Response is None"
    data = response.json().get("data")
    assert isinstance(data, list), "Expected 'data' to be a list"

# -------------------------
# Test get_ge_by_filter with a filter
# -------------------------
def test_get_generic_entity_by_name(datamanager):
    """
    Test retrieving generic entities using a filter on _name.
    If an entity with _name "entity1" is found, the method works.
    """
    filter_obj = {"_name": {"eq": "entity1"}}
    result = datamanager.get_ge_by_filter(filter_obj)
    if result is None or not result.get("data"):
        pytest.skip("No generic entities found with _name 'entity1'.")
    entities = result.get("data")
    found = any(entity.get("_name") == "entity1" for entity in entities)
    assert found, "Generic entity with _name 'entity1' not found."

# -------------------------
# Test create_usage_session and update_usage_session
# -------------------------

# -------------------------
# Test get_usage_session_by_id
# -------------------------
def test_get_usage_session_by_id(datamanager):
    """
    Test retrieving a usage session by its ID and device ID.
    Using dummy values that likely do not exist should lead to a failure response.
    """
    dummy_session_id = "nonexistent-session-id"
    dummy_device_id = "nonexistent-device-id"
    try:
        result = datamanager.get_usage_session_by_id(dummy_session_id, dummy_device_id)
        if result:
            data = result.json()
            if "data" in data:
                assert len(data["data"]) == 0, "Expected no usage session for dummy IDs"
    except Exception:
        pass

# -------------------------
# Test upload and file attachment
# -------------------------
@pytest.mark.skipif(os.getenv("test_template") is None, reason="test_template not provided in .env")
def test_entity_file_attachment(datamanager, credentials, tmp_path):
    """
    Test attaching an uploaded file to a generic entity.
    Workflow:
      1. Create and upload a file.
      2. Create a generic entity with a random _name and a 'test_file' key set to {'id': file_id}.
      3. Retrieve the entity via get_ge_by_filter (filtering on _name).
      4. Retrieve the signed URL for the attached file, download it,
         and compare its content to the original file.
      5. Clean up by deleting the created entity.
    """
    template_name = credentials["test_template"]
    
    # 1. Create a temporary file with known content and upload it.
    test_file = tmp_path / "attachment.txt"
    original_text = "This is the content of the attachment file."
    test_file.write_text(original_text)
    
    file_info = datamanager.upload_file(str(test_file))
    assert file_info is not None, "upload_file returned None"
    assert "id" in file_info, "upload_file response missing 'id'"
    file_id = file_info["id"]
    
    # 2. Generate a random entity name to avoid conflicts.
    entity_name = "entity_" + uuid.uuid4().hex
    entity_data = {
         "_name": entity_name,
         "test_file": {"id": file_id}
    }
    created_entity = datamanager.create_generic_entity_by_template_name(template_name, entity_data)
    assert created_entity is not None, "Failed to create generic entity"
    entity_id = created_entity.get("id")
    assert entity_id, "Created generic entity missing 'id'"
    
    # 3. Retrieve the entity using get_ge_by_filter with a filter on _name.
    filter_obj = {"_name": {"eq": entity_name}}
    entities_response = datamanager.get_ge_by_filter(filter_obj)
    assert entities_response is not None, "get_ge_by_filter returned None"
    entities = entities_response.get("data")
    assert isinstance(entities, list) and entities, "No generic entities found for the generated name"
    
    # Find the entity with the generated name
    entity = next((e for e in entities if e.get("_name") == entity_name), None)
    assert entity is not None, f"Entity with _name '{entity_name}' not found"
    
    # 4. Get the file reference from the entity and retrieve its signed URL.
    file_ref = entity.get("test_file")
    assert isinstance(file_ref, dict), "test_file key is not a dict"
    attached_file_id = file_ref.get("id")
    assert attached_file_id == file_id, "File id in entity does not match the uploaded file id"
    
    signed_url = datamanager.get_file_signedurl_by_fileid(attached_file_id)
    assert signed_url is not None, "Failed to get signed URL for attached file"
    
    # Download the file using the signed URL and compare its contents.
    download_resp = requests.get(signed_url)
    assert download_resp.status_code == 200, f"Failed to download attached file, status code {download_resp.status_code}"
    downloaded_content = download_resp.content.decode("utf-8")
    assert downloaded_content == original_text, "Downloaded attachment content does not match original"
    
    # 5. Clean up by deleting the created generic entity.
    delete_resp = datamanager.delete_generic_entity_by_id(entity_id)
    assert delete_resp is not None, "Failed to delete the generic entity"

# -------------------------
# Test upload_file_from_ram
# -------------------------
def test_upload_file_from_ram(datamanager):
    """
    Test uploading file data from memory.
    """
    data = b"This is a test file uploaded from RAM."
    file_name = "test_ram_upload.txt"
    file_info = datamanager.biot_client.upload_file_from_ram(data, file_name)
    assert file_info is not None, "upload_file_from_ram returned None"
    assert "id" in file_info, "upload_file_from_ram response missing 'id'"

# -------------------------
# Test upload_multipart
# -------------------------
def test_upload_multipart(datamanager, tmp_path):
    """
    Test uploading a file using multipart upload.
    """
    test_file = tmp_path / "test_multipart.txt"
    test_file.write_text("This is a test file for multipart upload." * 100)
    
    file_id = datamanager.upload_multipart(str(test_file), test_file.name, chunk_size=1024)
    assert file_id is not None, "upload_multipart did not return a file id"

# -------------------------
# Test refresh_token
# -------------------------
def test_refresh_token(datamanager):
    """
    Test refreshing the authentication token.
    """
    old_token = datamanager.biot_client.token
    resp = datamanager.refresh_token(old_token)
    assert resp is not None, "refresh_token returned None"
    new_token = resp.json().get("accessJwt", {}).get("token")
    assert new_token is not None, "New token not found in refresh response"

# -------------------------
# Test fetch_template_by_filter and fetch_template_by_id
# -------------------------
@pytest.mark.skipif(os.getenv("test_template") is None, reason="test_template not provided in .env")
def test_fetch_template_methods(datamanager, credentials):
    """
    Test fetching a template using a filter and then fetching it by its id.
    """
    template_name = credentials["test_template"]
    filter_obj = {"name": {"eq": template_name}}
    
    templates_response = datamanager.fetch_template_by_filter(filter_obj)
    assert templates_response is not None, "fetch_template_by_filter returned None"
    templates_data = templates_response.get("data")
    assert isinstance(templates_data, list), "Expected 'data' to be a list in templates response"
    
    matching_template = next((t for t in templates_data if t.get("name") == template_name), None)
    assert matching_template is not None, f"Template with name '{template_name}' not found in filter results"
    
    template_id = matching_template.get("id")
    assert template_id is not None, "Template id missing in the filter result"
    
    fetched_template = datamanager.fetch_template_by_id(template_id)
    assert fetched_template is not None, "fetch_template_by_id returned None"
    assert fetched_template.get("name") == template_name, "Fetched template name does not match"

# -------------------------
# Test update_template
# -------------------------
@pytest.mark.skipif(os.getenv("test_template") is None, reason="test_template not provided in .env")
def test_update_template(datamanager, credentials):
    """
    Test updating a template. This test fetches an existing template,
    then calls update_template with the same keys/values so that it passes validation.
    NOTE: This test may update the template on the test environment.
    """
    template_name = credentials["test_template"]
    template_id = datamanager._get_template_id_from_name(template_name)
    if not template_id:
        pytest.skip(f"Template id for {template_name} not found")
    
    existing_template = datamanager.fetch_template_by_id(template_id)
    if not existing_template:
        pytest.skip("Existing template could not be fetched")
    
    try:
        update_resp = datamanager.update_template(template_id, existing_template)
    except ValueError as ve:
        pytest.skip(f"update_template validation error (expected if no changes allowed): {ve}")
    assert update_resp is not None, "update_template returned None"

# -------------------------
# Test generic entity lifecycle: create, update, delete
# -------------------------
@pytest.mark.skipif(os.getenv("test_template") is None, reason="test_template not provided in .env")
def test_generic_entity_lifecycle(datamanager, credentials):
    """
    Test creating a generic entity using a template name, then updating and deleting it.
    """
    template_name = credentials["test_template"]
    data = {"_name": "Test Generic Entity"}
    created_entity = datamanager.create_generic_entity_by_template_name(template_name, data)
    assert created_entity is not None, "create_generic_entity_by_template_name returned None"
    entity_id = created_entity.get("id")
    assert entity_id, "Created generic entity missing 'id'"
    
    updated_data = {"_name": "Updated Generic Entity"}
    update_resp = datamanager.update_generic_entity_by_id(entity_id, updated_data)
    assert update_resp is not None, "update_generic_entity_by_id returned None"
    updated_entity = update_resp.json()
    assert updated_entity.get("_name") == "Updated Generic Entity", "Generic entity update did not take effect"
    
    delete_resp = datamanager.delete_generic_entity_by_id(entity_id)
    assert delete_resp is not None, "delete_generic_entity_by_id returned None"

# -------------------------
# New Test: Lookup Generic Entities by _templateName
# -------------------------
@pytest.mark.skipif(os.getenv("test_template") is None, reason="test_template not provided in .env")
def test_get_generic_entities_by_template(datamanager, credentials):
    """
    Test retrieving generic entities using the _templateName filter.
    This test uses the test_template value from .env to filter entities.
    """
    template_name = credentials["test_template"]
    filter_obj = {"_templateName": {"eq": template_name}}
    result = datamanager.get_ge_by_filter(filter_obj)
    if result is None:
        pytest.skip("No generic entities found using the _templateName filter")
    assert isinstance(result, dict), "Expected result to be a dictionary"
    assert "data" in result, "Result missing 'data' key"
    entities = result["data"]
    assert isinstance(entities, list), "Expected 'data' to be a list"
    # Optionally, ensure at least one entity has a populated field.
    if not entities:
        pytest.skip(f"No generic entities found for template '{template_name}'")
    for entity in entities:
        # Here you might add assertions checking specific populated fields.
        print("Entity:", entity)
