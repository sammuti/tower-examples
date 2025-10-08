import os
import json
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

# TODO: Replace with `import tower` once the CLI PR is merged
from _llms import llms


def get_database_connection():
    """
    Get a connection to the PostgreSQL database using POSTGRES_URI from environment.

    Returns:
        psycopg2.connection: Database connection object
    """
    postgres_uri = os.getenv("POSTGRES_URI")
    if not postgres_uri:
        raise ValueError("POSTGRES_URI environment variable is not set")

    return psycopg2.connect(postgres_uri)


def is_read_only_query(query: str) -> bool:
    """
    Check if a SQL query is read-only (SELECT only).

    Args:
        query (str): SQL query to check

    Returns:
        bool: True if query is read-only, False otherwise
    """
    # Remove leading/trailing whitespace and convert to uppercase
    query_upper = query.strip().upper()

    # Remove comments
    lines = []
    for line in query_upper.split('\n'):
        # Remove single-line comments
        if '--' in line:
            line = line[:line.index('--')]
        lines.append(line)
    query_upper = ' '.join(lines)

    # Remove multi-line comments
    while '/*' in query_upper and '*/' in query_upper:
        start = query_upper.index('/*')
        end = query_upper.index('*/', start) + 2
        query_upper = query_upper[:start] + ' ' + query_upper[end:]

    # Check for dangerous keywords
    dangerous_keywords = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE',
        'EXECUTE', 'EXEC', 'CALL'
    ]

    for keyword in dangerous_keywords:
        # Check if keyword appears as a standalone word (not part of column/table name)
        if f' {keyword} ' in f' {query_upper} ' or query_upper.startswith(f'{keyword} '):
            return False

    # Must start with SELECT, WITH (for CTEs), or SHOW/EXPLAIN/DESCRIBE
    safe_starts = ['SELECT', 'WITH', 'SHOW', 'EXPLAIN', 'DESCRIBE', 'DESC']
    starts_safe = any(query_upper.startswith(keyword) for keyword in safe_starts)

    return starts_safe


def execute_sql_query(query: str) -> Dict[str, Any]:
    """
    Execute a SQL query against the connected PostgreSQL database.
    Only read-only queries (SELECT, WITH, SHOW, EXPLAIN, DESCRIBE) are allowed.

    Args:
        query (str): SQL query to execute

    Returns:
        dict: Query results with columns, rows, and row count
    """
    try:
        # Validate query is read-only
        if not is_read_only_query(query):
            error_msg = "Only read-only queries (SELECT, WITH, SHOW, EXPLAIN, DESCRIBE) are allowed. Detected potentially dangerous operations."
            print(f"ERROR: {error_msg}\n")
            return {
                "success": False,
                "error": error_msg,
                "query": query
            }

        print(f"\n{'='*80}")
        print(f"Executing query:\n{query}")
        print(f"{'='*80}\n")

        # Connect to database and execute query
        conn = get_database_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(query)

        # Check if query returns results (SELECT) or just affects rows (INSERT/UPDATE/DELETE)
        if cursor.description:
            # SELECT query - fetch results
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            # Convert rows to list of dicts for JSON serialization
            rows_as_dicts = [dict(row) for row in rows]

            result = {
                "success": True,
                "columns": columns,
                "rows": rows_as_dicts,
                "row_count": len(rows),
                "message": f"Query returned {len(rows)} row(s)"
            }

            # Print preview of results
            print(f"Results: {len(rows)} row(s)")
            if rows and len(rows) > 0:
                print(f"Preview (first 5 rows):")
                for i, row in enumerate(rows[:5], 1):
                    print(f"  {i}. {dict(row)}")
                if len(rows) > 5:
                    print(f"  ... and {len(rows) - 5} more row(s)")
            print()

        else:
            # INSERT/UPDATE/DELETE query - no results to fetch
            conn.commit()
            result = {
                "success": True,
                "message": f"Query executed successfully. Rows affected: {cursor.rowcount}",
                "rows_affected": cursor.rowcount
            }
            print(f"Rows affected: {cursor.rowcount}\n")

        cursor.close()
        conn.close()

        return result

    except Exception as e:
        print(f"ERROR: {str(e)}\n")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Define tools that the LLM can use for database analysis.

    Returns:
        list: Tool definitions in the format expected by the LLM
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_sql_query",
                "description": "Execute a SQL query against the connected PostgreSQL database to retrieve data. Use this to explore the database schema, query tables, and analyze data to answer the user's question.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL query to execute. Should be valid PostgreSQL syntax."
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]


