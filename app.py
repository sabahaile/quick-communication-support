# app.py
# Run:
#   .\.venv\Scripts\Activate.ps1
#   pip install streamlit
#   streamlit run app.py

from __future__ import annotations

import json
import random
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Literal, Optional, Set, Tuple, Union

import streamlit as st

Scope = Literal["activities", "places"]

# -----------------------------
# DATA 
# -----------------------------
GENERIC_PHRASES = [
    "Can I have a moment, please?",
    "I know what I mean — I just need a second.",
    "Please give me a moment to organise my words.",
    "The word is on the tip of my tongue.",
    "I’m stuck — can I try again in a moment?",
    "Could you repeat the question, please?",
    "Can you say that more slowly?",
    "Sorry — my brain froze for a second.",
    "Let me restart that sentence.",
]

ACTIVITIES: Dict[str, List[str]] = {
    "Presentation": [
        "Let me restart that sentence.",
        "I’m nervous, but I understand the answer.",
        "I want to answer — I just need a moment.",
        "Can I quickly rephrase that?",
        "One second — I’m collecting my thoughts.",
    ],
    "Lecture": [
        "Could you repeat that last part, please?",
        "Can you say that more slowly?",
        "I’m following — give me a second to write it down.",
        "Can I ask a quick clarification?",
    ],
    "Exam": [
        "I understand — can I restate it in my own words?",
        "I know the answer — I just need a second.",
        "Can I have a moment to organise my words?",
        "Sorry — I’m stuck for a second. Let me try again.",
    ],
    "Games": [
        "Wait — my tongue is lagging 😂",
        "Give me a second, I’ll say it.",
        "I know what I want to say — one sec!",
        "Hold on — let me restart.",
    ],
    "Friends": [
        "Bro my tongue is protesting 😭",
        "Waittt — I’ll say it again 😂",
        "I swear I know the word… give me a sec 😅",
        "Let me restart before you roast me 😭",
        "My brain froze — not me!",
    ],
}

PLACES: Dict[str, List[str]] = {
    "Class": [
        "Can I have a moment, please?",
        "I know the answer — I just need a second.",
        "Sorry — I’m stuck for a second. Let me try again.",
        "Can you repeat the question, please?",
    ],
    "Library": [
        "Sorry — can you say that more slowly?",
        "One second — I’m thinking.",
        "Can I rephrase that?",
    ],
    "Hall": [
        "I’m stuck — can I try again in a moment?",
        "Give me a moment to organise my words.",
    ],
    "Gym": [
        "Wait — let me restart 😅",
        "One sec — I’ll say it.",
    ],
    "School Gate": [
        "Sorry — my brain froze for a second.",
        "Can I have a moment, please?",
    ],
    "Basketball Court": [
        "Wait — my tongue is lagging 😂",
        "Give me a second, I’ll say it.",
    ],
}

# -----------------------------
# ROUTING
# -----------------------------
@dataclass(frozen=True)
class Route:
    name: Literal["home", "scope_list", "category", "display", "favorites", "fullscreen"]
    scope: Optional[Scope] = None
    category: Optional[str] = None


def _route_dict(r: Route) -> dict:
    return {"name": r.name, "scope": r.scope, "category": r.category}


def get_route() -> Route:
    r = st.session_state.route
    return Route(r["name"], r.get("scope"), r.get("category"))


def go(route: Route) -> None:
    """Navigation memory: push current route into nav_stack, then go to target route."""
    current = st.session_state.get("route")
    if current:
        st.session_state.nav_stack.append(current)
        if len(st.session_state.nav_stack) > 50:
            st.session_state.nav_stack = st.session_state.nav_stack[-50:]
    st.session_state.route = _route_dict(route)


def nav_back(default: Route = Route("home")) -> None:
    if st.session_state.nav_stack:
        st.session_state.route = st.session_state.nav_stack.pop()
    else:
        st.session_state.route = _route_dict(default)


# -----------------------------
# TEXT HELPERS (search)
# -----------------------------
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def tokens(text: str) -> List[str]:
    return re.findall(r"[a-z0-9']+", normalize(text))


def score_text(query: str, text: str) -> float:
    """Token overlap + substring boost."""
    q = normalize(query)
    t = normalize(text)
    if not q:
        return 0.0

    q_toks = set(tokens(q))
    t_toks = set(tokens(t))
    overlap = len(q_toks & t_toks)

    substr = 2.0 if q in t else 0.0
    exact = 4.0 if q == t else 0.0
    return float(overlap) + substr + exact


def dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


# -----------------------------
# DATA ACCESS HELPERS
# -----------------------------
def base_map(scope: Scope) -> Dict[str, List[str]]:
    return ACTIVITIES if scope == "activities" else PLACES


def all_categories(scope: Scope) -> List[str]:
    return list(base_map(scope).keys())


def all_phrases_global() -> List[str]:
    out: List[str] = list(GENERIC_PHRASES)
    for sc in ("activities", "places"):
        for arr in base_map(sc).values():  # type: ignore[arg-type]
            out.extend(arr)
        for arr in st.session_state.custom_phrases[sc].values():  # type: ignore[index]
            out.extend(arr)
    return dedupe_keep_order(out)


def phrases_for(scope: Scope, category: str) -> List[str]:
    base = base_map(scope).get(category, [])
    custom = st.session_state.custom_phrases[scope].get(category, [])
    return dedupe_keep_order(base + custom + GENERIC_PHRASES)


# -----------------------------
# PERSISTENCE (JSON storage)
# -----------------------------
DATA_DIR = Path(__file__).parent / "data"
STATE_PATH = DATA_DIR / "qcs_state.json"


def _repair_loaded(obj: object) -> Tuple[Set[str], Dict[str, Dict[str, List[str]]], str]:
    favs: List[str] = []
    custom: Dict[str, Dict[str, List[str]]] = {"activities": {}, "places": {}}
    selected = ""

    if isinstance(obj, dict):
        if isinstance(obj.get("favorites"), list):
            favs = [str(x) for x in obj.get("favorites", [])]
        if isinstance(obj.get("custom_phrases"), dict):
            raw = obj.get("custom_phrases", {})
            if isinstance(raw.get("activities"), dict):
                custom["activities"] = {
                    str(k): [str(x) for x in (v if isinstance(v, list) else [])]
                    for k, v in raw["activities"].items()
                }
            if isinstance(raw.get("places"), dict):
                custom["places"] = {
                    str(k): [str(x) for x in (v if isinstance(v, list) else [])]
                    for k, v in raw["places"].items()
                }
        if isinstance(obj.get("selected_phrase"), str):
            selected = obj.get("selected_phrase", "")

    return set(favs), custom, selected


def load_state() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    if not STATE_PATH.exists():
        return
    try:
        raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return

    favs, custom, selected = _repair_loaded(raw)
    st.session_state.favorites = favs
    st.session_state.custom_phrases = custom
    if not st.session_state.selected_phrase and selected:
        st.session_state.selected_phrase = selected


def persist_now() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    payload = {
        "favorites": sorted(list(st.session_state.favorites)),
        "custom_phrases": st.session_state.custom_phrases,
        "selected_phrase": st.session_state.selected_phrase,
    }
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


# -----------------------------
# SELECTION / FAVORITES / CUSTOM MANAGEMENT
# -----------------------------
def push_history(phrase: str) -> None:
    if not phrase:
        return
    hist = st.session_state.history
    if hist and hist[-1] == phrase:
        return
    hist.append(phrase)
    if len(hist) > 50:
        del hist[0]


def set_selected(phrase: str, context_route: Optional[Route] = None) -> None:
    st.session_state.selected_phrase = phrase
    push_history(phrase)

    # Remember exact category route
    if context_route and context_route.name == "category":
        st.session_state.last_category_route = _route_dict(context_route)

    persist_now()


def toggle_favorite(phrase: str) -> None:
    if phrase in st.session_state.favorites:
        st.session_state.favorites.remove(phrase)
    else:
        st.session_state.favorites.add(phrase)
    persist_now()


def add_custom_phrase(scope: Scope, category: str, phrase: str) -> None:
    st.session_state.custom_phrases[scope].setdefault(category, []).append(phrase)
    persist_now()


def edit_custom_phrase(scope: Scope, category: str, index: int, new_text: str) -> None:
    arr = st.session_state.custom_phrases[scope].setdefault(category, [])
    if 0 <= index < len(arr):
        arr[index] = new_text
        persist_now()


def delete_custom_phrase(scope: Scope, category: str, index: int) -> None:
    arr = st.session_state.custom_phrases[scope].setdefault(category, [])
    if 0 <= index < len(arr):
        arr.pop(index)
        persist_now()


