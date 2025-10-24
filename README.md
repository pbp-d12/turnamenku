## README PBP 2025/2026 D-12 PTS

## Anggota Kelompok
2406413842 - Gibran Tegar Ramadhan Putra Lynardi

2406495786 - Izzudin Abdul Rasyid

2406407266 - Hillary Elizabeth Clara Pasaribu

2406361712 - Muhathir Muhammad Radian Oki

2406347424 - Bermulya Anugrah Putra

## Deskripsi Aplikasi (TURNAMENKU)

Turnamenku adalah aplikasi berbasis web yang jasa atau service utamanya memberikan fitur-fitur lengkap mengenai manajemen pelaksanaan turnamen. Dengan mengintegrasikan modul-modul inti seperti Manajemen Turnamen, Forum Diskusi, Prediksi Turnamen, dan Profil Pengguna, aplikasi ini bertujuan untuk menyediakan ekosistem yang terpusat dan interaktif. Aplikasi ini memfasilitasi penyelenggara turnamen dalam mengelola acaranya sekaligus memberikan pengalaman yang imersif dan interaktif bagi para peserta dan anggota komunitasnya.

---
## Implemented Modules

Proyek "Turnamenku" dibangun di atas arsitektur modular menggunakan beberapa aplikasi Django yang saling terhubung. Setiap aplikasi bertanggung jawab atas satu fitur inti, memungkinkan pengembangan yang terorganisir dan skalabel. Berikut adalah rincian dari setiap modul yang diimplementasikan:

---

### 1. User Profile (`main` app)

> **Deskripsi Fitur:** "Bagian inti dari aplikasi yang berfokus pada pengelolaan turnamen. Atribut dan detail lengkapnya masih perlu ditentukan, tetapi modul ini akan terhubung dengan Team dan Tournament Prediction."

**Implementasi di Website:**

Modul ini menjadi fondasi bagi seluruh interaksi pengguna di platform.

* **Model Data Utama:** Menggunakan model `User` kustom yang memperluas fungsionalitas bawaan Django. Model ini memiliki field tambahan seperti `role` (untuk membedakan 'Penyelenggara' dan 'Pemain'), `bio`, dan `profile_picture`.
* **Alur Pengguna:**
   1.  Pengguna melakukan **Registrasi** dan **Login** melalui form yang aman.
   2.  Setiap pengguna memiliki **halaman profil publik** yang dapat diakses oleh pengguna lain.
   3.  Di halaman profil, akan ditampilkan informasi seperti bio, foto, serta **daftar tim yang diikuti** (data dari modul `teams`) dan **histori/statistik prediksi** mereka (data dari modul `predictions`).
   4.  Pengguna dapat mengedit profil mereka sendiri melalui halaman **Edit Profile**.
* **Integrasi AJAX:** Saat pengguna mengunggah foto profil baru, preview gambar akan ditampilkan secara instan tanpa perlu me-refresh halaman, memberikan pengalaman pengguna yang lebih baik.

---

### 2. Turnamen (`tournaments` app)

> **Deskripsi Fitur:** "Bagian inti dari aplikasi yang berfokus pada pengelolaan turnamen. Atribut dan detail lengkapnya masih perlu ditentukan, tetapi modul ini akan terhubung dengan Team dan Tournament Prediction."

**Implementasi di Website:**

Modul ini adalah pusat dari seluruh aplikasi, tempat semua event turnamen dibuat dan dikelola.

* **Model Data Utama:** Terdiri dari dua model utama: `Tournament` (menyimpan info umum seperti nama, deskripsi, penyelenggara, dan banner) dan `Match` (menyimpan jadwal, tim yang bertanding, dan skor untuk setiap pertandingan dalam sebuah turnamen).
* **Alur Pengguna:**
   1.  Pengguna dengan role 'Penyelenggara' dapat mengakses form untuk **membuat turnamen baru**.
   2.  Semua pengguna dapat melihat **daftar turnamen** yang tersedia di halaman utama.
   3.  Setiap turnamen memiliki **halaman detail** yang menampilkan deskripsi lengkap, **daftar tim peserta** (dari modul `teams`), dan **jadwal pertandingan** (`Match`).
