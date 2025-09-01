# utils.py
import random
from pathlib import Path

from typing import TypedDict, List

class GameStatus(TypedDict):
    masked: str
    wrong: List[str]
    lives: int
    won: bool
    lost: bool

DIFFICULTY = {
    "easy":   {"min_len": 5, "max_len": 6, "lives": 10, "file": "words_easy.txt"},
    "normal": {"min_len": 6, "max_len": 8, "lives": 7,  "file": "words_normal.txt"},
    "hard":   {"min_len": 7, "max_len": 99, "lives": 5, "file": "words_hard.txt"},
}

def load_words(difficulty: str) -> list[str]:
    if difficulty not in DIFFICULTY:
        raise ValueError(f"Unknown difficulty: {difficulty!r}. Use easy|normal|hard.")
    cfg = DIFFICULTY[difficulty]
    path = Path(__file__).with_name(cfg["file"])
    if not path.exists():
        raise FileNotFoundError(f"Word list not found: {path}")
    seen = set()
    words: list[str] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            w = line.strip().lower()
            if not w or (not w.isalpha()):
                continue
            if not (cfg["min_len"]<= len(w) <= cfg["max_len"]):
                continue
            if w in seen:
                continue
            seen.add(w)
            words.append(w)
    return words

def choose_secret(words: list[str]) -> str:
    assert words, "Word list is empty—check your txt files/filters."
    return random.choice(words)

def is_valid_letter(ch:str) -> bool:
    ch = ch.strip()

    if len(ch) != 1:
        return False
    if not ch.isalpha():
        return False
    return True

def is_valid_word(s: str) -> bool:
    """
    Accept a-z words (2+ chars). You can loosen/tighten this later.
    """
    s = s.strip().lower()
    return len(s) >= 2 and s.isalpha()


def mask_word(secret: str, guessed_letters: set[str]) -> str:
    pieces: list[str] = []
    for c in secret:
        if c in guessed_letters:
            pieces.append(c)
        else:
            pieces.append("_")
    return " ".join(pieces)

def compute_status(secret: str, guessed_letters: set[str], lives: int) -> dict:
    masked = mask_word(secret, guessed_letters)
    wrong_letters = sorted([ch for ch in guessed_letters if ch not in secret])
    unique_letters_in_secret = set(secret)
    won = unique_letters_in_secret.issubset(guessed_letters)
    lost = lives <= 0
    return {
        "masked": masked,
        "wrong": wrong_letters,
        "lives": lives,
        "won": won,
        "lost": lost,
    }

def normalize_guess(ch: str) -> str:
    return ch.strip().lower()

if __name__ == "__main__":
    # 1) load_words basic checks (comment out if you don’t have files in place)
    # for diff in ("easy", "normal", "hard"):
    #     ws = load_words(diff)
    #     mn, mx = DIFFICULTY[diff]["min_len"], DIFFICULTY[diff]["max_len"]
    #     assert ws, f"No words loaded for {diff}"
    #     assert all(mn <= len(w) <= mx for w in ws), f"Length filter failed for {diff}"

    # 2) choose_secret
    assert choose_secret(["a","b","c"]) in {"a","b","c"}

    # 3) is_valid_letter
    assert is_valid_letter("a") and is_valid_letter("Z")
    assert not is_valid_letter("ab")
    assert not is_valid_letter("7")
    assert not is_valid_letter("!")
    assert not is_valid_letter(" ")

    # 4) mask_word
    assert mask_word("apple", {"a","e"}).replace(" ", "") == "a___e"
    assert mask_word("banana", {"b","n"}).replace(" ", "") == "b_n_n_"
    assert mask_word("test", set()).replace(" ", "") == "____"

    # 5) compute_status
    st = compute_status("banana", {"b","n"}, 5)
    assert st["masked"].replace(" ", "") == "b_n_n_"
    assert st["wrong"] == []
    assert not st["won"] and not st["lost"]

    st = compute_status("banana", {"b","n","x"}, 4)
    assert st["wrong"] == ["x"]
    assert not st["won"]

    st = compute_status("banana", {"a","b","n"}, 3)
    assert st["won"]

    st = compute_status("apple", {"x","y"}, 0)
    assert st["lost"]

    print("All helper tests passed ✅")
