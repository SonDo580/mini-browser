# Mini browser

A simple web browser

## Book

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

This project depends on **Skia** _(for 2D graphics rendering)_ and **SDL2** _(for window management and input handling)_. These libraries may require system-level dependencies.

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

## My extensions

- **project structure**: not officially provided by the authors, just try to use a "reasonable" organization.
- **user interactions**:
  - scroll up with `arrow up` key.
  - allow deleting characters when editing tab url & form input.
- **CSS**:
  - transparency & more color formats.
- **render & display**:
  - hidden input & password masking.
  - draw rounded rectangle.
