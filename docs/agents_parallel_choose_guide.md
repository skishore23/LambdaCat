# Parallel and Choose Operations

LambdaCat's agent framework supports non-linear execution patterns through two key operations:

**Parallel**: Run multiple plans with the same input and combine their results
**Choose**: Run multiple plans and pick one result based on your criteria

## Parallel Execution

Run multiple operations on the same input and combine their outputs.

```python
from LambdaCat.agents.actions import Task, parallel
from LambdaCat.agents.runtime import compile_plan

# Text analysis pipeline
plan = parallel(
    Task("summarize"),
    Task("extract_keywords"), 
    Task("sentiment_analysis")
)

# Combine results into a structured format
executable = compile_plan(
    actions,
    plan,
    aggregate_fn=lambda results: {
        "summary": results[0], 
        "keywords": results[1], 
        "sentiment": results[2]
    }
)
```

### Aggregation Strategies

Choose how to combine parallel results:

```python
# Join text outputs
concat_results = lambda results: " | ".join(str(r) for r in results)

# Create labeled dictionary
def labeled_dict(labels):
    return lambda results: dict(zip(labels, results))

# Take average of numbers
average = lambda results: sum(results) / len(results) if results else 0

# Use with plan
executable = compile_plan(actions, plan, aggregate_fn=average)
```

### Example: Text Analysis

```python
from LambdaCat.agents.actions import Task, sequence, parallel
from LambdaCat.agents.runtime import compile_plan

# Text processing actions
actions = {
    "clean_text": lambda x: x.strip().lower(),
    "word_count": lambda x: len(x.split()),
    "char_count": lambda x: len(x),
    "unique_words": lambda x: len(set(x.split()))
}

# Clean text, then run multiple analyses in parallel
plan = sequence(
    Task("clean_text"),
    parallel(
        Task("word_count"),
        Task("char_count"), 
        Task("unique_words")
    )
)

# Format results nicely
executable = compile_plan(
    actions,
    plan,
    aggregate_fn=lambda r: f"Words: {r[0]}, Chars: {r[1]}, Unique: {r[2]}"
)

result = executable("  Hello World! Hello Universe!  ")
# "Words: 4, Chars: 26, Unique: 3"
```

### Example: Writer Monad Aggregation

When using monadic contexts, parallel operations can aggregate Writer logs:

```python
from LambdaCat.core.fp.instances.writer import Writer
from LambdaCat.agents.runtime import compile_to_kleisli

# Actions that produce Writer values
def logged_increment(x):
    return Writer((x + 1, [f"Incremented {x} to {x + 1}"]))

def logged_double(x):
    return Writer((x * 2, [f"Doubled {x} to {x * 2}"]))

implementation = {
    "increment": logged_increment,
    "double": logged_double
}

# Parallel plan
plan = parallel(Task("increment"), Task("double"))

# In Kleisli context, Writer instances are combined automatically
kleisli_arrow = compile_to_kleisli(implementation, plan, Writer)
result = kleisli_arrow(5)
# Result: Writer((6, 10), ["Incremented 5 to 6", "Doubled 5 to 10"])
```

## Choose Operation

The `choose` operation executes multiple plans and selects one result based on a choice function.

### Basic Usage

```python
from LambdaCat.agents.actions import Task, choose
from LambdaCat.agents.runtime import compile_plan

# Define a choice plan
plan = choose(
    Task("aggressive_summary"),
    Task("conservative_summary"),
    Task("balanced_summary")
)

# Compile with a choice function
executable = compile_plan(
    implementation,
    plan,
    choose_fn=lambda results: 2  # Always choose the third option (index 2)
)
```

### Choice Functions

The `choose_fn` parameter determines which result is selected:

```python
from LambdaCat.agents.runtime import first, argmax

# Always choose first result
def choose_first():
    return lambda results: 0

# Choose based on length
def choose_shortest():
    return lambda results: min(range(len(results)), key=lambda i: len(str(results[i])))

# Choose based on custom scoring
def choose_by_score(score_fn):
    return lambda results: max(range(len(results)), key=lambda i: score_fn(results[i]))

# Built-in helpers
first_choice = first()  # Always returns 0
best_by_length = argmax(lambda x: len(str(x)))
```

### Example: Strategy Selection

