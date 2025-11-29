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

## Installation notes

This project depends on **Skia** (for 2D graphics rendering) and **SDL2** (for window management and input handling). These libraries may require system-level dependencies.

Consult the [skia-python](https://pypi.org/project/skia-python/) and [pysdl2](https://pysdl2.readthedocs.io/en/latest/install.html) web pages for more details.

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
python -m server_test

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

## Self-implemented:
(check commits with `extension` keyword)