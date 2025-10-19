# Mini browser

Develop a simple web browser

## Learning material

[Web Browser Engineering](https://browser.engineering/)

## Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

1. **Browser usage:**

```bash
# Run the browser with an optional `url` argument
# (default url: "https://browser.engineering/")
python -m browser <url>
```

2. **Test-Server usage:**

```bash
# Start the test server
python -m server

# Make request from browser
python -m browser http://localhost:8000
```

## Debugging (VS Code)

- Create a `launch.json` file _(The example below points to the test server)_.
- Add breakpoints and start debugging.

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python Debugger: Module",
      "type": "debugpy",
      "request": "launch",
      "module": "browser",
      "args": ["http://localhost:8000"]
    }
  ]
}
```
