### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
https://github.com/MuhammadMLV/hw05_final.git
```

Зайти в папку на уровень выше командой

```
cd yatube
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv env
```

```
source env/bin/activate  ИЛИ  env/scripts/activate
```


Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```

Выполнить миграции:

```
python3 manage.py migrate
```

Запустить проект:

```
python3 manage.py runserver
```
