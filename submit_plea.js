// 说明：
// 基于前端逻辑的 Node.js 脚本，完成：
// 1) 生成 filename（YYYYMMDD/后四位_YYYYMMDDHHmmssSSS.ext）
// 2) AES-CBC-PKCS7 加密手机为 plea_phone（Base64，/→_，+→-）
// 3) AES-CBC-PKCS7 计算 sign（Base64，不做字符替换）
// 4) 依次请求 addPlea 与 upload
//
// 依赖：axios、crypto-js、form-data
// 安装：
//   pnpm add axios crypto-js form-data
// 或 npm i axios crypto-js form-data
//
// 使用示例（支持 环境变量 或 命令行 参数）：
//  环境变量：
//    OPENID, COMPLAINT_PHONE, USER_PHONE, COMPANY_ID, COMPANY_NAME, PLEA_REASON, FILE, BASE_URL(可选)
//  命令行参数（优先级高于环境变量）：
//    --openid OID --complaint-phone 申诉手机号 --user-phone 账号手机号 --company-id CID \
//    --company-name NAME --plea-reason REASON --file /abs/path/img.jpg [--base https://...]
//  示例：
//    node submit_plea.js \
//      --openid "oYXTH6Gkqz-vn710nGpwbggJWDu0" \
//      --complaint-phone "13700000001" \
//      --user-phone "13800138000" \
//      --company-id "91410100MA44X4F98J" \
//      --company-name "郑州创万瑞酒店管理有限公司" \
//      --plea-reason "公司最近刚拿下的号码段..." \
//      --file "/absolute/path/to/license.jpg"
//
// 注意：
// - plea_phone 使用 申诉手机号(COMPLAINT_PHONE) 加密。
// - filename 的后四位来自 账号手机号(USER_PHONE) 的后四位。
// - 脚本会从文件路径推断扩展名为 filename 的后缀。

const fs = require('fs')
const path = require('path')
const axios = require('axios')
const FormData = require('form-data')
const CryptoJS = require('crypto-js')
require('dotenv').config()


// AES key/iv 与前端保持一致
const KEY = CryptoJS.enc.Utf8.parse('ebupt_1234567890')
const IV = CryptoJS.enc.Utf8.parse('1234567890123456')

function pad2(n) { return n.toString().padStart(2, '0') }
function pad3(n) { return n.toString().padStart(3, '0') }

function nowParts(d = new Date()) {
  const Y = d.getFullYear()
  const M = pad2(d.getMonth() + 1)
  const D = pad2(d.getDate())
  const h = pad2(d.getHours())
  const m = pad2(d.getMinutes())
  const s = pad2(d.getSeconds())
  const ms = pad3(d.getMilliseconds())
  return {
    ymd: `${Y}${M}${D}`,
    ymdHms: `${Y}${M}${D}${h}${m}${s}`,
    ms
  }
}

function inferExt(filePath) {
  const ext = path.extname(filePath).toLowerCase().replace(/^\./, '')
  if (!ext) return 'jpg'
  if (['jpg', 'jpeg', 'png'].includes(ext)) return ext === 'jpg' ? 'jpg' : ext
  // 非图片也允许，但建议与服务器协同
  return ext
}

function parseArgs(argv) {
  const args = {}
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i]
    if (a.startsWith('--')) {
      const key = a.slice(2)
      const val = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true
      args[key] = val
    }
  }
  return args
}

class ShensuClient {
  constructor(cfg) {
    this.cfg = cfg
    this.uaAddPlea = cfg.uaAddPlea || 'Mozilla/5.0 (iPhone; CPU iPhone OS 6_1_3 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Mobile/10B329 MicroMessenger/5.0.1'
    this.uaUpload = cfg.uaUpload || 'Mozilla/5.0 (iPhone; CPU iPhone OS 19_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.54(0x1800363a) NetType/WIFI Language/zh_CN'
  }

