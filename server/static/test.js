var input = document.querySelectorAll("input")[0];
var form = document.querySelectorAll("form")[0];
var warning = document.querySelectorAll("strong")[0];

function lengthCheck(input) {
  var value = input.getAttribute("value");
  var allow_submit = value.length <= 50;
  if (!allow_submit) {
    warning.innerHTML = "Comment is too long!";
  } else {
    warning.innerHTML = "";
  }
  return allow_submit;
}

input.addEventListener("keydown", function (e) {
  lengthCheck(input);
});

form.addEventListener("submit", function (e) {
  allow_submit = lengthCheck(input);
  if (!allow_submit) {
    e.preventDefault();
  }
});
