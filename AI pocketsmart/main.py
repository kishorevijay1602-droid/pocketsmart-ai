import os
import asyncio
import secrets
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import quote

from dotenv import load_dotenv
load_dotenv()

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form,
    Request,
    Cookie,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from jose import JWTError, jwt
from google import genai
from google.genai import types


# =========================================================
# 1. PROJECT DIRECTORIES
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# =========================================================
# 2. FASTAPI INITIALIZATION
# =========================================================

app = FastAPI(
    title="PocketSmart AI Budget Planner",
    version="1.0.0",
    description="AI-powered smart budget and recommendation assistant",
)


# =========================================================
# 3. CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# 4. STATIC FILES
# =========================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


# =========================================================
# 5. SECURITY
# =========================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "pocketsmart-development-secret-key",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# =========================================================
# 6. GEMINI
# =========================================================

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError(
        "GEMINI_API_KEY is not set in the environment."
    )

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.6-flash"


# =========================================================
# 7. IN-MEMORY DATABASE
# =========================================================

users_db = {}
active_sessions = {}
recommendation_history = {}


def save_recommendation_history(
    username: str,
    planner: str,
    budget: float,
    details: str,
    recommendations: str = "",
    shopping_links: Optional[dict] = None,
):
    """Save one recommendation under the logged-in username."""

    username = username.strip()

    if not username:
        return

    if username not in recommendation_history:
        recommendation_history[username] = []

    recommendation_history[username].append(
        {
            "planner": planner,
            "budget": budget,
            "details": details,
            "recommendations": recommendations,
            "shopping_links": shopping_links or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    print("=" * 60)
    print("HISTORY SAVED")
    print("Username:", username)
    print("Planner:", planner)
    print("Total saved:", len(recommendation_history[username]))
    print("=" * 60)


# =========================================================
# 8. PYDANTIC MODELS
# =========================================================

class HomeBudgetInput(BaseModel):
    total_budget: float
    room_type: str
    num_items: int = 5
    additional_requirements: Optional[str] = ""


class PartyBudgetInput(BaseModel):
    total_budget: float
    party_type: str
    number_of_guests: int
    venue_type: Optional[str] = "not specified"


# =========================================================
# 9. PASSWORD HASHING
# =========================================================

def hash_password(password: str) -> str:
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return (
        hash_password(plain_password)
        == hashed_password
    )


# =========================================================
# 10. JWT
# =========================================================

def create_access_token(
    username: str,
    expires_delta: Optional[timedelta] = None,
):
    expire = (
        datetime.now(timezone.utc)
        + (
            expires_delta
            if expires_delta
            else timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
        )
    )

    payload = {
        "sub": username,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        username = payload.get("sub")

        if not username:
            return None

        return username

    except JWTError:
        return None


# =========================================================
# 11. SESSION MANAGEMENT
# =========================================================

def create_session(username: str):
    token = secrets.token_urlsafe(32)

    now = datetime.now(
        timezone.utc
    ).isoformat()

    active_sessions[token] = {
        "username": username,
        "login_time": now,
        "last_activity": now,
    }

    return token


def get_session(token: Optional[str]):
    if not token:
        return None

    return active_sessions.get(token)


def update_session_activity(token: str):
    if token in active_sessions:
        active_sessions[token]["last_activity"] = (
            datetime.now(timezone.utc).isoformat()
        )


# =========================================================
# 12. SESSION CLEANUP
# =========================================================

@app.on_event("startup")
async def setup_session_cleanup():

    async def cleanup_expired_sessions():
        while True:
            current_time = datetime.now(timezone.utc)
            expired_sessions = []

            for token, session in list(
                active_sessions.items()
            ):
                try:
                    last_activity = datetime.fromisoformat(
                        session["last_activity"]
                    )

                    inactive_seconds = (
                        current_time - last_activity
                    ).total_seconds()

                    if inactive_seconds > 1800:
                        expired_sessions.append(token)

                except (
                    KeyError,
                    ValueError,
                    TypeError,
                ):
                    expired_sessions.append(token)

            for token in expired_sessions:
                active_sessions.pop(token, None)

            await asyncio.sleep(300)

    asyncio.create_task(
        cleanup_expired_sessions()
    )


# =========================================================
# 13. CURRENT USER
# =========================================================

async def get_current_user(
    access_token: Optional[str] = Cookie(
        default=None
    ),
):
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    session = get_session(access_token)

    if not session:
        raise HTTPException(
            status_code=401,
            detail="Session expired or invalid",
        )

    username = session["username"]

    if username not in users_db:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    update_session_activity(access_token)

    return users_db[username]


# =========================================================
# 14. GEMINI HELPER
# =========================================================

def ask_gemini(
    prompt: str,
    image_bytes: Optional[bytes] = None,
    image_type: Optional[str] = None,
):
    max_attempts = 2

    for attempt in range(max_attempts):
        try:
            if image_bytes and image_type:
                image_part = types.Part.from_bytes(
                    data=image_bytes,
                    mime_type=image_type,
                )

                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        prompt,
                        image_part,
                    ],
                )
            else:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                )

            if response and response.text:
                return response.text

            return "Gemini returned an empty response."

        except Exception as e:
            error_message = str(e)

            print(
                f"Gemini attempt "
                f"{attempt + 1}/{max_attempts} failed:"
            )
            print(error_message)

            temporary = (
                "503" in error_message
                or "UNAVAILABLE" in error_message
                or "429" in error_message
                or "RESOURCE_EXHAUSTED" in error_message
            )

            if temporary and attempt < max_attempts - 1:
                import time
                time.sleep(2 ** attempt)
                continue

            break

    return (
        "Gemini is temporarily unavailable. "
        "Please try again in a few moments."
    )


