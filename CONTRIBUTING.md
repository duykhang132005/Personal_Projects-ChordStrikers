# 🤝 Contributing to ChordStrikers

Thank you for your interest in contributing to **ChordStrikers**! We welcome all musicians, developers, and music enthusiasts to help improve this project.

---

## 🚀 How to Get Started

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/ChordStrikers.git
   cd ChordStrikers
   ```
3. **Set up a Virtual Environment**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
4. **Install Dependencies**:
   ```bash
   pip install -r requirements-dev.txt
   ```
5. **Set up Environment Variables**:
   Copy `.env.example` to `.env` and fill in any API keys if testing Spotify integration.

---

## 🧪 Running Tests

Before submitting a Pull Request, verify that all tests pass:

```bash
pytest
```

---

## 📝 Commit & PR Guidelines

- Use clear, descriptive commit messages (e.g. `feat: add PDF print export for chord sheets`).
- Keep changes focused and avoid unrelated code reformats.
- Ensure any new parser or route features include corresponding test cases in `tests/`.
