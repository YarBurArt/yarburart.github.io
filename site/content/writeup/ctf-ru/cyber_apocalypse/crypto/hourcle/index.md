+++
title = "Hourcle"
source = "CTF (RU)"
event = "Cyber apocalypse 2025"
category = "Crypto"
categories = ["Crypto"]
tags = ["Crypto", "Cyber apocalypse 2025", "CTF (RU)"]
showDate = false
+++

Подготовлено: `rasti`

Автор задания: `rasti`

Уровень сложности: Легко

## Описание 

- Могучее заклинание, созданное чтобы скрывать, небрежно было переосмыслено и теперь открывает больше, чем скрывает. Дурак искал безопасности, но создал проход для тех, кто осмелится заглянуть за пределы иллюзии. Сможешь ли ты воспользоваться самим заклинанием, предназначенным для защиты своих тайн, и обратить его в свою волю?

В таске дано только один файл:
- `server.py` срабатывет при подключении через утилиты типа nc, основная логика шифрования, проверки и чтения флага

## Анализ исходного кода

```python
def show_menu():
    return input('''
=========================================
||                                     ||
||   🏰 Теневая Крепость Эльдории 🏰  ||
||                                     ||
||  [1] Запечатай своё имя в Архивах   ||
||  [2] Войди в Запретное Святилище    ||
||  [3] Покинь Царство                 ||
||                                     ||
=========================================

Выбери свой путь, путешественник :: ''')

def main():
    while True:
        ch = show_menu()
        print()
        if ch == '1':
            username = input('[+] Произнеси своё имя, чтобы оно было запечатано в архивах :: ')
            pattern = re.compile(r"^[\w]{16,}$")
            if not pattern.match(username):
                print('[-] Древние писцы принимают только надлежащие имена-запрещённые символы не допускаются.')
                continue
            encrypted_creds = encrypt_creds(username)
            print(f'[+] Твои учётные данные были запечатаны в зашифрованных свитках: {encrypted_creds.hex()}')
        elif ch == '2':
            pwd = input('[+] Шепни священное заклинание, чтобы войти в Запретное Святилище :: ')
            if admin_login(pwd):
                print(f"[+] Врата открываются перед тобой, Хранитель Тайн! {open('flag.txt').read()}")
                exit()
            else:
                print('[-] Ты не пройдёшь!')
        elif ch == '3':
            print('[+] Ты отворачиваешься от теней и растворяешься в тумане...')
            exit()
        else:
            print('[-] Оракул не понимает твоих слов.')

```

У нас есть три варианта:
- написать имя, сервер его зашифрует вместе с захардкоженым паролем и вернет в хексах, но имя должно быть от 16 символов из за паддинга шифра
- написать пароль, и если верный мы получим флаг
- просто выйти

Посмотрим как приложение шифрует имя и пароль из первого варианта 
```python
import os, random, string
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

KEY = os.urandom(32)

password = ''.join(
    [random.choice(string.ascii_letters+string.digits)
     for _ in range(57)]
)

def encrypt_creds(user):
    padded = pad((user + password).encode(), 16)
    IV = os.urandom(16)
    cipher = AES.new(KEY, AES.MODE_CBC, iv=IV)
    ciphertext = cipher.decrypt(padded)
    return ciphertext
```

Здесь видно, что ключ захардкоженный в `KEY`, и используется сразу для всех пар кред, что уже странно. Более того, шифр не стандартный, используют AES в режиме CBC через дешифрование чистого текста.

## Решение

Основы как работает дешифрование AES CBC

![](https://raw.githubusercontent.com/hackthebox/cyber-apocalypse-2025/refs/heads/main/crypto/hourcle/assets/aes-cbc.png)

Для дешифрования, шифротекст и исходный текс поменяны местами.

Можно заметить, что для одинаковых блоков открытого текста шифрование даёт одинаковые блоки. Это особенность AES-ECB и причина, по которой его избегают для криптографии. Хотя в этой задаче AES используется в режиме расшифрования CBC, что особо не меняет сам процесс эксплуатации.

Зная вектор инициализации, мы можем продолжить эксплуатацию оракула AES-CBC. После небольшого исследования в сети наткнёшься на так называемую атаку оракула AES-ECB [оригинал](https://www.ctfrecipes.com/cryptography/symmetric-cryptography/aes/mode-of-operation/ecb/ecb-oracle#exploitation) , статьи на русском [AES-ECB oracle](https://habr.com/ru/articles/855906/) и [AES-CBC oracle](https://habr.com/ru/articles/247527/) . Обе эти техники часто используются в CTF.

Предположим, существует оракул, который шифрует сообщения вида user_input || secret. Секрет остаётся тем же для каждого вызова оракула и пусть это 16-байтовый пароль. Тогда если мы отправим ввод длиной 15 байт, блоки будут разделены так:

```
Block 0 : AAAAAAAAAAAAAAAx
Block 1 : xxxxxxxxxxxxxxxx
Block 2 : pppppppppppppppp
```

где A это наши байты ввода, x это любые неизвестные байты пароля, а p это байты паддинга и выравнивания. Следовательно:

- Block 0 : мы знаем всё, **кроме** одного байта
- Block 1 : мы ничего не знаем
- Block 2 : мы знаем весь блок

Хотя последний байт Block 0 неизвестен, общеизвестно, что пароль состоит из буквенно-цифровых символов, поэтому его тривиально подобрать брутом. Следовательно, можно зафиксировать 15 байт и перебрать последний байт первого блока как:

```
Block 0 : AAAAAAAAAAAAAAA?
```

Правильный байт совпадёт с исходным шифротекстом для `AAAAAAAAAAAAAAAx`.

Имея первый байт пароля, можно отправить 14 байт входа + найденный байт пароля + перебрать следующий байт пароля:

```
Block 0 : AAAAAAAAAAAAAAx?
```

В нашей задаче нельзя отправлять имя пользователя короче 16 байт, поэтому нужно начинать с Block 1, а не с Block 0. Это означает, что мы начинаем с отправки 31 байта ввода + 1 перебираемый байт и продолжаем тем же методом.

Автоматизация атаки 
```python
import string

alph = string.ascii_letters + string.digits
password = ''
block_num = 1

while len(password) < 57:
  	# префикс символов ввода исходника
    plaintext = 'x' * ((block_num+1) * 16 - 1 - len(password))
    # получить целевой шифротекст, с которым мы можем проверить валидность перебора текущего байта
    target_ct = encrypt(plaintext)
    current_target_ct_block = _b(target_ct)[block_num]
		
    # перебор последнего по алфавиту
    for c in alph:
      	# send : input || password || ?
        pt = (plaintext + password + c).encode()
        current_test_ct_blocks = _b(encrypt(pt))

        if current_test_ct_blocks[block_num] == current_target_ct_block:
            password += c
            # если блок заполнен, перемещаемся к следующему
            if len(password) % 16 == 0:
                block_num += 1
            print(password)
            break
    else:
        print(f'ошибка в блоке {block_num}')
        exit()
```

И автоматизация получения флага
```python
# ... подключение через pwntools
def admin_login(pwd):
    io.sendlineafter(b'traveler :: ', b'2')
    io.sendlineafter(b'Sanctum :: ', pwd.encode())
    resp = io.recvline().decode().strip()
    return re.findall(r'HTB{.+}', resp)[0]

print(admin_login(password))
```
