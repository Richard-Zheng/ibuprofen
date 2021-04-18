const hostUrl = `${window.location.protocol}//${window.location.host}`;
let userID = ""
let userGUID = ""

function getSoapRequestBody(action, params) {
    let res = `<v:Envelope xmlns:v="http://schemas.xmlsoap.org/soap/envelope/" xmlns:i="http://www.w3.org/2001/XMLSchema-instance" xmlns:d="http://www.w3.org/2001/XMLSchema" xmlns:c="http://schemas.xmlsoap.org/soap/encoding/">
    <v:Header/>
    <v:Body>
        <${action} xmlns="http://webservice.myi.cn/wmstudyservice/wsdl/" id="o0" c:root="1">`;
    for (let key in params) {
        res += `
            <${key} i:type="d:${typeof params[key]}">${params[key]}</${key}>`
    }
    res += `
        </${action}>
    </v:Body></v:Envelope>`;
    return res;
}

async function soapRequest(action, params) {
    let response = await fetch(hostUrl + "/wmexam/wmstudyservice.WSDL", {
        method: 'POST',
        headers: {
            "SOAPAction": `http://webservice.myi.cn/wmstudyservice/wsdl/${action}`,
            "Content-type": "text/xml;charset=utf-8",
        },
        body: getSoapRequestBody(action, params),
    })
    return new window.DOMParser().parseFromString(await response.text(), "text/xml")
}

async function login() {
    userID = document.getElementById("user-id").value
    try {
        let responseXml = await soapRequest("UsersGetUserGUID", {"lpszUserName": userID})
        userGUID = responseXml.getElementsByTagName("AS:szUserGUID")[0].innerHTML
    } catch (e) {
        alert(e)
    }
}

async function getAnswerSheet(element) {
    const resourceElement = element.parentElement
    const resourceGuid = resourceElement.dataset.guid
    let responseXML = await soapRequest("GetPrivateData2", {"lpszKey": `AnswerSheet_${resourceGuid}`})
    const data = JSON.parse(responseXML.getElementsByTagName("AS:szData")[0].innerHTML)
    let appendHtml = "<ul>"
    data.category.forEach((category) => {
        appendHtml += `<li>${category.name}<ul>`
        category.questions.forEach((question) => {
            appendHtml += `<li>${question.index}<input type="text" class="question-input" oninput="onQuestionInput(this)" data-type="${question.type}" data-correctanswer="${question.correctanswer}">(${question.score})</li>`
        })
        appendHtml += "</ul></li>"
    })
    appendHtml += "</ul><button onclick=\"checkAnswerLocally(this)\">Correct locally</button>"
    let newDiv = document.createElement("div")
    newDiv.innerHTML = appendHtml
    resourceElement.appendChild(newDiv)
}

function onQuestionInput(inputElement) {
    inputElement.value = inputElement.value.toUpperCase().replace(/[^a-zA-Z]/g,'')
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