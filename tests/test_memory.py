
import pytest
from unittest.mock import MagicMock, patch
from skills.memory_skill import MemorySkill
from qdrant_client.http import models

@pytest.fixture
def mock_qdrant():
    with patch('skills.memory_skill.QdrantClient') as mock:
        yield mock

@pytest.fixture
def mock_ollama():
    with patch('skills.memory_skill.ollama.Client') as mock:
        yield mock

def test_memory_add_success(mock_qdrant, mock_ollama):
    # Setup Mocks
    client_instance = mock_qdrant.return_value
    ollama_instance = mock_ollama.return_value
    ollama_instance.embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}

    # Execute
    mem = MemorySkill("test_agent")
    result = mem.add_memory("Test content")

    # Verify
    assert result is True
    # Ensure upsert was called
    client_instance.upsert.assert_called_once()
    # Correct collection name?
    args, _ = client_instance.upsert.call_args
    assert args[0] == "agent_memories" # collection_name

def test_memory_retrieval_v1_16_compat(mock_qdrant, mock_ollama):
    """Verify we are using query_points (newer API) instead of search."""
    client_instance = mock_qdrant.return_value
    ollama_instance = mock_ollama.return_value
    ollama_instance.embeddings.return_value = {"embedding": [0.1, 0.2, 0.3]}

    # Mock response for query_points
    mock_point = MagicMock()
    mock_point.payload = {"content": "Found memory"}
    mock_point.score = 0.95
    
    # query_points returns a generic object with a 'points' attribute list
    mock_response = MagicMock()
    mock_response.points = [mock_point]
    client_instance.query_points.return_value = mock_response

    # Execute
    mem = MemorySkill("test_agent")
    results = mem.get_memories("Query string")

    # Verify
    assert len(results) == 1
    assert results[0]['text'] == "Found memory"
    
    # CRITICAL: Verify query_points was called, NOT search
    client_instance.query_points.assert_called_once()
    assert not hasattr(client_instance, 'search') or not client_instance.search.called
