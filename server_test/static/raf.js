var count = 0;
var output = document.querySelectorAll("div")[1];

function callback() {
  output.innerHTML = "count: " + count;
  count = count + 1;
  if (count < 100) {
    requestAnimationFrame(callback);
  }
}

requestAnimationFrame(callback);
