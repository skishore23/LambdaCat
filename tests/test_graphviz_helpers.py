"""Tests for Graphviz helpers."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from LambdaCat.core import Diagram, check_graphviz_available, render_dot_string, render_to_file


def test_check_graphviz_available_no_package():
    """Test Graphviz availability check when package not installed."""
    # Remove graphviz from sys.modules to simulate import error
    with patch.dict('sys.modules', {'graphviz': None}):
        # Mock the import to raise ImportError
        original_import = __builtins__['__import__']

        def mock_import(name, *args, **kwargs):
            if name == 'graphviz':
                raise ImportError("No module named 'graphviz'")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            status = check_graphviz_available()

            assert not status["python_package"]
            assert not status["system_executable"]
            assert "Install Python package" in " ".join(status["instructions"])


def test_check_graphviz_available_package_only():
    """Test when Python package is available but system executable is not."""
    mock_graphviz = MagicMock()
    mock_digraph = MagicMock()
    mock_digraph.render.side_effect = Exception("System Graphviz not found")
    mock_graphviz.Digraph.return_value = mock_digraph

    with patch.dict('sys.modules', {'graphviz': mock_graphviz}):
        status = check_graphviz_available()

        assert status["python_package"]
        assert not status["system_executable"]
        assert "Install system Graphviz" in " ".join(status["instructions"])


def test_render_to_file_no_graphviz(capsys):
    """Test render_to_file when Graphviz is not available."""
    diagram = Diagram.from_edges(["A", "B"], [("A", "B", "f")])

    with patch.dict('sys.modules', {'graphviz': None}):
        def mock_import(name, *args, **kwargs):
            if name == 'graphviz':
                raise ImportError("No module named 'graphviz'")
            return __builtins__['__import__'](name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            result = render_to_file(diagram, "test.png")

            assert not result
            captured = capsys.readouterr()
            assert "Graphviz not available" in captured.out


def test_render_to_file_invalid_inputs():
    """Test render_to_file with invalid inputs."""
    diagram = Diagram.from_edges(["A", "B"], [("A", "B", "f")])

    # Mock graphviz to be available so we can test input validation
    mock_graphviz = MagicMock()

    with patch.dict('sys.modules', {'graphviz': mock_graphviz}):
        with pytest.raises(ValueError, match="filepath cannot be empty"):
            render_to_file(diagram, "")


def test_render_to_file_unknown_format(capsys):
    """Test render_to_file with unknown format."""
    diagram = Diagram.from_edges(["A", "B"], [("A", "B", "f")])

    # Mock graphviz to be available
    mock_graphviz = MagicMock()
    mock_source = MagicMock()
    mock_source.render.return_value = "output.png"
    mock_graphviz.Source.return_value = mock_source

    with patch.dict('sys.modules', {'graphviz': mock_graphviz}):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.xyz"
            render_to_file(diagram, str(filepath), format="unknown")

            captured = capsys.readouterr()
            assert "Unknown format 'unknown', using 'png'" in captured.out


def test_render_to_file_success():
    """Test successful render_to_file operation."""
    diagram = Diagram.from_edges(["A", "B"], [("A", "B", "f")])

    # Mock graphviz
    mock_graphviz = MagicMock()
    mock_source = MagicMock()
    mock_source.render.return_value = "output.png"
    mock_graphviz.Source.return_value = mock_source

    with patch.dict('sys.modules', {'graphviz': mock_graphviz}):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.png"
            result = render_to_file(diagram, str(filepath))

            assert result
            # Verify the Source was created with DOT content
            mock_graphviz.Source.assert_called_once()
            # Verify render was called
            mock_source.render.assert_called_once()


def test_render_to_file_graphviz_error():
    """Test render_to_file when Graphviz throws an error."""
    diagram = Diagram.from_edges(["A", "B"], [("A", "B", "f")])

    # Mock graphviz to throw an error
    mock_graphviz = MagicMock()
    mock_source = MagicMock()
    mock_source.render.side_effect = Exception("Graphviz render error")
    mock_graphviz.Source.return_value = mock_source

    with patch.dict('sys.modules', {'graphviz': mock_graphviz}):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.png"

            with pytest.raises(RuntimeError, match="Graphviz rendering failed"):
                render_to_file(diagram, str(filepath))


def test_render_dot_string_no_graphviz(capsys):
    """Test render_dot_string when Graphviz is not available."""
    dot_string = 'digraph G { A -> B; }'

    with patch.dict('sys.modules', {'graphviz': None}):
        def mock_import(name, *args, **kwargs):
            if name == 'graphviz':
                raise ImportError("No module named 'graphviz'")
            return __builtins__['__import__'](name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            result = render_dot_string(dot_string, "test.png")

            assert not result
            captured = capsys.readouterr()
            assert "Graphviz not available" in captured.out


def test_render_dot_string_success():
    """Test successful render_dot_string operation."""
    dot_string = 'digraph G { A -> B; }'

    # Mock graphviz
    mock_graphviz = MagicMock()
    mock_source = MagicMock()
    mock_source.render.return_value = "output.png"
    mock_graphviz.Source.return_value = mock_source

    with patch.dict('sys.modules', {'graphviz': mock_graphviz}):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.png"
            result = render_dot_string(dot_string, str(filepath))

            assert result
            mock_graphviz.Source.assert_called_once_with(
                dot_string, engine="dot", format="png"
            )


def test_render_dot_string_error(capsys):
    """Test render_dot_string when Graphviz throws an error."""
    dot_string = 'digraph G { A -> B; }'

    # Mock graphviz to throw an error
    mock_graphviz = MagicMock()
    mock_source = MagicMock()
    mock_source.render.side_effect = Exception("Render error")
    mock_graphviz.Source.return_value = mock_source

    with patch.dict('sys.modules', {'graphviz': mock_graphviz}):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "test.png"
            result = render_dot_string(dot_string, str(filepath))

            assert not result
            captured = capsys.readouterr()
            assert "Error rendering DOT" in captured.out


def test_directory_creation():
    """Test that output directories are created automatically."""
    diagram = Diagram.from_edges(["A", "B"], [("A", "B", "f")])

    # Mock graphviz
    mock_graphviz = MagicMock()
    mock_source = MagicMock()
    mock_source.render.return_value = "output.png"
    mock_graphviz.Source.return_value = mock_source

    with patch.dict('sys.modules', {'graphviz': mock_graphviz}):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a nested path that doesn't exist
            filepath = Path(tmpdir) / "subdir" / "another" / "test.png"
            result = render_to_file(diagram, str(filepath))

            assert result
            # Directory should have been created
            assert filepath.parent.exists()
