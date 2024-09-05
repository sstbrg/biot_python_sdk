import pytest
from biot_python_sdk import APIClient
from biot_python_sdk.BioT_API_URLS import BASE_URL, LOGIN_SUB_URL
import requests

@pytest.fixture
def api_client():
    return APIClient("https://api.dev.xtrodes1.biot-med.com")

def test_make_request_get(api_client, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mocker.patch('requests.request', return_value=mock_response)

    response = api_client.make_request("/settings/system/healthCheck")

    assert response == mock_response
    requests.request.assert_called_once_with('GET', 'https://api.dev.xtrodes1.biot-med.com/settings/system/healthCheck', headers=None, json=None, data=None)

def test_make_request_post(api_client, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mocker.patch('requests.request', return_value=mock_response)
    response = api_client.make_request(LOGIN_SUB_URL, method='POST', json={"username": "test", "password": "test"})
    assert response == mock_response
    requests.request.assert_called_once_with('POST', BASE_URL + LOGIN_SUB_URL, headers=None, json={"username": "test", "password": "test"}, data=None)

def test_make_request_failure(api_client, mocker):
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mocker.patch('requests.request', return_value=mock_response)

    response = api_client.make_request("/nonexistent-endpoint")

    assert response is None
    requests.request.assert_called()