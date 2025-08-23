"""Graphviz rendering helpers with safe file operations."""

from pathlib import Path

from .diagram import Diagram


def render_to_file(
    diagram: Diagram,
    filepath: str,
    format: str = "png",
    engine: str = "dot",
    cleanup: bool = True
) -> bool:
    """Render a diagram to file using Graphviz.

    Safely handles missing Graphviz installation with friendly error messages.

    Args:
        diagram: The diagram to render
        filepath: Output file path
        format: Output format (png, svg, pdf, etc.)
        engine: Graphviz layout engine (dot, neato, circo, etc.)
        cleanup: Whether to clean up intermediate .dot files

    Returns:
        True if successful, False if Graphviz not available

    Raises:
        ValueError: For invalid inputs
        RuntimeError: For rendering errors when Graphviz is available
    """
    try:
        import graphviz
    except ImportError:
        print("🚫 Graphviz not available")
        print("💡 To enable Graphviz rendering:")
        print("   pip install graphviz")
        print("   # Also install system Graphviz: brew install graphviz (macOS) or apt-get install graphviz (Ubuntu)")
        return False

    if not filepath:
        raise ValueError("filepath cannot be empty")

    # Validate format
    valid_formats = ["png", "svg", "pdf", "ps", "dot", "json"]
    if format not in valid_formats:
        print(f"⚠️  Unknown format '{format}', using 'png'")
        format = "png"

    # Create output directory if needed
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Generate DOT source
        dot_source = diagram.to_dot()

        # Create Graphviz object
        graph = graphviz.Source(dot_source, engine=engine, format=format)

        # Render to file
        output_file = graph.render(
            filename=str(output_path.with_suffix("")),
            cleanup=cleanup,
            format=format
        )

        print(f"✅ Rendered diagram to {output_file}")
        return True

    except Exception as e:
        print(f"❌ Error rendering diagram: {e}")
        print("💡 Check that system Graphviz is properly installed")
        raise RuntimeError(f"Graphviz rendering failed: {e}") from e


def render_dot_string(
    dot_string: str,
    filepath: str,
    format: str = "png",
    engine: str = "dot",
    cleanup: bool = True
) -> bool:
    """Render a DOT string to file.

    Args:
        dot_string: DOT format graph description
        filepath: Output file path
        format: Output format
        engine: Graphviz layout engine
        cleanup: Whether to clean up intermediate files

    Returns:
        True if successful, False if Graphviz not available
    """
    try:
        import graphviz
    except ImportError:
        print("🚫 Graphviz not available - install with: pip install graphviz")
        return False

    try:
        graph = graphviz.Source(dot_string, engine=engine, format=format)
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_file = graph.render(
            filename=str(output_path.with_suffix("")),
            cleanup=cleanup,
            format=format
        )

        print(f"✅ Rendered DOT to {output_file}")
        return True

    except Exception as e:
        print(f"❌ Error rendering DOT: {e}")
        return False


def check_graphviz_available() -> dict:
    """Check if Graphviz is available and return status information.

    Returns:
        Dictionary with availability status and installation instructions
    """
    status = {
        "python_package": False,
        "system_executable": False,
        "engines": [],
        "formats": [],
        "instructions": []
    }

    # Check Python package
    try:
        import graphviz
        status["python_package"] = True

        # Try to get available engines and formats
        try:
            # This will fail if system Graphviz is not installed
            dummy = graphviz.Digraph()
            dummy.render(format='png', engine='dot', filename='/tmp/test', cleanup=True)
            status["system_executable"] = True

            # Common engines and formats (Graphviz dependent)
            status["engines"] = ["dot", "neato", "fdp", "sfdp", "circo", "twopi"]
            status["formats"] = ["png", "svg", "pdf", "ps", "eps", "dot", "json"]

        except Exception:
            status["system_executable"] = False

    except ImportError:
        status["python_package"] = False

    # Generate installation instructions
    if not status["python_package"]:
        status["instructions"].append("Install Python package: pip install graphviz")

    if not status["system_executable"]:
        status["instructions"].extend([
            "Install system Graphviz:",
            "  macOS: brew install graphviz",
            "  Ubuntu/Debian: sudo apt-get install graphviz",
            "  Windows: Download from https://graphviz.org/download/",
            "  Or use conda: conda install graphviz"
        ])

    return status


def safe_render_example():
    """Example of safe rendering with error handling."""
    from .standard import simplex

    # Create example diagram
    simplex(2)
    diagram = Diagram.from_edges(
        ["0", "1", "2"],
        [("0", "1", "0->1"), ("1", "2", "1->2"), ("0", "2", "0->2")]
    )

    print("🎨 LambdaCat Graphviz Rendering Example")
    print("=" * 40)

    # Check availability
    status = check_graphviz_available()
    print(f"Python package available: {status['python_package']}")
    print(f"System executable available: {status['system_executable']}")

    if not (status["python_package"] and status["system_executable"]):
        print("\n❌ Graphviz not fully available")
        for instruction in status["instructions"]:
            print(f"   {instruction}")
        return False

    # Try to render
    print(f"\nAvailable engines: {', '.join(status['engines'])}")
    print(f"Available formats: {', '.join(status['formats'])}")

    # Render with different formats
    base_path = "/tmp/lambdacat_example"
    formats = ["png", "svg", "pdf"]

    for fmt in formats:
        success = render_to_file(diagram, f"{base_path}.{fmt}", format=fmt)
        if success:
            print(f"✅ {fmt.upper()} render successful")
        else:
            print(f"❌ {fmt.upper()} render failed")

    return True
