"""Content Repurposing Agent Streamlit app.

Setup:
1. Install dependencies: ``pip install -r requirements.txt``
2. Set the Gemini API key as an environment variable, e.g.
   - macOS/Linux: ``export GEMINI_API_KEY="your_key_here"``
   - Windows PowerShell: ``$env:GEMINI_API_KEY="your_key_here"``
3. Launch the app: ``streamlit run app.py``
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Dict, List

import streamlit as st
from dotenv import load_dotenv

# Load .env file from project root
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"
load_dotenv(ENV_FILE, override=True)

from utils import db
from utils.auth import authenticate_user, register_user
from utils.backend_client import BackendClient
from utils.db import fetch_all_posts
from utils.gemini_connector import GeminiConnector
from utils.input_handler import DEFAULT_MAX_WORDS, prepare_text, preview_text
from utils.prompt_builder import PromptBuilder
from utils.schema_loader import get_options_for_field, load_input_schema
from utils.segmentation import split_into_segments, word_count
from utils.templates import PLATFORMS, TONES


st.set_page_config(page_title="Content Repurposing Agent", layout="wide")

st.markdown(
    """
    <style>
        [data-testid="stAppViewContainer"] {
            background-color: #0e1117;
            color: #f8fafc;
        }
        [data-testid="stSidebar"] {
            display: none;
        }
        .title {
            font-size: 2.8rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 0.5rem;
        }
        .subtitle {
            font-size: 1.1rem;
            color: #94a3b8;
            margin-bottom: 2rem;
        }
        .card {
            background: linear-gradient(145deg, #1f2937 0%, #111827 100%);
            border-radius: 18px;
            padding: 1.75rem;
            box-shadow: 0 12px 30px rgba(15, 23, 42, 0.35);
            border: 1px solid rgba(148, 163, 184, 0.12);
        }
        .card h3 {
            margin: 0;
            font-size: 1.15rem;
            color: #38bdf8;
            font-weight: 600;
        }
        .card .stat {
            margin-top: 0.5rem;
            font-size: 2.1rem;
            font-weight: 700;
            color: #f8fafc;
        }
        .workflow-card ul {
            list-style-type: none;
            padding-left: 0;
            margin: 0;
        }
        .workflow-card li {
            font-size: 1rem;
            margin-bottom: 0.6rem;
            color: #e2e8f0;
        }
        .stButton > button {
            background: linear-gradient(120deg, #38bdf8, #6366f1);
            color: #0b1120;
            border: none;
            padding: 0.55rem 1.4rem;
            border-radius: 999px;
            font-weight: 600;
        }
        .stButton > button:hover {
            background: linear-gradient(120deg, #0ea5e9, #4f46e5);
            color: #f8fafc;
        }
        .footer {
            margin-top: 3rem;
            text-align: center;
            font-size: 0.85rem;
            color: #64748b;
        }
        .social-links {
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-top: 1rem;
        }
        .social-link {
            color: #94a3b8;
            font-size: 1.5rem;
            text-decoration: none;
            transition: color 0.3s;
        }
        .social-link:hover {
            color: #38bdf8;
        }
        .top-nav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
            margin-bottom: 2rem;
            border-bottom: 1px solid rgba(148, 163, 184, 0.2);
        }
        .nav-buttons {
            display: flex;
            gap: 0.75rem;
        }
        .nav-btn {
            padding: 0.5rem 1.25rem;
            border-radius: 8px;
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.3);
            color: #38bdf8;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s;
        }
        .nav-btn:hover {
            background: rgba(56, 189, 248, 0.2);
        }
        .about-section {
            background: linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(99, 102, 241, 0.1) 100%);
            border-radius: 18px;
            padding: 2rem;
            margin: 2rem 0;
            border: 1px solid rgba(56, 189, 248, 0.2);
        }
        .user-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 8px;
            color: #10b981;
            font-weight: 500;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def _setup_database() -> bool:
    db.init_db()
    return True


_ = _setup_database()


