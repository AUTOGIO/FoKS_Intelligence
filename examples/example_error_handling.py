"""Example: Error handling with FoKS Intelligence."""

import requests
import sys
import time


BASE_URL = "http://localhost:8001"


def handle_lm_studio_error(response):
    """Handle LM Studio errors."""
    if response.status_code == 503:
        data = response.json()
        error_code = data.get("error_code", "UNKNOWN")
        details = data.get("details", {})

        if error_code == "LM_STUDIO_NETWORK_ERROR":
            print("❌ LM Studio não está conectado")
            print("   Verifique se o LM Studio está rodando em http://127.0.0.1:1234")
        elif error_code == "LM_STUDIO_SERVER_ERROR":
            print(f"❌ Erro no servidor LM Studio (tentativas: {details.get('attempts', '?')})")
            print("   O servidor pode estar sobrecarregado")
        elif error_code == "LM_STUDIO_CLIENT_ERROR":
            print(f"❌ Erro de cliente: {details.get('status_code', '?')}")
            print(f"   Resposta: {details.get('response', 'N/A')}")
        else:
            print(f"❌ Erro LM Studio: {error_code}")
    else:
        print(f"❌ Erro HTTP {response.status_code}: {response.text}")


def handle_database_error(response):
    """Handle database errors."""
    if response.status_code == 500:
        data = response.json()
        if data.get("error_code") == "DATABASE_ERROR":
            print("❌ Erro de banco de dados")
            print("   Verifique a conexão e permissões")
        else:
            print(f"❌ Erro interno: {data.get('error', 'Unknown')}")


def handle_rate_limit(response):
    """Handle rate limit errors."""
    if response.status_code == 429:
        print("⚠️  Rate limit excedido")
        print("   Aguarde 1 minuto antes de fazer novas requisições")
        return True
    return False


def chat_with_retry(message: str, max_retries: int = 3):
    """Send chat request with retry logic."""
    url = f"{BASE_URL}/chat/"
    payload = {"message": message, "source": "example"}

    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                return response.json()

            # Handle specific errors
            if handle_rate_limit(response):
                if attempt < max_retries - 1:
                    print(f"   Tentando novamente em 60 segundos... (tentativa {attempt + 1}/{max_retries})")
                    time.sleep(60)
                    continue

            handle_lm_studio_error(response)
            handle_database_error(response)

            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"   Tentando novamente em {wait_time} segundos... (tentativa {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            else:
                response.raise_for_status()

        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout na tentativa {attempt + 1}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"   Tentando novamente em {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                print("❌ Timeout após todas as tentativas")
                return None

        except requests.exceptions.ConnectionError:
            print(f"🔌 Erro de conexão na tentativa {attempt + 1}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"   Tentando novamente em {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                print("❌ Não foi possível conectar ao servidor")
                print("   Verifique se o backend está rodando em http://localhost:8001")
                return None

        except requests.exceptions.RequestException as e:
            print(f"❌ Erro na requisição: {e}")
            return None

    return None


def check_health():
    """Check system health."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        response.raise_for_status()
        health = response.json()

        print("📊 Status do Sistema:")
        print(f"   Status geral: {health.get('status', 'unknown')}")
        print(f"   LM Studio: {health.get('services', {}).get('lmstudio', 'unknown')}")
        print(f"   Banco de dados: {health.get('services', {}).get('database', 'unknown')}")
        print()

        if health.get("status") != "ok":
            print("⚠️  Sistema em estado degradado")
            return False

        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Não foi possível verificar saúde do sistema: {e}")
        return False


def main():
    """Example usage."""
    print("Verificando saúde do sistema...\n")
    if not check_health():
        print("⚠️  Continuando mesmo com sistema degradado...\n")

    message = "Hello, how are you?"
    print(f"Enviando mensagem: {message}\n")

    result = chat_with_retry(message)

    if result:
        print("\n✅ Sucesso!")
        print(f"Resposta: {result.get('reply', 'N/A')}")
    else:
        print("\n❌ Falha ao processar mensagem")
        sys.exit(1)


if __name__ == "__main__":
    main()

