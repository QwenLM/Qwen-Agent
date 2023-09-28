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

})
