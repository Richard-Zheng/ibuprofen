const hostUrl = `${window.location.protocol}//${window.location.host}`;
let userID = ""
let userGUID = ""

async function getAnswerSheet(element) {
    const resourceElement = element.parentElement
    const resourceGuid = resourceElement.dataset.guid
    let responseXML = await soapRequest("GetPrivateData2", {"lpszKey": `AnswerSheet_${resourceGuid}`})
    const data = JSON.parse(responseXML.getElementsByTagName("AS:szData")[0].innerHTML)
    let appendHtml = "<ul>"
    data.category.forEach((category) => {
        appendHtml += `<li>${category.name}<ul>`
        category.questions.forEach((question) => {
            appendHtml += `<li>${question.index}<input type="text" class="question-input" oninput="onQuestionInput(this)" onkeydown="onQuestionInputKeyDown(this, event)" data-type="${question.type}" data-correctanswer="${question.correctanswer}">(${question.score})</li>`
        })
        appendHtml += "</ul></li>"
    })
    appendHtml += "</ul><button onclick=\"checkAnswerLocally(this)\">Correct locally</button>"
    let newDiv = document.createElement("div")
    newDiv.innerHTML = appendHtml
    resourceElement.appendChild(newDiv)
}

function onQuestionInputKeyDown(inputElement, event) {
    switch (event.keyCode) {
        case 8: // BackSpace
            if (inputElement.value === "") {
                inputElement.parentElement.previousElementSibling.getElementsByClassName("question-input")[0].focus()
            }
            break
        case 13: // enter
            inputElement.parentElement.nextElementSibling.getElementsByClassName("question-input")[0].focus()
    }
}

function onQuestionInput(inputElement) {
    inputElement.value = inputElement.value.toUpperCase().replace(/[^a-zA-Z]/g,'')
    if (inputElement.value === "") {
        return
    }
    switch (inputElement.dataset.type) {
        case "1":
            inputElement.value = inputElement.value.charAt(inputElement.value.length-1)
            inputElement.parentElement.nextElementSibling.getElementsByClassName("question-input")[0].focus()
    }
}

function checkAnswerLocally(element) {
    let newNode;
    let questionElements = element.parentElement.getElementsByClassName("question-input")
    for (let questionElement of questionElements) {
        if (questionElement.value === "") {
            continue;
        }
        if (questionElement.value === questionElement.dataset.correctanswer) {
            newNode = document.createElement("span");
            newNode.innerHTML = `<span style="color: green">${questionElement.value}</span>`;
        } else {
            newNode = document.createElement("span");
            newNode.innerHTML = `<span style="color: red">${questionElement.value}</span> ${questionElement.dataset.correctanswer}`;
        }
        questionElement.parentElement.insertBefore(newNode, questionElement);
    }
}

function changeSubjectFilterAll(bool) {
    const items = document.getElementsByName("category");
    for (let i of items) {
        i.checked = bool
    }
    onSubjectCheckboxChange();
}

function onSubjectCheckboxChange() {
    const items = document.getElementsByName("category");
    let selector = "";
    for (let i of items) {
        if (!i.checked) {
            selector += `.lesson-schedule[data-subject='${i.value}'],`;
        }
    }
    selector = selector.slice(0,-1);

    let styleElement = document.getElementById('styles_filter');
    if (!styleElement) {
        styleElement = document.createElement('style');
        styleElement.type = 'text/css';
        styleElement.id = 'styles_filter';
        document.getElementsByTagName('head')[0].appendChild(styleElement);
    }
    styleElement.innerHTML = `${selector} {display: none;}`;
}