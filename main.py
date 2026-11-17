import os
import shutil
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from core.extractor import extract_transcript
from core.doc_extractor import extract_document_text, is_document, DocumentExtractionError, DOCUMENT_EXTENSIONS
from core.Summarize import summarize, get_title
from core.rag_engine import HybridRAG

# Load environment variables (.env)
load_dotenv()

# Workspace & Storage Configuration
DOWNLOAD_DIR = os.path.abspath("downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Active Application Session State
active_state = {
    "title": None,
    "summary": None,
    "transcript": None,
    "rag_engine": None,
    "source": None,
    "language": "english",
    "source_type": "audio"   # "audio" (meeting transcript) or "document" (PDF / DOC / DOCX)
}

app = FastAPI(
    title="AI Video Meeting Assistant with Hybrid RAG",
    description="FastAPI backend featuring YouTube audio extraction, local drag & drop, file system explorer, BM25 + Vector Hybrid Search RAG, and Conversational Chat Memory.",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Assets
static_dir = os.path.abspath("static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def read_source_text(file_path: str, language: str):
    """
    Turns a local file into text. Returns (text, kind).
      - PDF / DOC / DOCX / MD -> document text extraction (kind="document")
      - TXT                   -> plain transcript text (kind="meeting")
      - audio / video         -> Whisper / Sarvam transcription (kind="meeting")
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), "meeting"
    if ext in DOCUMENT_EXTENSIONS:
        try:
            return extract_document_text(file_path), "document"
        except DocumentExtractionError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except Exception as e:  # corrupt / unreadable file
            raise HTTPException(status_code=422, detail=f"Could not read document: {e}")
    return extract_transcript(file_path, language=language), "meeting"


def index_and_summarize(text: str, kind: str, source: str, language: str) -> dict:
    """Title + summary + Hybrid RAG index; stores the result as the active session and returns the API payload."""
    title = get_title(text, kind=kind)
    summary_text = summarize(text, kind=kind)
    rag_engine = HybridRAG(text, kind=kind)

    active_state.update({
        "title": title, "summary": summary_text, "transcript": text, "rag_engine": rag_engine,
        "source": source, "language": language, "source_type": kind
    })
    return {
        "status": "success",
        "title": title,
        "summary": summary_text,
        "transcript": text,
        "word_count": len(text.split()),
        "language": language,
        "source": source,
        "source_type": "document" if kind == "document" else "audio",
    }


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serves the main single-page application dashboard."""
    index_path = os.path.abspath(os.path.join("templates", "index.html"))
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Index template not found")
    return FileResponse(index_path)


@app.post("/api/process/yt")
async def process_youtube_link(payload: dict = Body(...)):
    """Processes a YouTube URL: downloads audio, transcribes, summarizes, and indexes for Hybrid RAG."""
    url = payload.get("url")
    language = payload.get("language", "english")
    
    if not url or not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid YouTube URL provided")

    try:
        print(f"\n[FastAPI] Processing YouTube URL: {url} (Language: {language})")
        transcript = extract_transcript(url, language=language)
        
        if not transcript.strip():
            raise HTTPException(status_code=422, detail="Extraction returned empty transcript.")

        title = get_title(transcript)
        summary_text = summarize(transcript)
        
        # Initialize Hybrid RAG (BM25 + Vector Search + Conversational Memory)
        rag_engine = HybridRAG(transcript)
        
        # Store state
        active_state["title"] = title
        active_state["summary"] = summary_text
        active_state["transcript"] = transcript
        active_state["rag_engine"] = rag_engine
        active_state["source"] = url
        active_state["language"] = language

        word_count = len(transcript.split())

        return {
            "status": "success",
            "title": title,
            "summary": summary_text,
            "transcript": transcript,
            "word_count": word_count,
            "language": language,
            "source": url
        }
    except Exception as e:
        print(f"[Error] Failed processing YouTube link: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process/upload")
async def process_drag_and_drop_upload(
    file: UploadFile = File(...),
    language: str = Form("english")
):
    """Processes a drag-and-drop file upload from the client browser."""
    try:
        filename = file.filename
        file_path = os.path.join(DOWNLOAD_DIR, f"upload_{os.path.basename(filename)}")
        
        print(f"\n[FastAPI] Saving uploaded file to: {file_path}")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        print(f"[FastAPI] Processing uploaded file: {filename} (Language: {language})")

        transcript, kind = read_source_text(file_path, language)

        if not transcript.strip():
            raise HTTPException(status_code=422, detail="Transcript extraction returned empty content.")

        return index_and_summarize(transcript, kind, filename, language)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Error] Failed processing file upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/filesystem")
async def browse_file_system(path: Optional[str] = None):
    """Lists files and subdirectories for the Server File Explorer modal."""
    try:
        target_dir = os.path.abspath(path) if path else os.getcwd()

        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            target_dir = os.getcwd()

        parent_dir = os.path.dirname(target_dir) if target_dir != os.path.dirname(target_dir) else None

        items = []
        media_extensions = {".mp3", ".wav", ".m4a", ".mp4", ".mkv", ".flac", ".ogg", ".txt"} | DOCUMENT_EXTENSIONS

        for entry in os.scandir(target_dir):
            if entry.name.startswith(".") or entry.name in ["__pycache__", "node_modules", ".venv", ".git"]:
                continue

            is_dir = entry.is_dir()
            ext = os.path.splitext(entry.name)[1].lower()
            is_media = is_dir or (ext in media_extensions)
            is_doc = (not is_dir) and ext in DOCUMENT_EXTENSIONS

            size = entry.stat().st_size if not is_dir else 0

            items.append({
                "name": entry.name,
                "path": entry.path,
                "is_dir": is_dir,
                "is_media": is_media,
                "is_document": is_doc,
                "size": size
            })

        # Sort: directories first, then files alphabetically
        items.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))

        return {
            "current_path": target_dir,
            "parent_path": parent_dir,
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/process/filesystem")
async def process_file_system_item(payload: dict = Body(...)):
    """Processes a file selected directly from the local server file system."""
    file_path = payload.get("path")
    language = payload.get("language", "english")

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Selected server file does not exist")

    try:
        print(f"\n[FastAPI] Processing File System item: {file_path}")

        transcript, kind = read_source_text(file_path, language)

        if not transcript.strip():
            raise HTTPException(status_code=422, detail="Transcript is empty.")

        return index_and_summarize(transcript, kind, os.path.basename(file_path), language)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat_with_meeting_rag(payload: dict = Body(...)):
    """Conversational RAG Q&A endpoint featuring BM25 + Vector Search & Chat Memory."""
    question = payload.get("question")
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Empty question provided")

    rag_engine: HybridRAG = active_state.get("rag_engine")
    if not rag_engine:
        raise HTTPException(
            status_code=400,
            detail="No meeting transcript has been processed yet. Please upload audio, YouTube link, or file first."
        )

    try:
        answer = rag_engine.answer_question(question)
        return {
            "question": question,
            "answer": answer
        }
    except Exception as e:
        print(f"[Error] RAG Chat Exception: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear-memory")
async def clear_chat_memory():
    """Resets the conversational memory for the active RAG engine session."""
    rag_engine: HybridRAG = active_state.get("rag_engine")
    if rag_engine:
        rag_engine.clear_memory()
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 60)
    print("🚀 Starting AI Video Meeting Assistant Web Server on http://127.0.0.1:8000")
    print("=" * 60)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
