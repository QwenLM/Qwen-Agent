chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    // if (msg.flag == 'from_content'){
    //   console.log(msg.rsp);
    //   var sessionContainer = document.getElementById('session');
    //   sessionContainer.innerText = msg.rsp;
    //   // 发送响应消息
    //   sendResponse({ msg: 'Get!' });
    // }
    if (msg.flag === 'from_llm'){
      // var sessionContainer = document.getElementById('session');
      // // sessionContainer.innerHTML = msg.rsp;
      // sessionContainer.innerText = msg.rsp;
      // 发送响应消息
      sendResponse({ message: 'Get Response!' });
    }
});


// 当弹出窗口加载完成时触发
document.addEventListener('DOMContentLoaded', function() {
    chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
      var currentUrl = tabs[0].url;

      chrome.runtime.sendMessage({ data: currentUrl , close: true , flag: 'open_popup_and_send_url_from_popup'});

    });

})



// function pop_bot(query, url){
//   var sessionContainer = document.getElementById('session');
//   var input = document.createElement("input");
//   fetch('http://127.0.0.1:5000/get_data', {
//     method: 'POST',
//     headers: {
//       'Content-Type': 'application/json'
//     },
//     body: JSON.stringify({ 'content' : '', 'query': query, 'url':url })
//   })
//   .then(response => {
//     const reader = response.body.getReader();
//     return new ReadableStream({
//       start(controller) {
//         function push() {
//           reader.read().then(({ done, value }) => {
//             if (done) {
//               controller.close();
//               return;
//             }
//             controller.enqueue(value);
//             push();
//           });
//         }
//         push();
//       }
//     });
//   })
//   .then(stream => {
//     const reader = stream.getReader();
//     const decoder = new TextDecoder();
//     return new ReadableStream({
//       start(controller) {
//         function push() {
//           reader.read().then(({ done, value }) => {
//             if (done) {
//               controller.close();
//               return;
//             }
//             const text = decoder.decode(value);
//             sessionContainer.innerHTML += text;
//             console.log(text);
//             push();
//           });
//         }
//         push();
//       }
//     });
//   })
//   .catch(error => {
//     console.error('Error:', error);
//   });

// }


// 当弹出窗口加载完成时触发

// document.addEventListener('DOMContentLoaded', function() {
//     // 获取抓取按钮和内容容器的引用
//     var fetchButton = document.getElementById('fetchButton');
//     var fetchButton1 = document.getElementById('fetchButton1');
//     var fetchButton2 = document.getElementById('fetchButton2');

//     var contentContainer = document.getElementById('content');

//     // 当sumarize按钮被点击时触发
//     fetchButton.addEventListener('click', function() {
//       chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
//         var tabId = tabs[0].id;
//         var url = tabs[0].url;
//         // chrome.runtime.sendMessage({ data: "summarize" , close: true , flag: "from_user"});
//         pop_bot("summarize", url)
//         // chrome.tabs.sendMessage(tabId, {flag: "get_page_from_pop"}, function(response) {
//         //   console.log(response);　　// 向content-script.js发送请求信息
//         // });
//       });
//     });
//     fetchButton1.addEventListener('click', function() {
//       chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
//         var tabId = tabs[0].id;
//         var url = tabs[0].url;
//         // chrome.runtime.sendMessage({ data: "idea" , close: true , flag: "from_user"});
//         pop_bot("idea", url)
//         // chrome.tabs.sendMessage(tabId, {flag: "get_page_from_pop"}, function(response) {
//         //   console.log(response);　　// 向content-script.js发送请求信息
//         // });
//       });
//     });
//     fetchButton2.addEventListener('click', function() {
//       chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
//         var tabId = tabs[0].id;
//         var url = tabs[0].url;
//         // chrome.runtime.sendMessage({ data: "title" , close: true , flag: "from_user"});
//         pop_bot("title", url)
//         // chrome.tabs.sendMessage(tabId, {flag: "get_page_from_pop"}, function(response) {
//         //   console.log(response);　　// 向content-script.js发送请求信息
//         // });
//       });
//     });

//     var uploadButton = document.getElementById('uploadFileBtn');
//     var uploadContainer = document.getElementById('uploadFile');
//     // 当submit按钮被点击时触发
//     uploadButton.addEventListener('click', function() {
//       chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
//         var tabId = tabs[0].id;
//         var url = tabs[0].url;
//         // contentContainer.innerText = url;
//         const text = uploadContainer.value;
//         // chrome.runtime.sendMessage({ data: text , nowtab: url, close: true , flag: "from_user"});
//         pop_bot(text, url)
//       });
//     });


//     var copyButton = document.getElementById('copyButton');
//     // 当sumarize按钮被点击时触发
//     copyButton.addEventListener('click', function() {
//       var divContent = document.getElementById("session").innerText;
//       // divContent.select();
//       var tempInput = document.createElement("input");
//       tempInput.value = divContent;
//       document.body.appendChild(tempInput);
//       tempInput.select();
//       document.execCommand("copy");
//       document.body.removeChild(tempInput);
//     });

// });
