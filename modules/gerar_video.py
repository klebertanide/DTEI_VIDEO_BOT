import os
import io
import subprocess
import tempfile
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from urllib.parse import urlparse, parse_qs

CREDENTIALS_PATH = "/mnt/data/credentials.json"

def extrair_pasta_id(link):
    if "folders" in link:
        return link.split("/folders/")[1].split("?")[0]
    elif "drive.google.com/drive/u/0/folders/" in link:
        return link.split("/folders/")[1].split("?")[0]
    elif "id=" in link:
        return parse_qs(urlparse(link).query)["id"][0]
    else:
        raise ValueError("Não foi possível extrair o ID da pasta do link.")

def autenticar_drive():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)

def upload_para_drive(video_path, pasta_id):
    service = autenticar_drive()
    arquivo = MediaFileUpload(video_path, mimetype="video/mp4", resumable=True)

    metadata = {
        "name": os.path.basename(video_path),
        "parents": [pasta_id]
    }

    file = service.files().create(body=metadata, media_body=arquivo, fields="id").execute()
    file_id = file.get("id")

    # Torna o vídeo público
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
        fields="id"
    ).execute()

    return f"https://drive.google.com/file/d/{file_id}/view"

def gerar_video_dummy(saida="video-final.mp4"):
    comando = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=3",
        "-vf", "drawtext=text='Gerando vídeo...':fontsize=50:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264",
        "-t", "3",
        "-pix_fmt", "yuv420p",
        saida
    ]
    subprocess.run(comando, check=True)
    return saida
