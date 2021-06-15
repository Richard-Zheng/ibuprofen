const hostUrl = `https://gzzxws.lexuewang.cn:8013`;
const statusDiv = document.getElementById("status")

async function imLogin(event) {
    let userID = document.getElementById("user-id").value
    let password = document.getElementById("user-password").value

    statusDiv.innerHTML = "当前状态：正在尝试登录..."
    user = login(userID)
    if (user == null) {
        statusDiv.innerHTML = "当前状态：登录遇到错误"
    }

    statusDiv.innerHTML = "当前状态：正在尝试连接消息系统..."
    let messageWaitUrl = hostUrl + `WaitResponse?clientid=myipad_${userID}&version=5.2.3.52303&enablehistroy=true&sessionid=${user.sessionid}&ssid=null&ip=null&alias=`
    let msgResponse = await fetch(messageWaitUrl)
    let reader = msgResponse.body.getReader()
    statusDiv.innerHTML = "当前状态：消息系统已连接"
    while (true) {
        console.log(Utf8ArrayToStr((await reader.read()).value))
    }
}

function Utf8ArrayToStr(array) {
    let out, i, len, c;
    let char2, char3;
    out = "";
    len = array.length;
    i = 0;
    while(i < len) {
        c = array[i++];
        switch(c >> 4)
        {
            case 0: case 1: case 2: case 3: case 4: case 5: case 6: case 7:
            // 0xxxxxxx
            out += String.fromCharCode(c);
            break;
            case 12: case 13:
            // 110x xxxx   10xx xxxx
            char2 = array[i++];
            out += String.fromCharCode(((c & 0x1F) << 6) | (char2 & 0x3F));
            break;
            case 14:
                // 1110 xxxx  10xx xxxx  10xx xxxx
                char2 = array[i++];
                char3 = array[i++];
                out += String.fromCharCode(((c & 0x0F) << 12) |
                    ((char2 & 0x3F) << 6) |
                    ((char3 & 0x3F) << 0));
                break;
        }
    }
    return out;
}
