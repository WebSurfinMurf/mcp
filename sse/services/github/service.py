#!/usr/bin/env python3
"""
GitHub MCP SSE Service - GitHub API integration for repository and code operations
Implements MCP 2025-06-18 specification with output schemas and enhanced security
"""

import os
import sys
import asyncio
import base64
from datetime import datetime
from typing import List, Optional, Any, Dict

import httpx
from github import Github, GithubException
from github.Repository import Repository
from github.ContentFile import ContentFile

# Add core to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.mcp_sse import MCPSSEServer
from models import (
    SearchRepositoriesInput, GetRepositoryInfoInput, GetRepositoryContentsInput,
    GetFileContentInput, SearchCodeInput,
    SearchRepositoriesOutput, RepositoryInfoOutput, RepositoryContentsOutput,
    FileContentOutput, SearchCodeOutput,
    RepositoryInfo, RepositoryStats, LanguageStats, ContentItem, FileContent, CodeSearchResult,
    HealthOutput, ToolListOutput, ErrorOutput
)


class GitHubService:
    """GitHub API integration service"""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.github_client = None
        self.github_available = False
        self._initialize_github()
        
    def _initialize_github(self):
        """Initialize GitHub client if token is available"""
        if self.github_token:
            try:
                self.github_client = Github(self.github_token)
                # Test authentication
                user = self.github_client.get_user()
                user.login  # This will trigger an API call
                self.github_available = True
            except Exception as e:
                print(f"GitHub authentication failed: {e}")
                self.github_available = False
        else:
            print("GitHub token not configured")
            self.github_available = False

    def _convert_repository(self, repo) -> RepositoryInfo:
        """Convert GitHub repository object to our schema"""
        return RepositoryInfo(
            id=repo.id,
            name=repo.name,
            full_name=repo.full_name,
            owner=repo.owner.login,
            description=repo.description,
            private=repo.private,
            fork=repo.fork,
            archived=repo.archived,
            default_branch=repo.default_branch,
            language=repo.language,
            stars=repo.stargazers_count,
            forks=repo.forks_count,
            watchers=repo.watchers_count,
            open_issues=repo.open_issues_count,
            size=repo.size,
            created_at=repo.created_at.isoformat(),
            updated_at=repo.updated_at.isoformat(),
            pushed_at=repo.pushed_at.isoformat() if repo.pushed_at else repo.updated_at.isoformat(),
            clone_url=repo.clone_url,
            html_url=repo.html_url
        )

    def _get_repository_stats(self, repo: Repository) -> RepositoryStats:
        """Get additional repository statistics"""
        try:
            contributors = list(repo.get_contributors())
            releases = list(repo.get_releases())
            topics = repo.get_topics()
            license_info = repo.get_license()
            
            return RepositoryStats(
                contributors_count=len(contributors),
                releases_count=len(releases),
                topics=topics,
                license=license_info.license.name if license_info else None
            )
        except Exception as e:
            print(f"Error getting repository stats: {e}")
            return RepositoryStats(
                contributors_count=0,
                releases_count=0,
                topics=[],
                license=None
            )

    def _get_language_stats(self, repo: Repository) -> LanguageStats:
        """Get programming language statistics"""
        try:
            languages = repo.get_languages()
            primary_language = repo.language
            
            return LanguageStats(
                languages=languages,
                primary_language=primary_language
            )
        except Exception as e:
            print(f"Error getting language stats: {e}")
            return LanguageStats(
                languages={},
                primary_language=None
            )

    async def search_repositories(self, input_data: SearchRepositoriesInput) -> SearchRepositoriesOutput:
        """Search for GitHub repositories"""
        if not self.github_available:
            raise ValueError("GitHub API is not available. Please configure GITHUB_TOKEN.")
        
        try:
            # Build search query
            query = input_data.query
            if input_data.language:
                query += f" language:{input_data.language}"
            
            # Search repositories
            search_result = self.github_client.search_repositories(
                query=query,
                sort=input_data.sort,
                order=input_data.order
            )
            
            # Calculate pagination
            start_index = (input_data.page - 1) * input_data.per_page
            end_index = start_index + input_data.per_page
            
            # Get paginated results
            repositories = []
            for i, repo in enumerate(search_result):
                if i >= end_index:
                    break
                if i >= start_index:
                    repositories.append(self._convert_repository(repo))
            
            return SearchRepositoriesOutput(
                repositories=repositories,
                total_count=search_result.totalCount,
                incomplete_results=search_result.incomplete_results,
                page=input_data.page,
                per_page=input_data.per_page,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except GithubException as e:
            raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")
        except Exception as e:
            raise ValueError(f"Search error: {e}")

    async def get_repository_info(self, input_data: GetRepositoryInfoInput) -> RepositoryInfoOutput:
        """Get detailed information about a repository"""
        if not self.github_available:
            raise ValueError("GitHub API is not available. Please configure GITHUB_TOKEN.")
        
        try:
            repo = self.github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
            repository_info = self._convert_repository(repo)
            
            stats = None
            languages = None
            
            if input_data.include_stats:
                stats = self._get_repository_stats(repo)
            
            if input_data.include_languages:
                languages = self._get_language_stats(repo)
            
            return RepositoryInfoOutput(
                repository=repository_info,
                stats=stats,
                languages=languages,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"Repository '{input_data.owner}/{input_data.repo}' not found")
            raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")
        except Exception as e:
            raise ValueError(f"Repository info error: {e}")

    async def get_repository_contents(self, input_data: GetRepositoryContentsInput) -> RepositoryContentsOutput:
        """Get contents of a repository directory"""
        if not self.github_available:
            raise ValueError("GitHub API is not available. Please configure GITHUB_TOKEN.")
        
        try:
            repo = self.github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
            
            # Get contents
            contents = repo.get_contents(input_data.path, ref=input_data.ref)
            
            # Convert to our format
            content_items = []
            has_subdirectories = False
            
            # Handle both single file and directory contents
            if not isinstance(contents, list):
                contents = [contents]
            
            for item in contents:
                if item.type == "dir":
                    has_subdirectories = True
                
                content_items.append(ContentItem(
                    name=item.name,
                    path=item.path,
                    type=item.type,
                    size=item.size,
                    sha=item.sha,
                    url=item.url,
                    html_url=item.html_url,
                    download_url=item.download_url
                ))
            
            # Sort: directories first, then files
            content_items.sort(key=lambda x: (x.type != "dir", x.name.lower()))
            
            # Determine ref used
            actual_ref = input_data.ref or repo.default_branch
            
            return RepositoryContentsOutput(
                path=input_data.path,
                ref=actual_ref,
                contents=content_items,
                total_items=len(content_items),
                has_subdirectories=has_subdirectories,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"Path '{input_data.path}' not found in repository '{input_data.owner}/{input_data.repo}'")
            raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")
        except Exception as e:
            raise ValueError(f"Repository contents error: {e}")

    async def get_file_content(self, input_data: GetFileContentInput) -> FileContentOutput:
        """Get content of a specific file"""
        if not self.github_available:
            raise ValueError("GitHub API is not available. Please configure GITHUB_TOKEN.")
        
        try:
            repo = self.github_client.get_repo(f"{input_data.owner}/{input_data.repo}")
            
            # Get file content
            file_content = repo.get_contents(input_data.path, ref=input_data.ref)
            
            if isinstance(file_content, list):
                raise ValueError(f"Path '{input_data.path}' is a directory, not a file")
            
            if file_content.type != "file":
                raise ValueError(f"Path '{input_data.path}' is not a file")
            
            # Decode content
            content = ""
            encoding = file_content.encoding
            
            if encoding == "base64":
                try:
                    decoded_bytes = base64.b64decode(file_content.content)
                    content = decoded_bytes.decode('utf-8')
                    encoding = "utf-8"
                except UnicodeDecodeError:
                    # If UTF-8 decoding fails, return raw base64
                    content = file_content.content
                    encoding = "base64"
            else:
                content = file_content.content
            
            file_info = FileContent(
                name=file_content.name,
                path=file_content.path,
                content=content,
                encoding=encoding,
                size=file_content.size,
                sha=file_content.sha,
                url=file_content.url,
                html_url=file_content.html_url
            )
            
            # Determine ref used
            actual_ref = input_data.ref or repo.default_branch
            
            return FileContentOutput(
                file=file_info,
                repository=f"{input_data.owner}/{input_data.repo}",
                ref=actual_ref,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except GithubException as e:
            if e.status == 404:
                raise ValueError(f"File '{input_data.path}' not found in repository '{input_data.owner}/{input_data.repo}'")
            raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")
        except Exception as e:
            raise ValueError(f"File content error: {e}")

    async def search_code(self, input_data: SearchCodeInput) -> SearchCodeOutput:
        """Search for code in GitHub repositories"""
        if not self.github_available:
            raise ValueError("GitHub API is not available. Please configure GITHUB_TOKEN.")
        
        try:
            # Build search query
            query = input_data.query
            if input_data.language:
                query += f" language:{input_data.language}"
            if input_data.repo:
                query += f" repo:{input_data.repo}"
            
            # Search code
            search_result = self.github_client.search_code(query)
            
            # Calculate pagination
            start_index = (input_data.page - 1) * input_data.per_page
            end_index = start_index + input_data.per_page
            
            # Get paginated results
            results = []
            for i, code_result in enumerate(search_result):
                if i >= end_index:
                    break
                if i >= start_index:
                    # Extract text matches if available
                    text_matches = []
                    if hasattr(code_result, 'text_matches'):
                        text_matches = [
                            {
                                "object_url": match.get("object_url", ""),
                                "object_type": match.get("object_type", ""),
                                "property": match.get("property", ""),
                                "fragment": match.get("fragment", ""),
                                "matches": match.get("matches", [])
                            }
                            for match in code_result.text_matches or []
                        ]
                    
                    results.append(CodeSearchResult(
                        name=code_result.name,
                        path=code_result.path,
                        repository=code_result.repository.full_name,
                        sha=code_result.sha,
                        url=code_result.url,
                        html_url=code_result.html_url,
                        score=code_result.score,
                        text_matches=text_matches
                    ))
            
            return SearchCodeOutput(
                results=results,
                total_count=search_result.totalCount,
                incomplete_results=search_result.incomplete_results,
                page=input_data.page,
                per_page=input_data.per_page,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except GithubException as e:
            raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")
        except Exception as e:
            raise ValueError(f"Code search error: {e}")

    async def test_github_api(self) -> bool:
        """Test if GitHub API is available"""
        if not self.github_available:
            return False
        
        try:
            user = self.github_client.get_user()
            user.login  # Trigger API call
            return True
        except:
            return False


async def create_mcp_server() -> MCPSSEServer:
    """Create and configure the GitHub MCP SSE server"""
    
    # Initialize service
    github_service = GitHubService()
    
    # Create server with service info
    server = MCPSSEServer(
        name="github",
        version="1.0.0",
        port=int(os.getenv('SERVICE_PORT', 8004))
    )
    
    # Register tools with input/output schemas
    server.register_tool(
        name="search_repositories",
        handler=github_service.search_repositories,
        input_schema=SearchRepositoriesInput,
        output_schema=SearchRepositoriesOutput,
        description="Search for GitHub repositories with filters and pagination"
    )
    
    server.register_tool(
        name="get_repository_info",
        handler=github_service.get_repository_info,
        input_schema=GetRepositoryInfoInput,
        output_schema=RepositoryInfoOutput,
        description="Get detailed information about a specific repository"
    )
    
    server.register_tool(
        name="get_repository_contents",
        handler=github_service.get_repository_contents,
        input_schema=GetRepositoryContentsInput,
        output_schema=RepositoryContentsOutput,
        description="Get contents of a repository directory or file listing"
    )
    
    server.register_tool(
        name="get_file_content",
        handler=github_service.get_file_content,
        input_schema=GetFileContentInput,
        output_schema=FileContentOutput,
        description="Get content of a specific file from a repository"
    )
    
    server.register_tool(
        name="search_code",
        handler=github_service.search_code,
        input_schema=SearchCodeInput,
        output_schema=SearchCodeOutput,
        description="Search for code snippets in GitHub repositories"
    )
    
    return server


async def main():
    """Main entry point"""
    try:
        server = await create_mcp_server()
        await server.run_async()
    except Exception as e:
        print(f"Failed to start GitHub service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())