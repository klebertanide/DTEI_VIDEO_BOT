import os
import io
import subprocess
import tempfile
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from urllib.parse import urlparse, parse_qs
import glob
from pathlib import Path
from difflib import SequenceMatcher

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

def similaridade(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def encontrar_arquivos_por_extensao(pasta, extensao):
    arquivos = glob.glob(os.path.join(pasta, f"*.{extensao}"))
    return arquivos[0] if arquivos else None

def gerar_video_real(pasta_entrada, pasta_recursos, saida="video-final.mp4"):
    audio_path = encontrar_arquivos_por_extensao(pasta_entrada, "mp3")
    legenda_path = encontrar_arquivos_por_extensao(pasta_entrada, "srt")
    csv_path = encontrar_arquivos_por_extensao(pasta_entrada, "csv")
    imagens = glob.glob(os.path.join(pasta_entrada, "*.jpg")) + glob.glob(os.path.join(pasta_entrada, "*.png"))

    if not all([audio_path, legenda_path, csv_path]) or not imagens:
        raise Exception("Faltam arquivos obrigatórios na pasta de entrada.")

    df = pd.read_csv(csv_path)
    if "prompt" not in df.columns:
        raise Exception("Coluna 'prompt' não encontrada no CSV.")

    prompts = df["prompt"].tolist()
    imagem_para_tempo = []

    for prompt in prompts:
        tempo, texto = prompt.split(" ", 1)
        tempo = int(tempo)
        melhor_imagem = max(imagens, key=lambda img: similaridade(Path(img).stem, texto))
        imagem_para_tempo.append((tempo, melhor_imagem))

    imagem_para_tempo.sort(key=lambda x: x[0])
    fechamento_path = os.path.join(pasta_recursos, "fechamento.png")

    if not os.path.exists(fechamento_path):
        raise Exception("Arquivo fechamento.png não encontrado na pasta de recursos.")

    imagem_para_tempo.append((imagem_para_tempo[-1][0] + 4, fechamento_path))

    with open("lista.txt", "w") as f:
        for i in range(len(imagem_para_tempo)):
            tempo_atual, img = imagem_para_tempo[i]
            tempo_proximo = imagem_para_tempo[i + 1][0] if i + 1 < len(imagem_para_tempo) else tempo_atual + 4
            duracao = tempo_proximo - tempo_atual
            f.write(f"file '{img}'\n")
            f.write(f"duration {duracao}\n")

    ffmpeg_comando = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", "lista.txt",
        "-i", audio_path,
        "-vf", f"subtitles='{legenda_path}':force_style='Alignment=2,FontSize=24'",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        saida
    ]

    subprocess.run(ffmpeg_comando, check=True)
    return saida

# --- Versão com overlay e marca d'água ---
def gerar_video_real(pasta_entrada, pasta_recursos, saida="video-final.mp4"):
    audio_path = encontrar_arquivos_por_extensao(pasta_entrada, "mp3")
    legenda_path = encontrar_arquivos_por_extensao(pasta_entrada, "srt")
    csv_path = encontrar_arquivos_por_extensao(pasta_entrada, "csv")
    imagens = glob.glob(os.path.join(pasta_entrada, "*.jpg")) + glob.glob(os.path.join(pasta_entrada, "*.png"))

    if not all([audio_path, legenda_path, csv_path]) or not imagens:
        raise Exception("Faltam arquivos obrigatórios na pasta de entrada.")

    df = pd.read_csv(csv_path)
    if "prompt" not in df.columns:
        raise Exception("Coluna 'prompt' não encontrada no CSV.")

    prompts = df["prompt"].tolist()
    imagem_para_tempo = []

    for prompt in prompts:
        tempo, texto = prompt.split(" ", 1)
        tempo = int(tempo)
        melhor_imagem = max(imagens, key=lambda img: similaridade(Path(img).stem, texto))
        imagem_para_tempo.append((tempo, melhor_imagem))

    imagem_para_tempo.sort(key=lambda x: x[0])
    fechamento_path = os.path.join(pasta_recursos, "fechamento.png")
    overlay_path = os.path.join(pasta_recursos, "sobrepor.mp4")
    marca_path = os.path.join(pasta_recursos, "sobrepor.png")

    if not os.path.exists(fechamento_path) or not os.path.exists(overlay_path) or not os.path.exists(marca_path):
        raise Exception("Arquivos de recursos não encontrados na pasta de recursos.")

    imagem_para_tempo.append((imagem_para_tempo[-1][0] + 4, fechamento_path))

    with open("lista.txt", "w") as f:
        for i in range(len(imagem_para_tempo)):
            tempo_atual, img = imagem_para_tempo[i]
            tempo_proximo = imagem_para_tempo[i + 1][0] if i + 1 < len(imagem_para_tempo) else tempo_atual + 4
            duracao = tempo_proximo - tempo_atual
            f.write(f"file '{img}'\n")
            f.write(f"duration {duracao}\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", "lista.txt",
        "-vsync", "vfr",
        "-pix_fmt", "yuv420p",
        "base.mp4"
    ], check=True)

    filtros = [
        f"[0:v][1:v] overlay=shortest=1:format=auto [tmp]",
        f"[tmp][2:v] overlay=W-w-10:H-h-10:enable='lt(t,{{marca_fim}})'"
    ]
    marca_fim = imagem_para_tempo[-1][0]  # marca d'água até fechamento entrar

    subprocess.run([
        "ffmpeg", "-y",
        "-i", "base.mp4",
        "-i", overlay_path,
        "-i", marca_path,
        "-i", audio_path,
        "-vf", f"subtitles='{legenda_path}'," + filtros[0].replace("[tmp]", "tmp") + "," + filtros[1].replace("{{marca_fim}}", str(marca_fim)),
        "-map", "[tmp]",
        "-map", "3:a",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        saida
    ], check=True)

    return saida

