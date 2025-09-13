"""
RAG (Retrieval-Augmented Generation) service for code Q&A.

Provides intelligent question-answering capabilities about codebases using
vector embeddings, semantic search, and LLM integration with confidence scoring.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import numpy as np
import openai
import tiktoken
from chromadb.config import Settings
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Load environment variables
load_dotenv()

import constants
from models import FileInfo, Source
from services.semantic_chunker import SemanticChunker
from utils import (
    normalize_repo_url,
    generate_files_hash,
    get_confidence_level,
    combine_confidence_levels,
    extract_confidence_from_text,
    create_overlap_lines,
    load_json_file,
    save_json_file
)

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        # Initialize OpenAI client
        openai.api_key = os.getenv("OPENAI_API_KEY")

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(constants.EMBEDDING_MODEL)

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path="./chroma_db", settings=Settings(anonymized_telemetry=False)
        )

        # Text splitter configuration
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.chunk_size = constants.CHUNK_SIZE
        self.chunk_overlap = constants.CHUNK_OVERLAP

        # Collection for storing embeddings
        self.collection_name = constants.COLLECTION_NAME

        # Initialize semantic chunking service
        self.semantic_chunker = SemanticChunker()

    async def create_index(self, session_id: str, files: List[FileInfo], repo_url: str = None):
        """Create vector index from repository files"""
        try:
            # Create collection for this session
            collection_name = f"{self.collection_name}_{session_id}"
            
            # Normalize repository URL for consistent embedding reuse
            normalized_repo_url = normalize_repo_url(repo_url) if repo_url else None
            
            # Check if we can reuse existing embeddings (disabled for now)
            # if normalized_repo_url and self._can_reuse_embeddings(normalized_repo_url, files):
            #     logger.info(f"Reusing existing embeddings for repository: {normalized_repo_url}")
            #     self._reuse_existing_embeddings(collection_name, normalized_repo_url, session_id)
            #     return
            
            # Create new index
            self._delete_collection_if_exists(collection_name)
            
            collection = self.chroma_client.create_collection(
                name=collection_name, metadata={"session_id": session_id, "repo_url": normalized_repo_url}
            )

            # Process files and create chunks
            chunks_data = self._process_files_to_chunks(files, session_id)
            
            # Batch add to ChromaDB
            self._batch_add_to_collection(collection, chunks_data)
            
            # Store embedding metadata for future reuse
            if normalized_repo_url:
                self._store_embedding_metadata(normalized_repo_url, files, session_id)

            logger.info(f"Successfully created index with {len(chunks_data['chunks'])} chunks")

        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise Exception(f"Failed to create vector index: {str(e)}")

    def _create_chunks(self, file_info: FileInfo) -> List[str]:
        """Create text chunks from file content using semantic chunking"""
        content = file_info.content

        # Use semantic chunker for all files
        semantic_chunks = self.semantic_chunker.create_semantic_chunks(
            content, file_info.file_type, file_info.path
        )

        # Extract just the content for backward compatibility
        return [chunk["content"] for chunk in semantic_chunks]

    def _create_semantic_chunks(self, content: str, file_type: str) -> List[str]:
        """Create semantic chunks for code files"""
        chunks = []
        lines = content.split("\n")

        current_chunk = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1  # +1 for newline

            # Check if adding this line would exceed chunk size
            if current_size + line_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunk_text = "\n".join(current_chunk)
                if chunk_text.strip():
                    chunks.append(chunk_text)

                # Start new chunk with overlap
                overlap_lines = create_overlap_lines(current_chunk, constants.CHUNK_OVERLAP)
                current_chunk = overlap_lines + [line]
                current_size = sum(len(l) + 1 for l in current_chunk)
            else:
                current_chunk.append(line)
                current_size += line_size

        # Add final chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            if chunk_text.strip():
                chunks.append(chunk_text)

        return chunks


    def _create_text_chunks(self, content: str) -> List[str]:
        """Create simple text chunks"""
        # Split by sentences first
        sentences = content.split(". ")
        chunks = []
        current_chunk = []
        current_size = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_size = len(sentence) + 2  # +2 for '. '

            if current_size + sentence_size > self.chunk_size and current_chunk:
                chunk_text = ". ".join(current_chunk) + "."
                chunks.append(chunk_text)
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size

        # Add final chunk
        if current_chunk:
            chunk_text = ". ".join(current_chunk) + "."
            chunks.append(chunk_text)

        return chunks

    async def query(self, session_id: str, question: str) -> Dict[str, Any]:
        """Query the indexed repository"""
        try:
            # Get collection
            collection_name = f"{self.collection_name}_{session_id}"
            collection = self.chroma_client.get_collection(collection_name)

            # Generate query embedding
            query_embedding = self.embedding_model.encode(question).tolist()

            # Search for relevant chunks
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=constants.MAX_QUERY_RESULTS,
                include=["documents", "metadatas", "distances"],
            )

            # Extract relevant chunks
            relevant_chunks = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]

            # Prepare context for LLM
            context_sources = []
            context_text = ""

            for i, (chunk, metadata, distance) in enumerate(
                zip(relevant_chunks, metadatas, distances)
            ):
                # Create source reference
                source = Source(
                    file=metadata["file_path"],
                    snippet=chunk[:200] + "..." if len(chunk) > 200 else chunk,
                    line_number=None,  # Could be enhanced to include line numbers
                )
                context_sources.append(source)

                # Add to context
                context_text += f"\n--- File: {metadata['file_path']} ---\n{chunk}\n"

            # Generate answer using OpenAI with enhanced confidence scoring
            answer, confidence = await self._generate_answer_with_confidence(
                question, context_text, context_sources, distances
            )

            return {
                "answer": answer,
                "sources": [source.dict() for source in context_sources],
                "confidence": confidence,
            }

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise Exception(f"Query failed: {str(e)}")

    async def _generate_answer(
        self, question: str, context: str, sources: List[Source]
    ) -> str:
        """Generate answer using OpenAI GPT-4"""
        try:
            prompt = constants.BASE_ANSWER_PROMPT.format(question=question, context=context)

            client = openai.OpenAI(api_key=openai.api_key)
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=constants.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": constants.SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=constants.OPENAI_MAX_TOKENS,
                temperature=constants.OPENAI_TEMPERATURE,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return f"I encountered an error while generating the answer: {str(e)}"

    async def _generate_answer_with_confidence(
        self, question: str, context: str, sources: List[Source], distances: List[float]
    ) -> tuple[str, str]:
        """Generate answer with enhanced confidence scoring"""
        try:
            # Calculate base confidence from vector distances
            avg_distance = np.mean(distances)
            base_confidence = self._calculate_base_confidence(
                avg_distance, len(sources)
            )

            # Create enhanced prompt with confidence instruction
            prompt = constants.CONFIDENCE_ANSWER_PROMPT.format(question=question, context=context)

            client = openai.OpenAI(api_key=openai.api_key)
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=constants.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": constants.SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=constants.OPENAI_MAX_TOKENS,
                temperature=constants.OPENAI_TEMPERATURE,
            )

            answer = response.choices[0].message.content.strip()

            # Extract confidence from LLM response or use base confidence
            confidence = extract_confidence_from_text(answer)

            return answer, confidence

        except Exception as e:
            logger.error(f"Error generating answer with confidence: {str(e)}")
            return (
                f"I encountered an error while generating the answer: {str(e)}",
                "low",
            )

    def _calculate_base_confidence(self, avg_distance: float, num_sources: int) -> str:
        """Calculate base confidence from vector search results"""
        logger.info(
            f"Calculating confidence: avg_distance={avg_distance:.3f}, num_sources={num_sources}"
        )

        # Calculate confidence levels
        distance_confidence = get_confidence_level(
            avg_distance, 
            constants.HIGH_CONFIDENCE_DISTANCE, 
            constants.MEDIUM_CONFIDENCE_DISTANCE, 
            reverse=True  # Lower distance is better
        )
        source_confidence = get_confidence_level(
            num_sources, 
            constants.HIGH_CONFIDENCE_SOURCES, 
            constants.MEDIUM_CONFIDENCE_SOURCES
        )

        # Combine confidence levels
        return combine_confidence_levels(distance_confidence, source_confidence)



    def _delete_collection_if_exists(self, collection_name: str) -> None:
        """Delete collection if it exists"""
        try:
            self.chroma_client.delete_collection(collection_name)
        except:
            pass

    def _process_files_to_chunks(self, files: List[FileInfo], session_id: str) -> Dict[str, List]:
        """Process files and create chunks with embeddings and metadata"""
        chunks_data = {"chunks": [], "embeddings": [], "metadatas": [], "ids": []}
        chunk_id = 0

        for file_info in files:
            chunks = self._create_chunks(file_info)
            for i, chunk in enumerate(chunks):
                chunks_data["chunks"].append(chunk)
                chunks_data["embeddings"].append(self.embedding_model.encode(chunk).tolist())
                chunks_data["metadatas"].append({
                    "file_path": file_info.path,
                    "file_type": file_info.file_type,
                    "chunk_index": i,
                    "session_id": session_id,
                })
                chunks_data["ids"].append(f"{session_id}_{chunk_id}")
                chunk_id += 1

        return chunks_data

    def _batch_add_to_collection(self, collection, chunks_data: Dict[str, List]) -> None:
        """Add chunks to collection in batches"""
        for i in range(0, len(chunks_data["chunks"]), constants.BATCH_SIZE):
            end_idx = min(i + constants.BATCH_SIZE, len(chunks_data["chunks"]))
            collection.add(
                embeddings=chunks_data["embeddings"][i:end_idx],
                documents=chunks_data["chunks"][i:end_idx],
                metadatas=chunks_data["metadatas"][i:end_idx],
                ids=chunks_data["ids"][i:end_idx],
            )
            logger.info(f"Added batch {i//constants.BATCH_SIZE + 1} to collection")


    def _can_reuse_embeddings(self, repo_url: str, files: List[FileInfo]) -> bool:
        """Check if we can reuse existing embeddings for this repository"""
        try:
            # Check if we have stored embedding metadata for this repo
            embedding_metadata = self._get_embedding_metadata(repo_url)
            if not embedding_metadata:
                return False
            
            # Check if file list matches (same files, same content)
            current_files_hash = generate_files_hash([{"path": f.path, "content": f.content} for f in files])
            stored_files_hash = embedding_metadata.get('files_hash')
            
            return current_files_hash == stored_files_hash
        except Exception as e:
            logger.warning(f"Error checking embedding reuse: {e}")
            return False


    def _get_embedding_metadata(self, repo_url: str) -> Optional[Dict]:
        """Get stored embedding metadata for repository"""
        try:
            import hashlib
            import json
            
            repo_hash = hashlib.md5(repo_url.encode()).hexdigest()
            metadata_file = Path("./chroma_db") / f"{repo_hash}_embedding_metadata.json"
            
            return load_json_file(metadata_file)
        except Exception as e:
            logger.warning(f"Error reading embedding metadata: {e}")
            return None

    def _store_embedding_metadata(self, repo_url: str, files: List[FileInfo], session_id: str) -> None:
        """Store embedding metadata for future reuse"""
        try:
            import hashlib
            import json
            
            repo_hash = hashlib.md5(repo_url.encode()).hexdigest()
            metadata_file = Path("./chroma_db") / f"{repo_hash}_embedding_metadata.json"
            
            metadata = {
                'repo_url': repo_url,
                'session_id': session_id,
                'files_hash': generate_files_hash([{"path": f.path, "content": f.content} for f in files]),
                'created_at': str(datetime.now()),
                'collection_name': f"{self.collection_name}_{session_id}"
            }
            
            save_json_file(metadata_file, metadata)
                
        except Exception as e:
            logger.warning(f"Error storing embedding metadata: {e}")

    def _reuse_existing_embeddings(self, collection_name: str, repo_url: str, session_id: str) -> None:
        """Reuse existing embeddings by copying from previous collection"""
        try:
            import hashlib
            
            # Find the most recent collection for this repository
            original_collection_name = self._find_latest_collection_for_repo(repo_url)
            if not original_collection_name:
                raise Exception("No existing collection found for this repository")
            
            # Check if original collection still exists
            try:
                original_collection = self.chroma_client.get_collection(original_collection_name)
            except:
                raise Exception("Original collection no longer exists")
            
            # Create new collection with same data
            self._delete_collection_if_exists(collection_name)
            
            # Get all data from original collection
            results = original_collection.get(include=["documents", "metadatas", "embeddings"])
            
            if not results['documents']:
                raise Exception("Original collection is empty")
            
            # Create new collection
            new_collection = self.chroma_client.create_collection(
                name=collection_name, 
                metadata={"session_id": session_id, "reused_from": original_collection_name, "repo_url": repo_url}
            )
            
            # Update metadata with new session_id
            updated_metadatas = []
            updated_ids = []
            
            for i, metadata in enumerate(results['metadatas']):
                updated_metadata = metadata.copy()
                updated_metadata['session_id'] = session_id
                updated_metadatas.append(updated_metadata)
                updated_ids.append(f"{session_id}_{i}")
            
            # Add data to new collection
            new_collection.add(
                embeddings=results['embeddings'],
                documents=results['documents'],
                metadatas=updated_metadatas,
                ids=updated_ids
            )
            
            logger.info(f"Successfully reused embeddings from {original_collection_name} to {collection_name}")
            
        except Exception as e:
            logger.error(f"Error reusing embeddings: {e}")
            raise Exception(f"Failed to reuse embeddings: {e}")

    def _find_latest_collection_for_repo(self, repo_url: str) -> Optional[str]:
        """Find the most recent collection for a repository"""
        try:
            import hashlib
            import json
            from datetime import datetime
            
            repo_hash = hashlib.md5(repo_url.encode()).hexdigest()
            metadata_file = Path("./chroma_db") / f"{repo_hash}_embedding_metadata.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            collection_name = metadata.get('collection_name')
            if not collection_name:
                return None
            
            # Check if the collection still exists
            try:
                self.chroma_client.get_collection(collection_name)
                return collection_name
            except:
                # Collection doesn't exist, try to find any collection with the same repo
                collections = self.chroma_client.list_collections()
                for collection in collections:
                    try:
                        collection_metadata = collection.metadata
                        if (collection_metadata and 
                            collection_metadata.get('repo_url') == repo_url):
                            return collection.name
                    except:
                        continue
                return None
                
        except Exception as e:
            logger.warning(f"Error finding latest collection for repo: {e}")
            return None
