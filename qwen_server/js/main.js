() => {
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

  document.addEventListener('change', function(event) {
    // Check if the changed element is a checkbox
    if (event.target.type === 'checkbox') {
      console.log(location.hostname);
      var _server_url = "http://" + location.hostname + ":7866/endpoint";
      fetch(_server_url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({'task': 'change_checkbox', 'ckid': event.target.id}),
      })
      .then((response) => response.json())
      .then((data) => {
        console.log(data.result);
      });
    }
  });
}
