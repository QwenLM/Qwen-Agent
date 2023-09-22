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
