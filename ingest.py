import os
import time
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

load_dotenv()

DATA_DIR = "data" 
INDEX_NAME = "uae-finance-index"
TRACKER_FILE = "processed_files.txt" # <-- The new memory file

def get_processed_files():
    """Reads the tracker file and returns a set of already processed filenames."""
    if not os.path.exists(TRACKER_FILE):
        return set()
    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        return set(f.read().splitlines())

def mark_as_processed(filenames):
    """Saves the newly processed filenames to the tracker file."""
    with open(TRACKER_FILE, "a", encoding="utf-8") as f:
        for name in filenames:
            f.write(f"{name}\n")

def ingest_directory():
    if not os.path.exists(DATA_DIR):
        print(f"❌ Error: Directory '{DATA_DIR}' not found.")
        return

    # 1. Get all PDFs, then filter out the ones we already processed
    all_pdf_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
    processed_files = get_processed_files()
    
    # The Magic Line: Only keep files that are NOT in the tracker list
    new_pdfs = [f for f in all_pdf_files if f not in processed_files]

    if not new_pdfs:
        print(f"✅ All {len(all_pdf_files)} PDFs in the folder are already in the database. Nothing new to add!")
        return

    print(f"🚀 Found {len(new_pdfs)} NEW PDFs. Starting ingestion...")
    
    all_chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    for filename in new_pdfs:
        file_path = os.path.join(DATA_DIR, filename)
        print(f"📄 Processing: {filename}...")
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            chunks = text_splitter.split_documents(documents)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"⚠️ WARNING: Could not read {filename}. Skipping. Error: {e}")
            continue

    print(f"\n✂️ Total chunks successfully extracted: {len(all_chunks)}")

    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-2-preview", 
        output_dimensionality=768
    )

    print(f"🌐 Connecting to Pinecone index: '{INDEX_NAME}'...")
    vectorstore = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)

    batch_size = 20
    # Start loop from the chunk where it crashed last time.
    # Change '0' to '6840' to resume where you left off!
    start_index = 6840 
    
    for i in range(start_index, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        success = False
        retries = 0
        
        # The Unbreakable Retry Loop
        while not success and retries < 5:
            try:
                print(f"📤 Uploading chunks {i} to {i + len(batch)} of {len(all_chunks)}...")
                vectorstore.add_documents(batch)
                success = True # It worked, break the while loop
                
                if i + batch_size < len(all_chunks):
                    print("⏳ Sleeping for 20s...")
                    time.sleep(20)
                    
            except Exception as e:
                retries += 1
                print(f"\n🔥 API Error (Attempt {retries}/5): {e}")
                print("💤 Server hiccup or rate limit. Sleeping for 60 seconds before retrying...")
                time.sleep(60)
                
        if not success:
            print(f"❌ Failed to upload batch starting at {i} after 5 retries. Aborting to save progress.")
            break

    mark_as_processed(new_pdfs)
    print("✅ Ingestion process finished. Tracker updated.")

if __name__ == "__main__":
    ingest_directory()