* **Integrasi AJAX:** Halaman daftar turnamen dilengkapi dengan fitur pencarian dan filter. Saat pengguna mengetik atau memilih filter, daftar turnamen akan diperbarui secara *real-time* tanpa *reload*, mempercepat pencarian.

---

### 3. Team (`teams` app)

> **Deskripsi Fitur:** "Merupakan kumpulan dari beberapa pengguna yang tergabung dalam satu tim. Tim dapat didaftarkan untuk mengikuti Turnamen, dan datanya juga akan digunakan dalam Tournament Prediction."

**Implementasi di Website:**

Modul ini mengelola entitas tim dan keanggotaan di dalamnya.

* **Model Data Utama:** Model `Team` yang memiliki relasi `ForeignKey` ke `Tournament` (setiap tim dibuat untuk turnamen spesifik) dan `ManyToManyField` ke `User` (untuk menyimpan daftar anggota tim).
* **Alur Pengguna:**
   1.  Setelah sebuah turnamen dibuat, pengguna dapat **membuat tim baru** untuk turnamen tersebut, di mana pembuat tim otomatis menjadi kapten.
   2.  Pengguna lain dapat menelusuri tim yang ada dan **bergabung dengan tim** pilihan mereka. Terdapat validasi di backend untuk memastikan seorang pengguna hanya bisa bergabung dengan satu tim per turnamen.
   3.  Setiap tim memiliki **halaman profilnya sendiri** yang menampilkan logo, nama, dan daftar anggota.
* **Integrasi AJAX:** Tombol "Join Team" dan "Leave Team" dieksekusi melalui AJAX. Ketika diklik, permintaan dikirim ke server, dan UI tombol akan langsung berubah (misalnya, menjadi non-aktif atau teksnya berubah) untuk memberikan feedback instan kepada pengguna.

---

### 4. Forum Turnamen (`forums` app)

> **Deskripsi Fitur:** "Fitur ini memungkinkan pengguna membuat postingan seperti di Reddit, dengan opsi untuk menambahkan komentar. Forum akan terhubung dengan data User, karena setiap posting dan komentar berasal dari akun pengguna."

**Implementasi di Website:**

Modul ini menyediakan ruang interaksi sosial untuk setiap turnamen.

* **Model Data Utama:** Terdiri dari model `Thread` (untuk setiap postingan utama) dan `Post` (untuk setiap komentar/balasan). Kedua model ini terhubung ke `User` sebagai pembuat dan ke `Tournament` untuk memastikan forum bersifat spesifik per turnamen.
* **Alur Pengguna:**
   1.  Dari halaman detail turnamen, pengguna dapat masuk ke **halaman forum** khusus turnamen tersebut.
   2.  Di dalam forum, pengguna dapat **membuat thread diskusi baru** atau masuk ke thread yang sudah ada.
   3.  Di halaman detail thread, pengguna dapat membaca konten dan **menambahkan komentar** mereka sendiri.
* **Integrasi AJAX:** Form untuk mengirim komentar akan disubmit menggunakan AJAX. Setelah dikirim, komentar baru akan langsung muncul di bagian bawah daftar komentar tanpa perlu me-refresh seluruh halaman, menciptakan pengalaman diskusi yang lancar seperti aplikasi media sosial modern.

---

### 5. Tournament Prediction (`predictions` app)

> **Deskripsi Fitur:** "Fitur yang memungkinkan pengguna memberikan prediksi atau vote mengenai tim yang diperkirakan akan memenangkan turnamen. Nantinya akan tersedia leaderboard untuk menampilkan peringkat pengguna berdasarkan akurasi prediksi mereka."

**Implementasi di Website:**

Modul ini menambahkan elemen gamifikasi dan interaksi bagi para penonton.

* **Model Data Utama:** Model `Prediction` yang secara efektif menjadi penghubung antara `User`, `Match`, dan `Team` (sebagai tim yang diprediksi menang). Model ini juga menyimpan `points_awarded` untuk setiap prediksi yang benar.
* **Alur Pengguna:**
   1.  Pengguna dapat mengakses halaman **Prediksi** di mana daftar pertandingan (`Match`) yang akan datang ditampilkan.
   2.  Untuk setiap pertandingan, pengguna dapat **mengklik tim yang mereka prediksi akan menang**.
   3.  Setelah pertandingan selesai dan skor diperbarui oleh penyelenggara, sebuah proses di backend akan mengevaluasi semua prediksi untuk pertandingan tersebut dan memberikan poin kepada pengguna yang menebak dengan benar.
   4.  Tersedia halaman **Leaderboard** yang menampilkan peringkat semua pengguna berdasarkan total poin prediksi mereka.
