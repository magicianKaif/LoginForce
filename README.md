# LOGIN FORCE

LOGIN FORCE is a powerful command-line tool designed for educational purposes to demonstrate brute-force attacks on website login pages. It helps security professionals and penetration testers evaluate the strength of authentication mechanisms.

## Developer
**magician slime**

---

## Features
- Easy-to-use command-line interface.
- Processes large password lists line-by-line for memory efficiency.
- URL validation to ensure proper input formatting.
- Customizable username and password inputs.
- Timeout handling for stable and reliable connections.

---

## Requirements
- Python 3.x
- `requests` library
- `pyfiglet` library

Install dependencies using:
```bash
pip install requests pyfiglet
```

---

## Usage
```bash
python login_force.py -u <URL> -U <USERNAME> -P <PASSWORD_LIST>
```

### Arguments
- `-u`, `--url` : URL of the login page (required).
- `-U`, `--username` : Username to test (required).
- `-P`, `--password-list` : Path to the password list file (required).

### Example
```bash
python login_force.py -u http://example.com/login -U admin -P passwords.txt
```

---

## Output
The script displays all login attempts and highlights any valid credentials found.

### Sample Output
```
LOGIN FORCE
A powerful brute-force tool for testing login page security.
Developer: magician slime

Starting brute force attack...
[-] Tried: admin:password123
[+] Found valid credentials: admin:letmein
```

---

## Legal Disclaimer
This tool is intended for authorized testing and educational purposes only. Unauthorized access to computer systems is illegal. The developer assumes no responsibility for any misuse or damage caused by this tool.

---

## Contact
- **Developer:** magician slime
- **GitHub:** [magicianKaif](https://github.com/magicianKaif)
- **Telegram:** [t.me/magician_slime](https://t.me/magician_slime/)
- **Instagram:** [@magicianslime](https://instagram.com/magicianslime)

---

## Contribution
Contributions are welcome! Submit a pull request or report issues on GitHub.