# =========================================================
# 15. SHOPPING LINKS
# =========================================================

def create_search_links(search_text: str):
    query = quote(search_text)

    return {
        "amazon": f"https://www.amazon.in/s?k={query}",
        "flipkart": f"https://www.flipkart.com/search?q={query}",
        "meesho": f"https://www.meesho.com/search?q={query}",
    }


# =========================================================
# 16. HOME PLANNER PAGE
# =========================================================

@app.get(
    "/home-planner",
    response_class=HTMLResponse,
)
async def home_planner(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home_planner.html",
        context={},
    )


# =========================================================
# 17. HOME PLANNER GENERATION
# =========================================================

@app.post("/generate-home")
async def generate_home(
    request: Request,
    total_budget: float = Form(...),
    room_type: str = Form(...),
    num_items: int = Form(...),
    additional_requirements: str = Form(""),
):
    token = request.cookies.get("access_token")
    session = get_session(token)

    if not session:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    if total_budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than 0",
        )

    if num_items <= 0:
        raise HTTPException(
            status_code=400,
            detail="Number of items must be greater than 0",
        )

    username = session["username"]
    update_session_activity(token)

    prompt = f"""
You are PocketSmart AI Home Planner.

Create a practical home shopping plan for India.

Total Budget:
₹{total_budget}

Room Type:
{room_type}

Number of Items:
{num_items}

Additional Requirements:
{additional_requirements or "None"}

Suggest suitable home furniture and decor items.

For every item provide:

1. Item Name
2. Category
3. Quantity
4. Estimated Price
5. Total Cost
6. Reason for Recommendation

Keep the total estimated cost within the given budget.

Finally provide:

Estimated Total
Remaining Budget

Return the answer as clean plain text only.

Do not use Markdown.
Do not use asterisks.
Do not use hashtags.
Do not use Markdown tables.
Do not use special formatting symbols.

Use simple numbered sections.
Do not exceed the customer's budget.
"""

    ai_result = ask_gemini(prompt)

    links = create_search_links(
        f"{room_type} home furniture decor"
    )

    links["ikea"] = (
        "https://www.ikea.com/in/en/search/"
        f"?q={quote(room_type)}"
    )

    save_recommendation_history(
        username=username,
        planner="Home Planner",
        budget=total_budget,
        details=(
            f"Room: {room_type} | "
            f"Items: {num_items}"
        ),
        recommendations=ai_result,
        shopping_links=links,
    )

    return templates.TemplateResponse(
        request=request,
        name="home_result.html",
        context={
            "budget": total_budget,
            "room_type": room_type,
            "num_items": num_items,
            "recommendations": ai_result,
            "shopping_links": links,
        },
    )


# =========================================================
# 18. PARTY PLANNER PAGE
# =========================================================

