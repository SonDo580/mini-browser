/**
 * Runtime code that runs before any user JS code
 */

/*
- We can call an exported Python function from JS using DukPy’s call_python function
  -> usage: call_python("<exported_function_name>", args)
- DukPy does not implement newer syntax like 'let', 'const', arrow functions, etc
  -> use "old-school" JS
- JS cannot directly access Python objects
  -> use handles.
*/

// ===== Node =====
function Node(handle) {
  this.handle = handle;
}

Node.prototype.getAttribute = function (attribute) {
  return call_python("getAttribute", this.handle, attribute);
};

Object.defineProperty(Node.prototype, "innerHTML", {
  set: function (s) {
    call_python("innerHTML_set", this.handle, s.toString());
  },
});

// ===== Event handling =====
function Event(type) {
  this.type = type;
  this.doDefault = true;
}

Event.prototype.preventDefault = function () {
  this.doDefault = false;
};

LISTENERS = {}; // Map handle -> event type -> array of callback functions

Node.prototype.addEventListener = function (eventType, listener) {
  if (!LISTENERS[this.handle]) {
    LISTENERS[this.handle] = {};
  }

  if (!LISTENERS[this.handle][eventType]) {
    LISTENERS[this.handle][eventType] = [];
  }

  LISTENERS[this.handle][eventType].push(listener);
};

Node.prototype.dispatchEvent = function (event) {
  var eventType = event.type;
  var handle = this.handle;
  var listeners = (LISTENERS[handle] && LISTENERS[handle][eventType]) || [];

  // Execute each listener with 'this' bound to the current element
  for (var i = 0; i < listeners.length; i++) {
    listeners[i].call(this, event);
  }

  return event.doDefault;
};

// ===== Global objects =====
console = {
  log: function (x) {
    call_python("print", x);
  },
};

document = {
  querySelectorAll: function (selector) {
    var handles = call_python("querySelectorAll", selector);
    return handles.map(function (handle) {
      return new Node(handle);
    });
  },
};

// ===== XMLHttpRequest =====
function XMLHttpRequest() {}

XMLHttpRequest.prototype.open = function (method, url, is_async) {
  if (is_async) {
    throw new Error("Asynchronous XHR is not supported");
  }
  this.method = method;
  this.url = url;
};

XMLHttpRequest.prototype.send = function (body) {
  this.responseText = call_python(
    "XMLHttpRequest_send",
    this.method,
    this.url,
    body
  );
};
