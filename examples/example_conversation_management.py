"""Example: Managing conversations with FoKS Intelligence."""

import requests
import sys


BASE_URL = "http://localhost:8001"


def create_conversation(user_id: str, title: str = None):
    """Create a new conversation."""
    url = f"{BASE_URL}/conversations/"
    payload = {
        "user_id": user_id,
        "title": title,
        "source": "example",
    }

    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()


def list_conversations(user_id: str, limit: int = 50, offset: int = 0):
    """List conversations for a user."""
    url = f"{BASE_URL}/conversations/"
    params = {
        "user_id": user_id,
        "limit": limit,
        "offset": offset,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_conversation(conversation_id: int, user_id: str = None):
    """Get a conversation by ID."""
    url = f"{BASE_URL}/conversations/{conversation_id}"
    params = {"user_id": user_id} if user_id else {}

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_messages(conversation_id: int, user_id: str = None):
    """Get all messages for a conversation."""
    url = f"{BASE_URL}/conversations/{conversation_id}/messages"
    params = {"user_id": user_id} if user_id else {}

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def update_conversation_title(conversation_id: int, title: str):
    """Update conversation title."""
    url = f"{BASE_URL}/conversations/{conversation_id}/title"
    params = {"title": title}

    response = requests.patch(url, params=params)
    response.raise_for_status()
    return response.json()


def delete_conversation(conversation_id: int, user_id: str = None):
    """Delete a conversation."""
    url = f"{BASE_URL}/conversations/{conversation_id}"
    params = {"user_id": user_id} if user_id else {}

    response = requests.delete(url, params=params)
    response.raise_for_status()
    return response.json()


def main():
    """Example usage."""
    user_id = "example_user"

    print("1. Creating conversation...")
    conv = create_conversation(user_id, "Example Conversation")
    conversation_id = conv["id"]
    print(f"   Created conversation {conversation_id}\n")

    print("2. Listing conversations...")
    conversations = list_conversations(user_id)
    print(f"   Found {conversations['total']} conversations\n")

    print("3. Getting conversation details...")
    conv_details = get_conversation(conversation_id, user_id)
    print(f"   Title: {conv_details['title']}")
    print(f"   Messages: {conv_details['message_count']}\n")

    print("4. Getting messages...")
    messages = get_messages(conversation_id, user_id)
    print(f"   Found {len(messages)} messages\n")

    print("5. Updating title...")
    updated = update_conversation_title(conversation_id, "Updated Title")
    print(f"   {updated['message']}\n")

    print("6. Verifying update...")
    conv_details = get_conversation(conversation_id, user_id)
    print(f"   New title: {conv_details['title']}\n")

    print("7. Deleting conversation...")
    deleted = delete_conversation(conversation_id, user_id)
    print(f"   {deleted['message']}\n")

    print("Done!")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        if hasattr(e.response, "text"):
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)

