"""
Repository cloning and file processing service.

Handles cloning of GitHub repositories, file filtering, content extraction,
and repository caching for efficient reuse.
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set

import aiofiles
from git import InvalidGitRepositoryError, Repo

import constants
from models import FileInfo
from utils import (
    generate_repo_hash, 
    normalize_repo_url, 
    remove_directory_if_exists,
    get_file_type,
    is_text_file
)

logger = logging.getLogger(__name__)


class RepositoryService:
    def __init__(self):
        self.repositories_dir = Path(constants.REPOSITORIES_DIR)
        self.repositories_dir.mkdir(exist_ok=True)
        
        # Cache directory for storing cloned repositories
        self.cache_dir = Path(constants.CACHE_DIR)
        self.cache_dir.mkdir(exist_ok=True)

        # File extensions to include
        self.include_extensions = constants.INCLUDE_EXTENSIONS

        # Directories to exclude
        self.exclude_dirs = constants.EXCLUDE_DIRS

        # Files to exclude
        self.exclude_files = constants.EXCLUDE_FILES

    async def clone_repository(self, repo_url: str, session_id: str) -> Path:
        """Clone a GitHub repository to local storage"""
        try:
            # Normalize repository URL first
            original_url = str(repo_url) if hasattr(repo_url, "str") else repo_url
            repo_url_str = normalize_repo_url(original_url)
            
            # Log URL normalization if it changed
            if repo_url_str != original_url:
                logger.info(f"Normalized repository URL: {original_url} -> {repo_url_str}")

            # Determine repository name and path
            is_local = os.path.exists(repo_url_str) and os.path.isdir(repo_url_str)
            repo_name = (os.path.basename(repo_url_str.rstrip("/")) if is_local 
                        else repo_url_str.split("/")[-1].replace(".git", ""))
            repo_path = self.repositories_dir / session_id / repo_name

            # Remove existing directory if it exists
            remove_directory_if_exists(repo_path)

            # Handle both local and remote repositories with caching
            # Use normalized URL for consistent caching
            cache_repo_path = self._get_cached_repo_path(repo_url_str)
            
            if cache_repo_path and cache_repo_path.exists():
                # Check if repository content has changed
                if not self._is_repo_content_changed(cache_repo_path, repo_url_str):
                    logger.info(f"Using unchanged cached repository: {cache_repo_path}")
                    shutil.copytree(cache_repo_path, repo_path)
                else:
                    logger.info(f"Repository content changed, updating cache: {repo_url_str}")
                    if is_local:
                        # For local repos, just recopy from source
                        shutil.rmtree(cache_repo_path)
                        shutil.copytree(repo_url_str, cache_repo_path)
                        # Update the stored hash
                        content_hash = self._get_repo_content_hash(Path(repo_url_str))
                        self._store_repo_hash(repo_url_str, content_hash)
                    else:
                        # For remote repos, pull latest changes
                        self._update_cached_repository(repo_url_str)
                    shutil.copytree(cache_repo_path, repo_path)
            else:
                # No cache exists, create new cache
                if is_local:
                    logger.info(f"Copying local repository: {repo_url_str}")
                    shutil.copytree(repo_url_str, repo_path)
                else:
                    logger.info(f"Cloning repository: {repo_url_str}")
                    Repo.clone_from(repo_url_str, repo_path)
                
                # Cache the repository for future use
                self._cache_repository(repo_path, repo_url_str)

            logger.info(f"Successfully cloned repository to: {repo_path}")
            return repo_path

        except Exception as e:
            logger.error(f"Error cloning repository: {str(e)}")
            raise Exception(f"Failed to clone repository: {str(e)}")

    async def process_repository_files(self, repo_path: Path) -> List[FileInfo]:
        """Process repository files and return structured file information"""
        files = []

        try:
            for file_path in self._walk_repository(repo_path):
                try:
                    file_info = await self._process_file(file_path, repo_path)
                    if file_info:
                        files.append(file_info)
                except Exception as e:
                    logger.warning(f"Error processing file {file_path}: {str(e)}")
                    continue

            logger.info(f"Processed {len(files)} files from repository")
            return files

        except Exception as e:
            logger.error(f"Error processing repository files: {str(e)}")
            raise Exception(f"Failed to process repository files: {str(e)}")

    def _walk_repository(self, repo_path: Path):
        """Walk through repository files, applying filters"""
        for root, dirs, files in os.walk(repo_path):
            # Remove excluded directories from dirs list to prevent walking into them
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for file in files:
                if file in self.exclude_files:
                    continue
                    
                file_path = Path(root) / file
                if (file_path.suffix.lower() in self.include_extensions or 
                    is_text_file(file_path)):
                    yield file_path


    async def _process_file(
        self, file_path: Path, repo_path: Path
    ) -> Optional[FileInfo]:
        """Process a single file and return FileInfo"""
        try:
            # Read file content
            async with aiofiles.open(
                file_path, "r", encoding="utf-8", errors="ignore"
            ) as f:
                content = await f.read()

            # Skip empty files or very large files
            if not content.strip() or len(content) > constants.MAX_FILE_SIZE:
                return None

            # Get relative path from repository root
            relative_path = file_path.relative_to(repo_path)

            # Determine file type
            file_type = get_file_type(file_path)

            return FileInfo(
                path=str(relative_path),
                content=content,
                file_type=file_type,
                size=len(content),
            )

        except Exception as e:
            logger.warning(f"Error reading file {file_path}: {str(e)}")
            return None




    def _get_cached_repo_path(self, repo_url: str) -> Optional[Path]:
        """Get the cached repository path if it exists"""
        try:
            repo_hash = generate_repo_hash(repo_url)
            cache_path = self.cache_dir / repo_hash
            
            if cache_path.exists() and cache_path.is_dir():
                try:
                    Repo(cache_path)
                    return cache_path
                except Exception:
                    shutil.rmtree(cache_path)
                    return None
            return None
        except Exception as e:
            logger.warning(f"Error checking cached repository: {e}")
            return None

    def _get_repo_content_hash(self, repo_path: Path) -> str:
        """Generate a hash of repository content for change detection"""
        try:
            content_hash = hashlib.md5()
            
            # Walk through all files and hash their content
            for file_path in self._walk_repository(repo_path):
                try:
                    with open(file_path, 'rb') as f:
                        content_hash.update(f.read())
                except Exception:
                    continue
            
            return content_hash.hexdigest()
        except Exception as e:
            logger.warning(f"Error generating content hash: {e}")
            return ""

    def _is_repo_content_changed(self, repo_path: Path, repo_url: str) -> bool:
        """Check if repository content has changed since last indexing"""
        try:
            # For local repos, check the source path; for remote repos, check the cache path
            if os.path.exists(repo_url) and os.path.isdir(repo_url):
                # Local repository - check source
                source_path = Path(repo_url)
            else:
                # Remote repository - check cache (since we can't check remote directly)
                source_path = repo_path
            
            current_hash = self._get_repo_content_hash(source_path)
            stored_hash = self._get_stored_repo_hash(repo_url)
            
            if not stored_hash:
                return True  # First time indexing
            
            return current_hash != stored_hash
        except Exception as e:
            logger.warning(f"Error checking repo content changes: {e}")
            return True  # Assume changed if we can't determine

    def _get_stored_repo_hash(self, repo_url: str) -> Optional[str]:
        """Get stored repository hash from metadata"""
        try:
            repo_hash = generate_repo_hash(repo_url)
            hash_file = self.cache_dir / f"{repo_hash}.hash"
            
            if hash_file.exists():
                with open(hash_file, 'r') as f:
                    return f.read().strip()
            return None
        except Exception as e:
            logger.warning(f"Error reading stored repo hash: {e}")
            return None

    def _store_repo_hash(self, repo_url: str, content_hash: str) -> None:
        """Store repository content hash for future comparison"""
        try:
            repo_hash = generate_repo_hash(repo_url)
            hash_file = self.cache_dir / f"{repo_hash}.hash"
            
            with open(hash_file, 'w') as f:
                f.write(content_hash)
        except Exception as e:
            logger.warning(f"Error storing repo hash: {e}")

    def _cache_repository(self, repo_path: Path, repo_url: str):
        """Cache a repository for future use"""
        try:
            repo_hash = generate_repo_hash(repo_url)
            cache_path = self.cache_dir / repo_hash
            
            if cache_path.exists():
                shutil.rmtree(cache_path)
            
            shutil.copytree(repo_path, cache_path)
            
            # Store content hash for change detection
            content_hash = self._get_repo_content_hash(repo_path)
            self._store_repo_hash(repo_url, content_hash)
            
            logger.info(f"Cached repository: {repo_url} -> {cache_path}")
        except Exception as e:
            logger.warning(f"Error caching repository: {e}")

    def _update_cached_repository(self, repo_url: str):
        """Update a cached repository by pulling latest changes"""
        try:
            cache_path = self._get_cached_repo_path(repo_url)
            if cache_path:
                repo = Repo(cache_path)
                repo.remotes.origin.pull()
                logger.info(f"Updated cached repository: {repo_url}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Error updating cached repository: {e}")
            return False
