# Заглушки и инструкции к запуску Московского ДЭГ
## Заявление

На мой взгляд, ДЭГа в России быть не должно. 

Система ДЭГ, использовавшаяся в Москве на выборах в 2021 году неподконтрольна для наблюдения. 
В системе присутствует приватный блокчейн, о наличии которого члены комиссии осведомлены не были и не инструментов за ним наблюдать.
Подсчёт голосов был произведён с существенной задержкой, которая не может быть объяснена объективными причинами.

ДЭГ перевернул результаты выборов в Москве, украв победу у многих оппозиционных кандидатов.
В данных, полученных из ДЭГ по итогам голосования, прослеживаются очевидные аномалии, свидетельствующие о фальсификациях, о чём
можно прочитать [вот тут](https://novayagazeta.ru/articles/2021/09/30/mandaty-polzuiutsia-vbrosom), [вот тут](https://novayagazeta.ru/articles/2021/11/09/zazor-i-pozor)
и в видеоформе посмотреть [вот тут](https://www.youtube.com/watch?v=4ffEHROI8WI) и [вот тут](https://www.youtube.com/watch?v=SFogBbUGLk4).

Анализ исходного кода системы ДЭГ был сильно затруднён тем, что до недавнего времени, было невозможно запустить локально своё собственное электронное голосование.
Часть исходных кодов опубликована не была, а для опубликованной части отсутствуют конфигурационные файлы, без которых работа системы невозможно.
Запуск системы был осложнён многоичисленными ошибками, зависаниями и тд.

Этот репозиторий призван решить эту проблему и упростить анализ системы.

## Инструкция по запуску.

1. Поднимаем заглушки, базы и очереди RabbitMQ через `docker compose up --detach`.
1. Настраиваем PHP окружение для запуска необходимых компонентов ДЭГ (ниже подробнее).
1. Клонируем код с репозиторием ДЭГ с необходимыми для работы изменениями. Их можно найти в этой ветке: https://github.com/PeterZhizhin/blockchain-voting_2021_extracted/tree/fix_deg
1. Ставим [PHP Composer](https://getcomposer.org/) и в каждом из сервисов делаем `php composer install`. 
1. Копируем файлы `.env` и папки `config` в каждый из сервисов из компоненты `form`, конфигурацию можно найти в папке `sample_deg_configs`.
1. В каждом из компонентов ДЭГ (`form`, `ballot`, `componentX`, `encryptor`) запускаем `php artisian swoole:http start`.
1. Переходим по адресу [http://localhost:8004/election](http://localhost:8004/election) и пробуем голосовать.
Если всё будет правильно, то у вас получится получить код по SMS. **Сами SMS не отправляются**, надо посмотреть в stderr сервиса `form`,
там будет написан код который нужно ввести.
Если всё правильно настроено, то вы сможете поставить галочку и проголосовать.
1. Проверяем что голос попал в `p_ballot`, для этого переходим на [http://localhost:8080/](http://localhost:8080/) и указываем
```
system: PostgreSQL
server: postgres
username: deg_user
password: deg_user_password
database: deg_ballot_db
```
Дальше можно проверить, что голос есть в `p_ballot`, перейдя на эту таблицу, там на вкладку "Select data".
1. Проверяем, что голос есть в очереди RabbitMQ. Для этого переходим на [http://localhost:15672/](http://localhost:15672/). Логин/Пароль `guest/guest`.
На вкладке Queues видим очередь `mgik_queue-123`, переходим на неё. Дальше снизу "Get Messages", выбираем сообщение, оно должно быть. 
Получили строку типа такой:
```
LH2acRfLrI21sYhRbK6Ygx5u2JOVHzMSZPOZdScPi83uBfVidOIokHiHVx7antPRNgOfRcOxlO2BJeRRFd/JTchNxaQBOQD/CSKdYD6ompFf5TdgdGi8oMuXFkwA/EqQO3AI4NIF3vLUWtAznXvqmBjXfn3IsKHhmOsv4oaXIOBLIPaRsG1vJF/EQN5gnoASRqWfHEhf43v47SDkOI+ljitaPGBltFJtZ3YG3t9XtFVcsHd1WhwDeLmOgSxM07ASOmhh1TydBv/Kv3AR/wD+eP4a42FeXFEKl2CWbKfR+VpSHkpHi2FST93xxY3erEwRKYwX4udCA442SxF8QGVctOf+QPFf2aJu65IAMY1S6AZpdYLSnR0+yep6/UkTbK1Pi2BxjO6hMgNJZmBOFV4btpCn/z8Qby/g6VcblNnL+vz0ZUg+OlZ9tGNLJmPERmZZh0/B1LzfTDwHiq1dO4yYqtxbYPR7CPoD6fr1riKaAHDRJuQvrgSKNucv+7BYA58/7q7rJ+SIVygXiijkX+6CByI07CpAloPOGo3l+Z3om1uEKwc/q0EfCufqz3PJpAh93EiuXG6MKrpQ4DE7gUkgyXzfrdqhQ/1GRW/eDINYbEpebC9Y91giYLBdgrE6EwsPhf858DSTDYLftB1PYTlqkCQeSCRYkWxpoW4fO3wXEIBiwAEk6k8xLsVQGX4HzUz8xHueAXSsFIYHWf9rUc9E5XVGHy3tMFrRaLD8WXoz/Pbi3Y9Yscik7CIg5DShb9w7f/JBTpUFd8HnCjT6qB19giYfLnitR7obs7UCWEQ87J+wcvs9VfI3uvxGaHuN469Y8Nfp084MWEW/Q8jpSchpZ9MyWMRSOp3HuM1Gp8NnxPv8/rnxDqh5OgrGvpxkljyW9Q7X5CY5Yi/xI5ifBPfKsHDzK3A8+X9+XFxrJBNOaewCAry/zklFAMZr/p9q41uLxsMJb1AqK1EumDC/z/YzIvPZaLOb5I4LYpRv/Qsx21g1FhYp1WEycjurP+/DOz7D85K8oCoXD+Cl96mB06fO5MH3B83E7CbNO0DVrwYFwkd38q7N7yKmLHoY3a4wLpgK+tO5n23Oz419oFAoFvnkQJGMY+sfQ8OvtpzqMt8iuhXoqRDdKdXaCSnlUtQjs2hIQgdxX8JEGzerhvh9GzbU5dlio6In1xzWegKxiW6GmNpbQyo38WcqMIIhSO1czLHS2I2VilM33zUlqnkBIJzWn8Bz26YZ7JRGaLKPwNNLkNFx7lkiKk28Mb0WpL2q+eLi7oBiJqwKh7BU1w423qH66pz9T938sqrsPn87mgXwZBGhtx+/v3koFT3vvL5P1xKDvUBG5bKMKuw0j8sGGV/F5tjZcn1ZU+SPOEOe+NAqOfbQz2i1iIMZlvBsdLv33A0N
```
Её нужно расшифровать, для этого во-первых делаем urlencode (например вот тут вот: https://www.urlencoder.org/) дальше делаем `curl` запрос:
```
curl --header "SYSTEM: TestSystem" --header "SYSTEM_TOKEN: TOKEN_SECRET" "http://127.0.0.1:8001/api/encryption/decrypt?data[base64body]=<urlencode(строчка из RabbitMq)>"
```
Должно успешно расшифроваться и получиться вот примерно такое сообщение (после прогона через `jq -cr .data.result | jq`):
```
{
  "voterAddress": "ffd60326d82e8906500f350405b8b22b6d3d41a86f1914131c338740077e388a",
  "districtId": 198,
  "keyVerificationHash": "42df7f80033a7de73d926a1f127cc6566d91c314c24e9e7c93cdf1e5883d2710",
  "tx": "0a6d0a6b0a0508e907100612620a0010c6011a5b0a19f87ee8555423659cc9dae26c93051588a1dd75126348189518121a0a1849eb7d8d5af3a0615bba52fa239d0cb65d634483352fc8d81a220a20c91a590c2e8c7af09f947729b84c68477924adaa6572953e6a75d314921b2d4e12220a20ffd60326d82e8906500f350405b8b22b6d3d41a86f1914131c338740077e388a1a420a40d4ae1b4dc5303858104f8ec3cced5956444fee51142ee4240b5f9bf0a83078b1808e491cbf08e12eecd43c1d6d55a30547bdeb4b62b211391f4ae85f563c0705",
  "encryptedGroupId": "IbLfUXJ1QQZprl8pSqMoT1Ks0AvEt4hL+OkTNdSVxNGkDUjdoa654BADaMbD+Zll/Qdnn070iq05LLR7nVdIT4q5fQ4fPDpf2Y/eShqof6/1nmMmKIIJlB6DA/64zpAjwOJO7SxYx6mzmYSIjSEgoTGfDKtMRpAxbGvZiTKPmcfM2312S77wOjwSlI47dStWPQ47NjmAlkyttjR8JuK9ePm1wCX9zqw0uunglDCwYWGes5Gh8F7Rb3snWej21ELwjCgJhEEc109lscazYqOUr9pr7oi0cLXKpka/vazgW0PLO9gy4nxP7xtOJDQAReeH",
  "voteDateTime": "1641117415.182240"
}
```

## Настройка окружения PHP

Окружение настраивается примерно таким образом (Ubuntu):
```
sudo apt-get install php-fpm php-pgsql php-redis php-dev php-xml
```

Затем необходимо установить PHP Swoole:
```
sudo pecl install swoole
```
Потом нужно добавить модуль через phpenmod примерно вот так:
```
sudo bash -c "cat > /etc/php/7.4/mods-available/swoole.ini << EOF
; Configuration for Open Swoole
; priority=30
extension=swoole
EOF"
sudo phpenmod -s cli swoole
```

Далее нужно установить [Стрибог](https://ru.wikipedia.org/wiki/%D0%A1%D1%82%D1%80%D0%B8%D0%B1%D0%BE%D0%B3_(%D1%85%D0%B5%D1%88-%D1%84%D1%83%D0%BD%D0%BA%D1%86%D0%B8%D1%8F)) расширение для PHP.
Для этого воспользуемся инструкциями из вот этого репозитория: https://github.com/sjinks/php-stribog.

## Почему этот репозиторий существует
В исходных кодах московского ДЭГ ([оригинальный репозиторий](https://github.com/moscow-technologies/blockchain-voting_2021),
[перезалитый в распакованном виде](https://github.com/PeterZhizhin/blockchain-voting_2021_extracted))
отсутсвует часть необходимых сервисов, необходимых для запуска ДЭГ.

Также отсутствует необходимая конфигурация, которая бы позволила запустить электронное голосование.

На данный момент идентифицировано, что не опубликованы исходные коды следующих компонентов (галочкой отмечены реализованные в этом репозитории части)
- [ ] АРМ Председателя.
- [ ] Сервис записи в блокчейн.
- [x] СУДИР -- Система управления доступа к информационным ресурсам.
- [x] MDM (Реестр участников голосования) -- Реестр избирателей, осуществляющий проверку активного избирательного права.
Также он выдаёт `group id` пользователям (уникальный ID, одинаковый для каждого избирателя), который используется для учёта переголосований.
- [x] Сервис, который раздаёт настройки голосования (URL хостов, публичный ключ шифрования бюллетеней для передачи на фронт, имена кандидатов и тд).
- [ ] Сервис рассылки SMS.
- [ ] Сервис рассылки Email.

## Реализованные заглушки
### Сервис по раздаче настроек

При первом запуске компоненты `componentX`, `ballot` и `form` запрашивают настройки с сервера.
В них указываются технические характеристики голосования (например, публичный ключ для шифрования),
имена кандидатов и тд.

В заглушках для этого используется NGINX, который отдаёт необходимые JSON. По-хорошему туда надо дописать ещё и проверку хэдеров
`SYSTEM` и `SYSTEMTOKEN`, но я этого не сделал.

### СУДИР (`fake_sudir`)
Чтобы пользователь мог сделать запросы к форме голосования -- ему нужно авторизироваться.
Используется протокол `authorization_code` из OAuth2.

fake_sudir предоставляет базовую функциональность авторизации. Сервис доступен по адресу http://localhost:8025.

При первом старте сервера создаётся пользователь `admin` и OAuth2 клиент для компонента form.
Можно зайти в него, если ввести в поле `user` просто `admin`.

При заходе на компонент `form` -- пользователя редиректит на `fake_sudir` для авторизации.

У пользователя должны стоять поля телефона и Email, для этого на странице авторизации нужно ввести их в поля.

### MDM (`fake_mdm`)

Данный должен проверять наличие активного избирательного права, то есть должен проверять, что пользователь имеет одобренную заявку на ДЭГ.
Компонент form обращается по вот этим двум ссылкам этого компонента:
1. POST `/checkBallot` -- на вход приходит JSON с полем `ssoID` -- ID пользователя, должен вернуть sha256 "подпись" и статус, имеет ли человек право голосовать.
Например, он может сообщить что превышен лимит числа переголосований. В fake_mdm просто возвращается, что всё ОК и человек может голосовать.
2. POST `/getBallot` -- как `checkBallot`, но должен по идее как-то помечать, что пользователю выдали бюллетень. В fake_mdm просто возвращается, что всё ОК.

Также этот сервис реализует выдачу group id для пользователей. На вход приходит хэш ssoId, на выход должны вернуть group id этого пользователя.
