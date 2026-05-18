import os
import uuid
<<<<<<< Updated upstream
import re
=======
import datetime
from pathlib import Path
from dotenv import load_dotenv
>>>>>>> Stashed changes
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from sqlalchemy.orm import Session
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw, ImageFilter, ImageFont

load_dotenv()

from . import models

# Inicijalizacija baze
models.init_db()

app = FastAPI(docs_url=None, redoc_url=None)
BASE_URL = os.getenv("BASE_URL", "https://skrati.kset.org").rstrip("/")
QR_BOX_SIZE = int(os.getenv("QR_BOX_SIZE", "32"))
STATIC_DIR = Path("static")
QR_DIR = STATIC_DIR / "qr"
QR_TEMPLATE_DIR = STATIC_DIR / "qr_templates"

QR_TEMPLATES = {
    "general": {
        "name": "Generalno",
        "file": "general.png",
        "background": "#0f172a",
        "accent": "#38bdf8",
        "text": "KSET",
    },
    "kset-na-krku": {
        "name": "KSET na Krku",
        "file": "kset-na-krku.png",
        "background": "#0369a1",
        "accent": "#facc15",
        "text": "KRK",
    },
    "job-fair": {
        "name": "Job Fair",
        "file": "job-fair.png",
        "background": "#7c2d12",
        "accent": "#22c55e",
        "text": "JOB",
    },
}

def setup_static_assets():
    QR_DIR.mkdir(parents=True, exist_ok=True)
    QR_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    for template in QR_TEMPLATES.values():
        badge_path = QR_TEMPLATE_DIR / template["file"]
        if badge_path.exists():
            continue

        image = Image.new("RGBA", (512, 512), template["background"])
        draw = ImageDraw.Draw(image)
        draw.ellipse((44, 44, 468, 468), fill=template["accent"])
        draw.ellipse((78, 78, 434, 434), fill=template["background"])

        try:
            font = ImageFont.truetype("arial.ttf", 126)
        except OSError:
            font = ImageFont.load_default()

        text = template["text"]
        text_box = draw.textbbox((0, 0), text, font=font)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
        draw.text(
            ((512 - text_width) / 2, (512 - text_height) / 2 - 10),
            text,
            fill="white",
            font=font,
        )
        image.save(badge_path)

def generate_qr_code(short_url: str, short_id: str, template_key: str) -> str:
    template = QR_TEMPLATES.get(template_key, QR_TEMPLATES["general"])
    qr_path = QR_DIR / f"{short_id}.png"
    logo_path = QR_TEMPLATE_DIR / template["file"]

    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=QR_BOX_SIZE,
        border=4,
    )
    qr.add_data(short_url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    total_modules = qr.modules_count + (qr.border * 2)
    backplate_modules = max(7, round(total_modules * 0.28))
    if backplate_modules % 2 == 0:
        backplate_modules += 1

    backplate_size = backplate_modules * QR_BOX_SIZE
    padding = max(QR_BOX_SIZE // 2, int(backplate_size * 0.1))
    logo_size = backplate_size - padding * 2

    logo = Image.open(logo_path).convert("RGBA")
    logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
    logo = logo.filter(ImageFilter.UnsharpMask(radius=1.0, percent=220, threshold=1))

    box = Image.new("RGBA", (backplate_size, backplate_size), "white")
    box_draw = ImageDraw.Draw(box)
    box_draw.rectangle(
        (0, 0, backplate_size - 1, backplate_size - 1),
        fill="white",
        outline=(226, 232, 240, 255),
        width=max(1, QR_BOX_SIZE // 12),
    )
    logo_position = ((backplate_size - logo.size[0]) // 2, (backplate_size - logo.size[1]) // 2)
    box.paste(logo, logo_position, logo)

    position_modules = (total_modules - backplate_modules) // 2
    position = (position_modules * QR_BOX_SIZE, position_modules * QR_BOX_SIZE)
    image.paste(box, position, box)
    image.save(qr_path)
    return f"/static/qr/{short_id}.png"

setup_static_assets()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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
<<<<<<< Updated upstream
    return RedirectResponse(url='/')
=======
    return RedirectResponse(url='/dashboard')

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get('user')
    if not user:
        return RedirectResponse(url='/')
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"user": user, "qr_templates": QR_TEMPLATES},
    )

@app.post("/shorten")
async def shorten_url(
    request: Request,
    url: str = Form(...),
    qr_template: str = Form("general"),
    db: Session = Depends(get_db),
):
    user = request.session.get('user')
    if not user:
        raise HTTPException(status_code=401)

    if qr_template not in QR_TEMPLATES:
        qr_template = "general"
    
    short_id = str(uuid.uuid4())[:6]
    while db.query(models.URL).filter(models.URL.short_id == short_id).first():
        short_id = str(uuid.uuid4())[:6]

    short_url = f"{BASE_URL}/{short_id}"
    qr_code_path = generate_qr_code(short_url, short_id, qr_template)
    db_url = models.URL(
        short_id=short_id,
        original_url=url,
        qr_template=qr_template,
        qr_code_path=qr_code_path,
    )
    db.add(db_url)
    db.commit()
    
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "short_url": short_url,
            "qr_code_path": qr_code_path,
            "selected_template": qr_template,
            "qr_templates": QR_TEMPLATES,
            "user": user,
        }
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user or user.get('email') != "tadija75@gmail.com":
        return RedirectResponse(url='/')
    
    links = db.query(models.URL).order_by(models.URL.created_at.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"links": links, "user": user, "base_url": BASE_URL, "qr_templates": QR_TEMPLATES},
    )

@app.post("/edit/{link_id}")
async def edit_link(
    request: Request,
    link_id: int,
    new_url: str = Form(...),
    db: Session = Depends(get_db),
):
    user = request.session.get('user')
    if not user or user.get('email') != "tadija75@gmail.com":
        raise HTTPException(status_code=401)

    link = db.query(models.URL).filter(models.URL.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404)

    link.original_url = new_url
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/delete/{link_id}")
async def delete_link(request: Request, link_id: int, db: Session = Depends(get_db)):
    user = request.session.get('user')
    if not user or user.get('email') != "tadija75@gmail.com":
        raise HTTPException(status_code=401)

    link = db.query(models.URL).filter(models.URL.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404)

    if link.qr_code_path:
        qr_path = Path(link.qr_code_path.lstrip("/"))
        if qr_path.exists():
            qr_path.unlink()

    db.delete(link)
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)
>>>>>>> Stashed changes

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
            request=request, name="index.html", context={"user": user, "error": error_msg,"url":url}
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
        link.click_count = (link.click_count or 0) + 1
        link.last_clicked_at = datetime.datetime.utcnow()
        db.commit()
        return RedirectResponse(url=link.original_url)
<<<<<<< Updated upstream
    raise HTTPException(status_code=404, detail="Link nije pronađen.")
=======
    raise HTTPException(status_code=404)
>>>>>>> Stashed changes
