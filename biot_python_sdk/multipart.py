import requests
import os
import re
import platform
import subprocess
import mimetypes

POWERSHELL_SCRIPT_PATH = "split-file.ps1"

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
    # List and sort files with 'part_' prefix, based on the suffix part
    parts = sorted(
        [f for f in os.listdir() if f.startswith("part_") and f.endswith(".bin")],
        key=lambda f: re.search(r'part_(\w+)\.bin', f).group(1)
    )
    return parts

def upload_part(signed_url, file_path):
    with open(file_path, 'rb') as file_part:
        response = requests.put(signed_url, data=file_part)
        response.raise_for_status()
        # Extract ETag from response headers
        return response.headers.get('ETag')

# Function to delete the split file parts
def delete_file_parts():
    for f in os.listdir():
        if f.startswith("part_"):
            os.remove(f)