  static encryptPhone(plainPhone) {
    const payload = `${plainPhone}$${Date.now()}`
    const t = CryptoJS.enc.Utf8.parse(payload)
    const n = CryptoJS.AES.encrypt(t, KEY, { iv: IV, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 })
    return CryptoJS.enc.Base64.stringify(n.ciphertext).replace(/\//g, '_').replace(/\+/g, '-')
  }

  // 解密由 encryptPhone 生成的密文，返回明文手机号
  static decryptPhone(enc) {
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
    const idx = plaintext.lastIndexOf('$')
    return idx === -1 ? plaintext : plaintext.slice(0, idx)
  }

  static encryptSign(str) {
    const e = str + '91Bmzn$0$#brkNYX'
    const t = CryptoJS.enc.Utf8.parse(e)
    const n = CryptoJS.AES.encrypt(t, KEY, { iv: IV, mode: CryptoJS.mode.CBC, padding: CryptoJS.pad.Pkcs7 })
    return CryptoJS.enc.Base64.stringify(n.ciphertext)
  }

  static buildFilename(userPhone, filePath) {
    const { ymd, ymdHms, ms } = nowParts()
    const last4 = (userPhone || '').replace(/\D/g, '').slice(-4) || '0000'
    const ext = inferExt(filePath)
    return `${ymd}/${last4}_${ymdHms}${ms}.${ext}`
  }

  validate() {
    const req = ['openid', 'complaintPhone', 'userPhone', 'company_id', 'company_name', 'plea_reason', 'filePath', 'base']
    for (const k of req) {
      if (!this.cfg[k]) throw new Error(`缺少必填参数: ${k}`)
    }
    if (!fs.existsSync(this.cfg.filePath)) throw new Error(`文件不存在: ${this.cfg.filePath}`)
  }

  async addPlea() {
    const {
      openid, complaintPhone, company_id, company_name, plea_reason, userPhone, filePath, base
    } = this.cfg

    const filename = ShensuClient.buildFilename(userPhone, filePath)
    const plea_type = '2'
    const plea_phone = ShensuClient.encryptPhone(complaintPhone)
    const signPayload = openid + plea_type + plea_phone + company_id + company_name + plea_reason + filename
    const sign = ShensuClient.encryptSign(signPayload)

    const addPleaUrl = `${base}/pleaphone/addPlea`
    const addPleaHeaders = {
      'User-Agent': this.uaAddPlea,
      'Accept': 'application/json, text/plain, */*',
      'Content-Type': 'application/json',
      'Accept-Language': 'zh-CN,zh;q=0.9,fr;q=0.8,de;q=0.7,en;q=0.6',
      'Cache-Control': 'no-cache',
      'Origin': 'https://www.securityeb.com',
      'Pragma': 'no-cache',
      'Referer': 'https://www.securityeb.com/?state=ebupt'
    }

    const body = {
      openid,
      plea_type,
      plea_phone,
      company_id,
      company_name,
      plea_reason,
      filename,
      sign
    }

    console.log('[debug] filename =', filename)
    console.log('[debug] plea_phone =', plea_phone)
    console.log('[debug] sign =', sign)

    const resp = await axios.post(addPleaUrl, body, { headers: addPleaHeaders, timeout: 20000 })
    return { data: resp.data, filename }
  }

  async upload(filename) {
    const { filePath, base } = this.cfg
    const uploadUrl = `${base}/pleaphone/upload`

    const form = new FormData()
    form.append('file', fs.createReadStream(filePath), { filename: path.basename(filePath) })
    form.append('filename', filename)

    const uploadHeaders = {
      ...form.getHeaders(),
      'User-Agent': this.uaUpload,
      'Accept': 'application/json, text/plain, */*',
      'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
      'Origin': 'https://www.securityeb.com',
      'Referer': 'https://www.securityeb.com/?state=ebupt'
    }

    const resp = await axios.post(uploadUrl, form, { headers: uploadHeaders, maxBodyLength: Infinity, timeout: 30000 })
    return resp.data
  }

  async run() {
    this.validate()
    const add = await this.addPlea()
    console.log('[addPlea] 响应:', add.data)

    if (add && add.data && typeof add.data.code !== 'undefined' && add.data.code !== 200) {
      throw new Error('[addPlea] 非成功 code，终止上传。')
    }

    const up = await this.upload(add.filename)
    console.log('[upload] 响应:', up)
  }
}

function readConfig() {
  const args = parseArgs(process.argv)
  const env = process.env

  // console.log('[debug] args =', args)
  // console.log('[debug] env =', env)

  const cfg = {
    openid: args.openid || env.OPENID,
    complaintPhone: args['complaint-phone'] || env.COMPLAINT_PHONE,
    userPhone: args['user-phone'] || env.USER_PHONE,
    company_id: args['company-id'] || env.COMPANY_ID,
    company_name: args['company-name'] || env.COMPANY_NAME,
    plea_reason: args['plea-reason'] || env.PLEA_REASON,
    filePath: args.file || env.FILE,
    base: args.base || env.BASE_URL || 'https://www.securityeb.com/ktfsr'
  }
  return cfg
}

async function main() {
  try {
    const cfg = readConfig()
    const client = new ShensuClient(cfg)
    await client.run()
  } catch (err) {
    console.error('执行失败:', err.message || err)
    process.exit(1)
  }
}

main()
