webpackJsonp([17], {
    "17iA": function (t, e) { },
    Orwt: function (t, e, a) {
        "use strict"
        Object.defineProperty(e, "__esModule", {
            value: !0
        })
        var i = a("FuCC")
            , s = a("DcEF")
            , n = {
                name: "GpfsrSmeFrontPleaCompany",
                data: function () {
                    return {
                        plea_phone: "",
                        company_id: "",
                        company_name: "",
                        plea_reason: "",
                        idCard1: null,
                        idCard1Date: null,
                        idCard1Name: "",
                        blurFlag: !1,
                        isCommit: !1
                    }
                },
                mounted: function () { },
                methods: {
                    goBack: function () {
                        window.history.back()
                    },
                    formatToNumber: function (t) {
                        return t.replace(/[^0-9]/g, "")
                    },
                    formatToCompanyID: function (t) {
                        return t.replace(/[^0-9A-Z]/g, "")
                    },
                    queryPhoneIsSys: function () {
                        var t = this
                        return this.blurFlag = !0,
                            "" == this.plea_phone ? (this.$toast.fail("请输入需要申诉的号码"),
                                void setTimeout(function () {
                                    t.blurFlag = !1
                                }, 500)) : this.plea_phone.length < 3 ? (this.$toast.fail("申诉号码长度不能小于3位"),
                                    this.plea_phone = "",
                                    void setTimeout(function () {
                                        t.blurFlag = !1
                                    }, 500)) : void this.$axios.get("/sysblack/querySysphone?phone=" + Object(i.b)(this.plea_phone)).then(function (e) {
                                        200 == e.code ? "0" == e.data && (t.$toast.fail("该号码非高频骚扰号码，无法申诉"),
                                            t.plea_phone = "") : (t.$toast.fail(e.msg),
                                                t.plea_phone = ""),
                                            t.blurFlag = !1
                                    })
                    },
                    afterRead: function (t) {
                        if ("image/jpeg" == t.file.type || "image/png" == t.file.type)
                            if (t.file.size > 10485760)
                                this.$toast.fail("文件大小不能超过10M")
                            else {
                                var e = Object(s.b)(0) + (new Date).getMilliseconds()
                                    , a = t.file.name.split(".")
                                this.idCard1Data = t.content,
                                    this.idCard1 = t.file,
                                    this.idCard1Name = Object(s.b)(0).substring(0, 8) + "/" + localStorage.getItem("userphone").substring(7, 11) + "_" + e + "." + a[a.length - 1]
                            }
                        else
                            this.$toast.fail("文件格式错误")
                    },
                    closeFileImg: function () {
                        this.idCard1Data = "",
                            this.idCard1Name = "",
                            this.idCard1 = null
                    },
                    submitPlea: function () {
                        var t = this
                        if (!this.blurFlag)
                            if ("" != this.plea_phone)
                                if (this.plea_phone.length < 3)
                                    this.$toast.fail("申诉号码长度不能小于3位")
                                else if ("" != this.company_name)
                                    if (this.company_id.length < 15)
                                        this.$toast.fail("申诉机构证件号格式错误")
                                    else if ("" != this.plea_reason)
                                        if (null != this.idCard1)
                                            if (this.isCommit)
                                                console.log("请稍后重试")
                                            else {
                                                this.isCommit = !0
                                                var e = {
                                                    openid: localStorage.getItem("openid"),
                                                    plea_type: "2",
                                                    plea_phone: Object(i.b)(this.plea_phone),
                                                    company_id: this.company_id,
                                                    company_name: this.company_name,
                                                    plea_reason: this.plea_reason,
                                                    filename: this.idCard1Name
                                                }
                                                e.sign = Object(i.c)(e.openid + e.plea_type + e.plea_phone + e.company_id + e.company_name + e.plea_reason + e.filename),
                                                    this.$axios.post("/pleaphone/addPlea", e).then(function (e) {
                                                        if (200 == e.code) {
                                                            t.$dialog.alert({
                                                                message: "申诉已提交"
                                                            }).then(function () { })
                                                            var a = new FormData
                                                            a.append("file", t.idCard1),
                                                                a.append("filename", t.idCard1Name),
                                                                t.$axios.post("/pleaphone/upload", a).then(function (t) {
                                                                    console.log(t)
                                                                }),
                                                                setTimeout(function () {
                                                                    t.idCard1Data = "",
                                                                        t.idCard1 = null,
                                                                        t.idCard1Name = "",
                                                                        t.plea_phone = "",
                                                                        t.company_id = "",
                                                                        t.company_name = "",
                                                                        t.plea_reason = ""
                                                                }, 200)
                                                        } else
                                                            t.$toast.fail(e.msg)
                                                        t.isCommit = !1
                                                    })
                                            }
                                        else
                                            this.$toast.fail("营业执照附件不能为空")
                                    else
                                        this.$toast.fail("申诉理由不能为空")
                                else
                                    this.$toast.fail("申诉机构名称不能为空")
                            else
                                this.$toast.fail("请输入需要申诉的号码")
                    }
                }
            }
            , o = {
                render: function () {
                    var t = this
                        , e = t.$createElement
                        , i = t._self._c || e
                    return i("div", {
                        staticStyle: {
                            width: "100vw",
                            height: "100vh"
                        }
                    }, [i("div", {
                        staticStyle: {
                            background: "#FFFCDF",
                            "font-family": "PingFang SC",
                            "font-weight": "400",
                            color: "#206DF2",
                            display: "flex",
                            "justify-content": "center",
                            "align-items": "center",
                            height: "25px",
                            padding: "0px 12px"
                        }
                    }, [i("van-icon", {
                        staticStyle: {
                            "padding-right": "5px"
                        },
                        attrs: {
                            name: "info-o",
                            size: "12"
                        }
                    }), t._v(" "), t._m(0)], 1), t._v(" "), i("div", {
                        staticClass: "header-goback",
                        staticStyle: {
                            "padding-top": "0px",
                            color: "rgb(179, 179, 179)",
                            background: "rgb(245, 245, 245)",
                            height: "26px",
                            width: "100%",
                            "justify-content": "flex-start",
                            "align-items": "flex-end"
                        }
                    }, [i("img", {
                        staticStyle: {
                            width: "16PX"
                        },
                        attrs: {
                            src: "/static/imgs/go_back_gray.png"
                        },
                        on: {
                            click: t.goBack
                        }
                    }), t._v(" "), i("span", {
                        staticStyle: {
                            "padding-left": "4PX"
                        },
                        on: {
                            click: t.goBack
                        }
                    }, [t._v("返回上一页")])]), t._v(" "), i("div", {
                        staticStyle: {
                            background: "#F5F5F5",
                            padding: "20px",
                            "font-size": "15px",
                            "font-family": "PingFang SC",
                            "font-weight": "400",
                            color: "#434343",
                            "line-height": "15px"
                        }
                    }, [i("div", {
                        staticStyle: {
                            "margin-bottom": "24px"
                        }
                    }, [t._m(1), t._v(" "), i("van-field", {
                        staticStyle: {
                            "margin-top": "10px",
                            background: "#FFFFFF",
                            border: "1px solid #E1E1E1",
                            "border-radius": "5px"
                        },
                        attrs: {
                            formatter: t.formatToNumber,
                            maxlength: "16",
                            placeholder: "申诉号码",
                            clearable: ""
                        },
                        on: {
                            blur: t.queryPhoneIsSys
                        },
                        model: {
                            value: t.plea_phone,
                            callback: function (e) {
                                t.plea_phone = e
                            },
                            expression: "plea_phone"
                        }
                    })], 1), t._v(" "), i("div", {
                        staticStyle: {
                            "margin-bottom": "24px"
                        }
                    }, [t._m(2), t._v(" "), i("van-field", {
                        staticStyle: {
                            "margin-top": "10px",
                            background: "#FFFFFF",
                            border: "1px solid #E1E1E1",
                            "border-radius": "5px"
                        },
                        attrs: {
                            maxlength: "50",
                            placeholder: "申诉机构全称",
                            clearable: ""
                        },
                        model: {
                            value: t.company_name,
                            callback: function (e) {
                                t.company_name = e
                            },
                            expression: "company_name"
                        }
                    })], 1), t._v(" "), i("div", {
                        staticStyle: {
                            "margin-bottom": "24px"
                        }
                    }, [t._m(3), t._v(" "), i("van-field", {
                        staticStyle: {
                            "margin-top": "10px",
                            background: "#FFFFFF",
                            border: "1px solid #E1E1E1",
                            "border-radius": "5px"
                        },
                        attrs: {
                            maxlength: "20",
                            formatter: t.formatToCompanyID,
                            placeholder: "申诉机构证件号",
                            clearable: ""
                        },
                        model: {
                            value: t.company_id,
                            callback: function (e) {
                                t.company_id = e
                            },
                            expression: "company_id"
                        }
                    })], 1), t._v(" "), i("div", {
                        staticStyle: {
                            "margin-bottom": "24px"
                        }
                    }, [t._m(4), t._v(" "), i("van-field", {
                        staticStyle: {
                            "margin-top": "10px",
                            background: "#FFFFFF",
                            border: "1px solid #E1E1E1",
                            "border-radius": "5px"
                        },
                        attrs: {
                            rows: "5",
                            autosize: "",
                            type: "textarea",
                            maxlength: "200",
                            "show-word-limit": "",
                            placeholder: "请输入申诉理由",
                            clearable: ""
                        },
                        model: {
                            value: t.plea_reason,
                            callback: function (e) {
                                t.plea_reason = e
                            },
                            expression: "plea_reason"
                        }
                    })], 1), t._v(" "), i("div", {
                        staticStyle: {
                            "margin-bottom": "24px"
                        }
                    }, [t._m(5), t._v(" "), i("div", {
                        staticStyle: {
                            display: "flex",
                            "flex-direction": "column",
                            "justify-content": "center",
                            "align-items": "center",
                            position: "relative",
                            "padding-top": "10px"
                        }
                    }, [null == t.idCard1 ? i("van-uploader", {
                        attrs: {
                            "after-read": t.afterRead
                        }
                    }, [i("div", {
                        staticClass: "file-img",
                        staticStyle: {
                            display: "flex",
                            "justify-content": "center",
                            "align-items": "center"
                        }
                    }, [i("img", {
                        attrs: {
                            src: a("h8/1")
                        }
                    })])]) : i("img", {
                        staticClass: "file-img",
                        attrs: {
                            src: t.idCard1Data
                        }
                    }), t._v(" "), i("div", {
                        staticStyle: {
                            "margin-top": "5px"
                        }
                    }, [t._v("营业执照")]), t._v(" "), null != t.idCard1 ? i("van-icon", {
                        staticStyle: {
                            position: "absolute",
                            "font-size": "30px",
                            top: "10px",
                            right: "2px"
                        },
                        attrs: {
                            name: "close",
                            size: "30"
                        },
                        on: {
                            click: t.closeFileImg
                        }
                    }) : t._e()], 1)]), t._v(" "), i("div", {
                        staticStyle: {
                            width: "100%",
                            "text-align": "center",
                            "margin-top": "30px",
                            background: "#206DF2",
                            "border-radius": "4px",
                            height: "45px",
                            "line-height": "45px",
                            "font-size": "17px",
                            "font-family": "PingFang SC",
                            "font-weight": "400",
                            color: "#FFFFFF"
                        },
                        on: {
                            click: t.submitPlea
                        }
                    }, [t._v("\n      确认提交申诉")]), t._v(" "), i("div", {
                        staticStyle: {
                            width: "100%",
                            height: "40px"
                        }
                    })])])
                },
                staticRenderFns: [function () {
                    var t = this.$createElement
                        , e = this._self._c || t
                    return e("div", {
                        staticClass: "marquee"
                    }, [e("span", [this._v("小提示：仅支持正规用途的非营销及违法号码申诉，申诉请慎重，否则可能影响号码业务使用。")])])
                }
                    , function () {
                        var t = this.$createElement
                            , e = this._self._c || t
                        return e("span", [this._v("申诉号码"), e("span", {
                            staticStyle: {
                                color: "red"
                            }
                        }, [this._v("*")])])
                    }
                    , function () {
                        var t = this.$createElement
                            , e = this._self._c || t
                        return e("span", [this._v("申诉机构全称"), e("span", {
                            staticStyle: {
                                color: "red"
                            }
                        }, [this._v("*")])])
                    }
                    , function () {
                        var t = this.$createElement
                            , e = this._self._c || t
                        return e("span", [this._v("申诉机构证件号"), e("span", {
                            staticStyle: {
                                color: "red"
                            }
                        }, [this._v("*")])])
                    }
                    , function () {
                        var t = this.$createElement
                            , e = this._self._c || t
                        return e("span", [this._v("申诉理由"), e("span", {
                            staticStyle: {
                                color: "red"
                            }
                        }, [this._v("*")])])
                    }
                    , function () {
                        var t = this.$createElement
                            , e = this._self._c || t
                        return e("span", [this._v("营业执照附件"), e("span", {
                            staticStyle: {
                                color: "red"
                            }
                        }, [this._v("*")])])
                    }
                ]
            }
        var l = a("owSs")(n, o, !1, function (t) {
            a("17iA")
        }, "data-v-ae3c34c0", null)
        e.default = l.exports
    },
    "h8/1": function (t, e) {
        t.exports = "data:image/png;base64,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"
    }
})
