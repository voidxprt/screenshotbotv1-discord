# 📸 Discord Screenshot Bot

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg?logo=python)](https://www.python.org/)
[![Discord.py](https://img.shields.io/badge/discord.py-2.3+-5865F2.svg?logo=discord&logoColor=white)](https://discordpy.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/<your-username>/discord-screenshot-bot?style=social)](https://github.com/<your-username>/discord-screenshot-bot/stargazers)

> A sleek Python-powered Discord bot that generates **clean, realistic screenshots** of messages.  
> No more messy cropping — just copy, reply, and capture. ⚡  

---

## ✨ Features

- 🌗 **Light & Dark mode rendering**
- 🏷️ Mentions, roles, `@everyone`, and `@here`
- 😀 Emoji support via [Twemoji](https://github.com/twitter/twemoji)
- 🎨 **Custom licensed Whitney-style fonts** (bundled)
- ⚡ Prefix command (`!ss`) and slash commands (`/setup`, `/lightmode`, `/darkmode`)

---

## 📂 Project Structure

```

discord-screenshot-bot/
├── bot.py               # main bot file
├── config.json          # auto-created if missing (stores guild settings)
├── fonts/               # custom Whitney-style fonts (licensed)
│   ├── whitneybook.otf
│   ├── whitneysemibold.otf
│   ├── whitneybookitalic.otf
├── twemoji/             # auto-populated with emoji PNGs
├── requirements.txt     # dependencies
├── LICENSE              # MIT License
└── README.md

````

---

## ⚙️ Installation

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-username>/discord-screenshot-bot.git
cd discord-screenshot-bot
````

### 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Setup Environment

Create a `.env` file in the project root:

```env
DISCORD_TOKEN=your_discord_bot_token_here
```

> 🔒 **Never hardcode your token** inside `bot.py`.
> The bot will read it from `.env`.

### 4️⃣ Run the Bot

```bash
python bot.py
```

---

## 🎮 Usage

* **Prefix Command**

  * Reply to a message and type:

    ```
    !ss
    ```

    → Generates and sends a screenshot of that message.

* **Slash Commands**

  * `/setup` → choose light or dark mode for your server.
  * `/lightmode` → switch to light mode.
  * `/darkmode` → switch to dark mode.

---

## 🎨 Fonts

This bot uses **custom Whitney-style fonts** that I created and licensed.
They are legally shareable and included in the `fonts/` directory.

> ⚠️ These are **not Discord’s proprietary fonts** — they are original, licensed versions.

---

## 🖼️ Example

> *(Add screenshots here after running the bot — light & dark mode examples work great!)*

---

## 🛠️ Notes

* `config.json` → created automatically per server (stores mode).
* `twemoji/` → populated dynamically when new emojis are used.
* `screenshot_*.png` → temporary files, auto-deleted after sending.

---

## 📜 License

Licensed under the **MIT License** — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
Feel free to check the [issues page](https://github.com/<your-username>/discord-screenshot-bot/issues).

---

## 🌟 Support

If you find this project useful, please give it a ⭐ on GitHub — it helps a lot!