# -----------------------------
# STREAMLIT CONFIG + STATE INIT
# -----------------------------
st.set_page_config(page_title="Quick Communication Support", layout="centered")

if "route" not in st.session_state:
    st.session_state.route = _route_dict(Route("home"))

if "nav_stack" not in st.session_state:
    st.session_state.nav_stack = []

if "selected_phrase" not in st.session_state:
    st.session_state.selected_phrase = ""

if "history" not in st.session_state:
    st.session_state.history = []

if "favorites" not in st.session_state:
    st.session_state.favorites = set()

if "custom_phrases" not in st.session_state:
    st.session_state.custom_phrases = {"activities": {}, "places": {}}

if "last_category_route" not in st.session_state:
    st.session_state.last_category_route = None  # dict or None

if "home_search" not in st.session_state:
    st.session_state.home_search = ""

if "_loaded_once" not in st.session_state:
    load_state()
    st.session_state._loaded_once = True


# -----------------------------
# STYLE
# -----------------------------
st.markdown(
    """
<style>
.block-container { padding-top: 2.2rem; padding-bottom: 2.0rem; max-width: 900px; }

.h1 { font-size: 2.15rem; font-weight: 950; margin: 0.2rem 0 0.4rem 0; }
.sub { opacity: 0.78; margin-bottom: 1.0rem; }

.nav-row { margin-top: 0.15rem; margin-bottom: 0.75rem; }
.nav-row div.stButton > button{
  padding: 0.70rem 0.95rem !important;
  border-radius: 14px !important;
  font-weight: 900 !important;
}

.big-phrase {
  margin-top: 18px;
  padding: 64px 38px;
  border-radius: 22px;
  border: 1px solid rgba(255,255,255,0.14);
  background: rgba(255,255,255,0.04);
  min-height: 290px;
  display:flex;
  align-items:center;
  justify-content:center;
  text-align:center;
}
.big-phrase .phrase-text{
  font-size: 3.05rem;
  font-weight: 1000;
  line-height: 1.10;
  opacity: 1;
  color: rgba(255,255,255,0.96);
}

.section-title { font-size: 1.15rem; font-weight: 900; margin: 16px 0 10px 0; }

div.stButton > button {
  border-radius: 14px !important;
  padding: 0.95rem 1rem !important;
}

/* smaller action row buttons */
.small-actions div.stButton > button {
  padding: 0.52rem 0.70rem !important;
  border-radius: 12px !important;
  font-size: 0.95rem !important;
}

/* quick access round buttons */
.quick-btn div.stButton > button{
  height: 84px !important;
  border-radius: 999px !important;
  font-weight: 900 !important;
  font-size: 1.02rem !important;
}

/* small icon-ish buttons in edit rows */
.mini-actions div.stButton > button{
  padding: 0.35rem 0.45rem !important;
  border-radius: 10px !important;
  font-size: 0.9rem !important;
}

/* fullscreen */
.fullscreen-wrap {
  margin-top: 18px;
  padding: 78px 34px;
  border-radius: 26px;
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.02);
  min-height: 72vh;
  display:flex;
  align-items:center;
  justify-content:center;
  text-align:center;
}
.fullscreen-wrap .phrase-text{
  font-size: 3.6rem;
  font-weight: 1000;
  line-height: 1.05;
  color: rgba(255,255,255,0.98);
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# UI COMPONENTS
# -----------------------------
def top_nav(show_back: bool = True, back_default: Route = Route("home")) -> None:
    """HOME first, then Back."""
    st.markdown('<div class="nav-row">', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("🏠 Home", use_container_width=True):
            go(Route("home"))
            st.rerun()
    with c2:
        if show_back:
            if st.button("⬅ Back", use_container_width=True):
                nav_back(default=back_default)
                st.rerun()
        else:
            st.write("")
    st.markdown("</div>", unsafe_allow_html=True)


SearchHit = Union[Tuple[Literal["phrase"], str], Tuple[Literal["open_category"], Scope, str]]


def home_search_box() -> None:
    q = st.text_input(
        "SEARCH 🔎",
        value=st.session_state.home_search,
        placeholder="Type keywords… (e.g., gym, class, lecture, stuck)",
    )
    st.session_state.home_search = q

    if not q.strip():
        return

    hits: List[Tuple[float, SearchHit]] = []

    # Phrase hits
    for p in all_phrases_global():
        s = score_text(q, p)
        if s > 0:
            hits.append((s, ("phrase", p)))

    # Category hits
    for cat in all_categories("places"):
        s = score_text(q, cat)
        if s > 0:
            hits.append((s + 3.0, ("open_category", "places", cat)))
    for cat in all_categories("activities"):
        s = score_text(q, cat)
        if s > 0:
            hits.append((s + 3.0, ("open_category", "activities", cat)))

    hits.sort(key=lambda x: x[0], reverse=True)

    seen_keys: Set[str] = set()
    top: List[SearchHit] = []
    for _, h in hits:
        key = str(h)
        if key not in seen_keys:
            top.append(h)
            seen_keys.add(key)
        if len(top) >= 12:
            break

    st.markdown('<div class="section-title">Results</div>', unsafe_allow_html=True)
    if not top:
        st.info("No matches. Try fewer words.")
        return

    for i, h in enumerate(top):
        if h[0] == "open_category":
            _, scope, cat = h
            label = f"Open: {'Places' if scope=='places' else 'Activities'} • {cat}"
            if st.button(label, key=f"home_open_{i}", use_container_width=True):
                go(Route("category", scope=scope, category=cat))
                st.rerun()
        else:
            _, phrase = h
            cols = st.columns([7, 1])
            with cols[0]:
                if st.button(phrase, key=f"home_pick_{i}", use_container_width=True):
                    set_selected(phrase, context_route=None)
                    go(Route("display"))
                    st.rerun()
            with cols[1]:
                star = "★" if phrase in st.session_state.favorites else "☆"
                if st.button(star, key=f"home_star_{i}", use_container_width=True):
                    toggle_favorite(phrase)
                    st.rerun()


def phrase_list(phrases: List[str], key_prefix: str, context: Optional[Route] = None) -> None:
    for i, p in enumerate(phrases):
        cols = st.columns([7, 1])
        with cols[0]:
            if st.button(p, key=f"{key_prefix}_pick_{i}", use_container_width=True):
                set_selected(p, context_route=context)
                go(Route("display"))
                st.rerun()
        with cols[1]:
            star = "★" if p in st.session_state.favorites else "☆"
            if st.button(star, key=f"{key_prefix}_fav_{i}", use_container_width=True):
                toggle_favorite(p)
                st.rerun()


def phrase_box(phrase: str) -> None:
    safe = (
        phrase.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    st.markdown(
        f"""
<div class="big-phrase">
  <div class="phrase-text">{safe}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def fullscreen_box(phrase: str) -> None:
    safe = (
        phrase.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    st.markdown(
        f"""
<div class="fullscreen-wrap">
  <div class="phrase-text">{safe}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def pinned_favorites_top5() -> List[str]:
    # deterministic order: most recently used first, then alphabetical
    favs = list(st.session_state.favorites)
    if not favs:
        return []
    # prefer favorites that appear in history (recent usage)
    hist_rev = list(reversed(st.session_state.history))
    scored: List[Tuple[int, str]] = []
    for f in favs:
        try:
            idx = hist_rev.index(f)
            score = 1000 - idx  # earlier in hist_rev = more recent
        except ValueError:
            score = 0
        scored.append((score, f))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [f for _, f in scored[:5]]


# -----------------------------
# PAGES
# -----------------------------
def page_home() -> None:
    top_nav(show_back=False)
    home_search_box()

    st.markdown('<div class="h1">Quick Communication Support</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">Discreet help when words get stuck.</div>', unsafe_allow_html=True)

    # PIN section (top 5 favorites)
    pins = pinned_favorites_top5()
    if pins:
        st.markdown('<div class="section-title">Pinned</div>', unsafe_allow_html=True)
        for i, p in enumerate(pins):
            cols = st.columns([7, 1])
            with cols[0]:
                if st.button(p, key=f"pin_pick_{i}", use_container_width=True):
                    set_selected(p, context_route=None)
                    go(Route("display"))
                    st.rerun()
            with cols[1]:
                if st.button("★", key=f"pin_star_{i}", use_container_width=True):
                    toggle_favorite(p)  # unpin
                    st.rerun()

    st.markdown('<div class="section-title">Quick access</div>', unsafe_allow_html=True)
    q1, q2, q3, q4, q5 = st.columns(5)
    with q1:
        st.markdown('<div class="quick-btn">', unsafe_allow_html=True)
        if st.button("Gym", use_container_width=True):
            go(Route("category", scope="places", category="Gym"))
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with q2:
        st.markdown('<div class="quick-btn">', unsafe_allow_html=True)
        if st.button("Class", use_container_width=True):
            go(Route("category", scope="places", category="Class"))
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with q3:
        st.markdown('<div class="quick-btn">', unsafe_allow_html=True)
        if st.button("Lecture", use_container_width=True):
            go(Route("category", scope="activities", category="Lecture"))
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with q4:
        st.markdown('<div class="quick-btn">', unsafe_allow_html=True)
        if st.button("Exam", use_container_width=True):
            go(Route("category", scope="activities", category="Exam"))
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with q5:
        st.markdown('<div class="quick-btn">', unsafe_allow_html=True)
        if st.button("Friends", use_container_width=True):
            go(Route("category", scope="activities", category="Friends"))
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Browse</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🎯 Activities", use_container_width=True):
            go(Route("scope_list", scope="activities"))
            st.rerun()
    with c2:
        if st.button("📍 Places", use_container_width=True):
            go(Route("scope_list", scope="places"))
            st.rerun()

    if st.session_state.selected_phrase:
        st.markdown('<div class="section-title">Last selected</div>', unsafe_allow_html=True)
        st.info(st.session_state.selected_phrase)

    if st.session_state.history:
        st.markdown('<div class="section-title">Recent</div>', unsafe_allow_html=True)
        phrase_list(list(reversed(st.session_state.history[-6:])), "home_recent", context=None)


def page_scope_list(scope: Scope) -> None:
    top_nav(show_back=True, back_default=Route("home"))

    title = "Activities" if scope == "activities" else "Places"
    st.markdown(f'<div class="h1">{title}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">Pick a category.</div>', unsafe_allow_html=True)

    cats = all_categories(scope)
    cols = st.columns(2)
    for idx, name in enumerate(cats):
        with cols[idx % 2]:
            if st.button(name, key=f"{scope}_cat_{idx}", use_container_width=True):
                go(Route("category", scope=scope, category=name))
                st.rerun()

    st.markdown('<div class="section-title">Tip</div>', unsafe_allow_html=True)
    st.caption("Custom phrases and favorites are saved to disk automatically (data/qcs_state.json).")


def page_category(scope: Scope, category: str) -> None:
    top_nav(show_back=True, back_default=Route("scope_list", scope=scope))

    title = ("Activities" if scope == "activities" else "Places") + f" • {category}"
    st.markdown(f'<div class="h1">{title}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Quick button</div>', unsafe_allow_html=True)
    if st.button("🧠 I’m stuck (safe default)", use_container_width=True):
        set_selected(
            "I know what I mean — I just need a second.",
            context_route=Route("category", scope=scope, category=category),
        )
        go(Route("display"))
        st.rerun()

    st.markdown('<div class="section-title">Tap a phrase</div>', unsafe_allow_html=True)
    context = Route("category", scope=scope, category=category)
    phrase_list(phrases_for(scope, category), f"{scope}_{category}", context=context)

    # EDIT / DELETE custom phrases
    custom_list = st.session_state.custom_phrases[scope].get(category, [])
    if custom_list:
        st.markdown('<div class="section-title">Edit / Delete custom phrases</div>', unsafe_allow_html=True)
        for i, txt in enumerate(list(custom_list)):
            row = st.columns([6, 1, 1])
            with row[0]:
                new_val = st.text_input(
                    "Custom phrase",
                    value=txt,
                    key=f"edit_custom_{scope}_{category}_{i}",
                    label_visibility="collapsed",
                )
            with row[1]:
                st.markdown('<div class="mini-actions">', unsafe_allow_html=True)
                if st.button("💾", key=f"save_custom_{scope}_{category}_{i}", use_container_width=True):
                    new_val2 = (new_val or "").strip()
                    if not new_val2:
                        st.warning("Custom phrase can’t be empty.")
                    else:
                        edit_custom_phrase(scope, category, i, new_val2)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            with row[2]:
                st.markdown('<div class="mini-actions">', unsafe_allow_html=True)
                if st.button("🗑", key=f"del_custom_{scope}_{category}_{i}", use_container_width=True):
                    delete_custom_phrase(scope, category, i)
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">Add a custom phrase</div>', unsafe_allow_html=True)
    new_phrase = st.text_input("New phrase", key=f"new_{scope}_{category}", placeholder="Type a custom phrase…")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Save", use_container_width=True):
            txt = (new_phrase or "").strip()
            if not txt:
                st.warning("Type a phrase first.")
            else:
                add_custom_phrase(scope, category, txt)
                st.success("Saved to disk.")
                st.rerun()
    with c2:
        if st.button("Go to Favorites", use_container_width=True):
            go(Route("favorites"))
            st.rerun()


def page_display() -> None:
    top_nav(show_back=True, back_default=Route("home"))

    phrase = st.session_state.selected_phrase
    if not phrase:
        st.info("No phrase selected yet. Go Home and pick one.")
        return

    phrase_box(phrase)

    st.markdown('<div class="small-actions">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    with c1:
        label = "★ Favorited" if phrase in st.session_state.favorites else "☆ Favorite"
        if st.button(label, use_container_width=True):
            toggle_favorite(phrase)
            st.rerun()
    with c2:
        if st.button("📋 Copy", use_container_width=True):
            st.session_state.copy_text = phrase
            st.rerun()
    with c3:
        if st.button("🔄 Another", use_container_width=True):
            pick = random.choice(all_phrases_global())
            set_selected(pick, context_route=None)
            st.rerun()
    with c4:
        if st.button("⛶ Full-screen", use_container_width=True):
            go(Route("fullscreen"))
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # Copy-to-clipboard via a tiny JS snippet (runs in browser)
    # Shows a success message after copying.
    if st.session_state.get("copy_text"):
        to_copy = st.session_state.copy_text
        safe = (
            to_copy.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("$", "\\$")
        )
        st.components.v1.html(
            f"""
<script>
(async function() {{
  try {{
    await navigator.clipboard.writeText(`{safe}`);
    const el = window.parent.document.querySelector('section.main');
    if(el){{}}
  }} catch(e) {{}}
}})();
</script>
""",
            height=0,
        )
        st.success("Copied to clipboard.")
        st.session_state.copy_text = ""


def page_fullscreen() -> None:
    top_nav(show_back=True, back_default=Route("display"))

    phrase = st.session_state.selected_phrase
    if not phrase:
        st.session_state.route = _route_dict(Route("home"))
        st.rerun()

    fullscreen_box(phrase)

    st.markdown('<div class="small-actions">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        label = "★ Favorited" if phrase in st.session_state.favorites else "☆ Favorite"
        if st.button(label, use_container_width=True):
            toggle_favorite(phrase)
            st.rerun()
    with c2:
        if st.button("📋 Copy", use_container_width=True):
            st.session_state.copy_text = phrase
            st.rerun()
    with c3:
        if st.button("🔄 Another", use_container_width=True):
            pick = random.choice(all_phrases_global())
            set_selected(pick, context_route=None)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("copy_text"):
        to_copy = st.session_state.copy_text
        safe = (
            to_copy.replace("\\", "\\\\")
            .replace("`", "\\`")
            .replace("$", "\\$")
        )
        st.components.v1.html(
            f"""
<script>
(async function() {{
  try {{
    await navigator.clipboard.writeText(`{safe}`);
  }} catch(e) {{}}
}})();
</script>
""",
            height=0,
        )
        st.success("Copied to clipboard.")
        st.session_state.copy_text = ""


def page_favorites() -> None:
    top_nav(show_back=True, back_default=Route("home"))

    st.markdown('<div class="h1">Favorites</div>', unsafe_allow_html=True)
    favs = sorted(list(st.session_state.favorites))

    if not favs:
        st.info("No favorites yet. Tap ☆ next to a phrase to save it.")
        return

    phrase_list(favs, "favs", context=None)


# -----------------------------
# ROUTER
# -----------------------------
r = get_route()

if r.name == "home":
    page_home()
elif r.name == "scope_list" and r.scope:
    page_scope_list(r.scope)
elif r.name == "category" and r.scope and r.category:
    page_category(r.scope, r.category)
elif r.name == "display":
    page_display()
elif r.name == "fullscreen":
    page_fullscreen()
elif r.name == "favorites":
    page_favorites()
else:
    st.session_state.route = _route_dict(Route("home"))
    st.rerun()

# -----------------------------
# MOBILE PACKAGING PATH (notes)
# -----------------------------
# Streamlit is web-based. For an Android-style icon + app shell:
# 1) Streamlit -> PWA: host behind a small frontend that provides an installable manifest + service worker.
# 2) Streamlit -> Wrapper: run Streamlit on a server, load it in a WebView (Flutter/React Native).
