# 🔒 Security Policy & Architecture Manifesto

At **Tazala**, privacy, confidentiality, and account safety are our foundational principles. We operate under a strict **Zero-Knowledge Architecture** ensuring that we never store, persist, or expose your Telegram account credentials, messages, or authorization tokens.

---

## 🛡️ Zero-Knowledge Security Principles

### 1. Ephemeral MTProto QR Login (No Phone Numbers or SMS)
- Traditional Telegram logins require phone numbers and SMS/Telegram verification codes. This introduces risks of SIM-swapping, interception, and credential logging.
- **Tazala uses native MTProto QR Login:**
  - An ephemeral MTProto key exchange is initiated on demand.
  - You scan the QR code directly inside the official Telegram mobile app (**Settings ➔ Devices ➔ Link Desktop Device**).
  - The login session is treated by Telegram as a temporary connected device, giving you instant visibility and manual revocation control at any moment.

### 2. RAM-Only Session Storage (Zero Disk Persistence)
- Session tokens (`StringSession`) exist **exclusively in Redis RAM** with a strict Time-To-Live (TTL) of **300 seconds (5 minutes)**.
- **Not a single byte of session data is ever written to disk, databases, or logs.**
- If the Redis service restarts or the TTL expires, the authorization string vanishes completely from memory.

### 3. Immediate Deletion of 2FA Cloud Passwords
- If your Telegram account is protected with Two-Step Verification (2FA), the bot will request your cloud password.
- **Instant Chat Deletion:** The moment you send your password in the chat, Tazala immediately triggers `message.delete()` on Telegram's servers to remove it from your chat history.
- The password is only used in-memory for the single cryptographic computation needed to complete the SRP handshake with Telegram servers and is immediately garbage-collected. It is never logged, cached, or stored anywhere.

### 4. Cryptographic Revocation via `client.log_out()`
- Immediately after you finish your cleanup or click **"Log Out & Destroy Session"** (`session_logout`), Tazala invokes:
  ```python
  await client.log_out()
  ```
- **What this means:** Unlike simply deleting a local token, `log_out()` instructs Telegram's data centers to **permanently destroy and invalidate the auth key** for that device session. Even if an attacker obtained the discarded token, it is cryptographically dead and cannot be reused.

### 5. Don't Trust, Verify (100% Open Source)
- Every line of code running Tazala is public and open for community audit.
- There are no proprietary blobs, telemetry trackers, or external webhooks.
- **Self-Hosting:** You can run your own private instance of Tazala on your local machine or private server using Docker Compose within 60 seconds.

---

## 🚨 Reporting a Vulnerability

We appreciate the efforts of security researchers and community members who help keep Tazala and its users secure.

If you discover a security vulnerability in Tazala:
1. **Do not disclose it publicly** (such as in GitHub Issues, Reddit, or Telegram channels).
2. Please submit a confidential security advisory through **GitHub Security Advisories** on our repository:
   - [New Security Advisory](https://github.com/DeadOutside1/tazala/security/advisories/new)
   - Or email the project maintainers directly: `security@tazala.dev` / open a private discussion with [@DeadOutside1](https://github.com/DeadOutside1).
3. Include detailed steps to reproduce the issue, proof of concept, and any affected configurations.

### Response Timelines
- **Initial Response:** Within 24 hours acknowledging receipt.
- **Assessment & Triage:** Within 48 hours confirming the issue severity and impact.
- **Patch Release & Public Disclosure:** Coordinated release once a fix is verified and deployed.

---

## 📜 Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| `0.1.x` | :white_check_mark: |
