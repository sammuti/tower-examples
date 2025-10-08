import os
import json

# Set up environment variables
os.environ["TOWER_INFERENCE_ROUTER"] = "hugging_face_hub"
os.environ["TOWER_INFERENCE_ROUTER_API_KEY"] = "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"
os.environ["TOWER_INFERENCE_PROVIDER"] = "together"

import tower

# Define a simple tool
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city name"
                    }
                },
                "required": ["location"]
            }
        }
    }
]

# Create LLM instance
llm = tower.llms("meta-llama/Llama-3.3-70B-Instruct", max_tokens=500)

# Test with tools
messages = [
    {"role": "system", "content": "You are a helpful assistant with access to weather information."},
    {"role": "user", "content": "What's the weather in San Francisco?"}
]

print("Testing tool calling with Hugging Face Hub...")
print("=" * 80)

try:
    response = llm.complete_chat(messages, tools=tools)
    print(f"Response type: {type(response)}")
    print(f"Response: {response}")
    
    if hasattr(response, 'choices'):
        print(f"\nChoices: {response.choices}")
        if response.choices and hasattr(response.choices[0].message, 'tool_calls'):
            print(f"Tool calls: {response.choices[0].message.tool_calls}")
    
    print("\n✓ Tool calling test successful!")
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Testing WITHOUT tools (backward compatibility)...")
print("=" * 80)

try:
    # Test without tools - should return a string like before
    messages_simple = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say 'Hello, World!' and nothing else."}
    ]

    response_simple = llm.complete_chat(messages_simple)

    print(f"Response type: {type(response_simple)}")
    print(f"Response: {response_simple}")

    # Verify it's a string (backward compatibility)
    if isinstance(response_simple, str):
        print("\n✓ Backward compatibility test successful! Returns string when no tools.")
    else:
        print(f"\n✗ Expected string, got {type(response_simple)}")

except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