@app.get(
    "/party-planner",
    response_class=HTMLResponse,
)
async def party_planner(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="party_planner.html",
        context={},
    )


# =========================================================
# 19. PARTY PLANNER GENERATION
# =========================================================

@app.post("/generate-party")
async def generate_party(
    request: Request,
    total_budget: float = Form(...),
    party_type: str = Form(...),
    number_of_guests: int = Form(...),
    venue_type: str = Form(...),
):
    token = request.cookies.get("access_token")
    session = get_session(token)

    if not session:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    if total_budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than 0",
        )

    if number_of_guests <= 0:
        raise HTTPException(
            status_code=400,
            detail="Number of guests must be greater than 0",
        )

    username = session["username"]
    update_session_activity(token)

    prompt = f"""
You are PocketSmart AI Party Planner.

Create a practical party plan for India.

Total budget:
₹{total_budget}

Party type:
{party_type}

Number of guests:
{number_of_guests}

Venue:
{venue_type}

Suggest:

1. Food
2. Decorations
3. Venue/services
4. Entertainment
5. Other necessary items

For every item provide:

Item name
Quantity
Estimated price
Total cost

Keep the total within the given budget.

Finally provide:

Estimated total
Remaining budget

Return the answer as clean plain text only.

Do not use Markdown.
Do not use asterisks.
Do not use hashtags.
Do not use Markdown tables.
Do not use special formatting symbols.

Use simple numbered sections.
Do not exceed the customer's budget.
"""

    ai_result = ask_gemini(prompt)

    links = create_search_links(
        f"{party_type} party food decoration"
    )

    links["zomato"] = (
        "https://www.zomato.com/search"
        f"?query={quote(party_type + ' party food')}"
    )

    save_recommendation_history(
        username=username,
        planner="Party Planner",
        budget=total_budget,
        details=(
            f"Party: {party_type} | "
            f"Guests: {number_of_guests} | "
            f"Venue: {venue_type}"
        ),
        recommendations=ai_result,
        shopping_links=links,
    )

    return templates.TemplateResponse(
        request=request,
        name="party_result.html",
        context={
            "planner": "party",
            "budget": total_budget,
            "party_type": party_type,
            "number_of_guests": number_of_guests,
            "venue_type": venue_type,
            "recommendations": ai_result,
            "shopping_links": links,
        },
    )


# =========================================================
# 20. JEWELRY PLANNER PAGE
# =========================================================

@app.get(
    "/jewelry-planner",
    response_class=HTMLResponse,
)
async def jewelry_planner(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="jewelry_planner.html",
        context={},
    )


# =========================================================
# 21. JEWELRY PLANNER GENERATION
# =========================================================

@app.post("/generate-jewelry")
async def generate_jewelry(
    request: Request,
    total_budget: float = Form(...),
    occasion: str = Form(...),
    jewelry_type: str = Form(...),
    additional_requirements: str = Form(""),
    image: Optional[UploadFile] = File(None),
):
    token = request.cookies.get("access_token")
    session = get_session(token)

    if not session:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    if total_budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than 0",
        )

    username = session["username"]
    update_session_activity(token)

    image_bytes = None
    image_type = None
    saved_image = None

    if image and image.filename:
        allowed_types = {
            "image/jpeg",
            "image/png",
            "image/webp",
        }

        if image.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Only JPG, PNG and WEBP "
                    "images are supported."
                ),
            )

        image_bytes = await image.read()

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="Uploaded image is empty.",
            )

        if len(image_bytes) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Image size must be 10 MB or less.",
            )

        image_type = image.content_type

        extension = Path(
            image.filename
        ).suffix.lower()

        if extension not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }:
            extension = ".jpg"

        file_name = (
            secrets.token_hex(8)
            + extension
        )

        file_path = UPLOAD_DIR / file_name
        file_path.write_bytes(image_bytes)

        saved_image = (
            f"/static/uploads/{file_name}"
        )

    prompt = f"""
You are PocketSmart AI Jewelry Planner.

Create a practical jewelry recommendation
for a customer in India.

Customer details:

Total Budget:
₹{total_budget}

Occasion:
{occasion}

Jewelry Type:
{jewelry_type}

Additional Requirements:
{additional_requirements or "None"}

Suggest suitable jewelry options within
the customer's budget.

For every recommendation provide:

1. Jewelry Name
2. Jewelry Type
3. Suggested Material
4. Quantity
5. Estimated Price
6. Reason for Recommendation

Keep all recommendations practical and
make sure the total estimated cost stays
within the given budget.

Finally provide:

Estimated Total
Remaining Budget

Return the answer as clean plain text only.

Do not use Markdown.
Do not use asterisks.
Do not use hashtags.
Do not use Markdown tables.
Do not use special formatting symbols.

Use simple numbered sections.
Do not exceed the customer's budget.
"""

    ai_result = ask_gemini(
        prompt,
        image_bytes=image_bytes,
        image_type=image_type,
    )

    links = create_search_links(
        f"{occasion} {jewelry_type} jewelry"
    )

    save_recommendation_history(
        username=username,
        planner="Jewelry Planner",
        budget=total_budget,
        details=(
            f"Occasion: {occasion} | "
            f"Jewelry Type: {jewelry_type}"
        ),
        recommendations=ai_result,
        shopping_links=links,
    )

    return templates.TemplateResponse(
        request=request,
        name="jewelry_result.html",
        context={
            "planner": "jewelry",
            "budget": total_budget,
            "occasion": occasion,
            "jewelry_type": jewelry_type,
            "additional_requirements": (
                additional_requirements
            ),
            "recommendations": ai_result,
            "shopping_links": links,
            "image_uploaded": (
                image_bytes is not None
            ),
            "saved_image": saved_image,
        },
    )


