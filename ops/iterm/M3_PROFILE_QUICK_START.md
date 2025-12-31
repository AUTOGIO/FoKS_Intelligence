# FoKS M3 Profile — Quick Start

## 🚀 Install in 30 Seconds

```bash
cd /Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/ops/iterm
./install_m3_profile.sh
```

## ✅ Post-Install Checklist

1. **Open iTerm2 → Preferences (⌘,)**
2. **General → Magic**:
   - ✅ Enable "GPU Rendering"
   - ✅ Enable "Disable GPU renderer when disconnected from power"
   - ✅ Enable "Maximize Throughput"
3. **Profiles → Select "FoKS Intelligence — M3 Optimized"**
4. **Other Actions → Set as Default** (optional)

## 🎯 Use It

- **⌘T** → Select "FoKS Intelligence — M3 Optimized"
- Profile auto-activates venv and sets up environment
- Ready to run `make run` or `ops/scripts/foks_boot.sh`

## 📋 What's Included

- ✅ Auto-venv activation (`backend/.venv_foks`)
- ✅ Auto-cd to FoKS root
- ✅ M3 thermal optimizations
- ✅ 50k scrollback buffer
- ✅ Catppuccin Mocha colors
- ✅ Status bar (CPU/Memory/Network)
- ✅ Smart error highlighting
- ✅ Clickable URLs

## 🔧 Troubleshooting

**Profile not showing?**
```bash
# Reload profiles
# iTerm2 → Preferences → Profiles → Other Actions → Reload Dynamic Profiles
```

**Venv not activating?**
```bash
cd ~/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence/backend
python3 -m venv .venv_foks
```

**Font missing?**
```bash
brew install --cask font-jetbrains-mono-nerd-font
```

---

See `FoKS_M3_Profile_README.md` for full documentation.

