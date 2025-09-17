椰子云 api 接口文档:

如果不能复制请更换浏览器或者下载文档查看：点击下载 api 文档
主域名:http://api.sqhyw.net:90
备用域名:http://api.nnanx.com:90
注意：对服务器的所有请求及返回的请求，编码都为 UTF-8 请解码后处理，请求方式为 GET 1.用户注册接口 老有人输错接口 注意 后面是 logins 不是 login 2.返回的 token 虽然每次都会变，但是不修改密码 之前任意一次返回的 token 都可以一直使用,不用每次都获取
3.login 是测试接口,返回的 token 是无效的
4.X 是示例，具体参数请自行替换 5.返回的参数中 “1 分钟内剩余取卡数” 必须处理在小于 10 时 停止请求,否则拉黑 IP 需要 1 个小时才释放 6.指定取卡时请填写专属的对接码【例：12585----xxxx】 7.易语言的解码方式不能直接 url 解码，例子：utf8 到 gb2312

Api 支持功能如下： 1.登录 2.获取余额 3.取卡 4.获取短信 5.释放号码 6.拉黑号码 7.获取已对接专属 8.重新对接

---

1.登录：
请求 URL：
http://api.sqhyw.net:90/api/logins
请求示例主域名:http://api.sqhyw.net:90/api/logins?username=zzzxxx&password=xxxxx
备用域名:http://api.nnanx.com:90/api/logins?username=zzzxxx&password=xxxxx
请求方式：GET

参数示例：
参数名必选类型说明 username 是 string 用户名 password 是 string 密码

返回示例:
{
"token": "mhLO3K8DPMg5L/kkXWBpnemaI6D8iU6Nlz+LciAbi8ZRzFgdxK1UYN4BGSR3w5O0dQM+SASLQVJmof5NJ8LtT4/+YoXpXDtnjpwMFirlGJwjlx3sMLPLaa1M5y",
"data": [{
"money": "300",
"money_1": "0.0000",
"id": "10000",
"leixing": "用户"
}]
}
返回参数说明：
参数名类型 说明 token 文本后续请求所需要的 money 文本余额 id 文本你的用户 ID

---

2.用户获取余额:
请求 URL：
http://api.sqhyw.net:90/api/get_myinfo
请求示例主域名:http://api.sqhyw.net:90/api/get_myinfo?token=xxxxxxx
备用域名:http://api.nnanx.com:90/api/get_myinfo?token=xxxxxxx
请求方式：GET

参数示例：
参数名必选类型说明 token 是 string 登录返回的 token

返回示例：
{
"message": "ok",
"data": [{
"money": "179.6000",
"money_1": "0.0000"
}]
}

返回参数说明：
参数名类型说明 moneyString 余额

---

3.用户取卡接口:
请求 URL：
http://api.sqhyw.net:90/api/get_mobile
普通取卡例子:http://api.sqhyw.net:90/api/get_mobile?token=你的token&project_id=项目ID
专属取卡例子:http://api.sqhyw.net:90/api/get_mobile?token=你的token&project_id=专属项目对接码
从账户所有专属随机取卡例子:http://api.sqhyw.net:90/api/get_mobile?token=你的token&project_id=项目ID&special=1
从普通项目和专属对接码指定取卡例子:http://api.sqhyw.net:90/api/get_mobile?token=你的token&project_id=项目ID&phone_num=要取的指定号码
从账户所有专属随机指定取卡例子:http://api.sqhyw.net:90/api/get_mobile?token=你的token&project_id=项目ID&special=1&phone_num=要取的指定号码
指定号段取卡例子:http://api.sqhyw.net:90/api/get_mobile?token=你的token&project_id=项目ID&scope=170(最多支持前5位)
请求方式：GET
参数示例：
参数名必选类型说明 token 是 string 登录返回的 tokenproject_id 是 string 项目 ID;普通项目填普通项目的 ID，专属类型也可以填写专属项目的对接码【例：12585----xxxx】special 是 string 从专属取卡：special=1，不加这个参数取普通项目的卡 注意：此参数只有项目 id 是普通项目的时候才可以 loop 否 string 是否过滤项目 1 过滤 2 不过滤 默认不过滤 operator 否 string 运营商 (0=默认 1=移动 2=联通 3=电信 4=实卡 5=虚卡) 可空 phone_num 否 string 指定取号的话 这里填要取的手机号 scope 否 string 指定号段 最多支持号码前 5 位. 例如可以为 165，也可以为 16511address 否 string 归属地选择 例如 湖北 甘肃 不需要带省字 api_id 否 string 如果是开发者,此处填写你的用户 ID 才有收益，注意是用户 ID 不是登录账号 scope_black 否 string 排除号段最长支持 7 位且可以支持多个,最多支持 20 个号段。用逗号分隔 比如 150,1511111,15522creat_time 否 string 输入整数,单位/天,用来过滤上线时间的机器.比如输入 7,那么获取到的手机号最少上线了 7 天，范围 1-60designatedID=否 string 指定卡商 id

