const CryptoJS = require('crypto-js')

function encrypt_phone(e) {
    const r = CryptoJS.enc.Utf8.parse("ebupt_1234567890")
    const a = CryptoJS.enc.Utf8.parse("1234567890123456")
    e = e + "$" + (new Date).getTime()
    var t = CryptoJS.enc.Utf8.parse(e)
        , n = CryptoJS.AES.encrypt(t, r, {
            iv: a,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        })
    return n = (n = CryptoJS.enc.Base64.stringify(n.ciphertext)).replace(/\//g, "_").replace(/\+/g, "-")
}

function encrypt_sign(e) {
    const r = CryptoJS.enc.Utf8.parse("ebupt_1234567890")
    const a = CryptoJS.enc.Utf8.parse("1234567890123456")
    e += "91Bmzn$0$#brkNYX"
    var t = CryptoJS.enc.Utf8.parse(e)
        , n = CryptoJS.AES.encrypt(t, r, {
            iv: a,
            mode: CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7
        })
    return CryptoJS.enc.Base64.stringify(n.ciphertext)
}


var e = {
    "openid": "oYXTH6Gkqz-vn710nGpwbggJWDu0",
    "plea_type": "2",
    "plea_phone": "2H16NTIwlqM5prlDIpsGv9mW5zB_osxJauguAks8tW8=",
    "company_id": "91410100MA44X4F98J",
    "company_name": "郑州创万瑞酒店管理有限公司",
    "plea_reason": "公司最近刚拿下的号码段,需要去掉历史标记.与当前业务场景不符合.希望可以尽快处理.感谢.已经严重影响公司业务正常运行.",
    "filename": "20250917/0804_20250917105600412.jpg"
}
e.sign = encrypt_sign(e.openid + e.plea_type + e.plea_phone + e.company_id + e.company_name + e.plea_reason + e.filename)

// console.log(e)


// AES key/iv 与前端保持一致
const KEY = CryptoJS.enc.Utf8.parse('ebupt_1234567890')
const IV = CryptoJS.enc.Utf8.parse('1234567890123456')
// 解密由 encryptPhone 生成的密文，返回明文手机号
function decryptPhone(enc) {
    if (!enc) return ''
    // 还原 Base64 字符
    let b64 = enc.replace(/_/g, '/').replace(/-/g, '+')
    // 若外部去掉了填充，这里尝试补齐（encryptPhone 默认保留 '=')
    const pad = b64.length % 4
    if (pad === 2) b64 += '=='
    else if (pad === 3) b64 += '='
    else if (pad === 1) b64 += '==='

    const ciphertext = CryptoJS.enc.Base64.parse(b64)
    const cipherParams = CryptoJS.lib.CipherParams.create({ ciphertext })
    const decrypted = CryptoJS.AES.decrypt(cipherParams, KEY, { iv: IV, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 })
    const plaintext = CryptoJS.enc.Utf8.stringify(decrypted)
    // 明文格式：phone$timestamp
    console.log(plaintext)

    const idx = plaintext.lastIndexOf('$')
    return idx === -1 ? plaintext : plaintext.slice(0, idx)
}

console.log(decryptPhone("VjGm2Ag9MNEW21P_1Kpt3fOnukICKOIlIFJZ4UIN6no="))
