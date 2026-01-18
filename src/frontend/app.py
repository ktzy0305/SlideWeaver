"""Streamlit frontend for SlideWeaver."""

import json
import time

import requests
import streamlit as st

from core.config import get_api_base_url

# Configuration
API_BASE_URL = get_api_base_url()

# Page configuration
st.set_page_config(
    page_title="SlideWeaver",
    page_icon="🧵",
    layout="wide",
)


# ============================================================================
# Session Management
# ============================================================================


def init_session():
    """Initialize a new API session."""
    try:
        response = requests.post(f"{API_BASE_URL}/sessions", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None


def get_or_create_session():
    """Get existing session or create new one."""
    if "api_session" not in st.session_state:
        session_data = init_session()
        if session_data:
            st.session_state.api_session = session_data
            st.session_state.uploaded_images = []
            st.session_state.chat_history = []
            st.session_state.generation_status = None
            st.session_state.download_info = None
        else:
            st.error("Failed to connect to API server. Is it running?")
            st.stop()
    return st.session_state.api_session


# ============================================================================
# API Functions
# ============================================================================


def upload_image(session_id: str, file, title: str, description: str = ""):
    """Upload an image to the session."""
    try:
        files = {"file": (file.name, file.getvalue(), file.type)}
        data = {"title": title, "description": description, "tags": ""}

        response = requests.post(
            f"{API_BASE_URL}/sessions/{session_id}/images",
            files=files,
            data=data,
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Upload failed: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Upload error: {e}")
        return None


def get_uploaded_images(session_id: str):
    """Get list of uploaded images."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/sessions/{session_id}/images",
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
        return []
    except requests.exceptions.RequestException:
        return []


def delete_image(session_id: str, artifact_id: str):
    """Delete an uploaded image."""
    try:
        response = requests.delete(
            f"{API_BASE_URL}/sessions/{session_id}/images/{artifact_id}",
            timeout=10,
        )
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def generate_presentation_stream(
    session_id: str, user_request: str, audience: str, tone: str, api_key: str
):
    """Generate presentation with streaming progress."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/sessions/{session_id}/generate_stream",
            json={
                "user_request": user_request,
                "audience": audience,
                "tone": tone,
                "api_key": api_key,
            },
            stream=True,
            timeout=300,
        )

        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data == "[DONE]":
                            break
                        try:
                            yield json.loads(data)
                        except json.JSONDecodeError:
                            continue
        else:
            yield {"event": "error", "error": f"API error: {response.status_code}"}
    except requests.exceptions.RequestException as e:
        yield {"event": "error", "error": str(e)}


# ============================================================================
# UI Components
# ============================================================================


def render_sidebar():
    """Render the sidebar with image upload and settings."""
    with st.sidebar:
        st.header("🧵 SlideWeaver")
        st.caption("AI-Powered Presentations")

        # API Key
        st.subheader("API Configuration")
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            value=st.session_state.get("api_key", ""),
            help="Your OpenAI API key for generating presentations",
            placeholder="sk-...",
        )
        if api_key:
            st.session_state.api_key = api_key

        st.divider()

        # Settings
        st.subheader("Presentation Settings")
        audience = st.text_input(
            "Target Audience",
            value="General business audience",
            help="Who will view this presentation?",
        )

        tone = st.selectbox(
            "Tone",
            options=["executive", "technical", "teaching"],
            format_func=lambda x: x.title(),
            help="The style and tone of the presentation",
        )

        st.divider()

        # Image Upload Section
        st.subheader("Upload Figures")
        st.caption("Upload images to include in your presentation")

        uploaded_file = st.file_uploader(
            "Choose an image",
            type=["png", "jpg", "jpeg", "gif", "svg", "webp"],
            help="Drag and drop or click to upload",
        )

        if uploaded_file:
            # Preview
            st.image(uploaded_file, caption="Preview", use_container_width=True)

            # Title input
            image_title = st.text_input(
                "Image Title",
                value=uploaded_file.name.rsplit(".", 1)[0],
            )

            # Upload button
            if st.button("Add to Presentation", type="primary"):
                session = get_or_create_session()
                result = upload_image(
                    session["session_id"],
                    uploaded_file,
                    image_title,
                )
                if result:
                    st.success(f"Uploaded: {result['title']}")
                    # Refresh images list
                    st.session_state.uploaded_images = get_uploaded_images(
                        session["session_id"]
                    )
                    st.rerun()

        # Show uploaded images
        st.divider()
        st.subheader("Uploaded Images")

        session = get_or_create_session()
        images = get_uploaded_images(session["session_id"])
        st.session_state.uploaded_images = images

        if images:
            for img in images:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(img["title"][:20] + "..." if len(img["title"]) > 20 else img["title"])
                with col2:
                    if st.button("🗑️", key=f"del_{img['artifact_id']}", help="Remove"):
                        if delete_image(session["session_id"], img["artifact_id"]):
                            st.rerun()
        else:
            st.caption("No images uploaded yet. Text-based slides will be generated.")

        return audience, tone, api_key


