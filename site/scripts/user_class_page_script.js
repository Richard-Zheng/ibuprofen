const hostUrl = `${window.location.protocol}//${window.location.host}`;

function getSoapRequestBody(action, params) {
    var res = `<v:Envelope xmlns:v="http://schemas.xmlsoap.org/soap/envelope/" xmlns:i="http://www.w3.org/2001/XMLSchema-instance" xmlns:d="http://www.w3.org/2001/XMLSchema" xmlns:c="http://schemas.xmlsoap.org/soap/encoding/">
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

function getSoapRequest(action, params, onload) {
    let xhr = new XMLHttpRequest();
    xhr.open("POST", hostUrl + "/wmexam/wmstudyservice.WSDL");
    xhr.setRequestHeader('SOAPAction', `http://webservice.myi.cn/wmstudyservice/wsdl/${action}`);
    xhr.setRequestHeader('Content-Type', 'text/xml;charset=utf-8');
    xhr.responseType = "document";
    xhr.addEventListener("load", onload);
    xhr.send(getSoapRequestBody(action, params));
    return xhr;
}

function getSubmitAnswerRequest(questionGuid, answer, onload) {
    let xhr = new XMLHttpRequest();
    xhr.open("POST", hostUrl + "/restfuldatasource/answersheetstudentanswer/" + questionGuid);
    xhr.setRequestHeader('Content-Type', 'application/json;charset=UTF-8');
    xhr.addEventListener("load", onload);
    xhr.send(JSON.stringify(answer));
    return xhr
}

function login() {
    let userId = document.getElementById("user-id").value;
    let xhr = getSoapRequest("UsersGetUserGUID", {"lpszUserName": userId}, () => {
        let userGuid = xhr.responseXML.getElementsByTagName("AS:szUserGUID")[0].innerHTML;
        alert("Login successful " + userGuid);
        document.cookie = `szUserName=${userId};`;
        document.cookie = `szUserGUID=${userGuid};`;
    });
}

function getAnswerSheet(element) {
    const resourceElement = element.parentElement;
    const resourceGuid = resourceElement.dataset.guid;
    const xhr = getSoapRequest("GetPrivateData2", {"lpszKey": `AnswerSheet_${resourceGuid}`}, () => {
        const data = JSON.parse(xhr.responseXML.getElementsByTagName("AS:szData")[0].innerHTML);
        let appendHtml = "<ul>";
        data.category.forEach((category) => {
            appendHtml += `<li>${category.name}<ul>`
            category.questions.forEach((question) => {
                appendHtml += `<li>${question.index}<input type="text" class="question-input" data-guid="${question.guid}" data-correctanswer="${question.correctanswer}">(${question.score})</li>`;
            })
            appendHtml += "</ul></li>";
        });
        appendHtml += "</ul><button onclick=\"checkAnswerLocally(this)\">Correct locally</button><button onclick=\"submitAnswer(this)\">Submit</button>"
        let newDiv = document.createElement("div");
        newDiv.innerHTML = appendHtml;
        resourceElement.appendChild(newDiv);
    });
}

function submitAnswer(button) {
    let questionInputs = button.parentElement.getElementsByClassName("question-input")
    for (let questionInput of questionInputs) {
        if (questionInput.value === "") {
            continue;
        }
        let xhr = getSubmitAnswerRequest(questionInput.dataset.guid, {"answerchoice":questionInput.value}, () => {
            console.log(xhr.status)
        })
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