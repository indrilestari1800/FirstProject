import base64

# 1. Ganti dengan nama file JSON Firebase Anda
nama_file_json = "paud-almuttaqien-firebase-adminsdk-fbsvc-036c48df21.json"

try:
    with open(nama_file_json, "rb") as file:
        # Membaca file dan mengubahnya ke Base64
        data_bytes = file.read()
        base64_encoded = base64.b64encode(data_bytes)
        
        # Mengubah bytes menjadi string satu baris
        base64_string = base64_encoded.decode("utf-8")
        
        print("--- BERHASIL DI-ENCODE (Salin teks di bawah ini) ---\n")
        print(base64_string)
        print("\n---------------------------------------------------")
        
except FileNotFoundError:
    print(f"Error: File '{nama_file_json}' tidak ditemukan. Pastikan nama filenya sudah benar.")
