
// 获取页面的文本内容
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

// 创建悬浮框
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

// 创建按钮
const button = document.createElement('button');
button.style.position = 'fixed';
button.style.bottom = '630px';
button.style.right = '30px';
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

// 将按钮添加到悬浮框中
floatingBox.appendChild(button);

// 将悬浮框添加到页面中
document.body.appendChild(button);

// 按钮点击事件
button.addEventListener('click', () => {
  var result = confirm("Sure to Ask Qwen to Remember this Page?");
  if (result) {
    cache_browser()
  }
});

let isDragging = false;
let initialX;
let initialY;

// 鼠标按下事件
button.addEventListener('mousedown', (e) => {
  isDragging = true;
  initialX = e.clientX;
  initialY = e.clientY;
});

// 鼠标移动事件
document.addEventListener('mousemove', (e) => {
  if (isDragging) {
    const dx = e.clientX - initialX;
    const dy = e.clientY - initialY;
    button.style.right = `${parseFloat(button.style.right) - dx}px`;
    button.style.bottom = `${parseFloat(button.style.bottom) - dy}px`;
    initialX = e.clientX;
    initialY = e.clientY;
  }
});

// 鼠标释放事件
document.addEventListener('mouseup', () => {
  isDragging = false;
});
