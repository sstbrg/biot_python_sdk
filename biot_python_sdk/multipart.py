import requests
import os
import re
import platform
import subprocess
import mimetypes

# Constants
#BASE_URL = "https://api.xxxxx.com"  # Replace with your API URL
#USERNAME = "username"  # Replace with your username
#PASSWORD = "password"  # Replace with your password
#LOGIN_URL = f"{BASE_URL}/ums/v2/users/login"
POWERSHELL_SCRIPT_PATH = "split-file.ps1"
#FILE_PATH = "/path_to_file/file.zip"  # Replace with the file you want to split, include full path if file is not inside the project
#PART_SIZE = 20 * 1024 * 1024  # 20MB
#PATIENT_ID = "patient_id"  # Replace with your patient ID
#FILE_KEY = "file_entity_name"  # Replace with the "File" entity JSON name configured in the template
#FILE_NAME = "example.zip"  # Filename to be uploaded into patient


# Function to split file into parts

def split_file(file_path, part_size):
    system = platform.system()
    if system == "Darwin":  # macOS
        subprocess.run(["split", "-b", f"{part_size}", file_path, "part_"])
        # Rename split files to include .bin extension
        for f in os.listdir():
            if f.startswith("part_"):
                os.rename(f, f"{f}.bin")
    elif system == "Windows":
        subprocess.run([
            "powershell",
            "-ExecutionPolicy", "Bypass",
            "-File", POWERSHELL_SCRIPT_PATH,
            "-filePath", file_path,
            "-partSize", str(part_size)
        ])
        # Rename split files to include .bin extension
        for f in os.listdir():
            if f.startswith("part_"):
                os.rename(f, f"{f}.bin")
    else:  # Linux
        subprocess.run(["split", "-b", f"{part_size}", file_path, "part_"])
        # Rename split files to include .bin extension
        for f in os.listdir():
            if f.startswith("part_"):
                os.rename(f, f"{f}.bin")

# Function to determine the MIME type of a file
def get_mime_type(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


# Function to get list of file parts and sort them
def get_file_parts():
    # List files with 'part_' prefix
    parts = [f for f in os.listdir() if f.startswith("part_") and f.endswith(".bin")]
    # Define a function to extract the suffix part for sorting
    def extract_suffix(file_name):
        match = re.search(r'part_(\w+)\.bin', file_name)
        return match.group(1) if match else ''

    # Sort parts based on the suffix
    parts.sort(key=extract_suffix)
    return parts

# # Function to initiate the upload
# def initiate_upload(api_url, file_name, mime_type, parts_count, token):
#     headers = {
#         "Authorization": f"Bearer {token}"
#     }
#     response = requests.post(f"{api_url}/file/v1/files/upload/parts/", json={
#         "name": file_name,
#         "mimeType": mime_type,
#         "parts": parts_count
#     }, headers=headers)
#     response.raise_for_status()

#     upload_info = response.json()

#     if 'signedUrls' not in upload_info:
#         raise ValueError("Response does not contain 'signedUrls' key")

#     signed_urls = {url_info["partNumber"]: url_info["signedUrl"] for url_info in upload_info["signedUrls"]}

#     return upload_info["id"], signed_urls

# Function to upload a file part

def upload_part(signed_url, file_path):
    with open(file_path, 'rb') as file_part:
        response = requests.put(signed_url, data=file_part)
        response.raise_for_status()
        # Extract ETag from response headers
        return response.headers.get('ETag')

# # Function to complete the upload
# def complete_upload(api_url, file_id, etags, token):
#     headers = {
#         "Authorization": f"Bearer {token}"
#     }
#     response = requests.post(f"{api_url}/file/v1/files/upload/parts/{file_id}/complete", json={
#         "parts": [{"partNumber": i + 1, "etag": etag} for i, etag in enumerate(etags)]
#     }, headers=headers)
#     print("ETags:", ', '.join(f"Part {i + 1}: {etag}" for i, etag in enumerate(etags)))
#     response.raise_for_status()

#     complete_info = response.json()

#     return complete_info

# # Function to update the patient ID with the file ID
# def update_patient_id(base_url, patient_id, file_id, file_key, token):
#     url = f"{base_url}/organization/v1/users/patients/{patient_id}"
#     headers = {
#         'Content-Type': 'application/json',
#         'Authorization': f'Bearer {token}'
#     }
#     body = {
#         file_key: {
#             'id': file_id
#         }
#     }
#     response = requests.patch(url, headers=headers, json=body)
#     response.raise_for_status()
#     return response.json()

# Function to delete the split file parts
def delete_file_parts():
    for f in os.listdir():
        if f.startswith("part_"):
            os.remove(f)

# # Main function
# def main():
#     #token = get_token(USERNAME, PASSWORD)
#     #split_file(FILE_PATH, PART_SIZE)
#     #parts = get_file_parts()
#     #mime_type = get_mime_type(FILE_PATH)  # Determine the MIME type of the file
#     file_id, signed_urls = initiate_upload(BASE_URL, FILE_NAME, mime_type, len(parts), token)

#     print("Signed URLs:")
#     for part_number, signed_url in signed_urls.items():
#         print(f"Part {part_number}: {signed_url}")

#     etags = []
#     for i, part in enumerate(parts):
#         etag = upload_part(signed_urls[i + 1], part)
#         etags.append(etag)

#     complete_info = complete_upload(BASE_URL, file_id, etags, token)
#     print("File Upload Completed", complete_info)
#     update_patient_id(BASE_URL, PATIENT_ID, file_id, FILE_KEY, token)  # Attach File to a patient

#     # Delete the split file parts
#     delete_file_parts()

# if __name__ == "__main__":
#     main()