var database;

function send_data(msg){
    chrome.storage.local.get(['database_host'], function(result) {
        if (result.database_host) {
            console.log('database_host currently is ' + result.database_host);
            database = "http://"+result.database_host+":7866/endpoint";
        } else {
            database = "http://127.0.0.1:7866/endpoint";
        }
        fetch(database, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(msg),
        })
          .then((response) => response.json())
          .then((data) => {
            console.log(data.result);
          });
     });
}

chrome.runtime.onMessage.addListener(async (msg, sender) => {
  if (msg.flag == "open_tab_and_cache_from_content"){
    var url = "";
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      url = tabs[0].url;
      console.log(url);
      if (msg.data) {
        chrome.storage.sync.get(['data'], function(result) {
          chrome.storage.sync.set({ data: result.data }, function() {
            send_data({ 'content' : msg.data, 'query': '', 'url':url, 'task':'cache', 'type':msg.type});
          });
        });
      }
    });
  }
  if (msg.flag == "open_popup_and_send_url_from_popup"){
    if (msg.data) {
      chrome.storage.sync.get(['data'], function(result) {
        chrome.storage.sync.set({ data: result.data }, function() {
            send_data({ 'url' : msg.data, 'task':'pop_url'});
        });
      });
    }
  }
//  if (msg.flag == "set_addr"){
//    if (msg.data) {
//      chrome.storage.sync.get(['data'], function(result) {
//        chrome.storage.sync.set({ data: result.data }, function() {
//            send_data({ 'addr' : msg.data, 'task':'set_addr'});
//        });
//      });
//    }
//  }
});
