
function getPageTextContent() {
  var textContent = document.body.textContent;
  return textContent;
}

function cache_browser(){
  const body = document.querySelector('html');
  const text = body.innerHTML;
  console.log(text);
  chrome.runtime.sendMessage({ data: text , close: true , flag: 'open_tab_and_cache_from_content', type: 'html'});

}

const floatingBox = document.createElement('div');
floatingBox.style.position = 'fixed';
floatingBox.style.bottom = '650px';
floatingBox.style.right = '60px';
floatingBox.style.width = '125px';
floatingBox.style.height = '55px';
floatingBox.style.backgroundColor = '#f2f2f2';
floatingBox.style.border = '1px solid black';
floatingBox.style.borderRadius = '5px';
floatingBox.style.padding = '10px';
floatingBox.style.zIndex = '9999';

const button = document.createElement('button');
button.style.position = 'fixed';
button.style.top = '30px';
button.style.right = '30px';
button.style.zIndex = "9999";
button.textContent = "Add to Qwen's Reading List";
button.style.fontFamily = 'Arial, sans-serif';
button.style.fontSize = '14px';
button.style.width = '140px';
button.style.height = '60px';
button.style.backgroundColor = '#695DE8';
button.style.color = 'white';
button.style.borderRadius = '5px';
button.style.border = '0px';
button.style.whiteSpace = 'pre-wrap';
button.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.2)';

floatingBox.appendChild(button);

document.body.appendChild(button);

let isDragging = false;
var isMouseReleased = false;
let initialX;
let initialY;

button.addEventListener('mousedown', (e) => {
  isDragging = true;
  initialX = e.clientX;
  initialY = e.clientY;
});

document.addEventListener('mousemove', (e) => {
  if (isDragging) {
    const dx = e.clientX - initialX;
    const dy = e.clientY - initialY;
    button.style.right = `${parseFloat(button.style.right) - dx}px`;
    button.style.top = `${parseFloat(button.style.top) + dy}px`;
    initialX = e.clientX;
    initialY = e.clientY;
    isMouseReleased = true;
  }
});

document.addEventListener('mouseup', (e) => {
  isDragging = false;

});

button.addEventListener('click', (e) => {
  if (isMouseReleased) {
    isMouseReleased = false;
    e.stopPropagation();
  } else {
    var result = confirm("Are you sure to ask Qwen to remember this page?");
    if (result) {
      cache_browser()
    }
  }
});
