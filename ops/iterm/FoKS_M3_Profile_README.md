# FoKS Intelligence — M3-Optimized iTerm2 Profile

## Overview

This iTerm2 dynamic profile is specifically optimized for **MacBook Air 15" M3 (fanless)** running **macOS 26.0 (Tahoe)**. It includes thermal-aware GPU rendering, fast shell startup, auto-venv activation, and all FoKS-specific configurations.

## Features

### 🚀 Auto-Configuration
- **Auto-activates venv**: Automatically activates `backend/.venv_foks` on profile open
- **Auto-cd**: Changes to FoKS root directory (`~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence`)
- **PYTHONPATH**: Sets correct Python path for imports
- **Environment variables**: Sets `FOKS_ROOT` for scripts

### 🎨 Visual Optimizations
- **Font**: JetBrains Mono Nerd Font (13pt) with ligatures
- **Color scheme**: Catppuccin Mocha (high contrast, eye-friendly)
- **Scrollback**: 50,000 lines (M3 RAM-optimized, prevents Neural Engine conflicts)
- **Status bar**: CPU, Memory, Network, Clock, Current Directory

### ⚡ M3 Performance Optimizations
- **GPU Rendering**: Metal-accelerated (must enable in iTerm2 preferences)
- **Thermal gates**: Reduces GPU load during heavy text output
- **Fast shell**: Uses `/bin/zsh` with optimized startup
- **Silent bell**: Prevents audio interrupts during batch processing

### 🔔 Smart Triggers
- **Success**: Highlights "Application startup complete" in green
- **Errors**: Highlights "ERROR|CRITICAL|Exception" in red/yellow
- **Warnings**: Highlights "WARNING" in orange
- **Info/Debug**: Highlights in blue
- **URLs**: Makes `http://localhost:8000` clickable

## Installation

### Quick Install
```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/iterm
./install_m3_profile.sh
```

### Manual Install
```bash
# Copy profile to iTerm2 DynamicProfiles
cp ops/iterm/FoKS_M3_Optimized.json \
   ~/Library/Application\ Support/iTerm2/DynamicProfiles/

# Restart iTerm2 or reload profiles
# iTerm2 → Preferences → Profiles → Other Actions → Reload Dynamic Profiles
```

## Post-Installation: Enable M3 GPU Optimizations

After installing the profile, **manually enable** these iTerm2 settings for optimal M3 performance:

### 1. Enable GPU Rendering (Metal)
1. Open **iTerm2 → Preferences (⌘,)**
2. Go to **General → Magic**
3. Check **"GPU Rendering"** (Metal)
4. Check **"Disable GPU renderer when disconnected from power"** (thermal protection)
5. Check **"Maximize Throughput"** (reduces framerate to ~30fps during log floods, saves ~40% GPU power)

### 2. macOS 26.0 (Tahoe) Permissions
1. Open **System Settings → Privacy & Security → Local Network**
2. Ensure **iTerm2** is allowed (required for local AI APIs like LM Studio)

### 3. Set as Default (Optional)
1. **iTerm2 → Preferences → Profiles**
2. Select **"FoKS Intelligence — M3 Optimized"**
3. Click **"Other Actions..." → "Set as Default"**

## Usage

