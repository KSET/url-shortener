import os
import uuid
import re
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
from . import models

# Inicijalizacija baze
models.init_db()

app = FastAPI(docs_url=None, redoc_url=None)

# Middleware
SECRET_KEY = os.getenv("SECRET_KEY")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

templates = Jinja2Templates(directory="templates")

# OAuth Setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

FORBIDDEN_IDS = {"admin", "login", "logout", "dashboard", "oauth", "shorten", "static"}

def get_db():
    db = models.SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user = request.session.get('user')
    if user:
        # Prvi argument mora biti request, ime templatea ide pod 'name'
        return templates.TemplateResponse(
            request=request, name="index.html", context={"user": user}
        )
    return templates.TemplateResponse(
        request=request, name="login.html", context={}
    )

@app.get("/login")
async def login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/oauth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get('userinfo')
    if user:
        request.session['user'] = dict(user)
    return RedirectResponse(url='/')

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/')

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user or user.get('email') != "tadija75@gmail.com":
        raise HTTPException(status_code=403, detail="Pristup odbijen")
    
    links = db.query(models.URL).all()
    return templates.TemplateResponse(
        request=request, name="admin.html", context={"links": links, "user": user}
    )

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
        if not re.match(r"^[a-z0-9\-_]+$", proposed_id):
            error_msg = "URL smije sadržavati samo slova, brojke i crtice."
        elif proposed_id in FORBIDDEN_IDS:
            error_msg = "Ovaj naziv je rezerviran za sustav."
        else:
            existing = db.query(models.URL).filter(models.URL.short_id == proposed_id).first()
            if existing:
                error_msg = "Ovaj prilagođeni URL je već zauzet!"
            else:
                short_id = proposed_id
    else:
        short_id = str(uuid.uuid4())[:6]

    if error_msg:
        return templates.TemplateResponse(
            request=request, name="index.html", context={"user": user, "error": error_msg}
        )

    try:
        db_url = models.URL(short_id=short_id, original_url=url)
        db.add(db_url)
        db.commit()
    except Exception as e:
        db.rollback()
        return templates.TemplateResponse(
            request=request, name="index.html", context={"user": user, "error": "Pogreška pri spremanju."}
        )
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
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