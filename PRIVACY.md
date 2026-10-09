# 🛡️ Privacy Policy & Security Guarantee

**Published by:** TAB inc.  
**Effective Date:** 2026

At **TAB inc.**, our core philosophy is simple: **Your input, your network, and your data belong strictly to you.**

---

## 1. Zero Telemetry & Zero Analytics
* **Fetch collects NO telemetry**: There are zero tracking beacons, analytics scripts, crash report uploaders, or usage statistics embedded in either the mobile app or host servers.
* **No Cloud Servers**: Fetch does not communicate with any external TAB inc. server or cloud provider. All operations exist 100% locally on your home Wi-Fi / Local Area Network (LAN).
* **No Account Required**: You will never be asked to create an account, provide an email address, or log in to use Fetch.

## 2. Keystroke & Input Privacy
* Keystrokes, mouse coordinates, and media commands are streamed directly between your smartphone and your PC over an encrypted local RFC 6455 WebSocket connection.
* Input data is processed directly in volatile RAM and is **never written to disk or logged to files**.

## 3. Network Discovery
* Local discovery uses UDP broadcasts strictly within your local subnet (`255.255.255.255:8766`).
* Packets contain only your computer's local network hostname, local IP address, and MAC address (for Wake-on-LAN functionality).
* Discovery packets never leave your local router.

## 4. Open & Auditable
* The complete source code for both the Android client and the host servers (Python, Win32/.NET C#) is available for inspection and audit.

---
*For support or inquiries: contact TAB inc. via GitHub Issues.*
