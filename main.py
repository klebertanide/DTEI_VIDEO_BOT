from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Permitir que o ChatGPT acesse o OpenAPI via browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # necessário para funcionar com GPT Builder
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/gerar-video/")
async def gerar_video(link: str = Query(..., description="Link público do Google Drive com os arquivos")):
    return JSONResponse(content={
        "status": "em_processo",
        "mensagem": "Seu vídeo está sendo gerado. Isso pode levar alguns minutos.",
        "link_recebido": link,
        "link_video_final": "https://example.com/video-final.mp4"
    })

@app.get("/openapi.json")
async def custom_openapi():
    openapi_schema = get_openapi(
        title="Gerador de Vídeo API",
        version="1.0.0",
        description="API que gera vídeos verticais com base em mídia do Google Drive.",
        routes=app.routes,
    )
    openapi_schema["servers"] = [
        {"url": "https://dtei-video-bot.onrender.com"}
    ]
    return openapi_schema
