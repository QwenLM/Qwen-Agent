/* 
Copyright 2023 The Qwen team, Alibaba Group. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

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