返回示例：
{
"message": "ok",
"mobile": "16532643928",
"data": [],
"1 分钟内剩余取卡数": "298"}

返回参数说明：
参数名类型说明 messageString 结果提示 mobileString 手机号 1 分钟内剩余取卡数 String 剩余取卡数如果小于 10 时 停止请求,否则拉黑 IP 需要 1 个小时才释放

---

4.用户获取短信:
请求 URL：
http://api.sqhyw.net:90/api/get_message
请求示例主域名:http://api.sqhyw.net:90/api/get_message?token=你的token&project_id=项目ID&phone_num=取卡返回的手机号
备用域名:http://api.nnanx.com:90/api/get_message?token=你的token&project_id=项目ID&phone_num=取卡返回的手机号

请求方式：GET
参数示例：
参数名必选类型说明 token 是 string 登录返回的 tokenproject_id 是 string 项目 ID;普通项目填普通项目的 ID，专属类型也可以填写专属项目的对接码【例：12585----xxxx】special 否 string 如果取卡时调用了此参数，这里必须要填 special=1，否则获取不到短信 phone_num 是 stringget_mobile 取卡接口返回的手机号
短信如果还没到返回实例,返回这个请继续请求：
{
"message": "ok",
"data": []
}
短信到达返回实例：
{
"message": "ok",
"code": "807272",
"data": [{
"project_id": "10079",
"modle": "【酷狗音乐】您的登录验证码 807272。如非本人操作，请不要把验证码泄露给任何人。",
"phone": "16532645760",
"project_type": "1"
}]
}
返回参数说明：
参数名类型说明 codeString 验证码 modleString 短信完整内容 project_idString 项目 IDproject_typeString 项目类型

---

5.用户释放号码：
请求 URL：
http://api.sqhyw.net:90/api/free_mobile
请求示例主域名:http://api.sqhyw.net:90/api/free_mobile
备用域名:http://api.nnanx.com:90/api/free_mobile

取号后请等待至少 200 秒以上再释放，释放过早会因为信号等其他原因导致验证码延迟，而收不到短信，而且过早释放并不会释放取号数量!!!

请求方式：GET
参数示例：
参数名必选类型说明 token 是 string 登录返回的 tokenproject_id 否 string 普通项目填普通项目的 ID，专属类型也可以填写专属项目的对接码【例：12585----xxxx】special 否 string 如果取卡时调用了此参数，这里必须要填 special=1，否则不能释放号码 phone_num 否 stringget_mobile 取卡接口返回的手机号

返回示例：
{
"message": "ok",
"data": []
}
返回参数说明：
参数名类型说明 messagString 返回结果,请求成功返回 ok

备注：
释放所有号码:http://api.sqhyw.net:90/api/free_mobile?token=xxxxx;
释放指定号码:http://api.sqhyw.net:90/api/free_mobile?token=xxxxx&phone_num=xxxxx
释放号码的指定项目:http://api.sqhyw.net:90/api/free_mobile?token=xxxxx&phone_num=xxxxx&project_id=xxxx&project_type=X
-- X 是示例，具体参数请自行替换

---

6.用户拉黑号码：
请求 URL：
http://api.sqhyw.net:90/api/add_blacklist
请求示例主域名:http://api.sqhyw.net:90/api/add_blacklist?token=你的token&project_id=拉黑的项目ID&phone_num=拉黑的号码
备用域名:http://api.nnanx.com:90/api/add_blacklist?token=你的token&project_id=拉黑的项目ID&phone_num=拉黑的号码
请求方式：GET
参数示例：
参数名必选类型说明 token 是 string 登录返回的 tokenproject_id 是 string 普通项目填普通项目的 ID，专属类型也可以填写专属项目的对接码【例：12585----xxxx】special 否 string 如果取卡时调用了此参数，这里必须要填 special=1，否则拉黑不了号码 phone_num 是 stringget_mobile 取卡接口返回的手机号

