from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = BASE_DIR / "templates" / "index.html"
PDF_FILE = BASE_DIR / "eagunu.pdf"
PNG_FILE = BASE_DIR / "image" / "media" / "eagunu.png"


@router.get("/", response_class=HTMLResponse)
async def root():
    return INDEX_FILE.read_text()


@router.get("/eagunu.pdf")
async def eagunu_pdf():
    return Response(
        PDF_FILE.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="eagunu.pdf"'},
    )


@router.get("/eagunu.png")
async def eagunu_png():
    return Response(
        PNG_FILE.read_bytes(),
        media_type="image/png",
        headers={"Content-Disposition": 'inline; filename="eagunu.png"'},
    )
