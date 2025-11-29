"""
راهنمای کامل و خط‌به‌خط برای یک انسان واقعی (فارسی ساده)

این فایل یک اسکرِیپِر ساده است که صفحه آگهی‌های منطقه زعفرانیه در سایت دیوار را
می‌گیرد، لینک اولین آگهی‌ها را استخراج می‌کند و در صورت امکان (اگر Playwright نصب
باشد) از هر آگهی اسکرین‌شات می‌گیرد و آن را به یک چت تلگرام می‌فرستد.

اگر شما با برنامه‌نویسی آشنا نیستید، نکات مهم:
- این فایل توسط پایتون اجرا می‌شود: یعنی شما باید پایتون روی سیستم یا داخل کانتینر نصب باشد.
- بخشی از برنامه (ارسال به تلگرام) شامل یک توکن ثابت است که در متن برنامه است؛
  این روش امن نیست و بهتر است توکن را در متغیر محیطی یا فایل بیرونی قرار دهید.
- اگر Playwright نصب نباشد، برنامه فقط لینک‌ها را چاپ می‌کند و از مرورگر استفاده نمی‌کند.

در ادامه توضیح هر بخش آمده است، با کامنت‌های داخل کد نیز توضیح داده شده.
"""

import sys
import os
import requests
from bs4 import BeautifulSoup
import io
import os.path

# بخش: تلاش برای وارد کردن Playwright در زمان اجرا (به صورت امن)
# ما Playwright را به صورت "تنها زمانی که موجود است" وارد می‌کنیم زیرا ممکن است
# شما فقط بخواهید لینک‌ها را استخراج کنید و نخواهید مرورگر را نصب کنید.
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    # اگر وارد نشد، برنامه همچنان می‌تواند لینک‌ها را بگیرد اما اسکرین‌شات نمی‌گیرد
    PLAYWRIGHT_AVAILABLE = False


# آدرس صفحه‌ای که می‌خواهیم از آن لینک‌ها را بگیریم
START_URL = 'enter your url'


