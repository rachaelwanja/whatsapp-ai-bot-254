(function(){

let btn = document.createElement("button");
btn.innerHTML = "💬";
btn.style.position = "fixed";
btn.style.bottom = "20px";
btn.style.right = "20px";
btn.style.background = "#25D366";
btn.style.color = "white";
btn.style.borderRadius = "50%";
btn.style.width = "60px";
btn.style.height = "60px";
btn.style.border = "none";
btn.style.cursor = "pointer";

document.body.appendChild(btn);

btn.onclick = function(){
    window.open("https://YOUR-RENDER-URL/chat", "_blank");
};

})();
