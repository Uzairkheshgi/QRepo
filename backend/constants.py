# File extensions to include in indexing
INCLUDE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".cs",
    ".php",
    ".rb",
    ".go",
    ".rs",
    ".swift",
    ".kt",
    ".scala",
    ".r",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".ps1",
    ".bat",
    ".dockerfile",
    ".makefile",
    ".cmake",
    ".gradle",
    ".maven",
    ".pom",
    ".sbt",
}

# Directories to exclude from indexing
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "venv",
    "env",
    ".venv",
    ".env",
    "build",
    "dist",
    "target",
    "bin",
    "obj",
    ".vs",
    ".vscode",
    ".idea",
    "coverage",
    ".coverage",
    "htmlcov",
    "vendor",
    "bower_components",
    ".next",
    ".nuxt",
    "out",
    "public",
    "static",
    "assets",
    "images",
    "img",
    "icons",
    "fonts",
    "media",
}

# Files to exclude from indexing
EXCLUDE_FILES = {
    ".gitignore",
    ".gitattributes",
    ".gitmodules",
    ".gitkeep",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "requirements.txt",
    "Pipfile.lock",
    "poetry.lock",
    "composer.lock",
    "Gemfile.lock",
    "Cargo.lock",
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
}

# File type mapping for semantic chunking
FILE_TYPE_MAPPING = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".dockerfile": "dockerfile",
    ".makefile": "makefile",
}

# Text files without extensions
TEXT_FILES_WITHOUT_EXTENSION = {
    "dockerfile",
    "makefile",
    "rakefile",
    "gemfile",
    "readme",
    "changelog",
    "license",
    "authors",
    "contributors",
}

# RAG Configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "code_embeddings"
BATCH_SIZE = 100
MAX_QUERY_RESULTS = 5

# File size limits (in bytes)
MAX_FILE_SIZE = 1024 * 1024
MIN_FILE_SIZE = 0

# Confidence scoring thresholds (cosine similarity - lower is better)
HIGH_CONFIDENCE_DISTANCE = 0.4
MEDIUM_CONFIDENCE_DISTANCE = 0.7
HIGH_CONFIDENCE_SOURCES = 2
MEDIUM_CONFIDENCE_SOURCES = 1

# OpenAI Configuration
OPENAI_MODEL = "gpt-4"
OPENAI_MAX_TOKENS = 1000
OPENAI_TEMPERATURE = 0.1

# Directory paths
REPOSITORIES_DIR = "repositories"
CACHE_DIR = "repository_cache"
SESSIONS_FILE = "sessions.json"

# Prompts
SYSTEM_PROMPT = "You are an expert code analyst who provides accurate, detailed answers based on code context."

BASE_ANSWER_PROMPT = """
You are an expert code analyst. Answer the user's question about the codebase based ONLY on the provided context.

Question: {question}

Context from the codebase:
{context}

Instructions:
1. Answer based ONLY on the information provided in the context
2. Be specific and reference actual code snippets when relevant
3. If the context doesn't contain enough information to answer the question, say so
4. Focus on the actual implementation details, not assumptions
5. Reference specific files and code patterns when possible

Answer:
"""

CONFIDENCE_ANSWER_PROMPT = """
You are an expert code analyst. Answer the user's question about the codebase based ONLY on the provided context.

Question: {question}

Context from the codebase:
{context}

Instructions:
1. Answer based ONLY on the information provided in the context
2. Be specific and reference actual code snippets when relevant
3. If the context doesn't contain enough information to answer the question, say so
4. Focus on the actual implementation details, not assumptions
5. Reference specific files and code patterns when possible
6. At the end of your response, provide a confidence assessment

Confidence Assessment Guidelines:
- HIGH: You found clear, specific information that directly answers the question with concrete examples
- MEDIUM: You found relevant information that partially answers the question or requires some interpretation
- LOW: The context provides limited or indirect information, or the question cannot be adequately answered

End your response with: "Confidence: [HIGH/MEDIUM/LOW]"

Answer:
"""

