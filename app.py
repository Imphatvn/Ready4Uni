"""
Ready4Uni - AI University Readiness Chatbot
Streamlit Web Application

Entry point for the chatbot interface. Provides an intuitive UI for students
to explore university majors, analyze transcripts, and get personalized guidance.
"""

import streamlit as st
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import services
try:
    from services.chat_service import ChatService, ChatResponse
    from clients.pdf_client import validate_pdf_file, extract_text_from_pdf
    from config import GEMINI_MODEL
except ImportError as e:
    st.error(f"❌ Failed to import required modules: {e}")
    st.stop()

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Ready4Uni - University Readiness Assistant",
    page_icon="assets/logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CUSTOM CSS STYLING - Modern Clean Design
# ============================================================================

st.markdown("""
<style>
    /* ===== Import Google Fonts - Outfit (similar to Lufga) ===== */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* ===== Global Styles ===== */
    html, body, [class*="css"] {
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main container - clean white background */
    .main {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 100%);
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* ===== Typography - Lufga-style ===== */
    h1 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: #030318;
        letter-spacing: -0.02em;
    }
    
    h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        color: #030318;
    }
    
    p, li, span {
        font-family: 'Outfit', sans-serif;
        color: #030318;
    }
    
    /* ===== Chat Messages - Lufga Gradient Style ===== */
    [data-testid="stChatMessage"] {
        background: linear-gradient(135deg, #A3E28B22 0%, #F4C0F222 50%, #FFFFFF 100%);
        border-radius: 20px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 10px 30px rgba(3, 3, 24, 0.05);
        border: 1px solid rgba(163, 226, 139, 0.2);
    }
    
    [data-testid="stChatMessage"]:nth-child(even) {
        background: linear-gradient(135deg, #F4C0F211 0%, #A3E28B11 100%);
    }
    
    /* ===== Sidebar Styling ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8F9FA 100%);
        border-right: 1px solid #03031811;
    }
    
    /* ===== Buttons - Dark Navy & Rounded ===== */
    .stButton > button {
        background-color: #030318;
        color: #FFFFFF;
        border: none;
        border-radius: 12px;
        padding: 14px 32px;
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 8px 20px rgba(3, 3, 24, 0.2);
    }
    
    .stButton > button:hover {
        background-color: #1a1a3a;
        transform: translateY(-3px);
        box-shadow: 0 12px 25px rgba(3, 3, 24, 0.3);
    }
    
    /* Secondary button style */
    .stButton > button[kind="secondary"] {
        background-color: transparent;
        color: #030318;
        border: 2px solid #030318;
    }
    
    /* ===== File Uploader ===== */
    [data-testid="stFileUploader"] {
        background: linear-gradient(135deg, #A3E28B11 0%, #F4C0F211 100%);
        border-radius: 20px;
        padding: 30px;
        border: 2px dashed #03031822;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: #030318;
    }
    
    /* ===== Input Fields ===== */
    .stTextInput > div > div > input,
    .stTextArea textarea {
        border-radius: 14px;
        border: 2px solid #E9ECEF;
        font-family: 'Outfit', sans-serif;
        color: #030318;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: #030318;
        box-shadow: 0 0 0 4px rgba(3, 3, 24, 0.05);
    }
    
    /* ===== Chat Input - Fix double border ===== */
    [data-testid="stChatInput"] {
        border-radius: 20px !important;
        border: 2px solid #E9ECEF !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 10px 40px rgba(3, 3, 24, 0.08) !important;
        padding: 5px !important;
    }
    
    [data-testid="stChatInput"] textarea {
        border: none !important;
        box-shadow: none !important;
        background-color: transparent !important;
        font-family: 'Outfit', sans-serif !important;
        color: #030318 !important;
    }
    
    [data-testid="stChatInput"]:focus-within {
        border-color: #030318 !important;
    }
    
    /* ===== Cards/Containers ===== */
    [data-testid="stExpander"] {
        background: #FFFFFF;
        border-radius: 20px;
        border: 1px solid #F0F2F6;
        box-shadow: 0 10px 30px rgba(3, 3, 24, 0.05);
    }
    
    /* ===== Metrics - Lufga Gradient ===== */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #A3E28B22 0%, #F4C0F222 100%);
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(3, 3, 24, 0.05);
        border: 1px solid rgba(3, 3, 24, 0.03);
    }
    
    /* ===== Hide Streamlit Branding ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ===== Smooth Animations ===== */
    * {
        transition: all 0.3s ease-in-out;
    }
</style>
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    
    if "chat_service" not in st.session_state:
        st.session_state.chat_service = ChatService()
        logger.info("✅ ChatService initialized")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = f"session_{int(time.time())}"
    
    if "uploaded_transcript_path" not in st.session_state:
        st.session_state.uploaded_transcript_path = None
    
    if "student_grades" not in st.session_state:
        st.session_state.student_grades = None
    
    if "conversation_count" not in st.session_state:
        st.session_state.conversation_count = 0


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_message_history() -> List[Dict[str, str]]:
    """Format session messages for agent context."""
    return [
        {"role": msg["role"], "content": msg["content"]}
        for msg in st.session_state.messages
    ]


def add_message(role: str, content: str, metadata: Optional[Dict] = None):
    """Add a message to the conversation history."""
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "timestamp": time.time(),
    })
    st.session_state.conversation_count += 1


def render_chat_message(message: Dict[str, Any]):
    """Render a single chat message with proper styling."""
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(content)
    else:  # assistant
        with st.chat_message("assistant", avatar="🎓"):
            st.markdown(content)
            
            # Show metadata if available
            metadata = message.get("metadata", {})
            if metadata.get("intent"):
                with st.expander("ℹ️ Message Details", expanded=False):
                    st.caption(f"**Intent:** {metadata['intent']}")
                    if metadata.get("tools_used"):
                        st.caption(f"**Tools Used:** {', '.join(metadata['tools_used'])}")


def handle_transcript_upload(uploaded_file) -> Optional[str]:
    """
    Handle transcript PDF upload and validation.
    
    Returns:
        Path to saved transcript or None if validation fails
    """
    if not uploaded_file:
        return None
    
    # Create temp directory if needed
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    
    # Save uploaded file
    file_path = temp_dir / uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Validate PDF
    is_valid, error = validate_pdf_file(file_path)
    
    if not is_valid:
        st.error(f"❌ Invalid PDF: {error}")
        file_path.unlink()  # Delete invalid file
        return None
    
    st.success(f"✅ Transcript uploaded: {uploaded_file.name}")
    return str(file_path)


def render_suggestions(suggestions: List[str]):
    """Render clickable suggestion chips."""
    if not suggestions:
        return
    
    st.markdown("**💡 You might want to ask:**")
    
    cols = st.columns(min(len(suggestions), 3))
    for idx, suggestion in enumerate(suggestions):
        col_idx = idx % len(cols)
        with cols[col_idx]:
            if st.button(suggestion, key=f"suggestion_{idx}_{time.time()}"):
                # Simulate user clicking suggestion
                handle_user_input(suggestion)


def handle_user_input(user_message: str):
    """Process user input and get bot response."""
    
    # Add user message to history
    add_message("user", user_message)
    
    # Show thinking indicator
    with st.spinner("🤔 Thinking..."):
        try:
            # Prepare uploaded files info
            uploaded_files = None
            if st.session_state.uploaded_transcript_path:
                uploaded_files = [{
                    "name": Path(st.session_state.uploaded_transcript_path).name,
                    "path": st.session_state.uploaded_transcript_path,
                }]
            
            # Get response from chat service
            response: ChatResponse = st.session_state.chat_service.process_message(
                user_message=user_message,
                conversation_history=format_message_history(),
                session_id=st.session_state.session_id,
                uploaded_files=uploaded_files,
            )
            
            # Add assistant response
            add_message(
                "assistant",
                response.message,
                metadata=response.metadata,
            )
            
            # Store student grades if returned
            if response.metadata.get("student_grades"):
                st.session_state.student_grades = response.metadata["student_grades"]
            
            # Render suggestions
            if response.suggestions:
                render_suggestions(response.suggestions)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            
            # Provide user-friendly error messages
            error_str = str(e).lower()
            if "api key" in error_str or "403" in error_str:
                user_message = "🔑 There's an issue with the API configuration. Please check your API key."
            elif "rate limit" in error_str or "429" in error_str:
                user_message = "⏳ We're experiencing high demand. Please wait a moment and try again."
            elif "timeout" in error_str:
                user_message = "⏱️ The request took too long. Please try again with a simpler question."
            elif "no grades" in error_str:
                user_message = "📄 I couldn't find any grades in the transcript. Please make sure it's a valid transcript PDF."
            else:
                user_message = "😅 I ran into a small hiccup processing your request. Could you try rephrasing your question?"
            
            add_message(
                "assistant",
                user_message,
                metadata={"error": True},
            )


# ============================================================================
# SIDEBAR
# ============================================================================

def render_sidebar():
    """Render sidebar with app info and controls."""
    
    with st.sidebar:
        # 1. Profile Section (Lufga Style)
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 25px;">
            <div style="width: 50px; height: 50px; border-radius: 12px; background: linear-gradient(135deg, #A3E28B 0%, #F4C0F2 100%); 
                        display: flex; align-items: center; justify-content: center; font-size: 24px;">
                👤
            </div>
            <div style="margin-left: 15px;">
                <p style="margin: 0; font-size: 12px; color: #888;">Good Afternoon,</p>
                <p style="margin: 0; font-size: 16px; font-weight: 700; color: #030318;">Future Student</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. Progress Cards (Lufga Style)
        if st.session_state.student_grades:
            gpa = sum(st.session_state.student_grades.values()) / len(st.session_state.student_grades)
            progress_val = int((gpa / 20) * 100)
            
            st.markdown(f"""
            <div style="background: #030318; padding: 20px; border-radius: 16px; color: white; margin-bottom: 20px;">
                <p style="margin: 0; font-size: 14px; opacity: 0.8;">Readiness Score</p>
                <h2 style="margin: 5px 0; color: white; font-size: 28px;">{progress_val}%</h2>
                <div style="width: 100%; background: #ffffff33; height: 8px; border-radius: 4px; margin-top: 10px;">
                    <div style="width: {progress_val}%; background: #A3E28B; height: 8px; border-radius: 4px;"></div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 25px;">
                <div style="background: #FFF9E6; padding: 15px; border-radius: 16px; border: 1px solid #FFEBB3;">
                   <p style="margin: 0; font-size: 12px; color: #8B6E00;">Avg GPA</p>
                   <p style="margin: 5px 0 0 0; font-weight: 700; font-size: 18px; color: #8B6E00;">{gpa:.1f}</p>
                </div>
                <div style="background: #F0E4FF; padding: 15px; border-radius: 16px; border: 1px solid #D9C2FF;">
                   <p style="margin: 0; font-size: 12px; color: #5B2C9F;">Subjects</p>
                   <p style="margin: 5px 0 0 0; font-weight: 700; font-size: 18px; color: #5B2C9F;">{len(st.session_state.student_grades)}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # 3. Navigation/Actions
        st.markdown("### 📄 Transcript")
        
        uploaded_file = st.file_uploader(
            "Upload your transcript (PDF)",
            type=["pdf"],
            help="Upload your Portuguese high school transcript for personalized analysis",
            key="transcript_uploader",
        )
        
        if uploaded_file:
            transcript_path = handle_transcript_upload(uploaded_file)
            if transcript_path:
                st.session_state.uploaded_transcript_path = transcript_path
                # We don't parse here, the orchestrator/tools handle it via chat
        
        # Show current transcript
        if st.session_state.uploaded_transcript_path:
            st.success(f"✅ Transcript loaded")
            if st.button("🗑️ Remove Transcript", use_container_width=True):
                # Delete file
                try:
                    Path(st.session_state.uploaded_transcript_path).unlink()
                except Exception:
                    pass
                st.session_state.uploaded_transcript_path = None
                st.session_state.student_grades = None
                st.rerun()
        
        st.divider()
        
        # Session info
        with st.expander("📊 System Status", expanded=False):
            st.caption(f"**Model:** {GEMINI_MODEL}")
            st.caption(f"**Chat History:** {st.session_state.conversation_count} msgs")
            st.caption(f"**Session ID:** {st.session_state.session_id[:8]}...")
        
        st.divider()
        
        # Clear conversation
        if st.button("🔄 Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_count = 0
            st.session_state.student_grades = None
            st.rerun()
        
        st.divider()
        
        # Quick start guide
        with st.expander("🚀 Quick Start Guide"):
            st.markdown("""
            **Getting Started:**
            
            1. **Upload your transcript** (optional)
            2. **Ask questions** like:
               - "What majors match my interests?"
               - "Analyze my grades"
               - "What should I study for Computer Science?"
            3. **Get personalized recommendations**
            """)
        
        # Footer
        st.markdown("---")
        st.caption("🎓 University Readiness Assistant")
        st.caption("🤖 Capstone Project 2026")


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main application entry point."""
    
    # Initialize session state
    initialize_session_state()
    
    # Render sidebar
    render_sidebar()
    
    # Dashboard Header
    col1, col2 = st.columns([1, 8])
    with col1:
        try:
            st.image("assets/logo.png", width=80)
        except Exception:
            st.markdown("# 🎓")
    with col2:
        st.title("Ready4Uni - University Readiness Assistant")
        st.markdown("#### Your intelligent companion for university major selection")
    
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    
    # Welcome cards for new sessions
    if len(st.session_state.messages) == 0:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #F0E4FF 0%, #D9C2FF 100%); padding: 25px; border-radius: 24px; color: #5B2C9F; height: 100%;">
                <p style="margin: 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Step 1</p>
                <h2 style="color: #5B2C9F; margin: 10px 0;">Transcript Analysis</h2>
                <p style="font-size: 15px; opacity: 0.9;">Upload your transcript in the sidebar to get instant grade insights and path recommendations.</p>
                <div style="margin-top: 20px; font-weight: 700; display: flex; align-items: center;">
                    Upload in Sidebar <span style="margin-left: 10px; font-size: 20px;">↗</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="background: linear-gradient(135deg, #A3E28B 0%, #87C970 100%); padding: 25px; border-radius: 24px; color: #034D00; height: 100%;">
                <p style="margin: 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">Step 2</p>
                <h2 style="color: #034D00; margin: 10px 0;">Major Discovery</h2>
                <p style="font-size: 15px; opacity: 0.9;">Tell me your interests to find the perfect university courses at NOVA and across Portugal.</p>
                <div style="margin-top: 20px; font-weight: 700;">
                    Start Typing Below ↓
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)
    
    # Display conversation history
    for message in st.session_state.messages:
        render_chat_message(message)
    
    # Chat input
    user_input = st.chat_input(
        "Type your question here...",
        key="chat_input",
    )
    
    if user_input:
        handle_user_input(user_input)
        st.rerun()
    
    # Example questions (shown when no conversation yet)
    if len(st.session_state.messages) == 0:
        st.markdown("---")
        st.markdown("### 💡 Example Questions:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Discover majors", use_container_width=True):
                handle_user_input("I love programming and problem-solving. What majors should I consider?")
                st.rerun()
        
        with col2:
            if st.button("📊 Grade requirements", use_container_width=True):
                handle_user_input("What grades do I need for Computer Science?")
                st.rerun()
        
        with col3:
            if st.button("📚 Study resources", use_container_width=True):
                handle_user_input("How can I improve my Math grade from 13 to 16?")
                st.rerun()


# ============================================================================
# ERROR HANDLING & ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        st.error(f"""
        ❌ **Application Error**
        
        An unexpected error occurred: {str(e)}
        
        Please refresh the page or contact support if the issue persists.
        """)