def process_tool_calls(tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process tool calls from the LLM and execute them.

    Args:
        tool_calls (list): List of tool calls from the LLM

    Returns:
        list: Results of the tool calls
    """
    results = []

    for tool_call in tool_calls:
        function_name = tool_call["function"]["name"]
        arguments = json.loads(tool_call["function"]["arguments"])

        if function_name == "execute_sql_query":
            result = execute_sql_query(arguments["query"])
            results.append({
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": function_name,
                "content": json.dumps(result)
            })
        else:
            results.append({
                "tool_call_id": tool_call["id"],
                "role": "tool",
                "name": function_name,
                "content": json.dumps({"error": f"Unknown function: {function_name}"})
            })

    return results


def print_summary(question: str, analysis: str, queries_executed: List[str]):
    """
    Print a summary of the analysis in a console-friendly format.

    Args:
        question (str): The user's original question
        analysis (str): The LLM's analysis and answer
        queries_executed (list): List of SQL queries that were executed
    """
    print("\n" + "="*80)
    print("ANALYSIS SUMMARY")
    print("="*80)
    print(f"\nQuestion: {question}")
    print(f"\nQueries Executed ({len(queries_executed)}):")
    for i, query in enumerate(queries_executed, 1):
        print(f"\n  {i}. {query}")
    print("\n" + "="*80)


def main():
    # Get parameters from environment
    user_question = os.getenv("user_question")
    schema_context = os.getenv("schema_context", "")
    model_to_use = os.getenv("model_to_use")
    max_tokens_str = os.getenv("max_tokens")
    max_tokens = int(max_tokens_str) if max_tokens_str and max_tokens_str.strip() else 2000

    # Build system prompt with schema context
    system_prompt = """You are a helpful database analyst assistant. Your role is to help users understand and query their PostgreSQL database.

You have access to a tool called 'execute_sql_query' which allows you to run SQL queries against the database.

When answering questions:
1. First, understand what the user is asking
2. Plan which queries you need to run to gather the necessary information
3. Execute queries using the execute_sql_query tool
4. Analyze the results
5. Provide a clear, concise answer to the user's question

Always explain your reasoning and the queries you're running."""

    if schema_context:
        system_prompt += f"\n\nDatabase Schema Context:\n{schema_context}"

    # Initialize conversation with system prompt and user question
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_question}
    ]

    print("="*80)
    print("DATABASE ANALYST")
    print("="*80)
    print(f"\nUser Question: {user_question}\n")

    # Get LLM instance
    # TODO: Replace with `tower.llms()` once the CLI PR is merged
    llm = llms(model_to_use, max_tokens=max_tokens)
    tools = get_tool_definitions()

    # Track queries executed
    queries_executed = []

    # Agent loop - allow LLM to use tools iteratively
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- Iteration {iteration} ---")

        # Get LLM response with tool support
        response = llm.complete_chat(
            messages,
            tools=tools,
            max_tokens=max_tokens
        )

        # Check if response is a ChatCompletionOutput (HuggingFace) or ChatResponse (Ollama)
        # Both have different structures for tool_calls
        has_tool_calls = False
        tool_calls_list = []
        assistant_content = None

        if hasattr(response, 'choices'):
            # HuggingFace response
            message = response.choices[0].message
            if message.tool_calls:
                has_tool_calls = True
                # Convert HF tool calls to standard format
                for tc in message.tool_calls:
                    tool_calls_list.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
            assistant_content = message.content
        elif hasattr(response, 'message'):
            # Ollama response
            if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
                has_tool_calls = True
                tool_calls_list = response.message.tool_calls
            assistant_content = response.message.content

        # Check if LLM wants to use tools
        if has_tool_calls:
            # Add assistant message with tool calls to conversation
            messages.append({
                "role": "assistant",
                "content": assistant_content or "",
                "tool_calls": tool_calls_list
            })

            # Process tool calls
            tool_results = process_tool_calls(tool_calls_list)

            # Track queries
            for tool_call in tool_calls_list:
                if tool_call["function"]["name"] == "execute_sql_query":
                    args = json.loads(tool_call["function"]["arguments"])
                    queries_executed.append(args["query"])

            # Add tool results to conversation
            messages.extend(tool_results)

        else:
            # No more tool calls - LLM has final answer
            # Extract the actual text content from the response
            final_answer = None
            if hasattr(response, 'choices'):
                # HuggingFace response
                final_answer = response.choices[0].message.content
            elif hasattr(response, 'message'):
                # Ollama response
                final_answer = response.message.content
            elif isinstance(response, str):
                # Simple string response (backward compatibility)
                final_answer = response

            print("\n" + "="*80)
            print("ANALYSIS AND ANSWER")
            print("="*80)
            print(final_answer)
            print("="*80)

            # Print summary
            print_summary(user_question, final_answer, queries_executed)

            break

    if iteration >= max_iterations:
        print("\nReached maximum iterations without final answer")


if __name__ == "__main__":
    main()
