import os
import requests
import json
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

# Get API keys from environment
zyte_api_key = os.getenv("ZYTE_API_KEY")

def test_huggingface_embeddings():
    """Test if HuggingFace Sentence Transformers can load and create embeddings"""
    print("\nTesting HuggingFace Sentence Transformers...")
    try:
        print("Loading model - this may take a moment on first run...")
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        
        # Try creating an embedding
        embedding = model.encode("Hello world", convert_to_numpy=True)
        
        if embedding is not None and len(embedding) > 0:
            print(f"✅ HuggingFace model loaded successfully! (Vector dimension: {len(embedding)})")
            return True
        else:
            print("❌ Failed to generate embeddings.")
            return False
    except Exception as e:
        print(f"❌ Error loading or using HuggingFace model: {str(e)}")
        return False

def test_zyte_api():
    """Test if Zyte API key works by requesting extraction from a simple website"""
    print("\nTesting Zyte API...")
    try:
        url = "https://api.zyte.com/v1/extract"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "url": "https://example.com",
            "browserHtml": True
        }
        
        response = requests.post(
            url,
            auth=(zyte_api_key, ""),
            headers=headers,
            data=json.dumps(payload)
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Zyte API key is working correctly!")
            return True
        else:
            print(f"❌ Zyte API error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Zyte API error: {str(e)}")
        return False

if __name__ == "__main__":
    print("API and Model Test Results")
    print("=========================")
    
    hf_success = test_huggingface_embeddings()
    zyte_success = test_zyte_api()
    
    if hf_success and zyte_success:
        print("\n✅ All components are working! Ready to proceed with implementation.")
    else:
        print("\n❌ Some components are not working. Please check the errors above.")