返回示例：
{
"message": "ok",
"data": []
}
返回参数说明：
参数名类型说明 messageString 返回结果,请求成功返回 ok

---

7.获取已对接专属：
请求 URL：
http://api.sqhyw.net:90/api/get_join
请求示例主域名:http://api.sqhyw.net:90/api/get_join
备用域名http://api.nnanx.com:90/api/get_join
请求方式：GET
参数示例：
参数名必选类型说明 token 是 string 登录返回的 token

返回示例：
{"message":"ok","data":[{"id":"2482069","user_id":"56495","project_id":"37600","price":"0.22","key_":"37600----E02IZ0","service_price":"0.20","state":"0","keyword":"比心","user_count":"37","name":"比心","old_price":"0.2200","已用":"4","在线":"550","卡类型":"实卡"},{"id":"1865795","user_id":"212266","project_id":"10699","price":"4.40","key_":"10699----5419W7","service_price":"4.00","state":"0","keyword":"酷狗直播","user_count":"1","name":"酷狗直播","old_price":"4.4000","已用":"0","在线":"63","卡类型":"实卡"},{"id":"2525085","user_id":"27373","project_id":"10699","price":"0.60","key_":"10699----EX6SHY","service_price":"0.55","state":"0","keyword":"酷狗直播","user_count":"17","name":"酷狗直播","old_price":"0.6000","已用":"231","在线":"1357","卡类型":"实卡"},{"id":"3362925","user_id":"2","project_id":"98289","price":"0.33","key_":"98289----8Z29DA","service_price":"0.30","state":"0","keyword":"正弘物业","user_count":"1","name":"正弘物业","old_price":"0.3300","已用":"0","在线":"107","卡类型":"混合号段"},{"id":"4790588","user_id":"314109","project_id":"10649","price":"0.13","key_":"10649----6DD292","service_price":"0.12","state":"0","keyword":"一鸣食品","user_count":"0","name":"一鸣食品","old_price":"0.1300","已用":"115","在线":"1379","卡类型":"实卡"},{"id":"3671974","user_id":"241297","project_id":"10079","price":"0.16","key_":"10079----SG577E","service_price":"0.15","state":"0","keyword":"酷狗音乐","user_count":"11","name":"酷狗音乐","old_price":"0.1600","已用":"5","在线":"206","卡类型":"虚卡"},{"id":"4877676","user_id":"314109","project_id":"25486","price":"0.44","key_":"25486----0H048C","service_price":"0.40","state":"0","keyword":"初心互动","user_count":"20","name":"初心互动","old_price":"0.4400","已用":"1087","在线":"1379","卡类型":"实卡"},{"id":"4719047","user_id":"314109","project_id":"10404","price":"1.87","key_":"10404----7QLJKX","service_price":"1.70","state":"0","keyword":"虎牙科技","user_count":"17","name":"虎牙科技","old_price":"1.8700","已用":"90","在线":"1379","卡类型":"实卡"}]}

返回参数说明：
参数名类型说明 idString 专属项目 IDkey_String 专属对接码 priceString 专属的价格 old_priceString 你对接时专属的价格,如果 old_price 不等于 price ,说明专属需要重新对接 user_IdString 卡商的 ID

---

8.重新对接：
请求 URL：
http://api.sqhyw.net:90/api/sub_join
请求示例主域名:http://api.sqhyw.net:90/api/sub_join
备用域名:http://api.nnanx.com:90/api/sub_join
请求方式：GET
参数示例：
参数名必选类型说明 token 是 string 登录返回的 tokenkey\_是 string 需要重新对接的专属对接码 或是专属 ID

返回示例：
{
"message": "ok",
"data": []
}

返回参数说明：
参数名类型说明 messageString 返回结果,请求成功返回 ok

重新对接: http://api.sqhyw.net:90/api/sub_join?token=xxxxx&key_=专属对接码
X 是示例，具体参数请自行替换
