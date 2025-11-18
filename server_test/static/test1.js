// Test async XHR
console.log("Starting async XHR...");
var async_xhr = new XMLHttpRequest();
async_xhr.open("GET", "/static/test.js", true); // async = true
async_xhr.onload = function () {
  console.log("[async] onload fired!");
  console.log("[async] response length = " + this.responseText.length);
};
async_xhr.send();
console.log("[async] should appear before [async] onload fired!");

// Test sync XHR
console.log("Starting sync XHR...");
var sync_xhr = new XMLHttpRequest();
sync_xhr.open("GET", "/static/test.js", false); // async = false
sync_xhr.onload = function () {
  console.log("[sync] onload fired!");
  console.log("[sync] response length = " + this.responseText.length);
};
sync_xhr.send();
console.log("[sync] should appear after [sync] onload fired!");