def get_ad_links(url, count=10):
    """
    این تابع یک صفحه وب را دریافت می‌کند و تا `count` لینک آگهی را برمی‌گرداند.

    نکته برای شما که تازه‌کار هستید:
    - این تابع یک درخواست اینترنتی (HTTP GET) به آن آدرس می‌زند.
    - اگر سایت اجازه ندهد یا خطایی پیش بیاید، تابع لیست خالی برمی‌گرداند.
    - ما یک هدر 'User-Agent' می‌فرستیم تا سایت ما را مانند یک مرورگر بشناسد.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        # اگر خطایی در درخواست بود، پیغام مناسب چاپ می‌شود و تابع لیست خالی می‌دهد
        print(f"Error fetching page: {e}")
        return []

    # از BeautifulSoup برای خواندن HTML صفحه استفاده می‌کنیم و لینک‌ها را استخراج می‌کنیم
    soup = BeautifulSoup(resp.text, 'html.parser')

    links = []
    # دیوار لینک‌های داخلی برای آگهی‌ها را با مسیر /v/ شروع می‌کند؛ آن‌ها را جمع می‌کنیم
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/v/'):
            full = 'https://divar.ir' + href
            if full not in links:
                links.append(full)
        if len(links) >= count:
            break

    if not links:
        print('No ad links found. The page layout may have changed or the site blocks requests.')

    return links


def send_file_to_telegram(file_path, caption=None):
    """
    این تابع یک تصویر را به تلگرام ارسال می‌کند.

    هشدار مهم برای شما:
    - در این کد توکنِ رباتِ تلگرام (bot_token) و شناسه چت (chat_id) به صورت "کد شده" داخل
      برنامه قرار گرفته‌اند. این کار امن نیست. هر کسی که به این فایل دسترسی داشته باشد می‌تواند
      پیام بفرستد یا توکن را بدزدد. بهتر است از متغیر محیطی یا فایل محرمانه استفاده کنید.
    - اگر فایل به جای دیسک در حافظه (in-memory) ذخیره شده باشد، این تابع آن را نیز پشتیبانی می‌کند.
    """
    # Hard-coded credentials (user provided) — توصیه: اینها را در متغیر محیطی بگذارید
    bot_token = 'enter your bot token'
    chat_id = 'enter your chat id'
    if not (bot_token and chat_id):
        print("ℹ️  Telegram credentials not set in script; skipping send")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    # اگر ارسال موفق نبود، چند بار تلاش (retry) می‌کنیم با فاصلهٔ افزایشی
    max_attempts = 3
    delay = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption

            # اگر فایل روی دیسک هست از آن استفاده کن، در غیر این صورت از حافظه داخلی استفاده می‌کنیم
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    files = {'photo': f}
                    resp = requests.post(url, files=files, data=data, timeout=30)
            else:
                global _IN_MEMORY_FILES
                img_bytes = None
                if '_IN_MEMORY_FILES' in globals():
                    img_bytes = _IN_MEMORY_FILES.get(file_path)

                if img_bytes is None:
                    raise FileNotFoundError(f"File not found on disk and not present in memory: {file_path}")

                bio = io.BytesIO(img_bytes)
                files = {'photo': (os.path.basename(file_path), bio, 'image/png')}
                resp = requests.post(url, files=files, data=data, timeout=30)

            if resp.status_code == 200:
                print('\n✅ عکس با موفقیت به تلگرام ارسال شد!')
                return True
            else:
                print(f"❌ خطا در ارسال عکس به تلگرام (attempt {attempt}): {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"❌ Exception while sending to Telegram (attempt {attempt}): {e}")

        if attempt < max_attempts:
            print(f"Retrying in {delay} seconds...")
            import time
            time.sleep(delay)
            delay *= 2

    print('❌ All attempts to send the photo failed')
    return False


def send_text_to_telegram(text):
    """
    این تابع یک پیام متنی به همان چت تلگرام می‌فرستد.
    همان هشدار امنیتی دربارهٔ توکن‌ها برقرار است.
    """
    bot_token = '7661315445:AAFfyRXVDPm6IcG6-gDMbI-rrTUFKEBeuIk'
    chat_id = '-1002828741825'
    if not (bot_token and chat_id):
        print("ℹ️  Telegram credentials not set in script; skipping text send")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    max_attempts = 3
    delay = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            data = {'chat_id': chat_id, 'text': text, 'disable_web_page_preview': True}
            resp = requests.post(url, data=data, timeout=30)
            if resp.status_code == 200:
                print('\n✅ پیام متن به تلگرام ارسال شد!')
                return True
            else:
                print(f"❌ خطا در ارسال پیام به تلگرام (attempt {attempt}): {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"❌ Exception while sending text to Telegram (attempt {attempt}): {e}")

        if attempt < max_attempts:
            print(f"Retrying in {delay} seconds...")
            import time
            time.sleep(delay)
            delay *= 2

    print('❌ All attempts to send the text message failed')
    return False


def main():
    # مرحله اول: گرفتن لینک‌های آگهی
    links = get_ad_links(START_URL, count=10)
    if not links:
        print('No links to show.')
        return

    print('\nFirst {} ad links from Divar (Zaferanieh):\n'.format(len(links)))
    for i, link in enumerate(links, start=1):
        print(f"{i}. {link}")

    # اگر Playwright نصب باشد، از مرورگر headless برای گرفتن اسکرین‌شات استفاده کن
    if not PLAYWRIGHT_AVAILABLE:
        print('\nPlaywright not available. To enable screenshots install:')
        print('  pip install playwright')
        print('  python -m playwright install')
        return

    # ما اسکرین‌شات‌ها را در حافظه نگهداری می‌کنیم تا از نوشتن مداوم روی دیسک جلوگیری کنیم
    global _IN_MEMORY_FILES
    _IN_MEMORY_FILES = {}

    print('\nStarting headless browser to capture screenshots...')
    PLAYWRIGHT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    PLAYWRIGHT_USER_AGENT += '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

    # با sync_playwright() مرورگر را باز می‌کنیم و برای هر لینک یک context تازه می‌سازیم
    with sync_playwright() as p:
        # از کرومیوم استفاده می‌کنیم چون بیشترین سازگاری را دارد
        browser = p.chromium.launch(headless=True)

        for idx, url in enumerate(links, start=1):
            filename = os.path.join('screenshots', f'ad_{idx}.png')
            try:
                # ساختن یک context/صفحه جدید برای هر URL تا حالت صفحات جدا بماند
                context = browser.new_context(viewport={'width': 1280, 'height': 800}, user_agent=PLAYWRIGHT_USER_AGENT)
                page = context.new_page()
                print(f'[{idx}/{len(links)}] Navigating to {url} ...')
                page.goto(url, timeout=20000)

                # منتظر می‌مانیم تا شبکه بخوابد یا حداکثر زمان بگذرد
                try:
                    page.wait_for_load_state('networkidle', timeout=10000)
                except PlaywrightTimeoutError:
                    # اگر networkidle نیامد، ادامه می‌دهیم
                    pass

                # گرفتن اسکرین‌شات به صورت بایتی (بدون نوشتن روی دیسک)
                png_bytes = page.screenshot(full_page=True)
                _IN_MEMORY_FILES[filename] = png_bytes
                print(f'  Saved screenshot to memory as {filename}')

                # ارسال تصویر به تلگرام (اگر مشکلی بود، خطا گرفته می‌شود)
                try:
                    send_file_to_telegram(filename, caption=url)
                    try:
                        del _IN_MEMORY_FILES[filename]
                    except Exception:
                        pass
                    import time
                    time.sleep(1)
                except Exception as e:
                    print(f'  Failed to send screenshot to Telegram: {e}')

            except Exception as e:
                print(f'  Failed to capture {url}: {e}')
            finally:
                try:
                    context.close()
                except Exception:
                    pass

        try:
            browser.close()
        except Exception:
            pass

    # بعد از تمام شدن، یک پیام متنی حاوی لینک‌ها می‌فرستیم
    try:
        if links:
            numbered_lines = [f"{i}.. {u}" for i, u in enumerate(links, start=1)]
            message = "\n\n".join(numbered_lines)

            # تبدیل تاریخ میلادی به شمسی (ساده، به‌عنوان مثال)
            def gregorian_to_jalali(gy, gm, gd):
                g_d_m = [0,31,59,90,120,151,181,212,243,273,304,334]
                if gy > 1600:
                    jy = 979
                    gy -= 1600
                else:
                    jy = 0
                    gy -= 621

                if gm > 2:
                    gy2 = gy + 1
                else:
                    gy2 = gy

                days = 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 - 80 + gd + g_d_m[gm-1]
                jy += 33 * (days // 12053)
                days %= 12053
                jy += 4 * (days // 1461)
                days %= 1461
                if days > 365:
                    jy += (days - 1) // 365
                    days = (days - 1) % 365

                if days < 186:
                    jm = 1 + days // 31
                    jd = 1 + (days % 31)
                else:
                    days -= 186
                    jm = 7 + days // 30
                    jd = 1 + (days % 30)

                return jy, jm, jd

            import datetime
            # تلاش می‌کنیم از zoneinfo استفاده کنیم تا دقیقاً زمان به وقت تهران نمایش داده شود.
            # Python 3.9+ دارای ماژول zoneinfo است؛ در صورت نبودن، یک fallback ساده با اختلاف زمانی خواهیم داشت.
            try:
                # zoneinfo مسیر منطقه‌های زمانی استاندارد است (IANA). Asia/Tehran برابر UTC+03:30 است.
                from zoneinfo import ZoneInfo
                now = datetime.datetime.now(tz=ZoneInfo('Asia/Tehran'))
            except Exception:
                # fallback: اگر zoneinfo نصب نبود، از زمان محلی سیستم استفاده کن و 3.5 ساعت اضافه کن
                now = datetime.datetime.utcnow() + datetime.timedelta(hours=3, minutes=30)
            jy, jm, jd = gregorian_to_jalali(now.year, now.month, now.day)
            # حالا زمان به وقت تهران در now است؛ فرمت نمایش ساعت:دقیقه
            time_str = now.strftime('%H:%M')
            prefix = f"لینک اگهی های امروز ({jy:04d}/{jm:02d}/{jd:02d} >> {time_str} ):\n\n"

            full_message = prefix + message
            send_text_to_telegram(full_message)
    except Exception as e:
        print(f"Failed to send final URL list to Telegram: {e}")


if __name__ == '__main__':
    main()
 