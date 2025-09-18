1. 访问这个 获取 code
   curl -X POST 'http://gee.myds.me:8005/api/OfficialAccounts/OauthAuthorize' -H 'Accept: application/json' -H 'Content-Type: application/json' -H 'Cookie: wicgo=60021adba6859460e17110778e781717' -d '{
   "Appid": "wxe4a8657e84049860",
   "Url": "https://www.securityeb.com",
   "Wxid": "amaz1nglove"
   }'

获取 code {
"Code": 0,
"Success": true,
"Message": "成功",
"Data": {
"BaseResponse": {
"ret": 0,
"errMsg": {
"string": ""
}
},
"appname": "中国移动高频骚扰电话防护",
"appiconUrl": "http://wx.qlogo.cn/mmhead/Q3auHgzwzM7xc6RQQd7bib250KvqCaibB6NbhbNZ734oyMsbqEqb3IIQ/132",
"redirectUrl": "https://www.securityeb.com?code=071jMtFa18nsjK0sGlGa11tBro1jMtFj&state=123",
"isRecentHasAuth": true
},
"Data62": "",
"Debug": ""
}
提取 code=071jMtFa18nsjK0sGlGa11tBro1jMtFj code 得值;

2. 使用 curl -X GET 'https://www.securityeb.com/wechatService/wechatServ/getUserInfo?code=071jMtFa18nsjK0sGlGa11tBro1jMtFj' -H 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 19*0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x1800363a) NetType/WIFI Language/zh_CN' -H 'Accept: application/json, text/plain, */\_' -H 'Sec-Fetch-Site: same-origin' -H 'Sec-Fetch-Mode: cors' -H 'Referer: https://www.securityeb.com/?code=051vQH0002IdYU1Y8Q200b0Pjm4vQH0R&state=ebupt' -H 'Sec-Fetch-Dest: empty' -H 'Accept-Language: zh-CN,zh-Hans;q=0.9'  
   获取 openid 的值 {
   "code": 200,
   "msg": "查询成功",
   "data": {
   "openid": "oYXTH6I9ilba51LrU2ucVFXTQk9c",
   "nickname": null,
   "sex": null,
   "city": null,
   "country": null,
   "headimgurl": null,
   "privilege": null,
   "unionid": null
   }
   }

3. 然后发送验证码 curl -X POST 'https://www.securityeb.com/ktfsr/sms/send/sendCode' -H 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 19*0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x1800363a) NetType/WIFI Language/zh_CN' -H 'Accept: application/json, text/plain, */\_' -H 'Content-Type: application/json' -H 'Sec-Fetch-Site: same-origin' -H 'Accept-Language: zh-CN,zh-Hans;q=0.9' -H 'Sec-Fetch-Mode: cors' -H 'Origin: https://www.securityeb.com' -H 'Referer: https://www.securityeb.com/?code=051vQH0002IdYU1Y8Q200b0Pjm4vQH0R&state=ebupt' -H 'Sec-Fetch-Dest: empty' -d '{"userphone":"ByQ-9a5JC0NRsgzjwsZ1zQGS5_VGPXIJZ1Tp57RDpCw="}' --http1.1
   userphone 的加密就是 发送验证码的手机号 encrypt_phone 函数加密  
   返回 {"code":200,"msg":"请求成功"} 就是请求成功

4. 然后就可以获取验证码了 获取到验证码后, 进行登陆 curl -X POST 'https://www.securityeb.com/ktfsr/user/bind/ByQ-9a5JC0NRsgzjwsZ1zSM_Ie2xi5WXdEA8x3MGQKc=' -H 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 19*0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x1800363a) NetType/WIFI Language/zh_CN' -H 'Accept: application/json, text/plain, */\_' -H 'Content-Type: application/json' -H 'Sec-Fetch-Site: same-origin' -H 'Accept-Language: zh-CN,zh-Hans;q=0.9' -H 'Sec-Fetch-Mode: cors' -H 'Origin: https://www.securityeb.com' -H 'Referer: https://www.securityeb.com/?code=051vQH0002IdYU1Y8Q200b0Pjm4vQH0R&state=ebupt' -H 'Sec-Fetch-Dest: empty' -d '{"op_type":"1","code":"5VENZWdxud8NkUPBvfvXmLP7svImAjphVeD9m4X5_wk=","openid":"oYXTH6Gkqz-vn710nGpwbggJWDu0","seq":""}'
   code 就是验证码 使用 encrypt_phone 函数加密

返回 返回 {"code":200,"msg":"请求成功"} 就是登陆成功 就算绑定成功

配置说明:

- `config.json` 中的 `login.authorize_endpoint` 可修改为正确端口 (例如 8005)。
- `login.auto_sms` 支持椰子云自动取号/拉取验证码，需要填写 token 或用户名/密码以及项目 ID。
