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



chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    // if (msg.flag == 'from_content'){
    //   console.log(msg.rsp);
    //   var sessionContainer = document.getElementById('session');
    //   sessionContainer.innerText = msg.rsp;
    //   sendResponse({ msg: 'Get!' });
    // }
    if (msg.flag === 'from_llm'){
      // var sessionContainer = document.getElementById('session');
      // // sessionContainer.innerHTML = msg.rsp;
      // sessionContainer.innerText = msg.rsp;
      sendResponse({ message: 'Get Response!' });
    }
});


document.addEventListener('DOMContentLoaded', function() {
    chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
      var currentUrl = tabs[0].url;

      chrome.runtime.sendMessage({ data: currentUrl , close: true , flag: 'open_popup_and_send_url_from_popup'});

    });
    setTimeout(function() {
//        console.log('This message will be logged after 0.5 second');
        var popup_url='';
        chrome.storage.local.get(['database_host'], function(result) {
            if (result.database_host) {
                console.log('database_host currently is ' + result.database_host);
                popup_url = "http://"+result.database_host+":7863/";
            } else {
                popup_url = "http://127.0.0.1:7863/";
            }
            var iframe = document.createElement('iframe');
            iframe.src = popup_url;
            iframe.height = '570px';
//            iframe.sandbox = 'allow-same-origin allow-scripts';
//            iframe.allow = "geolocation *;";
            var iframe_area = document.getElementById('iframe_area')
            iframe_area.appendChild(iframe);

        });
    }, 500);

//    fetch('../config_host.json')
//      .then(response => response.json())
//      .then(data => {
//        console.log(data);
//        popup_url = "http://"+data.database_host+":"+data.app_in_browser_port+"/";
//        console.log(popup_url);
//    })
//    .catch(error => console.error('Error:', error));
})

document.getElementById('set_addr').addEventListener('click', function() {
    var addr = document.getElementById('addr').value;
    // save config
    chrome.storage.local.set({database_host: addr}, function() {
      console.log('database_host is set to ' + addr);
//      chrome.runtime.sendMessage({ data: addr , close: true , flag: 'set_addr'});
      document.getElementById('addr').value = '';
    });
})
