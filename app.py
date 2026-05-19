import os
import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage

try:
    from streamlit_mic_recorder import speech_to_text
except ImportError:
    st.error("Please run: pip install streamlit-mic-recorder")
    st.stop()

# Load API keys
load_dotenv()

# --- Page Configuration ---
st.set_page_config(page_title="UAE Finance Bot", page_icon="✨", layout="centered")

# --- UI UPGRADE: Theme & Settings Management ---
if "theme" not in st.session_state:
    st.session_state.theme = "Dark"

# --- Sidebar Layout ---
with st.sidebar:
    st.title("✨ Settings")
    st.session_state.theme = st.radio("Appearance", ["Dark", "Light"], horizontal=True, label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("### 🎙️ Voice Input")
    st.caption("Click below to speak your question:")
    # The STT button is safely inside the sidebar.
    spoken_text = speech_to_text(start_prompt="🎙️ Start Recording", stop_prompt="🛑 Stop Recording", language='en', just_once=True, key='STT_mic')
    
    st.markdown("---")
    st.markdown("### 🕒 Recent History")
    if "messages" in st.session_state and len(st.session_state.messages) > 0:
        for msg in reversed(st.session_state.messages):
            if msg["role"] == "user":
                st.caption(f"💬 {msg['content'][:35]}...")
    else:
        st.caption("No history yet.")
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_history = []
        st.rerun()

# --- Advanced Modern CSS ---
bg_color = "#ffffff" if st.session_state.theme == "Light" else "#131314"
sidebar_bg = "#f8f9fa" if st.session_state.theme == "Light" else "#1e1f20"
text_color = "#1f1f1f" if st.session_state.theme == "Light" else "#e3e3e3"
user_bubble = "#f0f4f9" if st.session_state.theme == "Light" else "#1e1f20"
bot_bubble = "transparent"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    
    /* --- 1. THEME BACKGROUND OVERRIDES --- */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{
        background-color: {bg_color} !important;
    }}
    
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
    }}
    
    /* --- 2. BLACK BOX ERADICATION --- */
    
    /* Chat Input Inner Black Box - Targeting BaseWeb explicitly */
    [data-testid="stChatInput"] div[data-baseweb="textarea"],
    [data-testid="stChatInput"] div[data-baseweb="base-input"],
    [data-testid="stChatInput"] textarea {{
        background-color: transparent !important;
        background: transparent !important;
    }}

    /* Remove Bottom Gradient */
    [data-testid="stBottom"], 
    [data-testid="stBottom"] > div {{
        background-color: transparent !important;
        background: transparent !important;
        background-image: none !important;
    }}

    /* Style the outer chat input container cleanly */
    [data-testid="stChatInput"] > div {{
        background-color: {sidebar_bg} !important;
        border: 1px solid #5f6368 !important;
        border-radius: 10px !important;
    }}

    /* Clear Chat Button */
    .stButton > button {{
        background-color: transparent !important;
        color: {text_color} !important;
        border: 1px solid #5f6368 !important;
    }}
    .stButton > button:hover {{
        background-color: {sidebar_bg} !important;
    }}

    /* Mic Component Background Stripping (No more filters!) */
    div[data-testid^="stCustomComponent"],
    div[data-testid^="stCustomComponent"] > iframe,
    div[data-testid="element-container"]:has(iframe) {{
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }}
    
    /* --- 3. TEXT COLOR VISIBILITY --- */
    html, body, [class*="css"], p, h1, h2, h3, h4, h5, h6, span {{
        font-family: 'Inter', sans-serif;
        color: {text_color} !important;
    }}
    
    [data-testid="stChatInput"] textarea {{
        color: {text_color} !important;
        -webkit-text-fill-color: {text_color} !important;
    }}
    
    /* --- 4. CHAT BUBBLE STYLING --- */
    .block-container {{ max-width: 850px; padding-top: 3rem; padding-bottom: 6rem; }}
    
    .stChatMessage {{ padding: 1rem; border-radius: 12px; margin-bottom: 8px; }}
    div[data-testid="stChatMessage"]:nth-child(even) {{ background-color: {user_bubble}; }}
    div[data-testid="stChatMessage"]:nth-child(odd) {{ background-color: {bot_bubble}; }}
    
    /* Clean up default Streamlit clutter */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)


# --- Initialize AI & Database ---
@st.cache_resource
def load_rag_pipeline():
    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-2-preview", output_dimensionality=768)
    vectorstore = PineconeVectorStore(index_name="uae-finance-index", embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 25})
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.2)
    
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given a chat history and the latest user question, formulate a standalone question. Do NOT answer it."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)
    
    qa_system_prompt = (
        "You are a friendly, highly intelligent UAE Financial and Legal AI. "
        "RULE 1 - SMALL TALK: If the user greets you, respond naturally and warmly. No context needed. "
        "RULE 2 - KNOWLEDGE: Answer strictly based on the context provided. Use clean formatting. "
        "If unsure, say 'I cannot find that in my current records.'\n\nContext: {context}"
    )
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    return create_retrieval_chain(history_aware_retriever, question_answer_chain)

try:
    rag_chain = load_rag_pipeline()
except Exception as e:
    st.error(f"Failed to connect to AI: {e}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Modern Empty State ---
empty_state_placeholder = st.empty()

if len(st.session_state.messages) == 0:
    with empty_state_placeholder.container():
        st.markdown(f"<h1 style='text-align: center; font-weight: 600;'>How can I help you today?</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>I am trained on official UAE corporate laws, labor rights, and banking regulations.</p><br>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)

        with c1:

            st.info("🏢 **Finance and Accounting**\n\n Explore Financial Regulations and Accounting Practices in the UAE.")

        with c2:

            st.success("💼 **Banking**\n\n Learn about UAE banking regulations and practices.")

        st.markdown("<br><br>", unsafe_allow_html=True)
else:
    empty_state_placeholder.empty()

# Display history in UI
for message in st.session_state.messages:
    avatar_icon = "👤" if message["role"] == "user" else "✨"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

# --- User Input Area ---
typed_text = st.chat_input("Ask about UAE laws, banking...")

# Combine inputs
user_query = typed_text if typed_text else spoken_text

if user_query:
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)

    # 2. Process Assistant Message
    with st.chat_message("assistant", avatar="✨"):
        
        with st.spinner("Thinking..."):
            try:
                pipeline_response = rag_chain.invoke({
                    "input": user_query,
                    "chat_history": st.session_state.chat_history
                })
                full_response = pipeline_response["answer"]
                
            except KeyError:
                direct_prompt = f"The user said: '{user_query}'. Respond naturally and warmly in 1-2 sentences."
                fallback_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.5)
                full_response = fallback_llm.invoke(direct_prompt).content
            
        # Print the final response
        st.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        st.session_state.chat_history.extend([
            HumanMessage(content=user_query),
            AIMessage(content=full_response)
        ])
        
        st.rerun()