# =========================================================
# 22. ROOT
# =========================================================

@app.get(
    "/",
    response_class=HTMLResponse,
)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


# =========================================================
# 23. REGISTER PAGE
# =========================================================

@app.get(
    "/register",
    response_class=HTMLResponse,
)
async def register_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={},
    )


# =========================================================
# 24. REGISTER
# =========================================================

@app.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(""),
):
    username = username.strip()

    if not username:
        return HTMLResponse(
            "<h2>Username is required</h2>",
            status_code=400,
        )

    if username in users_db:
        return HTMLResponse(
            """
            <h2>Registration failed</h2>
            <p>Username already exists.</p>
            <a href="/register">Try again</a>
            """,
            status_code=400,
        )

    if len(password) < 6:
        return HTMLResponse(
            """
            <h2>Registration failed</h2>
            <p>Password must contain at least 6 characters.</p>
            <a href="/register">Try again</a>
            """,
            status_code=400,
        )

    users_db[username] = {
        "username": username,
        "email": email,
        "password": hash_password(password),
    }

    return RedirectResponse(
        url="/login",
        status_code=303,
    )


# =========================================================
# 25. LOGIN PAGE
# =========================================================

@app.get(
    "/login",
    response_class=HTMLResponse,
)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={},
    )


# =========================================================
# 26. LOGIN
# =========================================================

@app.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
):
    username = username.strip()
    user = users_db.get(username)

    if not user:
        return HTMLResponse(
            """
            <h2>Login failed</h2>
            <p>User not found.</p>
            <a href="/login">Try again</a>
            """,
            status_code=401,
        )

    if not verify_password(
        password,
        user["password"],
    ):
        return HTMLResponse(
            """
            <h2>Login failed</h2>
            <p>Invalid password.</p>
            <a href="/login">Try again</a>
            """,
            status_code=401,
        )

    session_token = create_session(username)

    response = RedirectResponse(
        url="/dashboard",
        status_code=303,
    )

    response.set_cookie(
        key="access_token",
        value=session_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )

    return response


# =========================================================
# 27. TOKEN LOGIN
# =========================================================

@app.post("/token")
async def token_login(
    username: str = Form(...),
    password: str = Form(...),
):
    username = username.strip()
    user = users_db.get(username)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    if not verify_password(
        password,
        user["password"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(
        username,
        timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )

    session_token = create_session(username)

    response = JSONResponse(
        {
            "access_token": access_token,
            "session_token": session_token,
            "token_type": "bearer",
            "expires_in": (
                ACCESS_TOKEN_EXPIRE_MINUTES * 60
            ),
        }
    )

    response.set_cookie(
        key="access_token",
        value=session_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )

    return response


# =========================================================
# 28. DASHBOARD
# =========================================================

@app.get(
    "/dashboard",
    response_class=HTMLResponse,
)
async def dashboard(request: Request):
    token = request.cookies.get("access_token")
    session = get_session(token)

    if not session:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    username = session["username"]
    update_session_activity(token)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "username": username,
        },
    )


