window.onload = function() {
  // autoTriggerFunction();
};

function autoTriggerFunction() {
  var button = document.getElementById("update_all_bt");
  button.click();
}

// const textbox = document.querySelector('#cmd label textarea');

// textbox.addEventListener('input', () => {
//   textbox.scrollTop = textbox.scrollHeight;
//   console.log('input');
// });
// textbox.addEventListener('change', () => {
//   textbox.scrollTop = textbox.scrollHeight;
//   console.log('change');
// });

function scrollTextboxToBottom() {
  var textbox = document.querySelector('.textbox_container label textarea');
  textbox.scrollTop = textbox.scrollHeight*10;
}
window.addEventListener('DOMContentLoaded', scrollTextboxToBottom);


var checkboxes = document.querySelectorAll('input[type="checkbox"]');
checkboxes.forEach(function(checkbox) {
  checkbox.addEventListener("change", function() {
    fetch("http://127.0.0.1:7866/endpoint", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({'task': 'change_checkbox', 'ckid': checkbox.id}),
    })
    .then((response) => response.json())
    .then((data) => {
      console.log(data.result)
    });
  });
});
