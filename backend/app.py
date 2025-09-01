# backend/app.py
from __future__ import annotations

from uuid import uuid4
from pathlib import Path
from typing import List, Set, Dict, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, Field

from utils import (
    load_words,
    choose_secret,
    is_valid_letter,
    compute_status,
    DIFFICULTY,
)

# -------------------- FastAPI app --------------------
app = FastAPI(title="Hangman API", version="0.1.0")

# If you later serve frontend from the same origin (recommended), CORS can be permissive or removed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # you can lock this down later to your exact origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Models --------------------
Difficulty = Literal["easy", "normal", "hard"]

class NewGameRequest(BaseModel):
    difficulty: Difficulty

class GuessRequest(BaseModel):
    game_id: str = Field(..., min_length=8)
    letter: str

class RestartRequest(BaseModel):
    game_id: str
    difficulty: Optional[Difficulty] = None

class GameResponse(BaseModel):
    game_id: str
    masked: str
    lives: int
    wrong: List[str]
    won: bool
    lost: bool

class GameState(BaseModel):
    # Server-side only; never returned directly to clients
    difficulty: Difficulty
    secret: str
    lives: int
    guessed: Set[str]

# In-memory games store (resets when server restarts; fine for development)
games: Dict[str, GameState] = {}

# -------------------- Internal helpers --------------------
def _new_game_state(difficulty: Difficulty) -> GameState:
    words = load_words(difficulty)
    secret = choose_secret(words)
    lives = DIFFICULTY[difficulty]["lives"]
    return GameState(difficulty=difficulty, secret=secret, lives=lives, guessed=set())

def _normalize_letter(s: str) -> str:
    return s.strip().lower()

def _response(game_id: str, gs: GameState) -> GameResponse:
    status = compute_status(gs.secret, gs.guessed, gs.lives)
    return GameResponse(
        game_id=game_id,
        masked=status["masked"],
        lives=status["lives"],
        wrong=status["wrong"],
        won=status["won"],
        lost=status["lost"],
    )

# -------------------- API routes --------------------
@app.post("/api/new", response_model=GameResponse)
def api_new(req: NewGameRequest):
    gid = uuid4().hex
    gs = _new_game_state(req.difficulty)
    games[gid] = gs
    return _response(gid, gs)

@app.post("/api/guess", response_model=GameResponse)
def api_guess(req: GuessRequest):
    gs = games.get(req.game_id)
    if not gs:
        raise HTTPException(status_code=404, detail="Unknown game_id")

    # --- Normalize input (letter OR word) ---
    raw = req.letter.strip().lower()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty guess")

    # If the game already ended, just return current snapshot
    snap = compute_status(gs.secret, gs.guessed, gs.lives)
    if snap["won"] or snap["lost"]:
        return _response(req.game_id, gs)

    # --- Branch: single-letter vs full-word guess ---
    if len(raw) == 1:
        # Validate letter
        if not is_valid_letter(raw):
            raise HTTPException(status_code=400, detail="Invalid letter: must be a single A–Z character")
        # Ignore duplicate letters
        if raw in gs.guessed:
            return _response(req.game_id, gs)
        # Apply letter guess
        gs.guessed.add(raw)
        if raw not in gs.secret:
            gs.lives -= 1  # penalty for wrong letter
        return _response(req.game_id, gs)

    else:
        # Full word guess
        # (Use utils.is_valid_word if you added it; otherwise simple check)
        if not raw.isalpha():
            raise HTTPException(status_code=400, detail="Invalid word: only letters allowed")

        if raw == gs.secret:
            # Mark all letters as guessed so 'won' becomes True
            gs.guessed.update(set(gs.secret))
            return _response(req.game_id, gs)
        else:
            # Penalty for wrong word guess. Choose your rule:
            # Option A: -2 lives (harsher)
            # Option B: -1 life (same as letter)
            # Pick one:
            gs.lives -= 2
            if gs.lives < 0:
                gs.lives = 0
            return _response(req.game_id, gs)

@app.post("/api/restart", response_model=GameResponse)
def api_restart(req: RestartRequest):
    prev = games.get(req.game_id)
    if prev:
        diff: Difficulty = req.difficulty or prev.difficulty  # type: ignore
        games[req.game_id] = _new_game_state(diff)
        return _response(req.game_id, games[req.game_id])

    # No such game id — create a brand new one
    new_gid = uuid4().hex
    diff = req.difficulty or "normal"
    games[new_gid] = _new_game_state(diff)  # type: ignore
    return _response(new_gid, games[new_gid])

@app.get("/health")
def health():
    return {"ok": True}

# -------------------- Serve the frontend (SAFE) --------------------
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Log the path so you can see it in the console
print(f"[INFO] Serving frontend from: {FRONTEND_DIR}")

if not FRONTEND_DIR.exists():
    print(f"[WARN] Frontend folder not found at: {FRONTEND_DIR}")
else:
    # 1) Serve all static assets (css/js/images) at /assets/...
# 1) Serve all static assets (css/js/images) at /assets/...
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIR / "assets"), html=False),
        name="assets"
    )


    # 2) Serve the main HTML at /
    @app.get("/")
    def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")