def render_chat_area(audience: str, tone: str, api_key: str):
    """Render the main chat area."""
    st.header("🧵 SlideWeaver")
    st.caption("Weave your ideas into beautiful presentations")

    # Chat history display
    chat_container = st.container()

    with chat_container:
        # Display chat history
        for msg in st.session_state.get("chat_history", []):
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(msg["content"])

    # Download button if available
    if st.session_state.get("download_info"):
        info = st.session_state.download_info
        session = get_or_create_session()
        download_url = f"{API_BASE_URL}/sessions/{session['session_id']}/download/{info['path']}"

        st.success(f"✨ Woven: {info['title']} ({info['slides']} slides)")

        # Download button
        try:
            response = requests.get(download_url, timeout=30)
            if response.status_code == 200:
                st.download_button(
                    label="⬇️ Download Presentation",
                    data=response.content,
                    file_name=info["filename"],
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    type="primary",
                )
        except requests.exceptions.RequestException:
            st.error("Could not fetch download file")

    # Chat input
    user_input = st.chat_input("Describe what you'd like to weave into a presentation...")

    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Display user message
        with st.chat_message("user"):
            st.write(user_input)

        # Check for API key
        if not api_key:
            st.error("Please enter your OpenAI API key in the sidebar settings.")
            return

        # Generate presentation
        with st.chat_message("assistant"):
            generate_with_progress(user_input, audience, tone, api_key)


def generate_with_progress(user_request: str, audience: str, tone: str, api_key: str):
    """Generate presentation with progress display."""
    session = get_or_create_session()

    # Progress display
    status_text = st.empty()
    progress_bar = st.progress(0)

    status_messages = []

    for event in generate_presentation_stream(
        session["session_id"],
        user_request,
        audience,
        tone,
        api_key,
    ):
        event_type = event.get("event", "")

        if event_type == "brief_created":
            status_text.text("🧵 Gathering threads...")
            progress_bar.progress(5)

        elif event_type == "catalog_loaded":
            count = event.get("artifact_count", 0)
            status_text.text(f"🎨 Found {count} visual elements")
            progress_bar.progress(10)

        elif event_type == "planning_started":
            status_text.text("📐 Planning the pattern...")
            progress_bar.progress(15)

        elif event_type == "planning_complete":
            slide_count = event.get("slide_count", 0)
            title = event.get("title", "")
            status_text.text(f"📋 Pattern ready: {slide_count} slides")
            progress_bar.progress(25)
            status_messages.append(f"Presentation: **{title}** ({slide_count} slides)")

        elif event_type == "slide_designing":
            index = event.get("index", 0)
            total = event.get("total", 1)
            title = event.get("title", "")
            progress = 25 + int((index / total) * 60)
            status_text.text(f"🪡 Weaving slide {index}/{total}: {title}")
            progress_bar.progress(progress)

        elif event_type == "slide_complete":
            index = event.get("index", 0)
            # Keep progress updated

        elif event_type == "slide_error":
            error = event.get("error", "")
            status_messages.append(f"Warning: {error}")

        elif event_type == "build_started":
            status_text.text("📦 Finishing touches...")
            progress_bar.progress(90)

        elif event_type == "generation_complete":
            progress_bar.progress(100)
            status_text.text("✨ Masterpiece complete!")

            # Store download info
            st.session_state.download_info = {
                "path": event.get("download_path", ""),
                "filename": event.get("pptx_filename", "presentation.pptx"),
                "title": event.get("title", "Presentation"),
                "slides": event.get("slide_count", 0),
            }

            # Add completion message to chat
            completion_msg = f"✨ Woven **{event.get('title')}** with {event.get('slide_count')} slides."
            if event.get("warnings"):
                completion_msg += f"\n\n⚠️ {len(event.get('warnings'))} minor adjustments were made"

            st.session_state.chat_history.append(
                {"role": "assistant", "content": completion_msg}
            )

            time.sleep(0.5)
            st.rerun()

        elif event_type == "generation_error":
            error = event.get("error", "Unknown error")
            status_text.text(f"Error: {error}")
            progress_bar.progress(0)

            st.session_state.chat_history.append(
                {"role": "assistant", "content": f"Generation failed: {error}"}
            )
            st.error(error)
            break

        elif event_type == "error":
            error = event.get("error", "Unknown error")
            st.error(f"Error: {error}")
            break


# ============================================================================
# Main App
# ============================================================================


def main():
    """Main application."""
    # Initialize session
    get_or_create_session()

    # Render UI
    audience, tone, api_key = render_sidebar()
    render_chat_area(audience, tone, api_key)


if __name__ == "__main__":
    main()
