(function(){

const params = new URLSearchParams(document.currentScript.src);
const clientId = params.get("client") || "default";

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

document.body.appendChild(btn);

btn.onclick = function(){
    window.open(`https://yourapp.onrender.com/chat?client=${clientId}`, "_blank");
};

})();