# =========================================================
# 29. HISTORY
# =========================================================

@app.get(
    "/history",
    response_class=HTMLResponse,
)
async def history(request: Request):
    token = request.cookies.get("access_token")
    session = get_session(token)

    if not session:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    username = session["username"]
    update_session_activity(token)

    user_history = recommendation_history.get(
        username,
        [],
    )

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "username": username,
            "history": user_history,
        },
    )


# =========================================================
# 30. HISTORY DETAIL
# =========================================================

@app.get(
    "/history/{history_id}",
    response_class=HTMLResponse,
)
async def view_history(
    request: Request,
    history_id: int,
):
    token = request.cookies.get("access_token")
    session = get_session(token)

    if not session:
        return RedirectResponse(
            url="/login",
            status_code=303,
        )

    username = session["username"]
    update_session_activity(token)

    user_history = recommendation_history.get(
        username,
        [],
    )

    if (
        history_id < 0
        or history_id >= len(user_history)
    ):
        raise HTTPException(
            status_code=404,
            detail="History item not found",
        )

    selected_plan = user_history[history_id]

    return templates.TemplateResponse(
        request=request,
        name="history_detail.html",
        context={
            "username": username,
            "plan": selected_plan,
        },
    )


# =========================================================
# 31. SESSION INFO
# =========================================================

@app.get("/session-info")
async def session_info(request: Request):
    token = request.cookies.get("access_token")
    session = get_session(token)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="No active session found",
        )

    update_session_activity(token)

    login_time = datetime.fromisoformat(
        session["login_time"]
    )

    current_time = datetime.now(timezone.utc)

    duration = (
        current_time - login_time
    ).total_seconds()

    return {
        "username": session["username"],
        "login_time": session["login_time"],
        "last_activity": session["last_activity"],
        "session_duration_minutes": round(
            duration / 60,
            2,
        ),
        "login_status": "active",
    }


# =========================================================
# 32. SESSION DATA
# =========================================================

@app.put("/session-data")
async def update_session_data(
    data: dict,
    request: Request,
):
    token = request.cookies.get("access_token")
    session = get_session(token)

    if not session:
        raise HTTPException(
            status_code=404,
            detail="No active session found",
        )

    username = session["username"]

    if username not in users_db:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    users_db[username]["session_data"] = data
    update_session_activity(token)

    return {
        "message": "Session data updated successfully",
        "username": username,
        "data": data,
    }


# =========================================================
# 33. LOGOUT
# =========================================================

@app.api_route(
    "/logout",
    methods=["GET", "POST"],
)
async def logout(request: Request):
    token = request.cookies.get("access_token")

    if token and token in active_sessions:
        del active_sessions[token]

    response = RedirectResponse(
        url="/login",
        status_code=303,
    )

    response.delete_cookie("access_token")

    return response


# =========================================================
# 34. HEALTH
# =========================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "PocketSmart AI Budget Planner",
        "gemini_model": MODEL_NAME,
        "static_routing": "enabled",
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# =========================================================
# 35. API INFO
# =========================================================

@app.get("/api/info")
async def api_info():
    return {
        "application": "PocketSmart AI",
        "version": "1.0.0",
        "framework": "FastAPI",
        "ai_model": MODEL_NAME,
        "features": [
            "Home Budget Planner",
            "Party Budget Planner",
            "Jewelry Recommendation",
            "Image Analysis",
            "Gemini AI Integration",
            "User Registration",
            "User Login",
            "Session Management",
            "JWT Authentication",
            "Shopping Recommendations",
            "Recommendation History",
            "Saved Plan View",
            "CORS Configuration",
            "Static File Routing",
        ],
    }


# =========================================================
# 36. STARTUP
# =========================================================

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("PocketSmart AI Budget Planner starting...")
    print(f"Gemini model: {MODEL_NAME}")
    print(f"Static directory: {STATIC_DIR}")
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"Templates directory: {TEMPLATES_DIR}")
    print("=" * 60)


# =========================================================
# 37. MAIN
# =========================================================

if __name__ == "__main__":
    import uvicorn

    print(
        "Starting PocketSmart AI Budget Planner..."
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
    )
