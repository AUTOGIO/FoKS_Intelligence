"""Example: Using the streaming chat endpoint."""

import json
import requests
import sys


def stream_chat(message: str, conversation_id: int = None, user_id: str = "example_user"):
    """
    Stream chat response from FoKS Intelligence.

    Args:
        message: User message
        conversation_id: Optional conversation ID to continue
        user_id: User identifier
    """
    url = "http://localhost:8001/chat/stream"
    params = {
        "conversation_id": conversation_id,
        "user_id": user_id,
    }
    payload = {
        "message": message,
        "source": "example",
    }

    print(f"Sending: {message}\n")
    print("Response (streaming):\n")

    try:
        response = requests.post(
            url,
            json=payload,
            params=params,
            stream=True,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()

        full_response = ""
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    try:
                        data = json.loads(line_str[6:])  # Remove "data: " prefix
                        chunk = data.get("chunk", "")
                        done = data.get("done", False)

                        if chunk:
                            print(chunk, end="", flush=True)
                            full_response += chunk

                        if done:
                            print("\n")
                            break
                    except json.JSONDecodeError:
                        continue

        return full_response
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python example_chat_streaming.py <message> [conversation_id]")
        sys.exit(1)

    message = sys.argv[1]
    conversation_id = int(sys.argv[2]) if len(sys.argv) > 2 else None

    stream_chat(message, conversation_id)

