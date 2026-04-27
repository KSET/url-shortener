import os
import uuid
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
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in .env file!")

app.add_middleware(
    SessionMiddleware, 
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=True
)

templates = Jinja2Templates(directory="templates")

# OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def get_db():
    db = models.SessionLocal()
    try: yield db
    finally: db.close()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if request.session.get('user'):
        return RedirectResponse(url='/dashboard')
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/login")
async def login(request: Request):
    if request.session.get('user'):
        return RedirectResponse(url='/dashboard')
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/oauth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get('userinfo')
    if user:
        request.session['user'] = dict(user)
    return RedirectResponse(url='/dashboard')

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/')
    return templates.TemplateResponse(request=request, name="index.html", context={"user": user})

@app.post("/shorten")
async def shorten_url(request: Request, url: str = Form(...), db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401)
    
    short_id = str(uuid.uuid4())[:6]
    db_url = models.URL(short_id=short_id, original_url=url)
    db.add(db_url)
    db.commit()
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"short_url": f"https://skrati.kset.org/{short_id}", "user": user}
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user or user.get('email') != "tadija75@gmail.com":
        return RedirectResponse(url='/')
    
    links = db.query(models.URL).all()
    return templates.TemplateResponse(request=request, name="admin.html", context={"links": links, "user": user})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url='/')

@app.get("/{short_id}")
async def redirect_url(short_id: str, db: Session = Depends(get_db)):
    link = db.query(models.URL).filter(models.URL.short_id == short_id).first()
    if link:
        return RedirectResponse(url=link.original_url)
    raise HTTPException(status_code=404)