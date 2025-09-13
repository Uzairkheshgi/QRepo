# Project Overview
This project clones public GitHub repositories, analyzes their code, and lets the user ask natural language questions about the codebase. Get instant answers about how functions work, what files do, and understand complex codebases without reading through thousands of lines.

## Technologies Used

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **ChromaDB**: Vector database for storing embeddings
- **Sentence Transformers**: Text embedding generation
- **OpenAI GPT-4**: Large language model for Q&A
- **Tree-sitter**: Multi-language code parsing

### Frontend
- **React**: Modern JavaScript library for building user interfaces
- **Axios**: HTTP client for API communication
- **Tailwind_CSS**: Modern styling with responsive design


### 1. Clone the Repository
```bash
git clone https://github.com/Uzairkheshgi/QRepo
cd assessment_git_sleuth
```

### 2. Backend Setup
`Create and activate virtual environment`
```bash
python3 -m venv venv
source venv/bin/activate
```

# Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
```

## Running the Application

### Start Backend
```bash
cd backend
python main.py
```
Backend will be available at `http://localhost:8000/docs`

### Start Frontend
```bash
cd frontend
npm start
```
Frontend will be available at `http://localhost:3000`

## 📖 Usage
1. **Index Repository**: Enter a GitHub repository URL and click `Index Repository`
2. **Ask Questions**: Once indexing is complete, ask questions about the codebase


## API Endpoints

### POST /index
Index a GitHub repository for analysis.

**Response**
```json
{
  "repo_url": "https://github.com/user/repo"
}
```

### GET /status/{session_id}
Get the current status of repository indexing.

**Response:**
```json
{
  "status": "indexing|ready|error",
  "message": "Status details",
  "progress": 75
}
```

### POST /query
Ask questions about an indexed repository.
**Response**
```json
{
  "session_id": "unique_id",
  "question": "How does authentication work?"
}
```

## Sample .env
`OPENAI_API_KEY = "your_open_ai_api_key"`