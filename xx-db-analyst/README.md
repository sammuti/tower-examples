# Database Analyst with LLM Tool Calling

This Tower app demonstrates an AI-powered database analyst that can answer natural language questions about your PostgreSQL database. The app uses LLM tool calling to dynamically plan and execute SQL queries to answer user questions.

## Features

- **Natural Language Interface**: Ask questions about your database in plain English
- **Tool Calling Agent**: LLM plans and executes SQL queries autonomously to gather information
- **Schema Context**: Optionally provide schema documentation to help the LLM understand your database structure
- **Iterative Analysis**: The agent can execute multiple queries and refine its understanding
- **Local & Cloud Execution**: Develop locally with ollama, deploy to production with serverless inference

## How It Works

1. User provides a natural language question about their database
2. LLM receives the question along with optional schema context
3. LLM plans which SQL queries to execute using the `execute_sql_query` tool
4. App executes the queries and returns results to the LLM
5. LLM analyzes the results and can execute additional queries if needed
6. LLM provides a final answer with analysis
7. Results and query summary are displayed in the console

## Prerequisites

### Set Up Inference Providers

#### Install ollama and a DeepSeek R1 model (for local development)

```bash
pip install ollama
ollama pull deepseek-r1:14b
```

#### Sign Up for Hugging Face Hub (for production)

1. [Sign up for Hugging Face](https://huggingface.co/join)
2. Get your [access token](https://huggingface.co/docs/hub/en/security-tokens)
3. Install the hub: `pip install huggingface-hub>=0.34.3`

#### Sign Up for Together.ai (for production serverless inference)

1. Sign up for [together.ai](https://www.together.ai/)
2. Get your [access key](https://docs.together.ai/reference/authentication-1)
3. [Enable Together.ai in Hugging Face Hub](https://docs.together.ai/docs/quickstart-using-hugging-face-inference)

### Set up Tower

Follow the Tower [Quickstart](https://docs.tower.dev/docs/getting-started/quick-start) guide if you haven't already.

## Deploy the app to Tower

```bash
tower deploy
```

## Creating app secrets

The following secrets need to be defined in Tower's environments:

* `POSTGRES_URI` - PostgreSQL connection string (e.g., `postgresql://user:password@host:port/database`)
* `TOWER_INFERENCE_ROUTER` - Set to "ollama" for local development or "hugging_face_hub" for production
* `TOWER_INFERENCE_ROUTER_API_KEY` - Hugging Face token (not needed for ollama)
* `TOWER_INFERENCE_PROVIDER` - Set to "together" or other Hugging Face Hub inference provider

To create these secrets:

```bash
tower secrets create --environment="prod" \
  --name=POSTGRES_URI --value="postgresql://user:password@host:5432/database"

tower secrets create --environment="prod" \
  --name=TOWER_INFERENCE_ROUTER --value="hugging_face_hub"

tower secrets create --environment="prod" \
  --name=TOWER_INFERENCE_ROUTER_API_KEY --value="hf_1234567"

tower secrets create --environment="prod" \
  --name=TOWER_INFERENCE_PROVIDER --value="together"
```


## Running the app

### Running locally

Start ollama in a separate terminal:

```bash
ollama run deepseek-r1:14b
```

Run the app in local mode:

```bash
tower run --local \
  --parameter=user_question='What tables exist in the database?' \
  --parameter=model_to_use='deepseek-r1:14b'
```

With schema context:

```bash
tower run --local \
  --parameter=user_question='Show me the top 10 customers by total order value' \
  --parameter=schema_context='Database has tables: customers (id, name, email), orders (id, customer_id, total, created_at), order_items (id, order_id, product_id, quantity, price)' \
  --parameter=model_to_use='deepseek-r1:14b'
```

### Running in production

First ensure you have created the required secrets (see "Creating app secrets" section).

```bash
tower run --environment="prod" \
  --parameter=user_question='Analyze customer purchase patterns over the last 6 months' \
  --parameter=schema_context='[Your database schema description]' \
  --parameter=model_to_use='deepseek-ai/DeepSeek-R1' \
  --parameter=max_tokens=2000
```

## Parameters

- **user_question**: Natural language question about your database
- **schema_context**: Optional schema documentation (table names, columns, relationships, etc.)
- **model_to_use**: Model version (e.g., `deepseek-r1:14b` for local, `deepseek-ai/DeepSeek-R1` for production)
- **max_tokens**: Maximum output length in tokens (default: 2000)

## Example Questions

- "What tables exist in the database and how many rows does each have?"
- "Show me the distribution of orders by status"
- "Which customers have made more than 10 purchases?"
- "What is the average order value by month for the last year?"
- "Find products that haven't been ordered in the last 90 days"

## Check the run status

```bash
tower apps show
```

Or use the Tower [web UI](https://app.tower.dev) to monitor your app runs.

## Architecture

The app implements an agentic workflow:

1. **System Prompt**: Sets up the LLM as a database analyst with access to SQL execution tools
2. **Tool Definition**: Defines the `execute_sql_query` function that the LLM can call
3. **Agent Loop**: Iteratively processes LLM responses, executes tool calls, and feeds results back
4. **Console Output**: Displays the analysis and a summary of all queries executed

## Troubleshooting

### ModuleNotFoundError

```bash
export PYTHONPATH=.:$PYTHONPATH
```

### NotImplementedError on MPS device (Apple Silicon)

```bash
export PYTORCH_ENABLE_MPS_FALLBACK=1
```
