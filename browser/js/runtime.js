/**
 * Runtime code that runs before any user JS code
 */

/*
- We can call an exported Python function from JS using DukPy’s call_python function
  -> usage: call_python("<exported_function_name>", args)
- DukPy does not implement newer syntax like 'let', 'const', arrow functions, etc
  -> use "old-school" JS
- JS cannot directly access Python objects
  -> use handles
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
  }
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

Object.defineProperty(Node.prototype, "style", {
  set: function (s) {
    call_python("style_set", this.handle, s.toString());
  }
});

// ===== Global objects =====
console = {
  log: function (x) {
    call_python("print", x);
  }
};

document = {
  querySelectorAll: function (selector) {
    var handles = call_python("querySelectorAll", selector);
    return handles.map(function (handle) {
      return new Node(handle);
    });
  }
};

// ===== XMLHttpRequest =====

XHR_REQUESTS = {}; // Map handle to XMLHttpRequest

function XMLHttpRequest() {
  this.handle = Object.keys(XHR_REQUESTS).length;
  XHR_REQUESTS[this.handle] = this;
}

XMLHttpRequest.prototype.open = function (method, url, is_async) {
  this.method = method;
  this.url = url;
  this.is_async = is_async;
};

XMLHttpRequest.prototype.send = function (body) {
  this.responseText = call_python(
    "XMLHttpRequest_send",
    this.method,
    this.url,
    body,
    this.is_async,
    this.handle
  );
};

function __runXHROnload(body, handle) {
  var xhr_obj = XHR_REQUESTS[handle];
  xhr_obj.responseText = body;

  var event = new Event("load");
  if (xhr_obj.onload) {
    xhr_obj.onload(event);
  }
}

// ===== Timers =====
SET_TIMEOUT_REQUESTS = {}; // Map handle to callback functions

function setTimeout(callback, time_delta) {
  var handle = Object.keys(SET_TIMEOUT_REQUESTS).length;
  SET_TIMEOUT_REQUESTS[handle] = callback;
  call_python("setTimeout", handle, time_delta);
}

function __runSetTimeout(handle) {
  var callback = SET_TIMEOUT_REQUESTS[handle];
  callback();
}

// ===== Animation frame =====
RAF_LISTENERS = [];

/*
Schedule a rendering task;
Ask browser to call 'fn' at the beginning of that rendering task.
*/
function requestAnimationFrame(fn) {
  RAF_LISTENERS.push(fn);
  call_python("requestAnimationFrame");
}

function __runRAFHandlers() {
  // The callbacks can also call requestAnimationFrame()
  // -> Reset RAF_LISTENERS to [] before running callbacks
  //    to store callbacks for the next frame separately.
  var handlers_copy = RAF_LISTENERS;
  RAF_LISTENERS = [];
  for (var i = 0; i < handlers_copy.length; i++) {
    handlers_copy[i]();
  }
}
