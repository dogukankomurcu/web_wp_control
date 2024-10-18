from flask import Flask, render_template, request, redirect, send_file, url_for
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from io import BytesIO
import os
import uuid

app = Flask(__name__)
app.secret_key = 'gizli_anahtar'  # Güvenlik için güçlü bir anahtar kullanın

# Yüklenen dosyalar için geçici klasör
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# WhatsApp numarasını kontrol etme fonksiyonu
def check_whatsapp_number(driver, phone_number):
    driver.get(f'https://web.whatsapp.com/send?phone={phone_number}')
    time.sleep(10)  # QR kod tarama sonrası sayfanın yüklenmesini bekle

    try:
        error_message = driver.find_element(By.XPATH, '//*[contains(text(), "telefon numarası geçersiz")]')
        if error_message:
            return False  
    except:
        pass  

    return True  

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'Dosya bulunamadı.'

    file = request.files['file']
    if file.filename == '':
        return 'Lütfen bir dosya seçin.'

    # Benzersiz bir ID oluştur
    upload_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}.xlsx")
    file.save(file_path)

    # Selenium WebDriver'ı başlat
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--headless")  # QR kod tarama için tarayıcıyı görünür bırakın
    driver = webdriver.Chrome(service=service, options=options)

    driver.get('https://web.whatsapp.com/')

    # WebDriver oturumunu ID ile sakla
    if not hasattr(app, 'drivers'):
        app.drivers = {}
    app.drivers[upload_id] = driver

    return render_template('waiting.html', upload_id=upload_id)

@app.route('/process', methods=['POST'])
def process_file():
    upload_id = request.form.get('upload_id')
    if not upload_id:
        return 'Geçersiz istek.'

    file_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}.xlsx")
    if not os.path.exists(file_path):
        return 'Dosya bulunamadı.'

    # Excel dosyasını yükle
    df = pd.read_excel(file_path)

    # WebDriver oturumunu al
    driver = app.drivers.get(upload_id)
    if not driver:
        return 'Driver bulunamadı.'

    valid_phone_numbers = []

    for phone_number in df['Phone']:
        if check_whatsapp_number(driver, phone_number):
            valid_phone_numbers.append(phone_number)

    driver.quit()
    del app.drivers[upload_id]

    # Geçerli numaraları Excel dosyasına yaz
    valid_df = pd.DataFrame(valid_phone_numbers, columns=['Valid_Phone'])
    output = BytesIO()
    valid_df.to_excel(output, index=False)
    output.seek(0)

    # Geçici dosyayı sil
    os.remove(file_path)

    return send_file(output, as_attachment=True, download_name='valid_whatsapp_numbers.xlsx')

if __name__ == '__main__':
    app.run(debug=True)
