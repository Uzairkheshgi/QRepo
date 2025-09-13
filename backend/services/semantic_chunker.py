"""
Semantic chunking service using tree-sitter for language-aware parsing
"""

import os
import logging
from typing import List, Dict, Any
from tree_sitter import Language, Parser

import constants
from utils import is_function_start, is_class_start

logger = logging.getLogger(__name__)


class SemanticChunker:
    def __init__(self):
        self.parsers = {}
        self.language_configs = constants.TREE_SITTER_LANGUAGE_CONFIGS

        # Initialize parsers for supported languages
        self._initialize_parsers()

    def _initialize_parsers(self):
        """Initialize tree-sitter parsers for supported languages"""
        try:
            for lang_name, config in self.language_configs.items():
                try:
                    # Load the language grammar directly from the module
                    import importlib
                    grammar_module = importlib.import_module(config["grammar_path"])
                    
                    # Get the language function name (default to 'language')
                    language_func_name = config.get("language_function", "language")
                    
                    if hasattr(grammar_module, language_func_name):
                        language_capsule = getattr(grammar_module, language_func_name)()
                        language = Language(language_capsule)
                        parser = Parser()
                        parser.language = language
                        self.parsers[lang_name] = parser
                        logger.info("Successfully initialized parser for %s", lang_name)
                    else:
                        logger.warning("Grammar module %s does not have %s() function", config["grammar_path"], language_func_name)
                        self.parsers[lang_name] = None
                        
                except ImportError:
                    # Tree-sitter grammar not installed - use fallback chunking
                    logger.warning("Tree-sitter grammar for %s not installed, using fallback chunking", lang_name)
                    self.parsers[lang_name] = None
                except Exception as e:
                    logger.warning("Failed to initialize parser for %s: %s", lang_name, e)
                    # Fallback to basic chunking
                    self.parsers[lang_name] = None
        except Exception as e:
            logger.error("Failed to initialize tree-sitter parsers: %s", e)


    def create_semantic_chunks(
        self, content: str, file_type: str, file_path: str = ""
    ) -> List[Dict[str, Any]]:
        """Create semantic chunks from file content"""
        try:
            if file_type in self.parsers and self.parsers[file_type] is not None:
                return self._create_tree_sitter_chunks(content, file_type, file_path)
            else:
                return self._create_fallback_chunks(content, file_type, file_path)
        except Exception as e:
            logger.warning(f"Error in semantic chunking for {file_type}: {e}")
            return self._create_fallback_chunks(content, file_type, file_path)

    def _create_tree_sitter_chunks(
        self, content: str, file_type: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """Create chunks using tree-sitter parsing"""
        parser = self.parsers[file_type]
        config = self.language_configs[file_type]

        try:
            tree = parser.parse(bytes(content, "utf8"))
            chunks = []

            # Extract semantic units
            for node in self._extract_semantic_nodes(
                tree.root_node, config["chunk_types"]
            ):
                chunk_content = self._extract_node_content(content, node)
                if chunk_content.strip():
                    chunks.append(
                        {
                            "content": chunk_content,
                            "type": node.type,
                            "start_line": node.start_point[0] + 1,
                            "end_line": node.end_point[0] + 1,
                            "file_path": file_path,
                            "file_type": file_type,
                            "semantic_type": self._get_semantic_type(node.type),
                        }
                    )

            # If no semantic chunks found, fall back to basic chunking
            if not chunks:
                return self._create_fallback_chunks(content, file_type, file_path)

            return chunks

        except Exception as e:
            logger.warning(f"Tree-sitter parsing failed for {file_type}: {e}")
            return self._create_fallback_chunks(content, file_type, file_path)

    def _extract_semantic_nodes(self, node, target_types: List[str]) -> List:
        """Extract nodes of target types from the AST"""
        nodes = []

        if node.type in target_types:
            nodes.append(node)

        for child in node.children:
            nodes.extend(self._extract_semantic_nodes(child, target_types))

        return nodes

    def _extract_node_content(self, content: str, node) -> str:
        """Extract the text content of a node"""
        lines = content.split("\n")
        start_line, start_col = node.start_point
        end_line, end_col = node.end_point

        if start_line == end_line:
            return lines[start_line][start_col:end_col]
        else:
            result = []
            result.append(lines[start_line][start_col:])
            for i in range(start_line + 1, end_line):
                result.append(lines[i])
            result.append(lines[end_line][:end_col])
            return "\n".join(result)

    def _get_semantic_type(self, node_type: str) -> str:
        """Map node types to semantic types"""
        return constants.SEMANTIC_TYPE_MAPPING.get(node_type, "other")

    def _create_fallback_chunks(
        self, content: str, file_type: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """Create fallback chunks when tree-sitter is not available"""
        chunks = []
        lines = content.split("\n")

        # Simple chunking based on file type
        if file_type in ["python", "javascript", "typescript", "java", "cpp", "c"]:
            # Look for function/class patterns
            current_chunk = []
            current_type = "other"
            start_line = 0

            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # Detect function/class starts
                if is_function_start(line_stripped, file_type):
                    if current_chunk:
                        chunks.append(
                            {
                                "content": "\n".join(current_chunk),
                                "type": current_type,
                                "start_line": start_line + 1,
                                "end_line": i,
                                "file_path": file_path,
                                "file_type": file_type,
                                "semantic_type": current_type,
                            }
                        )
                    current_chunk = [line]
                    current_type = "function"
                    start_line = i
                elif is_class_start(line_stripped, file_type):
                    if current_chunk:
                        chunks.append(
                            {
                                "content": "\n".join(current_chunk),
                                "type": current_type,
                                "start_line": start_line + 1,
                                "end_line": i,
                                "file_path": file_path,
                                "file_type": file_type,
                                "semantic_type": current_type,
                            }
                        )
                    current_chunk = [line]
                    current_type = "class"
                    start_line = i
                else:
                    current_chunk.append(line)

            # Add the last chunk
            if current_chunk:
                chunks.append(
                    {
                        "content": "\n".join(current_chunk),
                        "type": current_type,
                        "start_line": start_line + 1,
                        "end_line": len(lines),
                        "file_path": file_path,
                        "file_type": file_type,
                        "semantic_type": current_type,
                    }
                )
        else:
            # For non-code files, use paragraph-based chunking
            paragraphs = content.split("\n\n")
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():
                    chunks.append(
                        {
                            "content": paragraph.strip(),
                            "type": "paragraph",
                            "start_line": i + 1,
                            "end_line": i + 1,
                            "file_path": file_path,
                            "file_type": file_type,
                            "semantic_type": "text",
                        }
                    )

        return chunks

