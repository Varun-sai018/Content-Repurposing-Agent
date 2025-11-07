"""Content Repurposing Agent Streamlit app.

Setup:
1. Install dependencies: ``pip install -r requirements.txt``
2. Set the Gemini API key as an environment variable, e.g.
   - macOS/Linux: ``export GEMINI_API_KEY="your_key_here"``
   - Windows PowerShell: ``$env:GEMINI_API_KEY="your_key_here"``
3. Launch the app: ``streamlit run app.py``
"""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from utils import db
from utils.auth import authenticate_user, register_user
from utils.gemini_connector import GeminiConnector
from utils.input_handler import DEFAULT_MAX_WORDS, prepare_text, preview_text
from utils.prompt_builder import PromptBuilder
from utils.segmentation import split_into_segments, word_count
from utils.templates import PLATFORMS, TONES


st.set_page_config(page_title="Content Repurposing Agent", layout="wide")


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
    st.session_state["tone"] = st.radio(
        "Choose a tone",
        options=list(TONES.keys()),
        index=list(TONES.keys()).index(st.session_state.get("tone", list(TONES.keys())[0])),
    )

    st.session_state["platforms"] = st.multiselect(
        "Choose platforms",
        options=list(PLATFORMS.keys()),
        default=st.session_state.get("platforms", [list(PLATFORMS.keys())[0]]),
    )


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

    st.header("Profile")
    st.markdown(f"**Name:** {user['name']}")
    st.markdown(f"**Email:** {user['email']}")

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


def _render_auth_sidebar() -> None:
    with st.sidebar:
        st.header("Account")
        user = st.session_state.get("user")

        if user:
            st.success(f"Signed in as {user['name']}")
            if st.button("View Profile", key="profile_button"):
                st.session_state["show_profile"] = True
            if st.button("Log out", key="logout_button"):
                st.session_state["user"] = None
                st.session_state["show_profile"] = False
                st.session_state["platform_outputs"] = {}
                st.session_state["segments"] = []
                st.rerun()
            return

        mode = st.radio("", options=["Sign in", "Sign up"], index=0, key="auth_mode_radio")
        st.session_state["auth_mode"] = mode

        if mode == "Sign in":
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Sign in", key="login_submit"):
                if not email or not password:
                    st.warning("Enter your email and password.")
                else:
                    user = authenticate_user(email=email, password=password)
                    if not user:
                        st.error("Invalid credentials. Try again or sign up.")
                    else:
                        st.session_state["user"] = user
                        st.session_state["show_profile"] = False
                        st.success("Signed in successfully.")
                        st.rerun()
        else:
            name = st.text_input("Name", key="signup_name")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")
            if st.button("Create account", key="signup_submit"):
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
                        st.success("Account created and signed in.")
                        st.rerun()


def main() -> None:
    _init_session_state()

    st.title("Content Repurposing Agent")
    st.caption(
        "Transform long-form articles into ready-to-post social content using Google Gemini."
    )

    with st.container():
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("From long-form to launch-ready in minutes")
            st.markdown(
                """
                Upload or paste your long-form content, pick the tone that matches your brand, and instantly produce
                polished posts for LinkedIn, Instagram, and YouTube. Edit segments, preview results, and keep your
                winning copy organized in a personal library.
                """
            )
            st.markdown(
                """
                **Workflow overview**
                - Ingest articles, PDFs, or docs up to 20k words
                - Segment and refine draft snippets
                - Choose tone + platforms and generate with Gemini
                - Edit, save, and revisit projects anytime
                """
            )
        with c2:
            st.metric("Projects saved", len(db.view_saved_posts(limit=100)))
            st.metric("Supported platforms", len(PLATFORMS))
            st.metric("Tone presets", len(TONES))

    st.markdown("---")

    _render_auth_sidebar()

    if not st.session_state.get("user"):
        st.info(
            "👋 Welcome! Sign in or create a free account from the left sidebar to unlock segmentation, generation, and saving."
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


if __name__ == "__main__":
    main()


# Run Instructions
# pip install -r requirements.txt
# export GEMINI_API_KEY="your_key_here"
# streamlit run app.py

