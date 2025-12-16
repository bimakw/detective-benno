# Recording Demo GIF Guide

## Option 1: Using asciinema + svg-term-cli (Best Quality)

```bash
# Install tools
brew install asciinema
npm install -g svg-term-cli

# Record the demo
cd /Users/okinn/code/portofolio/detective-benno
asciinema rec demo.cast -c "python3 scripts/demo.py"

# Convert to SVG (animated)
svg-term --in demo.cast --out docs/demo.svg --window --width 80 --height 30

# Or use gifski for GIF (need to install gifski)
brew install gifski
# Then use online converter: https://dstein64.github.io/gifcast/
```

## Option 2: Quick Screen Recording (macOS)

1. Open Terminal
2. Resize window to ~80x30 characters
3. Press `Cmd + Shift + 5` to open screen recording
4. Select "Record Selected Portion" and select terminal
5. Run: `python3 scripts/demo.py`
6. Stop recording
7. Convert MOV to GIF:
   ```bash
   # Using ffmpeg + gifski
   brew install ffmpeg gifski
   ffmpeg -i demo.mov -vf "fps=10,scale=800:-1" -c:v pam -f image2pipe - | gifski -o demo.gif --fps 10
   ```

## Option 3: Online Tools

1. Record with QuickTime (Cmd + Shift + 5)
2. Upload to https://ezgif.com/video-to-gif
3. Optimize settings: 800px width, 10 FPS

## After Recording

1. Save GIF to `docs/demo.gif`
2. Update README.md to include:
   ```markdown
   ## Demo

   ![Detective Benno Demo](docs/demo.gif)
   ```
3. Commit and push