# --- Versão leve sem overlay de vídeo ---
def gerar_video_real(pasta_entrada, pasta_recursos, saida="video-final.mp4"):
    audio_path = encontrar_arquivos_por_extensao(pasta_entrada, "mp3")
    legenda_path = encontrar_arquivos_por_extensao(pasta_entrada, "srt")
    csv_path = encontrar_arquivos_por_extensao(pasta_entrada, "csv")
    imagens = glob.glob(os.path.join(pasta_entrada, "*.jpg")) + glob.glob(os.path.join(pasta_entrada, "*.png"))

    if not all([audio_path, legenda_path, csv_path]) or not imagens:
        raise Exception("Faltam arquivos obrigatórios na pasta de entrada.")

    df = pd.read_csv(csv_path)
    if "prompt" not in df.columns:
        raise Exception("Coluna 'prompt' não encontrada no CSV.")

    prompts = df["prompt"].tolist()
    imagem_para_tempo = []

    for prompt in prompts:
        tempo, texto = prompt.split(" ", 1)
        tempo = int(tempo)
        melhor_imagem = max(imagens, key=lambda img: similaridade(Path(img).stem, texto))
        imagem_para_tempo.append((tempo, melhor_imagem))

    imagem_para_tempo.sort(key=lambda x: x[0])
    fechamento_path = os.path.join(pasta_recursos, "fechamento.png")
    marca_path = os.path.join(pasta_recursos, "sobrepor.png")

    if not os.path.exists(fechamento_path) or not os.path.exists(marca_path):
        raise Exception("Arquivo de recursos (fechamento ou sobrepor.png) não encontrado.")

    imagem_para_tempo.append((imagem_para_tempo[-1][0] + 4, fechamento_path))

    with open("lista.txt", "w") as f:
        for i in range(len(imagem_para_tempo)):
            tempo_atual, img = imagem_para_tempo[i]
            tempo_proximo = imagem_para_tempo[i + 1][0] if i + 1 < len(imagem_para_tempo) else tempo_atual + 4
            duracao = tempo_proximo - tempo_atual
            f.write(f"file '{img}'\n")
            f.write(f"duration {duracao}\n")

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", "lista.txt",
        "-vsync", "vfr",
        "-pix_fmt", "yuv420p",
        "base.mp4"
    ], check=True)

    marca_fim = imagem_para_tempo[-1][0]

    subprocess.run([
        "ffmpeg", "-y",
        "-i", "base.mp4",
        "-i", marca_path,
        "-i", audio_path,
        "-vf", f"subtitles='{legenda_path}',overlay=W-w-10:H-h-10:enable='lt(t,{marca_fim})'",
        "-map", "0:v",
        "-map", "2:a",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-shortest",
        saida
    ], check=True)

    return saida
