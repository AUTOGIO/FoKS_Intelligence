# AETHER

## Adaptive Environment & Task Handler for Enhanced Reality

> **Native macOS Menubar App for Intelligent Workspace Management**

![macOS](https://img.shields.io/badge/macOS-14.0+-blue)
![Swift](https://img.shields.io/badge/Swift-5.9+-orange)
![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-M3%20Optimized-green)

---

## 🚀 Quick Start

### Build & Run

```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/AETHER

# Open in Xcode
open AETHER.xcodeproj

# Or build from command line
xcodebuild -project AETHER.xcodeproj -scheme AETHER -configuration Debug build

# Run the built app
open build/Debug/AETHER.app
```

### First Launch

1. **Grant Accessibility Permission**

   - System Settings → Privacy & Security → Accessibility
   - Add AETHER and enable

2. **Click the menubar icon** (sparkles icon)

   - You'll see 3 default profiles: Work, Personal, AI Research

3. **Capture your first layout**

   - Arrange your windows how you like
   - Hover over a profile → Click 📸 (camera icon)
   - Layout saved!

4. **Switch profiles**
   - Click any profile name
   - Windows automatically rearrange

---

## ✨ Features

| Feature                | Description                                             |
| ---------------------- | ------------------------------------------------------- |
| **Profile Management** | Save and restore window layouts per workspace           |
| **Window Control**     | Uses native Accessibility API                           |
| **Screen Time**        | Tracks app usage locally in SQLite                      |
| **AI Suggestions**     | Connects to LM Studio for smart profile recommendations |
| **Privacy First**      | All data stored locally, no cloud required              |

---

## 🛠️ Configuration

### LM Studio Integration

AETHER connects to your LM Studio at `http://100.72.60.38:1234/v1`.

**To change the URL:**

1. Open Settings (gear icon in menubar)
2. Go to AI tab
3. Update the LM Studio URL
4. Click "Test Connection"

### Data Storage

All data is stored in `~/Library/Application Support/AETHER/`:

- `profiles.json` - Saved workspace profiles
- `screentime.db` - Usage tracking database

---

## 📊 Screen Time

AETHER tracks which apps you use and for how long:

- Polls active app every 30 seconds
- Stores in local SQLite
- View stats in Settings → Screen Time

---

## 🧠 AI Features

When LM Studio is running, AETHER can:

- Suggest optimal profiles based on time and active apps
- Provide productivity tips
- Learn your patterns (future)

**Recommended models:**

- `SmolLM2-1.7B-Instruct` - Fast routing decisions
- `DeepSeek-R1-Distill-Qwen-7B-4bit` - Complex reasoning

---

## 🔐 Permissions Required

| Permission        | Purpose                 |
| ----------------- | ----------------------- |
| **Accessibility** | Window management       |
| **Network**       | LM Studio communication |

---

## 📁 Project Structure

```
AETHER/
├── AETHER.xcodeproj
└── AETHER/
    ├── AETHERApp.swift         # App entry point
    ├── Models/
    │   ├── Profile.swift       # Workspace profile model
    │   └── ScreenTimeEntry.swift
    ├── Services/
    │   ├── WindowManager.swift # Accessibility API
    │   ├── ProfileManager.swift
    │   ├── ScreenTimeService.swift
    │   └── LMStudioClient.swift
    ├── Views/
    │   ├── MenuBarView.swift   # Main dropdown UI
    │   └── SettingsView.swift
    └── Resources/
        └── Assets.xcassets
```

---

## 🎯 Keyboard Shortcuts

Set up via **BetterTouchTool** or **Keyboard Maestro**:

- `⌘⇧1` → Switch to Work profile
- `⌘⇧2` → Switch to Personal profile
- `⌘⇧3` → Switch to AI Research profile

---

## 💡 Tips

1. **Capture layouts often** - Update profiles as your workflow evolves
2. **Use multiple displays** - AETHER remembers which display each window belongs to
3. **Keep LM Studio running** - For smart suggestions
4. **Check stats weekly** - Understand your productivity patterns

---

## 📜 License

MIT License - © 2026 Giovannini Mare Capital LLC - Tech Division

---

**Built with ❤️ for Apple Silicon**
