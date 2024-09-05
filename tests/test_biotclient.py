import pytest
from biot_python_sdk import APIClient, BiotClient

@pytest.fixture
def api_client():
    return APIClient("https://api.dev.xtrodes1.biot-med.com")

@pytest.fixture
def biot_client(api_client):
    return BiotClient(api_client, username="test", password="test")

def test_login(biot_client, mocker):
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"accessJwt": {"token": "test_token"}}
    mocker.patch.object(biot_client.api_client, 'make_request', return_value=mock_response)

    token = biot_client.login()

    assert token == "test_token"
    biot_client.api_client.make_request.assert_called_once_with('/ums/v2/users/login', method='POST', json={"username": "test", "password": "test"})

def test_is_system_healthy(biot_client, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mocker.patch.object(biot_client.api_client, 'make_request', return_value=mock_response)

    is_healthy = biot_client.is_system_healthy('/settings/system/healthCheck')

    assert is_healthy is True
    biot_client.api_client.make_request.assert_called_once_with('/settings/system/healthCheck', headers={"accept": "application/json"})

def test_get_headers(biot_client):
    headers = biot_client.get_headers()

    assert headers == {"accept": "application/json", "authorization": "Bearer test_token"}