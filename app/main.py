import os
import uuid
import re  # Za validaciju znakova
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from . import models

models.init_db()

app = FastAPI(docs_url=None, redoc_url=None)

# Middleware
SECRET_KEY = os.getenv("SECRET_KEY")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

templates = Jinja2Templates(directory="templates")

#URLovi
FORBIDDEN_IDS = {"admin", "login", "logout", "dashboard", "oauth", "shorten", "static"}

def get_db():
    db = models.SessionLocal()
    try: yield db
    finally: db.close()


@app.post("/shorten")
async def shorten_url(
    request: Request, 
    url: str = Form(...), 
    custom_id: str = Form(None), 
    db: Session = Depends(get_db)
):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url="/", status_code=303)
    
    short_id = ""
    error_msg = None

    if custom_id and custom_id.strip():
        proposed_id = custom_id.strip().lower()

        # Da se ne stavi čć i slicno, pa ako radi problema maknuti
        if not re.match(r"^[a-z0-9\-_]+$", proposed_id):
            error_msg = "URL smije sadržavati samo slova, brojke i crtice."
        
        # Provjera rezerviranih riječi
        elif proposed_id in FORBIDDEN_IDS:
            error_msg = "Ovaj naziv je rezerviran za sustav."
        
        # Gledanje uniq
        else:
            existing = db.query(models.URL).filter(models.URL.short_id == proposed_id).first()
            if existing:
                error_msg = "Ovaj prilagođeni URL je već zauzet!"
            else:
                short_id = proposed_id
    else:
        # Ako nema custom_id, generiraj nasumični
        short_id = str(uuid.uuid4())[:6]

    # Error return 
    if error_msg:
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "user": user, "error": error_msg}
        )

    # 2. Spremanje u bazu
    try:
        db_url = models.URL(short_id=short_id, original_url=url)
        db.add(db_url)
        db.commit()
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            "index.html", 
            {"request": request, "user": user, "error": "Došlo je do pogreške pri spremanju."}
        )
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "user": user, 
            "short_url": f"https://skrati.kset.org/{short_id}"
        }
    )

@app.get("/{short_id}")
async def redirect_url(short_id: str, db: Session = Depends(get_db)):
    link = db.query(models.URL).filter(models.URL.short_id == short_id).first()
    if link:
        return RedirectResponse(url=link.original_url)
    raise HTTPException(status_code=404, detail="Link nije pronađen.")