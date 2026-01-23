# AI Translator

![Version](https://img.shields.io/badge/version-1.5.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-yellow.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-informational.svg)

A Windows desktop application for instant text translation using advanced AI models (Google Gemini, OpenAI, DeepSeek, Groq, Claude, etc.). Select any text, press a hotkey, and get translations in a compact tooltip - no window switching needed!

## Features

### Quick Translation Hotkeys
*   `Win+Alt+V` → Vietnamese
*   `Win+Alt+E` → English
*   `Win+Alt+J` → Japanese
*   `Win+Alt+C` → Chinese Simplified
*   **Customizable hotkeys**: Record any key combination for any language in Settings.

### Modern UI
*   **Smart tooltip sizing**: Auto-adjusts based on text length.
*   **Dark theme**: Modern look with `ttkbootstrap`.
*   **Custom prompts**: Add instructions like "Make it formal" or "Use casual tone".
*   **Currency conversion**: Automatically converts currencies to target language's local currency.

### Multi-Provider Support
*   **Supports multiple AI providers**: Google Gemini, OpenAI, Anthropic (Claude), DeepSeek, Groq, xAI (Grok), Mistral, Perplexity, etc.
*   **Smart Routing**: Automatically detects provider based on API key format or model name.
*   **Failover System**: Configure multiple keys to ensure uninterrupted service.

### Settings
-   **GUI API Key Setup**: Easy configuration for multiple providers.
-   **Start with Windows**: One-click auto-start toggle.
-   **Test Connection**: Verify your API key works immediately.

### Additional Features
-   **100+ Languages** supported.
-   **System tray**: Runs quietly in background.
-   **Open in Web**: Quick access to Gemini web for complex translations.
-   **Auto-update check**: Get notified when new versions are available.
-   **Clipboard preservation**: Preserves your clipboard content (files/images) after translation.

## Installation

### Prerequisites
- Python 3.10 or higher
- Windows 10/11
- An API key (Google Gemini is free!)

### Option 1: Download .exe (Recommended)
1. Go to Releases
2. Download `AITranslator.exe`
3. Run the application
4. On first run, Settings will open - enter your API key
5. Get your free Gemini API key at: https://aistudio.google.com/app/apikey

### Option 2: Run from source

1. **Clone the repository**
   ```bash
   git clone https://github.com/sytacxinh/ai-translator.git
   cd ai-translator
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get your Gemini API key**
   - Go to Google AI Studio
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
   python main.py
   ```
   *Or double-click `run_silent.vbs` to run without the console window.*

## Usage

1. **Start the app** - It will minimize to system tray (look for "AI" icon)

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
   - Choose any of 100+ languages
   - Add custom prompt for special translation styles
   - Re-translate with different settings

5. **Settings**:
   - Right-click tray icon → Settings
   - Configure API key, hotkeys, auto-start

6. **Exit**: Right-click the tray icon → Quit

## Auto-start with Windows

**Method A: Settings (Recommended)**
1. Right-click tray icon → Settings
2. Go to General tab
3. Check "Start AI Translator with Windows"

**Method B: Manual**
1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `AITranslator.exe` in that folder

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

## Troubleshooting

### API Error / Connection Failed
1. Open Settings and enter your API key
2. Ensure you selected the correct **Provider** for your key (e.g., select "DeepSeek" for DeepSeek keys).
3. Click "Test" to verify the connection.

### Translation not working
- Check if text is actually selected (try Ctrl+C manually)
- Some applications may block clipboard access
- Wait for the cooldown period (2 seconds between translations)

### Hotkeys not working
- Check Settings → Hotkeys to see configured shortcuts
- Try running the app as administrator
- Some apps (like VS Code) may capture certain key combinations

## What's New in v1.5.0

-   🚀 **Modular Architecture**: Complete code refactoring for better stability and performance.
-   🛠 **Improved Settings**: Easier API key management and hotkey recording.
-   🐛 **Bug Fixes**: Fixed issues with clipboard handling and hotkey conflicts.
-   📦 **Lightweight**: Optimized resource usage.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Powered by Google Gemini AI
- Built with Python, Tkinter, and ttkbootstrap
