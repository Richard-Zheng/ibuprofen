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
    return soapRequestWithUrl(action, params, "wmexam/wmstudyservice.WSDL")
}

async function soapRequestWithUrl(action, params, wsdlUrl) {
    let response = await fetch(wsdlUrl, {
        method: 'POST',
        headers: {
            "SOAPAction": `http://webservice.myi.cn/wmstudyservice/wsdl/${action}`,
            "Content-type": "text/xml;charset=utf-8",
        },
        body: getSoapRequestBody(action, params),
    })
    return new window.DOMParser().parseFromString(await response.text(), "text/xml")
}