```python
from LambdaCat.agents.actions import Task, sequence, choose

# Different processing strategies
implementation = {
    "strip": lambda x: x.strip(),
    "aggressive_clean": lambda x: ''.join(c for c in x if c.isalnum()),
    "moderate_clean": lambda x: ''.join(c for c in x if c.isalnum() or c.isspace()),
    "preserve_punctuation": lambda x: x.strip()
}

# Plan with strategy choice
plan = sequence(
    Task("strip"),
    choose(
        Task("aggressive_clean"),
        Task("moderate_clean"),
        Task("preserve_punctuation")
    )
)

# Choose based on desired output characteristics
def choose_by_alphanumeric_ratio(results):
    def score(text):
        if not text:
            return 0
        alphanumeric = sum(1 for c in text if c.isalnum())
        return alphanumeric / len(text)
    
    scores = [score(r) for r in results]
    # Choose moderate if ratio is between 0.7 and 0.9
    if 0.7 <= scores[1] <= 0.9:
        return 1
    # Otherwise choose the one closest to 0.8
    return min(range(len(scores)), key=lambda i: abs(scores[i] - 0.8))

executable = compile_plan(implementation, plan, choose_fn=choose_by_alphanumeric_ratio)
```

### Example: Result vs Option Monad Behavior

Different monads handle choose operations differently:

```python
from LambdaCat.core.fp.instances.result import Result
from LambdaCat.core.fp.instances.option import Option

# Result monad - short-circuits on error
def safe_divide(x):
    return Result.ok(10 / x) if x != 0 else Result.err("Division by zero")

def safe_sqrt(x):
    import math
    return Result.ok(math.sqrt(x)) if x >= 0 else Result.err("Negative number")

result_implementation = {
    "divide": safe_divide,
    "sqrt": safe_sqrt
}

# With Result monad, choose will short-circuit on first error
plan = choose(Task("divide"), Task("sqrt"))

# Option monad - continues through None values
def maybe_parse_int(x):
    try:
        return Option.some(int(x))
    except:
        return Option.none()

option_implementation = {
    "parse": maybe_parse_int
}
```

## Complex Example: Multi-Stage Processing

Here's a complete example combining parallel and choose operations:

```python
from LambdaCat.agents.actions import Task, sequence, parallel, choose
from LambdaCat.agents.runtime import compile_plan

# Complex text processing implementation
implementation = {
    # Cleaning operations
    "strip": lambda x: x.strip(),
    "lowercase": lambda x: x.lower(),
    "remove_punctuation": lambda x: ''.join(c for c in x if c.isalnum() or c.isspace()),
    
    # Analysis operations
    "word_count": lambda x: f"{len(x.split())} words",
    "char_count": lambda x: f"{len(x)} chars",
    "avg_word_length": lambda x: f"{sum(len(w) for w in x.split()) / len(x.split()):.1f} avg",
    
    # Formatting operations
    "title_case": lambda x: x.title(),
    "sentence_case": lambda x: x[0].upper() + x[1:] if x else x,
    "preserve_case": lambda x: x
}

# Multi-stage plan
plan = sequence(
    # Stage 1: Clean the input
    Task("strip"),
    Task("lowercase"),
    Task("remove_punctuation"),
    
    # Stage 2: Parallel analysis
    parallel(
        Task("word_count"),
        Task("char_count"),
        Task("avg_word_length")
    ),
    
    # Stage 3: Choose formatting
    choose(
        Task("title_case"),
        Task("sentence_case"),
        Task("preserve_case")
    )
)

# Aggregate analysis results into readable format
def format_analysis(results):
    return f"[{', '.join(results)}]"

# Choose formatting based on content
def choose_format(results):
    # If it looks like a title (short), use title case
    if len(results[0]) < 50:
        return 0
    # If it looks like a sentence, use sentence case
    elif '.' in results[1]:
        return 1
    # Otherwise preserve
    else:
        return 2

# Compile the plan
executable = compile_plan(
    implementation,
    plan,
    aggregate_fn=format_analysis,
    choose_fn=choose_format
)

# Execute
text = "  Hello, World! This is a TEST.  "
result = executable(text)
print(result)  # Output will be analysis results in chosen format
```

## Best Practices

1. **Aggregation Functions**: Always provide an `aggregate_fn` when using `parallel`. Without it, the operation will fail.

2. **Choice Functions**: The `choose_fn` should return an index (0-based) into the results list, not the result itself.

3. **Error Handling**: When using monadic contexts (Result, Option), understand how each monad handles parallel/choose operations:
   - Result: Short-circuits on first error
   - Option: Continues through None values
   - Writer: Aggregates all logs

4. **Performance**: Parallel operations in the current implementation execute sequentially. True parallelism would require async/threading support.

5. **Debugging**: Use descriptive task names and consider adding logging in your action implementations to trace execution flow.

## See Also

- [Agent Framework Overview](./agents_overview.md)
- [Kleisli Compilation Guide](./kleisli_guide.md)
- [Examples: agents_demo.py](../examples/agents_demo.py)