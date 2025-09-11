"""
GitHub Service Models - Pydantic schemas with MCP 2025-06-18 output schemas
"""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


# Input Models
class SearchRepositoriesInput(BaseModel):
    """Input schema for searching GitHub repositories"""
    query: str = Field(..., description="Search query for repositories")
    language: Optional[str] = Field(None, description="Filter by programming language")
    sort: str = Field("stars", description="Sort repositories by: stars, forks, updated")
    order: str = Field("desc", description="Sort order: asc, desc")
    per_page: int = Field(10, description="Number of results per page", ge=1, le=100)
    page: int = Field(1, description="Page number for pagination", ge=1)


class GetRepositoryInfoInput(BaseModel):
    """Input schema for getting repository information"""
    owner: str = Field(..., description="Repository owner/organization name")
    repo: str = Field(..., description="Repository name")
    include_stats: bool = Field(True, description="Include repository statistics")
    include_languages: bool = Field(True, description="Include programming languages")


class GetRepositoryContentsInput(BaseModel):
    """Input schema for getting repository contents"""
    owner: str = Field(..., description="Repository owner/organization name")
    repo: str = Field(..., description="Repository name")
    path: str = Field("", description="File or directory path (empty for root)")
    ref: Optional[str] = Field(None, description="Branch, tag, or commit SHA")


class GetFileContentInput(BaseModel):
    """Input schema for getting file content"""
    owner: str = Field(..., description="Repository owner/organization name")
    repo: str = Field(..., description="Repository name")
    path: str = Field(..., description="File path")
    ref: Optional[str] = Field(None, description="Branch, tag, or commit SHA")


class SearchCodeInput(BaseModel):
    """Input schema for searching code in GitHub"""
    query: str = Field(..., description="Code search query")
    language: Optional[str] = Field(None, description="Filter by programming language")
    repo: Optional[str] = Field(None, description="Search within specific repository (owner/repo)")
    per_page: int = Field(10, description="Number of results per page", ge=1, le=100)
    page: int = Field(1, description="Page number for pagination", ge=1)


# Output Models (MCP 2025-06-18)
class RepositoryInfo(BaseModel):
    """Repository information structure"""
    id: int
    name: str
    full_name: str
    owner: str
    description: Optional[str] = None
    private: bool
    fork: bool
    archived: bool
    default_branch: str
    language: Optional[str] = None
    stars: int
    forks: int
    watchers: int
    open_issues: int
    size: int  # in KB
    created_at: str
    updated_at: str
    pushed_at: str
    clone_url: str
    html_url: str


class RepositoryStats(BaseModel):
    """Repository statistics structure"""
    contributors_count: int
    commits_count: Optional[int] = None
    releases_count: int
    topics: List[str]
    license: Optional[str] = None


class LanguageStats(BaseModel):
    """Programming language statistics"""
    languages: Dict[str, int]  # language -> bytes
    primary_language: Optional[str] = None


class ContentItem(BaseModel):
    """Repository content item structure"""
    name: str
    path: str
    type: str  # "file" or "dir"
    size: Optional[int] = None
    sha: str
    url: str
    html_url: str
    download_url: Optional[str] = None


class FileContent(BaseModel):
    """File content structure"""
    name: str
    path: str
    content: str
    encoding: str
    size: int
    sha: str
    url: str
    html_url: str


class CodeSearchResult(BaseModel):
    """Code search result structure"""
    name: str
    path: str
    repository: str
    sha: str
    url: str
    html_url: str
    score: float
    text_matches: List[Dict[str, Any]]


class SearchRepositoriesOutput(BaseModel):
    """Output schema for repository search"""
    repositories: List[RepositoryInfo]
    total_count: int
    incomplete_results: bool
    page: int
    per_page: int
    timestamp: str


class RepositoryInfoOutput(BaseModel):
    """Output schema for repository information"""
    repository: RepositoryInfo
    stats: Optional[RepositoryStats] = None
    languages: Optional[LanguageStats] = None
    timestamp: str


class RepositoryContentsOutput(BaseModel):
    """Output schema for repository contents"""
    path: str
    ref: str
    contents: List[ContentItem]
    total_items: int
    has_subdirectories: bool
    timestamp: str


class FileContentOutput(BaseModel):
    """Output schema for file content"""
    file: FileContent
    repository: str
    ref: str
    timestamp: str


class SearchCodeOutput(BaseModel):
    """Output schema for code search"""
    results: List[CodeSearchResult]
    total_count: int
    incomplete_results: bool
    page: int
    per_page: int
    timestamp: str


class HealthOutput(BaseModel):
    """Health check output schema"""
    status: str
    service: str
    version: str
    uptime: float
    tools_count: int
    github_api_available: bool
    github_token_configured: bool
    timestamp: str


class ToolListOutput(BaseModel):
    """Tool listing output schema"""
    tools: List[Dict[str, Any]]
    service: str
    version: str


class ErrorOutput(BaseModel):
    """Error response schema"""
    error: str
    details: Optional[str] = None
    error_code: Optional[str] = None