### Opening the Profile
- **Method 1**: Press **⌘T** (new tab), select "FoKS Intelligence — M3 Optimized"
- **Method 2**: Use keyboard shortcut **⌘+`** (if configured)
- **Method 3**: Right-click iTerm2 icon → "New Tab" → Select profile

### What Happens on Open
1. Changes to FoKS root directory
2. Activates `backend/.venv_foks` (if exists)
3. Sets `PYTHONPATH` and `FOKS_ROOT`
4. Displays welcome message with quick commands
5. Ready to use!

### Quick Commands (shown on profile open)
```bash
make run      # Start FoKS backend (port 8000)
make test     # Run backend tests
make lint     # Code quality checks
ops/scripts/foks_boot.sh  # Full boot script
```

## M3 Thermal Strategy

### Why These Settings Matter
The **MacBook Air 15" M3** is fanless. Sustained high-GPU terminal loads (like compiling logs or heavy text output) can cause thermal throttling, reducing CPU performance needed for dev/AI workflows.

### Our Approach
- **Burst performance**: GPU rendering enabled for smooth scrolling
- **Thermal gates**: Auto-disable GPU when on battery (if configured)
- **Throughput mode**: Drops framerate during massive text floods (logs)
- **50k scrollback**: Balanced buffer size (prevents RAM pressure on 16GB systems)

### Monitoring
The status bar shows:
- **CPU Utilization**: Watch for throttling (should stay <80% sustained)
- **Memory Usage**: Monitor for Neural Engine conflicts (keep <12GB free)
- **Network Throughput**: Track API calls to LM Studio/FBP

## Troubleshooting

### Profile Not Appearing
```bash
# Check if profile exists
ls -la ~/Library/Application\ Support/iTerm2/DynamicProfiles/FoKS_M3_Optimized.json

# Reload profiles manually
# iTerm2 → Preferences → Profiles → Other Actions → Reload Dynamic Profiles
```

### Venv Not Activating
```bash
# Check if venv exists
ls -la ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend/.venv_foks

# Create venv if missing
cd ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend
python3 -m venv .venv_foks
```

### GPU Rendering Not Working
1. Check iTerm2 version (needs 3.5+ for Metal)
2. Verify GPU rendering is enabled in Preferences → General → Magic
3. Check Activity Monitor → Energy tab (should show "GPU" usage for iTerm2)

### Font Not Found
```bash
# Install JetBrains Mono Nerd Font
brew tap homebrew/cask-fonts
brew install --cask font-jetbrains-mono-nerd-font

# Or use FiraCode
brew install --cask font-fira-code-nerd-font
```

## Advanced Configuration

### Custom Keyboard Shortcut
Edit the profile JSON and change:
```json
"Keyboard Shortcut": "0x3,0x3e"  // Change to your preferred shortcut
```

### Hotkey Window (Floating)
To enable floating hotkey window:
1. Edit profile JSON: Set `"Hotkey Window": true`
2. Configure in **Preferences → Keys → Hotkey**
3. Assign **Double-tap Cmd** or **⌘+`**

### Custom Triggers
Add more regex triggers in the profile JSON:
```json
"Triggers": [
  {
    "regex": "YOUR_PATTERN",
    "action": "HighlightTrigger",
    "parameter": "{#COLOR,}"
  }
]
```

## Profile Structure

```
FoKS_M3_Optimized.json
├── Profile Configuration
│   ├── Auto-venv activation
│   ├── Auto-cd to FoKS root
│   ├── Environment variables
│   └── Welcome message
├── Visual Settings
│   ├── Font (JetBrains Mono Nerd Font)
│   ├── Colors (Catppuccin Mocha)
│   └── Scrollback (50k lines)
├── Performance
│   ├── GPU Rendering (Metal)
│   └── Thermal optimizations
├── Status Bar
│   ├── CPU/Memory/Network
│   └── Clock/Directory
└── Triggers
    ├── Error highlighting
    ├── Success highlighting
    └── URL detection
```

## References

- [iTerm2 Dynamic Profiles Documentation](https://iterm2.com/documentation-dynamic-profiles.html)
- [M3 MacBook Air Specifications](https://support.apple.com/kb/SP844)
- [Catppuccin Color Scheme](https://github.com/catppuccin/catppuccin)
- [JetBrains Mono Font](https://www.jetbrains.com/lp/mono/)

## Support

For issues or questions:
1. Check this README
2. Review iTerm2 logs: `~/Library/Logs/iTerm2/`
3. Check FoKS logs: `~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/logs/`

---

**Last Updated**: 2025-01-XX  
**Profile Version**: 1.0  
**Compatible with**: iTerm2 3.5+, macOS 26.0+, M3 MacBook Air 15"

