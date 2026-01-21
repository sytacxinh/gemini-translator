# Gemini Translator

A Windows desktop application for instant text translation using Google's Gemini AI. Select any text, press a hotkey, and get translations in a compact tooltip - no window switching needed!

## Features

### Quick Translation Hotkeys
- `Win+Alt+V` → Vietnamese
- `Win+Alt+E` → English
- `Win+Alt+J` → Japanese
- `Win+Alt+C` → Chinese Simplified
- **Customizable hotkeys** in Settings

### Modern UI (v1.2.0)
- **Smart tooltip sizing** - Auto-adjusts based on text length (max 800px wide)
- **Dark theme** with modern ttkbootstrap styling
- **Hidden scrollbars** - Clean look with scroll functionality
- **Custom prompts** - Add instructions like "Make it formal" or "Use casual tone"
- **Currency conversion** - Automatically converts currencies to target language's local currency

### Settings (New in v1.2.0)
- **GUI API Key Setup** - No more manual .env editing
- **Custom Hotkeys** - Record any key combination for any language
- **Start with Windows** - One-click auto-start toggle
- **Test Connection** - Verify your API key works

### Additional Features
- **30+ Languages** supported
- **System tray** - Runs quietly in background
- **Open in Gemini** - Quick access to Gemini web for complex translations
- **Auto-update check** - Get notified when new versions are available
- **Single instance** - Prevents multiple instances running
- **Clipboard preservation** - Preserves your clipboard content (files/images)

## Screenshots

<!-- Add screenshots here -->
<!-- ![Tooltip](assets/tooltip.png) -->
<!-- ![Full Window](assets/full-window.png) -->
<!-- ![Settings](assets/settings.png) -->

## Installation

### Prerequisites

- Python 3.10 or higher
- Windows 10/11
- Gemini API key (free)

### Option 1: Download .exe (Recommended)

1. Go to [Releases](https://github.com/sytacxinh/gemini-translator/releases)
2. Download `GeminiTranslator.exe`
3. Run the application
4. On first run, Settings will open - enter your API key
5. Get your free API key at: https://aistudio.google.com/app/apikey

### Option 2: Run from source

1. **Clone the repository**
   ```bash
   git clone https://github.com/sytacxinh/gemini-translator.git
   cd gemini-translator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get your Gemini API key**
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a new API key (it's free!)

4. **Configure API key** (choose one method)

   **Method A: Settings GUI (Recommended)**
   - Run the application
   - Click "Open Settings" when prompted
   - Enter your API key and click Save

   **Method B: .env file**
   Create a `.env` file in the project folder:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

5. **Run the application**
   ```bash
   python translator.py
   ```

   Or double-click `run_silent.vbs` to run without console window.

## Usage

1. **Start the app** - It will minimize to system tray (look for "GT" icon)

2. **Translate text**:
   - Select any text in any application
   - Press one of the hotkeys:
     - `Win+Alt+V` → Vietnamese
     - `Win+Alt+E` → English
     - `Win+Alt+J` → Japanese
     - `Win+Alt+C` → Chinese Simplified
   - A tooltip with the translation will appear near your cursor

3. **Tooltip actions**:
   - **Copy** - Copy translation to clipboard
   - **Open Translator** - Open full window with more options
   - **✕** - Close tooltip (or press `Escape`)

4. **Full Translator window**:
   - Click "Open Translator" from tray menu or tooltip
   - Edit original text
   - Choose any of 30+ languages
   - Add custom prompt for special translation styles
   - Re-translate with different settings
   - Open in Gemini web for complex queries

5. **Settings**:
   - Right-click tray icon → Settings
   - Configure API key, hotkeys, auto-start

6. **Exit**: Right-click the tray icon → Quit

## Auto-start with Windows

**Method A: Settings (Recommended)**
1. Right-click tray icon → Settings
2. Go to General tab
3. Check "Start Gemini Translator with Windows"

**Method B: Manual**
1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `GeminiTranslator.exe` in that folder

## Configuration

### Customizing Hotkeys

1. Open Settings (right-click tray → Settings)
2. Go to Hotkeys tab
3. Click "Record" next to any language
4. Press your desired key combination
5. Click Save

### Custom Translation Prompts

In the full translator window, use the "Custom prompt" field to add special instructions:
- "Make it formal" - For business communication
- "Use casual tone" - For friendly messages
- "Technical translation" - For documentation
- "Keep it brief" - For concise translations

## Requirements

```
pyperclip==1.8.2
google-generativeai==0.8.3
pystray==0.19.5
Pillow==12.1.0
ttkbootstrap==1.10.1
pywin32==306
keyboard==0.13.5
packaging==24.0
```

## Troubleshooting

### "GEMINI_API_KEY not found" or API Error
1. Open Settings and enter your API key
2. Click "Test Connection" to verify
3. Or create a `.env` file with `GEMINI_API_KEY=your_key`

### Translation not working
- Check if text is actually selected (try Ctrl+C manually)
- Some applications may block clipboard access
- Wait for the cooldown period (2 seconds between translations)

### Hotkeys not working
- Check Settings → Hotkeys to see configured shortcuts
- Try running the app as administrator
- Some apps (like VS Code) may capture certain key combinations

### Hotkeys conflict with other apps
- Open Settings → Hotkeys
- Click "Record" and set a different key combination
- Recommended: Use `Ctrl+Shift+Alt+Letter` for less conflicts

### Multiple instances running
The app should prevent this automatically. If it happens, check Task Manager and end extra processes.

## What's New in v1.2.0

- **Modern UI** with ttkbootstrap dark theme
- **Smart tooltip sizing** that adapts to content
- **Settings window** with API key, hotkeys, and general settings
- **Customizable hotkeys** - Record any key combination
- **Win+Alt+C** for Chinese translation
- **Custom prompts** for specialized translations
- **Currency conversion** in translations
- **Auto-start with Windows** toggle
- **Auto-update checker**
- **Better clipboard handling** (preserves files/images)
- **Improved error messages** with setup instructions
- **Code architecture refactoring** for better maintainability

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Powered by [Google Gemini AI](https://deepmind.google/technologies/gemini/)
- Built with Python, Tkinter, and ttkbootstrap