def _init_session_state() -> None:
    defaults = {
        "raw_text": "",
        "word_count": 0,
        "segments": [],
        "segment_keys": [],
        "platform_outputs": {},
        "tone": list(TONES.keys())[0],
        "platforms": [list(PLATFORMS.keys())[0]],
        "user": None,
        "auth_mode": "Sign in",
        "show_profile": False,
        "backend_client": None,
        "use_backend": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_segment_widgets() -> None:
    for key in st.session_state.get("segment_keys", []):
        st.session_state.pop(key, None)
    st.session_state["segment_keys"] = []


def _update_segments(new_segments: List[str]) -> None:
    _reset_segment_widgets()
    keys: List[str] = []
    for index, segment in enumerate(new_segments):
        widget_key = f"segment_{index}"
        st.session_state[widget_key] = segment
        keys.append(widget_key)
    st.session_state["segment_keys"] = keys
    st.session_state["segments"] = new_segments


def _render_segments_editor() -> None:
    st.header("2. Review & Edit Segments")
    segment_keys: List[str] = st.session_state.get("segment_keys", [])
    segments: List[str] = st.session_state.get("segments", [])
    if not segments:
        st.info("Segment the content first to edit individual chunks.")
        return

    for index, widget_key in enumerate(segment_keys):
        with st.expander(f"Segment {index + 1} (≈ {word_count(st.session_state[widget_key])} words)", expanded=False):
            updated_text = st.text_area(
                "Edit segment",
                value=st.session_state[widget_key],
                key=widget_key,
                height=200,
            )
            st.session_state["segments"][index] = updated_text


def _render_generation_controls() -> None:
    st.header("3. Select Tone & Platforms")
    input_schema = load_input_schema()
    tone_options = get_options_for_field(input_schema, "tone") or list(TONES.keys())
    platform_options = get_options_for_field(input_schema, "platforms") or list(PLATFORMS.keys())

    st.session_state["tone"] = st.radio(
        "Choose a tone",
        options=tone_options,
        index=tone_options.index(st.session_state.get("tone", tone_options[0])),
    )

    st.session_state["platforms"] = st.multiselect(
        "Choose platforms",
        options=platform_options,
        default=st.session_state.get("platforms", [platform_options[0]]),
    )


def _get_backend_client() -> BackendClient:
    """Get or create backend client instance."""
    if st.session_state.get("backend_client") is None:
        st.session_state["backend_client"] = BackendClient()
    return st.session_state["backend_client"]


def _generate_posts() -> Dict[str, str]:
    segments: List[str] = [segment.strip() for segment in st.session_state.get("segments", []) if segment.strip()]
    tone = st.session_state.get("tone", list(TONES.keys())[0])
    platforms = st.session_state.get("platforms", [])

    if not segments:
        st.warning("Please segment the content and ensure each segment contains text before generating posts.")
        return {}

    if not platforms:
        st.warning("Select at least one platform before generating posts.")
        return {}

    use_backend = st.session_state.get("use_backend", True)
    user = st.session_state.get("user")
    user_id = user["id"] if user else None

    if use_backend:
        try:
            client = _get_backend_client()
            if not client.health_check():
                st.warning("Backend not available. Falling back to direct mode.")
                use_backend = False
        except Exception:
            st.warning("Backend check failed. Falling back to direct mode.")
            use_backend = False

    if use_backend:
        try:
            progress = st.progress(0, text="Generating via backend...")
            result = client.generate_content(
                segments=segments,
                tone=tone,
                platforms=platforms,
                user_id=user_id,
            )
            progress.progress(100)
            progress.empty()
            return result.get("outputs", {})
        except Exception as exc:
            st.error(f"Backend generation failed: {exc}")
            st.info("Falling back to direct mode...")
            use_backend = False

    # Fallback to direct Gemini calls
    prompt_builder = PromptBuilder(tone, platforms)
    prompts_by_platform = prompt_builder.build_prompts(segments)

    try:
        connector = GeminiConnector()
    except EnvironmentError as error:
        st.error(str(error))
        return {}

    total_prompts = sum(len(prompts) for prompts in prompts_by_platform.values())
    if total_prompts == 0:
        st.warning("Nothing to generate. Check that your segments contain text.")
        return {}

    progress = st.progress(0, text="Generating content...")
    completed = 0
    combined_outputs: Dict[str, str] = {}

    for platform_id, prompts in prompts_by_platform.items():
        responses: List[str] = []
        for prompt in prompts:
            responses.append(connector.generate_text(prompt))
            completed += 1
            progress.progress(min(int((completed / total_prompts) * 100), 100))

        combined_outputs[platform_id] = GeminiConnector.combine_segment_outputs(responses)

    progress.empty()
    return combined_outputs


def _render_generated_outputs() -> None:
    if not st.session_state.get("platform_outputs"):
        return

    st.header("4. Review & Edit Generated Posts")
    for label, platform_id in PLATFORMS.items():
        if platform_id not in st.session_state["platform_outputs"]:
            continue
        st.session_state["platform_outputs"][platform_id] = st.text_area(
            f"{label} Output",
            value=st.session_state["platform_outputs"][platform_id],
            key=f"output_{platform_id}",
            height=220,
        )


def _render_save_section() -> None:
    if not st.session_state.get("platform_outputs"):
        return

    st.header("5. Save Results")
    title = st.text_input("Project title", value=st.session_state.get("project_title", ""))
    st.session_state["project_title"] = title

    if st.button("Save to Library"):
        if not title.strip():
            st.warning("Add a project title before saving.")
            return
        user = st.session_state.get("user")
        user_id = user["id"] if user else None

        use_backend = st.session_state.get("use_backend", True)
        if use_backend:
            try:
                client = _get_backend_client()
                if client.health_check():
                    client.generate_content(
                        segments=st.session_state.get("segments", []),
                        tone=st.session_state["tone"],
                        platforms=st.session_state["platforms"],
                        project_title=title.strip(),
                        save=True,
                        user_id=user_id,
                    )
                    st.success("Saved via backend to local database.")
                    return
            except Exception:
                pass

        # Fallback to direct save
        db.save_to_db(
            title.strip(),
            st.session_state["tone"],
            st.session_state["platform_outputs"],
            user_id=user_id,
        )
        st.success("Saved to local database.")

    with st.expander("View saved posts"):
        user = st.session_state.get("user")
        saved_posts = db.view_saved_posts(user_id=user["id"] if user else None)
        if not saved_posts:
            st.write("No saved posts yet.")
        else:
            for row in saved_posts:
                st.markdown(
                    f"**#{row['id']}** — *{row['title']}* | {row['tone']} | {row['platform'].title()} | {row['timestamp']}"
                )

def _render_profile_section() -> None:
    if not st.session_state.get("show_profile"):
        return

    user = st.session_state.get("user")
    if not user:
        st.session_state["show_profile"] = False
        return

    st.markdown(
        f"""
        <div class='card' style='margin-bottom:1rem;'>
            <h3>Profile</h3>
            <p style='margin-top:0.75rem; font-size:1rem; color:#e2e8f0;'>
                <strong>Name:</strong> {user['name']}<br>
                <strong>Email:</strong> {user['email']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    saved_posts = db.view_saved_posts(user_id=user["id"], include_content=False)
    if saved_posts:
        st.subheader("Recent Projects")
        for row in saved_posts:
            st.markdown(
                f"- `{row['timestamp']}` — **{row['title']}** ({row['platform'].title()}, {row['tone']})"
            )
    else:
        st.info("No saved posts yet. Generate and save content to see it here.")

    if st.button("Hide Profile", key="hide_profile"):
        st.session_state["show_profile"] = False


def _render_top_nav() -> None:
    """Render top navigation bar with auth buttons."""
    user = st.session_state.get("user")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("<div></div>", unsafe_allow_html=True)  # Spacer
    with col2:
        if user:
            st.markdown(
                f"""
                <div class="user-badge">
                    {user['name']}
                </div>
                """,
                unsafe_allow_html=True,
            )
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Profile", key="nav_profile", use_container_width=True):
                    st.session_state["show_profile"] = True
                    st.rerun()
            with col_b:
                if st.button("Logout", key="nav_logout", use_container_width=True):
                    st.session_state["user"] = None
                    st.session_state["show_profile"] = False
                    st.session_state["platform_outputs"] = {}
                    st.session_state["segments"] = []
                    st.rerun()
        else:
            col_signin, col_signup = st.columns(2)
            with col_signin:
                if st.button("🔐 Sign In", key="nav_signin", use_container_width=True):
                    st.session_state["show_auth_modal"] = "signin"
            with col_signup:
                if st.button("✨ Sign Up", key="nav_signup", use_container_width=True):
                    st.session_state["show_auth_modal"] = "signup"


def _render_auth_modal() -> None:
    """Render authentication modal/popup."""
    if not st.session_state.get("show_auth_modal"):
        return
    
    user = st.session_state.get("user")
    if user:
        st.session_state["show_auth_modal"] = None
        return
    
    mode = st.session_state.get("show_auth_modal", "signin")
    
    with st.expander("🔐 Account Access", expanded=True):
        if mode == "signin":
            email = st.text_input("Email", key="modal_login_email")
            password = st.text_input("Password", type="password", key="modal_login_password")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Sign In", key="modal_login_submit", use_container_width=True):
                    if not email or not password:
                        st.warning("Enter your email and password.")
                    else:
                        user = authenticate_user(email=email, password=password)
                        if not user:
                            st.error("Invalid credentials. Try again or sign up.")
                        else:
                            st.session_state["user"] = user
                            st.session_state["show_profile"] = False
                            st.session_state["show_auth_modal"] = None
                            st.success("Signed in successfully.")
                            st.rerun()
            with col2:
                if st.button("Switch to Sign Up", key="switch_signup", use_container_width=True):
                    st.session_state["show_auth_modal"] = "signup"
                    st.rerun()
        else:
            name = st.text_input("Name", key="modal_signup_name")
            email = st.text_input("Email", key="modal_signup_email")
            password = st.text_input("Password", type="password", key="modal_signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="modal_signup_confirm")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Create Account", key="modal_signup_submit", use_container_width=True):
                    if not all([name.strip(), email.strip(), password, confirm]):
                        st.warning("Fill in all fields to sign up.")
                    elif password != confirm:
                        st.warning("Passwords do not match.")
                    else:
                        try:
                            user = register_user(name=name.strip(), email=email.strip(), password=password)
                        except ValueError as exc:
                            st.error(str(exc))
                        else:
                            st.session_state["user"] = user
                            st.session_state["show_profile"] = False
                            st.session_state["show_auth_modal"] = None
                            st.success("Account created and signed in.")
                            st.rerun()
            with col2:
                if st.button("Switch to Sign In", key="switch_signin", use_container_width=True):
                    st.session_state["show_auth_modal"] = "signin"
                    st.rerun()


def main() -> None:
    _init_session_state()
    
    # Initialize auth modal state
    if "show_auth_modal" not in st.session_state:
        st.session_state["show_auth_modal"] = None

    # Top Navigation
    _render_top_nav()
    
    # Header
    st.markdown("<h1 class='title'>Content Repurposing Agent</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtitle'>Transform long-form content into platform-ready posts using Google Gemini.</p>",
        unsafe_allow_html=True,
    )

    # Auth Modal
    _render_auth_modal()

    # Public Stats (visible to everyone)
    all_posts = fetch_all_posts(include_content=False)
    total_projects = len(all_posts)
    user = st.session_state.get("user")
    user_posts = db.view_saved_posts(user_id=user.get("id") if user else None, include_content=False) if user else []
    user_projects = len(user_posts) if user else 0

    st.markdown("---")

    # About Section
    st.markdown("### About This Project")
    st.markdown(
        """
        <div class='about-section'>
            <p style='font-size:1.05rem; line-height:1.8; color:#e2e8f0; margin-bottom:1rem;'>
                <strong>Content Repurposing Agent</strong> is a powerful tool designed to help content creators, 
                marketers, and businesses transform long-form articles, blog posts, and documents into optimized 
                social media content. Whether you need LinkedIn posts, Instagram captions, or YouTube Shorts scripts, 
                our platform uses Google Gemini AI to generate platform-specific content tailored to your brand's tone.
            </p>
            <p style='font-size:1rem; line-height:1.8; color:#cbd5f5;'>
                <strong>Key Features:</strong> Upload PDFs or DOCX files, paste text up to 20,000 words, 
                intelligently segment content, choose from professional/casual/promotional tones, and generate 
                ready-to-post content for multiple platforms. All your projects are saved securely and can be 
                accessed anytime.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Public Statistics
    st.markdown("### Platform Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class='card'>
                <h3>Total Projects</h3>
                <p class='stat'>{total_projects}</p>
                <p style='color:#94a3b8; margin-top:0.75rem; font-size:0.9rem;'>
                    Projects in database
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        active_users = 0
        if all_posts:
            user_ids = set()
            for row in all_posts:
                try:
                    user_id = row['user_id']
                    if user_id is not None:
                        user_ids.add(user_id)
                except (KeyError, IndexError):
                    continue
            active_users = len(user_ids)
        st.markdown(
            f"""
            <div class='card'>
                <h3>Active Users</h3>
                <p class='stat'>{active_users}</p>
                <p style='color:#94a3b8; margin-top:0.75rem; font-size:0.9rem;'>
                    Registered users
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class='card'>
                <h3>Platforms</h3>
                <p class='stat'>{len(PLATFORMS)}</p>
                <p style='color:#94a3b8; margin-top:0.75rem; font-size:0.9rem;'>
                    Supported channels
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
            <div class='card'>
                <h3>Tone Presets</h3>
                <p class='stat'>{len(TONES)}</p>
                <p style='color:#94a3b8; margin-top:0.75rem; font-size:0.9rem;'>
                    Content styles
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # User-specific stats (if logged in)
    if user:
        st.markdown("### Your Statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f"""
                <div class='card'>
                    <h3>Your Projects</h3>
                    <p class='stat'>{user_projects}</p>
                    <p style='color:#94a3b8; margin-top:0.75rem; font-size:0.9rem;'>
                        Projects you've saved
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""
                <div class='card'>
                    <h3>Storage</h3>
                    <p class='stat'>{user_projects}</p>
                    <p style='color:#94a3b8; margin-top:0.75rem; font-size:0.9rem;'>
                        Saved items
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if not user:
        # Social media links (can be configured via environment variables or backend)
        linkedin_url = st.session_state.get("linkedin_url", "#")
        facebook_url = st.session_state.get("facebook_url", "#")
        instagram_url = st.session_state.get("instagram_url", "#")
        
        st.markdown(
            f"""
            <div class='footer'>
                <p>© 2025 Content Repurposing Agent | Made with ❤️ by students</p>
                <div class='social-links'>
                    <a href='{linkedin_url}' target='_blank' class='social-link' title='LinkedIn'>🔗</a>
                    <a href='{facebook_url}' target='_blank' class='social-link' title='Facebook'>📘</a>
                    <a href='{instagram_url}' target='_blank' class='social-link' title='Instagram'>📷</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    _render_profile_section()

    st.header("1. Load Content")
    pasted_text = st.text_area(
        "Paste article, blog post, or transcript (optional)",
        value="",
        height=200,
    )
    uploaded_file = st.file_uploader(
        "Upload a PDF or DOCX (optional)",
        type=["pdf", "docx"],
    )

    if st.button("Segment Content"):
        try:
            prepared_text, total_words = prepare_text(pasted_text, uploaded_file, DEFAULT_MAX_WORDS)
        except ValueError as error:
            st.error(str(error))
            prepared_text, total_words = "", 0

        if not prepared_text:
            st.warning("Provide text via upload or paste to proceed.")
        else:
            st.session_state["raw_text"] = prepared_text
            st.session_state["word_count"] = total_words
            segments = split_into_segments(prepared_text)
            if not segments:
                segments = [prepared_text]
            _update_segments(segments)

            st.success(f"Loaded {total_words} words and created {len(segments)} segments.")
            st.info(preview_text(prepared_text))
            st.session_state["platform_outputs"] = {}

    st.divider()
    _render_segments_editor()

    st.divider()
    _render_generation_controls()

    if st.button("Generate Posts"):
        combined_outputs = _generate_posts()
        if combined_outputs:
            st.session_state["platform_outputs"] = combined_outputs

    st.divider()
    _render_generated_outputs()

    st.divider()
    _render_save_section()

    # Social media links (can be configured via environment variables or backend)
    linkedin_url = st.session_state.get("linkedin_url", "#")
    facebook_url = st.session_state.get("facebook_url", "#")
    instagram_url = st.session_state.get("instagram_url", "#")
    
    st.markdown(
        f"""
        <div class='footer'>
            <p>© 2025 Content Repurposing Agent | Made with ❤️ by students</p>
            <div class='social-links'>
                <a href='{linkedin_url}' target='_blank' class='social-link' title='LinkedIn'>🔗</a>
                <a href='{facebook_url}' target='_blank' class='social-link' title='Facebook'>📘</a>
                <a href='{instagram_url}' target='_blank' class='social-link' title='Instagram'>📷</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()


# Run Instructions
# 
# Setup:
# 1. Install dependencies: pip install -r requirements.txt
# 2. Set GEMINI_API_KEY in .env file (or export as environment variable)
#
# Running with Backend (Recommended):
# Terminal 1 (Backend):
#   python -m uvicorn main:app --reload
#   Backend runs at: http://127.0.0.1:8000
#
# Terminal 2 (Frontend):
#   streamlit run app.py
#   Frontend runs at: http://localhost:8501
#
# The app will automatically use the backend if available, or fall back to direct Gemini calls.

