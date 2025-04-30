# AES Vulnerable Implementation (Educational Use Only)

This is my educational implementation of the AES (Advanced Encryption Standard) encryption algorithm. The code includes **intentional vulnerabilities** and insecure practices that can be exploited, making it a valuable resource for **learning cryptography and security flaws** in encryption systems.

> ⚠️ **Disclaimer:** This project is for **educational purposes only**. Do **not** use this implementation in any real-world or production system.

---

## 🔒 Purpose

The goal of this project is to:

- Demonstrate a basic AES-like structure and logic flow.
- Highlight and explore **common cryptographic mistakes**.
- Enable hands-on experience for security students analyzing weak encryption implementations.

---

## 🛠 Features

- AES-like encryption with:
  - SubBytes
  - ShiftRows
  - MixColumns (simplified)
  - AddRoundKey with XOR
  - Round key generation (intentionally weak)
- Key is read from an external file (`key.txt`) for modularity.
- Works on **16-character plaintexts only**.

---

## ⚠️ Known Vulnerabilities

- **Time-based round key generation** using predictable values (UNSAFE).
- **Non-standard and incorrect** MixColumns transformation.
- No padding or IV (initialization vector).
- Weak entropy in key expansion.
- No decryption function provided.
- Minimal input validation.

---

## 🧪 How to Run

1. Ensure you have Python 3 and `numpy` installed:
   ```bash
   pip install numpy
