# Despregamento en PythonAnywhere

Guía para publicar Bambi en `https://USUARIO.pythonanywhere.com` (substitúe `USUARIO` polo teu nome de usuario de PythonAnywhere en todos os pasos).

## Requisitos

- Conta en [PythonAnywhere](https://www.pythonanywhere.com) (a gratuíta abonda).
- Python **3.12 ou superior** (Django 6.1 non funciona con versións anteriores).

## 1. Subir o código

Abre unha consola *Bash* (pestana **Consoles → Bash**) e clona o repositorio:

```bash
cd ~
git clone https://gitlab.iessanclemente.net/dawd/a22dianart.git
```

> As contas gratuítas só poden acceder a algúns sitios de Internet (lista branca). Se o `git clone` falla, xera o `.zip` no teu ordenador con `git archive --format=zip --prefix=a22dianart/ -o a22dianart.zip main`, súbeo desde a pestana **Files** e descomprímeo con `unzip a22dianart.zip -d ~`.

## 2. Contorno virtual e dependencias

```bash
mkvirtualenv --python=/usr/bin/python3.13 bambi-venv
cd ~/a22dianart
pip install -r requirements.txt
```

## 3. Variables de contorno (`.env`)

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"   # copia o resultado
nano .env
```

Contido do `.env`:

```ini
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=a-chave-xerada-no-paso-anterior
DJANGO_ALLOWED_HOSTS=USUARIO.pythonanywhere.com
DJANGO_SSL_REDIRECT=True
```

Gardar en nano: `Ctrl+O`, `Intro`, `Ctrl+X`.

## 4. Base de datos e ficheiros estáticos

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py cargar_demo        # opcional: datos de demostración
```

> `cargar_demo` crea un superusuario e outras contas de demostración. En produción exixe definir no `.env` un contrasinal propio e longo: `BAMBI_DEMO_CONTRASINAL=...`. Non uses o contrasinal de desenvolvemento do README nunha web pública.

## 5. Crear a aplicación web

Pestana **Web → Add a new web app**:

1. *Next* (dominio `USUARIO.pythonanywhere.com`).
2. **Manual configuration** (non "Django").
3. A mesma versión de Python que no contorno virtual.

Na páxina da aplicación configura:

| Sección | Valor |
|---|---|
| Source code | `/home/USUARIO/a22dianart` |
| Working directory | `/home/USUARIO/a22dianart` |
| Virtualenv | `/home/USUARIO/.virtualenvs/bambi-venv` |

### Ficheiro WSGI

Preme a ligazón *WSGI configuration file*, borra todo o contido e pon:

```python
import os
import sys

path = '/home/USUARIO/a22dianart'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'bambi.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### Ficheiros estáticos e subidos

En **Static files**:

| URL | Directory |
|---|---|
| `/static/` | `/home/USUARIO/a22dianart/staticfiles` |
| `/media/` | `/home/USUARIO/a22dianart/media` |

### Seguridade

Activa **Force HTTPS** na sección *Security*.

Preme **Reload** e abre `https://USUARIO.pythonanywhere.com`.

## 6. Tarefa programada: caducidade das reservas

Na pestana **Tasks**, crea unha tarefa diaria (a conta gratuíta permite unha) á hora que prefiras, por exemplo ás 03:00, co comando:

```bash
cd /home/USUARIO/a22dianart && /home/USUARIO/.virtualenvs/bambi-venv/bin/python manage.py caducar_reservas
```

Pecha as reservas co prazo vencido, libera os exemplares e aplica a penalización de fiabilidade. A saída (`Reservas caducadas: N`) queda no log da tarefa.

## Actualizar a web despois de cambios

```bash
workon bambi-venv
cd ~/a22dianart
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

E despois **Reload** na pestana Web.

## Problemas habituais

- **Erro 500 / "Something went wrong"**: mira o *Error log* (ligazón na pestana Web).
- **Bad Request (400)**: o dominio non está en `DJANGO_ALLOWED_HOSTS`.
- **Páxina sen estilos**: falta `collectstatic` ou a ruta de `/static/` está mal.
- **"Falta a variable de contorno DJANGO_SECRET_KEY"**: o `.env` non está en `/home/USUARIO/a22dianart/.env`.
- As contas gratuítas caducan se non se entra nelas: hai que premer *Run until 3 months from today* na pestana Web de vez en cando.
