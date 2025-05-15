from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from modules.gerar_video import gerar_video_dummy, extrair_pasta_id, upload_para_drive

app = FastAPI(openapi_url=None)

# CORS para integração com o GPT Builder
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/gerar-video/")
async def gerar_video(link: str = Query(..., description="Link público do Google Drive com os arquivos")):
    try:
        pasta_id = extrair_pasta_id(link)
        video_path = gerar_video_dummy()
        link_video = upload_para_drive(video_path, pasta_id)

        return JSONResponse(content={
            "status": "concluído",
            "mensagem": "Vídeo gerado com sucesso!",
            "link_recebido": link,
            "link_video_final": link_video
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

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