* **Integrasi AJAX:** Proses memilih prediksi dilakukan via AJAX. Ketika pengguna mengklik sebuah tim, pilihan mereka langsung disimpan ke database, dan UI akan memberikan feedback visual (misalnya, menyorot tim yang dipilih) untuk mengonfirmasi bahwa prediksi telah dicatat.

---
## Initial Dataset
https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017
https://www.kaggle.com/datasets/hamzaadhnanshakir/international-football-tournament-results

Data akan kami olah untuk menyajikan 100 Historical Tournaments (Sudah pernah dilaksanakan) sebagai initial dataset.

---

## User's Role Explained 

Aplikasi "Turnamenku" dirancang untuk melayani dua jenis pengguna utama dengan hak akses dan kemampuan yang berbeda. Pembagian peran ini penting untuk menjaga integritas data dan memberikan pengalaman yang sesuai bagi setiap pengguna.

---

### 1. Penyelenggara (Tournament Maker)

* **Deskripsi:**
   Peran ini ditujukan bagi pengguna yang ingin membuat, mengelola, dan menyelenggarakan turnamen mereka sendiri di platform ini. Mereka adalah administrator dari sebuah event turnamen.

* **Hak Akses & Kemampuan:**
   * **Membuat Turnamen Baru:** Memiliki akses ke halaman atau *dashboard* khusus untuk membuat entitas turnamen baru, lengkap dengan deskripsi, jadwal, dan banner.
   * **Mengelola Turnamen:** Dapat mengedit detail turnamen, mengatur jadwal pertandingan (`Match`), dan yang terpenting, memasukkan atau memperbarui skor pertandingan yang sedang berlangsung atau telah selesai.
   * Memiliki semua kemampuan yang dimiliki oleh peran **Pemain**.

---

### 2. Pemain (Player)

* **Deskripsi:**
   Ini adalah peran standar untuk semua pengguna yang mendaftar di platform. Mereka adalah partisipan, audiens, dan kontributor konten sosial dalam sebuah turnamen.

* **Hak Akses & Kemampuan:**
   * **Manajemen Profil:** Dapat membuat dan mengedit profil pengguna mereka sendiri.
   * **Partisipasi Tim:** Dapat membuat tim baru untuk sebuah turnamen atau bergabung dengan tim yang sudah ada.
   * **Interaksi Forum:** Dapat membuat *thread* diskusi baru dan mengirimkan komentar di forum spesifik turnamen.
   * **Melakukan Prediksi:** Dapat berpartisipasi dalam fitur *Tournament Prediction* dengan memberikan suara pada tim yang mereka jagokan.
   * **Akses Umum:** Dapat melihat semua halaman publik seperti daftar turnamen, detail pertandingan, profil tim, dan *leaderboard* prediksi.

---

### Implementasi Teknis

Pembagian peran ini diimplementasikan langsung pada model `User` kustom di aplikasi `main`.

* Sebuah *field* bernama `role` ditambahkan ke model `User` dengan pilihan (choices) yang telah ditentukan, yaitu `'PENYELENGGARA'` dan `'PEMAIN'`.
* Di dalam *views* dan *templates*, nilai dari *field* `role` ini akan digunakan untuk mengatur logika bisnis. Contohnya:
   * Tombol "Buat Turnamen" hanya akan muncul jika `user.role == 'PENYELENGGARA'`.
   * *View* yang memproses form pembuatan turnamen akan memiliki pengecekan untuk memastikan hanya penyelenggara yang dapat mengaksesnya, mencegah akses tidak sah melalui URL langsung.


---


## Link PWS Deployment-Web Design
- PWS: [https://pbp.cs.ui.ac.id/gibran.tegar/turnamenku](https://gibran-tegar-turnamenku.pbp.cs.ui.ac.id)
- Design: https://www.figma.com/design/YH1UAtsqAUqK75yXMdK64S/Turnamenku-Design?node-id=1-2&p=f&t=1R1eB2GkLPTcDFhc-0

