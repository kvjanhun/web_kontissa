document.addEventListener("DOMContentLoaded", function () {
    const commandText = "cowsay moo";
    const commandElem = document.getElementById("command");
    const outputElem = document.getElementById("output");

    function addNewPromptLine() {
        const terminalBody = document.getElementById("terminal_body");
      
        const newLine = document.createElement("div");
        newLine.classList.add("line");
      
        newLine.innerHTML = `
          <span class="terminal_prompt">
            <span id="user">konsta@erez.ac</span>
            <span>:</span>
            <span id="dir">~</span>
            <span id="bling">$</span>
            <span id="cursor"></span>
          </span>
        `;
      
        terminalBody.appendChild(newLine);
    }
    
    function fetchCowsay() {
        fetch("/api/cowsay")
            .then((res) => res.json())
            .then((data) => {
            outputElem.textContent = data.output;
            addNewPromptLine();
            });
        }

    let i = 0;
    function typeCommand() {
        if (i < commandText.length) {
            commandElem.textContent += commandText[i];
            i++;
            setTimeout(typeCommand, 80); // typing speed
        } else {
            setTimeout(fetchCowsay, 100); // short pause after typing
        }
    }  
    
    setTimeout(() => {
        typeCommand();
    }, 3000); // delay before command typing starts
});
