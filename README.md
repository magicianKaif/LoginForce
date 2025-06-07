
# LOGIN FORCE

**LOGIN FORCE** is a powerful command-line brute-force tool developed in Python.  
It is designed for ethical hackers and cybersecurity learners to test and demonstrate login page security using wordlists and optional proxy support.

> ðŸ”¥ Developer: magician slime

---

## ðŸš€ Features

- ðŸ” Brute-force attacks on login forms
- ðŸ“‚ Supports custom password lists
- ðŸ§‘ Custom username input
- ðŸŒ Proxy support (including Tor SOCKS5 by default)
- ðŸŽ¨ ASCII banner via `pyfiglet`
- âš ï¸ Handles invalid URLs, missing files, and request errors

---

## âš™ï¸ Requirements

- Python 3.x  
- [`requests`](https://pypi.org/project/requests/)  
- [`pyfiglet`](https://pypi.org/project/pyfiglet/)

Install dependencies:
```bash
pip install requests pyfiglet
```

---

## ðŸ› ï¸ Usage

```bash
python loginforce.py -u <URL> -U <USERNAME> -P <PASSWORD_LIST> [-p <PROXY_FILE>]
```

### Arguments

| Argument         | Description                               |
|------------------|-------------------------------------------|
| `-u`, `--url`    | Target login page URL (required)          |
| `-U`, `--username` | Username to test (required)             |
| `-P`, `--password-list` | Path to password file (required)   |
| `-p`, `--proxy-file` | Optional file containing proxy URL    |

---

### ðŸ”„ Default Proxy

If no proxy file is provided, LOGIN FORCE defaults to:
```
socks5h://127.0.0.1:9050
```
âž¡ï¸ This means you can route attacks via **Tor** if it's running on your system.

---

### ðŸ“Œ Example

```bash
python loginforce.py -u http://example.com/login -U admin -P passwords.txt
```

With proxy file:
```bash
python loginforce.py -u http://example.com/login -U admin -P passwords.txt -p proxies.txt
```

---

## ðŸ“¬ Output Example

```
LOGIN FORCE
A powerful brute-force tool for testing login page security.
Developer: magician slime

Starting brute force attack...

[-] Tried: admin:123456
[-] Tried: admin:qwerty
[+] Found valid credentials: admin:letmein
```

---

## âš ï¸ Legal Disclaimer

> This tool is strictly for **educational purposes and ethical penetration testing**.  
> Unauthorized use against systems you do not own is **illegal** and punishable by law.  
> The developer takes **no responsibility** for misuse.

---

## ðŸ“¢ Contact

- **GitHub**: [magicianKaif](https://github.com/magicianKaif)
- **Telegram**: [@magician_slime](https://t.me/magician_slime/)
- **Instagram**: [@magicianslime](https://instagram.com/magicianslime)

---

## ðŸ¤ Contribute

Pull requests are welcome. If you find a bug or want to improve functionality, feel free to contribute!

---

## ðŸ§  Note

Use in a **safe and controlled environment** such as test labs or CTFs.
