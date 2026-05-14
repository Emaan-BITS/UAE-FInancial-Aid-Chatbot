# UAE Finance Bot

Empowering financial literacy with AI-driven insights from official UAE regulations. Built with Streamlit, LangChain, Pinecone, and Google Gemini.

---

## Overview
The **UAE Finance Bot** is a localized Retrieval-Augmented Generation (RAG) application. It ingests official documentation regarding UAE Corporate Tax, VAT, and banking frameworks, converting complex legal jargon into straightforward, easy-to-understand guidance suitable for all age groups.

---

## Features
* **Context-Aware Answers:** Utilizes semantic search to ground all responses strictly in official ingested source material.
* **Optimized Data Pipeline:** Features automated document chunking, embeddings generation, and safe batch uploading that respects API rate limits.
* **Blazing Fast LLM:** Powered by `gemini-2.5-flash` for rapid conversational responsiveness and high-quality synthesis.
* **Clean UI Interface:** A sleek, responsive web application built on Streamlit featuring complete chat session state management.
* **Built-in Guardrails:** System instructions strictly prevent hallucinations, forcing the bot to decline answering if the context is missing.

---

## Tech Stack

| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend** | Streamlit | Chat interface and web application rendering |
| **Framework** | LangChain | Orchestrating document loading, chunking, and chains |
| **Embeddings** | Gemini Embedding 2 Preview | Vectorizing raw text into 768-dimensional space |
| **Vector Database**| Pinecone | Cloud-native storage and semantic similarity retrieval |
| **LLM Brain** | Gemini 2.5 Flash | Generating tailored, structured financial explanations |

---

## Project Structure

```text
├── data/
│   └── uae_tax_guide.pdf       # Source regulatory documentation
├── app.py                      # Main Streamlit web application
├── ingest.py                   # Document processing and database population script
├── .env                        # Environment variables (API Keys)
└── README.md                   # Project documentation
