# Biot Python SDK

## Introduction

The **Biot Python SDK** is a comprehensive toolkit designed to interact seamlessly with the **Bio-T Open API**. It provides easy-to-use classes for authentication, data retrieval, system health checks, and report management.

This SDK is ideal for developers looking to integrate Bio-T’s system into their applications, enabling quick and efficient API interactions.

---

## Installation

Before using the SDK, install the required dependencies:

```sh
pip install -r requirements.txt
```

or directly install the package:

```sh
pip install biot_python_sdk
```

---

## Quick Start

Here’s a simple example:

```python
from biot_python_sdk import APIClient, BiotClient

# Initialize API client
api_client = APIClient("https://api.dev.xtrodes1.biot-med.com")

# Authenticate using username and password
biot_client = BiotClient(api_client, username="your_username", password="your_password")
token = biot_client.login()

# Check system health
is_healthy = biot_client.is_system_healthy('/settings/system/healthCheck')
print(f"System Healthy: {is_healthy}")
```

---

# **Class Documentation**

## **1. APIClient (Handles HTTP Requests)**

### **Attributes**
| Attribute  | Description |
|------------|------------|
| `base_url` | The base URL of the Biot API (e.g., `"https://api.dev.xtrodes1.biot-med.com"`) |
| `headers`  | Default headers for requests (including authentication token) |
| `retry_count` | Number of request retries in case of failure |

### **Methods**
#### `make_request(endpoint: str, method: str = 'GET', data: dict = None, params: dict = None, headers: dict = None) -> dict`
- Sends an HTTP request and handles retries/errors.

**Example:**
```python
response = api_client.make_request("/settings/system/healthCheck")
```

---

## **2. BiotClient (Handles Authentication & Base API Functions)**

### **Attributes**
| Attribute | Description |
|------------|------------|
| `api_client`  | Instance of `APIClient` |
| `username`    | Bio-T account username |
| `password`    | Bio-T account password |
| `auth_token`  | Stores authentication token |

### **Methods**
#### `login() -> str`
- Authenticates user and retrieves API token.

```python
token = biot_client.login()
```

#### `is_system_healthy(endpoint: str) -> bool`
- Checks if the system is running correctly.
  
```python
is_healthy = biot_client.is_system_healthy('/settings/system/healthCheck')
```

---

## **3. DataManager (File and Data Management)**

### **Attributes**
| Attribute | Description |
|------------|------------|
| `biot_client` | Instance of `BiotClient` |

### **Methods**
#### `get_session_by_uuid(uuid: str) -> dict`
- Retrieves session details by UUID.

```python
session_data = data_manager.get_session_by_uuid("123e4567-e89b-12d3-a456-426614174000")
```

#### `upload_file(filepath: str) -> str`
- Uploads a file to Bio-T.

```python
file_id = data_manager.upload_file("data.csv")
```

#### `create_generic_entity(entity_name: str, entity_data: dict) -> dict`
- Creates a new Generic Entity (GE).

```python
entity = data_manager.create_generic_entity("NewEntity", {"key": "value"})
```

#### `update_generic_entity(entity_id: str, entity_data: dict) -> dict`
- Updates existing GE.

```python
updated_entity = data_manager.update_generic_entity("entity123", {"key": "new_value"})
```

---

## **4. ReportManager (Handles Reports & Config Snapshots)**

### **Attributes**
| Attribute | Description |
|------------|------------|
| `data_manager` | Instance of `DataManager` |

### **Methods**
#### `export_full_configuration_snapshot(report_name: str) -> str`
- Exports a full configuration snapshot.

```python
snapshot_id = report_manager.export_full_configuration_snapshot("Snapshot_ABC")
```

#### `get_report_file_by_name(report_name: str) -> dict`
- Retrieves report file details.

```python
report_data = report_manager.get_report_file_by_name("Snapshot_ABC")
```

#### `import_configuration_snapshot(snapshot_file: str) -> bool`
- Imports a configuration snapshot.

```python
success = report_manager.import_configuration_snapshot("Snapshot_ABC.json")
```

---

# **Environment Variables Setup**
For security, store credentials in an `.env` file, for example:

```ini
biot_username=your_email@domain.com
biot_password=your_secure_password
biot_endpoint=https://api.dev.xtrodes1.biot-med.com
```

---

# **Running Tests**
Run the full test suite:

```sh
pytest
```

---

# **Contributing**
We welcome community contributions! Here’s the workflow:

1. **Fork the repository**.
2. **Create a feature branch**.
3. **Implement changes & tests**.
4. **Submit a pull request**.

---

# **License**
This project is licensed under the **MIT License**.

---

# **Support**
For questions, contact **Stanislav Steinberg** at:
📧 [sstbrg@gmail.com](mailto:sstbrg@gmail.com)

---
